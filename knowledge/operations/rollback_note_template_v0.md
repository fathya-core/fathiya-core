# Rollback Note — [Operation ID]

## Operation Summary

| Field | Value |
|---|---|
| **Operation ID** | `[entry_id from operations queue]` |
| **Tool Contract** | `[tool_contract_id]` |
| **Approval Class** | `[approval_class]` |
| **Execution Timestamp** | `[timestamp or "not_executed"]` |
| **Target** | `[target_reference]` |
| **Status Before Rollback** | `[executed / failed / partial]` |

## What Was Done

Describe the operation that was executed (or attempted):

- [Action 1]
- [Action 2]

## What Needs to Be Reversed

Describe the specific state changes that must be undone:

| State Change | Reversal Action | Verified |
|---|---|---|
| [e.g., Branch `feature-x` created] | [Delete branch `feature-x`] | [ ] |
| [e.g., Webhook payload sent to endpoint X] | [No reversal possible — log as irreversible] | [N/A] |
| [e.g., Zap `intake-pipeline` enabled] | [Disable Zap `intake-pipeline`] | [ ] |

## Rollback Steps

1. [Step 1 — specific command, API call, or manual action]
2. [Step 2]
3. [Verify rollback completed — describe verification method]

## Irreversible Side Effects

List any side effects that cannot be reversed (e.g., sent emails, consumed API quotas, published data):

- [Side effect 1 — mitigation if any]
- [Side effect 2]

## Post-Rollback Verification

- [ ] Target system is in expected pre-operation state
- [ ] Receipt ledger entry updated with rollback status
- [ ] Operations queue entry updated to `rolled_back`
- [ ] No orphaned resources remain

## Notes

[Additional context, lessons learned, or follow-up actions]

---

*Template version: rollback_note_template_v0 — Added by ADR-003 FATHIYA Operations Autopilot Mode*
