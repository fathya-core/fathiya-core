# 🧰 My Bug Bounty Tool Stack (2026 Edition)

**Published:** 2026-02-12


![Image](https://miro.medium.com/v2/resize:fit:700/1*TGPpnLDlX3RM4_swVRzWjQ.png)

**What I Actually Use (and Why Less Beats More)**

If you’re new to this series, these posts explain _how_ I use tools — not just _which_ ones:

*   **How I Decide a Tool Result Is Worth My Time**
*   **From Signal to Impact**
*   **Authorization Is a Graph, Not a Check**
*   **Finding IDORs the Right Way (Burp-Only)**
*   **Burp Suite Repeater: How Professionals Find IDORs**
*   **403 Bypass Techniques Explained (Without Abuse)**
*   **Mastering ffuf: From Discovery to Real Bugs**
*   **nuclei Without Noise: A Practical Guide**
*   **httpx: Turning Subdomains into Attack Surface**
*   **katana vs waymore: When to Use Which**

This post is the practical snapshot of my 2026 workflow.

No hype. No “install 50 tools.”  
Just what actually earns me reports.

## 🧠 Philosophy First: Tools Don’t Find Bugs — You Do

Before the stack, the mindset:

*   Tools find **signals**
*   Humans build **impact**
*   Automation reduces noise
*   Manual testing creates value

This is the thread through the whole series.

If your stack feels overwhelming, it’s probably working against you.

## 🔍 Recon Layer

## ✅ httpx

**What I use it for:**  
Turning raw subdomains into living attack surface

*   Status codes
*   Tech stack hints
*   Redirect behavior
*   API exposure

This filters dead noise early.

→ Deep dive: _httpx: Turning Subdomains into Attack Surface_

## ✅ katana + waymore

**What I use them for (together):**

*   katana → live crawling & modern routes
*   waymore → historical endpoints, old APIs, forgotten paths

They complement each other.

→ Deep dive: _katana vs waymore: When to Use Which_

## 🔎 Discovery Layer

## ✅ ffuf

**What I use it for:**

*   Endpoint discovery
*   Parameter discovery
*   File exposure
*   Admin panels
*   Feature flags

ffuf gives me **surface area**.  
It doesn’t give me bugs.

→ Deep dive: _Mastering ffuf: From Discovery to Real Bugs_

## ✅ nuclei (carefully)

**What I use it for:**

*   Confirming known issues
*   Catching low-hanging fruit
*   Prioritizing manual testing
*   Template-driven signals

I treat nuclei as:

> _A noisy assistant, not a decision-maker._

→ Deep dive: _nuclei Without Noise: A Practical Guide_

## 🧪 Manual Testing Layer

## ✅ Burp Suite (Repeater is the core)

This is where bugs are actually found:

*   Role comparison
*   State transitions
*   IDOR testing
*   Auth bypass logic
*   API behavior differences

Repeater is my main “thinking space.”

→ Deep dives:

*   _Burp Suite Repeater: How Professionals Find IDORs_
*   _Finding IDORs the Right Way (Burp-Only)_

## 🔐 Access Control Layer

## ✅ Custom logic testing

Not a tool — a method:

*   Role switching
*   State mutation
*   Cross-feature references
*   Graph mapping

This is where:

*   Privilege escalation
*   Account takeover
*   Authorization bugs  
    actually emerge.

→ Deep dive: _Authorization Is a Graph, Not a Check_  
→ Workflow: _From Signal to Impact_

## 🧨 Exploitation Tools (Rarely, Carefully)

## ⚠️ sqlmap

I only use sqlmap when:

*   I already suspect injection
*   Manual testing shows anomalies
*   The endpoint influences queries

sqlmap is not a recon tool.  
It’s a confirmation tool.

→ Deep dive: _Why sqlmap Fails (And When It Doesn’t)_

## ⚠️ XSStrike

Occasional use when:

*   Reflection is obvious
*   Context is clear
*   I already see DOM behavior

Manual XSS testing comes first.

## 🧠 What I Don’t Use Much Anymore

Not because they’re bad — because they don’t fit my workflow:

*   Massive auto-scanners
*   Blind spraying tools
*   Huge recon frameworks
*   “One-click pwn” setups

They create noise and kill thinking.

## 🧩 The Real Stack Is a Flow, Not a List

My real stack looks like:

**httpx → katana/waymore → ffuf → nuclei (filtered) → Burp → Graph thinking → Chain building**

Tools feed thinking.  
Thinking creates bugs.

## 🏁 Final Thoughts

Your stack shouldn’t feel impressive.

It should feel **boring and effective**.

If your tools:

*   Reduce noise
*   Increase signal
*   Support manual reasoning

You’re doing it right.

If your tools replace thinking —  
you’re losing.

👏 **If this post helped, please clap** — it helps this series reach serious learners.

☕ **Support my work:**  
👉 [https://buymeacoffee.com/ghostyjoe](https://buymeacoffee.com/ghostyjoe)

## 💬 Your Turn

What tools are actually earning you reports in 2026?

*   What did you stop using?
*   What surprised you by being useful?

Drop a comment — I read them all and shape future posts around real struggles.