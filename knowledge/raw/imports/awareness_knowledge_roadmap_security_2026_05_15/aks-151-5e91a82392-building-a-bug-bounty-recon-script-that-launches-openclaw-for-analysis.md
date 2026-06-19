# 🦞⚡ Building a Bug Bounty Recon Script That Launches OpenClaw for Analysis

**Published:** 2026-03-06


![Image](https://miro.medium.com/v2/resize:fit:700/1*ybgRmPDP8RMCXkhHVOLD1A.png)

Bug bounty recon can quickly become chaotic.

At the beginning, the workflow feels manageable:

*   run a few enumeration tools
*   collect some URLs
*   fuzz a few endpoints
*   check some technologies

But once you start scanning larger programs, things begin to spread everywhere.

Subdomains in one folder.  
Screenshots somewhere else.  
URLs mixed with notes.  
Nuclei results buried in another directory.

Eventually you realize something frustrating:

You **did collect useful data**, but reviewing it becomes harder than collecting it.

That is the problem I wanted to solve.

Instead of running tools randomly, I built a **structured recon workflow script** that automates the repetitive parts and organizes the output.

Then I added **OpenClaw**, which launches automatically at the end of the scan to help review the collected data.

The result is a workflow that moves cleanly from **recon → organization → analysis**.

## 🚀 The Recon Workflow

The script runs a full reconnaissance pipeline in a structured order.

It includes:

*   Subdomain enumeration
*   Live host detection
*   Historical URL collection
*   Crawling
*   Port scanning
*   Technology detection
*   Content discovery
*   Screenshot capture
*   Vulnerability scanning
*   Automated reporting

Instead of juggling multiple terminals, everything runs through a single workflow.

![Image](https://miro.medium.com/v2/resize:fit:700/0*0IQOTsaHP52UWlft.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*29CBva0e_zQYxy7N.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*j5Roukk0UUCUdrAh.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*e4BFeG-YvKtX5Z17.png)

_Running the recon workflow from a single command._

## 🔎 Watching the Pipeline Execute

As the script runs, each stage of recon appears clearly in the terminal.

Typical stages include:

*   Subdomain enumeration
*   Live host detection
*   Katana crawling
*   Naabu port scanning
*   Nmap service discovery
*   Nuclei vulnerability scanning

Because everything runs sequentially, the workflow stays organized.

![Image](https://miro.medium.com/v2/resize:fit:700/0*ybEHE2-F-9ObbfHN.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*3eMQabj0-TqOX5CV.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*l7UClvmHPl9-QEg4.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*PpEyu2eoiwBRT_t2.png)

_Each recon stage executes in sequence._

## 📂 Clean Output Structure

Each run creates a structured output directory.

Instead of scattered files, results are stored like this:

recon\_target.com  
 ├─ subdomains  
 ├─ alive  
 ├─ urls  
 ├─ ports  
 ├─ technologies  
 ├─ screenshots  
 ├─ vulnerabilities  
 └─ report

![Image](https://miro.medium.com/v2/resize:fit:700/0*CbRsj_i9-_1CmeWn.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*0ucQx1iENptV1cRz)![Image](https://miro.medium.com/v2/resize:fit:700/0*Wde5Mm1Jii7Q9AOu.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*6CuqJzwPvoqTa4Jy.jpg)

_A structured folder layout makes reviewing recon much easier._

## 📸 Visual Recon with Screenshots

Visual reconnaissance is incredibly useful.

Using **gowitness**, the script captures screenshots of every discovered web application.

This quickly reveals:

*   login portals
*   admin dashboards
*   staging environments
*   forgotten services

![Image](https://miro.medium.com/v2/resize:fit:700/0*NwDH9OVO8EQYAP-W.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*VneOeQx9TbbqzXoI.png)

_Screenshots make it easier to visually map the attack surface._

## 🦞 Where OpenClaw Changes the Workflow

Collecting recon data is only half the job.

The second half is reviewing it without getting overwhelmed.

That is where **OpenClaw** fits into the process.

Once the recon script finishes, OpenClaw launches automatically.

![Image](https://miro.medium.com/v2/resize:fit:700/0*nk2nBwM3YchxMrtS)![Image](https://miro.medium.com/v2/resize:fit:700/0*WkNELxGtE3SmfklP.gif)![Image](https://miro.medium.com/v2/resize:fit:700/0*fzq0KdtZDZ2B1Kl_.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*OvTia0tvqoSgoDAd)

_OpenClaw launches after recon to help review the results._

## 🧠 Reviewing the Results

With OpenClaw running, the workflow shifts from **collection to analysis**.

Instead of manually reading dozens of files, it becomes easier to:

*   summarize recon findings
*   review scan results
*   identify interesting endpoints
*   organize notes
*   plan manual testing

![Image](https://miro.medium.com/v2/resize:fit:700/0*1qB0e5TBmabRChm-)![Image](https://miro.medium.com/v2/resize:fit:700/0*mrF2pgwVaTdhFoZl.jpg)![Image](https://miro.medium.com/v2/resize:fit:700/0*0inYaVvuN1YKTMeW)

_Recon collection first, analysis second._

## 💾 Installing the Script

Save the script:

nano recon\_openclaw.sh

Make it executable:

chmod +x recon\_openclaw.sh

Run a scan:

./recon\_openclaw.sh example.com

Run a scan and launch OpenClaw automatically:

./recon\_openclaw.sh --with-openclaw example.com

## 🧰 The Full Script

Below is the full script used in this workflow.

#!/usr/bin/env bash

set -eTARGET=$1  
USE\_OPENCLAW=0if \[\[ "$1" == "--with-openclaw" \]\]; then  
    USE\_OPENCLAW=1  
    TARGET=$2  
fiif \[\[ -z "$TARGET" \]\]; then  
    echo "Usage:"  
    echo "./recon\_openclaw.sh example.com"  
    echo "./recon\_openclaw.sh --with-openclaw example.com"  
    exit  
fiTS=$(date +"%Y%m%d\_%H%M%S")  
OUT="recon\_$TARGET\_$TS"mkdir -p $OUT/{subdomains,alive,urls,ports,technologies,screenshots,vulnerabilities,report}echo "Starting recon for $TARGET"subfinder -d $TARGET -silent > $OUT/subdomains/subfinder.txt  
assetfinder --subs-only $TARGET >> $OUT/subdomains/assetfinder.txtcat $OUT/subdomains/\*.txt | sort -u > $OUT/subdomains/all.txthttpx -l $OUT/subdomains/all.txt -silent -title -tech-detect -o $OUT/alive/alive.txtgau --subs $TARGET > $OUT/urls/gau.txt  
waybackurls $TARGET > $OUT/urls/wayback.txtcat $OUT/urls/\*.txt | sort -u > $OUT/urls/all\_urls.txtkatana -list $OUT/alive/alive.txt -o $OUT/urls/katana.txtnaabu -list $OUT/alive/alive.txt -o $OUT/ports/naabu.txtnmap -iL $OUT/alive/alive.txt -oN $OUT/ports/nmap.txtwhatweb -i $OUT/alive/alive.txt > $OUT/technologies/whatweb.txtwhile read url; do  
    ffuf -u $url/FUZZ \\  
    -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \\  
    -o $OUT/vulnerabilities/ffuf\_$(echo $url | tr '/' '\_').json  
done < $OUT/alive/alive.txtgowitness file -f $OUT/alive/alive.txt --destination $OUT/screenshotsnuclei -l $OUT/alive/alive.txt -o $OUT/vulnerabilities/nuclei.txtwhile read url; do  
    nikto -h $url -output $OUT/vulnerabilities/nikto\_$(echo $url | tr '/' '\_').txt  
done < $OUT/alive/alive.txtecho "Bug Bounty Recon Report" > $OUT/report/report.md  
echo "Target: $TARGET" >> $OUT/report/report.md  
echo "Date: $TS" >> $OUT/report/report.mdif \[\[ $USE\_OPENCLAW -eq 1 \]\]; then  
    openclaw  
fiecho "Recon complete. Results saved in $OUT"

## 📋 Quick Cheat Sheet

chmod +x recon\_openclaw.sh

./recon\_openclaw.sh example.com./recon\_openclaw.sh --with-openclaw example.com./recon\_openclaw.sh example.com | tee recon\_run.log

## 💡 Why This Workflow Works

The biggest improvement is not speed.

It is **clarity**.

Instead of ending a recon session with scattered data, you finish with:

*   organized folders
*   screenshots
*   URLs
*   scan results
*   a report
*   OpenClaw ready for analysis

That makes it much easier to slow down and ask the right questions.

Which hosts matter?  
Which endpoints look unusual?  
Where should manual testing begin?

That is where real bug bounty work starts.

## ❤️ Final Thoughts

I did not build this script to replace skill.

I built it to support skill.

Automation handles the repetitive work.  
OpenClaw helps organize the results.  
And the real work still belongs to the human in the loop.

👏 If you enjoyed this article, please **clap** so more people can discover it.

🧑‍💻 Follow me on **Medium** for more content about bug bounty, recon automation, and security workflows.

☕ If you want to support my work, you can buy me a coffee here:

[**https://buymeacoffee.com/ghostyjoe**](https://buymeacoffee.com/ghostyjoe)