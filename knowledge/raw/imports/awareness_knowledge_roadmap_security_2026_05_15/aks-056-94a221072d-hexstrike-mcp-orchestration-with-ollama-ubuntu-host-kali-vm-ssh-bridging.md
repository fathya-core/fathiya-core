# HexStrike MCP Orchestration with Ollama: Ubuntu Host, Kali VM, SSH Bridging, and Performance Caveats

**Published:** 2025-12-31


## How to wire Ubuntu (Ollama) to Kali (HexStrike) with MCP over SSH, what models actually behaved (Qwen3 8B/14B), and when you should move to GPU or cloud models.


![Image](https://miro.medium.com/v2/resize:fit:700/1*FEND4twn4pGNlLPNTCr6zQ.png)

Below is a practical, end-to-end setup that keeps the **LLM on Ubuntu (host)** and runs **HexStrike on Kali (VM)**, then bridges them so your local model can “drive” HexStrike tool calls.

## Additional guides:

[

## HexStrike AI: Install, Configure, and Run MCP with Gemini, OpenAI, Cursor, Llama

### A practical, end-to-end guide to installing HexStrike AI, wiring it as an MCP server, and running real tool-driven…

medium.com


](https://medium.com/ai-security-hub/hexstrike-on-kali-linux-2025-4-a-comprehensive-guide-85a0e5752949?source=post_page-----f049ab140596---------------------------------------)

### If you like this research, [buy me a coffee (PayPal) — Keep the lab running](https://www.paypal.com/donate/?business=W3XDKS7J9XTCG&no_recurring=0&item_name=Buy+me+a+coffee+%28PayPal%29+%E2%80%94+Keep+the+lab+running&currency_code=USD)

## Table of content

1.  [**Disclaimer (Performance & Practicality)**](#a980)
2.  [**Why use a local LLM for pentesting?**](#e69b)
3.  [**Target architecture (recommended)**](#4fb9)
4.  [**VM tuning**](#8daf)
5.  [**Ubuntu (host): install Ollama + pull a model**](#3d0c)
6.  [**Kali VM: install and start HexStrike**](#8311)
7.  [**Kali VM — Networking + SSH**](#770b)
8.  [**Install mcphost (terminal MCP host) and wire it to HexStrike**](#a0f4)
9.  [**SSH key auth (recommended) + prevent SSH banners from breaking MCP stdio**](#4047)
10.  [**Like ollama run …” — one-liner usage from Ubuntu terminal**](#86f9)
11.  [**Recommended hardening**](#11d0)
12.  [**Conclusion**](#02d5)

## **Disclaimer (Performance & Practicality)**

**This setup is functional and stable, but on a CPU-only laptop it can be very slow!** On my Dell Latitude 7420 without a discrete GPU, many tool-driven interactions take multiple minutes per command end-to-end (LLM planning → MCP tool invocation → tool output parsing).

### **Which LLM to use?**

I tested several local models; the most reliable for HexStrike MCP tool usage in my environment were `**ollama:qwen3:14b**` and `**ollama:qwen3:8b**`. Even with these, latency remains the main limitation on CPU-only hardware.

If you want a smooth experience, I strongly recommend trying this architecture on a **system with a capable GPU** (or a dedicated inference box). For day-to-day productivity right now, I personally still prefer **large cloud models** (e.g., OpenAI / Gemini) because they are dramatically faster and more consistent for agent-style workflows.

## Why use a local LLM for pentesting?

*   **Closed/air-gapped environments**: no internet required for inference
*   **Sensitive data**: you do not send scan outputs, internal hostnames, or credentials to cloud LLMs
*   **Cost**: local inference is effectively free after hardware + power, and avoids per-token costs

## 0) Target architecture (recommended)

**Ubuntu 24.10 (host)**

*   Local LLM runtime: **Ollama** (CPU-friendly for a Latitude 7420)

**Kali Linux (VM)**

*   **hexstrike\_server** (local API server, binds to `127.0.0.1:8888` by default) ([Kali Linux](https://www.kali.org/tools/hexstrike-ai/))
*   **hexstrike\_mcp** (MCP bridge/client pointing at `http://127.0.0.1:8888`) ([Kali Linux](https://www.kali.org/tools/hexstrike-ai/))
*   SSH enabled (for secure port-forward from Ubuntu to Kali)

**Flow**  
Open WebUI (Ubuntu) → (localhost via SSH forward) → mcpo (Kali) → hexstrike\_mcp → hexstrike\_server → Kali tools

## 1) VM tuning for Dell Latitude 7420 (performance-first)

Latitude 7420 is typically CPU-bound for local LLMs (often Intel i5/i7 + integrated GPU). Optimize by **not starving the host**.

**Kali VM recommended**

*   vCPU: **2** (max 3 if you have 32GB RAM and host stays responsive)
*   RAM: **6–8 GB**
*   Disk: **40–60 GB**
*   Networking: **NAT + Host-Only** (best balance: Kali gets internet via NAT; Ubuntu can SSH via Host-Only)

Why: HexStrike can run heavy tools; keeping Kali at 2 vCPU prevents it from stealing cycles from the host LLM.

![Image](https://miro.medium.com/v2/resize:fit:700/1*PdA_2FAMUoTEwkHamX9Atg.png)

## 2) Ubuntu (host): install Ollama + pull a model

### 2.1 Install Ollama

sudo apt update  
sudo apt install -y curl  
curl -fsSL https://ollama.com/install.sh | sh

![Image](https://miro.medium.com/v2/resize:fit:700/1*2v6HvBv_itqU1VRD-IyCqQ.png)

Verify:

ollama \--version

![Image](https://miro.medium.com/v2/resize:fit:700/1*sBh84Ho6RiAjAkRfuSHWEg.png)

### 2.2 Pull a laptop-friendly model

Pick one primary model to start (faster UX):

**Good defaults for a 7420 (CPU):**

*   7–8B “instruct” / “coder” model in 4-bit quant (usually best quality/speed tradeoff)
*   If you only have 16GB RAM and want more speed: 3B–4B

Example:

ollama pull qwen3:14b  
\# or smaller:  
ollama pull qwen3:8b

![Image](https://miro.medium.com/v2/resize:fit:700/1*UTLS3B91WoZ4yTr6AbSK3A.png)

Run a quick test:

ollama run qwen3:14b "Explain what nmap -sV does in one paragraph."

![Image](https://miro.medium.com/v2/resize:fit:700/1*Y8g7V1hslZGKDY93iJitDw.png)

### 2.3 Laptop optimization (recommended defaults)

Ollama supports environment variables to control behavior (parallelism, keep-alive, etc.). [אולמה](https://docs.ollama.com/faq?utm_source=chatgpt.com)  
On a 7420-class CPU, you typically want **low parallelism** and **only one model loaded**:

export OLLAMA\_NUM\_PARALLEL=1  
export OLLAMA\_MAX\_LOADED\_MODELS=1  
export OLLAMA\_KEEP\_ALIVE=5m  
\# If you ever need a non-default bind:  
\# export OLLAMA\_HOST=127.0.0.1:11434

You can place these in `~/.bashrc` or your systemd service override, depending on how you run Ollama.

## 3) Kali VM: install and start HexStrike

HexStrike is packaged in Kali as `hexstrike-ai` with binaries `hexstrike_server` and `hexstrike_mcp`. ([Kali Linux](https://www.kali.org/tools/hexstrike-ai/))

### 3.1 Install

sudo apt update  
sudo apt install \-y hexstrike\-ai openssh\-server python3\-venv python3\-pip  
sudo systemctl enable \--now ssh

Confirm tools exist:

hexstrike\_mcp -h  
hexstrike\_server -h

![Image](https://miro.medium.com/v2/resize:fit:700/1*KJZnnlLp2poewZqk4d3aPw.png)

(These flags and defaults are documented in Kali’s package page.) ([Kali Linux](https://www.kali.org/tools/hexstrike-ai/))

### 3.2 Start HexStrike API server (binds to localhost on Kali)

Run in a dedicated terminal (or `tmux`):

hexstrike\_server \--port 8888

You should see it start on `127.0.0.1:8888`. ([Kali Linux](https://www.kali.org/tools/hexstrike-ai/))

![Image](https://miro.medium.com/v2/resize:fit:700/1*LVV55RZI-QcrrVU_la9fJg.png)

## 4) Kali VM — Networking + SSH (so Ubuntu can run HexStrike tools inside Kali)

### 4.1 VM networking recommendation

Use **two adapters** (VirtualBox/VMware both support this):

*   **NAT**: for Kali internet updates
*   **Custom** : stable IP between Ubuntu ↔ Kali

Inside Kali:

ip a

![Image](https://miro.medium.com/v2/resize:fit:700/1*w6LebpT1UBDVkAuwWuSPfg.png)

Note the **host-only** IP (example: `172.16.59.132`).

### 4.2 Enable SSH on Kali

sudo apt update  
sudo apt install \-y openssh\-server  
sudo systemctl enable \--now ssh

From Ubuntu, confirm SSH works:

ssh andrey@172.16.59.132

![Image](https://miro.medium.com/v2/resize:fit:700/1*2Qj7uyDh8SLZndzkTN05zg.png)

## 5) Host (Ubuntu) — Install `mcphost` (terminal MCP host) and wire it to HexStrike

`mcphost` is a CLI host that supports **non-interactive one-shot prompts** and **Ollama models**. [GitHub+1](https://github.com/mark3labs/mcphost)

### 5.1 Install Go + mcphost

`mcphost` requires Go (1.23+). [GitHub](https://github.com/mark3labs/mcphost)

Ubuntu:

sudo apt update  
sudo apt install -y golang-go  
go install github.com/mark3labs/mcphost@latest

Installation command is documented by the project. [GitHub](https://github.com/mark3labs/mcphost)

Ensure it’s in PATH:

export PATH="$PATH:$(go env GOPATH)/bin"  
mcphost -h

![Image](https://miro.medium.com/v2/resize:fit:700/1*-zp6omdM2HI_v9Y6cHQeeA.png)

## 6) SSH key auth (recommended) + prevent SSH banners from breaking MCP stdio

### 6.1 Set up SSH keys (Ubuntu → Kali)

On Ubuntu:

ssh-keygen -t ed25519 -C "hexstrike-kali" -f ~/.ssh/hexstrike\_kali  
ssh-copy-id -i ~/.ssh/hexstrike\_kali.pub andrey@172.16.59.132

Test:

ssh -i ~/.ssh/hexstrike\_kali andrey@172.16.59.132 "echo ok"

![Image](https://miro.medium.com/v2/resize:fit:700/1*WGcR15hfphnOYHTo7pXrSA.png)

## 6.2 Disable MOTD/banner output for this Kali user (important)

MCP stdio can break if the remote shell prints banners/MOTD before the protocol starts.

On Kali (as the andrey user):

touch ~/.hushlogin

## 7) Create the mcphost config to run HexStrike MCP remotely via SSH

`mcphost` reads `~/.mcphost.yml` (preferred) and supports `mcpServers` with `type: local` commands, plus optional tool allow/deny lists. [GitHub+1](https://github.com/mark3labs/mcphost)

On **Ubuntu**, create `~/.mcphost.yml`:

nano ~/.mcphost.yml

mcpServers:  
  hexstrike:  
    type: "local"  
    command:  
      - "ssh"  
      - "-i"  
      - "${env://HOME}/.ssh/hexstrike\_kali"  
      - "-o"  
      - "BatchMode=yes"  
      - "-o"  
      - "StrictHostKeyChecking=accept-new"  
      - "-o"  
      - "LogLevel=ERROR"  
      - "andrey@172.16.59.132"  
      - "hexstrike\_mcp"  
      - "--server"  
      - "http://127.0.0.1:8888"  
      - "--timeout"  
      - "300"

\# Optional default model (you can also pass -m each time)  
model: "ollama:qwen3:14b"

Why this works:

*   `hexstrike_mcp` defaults to `http://127.0.0.1:8888` and supports `--timeout`. [Kali Linux](https://www.kali.org/tools/hexstrike-ai/)
*   HexStrike lists common MCP tool names like `nmap_scan()`, `nuclei_scan()`, etc. [GitHub](https://github.com/0x4m4/hexstrike-ai)
*   `mcphost` supports Ollama models and can run in non-interactive mode (`-p ... --quiet`). [GitHub+1](https://github.com/mark3labs/mcphost)

### 7.1 Test it:

mcphost --debug -m ollama:qwen3:8b  
/servers  
/tools

![Image](https://miro.medium.com/v2/resize:fit:700/1*L7hFrkmDBij7g2FTP-iI4g.png)

## 8) “Like ollama run …” — one-liner usage from Ubuntu terminal

### 8.1 Plain LLM (no tools), mcphost one-liner

mcphost \--debug -m ollama:qwen3:8b -p '@hexstrike list all available tools'

![Image](https://miro.medium.com/v2/resize:fit:700/1*9kjK-2jyPOUbxIDOSi36mg.png)

### 8.2 Tool-using prompt (HexStrike via MCP)

Give the model a prompt that clearly authorizes scope and requests HexStrike tools: Simplest and fastest function

mcphost \--debug -m ollama:qwen3:14b -p '@hexstrike: You must call exactly one tool: hexstrike\_\_nmap\_scan. Scan network 192.168.1.0/24. Use minimal flags for speed (no scripts). After the tool returns, output a 2-column table: IP | Open Ports. Do not call any other tools.'

![Image](https://miro.medium.com/v2/resize:fit:700/1*aIvIkyETWgXm6Jf3SmruZQ.png)

## 9) Recommended hardening (do this)

### 9.1 Do not expose HexStrike API on the network

Keep `hexstrike_server` on loopback (`127.0.0.1`). Kali package indicates it starts there by default. [Kali Linux](https://www.kali.org/tools/hexstrike-ai/)  
You are reaching it via SSH-spawned `hexstrike_mcp`, so no port-forwarding is needed.

### 9.2 Use tool filtering once you know tool names

`mcphost` supports `allowedTools` / `excludedTools` per server. [GitHub+1](https://github.com/mark3labs/mcphost)  
After you’ve listed tools once, you can restrict what the LLM may invoke.

### 9.3 Stay current: there has been at least one published HexStrike security advisory

There are public advisories describing command-injection risk paths in HexStrike components (example: GHSA / CVE listings). Use isolation (VM), least privilege, and do not expose the API. [nvd.nist.gov+1](https://nvd.nist.gov/vuln/detail/CVE-2025-35028?utm_source=chatgpt.com)

## Conclusion

HexStrike + a local LLM is absolutely possible — but it is **highly hardware-sensitive**. On a CPU-only laptop like a Dell Latitude 7420, the workflow is technically functional yet often **impractically slow**: many “one command” actions can take **minutes end-to-end** because you pay for the entire loop every time (LLM planning → MCP tool selection → tool execution → parsing → summarization). HexStrike itself is not the bottleneck; **local inference and agent reasoning latency** is.

There is also a capability gap. Smaller local models can execute tool-driven workflows, but they are typically **less “smart” and less consistent** than large cloud models: they make more planning mistakes, are more sensitive to tool overload, and more often need stricter prompts, tool allowlists, and guardrails to avoid wasted steps. In other words, you can get it working — but you don’t get the same “agent quality” you’ll see from top-tier cloud models.

If you want this architecture to feel smooth and productive, you realistically need **strong hardware**, ideally a capable GPU (or a dedicated inference box). For day-to-day productivity today, large cloud models (OpenAI / Gemini / etc.) remain the fastest and most reliable choice for agent-style workflows. The local setup still has a clear niche — privacy, air-gapped environments, and cost control — but you should go into it with realistic expectations: **on basic hardware it will work, but it will feel slow and less intelligent** compared to big models.


## Follow for practical cybersecurity research

If you’re interested in **Offensive security,** **AI security, real-world attack simulations, CTI, and detection engineering** — this is exactly what I focus on.

Stay connected:

→ **Subscribe on Medium:** [medium.com/@1200km](https://medium.com/@1200km)  
→ **Connect on LinkedIn:** [andrey-pautov](https://www.linkedin.com/in/andrey-pautov/)  
→ **GitHub — tools & labs:** [github.com/anpa1200](https://github.com/anpa1200)  
→ **Contact:** [1200km@gmail.com](mailto:1200km@gmail.com)

### Andrey Pautov