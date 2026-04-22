// FATHIYA Ops Console — Task Stack
// Source of truth for the 16 tasks. Mirror artifacts in /artifacts/.

export type TaskStatus = "todo" | "in_progress" | "done";
export type Owner = "Claude" | "GPT" | "Perplexity" | "Manus" | "n8n" | "Zapier";
export type LayerId = "A" | "B" | "C" | "D" | "E";

export interface ExpectedArtifact {
  path: string;
  kind: "json" | "md" | "yaml" | "workflow";
  description: string;
}

export interface Task {
  id: string; // T01..T16
  code: string;
  title: string;
  description: string;
  layer: LayerId;
  owners: Owner[];
  status: TaskStatus;
  priority: 0 | 1 | 2 | 3; // 3 = top immediate priority
  artifacts: ExpectedArtifact[];
  depends_on: string[];
  notes?: string;
}

export interface Layer {
  id: LayerId;
  name: string;
  subtitle: string;
}

export const LAYERS: Layer[] = [
  { id: "A", name: "Security Ops Layer", subtitle: "النواة الأمنية فوق فتحية" },
  { id: "B", name: "Account Orchestration Layer", subtitle: "إدارة الحسابات وملفات التخصيص" },
  { id: "C", name: "Intelligence Harvest Layer", subtitle: "حصاد الاستخبارات قبل اختفاء الاشتراكات" },
  { id: "D", name: "Crypto Engine Preparation", subtitle: "تجهيز محرك الكريبتو" },
  { id: "E", name: "Knowledge Base / RAG", subtitle: "الأصول الدائمة بعد الاشتراكات" },
];

