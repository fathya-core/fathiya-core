# FATHIYA HexStrike-AI Juice Shop Local Scan Report v1

**Timestamp:** 2026-06-14T13:26:43Z
**Runtime task:** `90c182c6-0d0a-42d5-b792-08539a714190`
**Runtime receipt:** `AR-20260614132643119037-90c182c6`
**Mode:** Local authorized lab only

## Executive Result

FATHIYA successfully used the local HexStrike-AI server inside Kali WSL against a local OWASP Juice Shop lab target at `http://127.0.0.1:3000`.

The agent retrieved the imported HexStrike/security knowledge corpus first, selected the registered runtime tool `hexstrike_lab_scan`, executed a light loopback-only scan, evaluated the result, and issued a runtime receipt.

## Local Lab Setup

- Target application: OWASP Juice Shop v20.0.0
- Target URL from Kali/HexStrike perspective: `http://127.0.0.1:3000`
- Lab path in Kali: `/tmp/fathiya-labs/juice-shop-v20`
- HexStrike server: `http://127.0.0.1:8888`
- HexStrike version reported by health endpoint: `6.0.0`
- HexStrike available tools: `80/127`
- Essential HexStrike tools: available

## Runtime Integration Added

The runtime now exposes a registered tool:

- `hexstrike_lab_scan`

This tool is intentionally restricted to loopback targets only. It rejects non-local targets before sending a request to HexStrike. The default scan path collects:

- HexStrike health
- HexStrike target analysis
- HexStrike tool selection
- Limited nmap scan against a single local port

The planner now selects this tool when the operator asks for HexStrike, bug bounty, Juice Shop, or local penetration-testing lab checks.

## Scan Evidence

HexStrike target analysis:

- Target type: `web_application`
- Risk level: `high`
- Attack surface score: `7.5`
- Confidence score: `0.7`
- IP address: `127.0.0.1`

HexStrike selected tools for quick objective:

- `nuclei`
- `wpscan`
- `dalfox`

Limited nmap result through HexStrike:

```text
PORT     STATE SERVICE
3000/tcp open  ppp
```

HTTP probe result:

- HTTP status: `200 OK`
- Header highlights: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-Recruiting: /#/jobs`
- Content type: `text/html; charset=UTF-8`

Nuclei local info/low check:

- Templates were installed under `/home/kali/.local/nuclei-templates`.
- The broad low-rate `tech,exposure` run reached HexStrike's 300 second tool timeout.
- Partial result was still captured:

```text
[swagger-api] [http] [info] http://127.0.0.1:3000/api-docs/swagger.json [paths="/api-docs/swagger.json"]
```

## Knowledge Used

Runtime retrieval selected five imported sources from the awareness/security corpus, including:

- `aks-021-b6ce1a01ab-ai-driven-web-application-pentesting-with-hexstrike-ai.md`
- `aks-020-82d02e1e14-ai-driven-pentesting-at-home-using-hexstrike-ai-for-full-network-discove.md`
- `aks-053-9d248602d8-hexstrike-cursor-for-osint-from-one-email-to-a-full-exposure-map.md`

This confirms the agent used the imported HexStrike material as context, then executed the registered local tool instead of only summarizing the articles.

## Boundaries

- External target scanning executed: no
- Third-party target activity executed: no
- Destructive action executed: no
- Brute force/exploitation modules executed: no
- Local lab scan executed: yes
- Target restriction: loopback only

## Sources

- Official HexStrike-AI repository: https://github.com/0x4m4/hexstrike-ai
- Kali HexStrike-AI package page: https://www.kali.org/tools/hexstrike-ai/
- OWASP Juice Shop project page: https://owasp.org/www-project-juice-shop/
- OWASP Juice Shop running guide: https://pwning.owasp-juice.shop/companion-guide/latest/part1/running.html

## Next Step

Keep `hexstrike_lab_scan` as the safe default for local training labs. For deeper bug bounty work, add explicit target scope records and a separate approval-gated tool profile before enabling non-loopback scanning.
