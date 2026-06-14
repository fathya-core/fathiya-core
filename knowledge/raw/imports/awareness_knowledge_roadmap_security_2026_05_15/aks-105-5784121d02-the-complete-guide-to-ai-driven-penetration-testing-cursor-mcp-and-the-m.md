# The Complete Guide to AI-Driven Penetration Testing: Cursor, MCP, and the Modern PT Workflow

**Published:** 2026-02-19


## **A comprehensive, step-by-step guide to running penetration tests the way that actually works — faster, deeper, and more powerful — after hundreds of engagements and countless tools.**


![Image](https://miro.medium.com/v2/resize:fit:700/1*dDhsk11-rmAvlsJ_93jeUA.png)

## Introduction

Penetration testing hasn’t changed because of AI. The kill chain is still the kill chain: scope → recon → enumeration → exploitation → post-exploitation → reporting. What _has_ changed is the execution layer — how fast you can move, how consistently you can capture artifacts, and how well you can turn raw output into decisions.

Most “AI pentesting” content today is either:

*   a chatbot generating one-off commands with no state, or
*   a flashy demo that collapses the real workflow into a single prompt.

That’s not how real engagements work.

Real engagements are won by **pipeline discipline**: every phase produces artifacts (hosts, ports, screenshots, creds, notes), and those artifacts drive the next phase. The bottleneck isn’t knowing _what_ to do — it’s doing it **reliably**, **documenting it**, and **iterating** without losing context.

That’s why this guide is centered around a specific model that consistently works in practice:

**Cursor as the control plane + MCP as the tool bus + a modern PT toolset as the execution layer.**

Cursor isn’t “another chat.” It’s an IDE that can see your project, your files, your outputs, and your knowledge base. Add MCP, and the same interface can orchestrate real tooling — recon, scanning, Burp workflows, exploit chains — while keeping everything inside a repeatable project structure. The result is not “automatic hacking.” It’s **manual methodology with amplified throughput**: faster recon loops, better correlation of findings, cleaner artifacts, and dramatically improved reporting velocity.

This post is a step-by-step playbook for building that workflow:

*   how to set up a PT machine and keep it stable,
*   how to structure engagements so the AI has _correct context_,
*   how to run the kill chain as a pipeline (not random commands),
*   and how to use AI where it’s strongest: orchestration, analysis, iteration, and narrative building — while you stay in control of scope, judgment, and risk.

If you want a workflow that feels like a high-quality manual PT — just faster, deeper, and harder to derail — this is the one.

### If you like this research, [buy me a coffee (PayPal) — Keep the lab running](https://www.paypal.com/donate/?business=W3XDKS7J9XTCG&no_recurring=0&item_name=Buy+me+a+coffee+%28PayPal%29+%E2%80%94+Keep+the+lab+running&currency_code=USD)

## Table of Contents

[**Introduction**](#ce0e)

1.  [**Why Cursor? The Short Answer After Many PTs**](#f6ad)
2.  [**How AI-Driven PT Works: The Big Picture**](#8e9c)
3.  [**Building and Configuring Your PT Toolset**](#adb2)
4.  [**Starting a New PT Project: Structure and Knowledge Base**](#fd0d)
5.  [**The Kill Chain as a Pipeline: Step by Step**](#b7a4)
6.  [**Examples and Deep Dives**](#2064)
7.  [**References and Further Reading**](#6c91)

## 1\. Why Cursor? The Short Answer After Many PTs

After running many penetration tests with many different tools — [Nmap](https://medium.com/@1200km/mastering-nmap-a-comprehensive-guide-to-network-exploration-and-security-auditing-f36d74d1b2c0), [Burp Suite](https://medium.com/@1200km/mastering-burp-suite-vulnerability-scanner-019ed82c8bac), [Metasploit](https://medium.com/@1200km/the-ultimate-guide-to-metasploit-43c8573487df), [Hydra](https://medium.com/@1200km/mastering-hydra-the-ultimate-guide-to-network-logon-cracking-182579dbaed1), [HexStrike-AI](https://medium.com/ai-security-hub/hexstrike-on-kali-linux-2025-4-a-comprehensive-guide-85a0e5752949), [HackerAI](https://medium.com/@1200km/enhancing-penetration-testing-with-hackerai-step-by-step-guide-metasploitable-lab-b2ab2cdd4139), [standalone LLMs](/hexstrike-mcp-orchestration-with-ollama-ubuntu-host-kali-vm-ssh-bridging-and-performance-f049ab140596), and MCP in isolation — the approach that consistently delivers the best results is **working with Cursor** as the central interface.

**Why Cursor wins:**

*   **Single surface for everything.** You stay in one environment: natural language, code generation, script execution, and tool orchestration. No constant switching between terminal, browser, and chat.
*   **Full workflow, not just “chat with a tool.”** Cursor is an IDE with an AI that sees your project, your files, and your context. When you add MCP (Model Context Protocol), the same AI can drive HexStrike-AI, Burp, Shodan, and other tools. That’s not a chatbot with plugins — it’s an **ops copilot** that can run a full PT from recon to report. See: [HexStrike + Gemini vs. HackerAI: “Ops Copilot” vs. “Chatbot with Tools”](https://medium.com/@1200km/hexstrike-gemini-vs-hackerai-ops-copilot-vs-chatbot-with-tools-1d799845410b).

*   **Project and knowledge base in one place.** You create a project folder, add scope docs, previous reports, and tool outputs. The AI uses all of that as context. That’s how you get “like a regular manual PT, just faster and deeper.”
*   **Pipeline thinking.** Each phase of the kill chain produces outputs (scan results, credentials, screenshots). You feed those into the next phase. Cursor + MCP lets you do that in a structured way: same rigor as manual PT, with automation and AI-assisted decisions.

So: the best way to work, based on real experience, is **Cursor + MCP + your PT toolset (e.g. HexStrike-AI, Burp MCP)** — with a clean toolset, a dedicated project layout, and a project-specific knowledge base. The rest of this guide details how to build that.

## 2\. How AI-Driven PT Works: The Big Picture

AI-driven PT is still a **manual methodology** in spirit: you follow a kill chain, you analyze each step, you decide when to go deeper or go back. The difference is **how** you execute and analyze.

1.  **You work in Cursor** (or another MCP-capable client) connected to your tools via MCP (e.g. HexStrike-AI, Burp Suite MCP).
2.  **You give high-level instructions** in natural language (“enumerate this subnet,” “find web vulns on this host,” “crack this hash with context from the client name”).
3.  **The AI proposes and runs tool invocations** (Nmap, Nuclei, Burp, Hydra, etc.), reads outputs, and suggests next steps.
4.  **You review results** at each stage. You can ask to re-run with different options, go back to recon, or drill into a specific finding.
5.  **Outputs form a pipeline:** recon → scanning → exploitation → post-exploitation → reporting. Each step’s artifacts (files, logs, screenshots) are stored in the project and used as context for the next.

So: **same phases as a regular manual PT, with AI and automation making each phase faster and more thorough.** For a full lab example, see [HexStrike + Cursor (MCP): From Single Target → Full Subnet Compromise (Lab PT Walkthrough](https://medium.com/ai-security-hub/hexstrike-cursor-mcp-from-single-target-full-subnet-compromise-lab-pt-walkthrough-f2e1fd793ad7)).

## 3\. Building and Configuring Your PT Toolset

Before you run a single engagement, your environment must be ready. That means: base OS (Kali, Arch, or custom), tools updated, API keys set, wordlists and rainbow tables in place, and dependencies installed. Do this once (and maintain it); then every new PT starts from a known-good state.

### 3.1 Choose and Harden Your Base System

*   **Kali Linux** — Easiest: most tools preinstalled, good for getting started. See [HexStrike on Kali Linux 2025.4: A Comprehensive Guide](https://medium.com/ai-security-hub/hexstrike-on-kali-linux-2025-4-a-comprehensive-guide-85a0e5752949).
*   **Arch (BlackArch or plain Arch + tools)** — Rolling updates, minimal by default; you add only what you need.
*   **Custom (e.g. Ubuntu/Debian + your own tool list)** — Full control; you maintain updates and dependencies yourself.

**Regardless of base:**

*   Use a dedicated VM or physical machine for PT (never on a production or corporate main workstation without policy approval).
*   Snapshot the VM after a clean toolset build so you can revert if something breaks.
*   Keep the system updated regularly (`apt update && apt full-upgrade` or equivalent).

### 3.2 Install and Update Core Tools

Install or verify these (versions and names may differ by distro):

*   **Recon / scanning:** Nmap, Masscan, Nikto, Nuclei, theHarvester, Sublist3r, Amass, SpiderFoot.  
    Refs: [Nmap](https://medium.com/@1200km/mastering-nmap-a-comprehensive-guide-to-network-exploration-and-security-auditing-f36d74d1b2c0), [theHarvester](https://medium.com/@1200km/theharvester-your-essential-tool-for-osint-and-reconnaissance-in-cybersecurity-10aa6d76f5b3), [Sublist3r](https://medium.com/@1200km/sublist3r-your-essential-tool-for-subdomain-enumeration-c1910121d712), [OWASP Amass](https://medium.com/@1200km/owasp-amass-project-guide-94bd55521f91), [SpiderFoot](https://medium.com/@1200km/spiderfoot-deep-dive-installation-scans-and-practical-use-cases-11ea6537ad6f).
*   **Web:** Burp Suite (Pro or Community), OWASP ZAP, SQLMap, Dirb/Gobuster/FFuf.  
    Refs: [Burp Suite](https://medium.com/@1200km/mastering-burp-suite-vulnerability-scanner-019ed82c8bac), [Getting More from Burp Suite with LLMs](https://medium.com/@1200km/getting-more-from-burp-suite-with-llms-fdd03cec343d).
*   **Exploitation:** Metasploit Framework, searchsploit, custom PoC scripts.  
    Ref: [Metasploit](https://medium.com/@1200km/the-ultimate-guide-to-metasploit-43c8573487df).

*   **Credential testing:** Hydra, Medusa, Ncrack, John the Ripper, Hashcat.  
    Refs: [Hydra](https://medium.com/@1200km/mastering-hydra-the-ultimate-guide-to-network-logon-cracking-182579dbaed1), [John the Ripper](https://medium.com/@1200km/mastering-john-the-ripper-a-complete-guide-to-password-cracking-e42d68239c71), [Hashcat](https://medium.com/@1200km/breaking-the-code-how-to-use-hashcat-for-effective-password-cracking-15f8da8facb8).
*   **Wireless (if in scope):** Aircrack-ng suite.  
    Ref: [Wifi cracking with Aircrack-ng](https://medium.com/@1200km/wifi-cracking-with-aircrack-ng-d51cf98c789f).

*   **AI/MCP stack:** HexStrike-AI (or your chosen MCP server), Cursor (or another MCP client).  
    Refs: [HexStrike AI: Install, Configure, and Run MCP with Gemini, OpenAI, Cursor, Llama](https://medium.com/@1200km/hexstrike-ai-install-configure-and-run-mcp-with-gemini-openai-cursor-llama), [Burp Suite MCP + Gemini CLI](https://medium.com/@1200km/burp-suite-mcp-gemini-cli-connect-burp-suite-to-gemini-cli-using-mcp).

After install, run tool-specific update commands (e.g. `msfupdate`, `nuclei -update-templates`, `searchsploit -u`).

### 3.3 API Keys and External Services

Configure once; reuse for every project:

*   **Shodan** — Recon and exposed-asset discovery. Create key at shodan.io, set in env (e.g. `SHODAN_API_KEY`) or in HexStrike/Shodan config.  
    Ref: [Shodan — you can find everything](https://medium.com/@1200km/shodan-you-can-find-everything-640f47f41bbe), [Integrating Shodan with HexStrike-AI Using Gemini-CLI](https://medium.com/@1200km/integrating-shodan-with-hexstrike-ai-using-gemini-cli-b6f9fcbe8e6e).

*   **VirusTotal** (optional) — Hash/file/URL lookups. Use env or config.
*   **Censys / ZoomEye / etc.** (optional) — Same idea: key in env or tool config so MCP/AI can use them when needed.

Store keys in a secure store (e.g. env file not in git, or a secrets manager) and document in your internal runbook where each tool reads them from.

### 3.4 Wordlists, Username Lists, and Directory Dictionaries

Create a single, well-organized directory (e.g. `/opt/wordlists` or `~/wordlists`) and keep it updated:

**Best resource:**

[**https://weakpass.com/wordlists/**](https://weakpass.com/wordlists/)

*   **Passwords:**
*   RockYou (and variants), SecLists `Passwords/`, weak passwords from breaches, company/context-specific lists.
*   For AI-assisted cracking: [HexStrike + Gemini. AI-Assisted SMB Credential Brute-Force](https://medium.com/@1200km/hexstrike-gemini-ai-assisted-smb-exposure-credential-brute-force-2c5f99dcdbf4), [AI-Driven ZIP Password Recovery with HexStrike-AI and Gemini-CLI](https://medium.com/@1200km/ai-driven-zip-password-recovery-with-hexstrike-ai-and-gemini-cli-b8fc5c475ebc).
*   **Usernames:**
*   SecLists `Usernames/`, generated lists from OSINT (names, emails, IDs). Feed these into Hydra/Medusa and into AI context for smarter guessing.
*   **Web/directory:**
*   SecLists `Discovery/Web-Content/`, DirBuster lists, custom lists for tech stacks (e.g. `admin`, `wp-admin`, `.git`, API paths).
*   **Subdomains:**
*   SecLists, Amass wordlists, custom from previous engagements (sanitized).

Point HexStrike and your scripts at this directory so the AI can “choose the right list” based on target (e.g. [AI-Driven PDF/Office Password Recovery](https://medium.com/@1200km/ai-driven-pdf-password-recovery-with-hexstrike-ai-and-gemini-cli-cfa7eb0fae91), [Office Documents](https://medium.com/@1200km/ai-driven-office-documents-password-recovery-with-hexstrike-ai-and-gemini-cli-3c8bb7deb82d)).

### 3.5 Rainbow Tables and Hash Cracking Resources

*   **Rainbow tables:** For LM/NTLM and other algorithms where you’ve decided to use them (storage-heavy). Store in a known path and document which hash types they cover.
*   **Hashcat/John rules:** Install and update rule sets (e.g. Hashcat rules, John rules) so the AI can suggest “try rule X with this wordlist” for credential and file-cracking tasks.  
    Refs: [John the Ripper](https://medium.com/@1200km/mastering-john-the-ripper-a-complete-guide-to-password-cracking-e42d68239c71), [Hashcat](https://medium.com/@1200km/breaking-the-code-how-to-use-hashcat-for-effective-password-cracking-15f8da8facb8).

### 3.6 Dependencies and Runtimes

*   **Python 3** — Many tools and HexStrike depend on it. Use a venv per project if you have custom scripts.
*   **Ruby (Metasploit), Go (many modern tools)** — Install as required by your distro.
*   **GPU drivers (for Hashcat)** — Install and test if you use GPU cracking.
*   **MCP server dependencies** — Whatever HexStrike-AI or Burp MCP need (Node/Python, etc.); document in your setup guide.

After this section, your “PT machine” is a single, repeatable environment: base OS + updated tools + API keys + wordlists + cracking resources + dependencies. Then every new engagement starts from the same foundation.

## 4\. Starting a New PT Project: Structure and Knowledge Base

For **every** new penetration test, do the following before running any attacks. This keeps engagements consistent and lets the AI use project-specific context.

### 4.1 Create a Project Directory

Create one folder per engagement, for example:

~/pt-projects/  
  client-name-2025-01/  
    scope.txt           \# In-scope IPs/domains, OOB, rules of engagement  
    notes.md            \# Timeline, credentials found, open questions  
    recon/  
    scan/  
    exploit/  
    postex/  
    report/  
    kb/                 \# Knowledge base (see below)

*   **scope.txt (or scope.md):** In-scope targets, out-of-scope, and any constraints (e.g. “no DoS,” “only these subnets”).
*   **notes.md:** Running log: what you did, what you found, credentials, next steps. The AI can use this file when you ask “what have we tried on this host?”
*   **recon / scan / exploit / postex / report:** Store phase outputs here (see pipeline below). Use subfolders per host or per phase if needed (e.g. `scan/nmap/`, `scan/burp/`).

### 4.2 Build a Project-Specific Knowledge Base (KB)

Put in `kb/` (or a dedicated subfolder) everything that should guide this engagement:

*   **Official docs:** Product/version docs for in-scope systems (e.g. CMS, API framework, VPN). PDFs or cleaned HTML are fine.
*   **Previous reports:** Sanitized excerpts or summaries from past PTs for the same client (if allowed). Helps the AI suggest “last time we saw X, try Y.”
*   **Scope and RoE:** Copy or link scope, rules of engagement, and any communication constraints.
*   **Asset list (if provided):** IPs, hostnames, critical apps. The AI can use this to prioritize and avoid out-of-scope targets.

You don’t need to paste every doc into the chat — Cursor (and the AI) can read files in the project. So you can say: “Using the docs in `kb/`, suggest the best way to test this API.” This is how you get “like a regular manual PT”: the same kind of context a human would use, but available to the model.

### 4.3 Open the Project in Cursor and Connect MCP

*   Open the project root (e.g. `~/pt-projects/client-name-2025-01`) in Cursor.
*   Ensure MCP is configured so Cursor talks to HexStrike-AI (and Burp MCP if you use it).  
    Ref: [HexStrike AI: Install, Configure, and Run MCP with Gemini, OpenAI, Cursor, Llama](https://medium.com/@1200km/hexstrike-ai-install-configure-and-run-mcp-with-gemini-openai-cursor-llama).

From here on, all recon, scanning, exploitation, and note-taking can be driven from Cursor with the project and KB as context.

## 5\. The Kill Chain as a Pipeline: Step by Step

Run the engagement as a **pipeline**: each phase produces outputs that feed the next. After each phase, **analyze results**; if something is unclear or you need more data, **go back** to an earlier step (e.g. more recon or a different scan). This is the same discipline as a manual PT — just faster and with AI assistance.

### 5.1 Reconnaissance (Recon)

*   **Goals:** Discover in-scope targets, subdomains, tech stack, and public exposure.
*   **Actions:**
*   Passive: Shodan, theHarvester, Amass, Sublist3r, SpiderFoot (with API keys where needed).
*   Active (only within RoE): light Nmap (e.g. -sV -sC on allowed IPs).
*   **Outputs to save in project:**
*   `recon/domains.txt`, `recon/subdomains.txt`, `recon/ips.txt`, `recon/shodan_*.json` (or similar), `recon/theharvester_*.json`.
*   **AI use:** Ask Cursor/HexStrike to run Shodan/theHarvester/Amass for the scope, then “summarize findings and suggest next scans.”  
    Refs: [Integrating Shodan with HexStrike-AI](https://medium.com/@1200km/integrating-shodan-with-hexstrike-ai-using-gemini-cli-b6f9fcbe8e6e), [HexStrike + Cursor for OSINT: From One Email to a Full Exposure Map](https://medium.com/@1200km/hexstrike-cursor-for-osint-from-one-email-to-a-full-exposure-map).
*   **Pipeline:** Recon outputs become the **target list** for scanning (hosts, ports, services).

### 5.2 Scanning and Enumeration (Scan)

*   **Goals:** Open ports, services, versions, and potential vulns (e.g. Nuclei, Nikto, default creds).
*   **Actions:**
*   Nmap (version + scripts) on targets from recon.
*   Nuclei with appropriate templates.
*   Web: Burp/ZAP crawls and scans; Dirb/Gobuster/FFuf for paths.
*   Optional: vulnerability scanners (Nessus, etc.) if in scope.
*   **Outputs to save:**
*   `scan/nmap/<host>.xml` and `.nmap`, `scan/nuclei/*.json`, `scan/burp/*.xml` or project file, `scan/dirb_*.txt`.
*   **AI use:** “From `recon/ips.txt` and scope, run Nmap and Nuclei; put results in `scan/`. Then prioritize by criticality.”  
    Refs: [Reinventing Recon: Nmap Meets ChatGPT](https://medium.com/@1200km/reinventing-recon-nmap-meets-chatgpt-e2acb6130be5), [Getting More from Burp Suite with LLMs](https://medium.com/@1200km/getting-more-from-burp-suite-with-llms-fdd03cec343d), [AI-Driven Web Application Pentesting with HexStrike-AI](https://medium.com/@1200km/ai-driven-web-application-pentesting-with-hexstrike-ai-67f3dae32040).
*   **Pipeline:** Scan results (CVEs, services, paths) feed into **exploitation** (exploit selection, payload design).

### 5.3 Exploitation

*   **Goals:** Gain initial access (or prove impact) using findings from scan + recon.
*   **Actions:**
*   Metasploit, searchsploit, custom PoCs.
*   Web: Burp-based exploitation (SQLi, XSS, SSRF, etc.).
*   Credential stuffing / brute-force where allowed (using wordlists from your toolset).
*   Wireless: only if in scope ([AI-Driven Wireless Penetration Testing. One Prompt WIFI cracking](https://medium.com/@1200km/ai-driven-wireless-penetration-testing-one-promt-wifi-cracking-6477c06f6af4)).
*   **Outputs to save:**
*   `exploit/<host>_<service>_notes.md`, screenshots, hashes/creds in `notes.md` (or a creds file with care).
*   **AI use:** “Given this Nmap/Nuclei output in `scan/`, suggest and run Metasploit modules or PoCs; document results in `exploit/`.”  
    Ref: [HexStrike+OpenAI Codex. AI-Driven Exploitation of Metasploitable](https://medium.com/@1200km/ai-driven-exploitation-of-metasploitable2-from-recon-to-root-with-codex-hexstrike-ai-b892c07be39f).
*   **Pipeline:** Obtained access and credentials feed **post-exploitation** (lateral movement, privilege escalation, persistence).

### 5.4 Post-Exploitation

*   **Goals:** Escalate privileges, move laterally, and (if in scope) demonstrate full impact (e.g. domain compromise).
*   **Actions:**
*   Local enumeration (WinPEAS, LinPEAS, etc.), credential dumping, pass-the-hash, Kerberos attacks (e.g. ADCS ESC8), DCSync.
*   Pivot and re-scan from compromised host (using project context and scope).
*   **Outputs to save:**
*   `postex/<host>_*.md`, dumps (stored securely), screenshots.
*   **AI use:** “We have access to host X and creds Y; suggest next steps for privilege escalation and lateral movement given scope.” You can reference internal docs (e.g. ADCS, BloodHound) in `kb/`.
*   **Pipeline:** Post-ex findings and evidence feed **reporting**.

### 5.5 Analysis and Iteration

*   After **each** phase:
*   Review AI-suggested and tool outputs.
*   If results are insufficient or ambiguous, **go back**: e.g. more recon, different Nmap options, or a deeper Burp scan.
*   Update `notes.md` and phase folders so the next step has full context.

This loop (recon → scan → exploit → postex → analyze → possibly back) is exactly like a manual PT; the difference is that the AI can propose and run many of the commands and correlate findings for you. For an end-to-end example: [AI-Driven Pentesting at Home: Using HexStrike-AI for Full Network Discovery and Exploitation](https://medium.com/@1200km/ai-driven-pentesting-at-home-using-hexstrike-ai-for-full-network-discovery-and-exploitation-00a9e88b3bde).

### 5.6 Reporting

*   **Goals:** Clear, evidence-based report (findings, impact, remediation).
*   **Inputs:** All artifacts in `recon/`, `scan/`, `exploit/`, `postex/`, and `notes.md`.
*   **AI use:** “Draft the executive summary and findings sections from `notes.md` and the evidence in the project; use scope in `scope.txt` for in-scope summary.” You then edit and approve.  
    Ref: [Augmenting Digital Forensics with AI: How ChatGPT Transforms Investigation Workflows](https://medium.com/@1200km/augmenting-digital-forensics-with-ai-how-chatgpt-transforms-investigation-workflows-34eb10887ea5) (same idea: AI helps turn technical output into structured narrative).

## 6\. Examples and Deep Dives

*   **Full lab PT (single host → subnet):** [HexStrike + Cursor (MCP): From Single Target → Full Subnet Compromise (Lab PT Walkthrough)](https://medium.com/ai-security-hub/hexstrike-cursor-mcp-from-single-target-full-subnet-compromise-lab-pt-walkthrough-f2e1fd793ad7).

[

## HexStrike + Cursor (MCP): From Single Target → Full Subnet Compromise (Lab PT Walkthrough)

### A real end-to-end lab engagement: recon → credential discovery → share abuse → lateral movement → multi-host compromise…

medium.com


](https://medium.com/ai-security-hub/hexstrike-cursor-mcp-from-single-target-full-subnet-compromise-lab-pt-walkthrough-f2e1fd793ad7?source=post_page-----8f27ff19f9ca---------------------------------------)

*   **OSINT from one email:** [HexStrike + Cursor for OSINT: From One Email to a Full Exposure Map](https://medium.com/ai-security-hub/hexstrike-cursor-for-osint-from-one-email-to-a-full-exposure-map-ffdfc7ba1b30).

[

## HexStrike + Cursor for OSINT: From One Email to a Full Exposure Map

### Why OSINT is harder than “hack the box,” what an AI-assisted workflow looks like in practice, and how to publish a real…

medium.com


](https://medium.com/ai-security-hub/hexstrike-cursor-for-osint-from-one-email-to-a-full-exposure-map-ffdfc7ba1b30?source=post_page-----8f27ff19f9ca---------------------------------------)

*   **Web + cloud with Cursor and MCP:** [AI-Assisted Web and Cloud Penetration Testing with Cursor + MCP HexStrike and Burp Suite MCP](https://medium.com/@1200km/ai-assisted-web-and-cloud-penetration-testing-with-cursor-mcp-hexstrike-and-burp-suite-mcp-01c02eed5258).

[

## AI-Assisted Web and Cloud Penetration Testing with Cursor + MCP HexStrike and Burp Suite MCP.

### A Complete Guide to Modern AI-Powered Security Testing. From One Prompt to Full Attack Surface Coverage (Recon →…

infosecwriteups.com


](/ai-assisted-web-and-cloud-penetration-testing-with-cursor-mcp-hexstrike-and-burp-suite-mcp-01c02eed5258?source=post_page-----8f27ff19f9ca---------------------------------------)

*   **Credential attacks (SMB/SSH):** [HexStrike + Gemini. AI-Assisted SMB Exposure Credential Brute-Force](https://medium.com/@1200km/hexstrike-gemini-ai-assisted-smb-exposure-credential-brute-force-2c5f99dcdbf4), [HexStrike + Gemini. AI-Assisted SSH Credential Brute-Force](https://medium.com/@1200km/hexstrike-gemini-ai-assisted-ssh-credential-brute-force-a9162f8e253b).

*   **Password/file recovery (ZIP, PDF, Office):** [AI-Driven ZIP Password Recovery with HexStrike-AI and Gemini-CLI](https://medium.com/@1200km/ai-driven-zip-password-recovery-with-hexstrike-ai-and-gemini-cli-b8fc5c475ebc), [AI-Driven PDF Password Recovery](https://medium.com/@1200km/ai-driven-pdf-password-recovery-with-hexstrike-ai-and-gemini-cli-cfa7eb0fae91), [AI-Driven Office Documents Password Recovery](https://medium.com/@1200km/ai-driven-office-documents-password-recovery-with-hexstrike-ai-and-gemini-cli-3c8bb7deb82d).

*   **Tool dev and env setup with Cursor:** [Hacker Tool Development Workflow: Android Rubber Ducky Payloads in Cursor AI](https://medium.com/@1200km/how-cursor-ai-became-my-full-stack-development-partner-from-arduino-code-to-visual-validation-47fcccb9c845), [Building a USB Rubber Ducky with Arduino Leonardo with Cursor](https://medium.com/@1200km/building-a-usb-rubber-ducky-with-arduino-leonardo-with-cursor-a23dd64d1bbe).

*   **Threat hunting (defender side, same mindset):** [Endpoint Threat Hunting: Proactive Detection on Windows, Linux, and macOS](https://medium.com/@1200km/endpoint-threat-hunting-proactive-detection-on-windows-linux-and-macos-f892d9b8a113), [Protocol-Level Network Threat Hunting: A Wireshark-Centric Guide](https://medium.com/@1200km/protocol-level-network-threat-hunting-a-wireshark-centric-guide-a6770ffc96c6), [Threat Hunting with the Pyramid of Pain](https://medium.com/@1200km/threat-hunting-with-the-pyramid-of-pain-8add3cedb380).

*   **Broader picture:** [HexStrike-AI: A Force Multiplier for Red Teams — and a Dangerous Shift in the Threat Landscape](https://medium.com/@1200km/hexstrike-ai-a-force-multiplier-for-red-teams-and-a-dangerous-shift-in-the-threat-landscape-3e1d4e86f3ae), [The 20x Employee: A Strategic Framework for Unlocking Hyper-Productivity with Artificial Intelligence](https://medium.com/@1200km/the-20x-employee-a-strategic-framework-for-unlocking-hyper-productivity-with-artificial-8f49cde95a25).

## 7\. References and Further Reading

### My Articles (by topic)

*   **Setup and MCP:** [HexStrike AI: Install, Configure, and Run MCP with Gemini, OpenAI, Cursor, Llama](https://medium.com/@1200km/hexstrike-ai-install-configure-and-run-mcp-with-gemini-openai-cursor-llama), [HexStrike on Kali Linux 2025.4: A Comprehensive Guide](https://medium.com/@1200km/hexstrike-on-kali-linux-2025-4-a-comprehensive-guide).
*   **Burp + AI/MCP:** [Getting More from Burp Suite with LLMs](https://medium.com/@1200km/getting-more-from-burp-suite-with-llms-fdd03cec343d), [Burp Suite MCP + Gemini CLI](https://medium.com/@1200km/burp-suite-mcp-gemini-cli-connect-burp-suite-to-gemini-cli-using-mcp).
*   **Recon and OSINT:** [Reinventing Recon: Nmap Meets ChatGPT](https://medium.com/@1200km/reinventing-recon-nmap-meets-chatgpt-e2acb6130be5), [Shodan](https://medium.com/@1200km/shodan-you-can-find-everything-640f47f41bbe), [theHarvester](https://medium.com/@1200km/theharvester-your-essential-tool-for-osint-and-reconnaissance-in-cybersecurity-10aa6d76f5b3), [Sublist3r](https://medium.com/@1200km/sublist3r-your-essential-tool-for-subdomain-enumeration-c1910121d712), [OWASP Amass](https://medium.com/@1200km/owasp-amass-project-guide-94bd55521f91), [SpiderFoot](https://medium.com/@1200km/spiderfoot-deep-dive-installation-scans-and-practical-use-cases-11ea6537ad6f).
*   **Core tools (no AI):** [Nmap](https://medium.com/@1200km/mastering-nmap-a-comprehensive-guide-to-network-exploration-and-security-auditing-f36d74d1b2c0), [Burp Suite](https://medium.com/@1200km/mastering-burp-suite-vulnerability-scanner-019ed82c8bac), [Metasploit](https://medium.com/@1200km/the-ultimate-guide-to-metasploit-43c8573487df), [Hydra](https://medium.com/@1200km/mastering-hydra-the-ultimate-guide-to-network-logon-cracking-182579dbaed1), [John the Ripper](https://medium.com/@1200km/mastering-john-the-ripper-a-complete-guide-to-password-cracking-e42d68239c71), [Hashcat](https://medium.com/@1200km/breaking-the-code-how-to-use-hashcat-for-effective-password-cracking-15f8da8facb8), [Aircrack-ng](https://medium.com/@1200km/wifi-cracking-with-aircrack-ng-d51cf98c789f).

### External frameworks and references

*   **MITRE ATT&CK:** [attack.mitre.org](https://attack.mitre.org/) — Map your actions and findings to tactics and techniques.
*   **PTES (Penetration Testing Execution Standard):** [ptes.org](http://www.ptes.org/) — High-level PT methodology.
*   **OWASP:** [owasp.org](https://owasp.org/) — Web and API testing (e.g. Top 10, Testing Guide).
*   **NIST SP 800–115 (Technical Guide to Information Security Testing and Assessment):** For scope and methodology alignment in formal engagements.

## Summary

*   **Best way to work after many PTs:** **Cursor + MCP + your PT toolset** (e.g. HexStrike-AI, Burp MCP), with a clean, repeatable environment and a project-based workflow.
*   **Environment:** One base system (Kali/Arch/custom), all tools updated, API keys set, wordlists and cracking resources in one place, dependencies documented.
*   **Per engagement:** One project directory, scope and RoE, a small knowledge base (docs, previous reports), and phase folders (recon → scan → exploit → postex → report).
*   **Execution:** Run the kill chain as a **pipeline**: each phase’s outputs feed the next; analyze after each step and go back when needed; use the AI to propose and run tools and to draft reports from your artifacts.

Same rigor as a manual PT — faster, deeper, and more powerful.

_This guide is based on many real penetration tests and the articles linked above. For the full narrative on AI in cybersecurity and the evolution from simple LLM use to Cursor + MCP, see_ [_The AI Revolution in Cybersecurity: A Comprehensive Journey Through Modern AI-Driven Security Operations_](https://medium.com/@1200km/the-ai-revolution-in-cybersecurity-31e44704d51a) _(and the_ [_summary on my Medium_](https://medium.com/@1200km)_)._


## Follow for practical cybersecurity research

If you’re interested in **Offensive security,** **AI security, real-world attack simulations, CTI, and detection engineering** — this is exactly what I focus on.

Stay connected:

→ **Subscribe on Medium:** [medium.com/@1200km](https://medium.com/@1200km)  
→ **Connect on LinkedIn:** [andrey-pautov](https://www.linkedin.com/in/andrey-pautov/)  
→ **GitHub — tools & labs:** [github.com/anpa1200](https://github.com/anpa1200)  
→ **Contact:** [1200km@gmail.com](mailto:1200km@gmail.com)

### **Andrey Pautov**