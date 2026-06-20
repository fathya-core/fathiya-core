---
schema: fathiya_retrieval_boost_card_v1
topic: hackerone_ci_supply_chain_pull_request_target
captured_at: 2026-06-15
detail_path: security/bug-bounty/hackerone/20260615-hacktivity-high-critical-lessons.md
---

# CI Supply Chain Pull Request Target Card

Use for bug bounty, HackerOne, CI, supply chain, pull_request_target,
workflow_run, GitHub Actions, secrets, CI secrets, publish token, write token,
release path, untrusted checkout, fork checkout, PR head checkout, package
lifecycle script, npm install, privileged workflow, build artifact, product
release, severity escalation, proof quality.

pull_request_target CI secrets bug bounty.
pull_request_target untrusted checkout CI secrets.
pull_request_target privileged workflow release path.
workflow_run CI secrets supply chain bug bounty.
GitHub Actions untrusted checkout package lifecycle.

Core rule: prove untrusted code execution inside a privileged workflow and show
the crossed boundary: secrets, tokens, release, package publishing, signing, or
product distribution. Use safe evidence and never exfiltrate real secrets.
