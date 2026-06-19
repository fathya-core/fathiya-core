# FATHIYA Awareness/Security Corpus Ingest Report v1

## Verdict

The uploaded `AWARENESS_KNOWLEDGE_ROADMAP-and-securty.zip` is now a primary imported operator corpus for FATHIYA. Markdown sources were copied into `knowledge/raw/imports/...` using stable ASCII filenames, while every original filename is preserved in the manifest. Spreadsheet and PDF files were converted into searchable Markdown summaries. Raw extracted copies remain in the local runtime import directory.

This corpus contains execution-capable security material. It is for learning,
lab planning, owned-scope preparation, detection engineering, and agent/tool
design. Project-specific allowed and disallowed boundaries are operator-owned
and pending definition in
`knowledge/policies/FATHIYA_OPERATOR_BOUNDARY_PROFILE_PENDING_v1.json`.
Until the operator fills that profile, sensitive or state-changing actions are
recorded as `boundary_pending` instead of being treated as permanently decided
by this report.

## Inventory

- Source files: 152
- `.md`: 141
- `.xlsx`: 10
- `.pdf`: 1

## Dominant Categories

- `infrastructure_cloud_linux`: 129
- `career_roadmap_tools`: 122
- `security_lab_pentest`: 106
- `detection_threat_intel`: 94
- `osint_attack_surface`: 83
- `agentic_ai_security`: 65
- `general_awareness`: 4

## FATHIYA Planes Affected

- Knowledge / RAG Plane: 152
- Understanding / Evaluation Plane: 144
- Security Lab Plane: 138
- Tool / Automation Plane: 65

## Sensitivity

- `execution_capable`: 119
- `review_before_use`: 19
- `reference`: 14

## Content Redactions

- Secret-like imported text values redacted from searchable copies: 1
- Original file names and source SHA-256 hashes remain preserved in the manifest.

## Largest / Highest-Weight Sources

- `aks-113-30fa4921dc` - Thunderbit 541103 20260511 113916 (`.xlsx`, 3316442 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/converted/aks-113-30fa4921dc-thunderbit-541103-20260511-113916.md`
- `aks-119-f0fa6abee3` - Thunderbit Articles (`.xlsx`, 2126100 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/converted/aks-119-f0fa6abee3-thunderbit-articles.md`
- `aks-120-f1009e7f43` - Thunderbit Articles Clean (`.xlsx`, 263429 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/converted/aks-120-f1009e7f43-thunderbit-articles-clean.md`
- `aks-046-b8c1fcfcd4` - Gmail   Chain models for complex tasks (`.pdf`, 170634 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/converted/aks-046-b8c1fcfcd4-gmail-chain-models-for-complex-tasks.md`
- `aks-040-5040e233c8` - Detecting Malicious Insider Activity: A Technical Detection Engineering Guide (`.md`, 119813 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/aks-040-5040e233c8-detecting-malicious-insider-activity-a-technical-detection-engineering-g.md`
- `aks-045-ba6dff6b94` - From Threat Intelligence to Detection: A Practitioner’s Guide (`.md`, 109216 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/aks-045-ba6dff6b94-from-threat-intelligence-to-detection-a-practitioners-guide.md`
- `aks-028-ff3113518a` - Attack Playbook — Operation DragonRx (`.md`, 67925 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/aks-028-ff3113518a-attack-playbook-operation-dragonrx.md`
- `aks-024-fa11650a15` - AI Offensive Security: Practical Attacks Against LLM Agents (`.md`, 55265 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/aks-024-fa11650a15-ai-offensive-security-practical-attacks-against-llm-agents.md`
- `aks-118-03695a9ec8` - Thunderbit 541103 20260512 214709 (`.xlsx`, 54810 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/converted/aks-118-03695a9ec8-thunderbit-541103-20260512-214709.md`
- `aks-017-65161270f6` - Active Directory Penetration Testing (`.md`, 48898 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/aks-017-65161270f6-active-directory-penetration-testing.md`
- `aks-023-ebb20c0481` - AI Agents: Complete Course (`.md`, 47143 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/aks-023-ebb20c0481-ai-agents-complete-course.md`
- `aks-115-a1a4856c57` - Thunderbit 541103 20260512 160121 (`.xlsx`, 46285 bytes) -> `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/converted/aks-115-a1a4856c57-thunderbit-541103-20260512-160121.md`

## Operating Interpretation

- AI-agent, MCP, Cursor, Gemini, HexStrike, prompt-injection, and autonomous-security material routes through PLAYBOOK_002 and PLAYBOOK_004 before it becomes a tool, workflow, or agent capability.
- Pentest, recon, OSINT, AD, cloud, Kubernetes, Burp, Nmap, IDOR, upload, and bug-bounty material routes through PLAYBOOK_005 and remains boundary-aware planning unless the operator boundary profile defines scope and authority.
- Detection engineering, threat intelligence, SOC, endpoint, and incident material can be used immediately for defensive lab plans, detections, report templates, and knowledge cards.
- Career, roadmap, tool-stack, and learning material feeds the Knowledge/RAG and Understanding/Evaluation planes.
- Execution-capable snippets are not execution permission. They become lab notes, checklists, local-only examples, or boundary-pending items depending on the operator-defined scope.

## Generated Artifacts

- Manifest: `knowledge/intake/runtime/awareness_knowledge_roadmap_security_2026_05_15_manifest.json`
- Registry: `knowledge/registries/imported_corpus_registry_v1.json`
- Raw Markdown import root: `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15`
- Converted spreadsheet/PDF summaries: `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15/converted`

## Comprehension Check Prompt

```text
استرجع corpus awareness_knowledge_roadmap_security_2026_05_15 واصنع خريطة فهم: AI agents، security lab، OSINT/recon، detection engineering، tool contracts، وما هو مسموح الآن وما ينتظر تعريف حدود المشغل قبل التنفيذ. سجل إيصالًا.
```
