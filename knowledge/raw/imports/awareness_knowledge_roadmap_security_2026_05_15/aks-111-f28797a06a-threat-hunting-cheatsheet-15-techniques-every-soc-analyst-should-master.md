# Threat Hunting Cheatsheet: 15 Techniques Every SOC Analyst Should Master

**Published:** 2026-03-30


Ever felt like you’re only reacting to alerts — meanwhile real threats slip by as “noise”? Here’s something wild: over 50% of successful breaches go undetected for months, sometimes years. Most SOC analysts are armed with dashboards, scripts, and logs… but not always with a battle-tested threat hunting mindset. Let’s change that, right now.

Ready to move from overwhelmed to in-control? Here’s a step-by-step cheatsheet: 15 actionable threat hunting techniques every analyst should know. Whether you’re deep into pentesting, chasing privilege escalation, reverse engineering malware, or just love bug bounty stories — this is your practical guide. No fluff. Just real-world tactics and code you can use starting today.

![Image](https://miro.medium.com/v2/resize:fit:700/0*3uGmkxduAkaa_Hsa)

*Photo by RoonZ nl on Unsplash*

### Why Threat Hunting Matters (And Why Most Teams Get It Wrong)

You might think, “We have SIEM, EDR, and a stack of tools — why hunt?” In practice, here’s what really happens: attackers know your tools. They blend in, use living-off-the-land binaries (LOLBins), or hijack normal behavior. Automated alerts only catch the obvious stuff.

Threat hunting isn’t about waiting for the “red light” to flash. It’s a proactive search for signs of compromise, misconfigurations, and subtle indicators attackers hope you’ll miss. The cool part? You get to think like an adversary. And when you do it right, you spot attacks that even the best tools can’t.

### Baseline User and System Behavior

Before you can spot “weird,” you gotta know what “normal” looks like.

### Step-by-Step

1.  **Collect logs:** Pull Windows Event Logs, Linux syslogs, authentication logs, etc.
2.  **Profile users:** Who logs in where, when? Which devices?
3.  **Profile systems:** Usual running processes, scheduled tasks, and network connections.

### Code Example: Baseline Logins

### \# PowerShell: Get most common login hours for all users  
Get-EventLog -LogName Security -InstanceId 4624 |  
Group-Object {$\_.ReplacementStrings\[5\]} | Select-Object Name, Count | Sort-Object Count -Descendin  


Why it matters: An attacker often logs in at odd hours or from weird locations. But unless you know the usual patterns, you’ll never catch it. I’ve seen pentests where this alone flagged initial access.  
  
2\. Hunt for Suspicious PowerShell Usage

Attackers love PowerShell for privilege escalation, lateral movement, and malware droppers. Most defenders overlook it.

### How To

*   **Look for encoded commands:** Legit admins rarely use `-EncodedCommand`.
*   **Scan for network calls:** Exfiltration or C2 traffic uses `Invoke-WebRequest`, `Invoke-Expression`, etc.
*   **Check child process creation:** PowerShell launching `cmd.exe`, `mshta.exe`, or `rundll32.exe`? Bad sign.

### Code Example: Encoded PowerShell Command Detection

\# Splunk SPL  
index=wineventlog EventCode=4104 OR EventCode=4688  
| search CommandLine="\*EncodedCommand\*"

### 3\. Identify Living-off-the-Land Binaries (LOLBins)

LOLBins are legit tools attackers hijack for evil: `certutil.exe`, `wmic.exe`, `bitsadmin.exe`, etc.

### Practical Steps

1.  **Inventory all LOLBin usage across endpoints.**
2.  **Correlate with user context:** Is `certutil.exe` running under a service account that never uses it?
3.  **Flag network activity:** LOLBins downloading files? Rarely normal.

### LOLBin Example: Certutil Download

\# Hunt for suspicious certutil downloads  
index=wineventlog EventCode=4688   
| search CommandLine="\*certutil\*urlcache\*"

**Pro tip:** Many ransomware crews drop payloads this way. Flag early, sleep better.

### 4\. Track Lateral Movement via Service Creation

Attackers often move laterally by creating remote services (\`sc.exe\`, WMI, PsExec).


*   **Look for Service Control activity (\`sc.exe\`)**
*   **Monitor for Windows Event IDs:**
*   4697: Service installed
*   7045: New service created

### Example: Detect PsExec Lateral Movement

\# Splunk SPL for new service creation (common with PsExec)  
index=wineventlog (EventCode=4697 OR EventCode=7045)  
| search ServiceFileName="\*PSEXESVC\*"

You’ll spot pentesters and attackers moving sideways, clear as day.

### 5\. Detect Credential Dumping Attempts

Credential theft = game over. Attackers use `lsass.exe`, `procdump.exe`, `mimikatz`, and friends.

### Steps

1.  **Watch for access to LSASS process.**
2.  **Check for suspicious tools executed by non-admin users.**
3.  **Correlate with dump file creation in temp locations.**

### Code Example: LSASS Access

\# Sysmon event for process access (Event ID 10)  
index=sysmon EventCode=10 TargetImage="\*lsass.exe\*"  
| stats count by SourceImage, User, Computer

**In real-world hunts, most legit users never touch LSASS. If you see it, dig in.**

### 6\. Search for Persistence via Scheduled Tasks

Persistence is how attackers survive reboots. Scheduled tasks are a classic (and overlooked!) method.

### What to Look For

*   Unusual task names (random strings, disguised as system tasks)
*   Tasks running from temp folders or user profiles
*   Creation time outside patch windows

### Example: Find Weird Tasks

\# PowerShell: List tasks not in standard Windows paths  
Get-ScheduledTask | Where-Object { $\_.TaskPath -notlike '\\Microsoft\*' }

### 7\. Hunt for Abnormal Network Connections

Attackers need C2. They often use rare ports, foreign IPs, or direct connections that don’t fit the baseline.

### Quick Wins

*   Flag outbound connections to:
*   IPs not seen in last 30 days
*   Non-standard ports (like 8080, 8443, 53)
*   Dynamic DNS (No-IP, DuckDNS, etc.)

### Code Example: New External IPs

\# Zeek/Bro conn.log  
cat conn.log | awk '{print $3}' | sort | uniq -c | sort -n

I’ve caught beaconing malware just by watching for “new” connections that nobody could explain.

### 8\. Trace Phishing Delivery and Malicious Attachments

Phishing is the #1 entry point, period. Once a user clicks, the payload drops — often with RCE or macro-based initial access.


1.  **Search mail logs for mismatched sender domains.**
2.  **Correlate with endpoint events (macro execution, script drops).**
3.  **Flag executable attachments (\`.exe\`,** `**.js**`**,** `**.vbs**`**).**

### Example: Suspicious Macro Execution

\# Windows Event ID 300 (Office macro execution)  
index=wineventlog EventCode=300  
| search FileName="\*.doc\*" CommandLine="\*powershell\*"

### 9\. Analyze Web Shell Activity on Servers

Compromised web servers often hide web shells — think SQLi, RCE, and file uploads.

### How To Spot Web Shells

*   Unusual file names in web root (\`cmd.aspx\`, `1.php`, `shell.jsp)`
*   Scripts that suddenly appear, especially after SQLi or upload events
*   HTTP requests with suspicious parameters (\`cmd=\`, `exec=`, base64 blobs)

### Quick Web Shell Hunt

\# Linux: Find recent PHP files not owned by webadmin  
find /var/www -name '\*.php' -mtime -2 ! -user webadmin

### 10\. Watch for Suspicious Parent-Child Process Chains

Legit processes rarely spawn odd pairs. Word launching PowerShell? Suspicious. Service Host spawning cmd? Worth a look.


1.  **Collect process creation logs (Sysmon Event ID 1).**
2.  **Map parent-child relationships.**
3.  **Flag uncommon/rare pairs.**

### Example: Word Spawns PowerShell

\# Sysmon hunt: winword.exe -> powershell.exe  
index\=sysmon EventCode=1 ParentImage="\*winword.exe\*" Image="\*powershell.exe\*"

### 11\. Find Privilege Escalation Attempts

Attackers rarely settle for low-privs. They’ll poke for kernel exploits, misconfigurations, or relay attacks.

### What to Check

*   Use of tools like `whoami`, `net localgroup administrators`
*   Write attempts to protected areas (e.g., System32)
*   Scheduled task or service installs by non-admins

### Example: Local Admin Group Changes

\# Windows Event 4732 (user added to local admin)  
index\=wineventlog EventCode=

Every time a pentester pops a box, adding their user to admin is still a favorite.

### 12\. Detect Unusual File and Registry Activity

Malware needs to write, modify, or read files/registry keys to persist or escalate.


*   Watch for creation of executables in temp/user folders
*   Registry writes to `HKLM\Software\Microsoft\Windows\CurrentVersion\Run`

### Example: Find New EXEs in Temp

\# PowerShell: List all .exe files created last 24h in temp  
Get-ChildItem $env:TEMP -Recurse -Filter \*.exe | Where-Object { $\_.CreationTime -gt (Get-Date).AddDays(-1) }

### 13\. Monitor Cloud and SaaS Anomalies

Attackers adapt. Now, they brute-force cloud creds, abuse OAuth, or exfil via Google Drive.


1.  **Check for new, unrecognized cloud logins.**
2.  **Flag mass permission changes or new API tokens.**
3.  **Watch for data spikes (downloads/uploads) outside normal hours.**

### Example: Azure/M365 Sign-in Anomalies

\# Azure Sentinel KQL: Impossible travel  
SigninLogs  
| where Location != PreviousLocation  
| summarize count() by UserPrincipalName, Location, PreviousLocatio  

### 14\. Correlate Multiple Weak Signals

One odd event? Maybe nothing. Three weak signals together? Now you’re onto something.


*   **Link multiple events for the same user/device:** Odd login **plus** rare process **plus** external connection.
*   **Build timelines:** Sequence events to spot patterns attackers try to hide.

### Real Story

On an actual hunt, I once flagged a user for a 3AM login. Alone, it looked like a false positive. But add a new scheduled task and outbound connection to Russia — suddenly, it made sense. It was a targeted intrusion.

### 15\. Automate and Iterate Your Hunts

Manual is good for learning, but automation scales your reach.


1.  **Script repeatable hunts.**
2.  **Use open-source frameworks (Sigma, MITRE ATT&CK, HELK).**
3.  **Continuously tune based on new TTPs (tactics, techniques, procedures).**

### Example: Sigma Rule for Encoded PowerShell

title: Encoded PowerShell Command  
logsource:  
    product: windows  
    service: security  
detection:  
    selection:  
        CommandLine|contains: '-encodedcommand'  
    condition: selection  
level: high

Plug Sigma rules into your SIEM — suddenly your playbook runs 24/7. The best part? You get notified, not overwhelmed.

### Wrapping Up — Your New Threat Hunting Arsenal

There you have it — 15 threat hunting techniques that turn you from a “reactive” analyst into a proactive hunter. This isn’t just about better dashboards or more noisy alerts. It’s about shifting your mindset: always ask, “What would I do if I were an attacker?”

Threat hunting takes patience and a healthy dose of curiosity. Not every hunt finds gold, but every hunt teaches you something — about your environment, your team, and, honestly, yourself.

If you’re in a SOC, deep into pentesting, or just love the chase — these methods will save you time, catch threats earlier, and make you way more effective. Master these, and you’ll be the analyst everyone wants on their incident response war room.

Ready to hunt? Your adversaries hope you won’t.

**Want more actionable guides and cheatsheets? Follow @verylazytech on Medium for fresh, field-tested cybersecurity tactics.**

### 🚀 Become a VeryLazyTech Member — Get Instant Access

What you get today:

✅ **70GB Google Drive** packed with cybersecurity content

✅ **3 full courses** to level up fast

👉 **Join the Membership** → [https://shop.verylazytech.com](https://shop.verylazytech.com)

### 📚 Need Specific Resources?

✅ Instantly download the **best hacking guides, OSCP prep kits, cheat sheets, and scripts** used by real security pros.

👉 **Visit the Shop** → [https://shop.verylazytech.com](https://shop.verylazytech.com)

### 💬 Stay in the Loop

Want quick tips, free tools, and sneak peeks?

✖ [https://x.com/verylazytech/](https://x.com/verylazytech/)

| 👾 [https://github.com/verylazytech/](https://github.com/verylazytech/)

| 📺 [https://youtube.com/@verylazytech/](https://youtube.com/@verylazytech/)

| 📩 [https://t.me/+mSGyb008VL40MmVk/](https://t.me/+mSGyb008VL40MmVk/)

| 🕵️‍♂️ [https://www.verylazytech.com/](https://www.verylazytech.com/)