export type FathiyaCapabilityCategory =
  | "models"
  | "automation"
  | "security"
  | "engineering"
  | "browser"
  | "knowledge"
  | "domain";

export type FathiyaCapability = {
  id: string;
  runtimeIds: string[];
  name: string;
  category: FathiyaCapabilityCategory;
  role: string;
  runtimeUse: string;
  proof: string;
  primaryLane: "trading" | "bug-bounty" | "knowledge" | "integrations";
  accountRequired: boolean;
};

export type FathiyaQualityGate = {
  id: string;
  label: string;
  promptRule: string;
};

export const FATHIYA_ALLOWED_CAPABILITIES: FathiyaCapability[] = [
  {
    id: "openrouter",
    runtimeIds: ["openrouter"],
    name: "OpenRouter",
    category: "models",
    role: "توجيه النماذج والبحث العميق والتحكيم",
    runtimeUse: "استراتيجية، تقييم، Fusion للبحث العميق فقط",
    proof: "مفتاح خادم محلي + health يثبت openrouter_configured",
    primaryLane: "knowledge",
    accountRequired: true,
  },
  {
    id: "hugging-face",
    runtimeIds: ["huggingface_local"],
    name: "Hugging Face",
    category: "models",
    role: "استرجاع محلي، نماذج خفيفة، تقييم وفهم",
    runtimeUse: "local_planning + embeddings/retrieval",
    proof: "health يعرض local_model ومسار planning_route",
    primaryLane: "knowledge",
    accountRequired: false,
  },
  {
    id: "ollama",
    runtimeIds: ["ollama", "local_model"],
    name: "Ollama",
    category: "models",
    role: "استدلال محلي خاص وخفيف",
    runtimeUse: "fallback محلي للمهام الخاصة",
    proof: "فحص endpoint محلي قبل الاستخدام",
    primaryLane: "knowledge",
    accountRequired: false,
  },
  {
    id: "zapier-mcp",
    runtimeIds: ["zapier_mcp"],
    name: "Zapier MCP",
    category: "automation",
    role: "جسر التطبيقات، البريد، المستندات، GitHub، والقراءات الآمنة",
    runtimeUse: "inventory ثم read proof ثم write approval",
    proof: "diagnostics + action inventory + إيصال مهمة",
    primaryLane: "integrations",
    accountRequired: true,
  },
  {
    id: "n8n",
    runtimeIds: ["n8n", "n8n_local"],
    name: "n8n",
    category: "automation",
    role: "تدفقات deterministic وwebhooks وإيصالات",
    runtimeUse: "workflow execution + receipts",
    proof: "API health أو webhook receipt",
    primaryLane: "integrations",
    accountRequired: true,
  },
  {
    id: "kali",
    runtimeIds: ["kali_wsl"],
    name: "Kali Linux",
    category: "security",
    role: "تحقق أمني مصرح داخل نطاق واضح",
    runtimeUse: "أدوات فحص/تحقق bounded لا live abuse",
    proof: "أمر/إخراج محفوظ + نطاق مصرح",
    primaryLane: "bug-bounty",
    accountRequired: false,
  },
  {
    id: "hexstrike",
    runtimeIds: ["hexstrike"],
    name: "HexStrike",
    category: "security",
    role: "تجميع أدوات أمنية ومساعدة تحقق",
    runtimeUse: "اقتراح مسارات فحص وإثبات ضمن النطاق",
    proof: "tool output + false positive review",
    primaryLane: "bug-bounty",
    accountRequired: false,
  },
  {
    id: "codex-security",
    runtimeIds: ["codex_security"],
    name: "Codex Security",
    category: "security",
    role: "تحليل ثابت، تهديدات، triage، validation",
    runtimeUse: "review gate قبل أي تقرير",
    proof: "finding rationale + counter evidence + next step",
    primaryLane: "bug-bounty",
    accountRequired: false,
  },
  {
    id: "github-codespaces",
    runtimeIds: ["github_codespaces"],
    name: "GitHub Codespaces",
    category: "engineering",
    role: "بيئة بناء واختبار بعيدة",
    runtimeUse: "build/test/review في VM",
    proof: "build logs أو PR/check run",
    primaryLane: "integrations",
    accountRequired: true,
  },
  {
    id: "github",
    runtimeIds: ["github_cli", "github"],
    name: "GitHub",
    category: "engineering",
    role: "مصدر الكود والديدوب وissues/PRs",
    runtimeUse: "repo review + dedupe + diff",
    proof: "روابط issues/commits/PRs أو checkout محلي",
    primaryLane: "bug-bounty",
    accountRequired: true,
  },
  {
    id: "chrome",
    runtimeIds: ["chrome"],
    name: "Chrome",
    category: "browser",
    role: "جلسات المستخدم والمواقع التي تحتاج دخول",
    runtimeUse: "مشاهدة/لقطات/قراءة حالة بعد إذن إجراء",
    proof: "screenshot أو DOM observation",
    primaryLane: "knowledge",
    accountRequired: false,
  },
  {
    id: "computer-use",
    runtimeIds: ["computer_use"],
    name: "Computer Use",
    category: "browser",
    role: "تحكم سطح المكتب عند الحاجة",
    runtimeUse: "فتح تطبيقات، مراقبة، لقطات",
    proof: "screenshot أو app state",
    primaryLane: "integrations",
    accountRequired: false,
  },
  {
    id: "vs-code",
    runtimeIds: ["vs_code"],
    name: "VS Code",
    category: "engineering",
    role: "مراجعة الكود محليًا وتشغيل agent/editor tasks",
    runtimeUse: "workspace review + tests",
    proof: "git diff + build result",
    primaryLane: "integrations",
    accountRequired: false,
  },
  {
    id: "genspark-claw",
    runtimeIds: ["genspark_claw"],
    name: "Genspark Claw",
    category: "engineering",
    role: "عامل سحابي مساعد للبحث أو مسودة patch",
    runtimeUse: "delegate brief ثم مراجعة محلية",
    proof: "diff/checklist مستورد ومراجع",
    primaryLane: "integrations",
    accountRequired: true,
  },
  {
    id: "bolt",
    runtimeIds: ["bolt"],
    name: "Bolt",
    category: "engineering",
    role: "تصميم وبناء UI بعد brief محدد",
    runtimeUse: "UI proposal ثم local review",
    proof: "screenshot + build + diff",
    primaryLane: "integrations",
    accountRequired: true,
  },
  {
    id: "cherry-studio",
    runtimeIds: ["cherry_studio"],
    name: "Cherry Studio",
    category: "knowledge",
    role: "محطة نماذج ومعرفة محلية",
    runtimeUse: "knowledge import + retrieval evaluation",
    proof: "knowledge card + mastery receipt",
    primaryLane: "knowledge",
    accountRequired: false,
  },
  {
    id: "godaddy",
    runtimeIds: ["godaddy"],
    name: "GoDaddy API",
    category: "domain",
    role: "DNS وربط الدومين",
    runtimeUse: "domain health + records verification",
    proof: "DNS lookup + production route check",
    primaryLane: "integrations",
    accountRequired: true,
  },
];

