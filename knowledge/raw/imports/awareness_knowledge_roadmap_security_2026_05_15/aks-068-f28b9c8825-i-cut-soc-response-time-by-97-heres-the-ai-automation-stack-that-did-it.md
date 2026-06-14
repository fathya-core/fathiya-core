# I Cut SOC Response Time by 97%: Here’s the AI Automation Stack That Did It

**Published:** 2025-12-28


## **From Alert Fatigue to Autonomous Defense**


![Image](https://miro.medium.com/v2/resize:fit:700/1*AoZ0wzj_128hn6K4HemOFQ.png)

If you manage a Security Operations Center (SOC), you know the nightmare: Your SIEM lights up like a Christmas tree. Your analysts are drowning in false positives. By the time they investigate one alert, ten more have piled up.

Alert fatigue isn’t just annoying — it’s a security vulnerability.

_read for free from_ [_here_](https://medium.com/@aloulouomarr/i-cut-soc-response-time-by-97-heres-the-ai-automation-stack-that-did-it-a6b8f43022e3?sk=504c0ee56bf1c0d80462437b5d800474)

I faced this exact challenge in a recent deployment. Our Wazuh implementation was catching threats effectively, but the manual investigation process was a bottleneck. We needed to fetch logs, check IP reputations, analyze patterns, and write compliance reports.

**This manual loop took 15–30 minutes per alert.** With 50+ alerts daily, the math didn’t add up.

So, I built an enterprise-grade, AI-powered automation workflow. **Now, that same process takes under 30 seconds.**

Here is the exact architecture I used to build it, and how it can be adapted to your organization.

## The Solution: The “30-Second SOC” Architecture

I designed an end-to-end automation system using **n8n**, **Ollama (running Mistral 7B)**, and **Wazuh**. This isn’t just a script; it’s a self-healing security ecosystem that:

1.  **Ingests** alerts in real-time via webhooks.
2.  **Context-Aware** Log Retrieval
3.  **Routes** logic to the specific affected VM/Endpoint.
4.  **Fetches** raw logs via secure SSH channels.
5.  **Enriches** data with Threat Intel (VirusTotal).
6.  **Analyzes** logs using a local LLM (Mistral 7B) to extract attack patterns.
7.  **Reports** a full incident summary to the team instantly.

**The result?** Zero human intervention until the final decision is needed.

## Under the Hood: The Enterprise Architecture

To make this scalable and secure, I moved away from monolithic setups. The infrastructure is split into dedicated nodes to ensure high availability:

*   **Core SIEM Cluster:** A 3-node Wazuh cluster handling Management, Indexing, and Dashboarding separately to prevent log ingestion bottlenecks.
*   **The Brain (AI & DFIR):** A dedicated high-memory node hosting the **IRIS DFIR** platform and **Ollama**.
*   **The Orchestrator:** An **n8n** instance that acts as the “glue,” managing the logic flow between the SIEM and the AI.

## Get the Workflow

The **AI SOC Analyst L1 Pro Edition** ( updated Version ) is available now on my store as a ready-to-import n8n JSON with full setup documentation.

👉 **Get it from —** [**Here**](https://neetrox.gumroad.com/l/ai-soc-analyst-n8n-wazuh)

👉 P**ay with Paypal —** [**Here**](https://payhip.com/Neetrox)

## How It Works: A Technical Deep Dive

### Step 1: Intelligent Reception & Normalization

SIEMs are notorious for sending messy JSON data. The first step in my n8n pipeline is a “Normalization Node.” It standardizes wazuh alerts — whether they come from a Syslog stream or a file integrity monitor — into a single, usable format.

### Step 2: Context-Aware Log Retrieval

Most automation tools fail here because they don’t know _where_ to look. I built a logic switch that routes the request and prepare the command based on the attack vector:

*   **SSH Brute Force?** → Pull /var/log/auth.log
*   **Web Attack?** → Pull Nginx/Apache access logs
*   **System Anomaly?** → Query journalctl

### Step 3: **Routes** logic to the specific affected VM/Endpoint.

The system then routes the request to the correct VM using a Switch node:

WManager → SSH: Wazuh Manager  
WDash → SSH: Wazuh Dashboard  
WIRIS → SSH: IRIS VM  
etc.

Each SSH node executes the prepared command and retrieves the last 100–500 relevant log lines containing the attacker’s IP address.

### Step 4: Parallel Threat Enrichment

While the logs are downloading, the system simultaneously queries the **VirusTotal API**.

This parallel processing cuts the total execution time by 40%.

### Step 5: The “AI Analyst” (Prompt Engineering)

This is the game-changer. Raw logs are noisy. I don’t just send logs to the AI; I send them to a **specialized Agent** with a strict system prompt

Instead of reading 500 lines of code, the human analyst receives:

*   **Auth:** 47 failed attempts (users: root, admin)
*   **Network:** 847 attempts in 15 mins via Port 22
*   **Pattern:** Dictionary attack, likely botnet

### Step 6: The Final Incident Report

A second AI agent takes the normalized alert, the VirusTotal data, and the log analysis to write the final report. This isn’t a robot output; it maps findings to the **MITRE ATT&CK** framework.

**Actual Output Example:**

![Image](https://miro.medium.com/v2/resize:fit:700/1*BlCFyFDBf2BjGa5SW5fvAg.png)

## You Want to See This in Action, Check this:

## The ROI: Why This Matters

I implemented this system to solve a specific business problem: **Resource Burnout.**

**Traditional Workflow VS My Automated Workflow**

**Investigation Time** 20 Minutes **1 Minute**

**False Positive Rate** High (Human Fatigue) **Low (AI Pre-filtering)**

**MTTR (Response)** 45 Minutes **5 Minutes**

**Cost** High (Analyst Hours) **Near Zero (Local LLM)**

The SOC team now receives a complete incident report in Discord/Slack _before_ they even notice the alert on the dashboard.

## Bring This Architecture to Your Organization

Automation is no longer a luxury; it is a necessity for modern security operations.

I help organizations transform their security posture from “Reactive Firefighting” to “Proactive Defense.” Whether you are running a lean startup or an enterprise SOC, I can tailor this architecture to your stack.

## How I Can Help You:

**Custom SOC Automation:** I design workflows tailored to your specific infrastructure (Cloud, On-Prem, or Hybrid).

**SIEM Optimization:** Whether you use **Wazuh, Splunk, ELK, or Sentinel**, I can integrate AI-driven analysis into your existing pipeline.

**Cost-Efficient AI:** I specialize in deploying local LLMs (Ollama/Mistral) that provide high-level analysis without the data privacy risks or costs of public APIs like OpenAI.

**Team Training:** I have a video ready for your team that explains how to maintain and expand the automation.

**Ready to stop drowning in alerts?**

*   💼 **LinkedIn:** [**Link**](https://www.linkedin.com/in/omar-aloulou/)

_The machines handle the repetitive data. Your humans handle the strategy. Let’s build your future SOC today._