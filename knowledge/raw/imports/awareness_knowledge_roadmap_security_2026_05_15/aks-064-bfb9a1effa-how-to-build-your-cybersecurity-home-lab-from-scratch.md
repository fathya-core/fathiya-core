# How to build your cybersecurity home lab from scratch

**Published:** 2026-02-11


## without going broke


So you want to build a cybersecurity home lab? Nice. You’re already ahead of 90% of people who just watch YouTube tutorials and call it “learning.”

Here’s the thing: you don’t need a server rack in your basement or a $3,000 budget. You need a laptop, some free software, and the willingness to break stuff (virtually, of course).

Let me show you how to build a proper cybersecurity lab that’ll let you practice real skills without spending real money.

![Image](https://miro.medium.com/v2/resize:fit:700/0*7L3tIBbmx5k-rdbt.jpg)

## Why you actually need a home lab

Before we dive in, let’s talk about why this matters.

Reading about cybersecurity is like reading about swimming. You might understand the theory, but you’re going to sink the first time you jump in the pool.

A home lab lets you:

*   Actually practice hacking (legally)
*   Break things without getting fired
*   Test tools before you use them at work
*   Build a portfolio of real projects
*   Learn by doing, not just reading

Plus, when you’re in a job interview and someone asks “have you actually used Wireshark?” you can say “yeah, I use it in my home lab all the time” instead of “uh… I watched a video once.”

## What you’ll need (spoiler: not much)

Let’s start with the hardware. And no, you don’t need to buy anything new.

**Minimum requirements:**

*   Any laptop or desktop made in the last 8–10 years
*   At least 8GB RAM (16GB is better, but 8GB works)
*   100GB+ free hard drive space
*   That’s literally it

Your current computer? It’ll probably work fine.

## Step 1: Choose your virtualization platform

This is your foundation. Virtualization lets you run multiple “virtual computers” on your one physical computer. It’s how you’ll set up vulnerable machines, attack machines, and everything in between without needing 10 different laptops.

**Your options (all free):**

**VirtualBox** — This is where most people start, and honestly, it’s perfect for beginners. It’s free, open-source, and works on Windows, Mac, and Linux. The interface is straightforward, and there are a million tutorials online.

**VMware Workstation Player** — Free for personal use. Slightly better performance than VirtualBox, but the interface can be a bit more confusing at first.

**Proxmox** — If you have an old computer lying around that you can dedicate entirely to being a lab server, Proxmox is amazing. But for beginners with one laptop? Start with VirtualBox.

**My recommendation:** Start with VirtualBox. Download it, install it, move on. You can always switch later.

## Step 2: Build your attack machine

Every good lab needs an attacking machine. This is your “hacker computer” where you’ll run all your security tools.

**Kali Linux is your best friend here.**

Kali comes pre-loaded with hundreds of security tools. Instead of spending weeks installing nmap, Metasploit, Burp Suite, Wireshark, and everything else individually, you just download Kali and boom — you’ve got everything.

Here’s how to set it up:

1.  Download the Kali Linux virtual machine image (it’s free)
2.  Import it into VirtualBox
3.  Boot it up
4.  You now have a hacking machine

First time you boot into Kali and see all those tools in the menu? Yeah, that feeling never gets old.

**Pro tip:** Give your Kali VM at least 4GB of RAM and 2 CPU cores if you can spare them. It’ll run smoother.

## Step 3: Set up your victim machines

Now you need something to attack. You can’t just practice on random websites (that’s super illegal). You need intentionally vulnerable machines.

**Here are the best free vulnerable VMs:**

**Metasploitable 2 & 3** — These are intentionally vulnerable Linux machines created specifically for practice. They’re packed with vulnerabilities. Perfect for learning exploitation.

**DVWA (Damn Vulnerable Web Application)** — A web app that’s deliberately full of security holes. Great for learning web application hacking.

**VulnHub machines** — A whole website full of free vulnerable VMs. Download them, import them, hack them. There are hundreds of different scenarios and difficulty levels.

**HackTheBox retired machines** — While active HTB machines require a subscription, they release retired machines for free. These are gold.

Start with Metasploitable 2. It’s the “hello world” of vulnerable machines. Everyone starts here, and for good reason — it’s straightforward and well-documented.

## Step 4: Network your lab properly

This is where beginners often mess up. You need to configure your networks correctly, or you’ll either have connectivity issues or accidentally expose your vulnerable machines to the internet (bad idea).

**Here’s the simple setup:**

Create a “host-only” or “internal” network in VirtualBox. This creates a network that only exists between your VMs and your host computer. Your vulnerable machines can’t touch the internet, and the internet can’t touch them.

Put your Kali machine and your vulnerable machines on this isolated network. Now they can talk to each other, but they’re completely cut off from the outside world.

**Why this matters:** You don’t want your intentionally vulnerable Metasploitable machine sitting on your home network where someone could actually attack it. And you definitely don’t want it exposed to the internet.

## Step 5: Add a windows target

Most corporate environments run Windows, so you should practice attacking it too.

**Here’s the clever part:** Microsoft gives away free Windows VMs for testing. They expire after 90 days, but you can just download a fresh one. It’s completely legal and free.

Download a Windows 10 or Windows 11 VM from Microsoft, set it up in your lab, and now you can practice Windows-specific attacks, Active Directory stuff (if you set up multiple Windows VMs), and all the fun Windows vulnerabilities.

**What you can practice:**

*   Privilege escalation
*   Pass-the-hash attacks
*   Windows exploit development
*   PowerShell kung fu
*   Active Directory attacks (if you set up a domain)

## Step 6: Set up your defensive tools

Hacking is fun, but defense is where the jobs are. Set up some blue team tools too.

**Security Onion** — A free Linux distro that’s basically a security monitoring platform in a box. It includes intrusion detection, network security monitoring, and log management. It’s like having a mini SOC in your lab.

Install Security Onion on another VM, configure it to monitor your network traffic, and now you can see what your attacks look like from a defender’s perspective.

This is huge. Being able to see both sides, what the attack looks like when you’re doing it, and what it looks like in the logs will make you so much better at both offense and defense.

## Your First Week: What to actually do

Okay, you’ve got everything set up. Now what?

**Day 1–2: Get comfortable**

*   Boot up your VMs
*   Make sure they can ping each other
*   Break something, figure out how to fix it
*   Take snapshots of your VMs (so you can restore them when you break things)

**Day 3–4: Run your first scans**

*   Use nmap to scan Metasploitable
*   Find the open ports and services
*   Look up what those services are
*   Try to identify vulnerabilities

**Day 5–7: Your first exploit**

*   Pick one vulnerability you found
*   Google how to exploit it
*   Follow a tutorial
*   Actually exploit it
*   Feel like a absolute wizard when it works

Don’t try to learn everything at once. Pick one thing, master it, move on.

## Common beginner mistakes (and how to avoid them)

**Mistake #1: Not taking snapshots** You’re going to break things. A lot. Take snapshots of your VMs before you make major changes. Then when you inevitably mess something up, you can just restore the snapshot instead of rebuilding from scratch.

**Mistake #2: Giving up when something doesn’t work** Nothing will work perfectly the first time. Your VM won’t boot. Your exploit will fail. Your network won’t connect. This is normal. Google the error message, check the forums, try again. Every single person who’s good at this has been exactly where you are.

**Mistake #3: Trying to build the perfect lab before starting** You don’t need everything perfect. You don’t need every possible VM. Start with Kali and Metasploitable. That’s it. You can add more stuff later.

**Mistake #4: Not documenting what you learn** Write down what you do. Take screenshots. When you successfully exploit something, document how you did it. This becomes your portfolio, your cheat sheet, and proof that you actually know this stuff.

## What this lab will cost you

Let’s talk money:

*   VirtualBox: $0
*   Kali Linux: $0
*   Metasploitable: $0
*   VulnHub VMs: $0
*   Windows VMs: $0
*   Security Onion: $0
*   Your internet connection: You already have it

**Total: $0**

The only thing you’re investing is time. And that investment pays off massively.

## Level up your lab (when you’re ready)

Once you’ve got the basics down, here’s how to expand:

**Add more vulnerable machines.** VulnHub has hundreds. Try different difficulty levels. Build a collection.

**Set up Active Directory.** Multiple Windows VMs in a domain environment. This is where enterprise attacks get real.

**Build a SOC.**Add Elasticsearch, Kibana, Splunk Free. Practice log analysis and threat hunting.

**Automate everything.** Use Ansible or Terraform to build and tear down your lab automatically. This is a skill that’ll make you very employable.

**Practice certifications.** Use your lab to practice for OSCP, CEH, or whatever cert you’re chasing.

## The real secret

Here’s what nobody tells you: having a home lab isn’t just about learning technical skills.

It shows initiative. It shows you care enough to practice on your own time. It shows you’re not just memorizing definitions, but you’re actually doing the work.

When you’re applying for jobs and you can say “I have a home lab where I practice penetration testing and defensive security,” you immediately stand out. Most candidates don’t have that.

When you can pull up your documentation and show “here’s a vulnerable machine I exploited, here’s how I did it, here’s what it looked like in the logs,” you’re not just another resume in the pile.

## Your next step

Stop reading. Seriously.

Download VirtualBox right now. Then download Kali. Then download Metasploitable.

You can have a working lab set up in an hour. You’ll probably run into issues. You’ll probably get frustrated. That’s the point. Every problem you solve makes you better.

The difference between someone who wants to work in cybersecurity and someone who does work in cybersecurity? The person who does it has a home lab and actually practices.

Build your lab. Break things. Learn from it. Repeat.

That’s how you get insanely good at this stuff.

_Now go build something. Your future self will thank you._