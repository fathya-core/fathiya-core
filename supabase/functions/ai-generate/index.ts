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
  provider?: "openrouter" | "huggingface";
  system?: string;
  user?: string;
  taskId?: string;
  saveAs?: string;
  saveKind?: "json" | "md";
  expectsJson?: boolean;
}

interface ProviderConfig {
  url: string;
  apiKey: string;
  headers: Record<string, string>;
  bodyExtra: Record<string, unknown>;
}

function getProviderConfig(
  provider: "openrouter" | "huggingface",
  model: string,
): ProviderConfig | { error: string } {
  if (provider === "openrouter") {
    const apiKey = Deno.env.get("OPENROUTER_API_KEY");
    if (!apiKey) {
      return {
        error:
          "OPENROUTER_API_KEY not configured. Add it via Supabase Edge Function secrets.",
      };
    }
    return {
      url: "https://openrouter.ai/api/v1/chat/completions",
      apiKey,
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://fathiya.ops",
        "X-Title": "FATHIYA Ops Console",
      },
      bodyExtra: {},
    };
  }

  // huggingface
  const apiKey = Deno.env.get("HUGGINGFACE_API_KEY");
  if (!apiKey) {
    return {
      error:
        "HUGGINGFACE_API_KEY not configured. Add it via Supabase Edge Function secrets.",
    };
  }
  return {
    url: `https://router.huggingface.co/v1/chat/completions`,
    apiKey,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    bodyExtra: {},
  };
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  try {
    let body: GenerateBody;
    try {
      body = await req.json();
    } catch {
      return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
    }

    const provider = body.provider || "openrouter";
    const model = body.model || "google/gemini-2.5-flash";
    const systemPrompt = body.system || "You are a helpful assistant.";
    const userPrompt = body.user;

    if (!userPrompt) {
      return jsonResponse({ ok: false, error: "user prompt is required" }, 400);
    }

    const config = getProviderConfig(provider, model);
    if ("error" in config) {
      return jsonResponse({ ok: false, error: config.error }, 500);
    }

    const startedAt = Date.now();

    const requestBody: Record<string, unknown> = {
      model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      ...config.bodyExtra,
    };

    if (body.expectsJson) {
      requestBody.response_format = { type: "json_object" };
    }

    const upstream = await fetch(config.url, {
      method: "POST",
      headers: config.headers,
      body: JSON.stringify(requestBody),
    });

    const durationMs = Date.now() - startedAt;

    if (!upstream.ok) {
      const text = await upstream.text();
      let errMsg = `${provider} API error ${upstream.status}`;
      if (upstream.status === 429)
        errMsg = "Rate limited -- try again shortly";
      if (upstream.status === 401) errMsg = `Invalid ${provider} API key`;
      if (upstream.status === 403)
        errMsg = `API key does not have access to model: ${model}`;
      if (upstream.status === 404)
        errMsg = `Model not found: ${model}`;

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

      return jsonResponse(
        { ok: false, error: errMsg, upstream: text },
        upstream.status === 429 ? 429 : 502,
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

      return jsonResponse(
        { ok: false, error: "Empty response from model" },
        502,
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

          return jsonResponse(
            { ok: false, error: "Model returned invalid JSON", raw: content },
            502,
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

    return jsonResponse({
      ok: true,
      model,
      provider,
      taskId: body.taskId ?? null,
      content,
      saved: !!savedPath,
      savedPath,
    });
  } catch (e) {
    return jsonResponse({ ok: false, error: String(e) }, 500);
  }
});

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

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
