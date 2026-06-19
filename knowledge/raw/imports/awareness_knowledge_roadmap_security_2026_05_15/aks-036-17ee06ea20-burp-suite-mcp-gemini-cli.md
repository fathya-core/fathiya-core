# Burp Suite MCP + Gemini CLI

**Published:** 2026-01-02


## Connect Burp Suite to Gemini CLI using Model Context Protocol (MCP) and Turn Burp into an AI-callable toolset and accelerate recon, analysis, and reporting in authorized tests.


![Image](https://miro.medium.com/v2/resize:fit:700/1*BDe41fzpmr9R53fn5CbjcQ.png)

This guide walks you through connecting **Burp Suite** to **Gemini CLI** using PortSwigger’s official **MCP Server** extension. Once wired, Gemini can invoke Burp as a set of **callable tools** (via MCP) to review proxy history, push requests into Intruder, and accelerate **recon, analysis, and reporting** during a web assessment.  
**Authorization & privacy note:** Use this only on systems you’re explicitly permitted to test. If you connect Burp to an external AI service, you are responsible for understanding what data may be transmitted and how it is handled under that provider’s policies.

## 1) What you’re building (high-level)

PortSwigger’s **MCP Server** extension adds an MCP endpoint to Burp so an AI client can interact with Burp through a standard tool interface. The extension supports:

*   an **SSE MCP server** hosted by Burp (default `127.0.0.1:9876`)
*   a packaged **stdio proxy** for clients that only support stdio MCP servers

Gemini CLI supports multiple MCP transports, including **SSE** and **stdio**, configured via `mcpServers` in `settings.json`. [Gemini CLI+1](https://geminicli.com/docs/tools/mcp-server/)

## 2) Prerequisites

*   **Burp Suite** (Community or Professional)
*   The **MCP Server** extension installed in Burp (via BApp Store, or from source)
*   **Gemini CLI** installed and authenticated (Google account or API key) [Google Cloud Documentation](https://docs.cloud.google.com/gemini/docs/codeassist/gemini-cli)

sudo apt install gemini-cli

![Image](https://miro.medium.com/v2/resize:fit:700/1*_J5i599Xo9-GiSA1tj6ZmA.png)

## 3) Install the Burp MCP Server extension

### Option A (recommended): Install from Burp BApp Store

1.  Open Burp Suite
2.  Go to **Extensions** (or **Extender**) → **BApp Store**
3.  Search for **“MCP Server”** and install it

![Image](https://miro.medium.com/v2/resize:fit:700/1*_l8sqAtpBw5lXgBGYfXdCw.png)

### Option B: Build from source (offline / repeatable)

PortSwigger provides build instructions; the extension can be built into `burp-mcp-all.jar` and loaded as a Java extension in Burp. [GitHub](https://github.com/PortSwigger/mcp-server)

## 4) Configure MCP inside Burp Suite

After installing, you should see an **MCP** tab in Burp.

Key settings (from the official README):

*   **Enabled**: turns the MCP server on/off
*   **Enable tools that can edit your config**: exposes tools that can modify Burp config (recommended OFF initially)
*   **Host/port**: default listener is `http://127.0.0.1:9876` [GitHub](https://github.com/PortSwigger/mcp-server)

**Important**: Keep the server bound to `127.0.0.1` unless you _fully_ understand the exposure risks.

![Image](https://miro.medium.com/v2/resize:fit:700/1*-FkdlCZ_mS4UA13uTAzP6w.png)

## 5) Configure Gemini CLI to connect to Burp MCP

### 5.1 Find Gemini CLI settings file

Gemini CLI uses a `settings.json` file. Common locations:

*   Global: `~/.gemini/settings.json`
*   Project-specific: `.gemini/settings.json` (in your project root)

If it doesn’t exist yet, create it:

mkdir -p ~/.gemini  
nano ~/.gemini/settings.json

### 5.2 Add the Burp MCP server to `mcpServers`

Gemini CLI can connect to an MCP server over **SSE** using the `url` field.

Add this block (merge with any existing JSON):

{  
  "mcpServers": {  
    "burp": {  
      "url": "http://127.0.0.1:9876/sse",  
      "timeout": 30000,  
      "trust": false  
    }  
  }  
}

**URL detail**: PortSwigger notes that — depending on client and Burp extension configuration — the SSE endpoint may be either:

*   `[http://127.0.0.1:9876](http://127.0.0.1:9876)`
*   `http://127.0.0.1:9876/sse`

If the first URL doesn’t work in Gemini CLI, switch to the other.

**About** `**trust**`: `trust: false` keeps Gemini CLI in “confirm before tool execution” mode (recommended for security). Gemini CLI explicitly documents `trust` as bypassing confirmations.

## 6) Validate the connection

1.  Start **Burp Suite** and ensure the MCP extension is **Enabled**
2.  Start **Gemini CLI**
3.  In Gemini CLI, run the MCP listing command (interactive command support includes `/mcp`). [Google Cloud Documentation](https://docs.cloud.google.com/gemini/docs/codeassist/gemini-cli)

You should see the **burp** server and its available tools/resources.

![Image](https://miro.medium.com/v2/resize:fit:700/1*9yIPrzwpYCVJBNsckhHs8g.png)

## 7) Practical starter prompts

@burp Target:The official OWASP vulnerable machine running on my VM:  http://172.16.59.133/peruggia/. Do full scan and try to exploit all found vulnerabilities. Output: Full PT report with  
  proofs

Below is a structured analysis of the pentest session logs (Gemini CLI orchestration + Burp MCP + shell tooling), including the flow, tool/MCP usage, key findings, and a “report-style” output. I am **not** reproducing exploit payloads/step-by-step commands; instead I’m documenting what the logs demonstrate and the evidence artifacts.

## 8) Engagement overview of PT

*   **Target:** Peruggia web app at `[http://172.16.59.133/peruggia/](http://172.16.59.133/peruggia/)`
*   session-2026–01–02T08–15-a125f2…
*   **Primary objective stated in-session:** scan for vulnerabilities and attempt exploitation; produce a PT report
*   **Outcome:** Multiple high/critical issues were identified (and at least one RCE condition was demonstrated), but the session did **not** achieve a stable interactive shell; data extraction via SQLi was partial/slow and unstable
*   session-2026–01–02T08–15-a125f2…

### Toolchain used and how it was orchestrated

### Burp Suite via MCP

Observed MCP calls:

*   `get_proxy_http_history` (initially errored due to missing required `offset`; then returned end-of-history)
*   session-2026–01–02T06–32-a125f2…
*   `send_to_intruder` used to push an HTTP request into Burp Intruder for further testing

Operational note:

*   There was at least one MCP connectivity failure reported: “could not connect to any server”
*   session-2026–01–02T06–32-a125f2…

### Shell tools (run via orchestration)

Confirmed from logs:

*   **nmap** service discovery and follow-up port checks
*   session-2026–01–02T06–32-a125f2…
*   session-2026–01–02T06–32-a125f2…
*   **nmap smb-vuln\*** scripts against 139/445
*   session-2026–01–02T06–32-a125f2…
*   **sqlmap** for SQL injection verification/exploitation and attempted file read
*   **directory brute forcing** was attempted (wordlist issue observed; enumeration ran afterwards)

### Workspace/file-write constraint (impacted reporting/automation)

The run attempted to write files, but tooling enforced a workspace restriction: “File path must be within … /usr/lib/gemini-cli”

3) Reconnaissance results (network and service exposure)

**nmap -sV** identified the following open services on the target host:

*   22/ssh (OpenSSH), 80/http (Apache 2.2.14 + PHP 5.3.2), 139/445 (Samba), 143 (IMAP), 443 (unknown SSL/HTTPS), 5001 (Java Object Serialization), 8080 (Tomcat/Coyote), 8081 (Jetty)
*   Port 5001 returned a Java serialization magic header (`\xac\xed\0\x05`), consistent with **Java deserialization attack surface**
*   Port 443 remained unidentified by version scan in the session
*   SMB-focused scripting:
*   `smb-vuln-ms10-054: false`, `smb-vuln-ms10-061` negotiation error; `regsvc-dos` flagged “VULNERABLE” (note: this script’s relevance/accuracy depends on target OS/service behavior; treat as a signal to validate manually, not a final verdict)

## 9) Application-layer findings (confirmed)

### Finding 1 — Remote Code Execution via insecure upload handling (Critical)

**What the logs show**

*   The session produced a “Penetration Test Report” draft stating that upload functionality allowed uploading a `.htaccess` into `/images/` and then executing a “PHP web shell” uploaded into that directory
*   The application UI response confirms the upload outcome and shows `.htaccess` in `/images/` plus other uploaded artifacts listed in the gallery

**Impact**

*   This is effectively **server-side code execution** in the web server context (often leads to full host compromise depending on permissions, lateral movement options, and exposed secrets).

**Why exploitation did not become “stable” in this run**

*   The session narrative explicitly states repeated reverse-shell attempts failed, despite command execution being possible

**Recommendations**

*   Store uploads **outside** the web root; serve them via a controlled handler.
*   Enforce strict allowlist validation by MIME and magic bytes; block/strip risky extensions and double extensions.
*   Disable `.htaccess` overrides where possible (`AllowOverride None`) and prevent upload of server-interpreted config files.
*   Run the web tier with least privilege; ensure filesystem permissions prevent web user from writing to executable paths.

### Finding 2 — Time-based blind SQL injection in `pic_id` (High)

**What the logs show**

*   sqlmap resumed a stored session identifying `pic_id` as **time-based blind SQL injection** on `index.php?action=comment` and fingerprinted **MySQL >= 5.0.12 on Linux**, plus web stack details (Apache/PHP)
*   The session attempted DB enumeration; extraction was unstable/slow, but the logs indicate partial retrieval activity and warnings typical of time-based channels

**Impact**

*   Time-based blind SQLi can usually be weaponized for:
*   data extraction (slow but feasible),
*   auth bypass depending on queries,
*   reading files / writing files in some configurations (highly environment-dependent),
*   potential RCE via DB features if misconfigured.

**Recommendations**

*   Use parameterized queries (prepared statements) everywhere.
*   Apply strict input validation for numeric parameters (type enforcement).
*   Add centralized query logging/alerting for time-delay patterns.
*   Consider a WAF rule-set for SQLi (defense-in-depth), but treat it as secondary to code fixes.

### Finding 3 — Excessive exposed services / attack surface (Medium–High, compounding risk)

**What the logs show**

*   The host exposes multiple high-risk legacy services and middleware (Samba, IMAP, Tomcat, Jetty) in addition to the web app, and a Java deserialization endpoint on 5001

**Impact**

*   Even if the web app were fixed, exposed services expand lateral movement and alternate entry points.

**Recommendations**

*   Close or firewall nonessential ports; restrict admin/middleware to management subnets.
*   Patch/upgrade legacy components (notably Ubuntu 10.04-era stack indicated in the session report draft)
*   For SMB: disable SMBv1, enforce signing where possible, restrict to known clients.

## 10) Workflow timeline summary (condensed)

1.  **MCP initiated** and Burp MCP used; proxy history retrieval initially failed due to missing offset, then proceeded
2.  **Traffic sent to Intruder** for parameter manipulation/testing
3.  **nmap service discovery** identified broad attack surface including Java serialization, Tomcat, Jetty, Samba
4.  **Port 443 follow-up** remained unidentified by nmap version detection
5.  **SQLi confirmed** via sqlmap on `pic_id` (time-based blind); attempts to enumerate/extract were slow/unstable
6.  **RCE condition demonstrated** through upload behavior (.htaccess in images + server-side execution claim in report draft; upload result visible in UI)
7.  **Exploitation attempts** did not result in a stable shell; reporting was initiated

## 11) “Full report” output (ready-to-paste)

### Executive Summary

Testing of the Peruggia application at `172.16.59.133/peruggia/` identified (1) a critical remote code execution condition via insecure upload handling and (2) a high-severity time-based blind SQL injection in the `pic_id` parameter. The host additionally exposes multiple legacy/high-risk network services (Samba/IMAP/Tomcat/Jetty) and a Java object serialization service (potential deserialization risk). The session demonstrated code execution conditions but did not achieve a stable interactive shell; database extraction via SQLi was partially attempted but unstable/slow.

### Scope & Methodology

*   Hybrid testing using Burp Suite via MCP (history review, Intruder dispatch) and shell-based tooling for recon and vulnerability confirmation.
*   Primary focus: HTTP attack surface and adjacent exposed services.

### Tools & Automation

*   Burp MCP: `get_proxy_http_history`, `send_to_intruder`
*   nmap: service discovery and targeted scripts
*   sqlmap: SQLi confirmation/exploitation attempt
*   Findings

1.  **Critical — Remote Code Execution via Upload Handling**  
    Evidence indicates upload functionality allowed dangerous server-side execution behavior in `/images/` and visible upload artifacts in the UI.
2.  Recommendation: remove executable interpretation from upload paths; enforce strict upload validation; disable overrides; isolate uploads.
3.  **High — Time-Based Blind SQL Injection (**`**pic_id**`**)**  
    sqlmap confirmed time-based blind SQLi in `index.php?action=comment&pic_id=...` with MySQL fingerprinting on Linux.
4.  Recommendation: prepared statements, strict type validation, and monitoring for delay-based probes.
5.  **Medium–High — Broad Exposed Attack Surface (Services/Middleware)**  
    Open services include Samba, IMAP, Tomcat, Jetty, and Java serialization (port 5001).
6.  Recommendation: reduce exposure (firewall/segmentation), patch/upgrade, restrict management services to trusted networks.

## 12) Limitations / Operational Issues

*   Burp MCP connectivity instability observed
*   Workspace write restrictions impacted artifact generation during the run

![Image](https://miro.medium.com/v2/resize:fit:700/1*uelY5fsu1eeG8td3ncRGrg.png)

## Conclusion

The target is presently vulnerable to at least two high-impact web issues (RCE condition and SQLi) and exhibits significant service exposure that compounds compromise likelihood. Prioritize remediation of upload handling and SQL injection first, then reduce network attack surface and modernize/patch legacy components.

## 13) Hardening recommendations

*   **Bind to localhost** (`127.0.0.1`) and avoid exposing MCP to your LAN/WAN.
*   Start with `**trust: false**` in Gemini CLI and only enable trust for servers you fully control.
*   Leave **“tools that can edit your config”** disabled until you have a clear need (and understand what it enables).
*   Treat Burp data as sensitive. PortSwigger explicitly warns about external data processing policies.


Burp MCP + Gemini CLI is the difference between “AI that talks” and **AI that works**. Once Burp is exposed as MCP tools, the assistant can navigate real traffic, push test cases, and turn raw proxy noise into a structured storyline for your report. The Peruggia session showed both sides: it accelerated recon and validation, surfaced critical issues quickly, and also highlighted why guardrails matter — local-only exposure, confirmations enabled, and minimal privileges.

If you’re already using Burp every day, this is one of the highest leverage upgrades you can make: less copy/paste, more signal, and a workflow you can repeat across engagements.