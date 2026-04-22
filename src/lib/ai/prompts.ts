// System prompts per task — what kind of artifact GPT/Lovable AI should produce.

export interface TaskPromptSpec {
  system: string;
  userTemplate: string;
  artifactPath: string; // primary artifact path (relative to artifacts/)
  artifactKind: "json" | "md";
  expectsJson: boolean;
}

const ARABIC_RULE = `أنت محرّك توليد artifacts دائمة ضمن مشروع FATHIYA Ops Console.
القواعد:
1. المخرجات يجب أن تكون نهائية وقابلة للنشر تحت artifacts/ مباشرة.
2. اكتب المحتوى المطلوب فقط — لا مقدمات ولا اعتذارات ولا شروحات خارج الملف.
3. إذا كان المطلوب JSON — أرجع JSON صالح فقط (بدون \`\`\`json fences).
4. إذا كان MD — أرجع Markdown نظيف بعناوين هرمية واضحة.
5. لغة العمل: عربي للمحتوى الفكري، إنجليزي تقني للمفاتيح/الحقول/الأكواد.`;

export const TASK_PROMPTS: Record<string, TaskPromptSpec> = {
  T01: {
    system: ARABIC_RULE,
    userTemplate: `Security Playbook Surface — صمّم 5 مداخل تشغيل أمنية فوق فتحية:
target_profiling, surface_mapping, recon_planning, evidence_review, status_report.
لكل مدخل: id, title_ar, title_en, inputs[], outputs[], gates[], primary_provider, fallback_provider, when_to_use, when_to_skip.
أرجع JSON واحد بالشكل: { "version": 1, "entries": [...] }`,
    artifactPath: "playbooks/security.surface.entries.json",
    artifactKind: "json",
    expectsJson: true,
  },
  T02: {
    system: ARABIC_RULE,
    userTemplate: `Security Evals Library — مكتبة حالات اختبار ثابتة لنواة فتحية الأمنية.
غطّي: domain صحيح، ip صحيح، cidr صحيح، invalid input، false positive، early-stop case، report consistency.
لكل حالة: id, category, input, expected_route, expected_extracted_fields, expected_status, fail_conditions[], notes.
أرجع JSON: { "version": 1, "cases": [...] } بحد أدنى 12 حالة.`,
    artifactPath: "evals/security.cases.json",
    artifactKind: "json",
    expectsJson: true,
  },
  T03: {
    system: ARABIC_RULE,
    userTemplate: `Security Routing Matrix — مصفوفة توجيه أي مهمة أمنية إلى المزود المناسب.
المزودون: claude, gpt-5, gemini-pro, gemini-flash, perplexity, manus.
لكل task_type (recon, vuln_analysis, report_writing, threat_intel, incident_review, false_positive_check):
primary, fallback, cheap, premium, when, why, max_tokens_hint, fail_closed.
أرجع JSON: { "version": 1, "policy": {...} }`,
    artifactPath: "routing/security.matrix.json",
    artifactKind: "json",
    expectsJson: true,
  },
  T05: {
    system: ARABIC_RULE,
    userTemplate: `Account Registry Schema — JSON Schema موحّد لسجل حسابات FATHIYA.
الحقول الإلزامية: provider, account_id, status (active/draining/exhausted/banned), balance_state, customization_profile (ref to profiles/), domain_pool[], last_success_at, last_failure_at, fallback_group, notes.
أرجع JSON Schema (draft 2020-12) بصيغة { "$schema": "...", "type": "object", "properties": {...}, "required": [...] }`,
    artifactPath: "registry/accounts.schema.json",
    artifactKind: "json",
    expectsJson: true,
  },
  T07: {
    system: ARABIC_RULE,
    userTemplate: `Account Readiness Validator Rules — قواعد فحص جاهزية كل حساب قبل استخدامه.
الفحوصات: customized?, warm?, valid_output?, assigned_pool?, draining?, exhausted?, recent_failure?, rate_limited?.
لكل قاعدة: id, check, severity (block/warn/info), action_on_fail, related_field.
أرجع JSON: { "version": 1, "rules": [...] }`,
    artifactPath: "registry/validator.rules.json",
    artifactKind: "json",
    expectsJson: true,
  },
  T10: {
    system: ARABIC_RULE,
    userTemplate: `Competitive Capability Map — مقارنة عملية بين المزودين.
المزودون: Manus, Claude, Perplexity, GPT-5, OpenRouter, Lovable AI Gateway.
لكل مزود × مهمة (research, code, reasoning, writing, security_review, crypto_analysis, structured_output, long_context):
score (0-10), cost_tier (free/cheap/mid/premium), risk_tier (low/mid/high), notes.
أرجع JSON: { "version": 1, "providers": [...], "tasks": [...], "matrix": [[...]] }`,
    artifactPath: "capability_map.json",
    artifactKind: "json",
    expectsJson: true,
  },
  T13: {
    system: ARABIC_RULE,
    userTemplate: `Crypto Routing Matrix — أي مهمة كريبتو → أي مزود.
task_types: news_scan, narrative_analysis, thesis_review, transformation, invalidation_check, report.
نفس بنية security routing: primary, fallback, cheap, premium, when, why, fail_closed.
أرجع JSON: { "version": 1, "policy": {...} }`,
    artifactPath: "routing/crypto.matrix.json",
    artifactKind: "json",
    expectsJson: true,
  },
  T14: {
    system: ARABIC_RULE,
    userTemplate: `Crypto Evals Set — حالات تقييم لمحرك كريبتو.
غطّي: false narrative, conflicting signals, hype vs evidence, invalid thesis, missing data, no-trade case, FOMO trap, exit signal.
لكل حالة: id, category, scenario, expected_action (trade/no_trade/research_more/abort), invalidation_signals[], notes.
أرجع JSON: { "version": 1, "cases": [...] } بحد أدنى 10.`,
    artifactPath: "evals/crypto.cases.json",
    artifactKind: "json",
    expectsJson: true,
  },
};

export function getPromptForTask(taskId: string): TaskPromptSpec | null {
  return TASK_PROMPTS[taskId] ?? null;
}
