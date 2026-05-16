# FATHIYA Runtime Architecture After Full Study v0

## الحكم
بعد قراءة الحزمة، Runtime ليس مرحلة لاحقة؛ هو العمود الذي يمنع كل المعرفة من التحول إلى أرشيف ساكن.

## Architecture

```text
Input Sources
  ↓
Raw Archive
  ↓
Corpus Intake Playbook
  ↓
Classification
  ↓
Agent/Machine/Workflow Intelligence Layer
  ↓
Registries:
  - Agent Registry
  - Skill Registry
  - Workflow Registry
  - Machine Task Registry
  - Tool Contract Registry
  ↓
Runtime Queue
  ↓
Approval / Policy Gate
  ↓
Adapter Router
  ↓
Execution / Draft / Validation
  ↓
Receipt Ledger
  ↓
Awareness State Update
```

## Required registries

### Agent Registry
Who can act.

### Skill Registry
What capability is being invoked.

### Workflow Registry
Which repeated chain applies.

### Machine Task Registry
What machine-executable unit is needed.

### Tool Contract Registry
What each adapter can and cannot do.

### Runtime Queue
What is waiting, running, blocked, or complete.

### Receipt Ledger
What happened and where the proof lives.

## لماذا هذا مهم
بدون Runtime، كل المعرفة تصبح أرشيف.
مع Runtime، كل معرفة يمكن أن تتحول إلى:
- decision
- card
- workflow
- machine task
- adapter call
- receipt

## Next files
- `knowledge/registries/agent_registry_v0.json`
- `knowledge/registries/skill_registry_v0.json`
- `knowledge/registries/workflow_registry_v0.json`
- `knowledge/registries/machine_task_registry_v0.json`
- `knowledge/registries/tool_contract_registry_v0.json`
- `knowledge/runtime/runtime_queue_v0.json`
- `knowledge/runtime/receipt_ledger_v0.json`

## Next playbook
PLAYBOOK 003 — Runtime Queue & Receipt Ledger