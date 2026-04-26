import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.49.4";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers":
    "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface GenerateBody {
  model?: string;
  system?: string;
  user?: string;
  taskId?: string;
  saveAs?: string;
  saveKind?: "json" | "md";
  expectsJson?: boolean;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  try {
    const OPENAI_API_KEY = Deno.env.get("OPENAI_API_KEY");
    if (!OPENAI_API_KEY) {
      return new Response(
        JSON.stringify({
          ok: false,
          error:
            "OPENAI_API_KEY not configured. Add it via Supabase Edge Function secrets.",
        }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    let body: GenerateBody;
    try {
      body = await req.json();
    } catch {
      return new Response(
        JSON.stringify({ ok: false, error: "Invalid JSON body" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    const model = body.model || "gpt-4o-mini";
    const systemPrompt = body.system || "You are a helpful assistant.";
    const userPrompt = body.user;

    if (!userPrompt) {
      return new Response(
        JSON.stringify({ ok: false, error: "user prompt is required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    const startedAt = Date.now();

    const upstream = await fetch(
      "https://api.openai.com/v1/chat/completions",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${OPENAI_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt },
          ],
          ...(body.expectsJson
            ? { response_format: { type: "json_object" } }
            : {}),
        }),
      },
    );

    const durationMs = Date.now() - startedAt;

    if (!upstream.ok) {
      const text = await upstream.text();
      let errMsg = `AI API error ${upstream.status}`;
      if (upstream.status === 429) errMsg = "Rate limited -- try again shortly";
      if (upstream.status === 401) errMsg = "Invalid API key";
      if (upstream.status === 403) errMsg = "API key does not have access to this model";

      await logRun({
        taskId: body.taskId ?? null,
        model,
        system: systemPrompt,
        user: userPrompt,
        output: text.slice(0, 4000),
        savedPath: null,
        saveKind: null,
        status: "error",
        errorMessage: errMsg,
        httpStatus: upstream.status,
        durationMs,
      });

      return new Response(
        JSON.stringify({ ok: false, error: errMsg, upstream: text }),
        {
          status: upstream.status === 429 ? 429 : 502,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    const data = await upstream.json();
    const content = data.choices?.[0]?.message?.content ?? "";

    if (!content.trim()) {
      await logRun({
        taskId: body.taskId ?? null,
        model,
        system: systemPrompt,
        user: userPrompt,
        output: null,
        savedPath: null,
        saveKind: null,
        status: "error",
        errorMessage: "Empty response from model",
        httpStatus: 502,
        durationMs,
      });

      return new Response(
        JSON.stringify({ ok: false, error: "Empty response from model" }),
        {
          status: 502,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    const savePath = body.saveAs ?? null;
    const saveKind = body.saveKind ?? (body.expectsJson ? "json" : "md");
    let savedPath: string | null = null;

    if (savePath) {
      const safe = savePath.replace(/^\/+/, "").replace(/\.\.\//g, "");
      savedPath = `artifacts/${safe}`;

      if (saveKind === "json") {
        let cleaned = content.trim();
        cleaned = cleaned
          .replace(/^```(?:json)?\s*/i, "")
          .replace(/```\s*$/i, "");
        try {
          JSON.parse(cleaned);
        } catch (e) {
          await logRun({
            taskId: body.taskId ?? null,
            model,
            system: systemPrompt,
            user: userPrompt,
            output: content,
            savedPath: null,
            saveKind,
            status: "error",
            errorMessage: `Invalid JSON from model: ${String(e)}`,
            httpStatus: 502,
            durationMs,
          });

          return new Response(
            JSON.stringify({
              ok: false,
              error: "Model returned invalid JSON",
              raw: content,
            }),
            {
              status: 502,
              headers: { ...corsHeaders, "Content-Type": "application/json" },
            },
          );
        }
      }
    }

    await logRun({
      taskId: body.taskId ?? null,
      model,
      system: systemPrompt,
      user: userPrompt,
      output: content,
      savedPath,
      saveKind,
      status: "ok",
      errorMessage: null,
      httpStatus: 200,
      durationMs,
    });

    return new Response(
      JSON.stringify({
        ok: true,
        model,
        taskId: body.taskId ?? null,
        content,
        saved: !!savedPath,
        savedPath,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  } catch (e) {
    return new Response(
      JSON.stringify({ ok: false, error: String(e) }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  }
});

async function logRun(row: {
  taskId: string | null;
  model: string;
  system: string | null;
  user: string | null;
  output: string | null;
  savedPath: string | null;
  saveKind: string | null;
  status: "ok" | "error";
  errorMessage: string | null;
  httpStatus: number | null;
  durationMs: number;
}) {
  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    await supabase.from("ai_runs").insert({
      task_id: row.taskId,
      model: row.model,
      system_prompt: row.system,
      user_prompt: row.user,
      output: row.output,
      saved_path: row.savedPath,
      save_kind: row.saveKind,
      status: row.status,
      error_message: row.errorMessage,
      http_status: row.httpStatus,
      duration_ms: row.durationMs,
    });
  } catch (e) {
    console.error("[ai-generate] failed to log run:", e);
  }
}
