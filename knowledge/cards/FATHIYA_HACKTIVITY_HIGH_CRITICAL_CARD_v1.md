---
schema: fathiya_knowledge_card_v1
topic: hackerone_high_critical_disclosed_bug_bounty_patterns
captured_at: 2026-06-15
detail_path: security/bug-bounty/hackerone/20260615-hacktivity-high-critical-lessons.md
patterns_path: security/bug-bounty/hackerone/20260615-hacktivity-high-critical-patterns.json
trust_boundary: public_disclosed_reports
---

# HackerOne High/Critical Bug Bounty Pattern Card

Use this card when FATHIYA is asked to hunt, triage, escalate, or draft reports
for authorized bug bounty work.

Primary lesson: strong reports prove source, sink, normal trigger, observable
result, and crossed security boundary. Do not stop at an unsafe pattern.

High-value hunt lanes:

- CI supply chain: pull_request_target, workflow_run, untrusted checkout,
  package lifecycle scripts, secrets, publish tokens, release paths.
- Command injection: bash -c, sh -c, cmd /c, exec, execSync, shell-enabled spawn,
  joined command strings, bundler/deploy/IaC options.
- SSRF: link previews, webhook validators, import-from-URL, screenshots,
  metadata fetchers, DNS resolution, redirects, internal/private IPs.
- Local browser/crawler tools: attacker-controlled page metadata to filename,
  path, local file write, project mutation, startup/config/plugin paths.
- OIDC/JWT auth bypass: missing signature, issuer, audience, nonce, expiry,
  algorithm, key binding, unsafe account linking.
- Blind SQLi: exact endpoint, parameter, role, side channel, and data impact.

Escalate only when evidence proves the larger boundary: privileged CI, secret or
release exposure, internal resource access, trusted local execution path,
account impersonation, or sensitive database access.

Detailed source:
security/bug-bounty/hackerone/20260615-hacktivity-high-critical-lessons.md
