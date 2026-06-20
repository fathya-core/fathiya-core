---
schema: fathiya_security_knowledge_v1
source: hackerone_hacktivity_disclosed_high_critical
captured_at: 2026-06-15
trust_boundary: public_disclosed_reports
use_for: authorized_bug_bounty_learning_static_review_report_quality
---

# HackerOne High/Critical Disclosed Report Lessons

Source filter:
https://hackerone.com/hacktivity/overview?queryString=severity_rating%3A%28%22High%22+OR+%22Critical%22%29+AND+disclosed%3Atrue&sortField=latest_disclosable_activity_at&sortDirection=DESC&pageIndex=0

This note distills public disclosed HackerOne reports into safe hunting
heuristics for FATHIYA. It is a learning source, not an instruction to test
third-party systems outside authorized scope.

## Reports Studied

- https://hackerone.com/reports/3712279 - PortSwigger Burp Suite Professional:
  browser-powered crawl accepted attacker-controlled file input metadata and
  could write local files through traversal-like filename handling.
- https://hackerone.com/reports/3558713 - AWS CDK:
  command injection through unsafely joined bundling options executed by a
  shell during normal CDK workflows.
- https://hackerone.com/reports/3619288 - DuckDuckGo:
  privileged GitHub Actions workflow exposed supply-chain risk through
  pull_request_target and untrusted pull-request code paths.
- https://hackerone.com/reports/3619287 - DuckDuckGo:
  another pull_request_target supply-chain chain where proof quality mattered;
  static reasoning alone was not enough until clear evidence was supplied.
- https://hackerone.com/reports/3393664 - Rocket.Chat:
  link-preview SSRF after URL validation failed to re-check resolved DNS/IP
  targets before server-side fetch.
- https://hackerone.com/reports/3489490 - Nextcloud:
  authentication bypass in ID4me/OIDC handling through missing JWT signature
  verification.
- https://hackerone.com/reports/3653196 - Revive Adserver:
  blind SQL injection in a low-privileged path with precise parameter and file
  attribution.

## Rules FATHIYA Must Internalize

### 1. Prove source, sink, normal trigger, and impact

Strong reports identify attacker-controlled input, the exact security-sensitive
sink, the normal workflow that triggers it, and the boundary that gets crossed.
For review tasks, FATHIYA should connect:

input -> code path -> sink -> observable result -> program impact.

### 2. Severity comes from crossed boundaries

High or Critical reports usually proved one or more of these boundaries:

- untrusted web content influences local files or local app behavior;
- untrusted dependency, construct, config, or PR code reaches developer/CI
  command execution;
- CI token, secret, release, package, signing, or product distribution boundary
  is exposed;
- server-side fetch reaches internal network, metadata, admin, or private
  service space;
- identity/authentication control is bypassed through improperly verified
  tokens;
- database query control is reachable with realistic preconditions and data
  impact.

If the larger boundary is only hypothetical, keep severity honest and present
the chain as a risk note.

### 3. CI and supply-chain checklist

Search for:

- `pull_request_target`, `workflow_run`, `repository_dispatch`, and reusable
  workflows running in elevated context;
- checkout of fork or PR-head code in a privileged workflow;
- package-manager lifecycle hooks or local scripts after untrusted checkout;
- secrets, publish tokens, signing keys, or write-scoped GitHub tokens in the
  same trust zone;
- release, package, extension, app, browser, or auto-update paths that consume
  artifacts from the risky workflow.

Ready-to-submit evidence should show untrusted code execution in the privileged
context and explain downstream product impact. Use safe proof signals such as
controlled logs, benign marker files, or redacted callback evidence. Do not
exfiltrate real secrets.

### 4. Command injection checklist

Look for:

- command arguments joined into one shell string;
- `bash -c`, `sh -c`, `cmd /c`, `exec`, `execSync`, or shell-enabled spawn;
- bundler, compiler, docker, IaC, codegen, package, or deploy options controlled
  by a project, package, template, PR, or config file;
