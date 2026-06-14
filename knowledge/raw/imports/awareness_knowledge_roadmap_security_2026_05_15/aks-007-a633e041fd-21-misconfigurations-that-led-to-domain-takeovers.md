# 21 Misconfigurations That Led to Domain Takeovers

**Published:** 2026-01-14


## A Step-by-Step Guide for Security Professionals

Ever seen a giant brand lose their website overnight — because of a tiny config error?

You’d be shocked how often **domain takeovers** happen. All it takes is:

*   One overlooked DNS record
*   A forgotten subdomain
*   A botched cloud configuration

And suddenly, an attacker controls your domain.

Even experienced IT and security teams miss these issues. That’s why domain takeovers remain one of the most profitable and repeatable attack vectors today.

This guide breaks down **21 real-world misconfigurations** that have actually led to domain takeovers. You’ll learn:

*   How attackers discover them
*   How exploitation works
*   How to detect and fix them _before someone else does_

![Image](https://miro.medium.com/v2/resize:fit:700/0*nUhiQAdx_7vpw_Yj)

*Photo by Adi Goldstein on Unsplash*

## Why Domain Takeovers Matter More Than You Think

When people hear “domain takeover,” they imagine elite hackers and zero-days.

The truth is much simpler.

Attackers don’t need exploits.  
They need **your mistakes**.

A successful domain takeover allows attackers to:

*   Send emails from your domain
*   Host phishing or malware on trusted subdomains
*   Steal credentials via XSS or fake login pages
*   Destroy brand reputation in hours

Bug bounty hunters routinely earn **$5,000–$10,000+** for a single overlooked DNS record. Some pentesters (myself included) have discovered dozens of takeover-ready domains in one afternoon.

Let’s break down how it actually happens.

## 1\. Orphaned DNS Records (Classic Subdomain Takeover)

### What Goes Wrong

A DNS record points to a cloud resource that no longer exists.

### How Attackers Exploit It

Example:

*   `blog.example.com` → Heroku app (deleted)
*   Heroku allows anyone to claim that app name

The attacker registers the missing app and instantly controls the subdomain.

### How to Find & Fix

subfinder -d example.com  
dig blog.example.com

**Fix:**  
Remove DNS records for deleted resources. Monitor dangling CNAMEs continuously.

## 2\. Wildcard DNS Records Pointing to External Providers

### The Problem

Wildcard records (`*.example.com`) resolve every subdomain—even ones you never created.

### Real-World Impact

A deleted cloud app + wildcard DNS = **hundreds of takeover candidates**.

### Detection

dig '\*.app.example.com'

**Fix:**  
Avoid wildcards unless absolutely necessary. Audit them often.

## 3\. CloudFront / CDN Misconfigurations

### What Happens

A subdomain points to a deleted CloudFront distribution.

### Attack Flow

1.  Attacker finds unclaimed CloudFront hostname
2.  Creates a new distribution
3.  Attaches your subdomain

**Fix:**  
Remove DNS entries when CDNs are deleted. Track all active distributions.

## 4\. Unclaimed Amazon S3 Buckets

### Scenario

*   `assets.example.com` → `assets-example.s3.amazonaws.com`
*   Bucket deleted
*   Attacker recreates bucket with same name

### Proof-of-Concept

aws s3 mb s3://assets-example  
aws s3 cp index.html s3://assets-example

**Fix:**  
Audit DNS-linked buckets regularly. Never delete a bucket before removing DNS.

## 5\. Expired External Domains in DNS Records

### Why This Works

DNS records sometimes point to third-party domains that expire.

Attackers simply re-register them.


*   Scan DNS for external domains
*   Check expiration using `whois`

**Fix:**  
Remove expired or unnecessary external domain references.

## 6\. GitHub Pages CNAME Takeovers

### The Setup

*   `project.example.com` → GitHub Pages
*   Repo deleted, DNS remains

### Exploit

Anyone can create a repo, add a `CNAME` file, and hijack the subdomain.

\# CNAME  
project.example.com

**Fix:**  
Remove unused GitHub Pages DNS entries. Monitor public repos.

## 7\. Heroku App Deletion Without DNS Cleanup

### Why It’s Dangerous

Heroku app names are globally claimable.

### Attack Steps

1.  Attacker claims old app name
2.  Deploys content
3.  Your subdomain serves attacker data

**Fix:**  
Delete DNS records before deleting Heroku apps.

## 8\. Azure Web App Takeovers

### The Issue

Subdomains still point to deleted `azurewebsites.net` apps.

nslookup site.example.com

**Fix:**  
Track custom domains mapped to Azure. Clean DNS on teardown.

## 9\. Unrestricted HTTP Host Header Trust

### The Risk

Apps blindly trust the `Host` header.

GET / HTTP/1.1  
Host: evil.example.com

**Fix:**  
Strictly validate allowed hostnames at the web server or app layer.

## 10\. Misconfigured MX Records


MX records point to expired or abandoned mail servers.

### Impact

*   Email interception
*   Phishing
*   Credential theft

dig MX example.com

**Fix:**  
Audit MX records after every email migration.

## 11\. Outdated SPF, DKIM, and DMARC Records

### Common Mistake

Old mail providers remain in SPF records.

v=spf1 include:oldmail.com include:spf.protection.outlook.com -all

**Fix:**  
Clean mail records whenever infrastructure changes.

## 12\. Weak CORS on API Subdomains

### The Danger

If a taken-over subdomain is allowed in CORS, attackers can read sensitive data.

fetch("https://api.example.com/user", {  
  credentials: "include"  
})

**Fix:**  
Never use wildcard CORS. Restrict origins strictly.

## 13\. Forgotten Reverse Proxies and Load Balancers


DNS still routes traffic through proxies after backends are gone.

**Fix:**  
Audit proxy configs alongside DNS records.

## 14\. Open DNS Zone Transfers (AXFR)

### The Shock Factor

Anyone can dump your full DNS zone.

dig AXFR example.com @ns1.example.com

**Fix:**  
Restrict zone transfers to trusted IPs only.

## 15\. Misconfigured CDN Custom Hostnames

### The Gap

DNS remains after CDN custom hostname deletion.

**Fix:**  
Always remove DNS entries when disabling CDN configs.

## 16\. Exposed Cloud Credentials on Taken-Over Subdomains

### Exploit Chain

1.  Subdomain takeover
2.  Old JS files expose API keys
3.  Full cloud compromise

**Fix:**  
Rotate credentials regularly. Scan for secrets before deployment.

## 17\. Open Redirects on Subdomains

### Why It Matters

Taken-over subdomains + open redirects = perfect phishing.

GET /redirect?next=https://evil.com

**Fix:**  
Whitelist redirect destinations.

## 18\. SSRF via Trusted Internal Subdomains


Internal subdomains are implicitly trusted.

### Result

SSRF + takeover = internal API access.

**Fix:**  
Validate destination IPs and never trust subdomains blindly.

## 19\. Leaky DNS TXT Records

## What Leaks

*   API keys
*   Internal IPs
*   Cloud resource names

## Check

dig TXT example.com

**Fix:**  
Scrub TXT records regularly.

## 20\. Forgotten Dev and Test Environments

## Common Target

*   `dev.example.com`
*   `test-api.example.com`

Often abandoned and vulnerable.

**Fix:**  
Track all environments. Delete DNS when decommissioning.

## 21\. No DNS Change Monitoring

## The Silent Killer

If you don’t monitor DNS, you won’t notice mistakes until it’s too late.

dnsmonitor \--domain example.com \--alert email

**Fix:**  
Enable automated DNS change alerts.

## How Attackers Find These Issues

This is mostly automated.

Typical workflow:

subfinder -d example.com | tee subs.txt  
subjack -w subs.txt -t 100 -ssl

Attackers look for:

*   Dangling CNAMEs
*   Unclaimed cloud resources
*   Expired domains

This is how real bug bounties are won.

## Practical Checklist to Prevent Domain Takeovers

*   Inventory all DNS records
*   Remove orphaned CNAME, A, and MX records
*   Audit cloud mappings
*   Minimize wildcard DNS usage
*   Monitor DNS changes
*   Rotate secrets regularly
*   Lock down CORS, Host headers, SSRF
*   Kill unused environments