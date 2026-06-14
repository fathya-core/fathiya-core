# HexStrike + Cursor for OSINT: From One Email to a Full Exposure Map

**Published:** 2026-01-11


## Why OSINT is harder than “hack the box,” what an AI-assisted workflow looks like in practice, and how to publish a _real_ report without doxxing yourself or your family.


![Image](https://miro.medium.com/v2/resize:fit:700/1*nJTueyo4IxR8Nw8jYLDS-g.png)

I started OSINT on myself from a single email address. Within a short time, I could correlate a surprising amount of information.

**But OSINT is not the same game as attacking a system or a website.**

It’s slower, messier, and far more dependent on data sources (APIs, subscriptions, public indexes). It also becomes genuinely dangerous the moment you connect identity → address → family → phone → credentials. That is why this article is intentionally written as a defensive self-audit, and why some steps and sources are not described.

**OSINT also demands a specific, professional setup on Kali Linux**: properly configured OSINT tooling, clean operational workflows, and secure handling of API keys and tokens. In practice, serious investigations often require paid subscriptions to commercial data sources and breach intelligence platforms, along with carefully managed OSINT “avatars” (separate identities, browser profiles, and accounts) to reduce attribution risk and avoid contaminating results. **In other words: it’s highly effective, but it’s not out-of-the-box.**

In the examples below, **all sensitive information is masked with** `*****`. I’m keeping the methodology and report structure intact so you can reuse it safely.

## Exposed Information:


\- ✅ Full name   
\- ✅ ID number - \*\*CRITICAL PII\*\*  
\- ✅ Full residential address - \*\*CRITICAL\*\*  
\- ✅ Phone number   
\- ✅ Email address  
\- ✅ Professional information  
\- ✅ Family network   
\- ✅ Household member information   
\- ✅ Likely sibling information  
\- ✅ Digital footprint (GitHub, Medium)  
\- ✅ Professional focus and expertise

### 1) What makes OSINT harder than pentesting

In pentesting, “progress” is often technical and measurable: ports, services, versions, exploits.

In OSINT, progress is a combination of:

*   **Data availability** (and permissions)
*   **Identity ambiguity** (false positives everywhere)
*   **Correlation discipline** (how you _prove_ two data points belong to the same person)
*   **Safety constraints** (what you must never publish)

OSINT is an intelligence problem, not a tool problem.

### 2) Why Cursor + HexStrike is a strong OSINT pairing

### Cursor (the “brain”)

Cursor is where you want:

*   planning,
*   hypothesis generation,
*   correlation scoring,
*   report writing,
*   and redaction enforcement.

### HexStrike (the “hands”)

HexStrike is valuable when you need repeatable tool execution:repository footprint checks,

*   public endpoint collection,
*   crawling,
*   scripted searches across your own datasets,
*   and consistent logs.

In practice, this becomes: **Cursor reasons → HexStrike executes → Cursor explains + documents**.

## 3) Kali OSINT configuration that actually matters (and why it’s not out-of-the-box)

You already said it perfectly: OSINT is effective, but **not** “out of the box.”

### 3.1 Key management (non-negotiable)

If you use multiple services, you’ll have multiple API keys. If you don’t manage keys properly, the OSINT workstation becomes the weakest link.

**Minimum baseline:**

*   Keep keys out of shell history
*   Don’t store keys in repo files
*   Prefer `.env` locally, never committed
*   Use per-project separation (work vs personal)
*   Track what each key can access (least privilege)

**Public post rule:** never show a “working” key format, header examples, or curl commands that reveal how auth is performed. Even masked headers can leak patterns.

### 3.2 Accounts, subscriptions, and rate limits

High-signal OSINT often depends on commercial services. That means:

*   quotas,
*   rate limits,
*   **and “manual steps” that AI cannot bypass.**

Your workflow must explicitly account for “this source requires manual access / paid tier.”

### 3.3 Separate “collection” and “publishing” modes

Your Kali should have two modes:

*   **Collection mode:** full data access, full notes, strict local protection
*   **Publishing mode:** everything redacted by default, minimal retained artifacts

If you mix them, you will eventually leak something.

### 3.4 Logging controls

Treat OSINT logs as sensitive evidence:

*   record _what you did_ and _why_,
*   but don’t log raw sensitive outputs into files intended for publication.

### 4) The OSINT workflow: how AI “thinks” (the reasoning loop)

A correct AI-assisted OSINT process is not “search everything.” It’s structured intelligence:

1.  **Normalize identifiers**

*   email → usernames → linked accounts → controlled pivot list

1.  **Collect low-risk public evidence**

*   public profiles you control
*   public developer footprints
*   public author pages

**2\. Enrich**

*   breach-notification checks (defensive)
*   repository secret scanning (defensive)

**3\. Corroborate**

*   prove relationships between artifacts using multiple independent signals

**4\. Score confidence**

*   low / medium / high with reasons

**5\. Generate two deliverables**

*   internal (full)
*   public (redacted)

**6\. Redaction pass (mandatory)**

**If it’s publishable, it’s redacted**

## 5) Real report (PUBLIC / REDACTED): Exposure & Correlation Report

Below is a **more detailed** report format that includes **family, ID, phone, address** — but **all masked**.

\# Andrey Pautov: Complete Life History & Deep Investigation Report  
  
\*\*Report Date:\*\* January 2026    
\*\*Investigation Type:\*\* Comprehensive OSINT & Life History Analysis    
\*\*Classification:\*\* SENSITIVE - Contains PII    
\*\*Status:\*\* Complete  
  
\---  
  
\## EXECUTIVE SUMMARY  
  
This comprehensive report documents the complete life history and digital  
footprint of \*\*Andrey Pautov\*\* , a cybersecurity expert residing in \*\*\*,   
The investigation utilized multiple OSINT techniques, HexStrike MCP tools,  
Breached Database (founded in WEB) analysis, cross-referencing, and correlation mapping to  
build a complete timeline and profile.  
  
\*\*⚠️ IMPORTANT:\*\* This report contains sensitive personal information (PII)  
including ID numbers, addresses, phone numbers, and family relationships.   
Use responsibly and in compliance with privacy laws.  
  
\---  
  
\## CHRONOLOGICAL LIFE HISTORY  
  
\### Early Life & Background (Pre-2016)  
  
\*\*Origin & Family:\*\*  
\- \*\*Family Name:\*\* \*\*\*  
\- \*\*Family Network:\*\* \*\*\*\*  
  - \*\*\*: \* members  
  - \*\*\*: \* members    
  - \*\*\*: \* members  
\- \*\*Likely Sibling:\*\* \*\*\*  
  - Address: \*\*\*  
  - Strong evidence of sibling relationship based on sequential ID numbers  
\- \*\*Family Pattern:\*\* SequentialID numbers suggest family members registered  
 around the same period  
  
\*\*Education & Early Career:\*\*  
\- \*\*Possible Education:\*\* \*\*\*  
\- \*\*Institution:\*\*\*  
\- \*\*Note:\*\* \*\*\*  
  
\---  
  
\### 2016: Digital Footprint Begins  
  
\*\*March 25, 2016:\*\*  
\- Created GitHub account \`\*\*\*\`  
\- \*\*Account ID:\*\* \*\*\*  
\- \*\*Status:\*\* Inactive (0 public repositories)  
\- \*\*Purpose:\*\* Initial foray into public code sharing  
\- \*\*Username Pattern:\*\* "\*\*\*" - likely personal identifier or distance reference  
  
\*\*Digital Identity Formation:\*\*  
\- Established email: \`1200km@gmail.com\`  
\- Pattern: Username "\*\*\*" consistent across platforms  
\- Professional interest in cybersecurity emerging  
  
\---  
  
\### 2017-2021: Professional Development Period  
  
\*\*Professional Growth:\*\*  
\- Developing cybersecurity skills  
\- Learning security tools and techniques  
\- Building technical expertise  
\- \*\*Note:\*\* Limited public digital footprint during this period  
  
\*\*Possible Activities:\*\*  
\- Professional training and certifications  
\- Work experience in cybersecurity  
\- Building technical portfolio  
\- Learning programming languages (Python, C++, Shell)  
  
\---  
  
\### 2022: Active Professional Development  
  
\*\*December 18, 2022:\*\*  
\- Created active GitHub account \`anpa1200\`  
\- \*\*Account ID:\*\* \*\*\*  
\- \*\*Name:\*\* Andrey Pautov  
\- \*\*Bio:\*\* "Cyber security expert"  
\- \*\*Username Pattern:\*\* "anpa1200" = "Andrey Pautov 1200"   
(first 2 letters of first name + first 2 letters of last name + "1200")  
\- \*\*Purpose:\*\* Professional development and active code sharing  
  
\*\*December 26, 2022:\*\*  
\- Created first repository: \`lpi\` (Shell scripting)  
\- \*\*Language:\*\* Shell  
\- \*\*Focus:\*\* Linux Professional Institute related work  
  
\*\*Professional Focus Established:\*\*  
\- Cybersecurity expertise confirmed  
\- Active development begins  
\- Professional identity solidified  
  
\---  
  
\### 2023: Expanding Technical Portfolio  
  
\*\*February 17, 2023:\*\*  
\- Created repository: \`Networking\`  
\- \*\*Language:\*\* Python  
\- \*\*Focus:\*\* Network security and analysis  
  
\*\*October 3, 2023:\*\*  
\- Created repository: \`Malware\_analysis\`  
\- \*\*Description:\*\* "My malware analysis tools"  
\- \*\*Language:\*\* C++  
\- \*\*Focus:\*\* Malware analysis and reverse engineering  
\- \*\*Significance:\*\* Demonstrates advanced security expertise  
  
\*\*Professional Development:\*\*  
\- Expanding into malware analysis  
\- Building security tool portfolio  
\- Developing specialized expertise  
\- Active code development  
  
\---  
  
\### 2024: Active Professional Activity & Public Presence  
  
\*\*May 16, 2024:\*\*  
\- Created repository: \`WebAppPT\`  
\- \*\*Focus:\*\* Web application penetration testing  
  
\*\*September 12, 2024:\*\*  
\- Created repository: \`Coursera\`  
\- \*\*Description:\*\* "Practice account for learning MobileAppDev"  
\- \*\*Focus:\*\* Mobile app development learning  
\- \*\*Significance:\*\* Expanding skillset beyond security  
  
\*\*October 12, 2024:\*\*  
\- Created repository: \`Passwords\`  
\- \*\*Language:\*\* Python  
\- \*\*Stars:\*\* 2, \*\*Forks:\*\* 1  
\- \*\*Focus:\*\* Password security tools  
  
\*\*October 23, 2024:\*\*  
\- Created repository: \`RTSP-brute-force-tool\`  
\- \*\*Description:\*\* "RTSP Brute Force Tool: A powerful utility for security testing of RTSP services through systematic credential brute forcing, designed for ethical hacking and educational purposes."  
\- \*\*Language:\*\* Python  
\- \*\*Stars:\*\* 2  
\- \*\*Focus:\*\* Network security testing, RTSP protocol security  


\*\*2024 - Medium Publishing:\*\*  
\- Active Medium article publishing under \`@1200km\`  
\- \*\*Profile:\*\* https://medium.com/@1200km  
\- \*\*Author Name:\*\* Andrey Pautov  
\- \*\*Followers:\*\* 540+  
\- \*\*Focus:\*\* Cybersecurity, HexStrike AI, Penetration Testing  
  
\*\*Notable Articles Published:\*\*  
1. "HexStrike Cursor MCP: From Single Target to Full Subnet Compromise Lab PT Walkthrough"  
2. "HexStrike on Kali Linux 2025.4: A Comprehensive Guide"  
3. "AI-Driven Wireless Penetration Testing: One Prompt WiFi Cracking"  
4. "HexStrike AI: A Force Multiplier for Red Teams and a Dangerous Shift in the Threat Landscape"  
5. "Building an Extremely Vulnerable Ubuntu 24.04 Server Lab"  
6. "Building an Extremely Vulnerable Windows 10 Lab"  
7. "AI-Driven Exploitation of Metasploitable2: From Recon to Root"  
  
\*\*Professional Recognition:\*\*  
\- Published in AI Security Hub (https://medium.com/ai-security-hub)  
\- Following cybersecurity influencers: @taleliyahu, @infosecwriteups, @kmskrishna, @anangsha, bugbountywriteup  
\- Building professional network in cybersecurity community  
  
\*\*2024 - Personal Life:\*\*  
\- \*\*Residence:\*\* \*\*\*  
\- \*\*Household:\*\* Living with \*\*\* (same address)  
\- \*\*Relationship:\*\* Married/Partners (confirmed by same address, sequential phone numbers)  
\- \*\*Phone Number:\*\* \*\*\*  
\- \*\*Phone Pattern:\*\* Sequential with \*\*\*'s number \*\*\*) - likely registered together  
  
\---  
  
\### 2025: Continued Professional Growth  
  
\*\*April 12, 2025:\*\*  
\- Created repository: \`DataSciense\`  
\- \*\*Description:\*\* "My Data Sciense learning and projects"  
\- \*\*Language:\*\* Jupyter Notebook  
\- \*\*Focus:\*\* Data science learning and projects  
\- \*\*Significance:\*\* Expanding into data science  
  
\*\*April 17, 2025:\*\*  
\- Created three repositories on same day:  
  1. \`Basic-File-Information-Gathering-Script\`  
     - \*\*Description:\*\* "This repository contains a versatile Python script, Basic\_inf\_gathering.py, designed to automate the extraction of critical metadata and characteristics from arbitrary files. It is particularly valuable for malware analysts, digital forensics investigators, and SOC engineers who need to rapidly triage files for suspicious or malicious behavior."  
     - \*\*Language:\*\* Python  
     - \*\*Stars:\*\* 1  
  2. \`String-Analyzer-\`  
     - \*\*Description:\*\* "A powerful Python script to extract and analyze printable strings from binaries. Ideal for malware analysts, reverse engineers, and forensics investigators to uncover hidden indicators and generate AI-assisted analysis prompts."  
     - \*\*Language:\*\* Python  
  3. \`PE-Import-Analyzer\`  
     - \*\*Description:\*\* "A command-line utility to analyze the import table of PE files. Provides detailed DLL descriptions, API function explanations, and flexible output formats (HTML or plain text). Ideal for malware analysts, reverse engineers, and forensic investigators."  
     - \*\*Language:\*\* Python  
  
\*\*September 28, 2025:\*\*  
\- Created repository: \`Ansible-Capstone\`  
\- \*\*Focus:\*\* Infrastructure automation  
  
\*\*October 20, 2025:\*\*  
\- Created repository: \`SystemCheck\`  
\- \*\*Description:\*\* "Simple tool for system configuration check"  
\- \*\*Language:\*\* Python  
\- \*\*Focus:\*\* System security and configuration  
  
\*\*2025 - Current Status:\*\*  
\- \*\*Active Development:\*\* 13 public repositories  
\- \*\*Total Stars:\*\* 5  
\- \*\*Total Forks:\*\* 3  
\- \*\*Languages Used:\*\* Python, C++, Shell, Jupyter Notebook  
\- \*\*Professional Focus:\*\* Cybersecurity, malware analysis, penetration testing, digital forensics  
\- \*\*Content Creation:\*\* Active Medium publishing  
\- \*\*Location:\*\* \*\*\*  
\- \*\*Professional Status:\*\* Active cybersecurity expert  
  
\---  
  
\## COMPLETE PERSONAL PROFILE  
  
\### Identity Information  
  
\*\*Full Name:\*\*  
\- \*\*English:\*\* \*\*\*  
\- \*\*\*\*\*:\*\* \*\*\*  
\- \*\*Alternative Spellings:\*\* Andrei Pautov, Andrey Pautov  
  
\*\*\*\*\* ID Number:\*\* \*\*\* ⚠️ \*\*CRITICAL PII\*\*  
  
\*\*Date of Birth:\*\* \*\*\*  
  
\*\*Nationality:\*\* \*\*\*  
  
\*\*Location:\*\*  
\- \*\*City:\*\* \*\*\*  
\- \*\*Address:\*\* \*\*\*  
\- \*\*English Address:\*\* \*\*\*  
\- \*\*Neighborhood:\*\* \*\*\*  
\- \*\*District:\*\* \*\*\*  
\- \*\*Postal Code:\*\* \*\*\*  
  
\*\*Phone Number:\*\* \*\*\*  
\- \*\*Format:\*\* \*\*\*  
\- \*\*Type:\*\* Mobile  
\- \*\*Carrier:\*\* Not identified  
\- \*\*Pattern:\*\* Sequential with \*\*\*'s number  
\- \*\*masked\*\* --  
  
\---  
  
\### Contact Information  
  
\*\*Email Addresses:\*\*  
1. \*\*Primary:\*\* 1200km@gmail.com  
2. - \*\*masked\*\* --  
3. - \*\*masked\*\* --  


\---  
  
\### Professional Information  
  
\*\*Current Profession:\*\* Cyber Security Expert  
  
\*\*Professional Title:\*\* Cybersecurity Researcher, Penetration Tester, Security Consultant  
  
\*\*Areas of Expertise:\*\*  
\- Penetration Testing  
\- Malware Analysis  
\- Digital Forensics  
\- Network Security  
\- Binary Analysis  
\- Web Application Security  
\- AI-Powered Security Tools  
\- OSINT (Open Source Intelligence)  
\- Wireless Penetration Testing  
\- Password Recovery  
\- End-to-End Attack Chains  
\- Data Science (learning)  
\- Mobile App Development (learning)  
\- Infrastructure Automation (Ansible)  
  
\*\*Technical Skills:\*\*  
\- Python Programming  
\- C++ Programming  
\- Shell Scripting  
\- Ansible Automation  
\- Malware Analysis Tools  
\- PE File Analysis  
\- String Analysis  
\- RTSP Security Testing  
\- System Configuration  
\- Data Science (Jupyter Notebooks)  
\- Mobile App Development (learning)  
\- Golang (based on alternative profile found)  
\- Django, FastAPI, Flask  
\- PostgreSQL, Kafka, Redis  
\- Docker, Kubernetes  
  
\*\*Professional Focus:\*\*  
\- Red Team Operations  
\- AI-Driven Penetration Testing  
\- HexStrike AI Framework  
\- Practical Offensive Security Workflows  
\- Educational Security Content  
\- Security Tool Development  
  
\*\*Current Work:\*\* Not explicitly stated in public sources  
  
\*\*Professional Experience:\*\*  
\- Cybersecurity Researcher  
\- Penetration Tester  
\- Security Consultant (implied from Medium articles)  
\- Backend Engineer (alternative profile suggests fintech, HR tech, medical industries experience)  
  
\*\*Notable Projects:\*\*  
\- HexStrike AI Framework development  
\- Multiple security tool repositories (13 total)  
\- Educational security content creation  
\- Malware analysis tools  
\- Digital forensics tools  
\- Web application penetration testing tools  
  
\*\*Professional Publications:\*\*  
\- Medium blog (@1200km) with multiple cybersecurity articles  
\- GitHub repositories with security tools  
\- Educational lab write-ups  
\- AI Security Hub publications  
  
\*\*GitHub Activity Summary:\*\*  
\- \*\*Total Repositories:\*\* 13  
\- \*\*Total Stars:\*\* 5  
\- \*\*Total Forks:\*\* 3  
\- \*\*Languages:\*\* Python (primary), C++, Shell, Jupyter Notebook  
\- \*\*Most Active Period:\*\* 2024-2025  
\- \*\*Focus:\*\* Security tools, malware analysis, forensics  
  
\---  
  
\### Digital Presence  
  
\#### GitHub Profiles  
  
\*\*1. Primary Account: anpa1200\*\*  
\- \*\*URL:\*\* https://github.com/anpa1200  
\- \*\*Account Created:\*\* December 18, 2022  
\- \*\*Status:\*\* Active  
\- \*\*User ID:\*\*   
\- \*\*Name:\*\* Andrey Pautov  
\- \*\*Bio:\*\* "Cyber security expert"  
\- \*\*Location:\*\* Not specified  
\- \*\*Public Repositories:\*\* 13  
\- \*\*Public Gists:\*\* 0  
\- \*\*Followers:\*\* 3  
\- \*\*Following:\*\* 0  
\- \*\*Organizations:\*\* None  
  
\*\*Repositories (Chronological):\*\*  
1. \*\*lpi\*\* (2022-12-26) - Shell scripting  
2. \*\*Networking\*\* (2023-02-17) - Python, network security  
3. \*\*Malware\_analysis\*\* (2023-10-03) - C++, malware analysis tools  
4\. \*\*WebAppPT\*\* (2024-05-16) - Web application penetration testing  
5\. \*\*Coursera\*\* (2024-09-12) - Mobile app development learning  
6\. \*\*Passwords\*\* (2024-10-12) - Python, password security tools  
7\. \*\*RTSP-brute-force-tool\*\* (2024-10-23) - Python, RTSP security testing  
8\. \*\*DataSciense\*\* (2025-04-12) - Jupyter Notebook, data science  
9\. \*\*Basic-File-Information-Gathering-Script\*\* (2025-04-17) - Python, file analysis  
10\. \*\*String-Analyzer-\*\* (2025-04-17) - Python, binary string analysis  
11\. \*\*PE-Import-Analyzer\*\* (2025-04-17) - Python, PE file analysis  
12\. \*\*Ansible-Capstone\*\* (2025-09-28) - Infrastructure automation  
13\. \*\*SystemCheck\*\* (2025-10-20) - Python, system configuration  
  
\*\*2. Secondary Account: 1200km\*\*  
\- \*\*URL:\*\* https://github.com/1200km  
\- \*\*Account Created:\*\* March 25, 2016  
\- \*\*Status:\*\* Inactive  
\- \*\*User ID:\*\* 18067032  
\- \*\*Public Repositories:\*\* 0  
\- \*\*Public Gists:\*\* 0  
\- \*\*Followers:\*\* 0  
\- \*\*Following:\*\* 0  
  
\*\*GitHub Followers:\*\*  
  
\#### Medium Profile  
  
\*\*Profile:\*\* @1200km  
\- \*\*URL:\*\* https://medium.com/@1200km  
\- \*\*Author Name:\*\* Andrey Pautov  
\- \*\*Status:\*\* Active  
\- \*\*Followers:\*\* 540+  
\- \*\*Focus:\*\* Cybersecurity, HexStrike AI, Penetration Testing  
  
\*\*Notable Articles:\*\*  
1\. "HexStrike Cursor MCP: From Single Target to Full Subnet Compromise Lab PT Walkthrough"  
2\. "HexStrike on Kali Linux 2025.4: A Comprehensive Guide"  
3\. "AI-Driven Wireless Penetration Testing: One Prompt WiFi Cracking"  
4\. "HexStrike AI: A Force Multiplier for Red Teams and a Dangerous Shift in the Threat Landscape"  
5\. "Building an Extremely Vulnerable Ubuntu 24.04 Server Lab"  
6\. "Building an Extremely Vulnerable Windows 10 Lab"  
7\. "AI-Driven Exploitation of Metasploitable2: From Recon to Root"  
  
\*\*Publications:\*\*  
\- AI Security Hub (https://medium.com/ai-security-hub)  
  
\*\*Following:\*\*  
\- @taleliyahu  
\- @infosecwriteups  
\- @kmskrishna  
\- @anangsha  
\- bugbountywriteup  
  
\#### LinkedIn  
  
\*\*Status:\*\* Not found in public searches  
\- Profile may exist but not publicly discoverable  
\- May use privacy settings  
\- May use different name variation  
  
\*\*Recommendation:\*\* Manual LinkedIn search required  
  
\#### Personal Site/Blog  
  
\*\*Primary Blog:\*\* Medium (@1200km)  
\- \*\*URL:\*\* https://medium.com/@1200km  
\- \*\*Focus:\*\* Cybersecurity, penetration testing, security tools  
\- \*\*Content Type:\*\* Educational articles, lab write-ups, tool guides  
  
\*\*Alternative Profile Found:\*\*  
\- \*\*Contra Profile:\*\* https://contra.com/andrey\_pautov  
\- \*\*Type:\*\* Professional portfolio  
\- \*\*Status:\*\* Active  
  
\*\*Domain:\*\*  
\- \*\*1200km.com:\*\* Not currently registered  
\- \*\*Historical Subdomains Found:\*\*  
  - - \*\*masked\*\* --  
  - - \*\*masked\*\* --  
  - - \*\*masked\*\* --  
  
\#### Social Media  
  
\*\*Facebook:\*\*  
\- \*\*Status:\*\* - \*\*masked\*\* --  
  
\*\*Instagram:\*\*  
\- \*\*Status:\*\* - \*\*masked\*\* --  


\*\*Twitter/X:\*\*  
\- \*\*Status:\*\* Not found in public searches  
\- \*\*Recommendation:\*\* Manual search required  
  
\*\*Other Platforms:\*\*  
\- \*\*TikTok:\*\* Not found  
\- \*\*YouTube:\*\* - \*\*masked\*\* --  
\- \*\*Reddit:\*\* Not found  
  
\---  
  
\### Family Information  
  
\#### Wife/Partner  
  
\*\*Name:\*\* - \*\*masked\*\* --  
  
\*\*Full Details:\*\*  
\- \*\*ID Number:\*\* - \*\*masked\*\* -- ⚠️ \*\*CRITICAL PII\*\*  
\- \*\*Address:\*\*- \*\*masked\*\* -- (Same address as Andrey)  
\- \*\*Phone Number:\*\* - \*\*masked\*\* --  
\- \*\*Status:\*\*- \*\*masked\*\* --  
\- \*\*Relationship:\*\* Wife/Partner (confirmed by same address, sequential phone numbers)  


\*\*Digital Presence:\*\*  
\- \*\*Email:\*\*- \*\*masked\*\* --  
\- \*\*LinkedIn:\*\* - \*\*masked\*\* --  
\- \*\*Social Media:\*\* - \*\*masked\*\* --  
\- \*\*Personal Site:\*\* - \*\*masked\*\* --  
  
\#### Children  
  
\*\*Status:\*\* - \*\*masked\*\* --  
  
\#### Extended Family  
\- \*\*masked\*\* -  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\---  
  
\### Location & Address Details  
\- \*\*masked\*\* --  
\---  
  
\### Username & Digital Identity Patterns  
  
\*\*Usernames:\*\*  
\- 1200km (GitHub, Medium, Email)  
\- anpa1200 (GitHub - active)  
\- @1200km (Medium)  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  


\*\*Username Pattern Analysis:\*\*  
\- "anpa1200" = "Andrey Pautov 1200" (first 2 letters of first name + first 2 letters of last name + "1200")  
\- "1200km" = likely related to distance or personal identifier  
\- "1200" consistent across all platforms ✅  
  
\*\*Email Pattern:\*\*  
\- 1200km@gmail.com (matches username pattern)  
  
\---  
  
\### Data Breach Exposure  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
  
\*\*Other Breach Databases:\*\*  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
  
\---  
  
\## CROSS-REFERENCE & CORRELATION ANALYSIS  
  
\### Data Point Correlations  
  
\*\*1\. EMAIL PATTERN:\*\*  
\- Email: 1200km@gmail.com  
\- Username: '1200km'  
\- GitHub: 'anpa1200' (an + pa + 1200)  
\- Medium: '@1200km'  
\- Pattern: '1200' consistent across all platforms ✅  
  
\*\*2\. ID NUMBER CORRELATION:\*\*  
\- Andrey ID: - \*\*masked\*\* --  
\- - \*\*masked\*\* -- ID: - \*\*masked\*\* --  
\- Difference: - \*\*masked\*\* --  
\- Analysis: Different registration periods, likely different ages  
\- - \*\*masked\*\* -- ID: (only 15 digits away - likely sibling)  
  
\*\*3\. PHONE NUMBER CORRELATION:\*\*  
\- Andrey: - \*\*masked\*\* --  
\- - \*\*masked\*\* --  
\- Pattern: Sequential numbers  
\- Analysis: Likely registered together, same carrier/plan ✅  
  
\*\*4\. ADDRESS CORRELATION:\*\*  
\- - \*\*masked\*\* --  
\- Both Andrey and - \*\*masked\*\* -- registered at same address ✅  
\- Location: - \*\*masked\*\* --  
  
\*\*5\. DIGITAL FOOTPRINT CORRELATION:\*\*  
\- GitHub accounts: 2  
\- Active account: anpa1200 (13+ repositories)  
\- Inactive account: 1200km (0 repositories)  
\- Medium: Active publishing  
\- Professional focus: Cybersecurity/Security tools ✅  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
  
\*\*6\. FAMILY CORRELATION:\*\*  
\- - \*\*masked\*\* -- ✅  
\- - \*\*masked\*\* --✅  
\- - \*\*masked\*\* -- ✅  
  
\*\*7\. PROFESSIONAL CORRELATION:\*\*  
\- GitHub repos: 13 security-focused repositories  
\- Medium articles: Cybersecurity content  
\- Professional focus: Consistent ✅  
  
\*\*8\. TEMPORAL CORRELATION:\*\*  
\- 2016: GitHub account '1200km' created  
\- 2022: GitHub account 'anpa1200' created (more active)  
\- 2024-2025: Active Medium publishing  
\- Evolution: Professional development visible ✅  
  
\---  
  
\## RISK ASSESSMENT  
  
\*\*Privacy Exposure Level:\*\* \*\*CRITICAL\*\* ⚠️  
  
\*\*Exposed Information:\*\*  
\- ✅ Full name   
\- ✅ ID number - \*\*CRITICAL PII\*\*  
\- ✅ Full residential address - \*\*CRITICAL\*\*  
\- ✅ Phone number   
\- ✅ Email address (1200km@gmail.com)  
\- ✅ Professional information  
\- ✅ Family network   
\- ✅ Household member information   
\- ✅ Likely sibling information  
\- ✅ Digital footprint (GitHub, Medium)  
\- ✅ Professional focus and expertise  
  
\*\*Attack Vectors Enabled:\*\*  
1\. Identity theft (ID number exposure)  
2\. Physical stalking (address exposure)  
3\. Phone-based attacks (SIM swap, phishing)  
4\. Social engineering (family network exposure)  
5\. Targeted phishing (professional focus known)  
6\. Professional targeting (expertise known)  
7\. Family member targeting (extended family identified)  


\## INVESTIGATION METHODOLOGY  
  
\### Tools & Techniques Used  
  
\*\*HexStrike MCP Tools:\*\*  
\- Nuclei vulnerability scanning  
\- HTTPX probing  
\- Subfinder subdomain enumeration  
\- Amass domain enumeration  
\- Waybackurls historical URL discovery  
\- Hakrawler web crawling  
\- Katana crawling  
\- Dirsearch directory scanning  
\- Arjun parameter discovery  
\- Nmap port scanning  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
  
\*\*OSINT Techniques:\*\*  
\- GitHub API analysis  
\- Medium profile analysis  
\- Elector database search  
\- Cross-referencing and correlation  
\- Pattern analysis  
\- Timeline construction  
\- Family network mapping  
  
\*\*Data Sources:\*\*  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- \*\*masked\*\* --  
\- GitHub API  
\- Medium Profile  
\- Web Search Engines  
\- Public Records  
  
\---  

## Finding 1 — Identity correlation is possible from minimal starting data

**Input:** one email address  
**Output:** a mapped set of handles, accounts, and cross-platform identity signals

**Confidence:** High  
**Why:** Multiple independent signals converged (account linking, consistent handle usage, content alignment)

## Finding 2 — Real-world identifiers are the highest-risk exposure category

**Observed data types (masked):**

*   government ID
*   phone number
*   residential address
*   family/household relationships

**Risk:** Critical  
**Reason:** These enable impersonation, targeted fraud, and physical risk escalation

## Finding 3 — Credential exposure checks**Result summary (public-safe):**

*   No confirmed passwords recovered via automated portion
*   No confirmed API keys identified in public repo surface review
*   Some sources require authentication/subscriptions for full coverage

**Confidence:** Medium  
**Why:** Lack of visibility into private repos + paid sources limitations

### Risk Assessment (Public Version)

### Overall exposure level: CRITICAL

Because the profile contains (even if partially discoverable):

*   identity + phone + address + family links

### Likely attack paths enabled

1.  Targeted phishing (high confidence personalization)
2.  SIM swap attempts (phone-based leverage)
3.  Account recovery abuse (“support desk” social engineering)
4.  Identity misuse (government ID)
5.  Physical safety risk (address)

## Recommendations (Defensive)

### Immediate

*   Enable strongest MFA possible on email and primary accounts
*   Add SIM swap protection / carrier port-out PIN
*   Review public profiles for accidental disclosures
*   Rotate API keys as a precaution (even if not found)

### Short-term

*   Run deep secret scans on repos (including commit history)
*   Remove old exposed artifacts
*   Create “public-safe” contact methods (separate email / alias)

### Ongoing

*   Periodic exposure monitoring (quarterly cadence)
*   Family awareness: basic anti-phishing and privacy hygiene

## Conclusion

OSINT is not “one tool.” It’s disciplined correlation under safety constraints. Cursor + HexStrike is powerful because it can execute repeatable collection steps while maintaining a consistent reasoning and reporting layer — but the operator must enforce ethical boundaries and redaction.