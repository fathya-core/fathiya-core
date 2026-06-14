# 6 Nmap Concepts the CySA+ Exam Will Actually Test You On

**Published:** 2026-04-06


Most CySA+ study guides give you a command table and move on. The exam shows you output and asks what produced it. Here is what to focus on.

![Image](https://miro.medium.com/v2/resize:fit:700/1*xjrwSW2SgNI8AOOhmpeDuA.png)

Good afternoon folks! If you are studying for the CompTIA CySA+ right now, I can almost guarantee you have come across the advice to “know your Nmap commands.” And that advice is fine. But I am going to be real with you because that is what I do here. Knowing the commands is only half the battle. The other half, and arguably the more important half for the CS0–003 exam, is being able to look at Nmap output and interpret what you are seeing on the spot.

I have the CySA+ myself and I have spoken with a good amount of people who have recently taken the exam. The feedback is pretty consistent across the board. The exam does not just ask you “what does -sS do.” It shows you actual output and asks what command produced it. It shows you scan results and asks you to identify the security concern. If all you did was memorize a table of flags and one liner descriptions, you are going to be in a rough spot when you are sitting there staring at a block of output with the timer ticking down.

Let me walk you through the six Nmap concepts that I think are the most important to nail down before sitting for the CySA+. If you get comfortable with these six areas, you should feel pretty confident when the Nmap questions start showing up on exam day. I also created a pretty thorough guide specifically for [**Nmap Prep for the CySa+**](https://jbirdcyber.gumroad.com/l/nmap-for-cysa-exam-guide) too that may be worth checking out if you still are having a bit of trouble. (No shame, it really is a tricky area for most people)

## 1\. You Need to Identify Scan Types From the Output, Not Just the Flags

This is the single biggest gap I see in CySA+ study material and it is where the exam actually lives. Most guides will teach you that -sS is a SYN scan and -sU is a UDP scan and then move on to the next topic. That is great for flashcards but the exam is going to show you output and expect you to work backwards from what you see.

Here is the thing that makes this way more doable than it sounds. The port states in Nmap output are dead giveaways for what kind of scan was run.

If you see **“unfiltered”** as a port state, that is an ACK scan. Every single time. There is no other scan type in Nmap that produces the unfiltered state. So if you see that word in the output on exam day, you already have your answer before you even read the rest of the question.

If you see **“open|filtered”** you are looking at a UDP scan, or potentially a Null, FIN, or Xmas scan. These scan types cannot definitively distinguish between an open port and a filtered one in certain situations, so Nmap lumps them together into that combined state.

If you only see clean **“open” and “closed”** states with /tcp designations and no version info, you are most likely looking at a SYN scan or a TCP Connect scan. These two produce virtually identical output from the results perspective. The difference between them is what happens on the wire and in the target’s logs, not what the Nmap output looks like.

**The takeaway here is to stop studying commands in isolation.** Start associating each scan type with what its output actually looks like. That mental shift alone is going to make Nmap questions significantly easier.

## 2\. The Bottom of the Output is Basically Free Points

I am not exaggerating here. The footer lines at the bottom of Nmap output contain some of the most useful information for answering exam questions and almost nobody pays attention to them when studying.

If you see **“Service detection performed”** at the bottom of the output, that confirms version detection was used. That means the scan included a -sV flag or the -A flag. This is a really easy way to confirm what flags were part of the scan command even if the command itself is not shown to you in the question.

If you see a **TRACEROUTE section** alongside OS details and script output (lines that start with | or |\_ characters), that is the -A flag at work. The -A flag bundles together OS detection, version detection, default NSE scripts, and traceroute all in one. No other single flag gives you all of that combined output.

The exam may show you a block of output that has all four of those elements and ask you what flag could produce it. If you have been ignoring the footer in your practice, you might overthink this and try to piece together multiple individual flags when the answer is just -A.

Another footer detail worth banking away is the **“Not shown: 997 closed tcp ports (reset)”** line. That “(reset)” tells you RST packets were received, which is consistent with a SYN scan behavior. These small details add up to easy points if you know what to look for.

## 3\. Know Your Red Flag Ports Cold

The CySA+ loves to show you scan output and ask you to identify the security concern. This is where having a mental list of suspicious ports and services becomes really valuable and can save you a bunch of time on exam day.

**Port 4444** is the big one. This is the default port for Metasploit’s Meterpreter reverse shell. If you see 4444/tcp open on any scan result during the exam, especially on a production server, that should immediately point you toward a potential compromise. The service column might show something like “krb524?” with a question mark, meaning Nmap could not identify the service, which makes it even more suspicious.

**Port 23** open means Telnet is running and everything including credentials is transmitting in cleartext. There is basically no legitimate reason for Telnet to be running on a production system and the exam knows that. If you see port 23 open in a scenario, the security concern is cleartext transmission.

**Port 21 with vsftpd 2.3.4** is a classic CySA+ scenario. That specific version of vsftpd has a well documented backdoor vulnerability. If you see that exact version string in scan output on the exam, flag it. You do not need to memorize every CVE out there obviously, but this particular one shows up enough in study material and exam feedback that it is worth having in your back pocket.

**Port 445** wide open to the internet is an SMB exposure. SMB should pretty much never be publicly accessible. If the exam shows you a scan of an internet facing server and 445 is open, that is the finding they want you to catch.

Drilling these port associations into memory is one of the highest return study activities you can do for the Nmap portion of the exam. If you want to practice with full output scenarios that include red flag ports and walk you through the analysis, [**I put together a guide specifically for this**](https://jbirdcyber.gumroad.com/l/nmap-for-cysa-exam-guide) that I will mention toward the end.

## 4\. The -sn vs -Pn Trap

If there is one single Nmap concept that trips up more CySA+ candidates than any other, this is probably it. These two flags look similar, they both have a lowercase “n” in them, but they do essentially opposite things.

**\-sn** is a ping scan. It performs host discovery only and does NOT scan any ports at all. You use this when you just want to see what devices are alive on a network without making noise with port scanning. The output from a -sn scan will show you hosts with their MAC addresses and latency but you will not see a single port column anywhere in the results. That absence of port data is the giveaway.

**\-Pn** is the opposite. It skips the host discovery step entirely and jumps straight to port scanning. You would use this when you know a host is up but it is blocking ICMP, so a normal ping would incorrectly report the host as down.

The way I lock this into memory is that -sn means “scan network, no ports” and -Pn means “ports now, no ping.” Whatever mnemonic works for you, drill this one until it is second nature because it will absolutely show up on the CS0–003. I have seen enough exam feedback at this point to basically guarantee that.

## 5\. UDP Scanning is Real and the Exam Knows It

Most people default to thinking about TCP when they study Nmap and that is totally understandable because the default scan type is a TCP SYN scan. But the CySA+ is going to test you on UDP and if you are not ready for it, you are leaving free points on the table.

Here is the scenario that comes up over and over in exam feedback. The question describes a situation where certain services were not detected during a network scan and asks you why. The services in question are things like DNS, DHCP, SNMP, or TFTP. All of these run on UDP. A standard -sS scan will never detect them. The answer is that a UDP scan (-sU) was never performed.

Also worth knowing is that UDP scans are significantly slower than TCP scans. This is because UDP is connectionless, so Nmap has to send a packet and then wait for either a response or an ICMP port unreachable message. Many systems also rate limit ICMP messages which drags the whole process out even further. The exam might present a scenario where a scan is taking an unusually long time and ask you why, and the answer could be that a UDP scan is in progress.

The **open|filtered** state that shows up in UDP scan output is another giveaway. If you see that state on the exam paired with /udp designations, you know exactly what scan type was involved.

## 6\. Default Nmap Does Not Scan Every Port

This one is deceptively simple but it catches people off guard constantly. A default Nmap scan, regardless of what scan type you use, only scans the **top 1000 most common ports.** That is it. It does not scan all 65,535 ports unless you explicitly tell it to with the **\-p-** flag.

Why does this matter for the exam? Because you will very likely see a scenario where a service running on an unusual high numbered port was missed during a scan. The question will ask why it was missed, and the answer is that a full port scan was not performed. This is especially common in threat hunting or incident response scenarios where an attacker might be running a backdoor on port 31337 or some other non standard port that falls well outside the top 1000.

You should also know the **\-p** flag for specifying individual ports (like -p 80,443,8080) and **— top-ports** for scanning a custom number of the most common ports (like — top-ports 100). These are all fair game on the CS0–003.

## I Put Together a Full Guide For This

If this article was useful and you want to go deeper on all of this, **I put together a 35 page guide called Nmap Mastery that is built specifically for CySA+ exam prep.** It is not another command cheat sheet with a one liner per flag. It goes deep on every scan type with full output breakdowns so you can actually see what each one looks like, covers all six port states and which scans produce each one, walks you through real output scenarios with full analysis, **and includes 30 practice questions with detailed explanations modeled after the style of the actual CS0–003 exam.**

I built it because I kept running into the same gap in study material. Everyone covers the commands. Barely anyone covers what the output actually looks like and how to interpret it. And based on the exam feedback I have gotten from people who recently sat for the CySA+, output interpretation is exactly where the questions live.

### [**Grab the Nmap CySa+ Mastery Guide**](https://jbirdcyber.gumroad.com/l/nmap-for-cysa-exam-guide)

![Image](https://miro.medium.com/v2/resize:fit:680/1*DHTTsGb4TLNYDp944po6eQ.png)

**Trying to break into IT or cyber? I make cheat sheets, study guides, and skill building references for beginners. The kind of stuff I wish I’d had when I started. Most are between $2 and $10. Check it out at** [**jbirdcyber.gumroad.com**](https://jbirdcyber.gumroad.com)**!**

## Quick Review Before You Go

Here is the short version of everything above if you want a fast refresher before exam day.

Know the six port states: open, closed, filtered, unfiltered, open|filtered, and closed|filtered. Know which scan types produce each one. This alone will answer a surprising chunk of Nmap questions on the CySA+.

The SYN scan (-sS) does NOT complete the TCP three way handshake. The Connect scan (-sT) does. This is probably the most tested individual Nmap concept on the entire exam.

The -A flag bundles OS detection, version detection, default NSE scripts, and traceroute. If the output has all four of those elements, it was -A.

Default Nmap only scans the top 1000 ports. If a service was missed on a high port, think -p-.

UDP scans (-sU) are required for DNS (53), DHCP (67/68), SNMP (161), and TFTP (69). TCP scans will never find these services.

Lines starting with | or |\_ in the output mean NSE scripts were run via -sC, — script, or -A.