- normal workflows such as build, synth, deploy, diff, test, import, or codegen.

Ready-to-submit evidence should identify the controllable option, the sink, the
normal workflow trigger, and a benign observable command result. Recommended
fix: pass arguments as arrays to a process API without shell evaluation, or
strictly validate options at the boundary.

### 5. SSRF checklist

Review server-side fetchers in:

- link previews;
- webhook validators;
- import-from-URL features;
- screenshot/PDF generation;
- metadata enrichers;
- avatar, image, and oEmbed handlers.

Validation must happen after DNS resolution and after redirects. Review internal
IP ranges, loopback, IPv6, decimal/octal/mixed encodings, DNS rebinding, and
redirects to internal targets.

Ready-to-submit evidence should show server-side request evidence plus reflected
internal response or safe blind callback proof.

### 6. Browser, crawler, and local-agent tools are attack surfaces

When a product crawls, renders, imports, or automates attacker-controlled pages,
page attributes, filenames, MIME hints, URLs, redirects, and generated artifacts
are hostile local input.

High-value sinks include local file write, archive extraction path, protocol
handler launch, browser profile data, workspace/project mutation, OS startup,
config, plugin, extension, or generated code paths.

Ready-to-submit evidence should show the local effect in a user-writable path and
how normal product usage triggers it.

### 7. OIDC/JWT identity checklist

For OAuth/OIDC/ID4me/SAML-like flows, verify:

- JWT signature is always checked;
- issuer, audience, nonce, expiry, algorithm, and key binding are checked;
- key selection cannot be confused across issuers or tenants;
- account linking does not trust identity claims before verification.

Ready-to-submit evidence should prove account boundary crossing, not only token
parsing.

### 8. Blind SQL injection report quality

Include exact endpoint, parameter, file, required role, side channel, and data
impact. Use timing, boolean, error, or content-difference evidence. Avoid
claiming full database takeover unless the privileges are demonstrated.

## Proof Quality Rules

FATHIYA should consider a bug bounty report ready only when it has:

- exact source path and line-level sink attribution for code review;
- minimal safe reproduction in local lab or clearly authorized environment;
- observable result that does not leak real third-party secrets;
- screenshots or logs separating static reasoning from demonstrated execution;
- impact chain mapped to program scope and severity guidance;
- direct remediation guidance;
- clear assumptions and preconditions.

Triage lesson from the DuckDuckGo workflow reports: a strong static chain can be
pushed back when proof is abstract. Attach safe evidence that the path actually
executes.

## Escalation Logic

Move from P4/P3 toward P2/P1 only when evidence supports a larger boundary:

- unsafe pattern -> attacker-controlled input reaches sink;
- code execution -> privileged workflow token, secret, or release path;
- internal request -> internal service content or metadata class reachable;
- local file write -> file written where normal app/OS behavior later trusts or
  executes it;
- JWT bug -> account impersonation or auth bypass;
- blind injection -> sensitive read/write or admin-impacting database control.

## Next Hunt Queue

1. Open-source CI workflows with privileged triggers, untrusted checkout,
   secrets, and release paths.
2. SDKs, CLIs, build tools, and IaC libraries with shell command construction.
3. Crawlers, scanners, importers, and browser automation tools with filename,
   path, and local file handling.
4. Link preview and URL import features with DNS and redirect SSRF risk.
5. Auth connectors with token verification, key confusion, issuer/audience, and
   unsafe account linking risks.
6. Legacy PHP/admin/adserver code where low-privileged parameters reach database
   queries.

## Retrieval Terms

bug bounty, HackerOne, high severity, critical severity, disclosed report,
pull_request_target, workflow_run, GitHub Actions, supply chain, CI secrets,
untrusted checkout, command injection, shell injection, bash -c, cmd /c,
bundling options, SSRF, link preview, DNS resolution, redirects, OIDC, ID4me,
JWT signature verification, authentication bypass, blind SQL injection,
browser-powered crawler, local file write, path traversal, proof quality,
triage evidence, severity escalation.