export const TASKS: Task[] = [
  // ───── A. Security Ops Layer ─────
  {
    id: "T01",
    code: "SEC_PLAYBOOK",
    title: "Security Playbook Surface",
    description:
      "5 مداخل تشغيل جاهزة فوق فتحية: target profiling, surface mapping, recon planning, evidence review, status report.",
    layer: "A",
    owners: ["Manus", "GPT", "Claude"],
    status: "todo",
    priority: 1,
    artifacts: [
      { path: "playbooks/security.surface.md", kind: "md", description: "هيكل الـ 5 مداخل" },
      { path: "playbooks/security.surface.entries.json", kind: "json", description: "تعريف كل مدخل بصيغة قابلة للتشغيل" },
    ],
    depends_on: [],
  },
  {
    id: "T02",
    code: "SEC_EVALS",
    title: "Security Evals Library",
    description:
      "حالات اختبار ثابتة: domain / ip / cidr / invalid / false positives / early-stop / report consistency.",
    layer: "A",
    owners: ["Claude", "GPT"],
    status: "todo",
    priority: 3,
    artifacts: [{ path: "evals/security.cases.json", kind: "json", description: "مكتبة evals" }],
    depends_on: [],
  },
  {
    id: "T03",
    code: "SEC_ROUTING",
    title: "Security Routing Matrix",
    description: "أي مهمة أمنية → أي مزود (primary / fallback / cheap / premium). يُحوَّل إلى JSON policy.",
    layer: "A",
    owners: ["Claude", "GPT"],
    status: "todo",
    priority: 3,
    artifacts: [
      { path: "routing/security.matrix.json", kind: "json", description: "policy قابلة للحقن" },
      { path: "routing/security.matrix.md", kind: "md", description: "شرح المنطق من Claude" },
    ],
    depends_on: ["T05", "T06"],
  },
  {
    id: "T04",
    code: "SEC_N8N",
    title: "n8n Security Operational Flow",
    description: "workflows: تشغيل أمني، تقارير، حالات قياسية، إنذارات.",
    layer: "A",
    owners: ["GPT", "n8n", "Manus"],
    status: "todo",
    priority: 1,
    artifacts: [
      { path: "workflows/n8n.security.run.json", kind: "workflow", description: "تشغيل أمني" },
      { path: "workflows/n8n.security.report.json", kind: "workflow", description: "تقارير" },
      { path: "workflows/n8n.security.alerts.json", kind: "workflow", description: "إنذارات" },
    ],
    depends_on: ["T01", "T03"],
  },

  // ───── B. Account Orchestration ─────
  {
    id: "T05",
    code: "ACCT_REGISTRY",
    title: "Account Registry Schema",
    description:
      "سجل حسابات موحد: provider, account_id, status, balance_state, customization_profile, domain_pool, last_success/failure, fallback_group.",
    layer: "B",
    owners: ["GPT"],
    status: "todo",
    priority: 3,
    artifacts: [
      { path: "registry/accounts.schema.json", kind: "json", description: "JSON Schema" },
      { path: "registry/accounts.example.json", kind: "json", description: "مثال مملوء" },
    ],
    depends_on: [],
    notes: "أولوية مباشرة #1 — كل الباقي يعتمد عليه.",
  },
  {
    id: "T06",
    code: "ACCT_PROFILES",
    title: "Customization Profiles Pack",
    description:
      "ملفات profiles جاهزة للحقن: SECURITY_BASE, CRYPTO_BASE, RESEARCH_BASE, CODE_BASE.",
    layer: "B",
    owners: ["Claude", "GPT"],
    status: "in_progress",
    priority: 3,
    artifacts: [
      { path: "profiles/FATHIYA_SECURITY_BASE.json", kind: "json", description: "Security base (stub موجود)" },
      { path: "profiles/FATHIYA_CRYPTO_BASE.json", kind: "json", description: "Crypto base (stub موجود)" },
      { path: "profiles/FATHIYA_RESEARCH_BASE.json", kind: "json", description: "Research base (stub موجود)" },
      { path: "profiles/FATHIYA_CODE_BASE.json", kind: "json", description: "Code base (stub موجود)" },
    ],
    depends_on: [],
    notes: "Stubs منشورة. ينتظر Claude يملأها بمحتوى نهائي.",
  },
  {
    id: "T07",
    code: "ACCT_VALIDATOR",
    title: "Account Readiness Validator",
    description: "فحص جاهزية كل حساب: customized? warm? valid output? assigned pool? draining/exhausted?",
    layer: "B",
    owners: ["GPT", "Claude"],
    status: "todo",
    priority: 1,
    artifacts: [
      { path: "registry/validator.rules.json", kind: "json", description: "قواعد التحقق" },
      { path: "registry/validator.script.md", kind: "md", description: "مواصفات السكريبت" },
    ],
    depends_on: ["T05", "T06"],
  },
  {
    id: "T08",
    code: "ACCT_ZAPIER",
    title: "Zapier Account Control Plane",
    description: "Tables, Forms, alerts, approval flows, draining/exhausted notifications, intake للحسابات الجديدة.",
    layer: "B",
    owners: ["Zapier", "GPT", "Claude"],
    status: "todo",
    priority: 1,
    artifacts: [
      { path: "workflows/zapier.control_plane.md", kind: "md", description: "مخطط الـ control plane" },
      { path: "workflows/zapier.intake.json", kind: "workflow", description: "intake flow" },
    ],
    depends_on: ["T05", "T07"],
  },

  // ───── C. Intelligence Harvest ─────
  {
    id: "T09",
    code: "INTEL_DOSSIERS",
    title: "Perplexity Research Dossiers",
    description:
      "ملفات استخبارات: security model map, vuln discovery tools map, crypto research map, market intelligence, premium source taxonomy.",
    layer: "C",
    owners: ["Perplexity"],
    status: "todo",
    priority: 2,
    artifacts: [
      { path: "dossiers/security_models.md", kind: "md", description: "خريطة نماذج الأمن" },
      { path: "dossiers/vuln_tools.md", kind: "md", description: "خريطة أدوات الثغرات" },
      { path: "dossiers/crypto_research.md", kind: "md", description: "خريطة أبحاث الكريبتو" },
      { path: "dossiers/market_intel.md", kind: "md", description: "استخبارات سوقية" },
      { path: "dossiers/premium_sources.json", kind: "json", description: "Taxonomy للمصادر المدفوعة" },
    ],
    depends_on: [],
  },
  {
    id: "T10",
    code: "INTEL_CAPMAP",
    title: "Competitive Capability Map",
    description: "مقارنة عملية: Manus / Claude / Perplexity / GPT / OpenRouter — لأي مهمة، بأي تكلفة، بأي مخاطر.",
    layer: "C",
    owners: ["Claude", "Perplexity", "GPT"],
    status: "todo",
    priority: 1,
    artifacts: [{ path: "capability_map.json", kind: "json", description: "matrix قابلة للاستخدام" }],
    depends_on: ["T09"],
  },
  {
    id: "T11",
    code: "INTEL_FAILURES",
    title: "Failure Library",
    description: "متى يفشل كل مزود؟ متى يهلوس؟ متى يوسّع بلا داع؟ متى يستهلك بلا قيمة؟ متى نمنعه؟",
    layer: "C",
    owners: ["Claude", "Perplexity", "GPT"],
    status: "todo",
    priority: 2,
    artifacts: [{ path: "failures/failure_library.json", kind: "json", description: "سجل الإخفاقات" }],
    depends_on: ["T09"],
  },

  // ───── D. Crypto Engine Preparation ─────
  {
    id: "T12",
    code: "CRYPTO_PLAYBOOK",
    title: "Crypto Intelligence Playbook",
    description: "playbook منظم: catalyst scan, narrative analysis, thesis review, invalidation map, watchlist output.",
    layer: "D",
    owners: ["Claude", "Perplexity", "Manus"],
    status: "todo",
    priority: 3,
    artifacts: [
      { path: "playbooks/crypto.intelligence.md", kind: "md", description: "الـ playbook الكبير" },
      { path: "playbooks/crypto.intelligence.entries.json", kind: "json", description: "إدخالات قابلة للتشغيل" },
    ],
    depends_on: [],
  },
  {
    id: "T13",
    code: "CRYPTO_ROUTING",
    title: "Crypto Routing Matrix",
    description: "أي مهمة كريبتو → أي مزود (news, thesis, transformation, review, reporting).",
    layer: "D",
    owners: ["Claude", "GPT"],
    status: "todo",
    priority: 1,
    artifacts: [{ path: "routing/crypto.matrix.json", kind: "json", description: "policy للكريبتو" }],
    depends_on: ["T05", "T12"],
  },
  {
    id: "T14",
    code: "CRYPTO_EVALS",
    title: "Crypto Evals Set",
    description: "false narrative, conflicting signals, hype vs evidence, invalid thesis, missing data, no-trade cases.",
    layer: "D",
    owners: ["Claude", "GPT"],
    status: "todo",
    priority: 1,
    artifacts: [{ path: "evals/crypto.cases.json", kind: "json", description: "حالات تقييم" }],
    depends_on: ["T12"],
  },

  // ───── E. Knowledge Base / RAG ─────
  {
    id: "T15",
    code: "CORPUS",
    title: "FATHIYA Internal Corpus",
    description:
      "corpus داخلي: status reports, bridge docs, playbooks, routing policies, evals, failure library, benchmarks, workflow docs.",
    layer: "E",
    owners: ["GPT", "Perplexity", "Claude"],
    status: "todo",
    priority: 3,
    artifacts: [
      { path: "corpus/index.json", kind: "json", description: "فهرس الـ corpus" },
      { path: "corpus/README.md", kind: "md", description: "دليل التنظيم والمصادر" },
    ],
    depends_on: ["T01", "T02", "T03", "T11"],
  },
  {
    id: "T16",
    code: "PROMPTS",
    title: "Distilled Prompt Packs",
    description: "router / reviewer / critic / synthesizer / report / fail-closed prompts — نهائية وتبقى بعد الاشتراكات.",
    layer: "E",
    owners: ["Claude", "GPT"],
    status: "todo",
    priority: 2,
    artifacts: [
      { path: "prompts/router.md", kind: "md", description: "router prompt" },
      { path: "prompts/reviewer.md", kind: "md", description: "reviewer prompt" },
      { path: "prompts/critic.md", kind: "md", description: "critic prompt" },
      { path: "prompts/synthesizer.md", kind: "md", description: "synthesizer prompt" },
      { path: "prompts/report.md", kind: "md", description: "report prompt" },
      { path: "prompts/fail_closed.md", kind: "md", description: "fail-closed prompt" },
    ],
    depends_on: ["T15"],
  },
];

// Helpers
export const OWNER_COLORS: Record<Owner, string> = {
  Claude: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  GPT: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  Perplexity: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  Manus: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  n8n: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  Zapier: "bg-orange-500/15 text-orange-300 border-orange-500/30",
};

export function tasksByLayer(layer: LayerId): Task[] {
  return TASKS.filter((t) => t.layer === layer);
}

export function progressFor(layer: LayerId): { done: number; total: number; pct: number } {
  const list = tasksByLayer(layer);
  const done = list.filter((t) => t.status === "done").length;
  const total = list.length;
  return { done, total, pct: total ? Math.round((done / total) * 100) : 0 };
}

export function overallProgress(): { done: number; total: number; pct: number } {
  const total = TASKS.length;
  const done = TASKS.filter((t) => t.status === "done").length;
  return { done, total, pct: total ? Math.round((done / total) * 100) : 0 };
}

export function priorityStars(p: Task["priority"]): string {
  return p > 0 ? "★".repeat(p) : "";
}
