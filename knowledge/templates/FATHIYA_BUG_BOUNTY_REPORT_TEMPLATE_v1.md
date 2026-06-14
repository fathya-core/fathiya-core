# FATHIYA Bug Bounty Report Template v1

## Title

`[Severity] Vulnerability class in affected asset/workflow`

## Scope Proof

- Program/platform:
- Policy URL or uploaded scope artifact:
- Target asset:
- Asset type:
- In-scope rule:
- Testing limits used:
- Receipt ID:

## Summary

Write a short, direct description of what is broken, where it is broken, and why it matters.

## Affected Asset

- URL, endpoint, mobile screen, API route, WebSocket channel, or workflow:
- Required role/account:
- Preconditions:

## Vulnerability Class

- Candidate class:
- OWASP / API Top 10 / WSTG mapping:
- Bugcrowd VRT or program severity mapping:

## Steps To Reproduce

1. Establish authorized account or lab state.
2. Perform the minimum non-destructive action needed to show the behavior.
3. Observe expected versus actual result.
4. Attach redacted evidence.

## Expected Result

Describe the access control, validation, encoding, rate/state, or business rule that should have applied.

## Actual Result

Describe only what was proven. Do not over-claim impact from scanner output.

## Evidence

- Screenshots:
- Redacted request/response snippets:
- Tool output summary:
- Manual validation result:
- False-positive checks:

## Impact

Explain practical business/security impact using demonstrated evidence:

- Data sensitivity:
- Affected users or roles:
- Scale:
- Write/read capability:
- Chain requirements:
- What was not tested:

## Severity Rationale

Use the program's policy first. If absent, use Bugcrowd VRT as a baseline and adjust by demonstrated impact.

## Remediation

Provide specific, context-aware remediation:

- Authorization checks:
- Output encoding or sanitization:
- SSRF egress allowlist or metadata protections:
- API/object-level checks:
- WebSocket per-message authorization:
- Logging and detection:

## Limitations And Safety

- No destructive testing performed:
- No third-party user data retained:
- No secrets or tokens included:
- Rate/noise limits followed:
- Pending validation:

## References

- OWASP WSTG:
- OWASP API Security Top 10:
- OWASP Cheat Sheet:
- Program policy:
- FATHIYA learning card IDs:
