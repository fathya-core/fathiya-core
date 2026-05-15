# FATHIYA CORE — Hub Queue Routing v0

## الهدف
تحديد كيف تتحول المخرجات من معرفة إلى مهام موجهة بدون تنفيذ عشوائي.

## Routing Principle
Input → Hub Classification → Policy Layer → Queue → Adapter → Receipt

## Queue Types

### 1. Knowledge Queue
For articles, notes, documents, and knowledge conversion.
Outputs:
- Knowledge Card
- Tool Card
- Skill Card
- Risk Card
- Relation update
Adapter:
- Local Vault
- Cursor validation when needed

### 2. Research Queue
For deeper research and synthesis.
Outputs:
- Research brief
- Comparison report
- Source map
Adapter:
- Manus AI
- Perplexity/Gemini as supporting sources when available

### 3. Engineering Queue
For repo validation and code/vault changes.
Outputs:
- Patch
- Validation report
- Pull request update
Adapter:
- Cursor Agent
- GitHub

### 4. Automation Queue
For intake and batch workflows.
Outputs:
- Workflow draft
- n8n blueprint
- Zapier action plan
Adapter:
- n8n
- Zapier MCP

### 5. Approval Queue
For external changes and execution-capable actions.
Outputs:
- Payload preview
- Approval record
- Execution receipt
Adapter:
- GitHub
- Webhooks
- n8n
- Email tools

## Routing Matrix
| Request Type | Queue | Adapter | Requires approval |
|---|---|---|---|
| New article or file | Knowledge Queue | Vault/Cursor | No |
| Deep research | Research Queue | Manus | No for draft |
| Repo change | Engineering Queue | Cursor/GitHub | Yes if write |
| External workflow | Automation Queue | n8n/Zapier | Yes before activation |
| Email/webhook/GitHub mutation | Approval Queue | Relevant adapter | Yes |
| Crypto analysis | Knowledge Queue | Vault/Manus | Yes only if external action |
| Bug bounty preparation | Knowledge Queue | Vault/Manus/Cursor | Yes for target-specific execution |

## Receipt Schema
Every routed task should create:
- id
- timestamp
- source_request
- queue
- adapter
- output_artifact
- status
- human_approval_required
- receipt_url_or_path

## Current status
Hub routing is installed as governance. Real automation remains draft-first.