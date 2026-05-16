# FATHIYA Repository Identity Map v0

## Purpose

Canonical reference for FATHIYA project repository identities. Prevents misattribution of repositories to wrong GitHub organizations.

## Repositories

| Role | GitHub Path | URL |
|---|---|---|
| Core repo | `fathya-core/fathiya-core` | https://github.com/fathya-core/fathiya-core |
| Ops Console repo | `fathya-project/fathiya-ops-console` | https://github.com/fathya-project/fathiya-ops-console |

## Corrections applied

| Incorrect reference | Correct reference | Where corrected |
|---|---|---|
| `fathya-core/fathiya-ops-console` | `fathya-project/fathiya-ops-console` | Target Card, Scope Map |

## Key facts

- The core repo lives under the `fathya-core` org: `fathya-core/fathiya-core`.
- The ops console repo lives under the `fathya-project` org: `fathya-project/fathiya-ops-console`.
- `fathya-project/fathiya-core` does not exist and must not be referenced.
- `fathya-core/fathiya-ops-console` does not exist and must not be referenced.
- The PR chain lives in `fathya-core/fathiya-core`.

## PR chain host

All PR chain branches (`cursor/scope-auth-and-pr-chain-v0`, etc.) live in the core repo `fathya-core/fathiya-core`.

## Created

- Date: 2026-05-16
- Trigger: Repository identity correction task
- Branch: `cursor/repo-identity-correction-v0`
- Base: `cursor/scope-auth-and-pr-chain-v0`
