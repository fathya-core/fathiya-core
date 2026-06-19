# FATHIYA Bugcrowd Bluehost Passive Plan v1

Status: ready_for_passive_first_operation
Date: 2026-06-14
Selected target: `https://www.bluehost.com/`
Program: Bugcrowd Web.com Bug Bounty

## Readiness State

The operator reports that Bugcrowd identity verification is complete. FATHIYA
has already stored and understood the Web.com Bugcrowd scope map and target
card. This plan advances the bug bounty agent from exact scope understanding to
target-specific passive preparation.

No external scan, exploitation attempt, automated crawling, report submission,
or target testing was performed while creating this plan.

## Target Selection

Bluehost was selected as the first target because it is explicitly in scope and
had a lower known issue count at capture time than Network Solutions.

- In scope: `https://www.bluehost.com/`
- Known issue count at capture: 15
- Out of scope: `*.bluehost.com`
- Required testing header for any future live test plan: `X-Request-Purpose: Research`
- Optional header: `X-Bugcrowd-Ninja: [username]`

If normal browsing redirects from `https://www.bluehost.com/` to any subdomain
or asset not explicitly listed in scope, FATHIYA must stop and classify that
path as out of scope unless the Bugcrowd program page explicitly authorizes it.

## Allowed Now

- Review the official Bugcrowd program policy and known issues.
- Keep a target-specific hypothesis list.
- Use `security_core_plan` for internal reasoning only.
- Prepare a manual, low-rate validation checklist for one vulnerability class at
  a time.
- Draft report structure only from operator-provided or safely collected
  evidence.
- Use Kali and HexStrike only for local loopback labs or offline replay, not for
  production Bugcrowd targets.

## Blocked Now

- Automated scanning of `https://www.bluehost.com/`.
- Wildcard or subdomain testing under `*.bluehost.com`.
- Testing `app.bluehost.com`, account-manager subdomains, or any linked
  hostname unless it appears as an explicitly authorized in-scope asset.
- DoS, DDoS, stress tests, rate-limit tests, brute force, credential attacks, or
  availability-impacting behavior.
- Customer-account interaction, real customer data access, or any attempt to
  modify third-party data.
- Source-code disclosure testing, secret harvesting from indexed sources, or
  excluded issue classes listed in the scope map.
- Final Bugcrowd report submission until the Submit report page is visible and
  enabled.

## First Hypotheses

1. Account and signup workflow authorization boundaries.
   - Requires only researcher-owned test identities.
   - Stop if the flow leaves the exact in-scope host.

2. Storefront and plan-selection business logic.
   - Focus on impact-bearing state changes, pricing transitions, eligibility,
     and authorization checks.
   - Do not complete paid purchases or consume non-reimbursed services.

3. Public API surface discovered through normal page use.
   - Treat endpoints as candidates only if they remain on the exact in-scope
     host.
   - Do not fuzz, enumerate, or brute force parameters.

4. Session lifecycle for sensitive actions.
   - Only evaluate non-destructive, operator-owned flows.
   - Ignore excluded low-impact categories unless combined with concrete,
     reportable impact.

5. Access-control and object reference checks.
   - Requires two researcher-owned test accounts before any live validation.
   - Stop immediately if any response contains data belonging to a real
     customer or unrelated user.

## Required Gate Before Live Manual Testing

Before any live request beyond normal browsing, FATHIYA must record:

- Exact URL path and hostname, proving it remains under `https://www.bluehost.com/`.
- One narrow test objective.
- Known issue review result for the chosen area.
- Header plan containing `X-Request-Purpose: Research`.
- Test-account state, with no real customer interaction.
- Expected safe stop conditions.
- Evidence capture format for screenshots, request IDs, timestamps, and ordered
  reproduction steps.

## Agent Tool Policy

- `security_core_plan`: allowed for reasoning and checklist generation.
- `web_fetch`: allowed for official policy pages and documentation only.
- `browser`: allowed for normal manual browsing and policy review.
- `kali_tool_inventory`: allowed for local readiness checks only.
- `hexstrike_lab_scan`: loopback lab targets only.
- External scanners, fuzzers, crawlers, exploit runners, and high-volume tools:
  blocked for this production target.

## Ready Signal

FATHIYA is ready to operate as a Bugcrowd bug bounty assistant for this target
in a passive-first, scope-bound mode. The next safe action is to open the
Bugcrowd known issues for `https://www.bluehost.com/`, choose one narrow manual
objective, and create a live-test gate record before touching the production
target.