export const BUG_BOUNTY_QUALITY_GATES: FathiyaQualityGate[] = [
  {
    id: "authorized-scope",
    label: "نطاق مصرح",
    promptRule: "لا تبدأ فحصًا حيًا بلا نطاق مصرح واضح من برنامج Bug Bounty أو مالك الهدف.",
  },
  {
    id: "dedupe-first",
    label: "ديدوب قبل التقرير",
    promptRule:
      "ابحث في التقارير المنشورة، GitHub issues/PRs/discussions، changelog، CVEs، أسماء الدوال، وroot-cause terms قبل صياغة تقرير.",
  },
  {
    id: "practical-impact",
    label: "أثر عملي",
    promptRule:
      "كل تقرير يجب أن يجيب بوضوح: as an attacker I could، مع أثر على مستخدم أو نظام أو بيانات أو صلاحيات.",
  },
  {
    id: "reproducible-proof",
    label: "إثبات قابل للإعادة",
    promptRule:
      "اجمع request/response أو screenshot أو local PoC أو test case يثبت السلوك، ولا تكتف بادعاء نصي.",
  },
  {
    id: "severity-calibration",
    label: "تصعيد مبني على دليل",
    promptRule:
      "لا ترفع P2/P1 إلا إذا أثبتت primitive جديدًا أو impact chain واقعيًا يتجاوز best practice أو theoretical issue.",
  },
  {
    id: "counter-evidence",
    label: "اعتراضات البرنامج",
    promptRule:
      "راجع أسباب الرفض السابقة، وابحث عن counter evidence قبل إعادة فتح نفس الفكرة أو رفعها بصياغة جديدة.",
  },
];

export function capabilityNames(capabilities = FATHIYA_ALLOWED_CAPABILITIES) {
  return capabilities.map((capability) => capability.name).join(", ");
}

export function capabilitiesForLane(lane: FathiyaCapability["primaryLane"]) {
  return FATHIYA_ALLOWED_CAPABILITIES.filter((capability) => capability.primaryLane === lane);
}

export function bugBountyGatePrompt() {
  return BUG_BOUNTY_QUALITY_GATES.map((gate) => `${gate.label}: ${gate.promptRule}`).join("\n");
}
