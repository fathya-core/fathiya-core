# Autorize: The Burp Suite Extension That Finds Broken Access Control While You Browse

**Published:** 2026-03-25


![Image](https://miro.medium.com/v2/resize:fit:700/1*cOC9OEQgwN69EeB5plXppA.png)

Testing access control manually is one of the most tedious parts of a pentest.

You log in as User A, copy the cookie, log in as User B, replay the request, compare the responses, and then do it again for the next endpoint. On a real application with hundreds of endpoints, that process is slow and it is easy to miss things.

Autorize removes that problem entirely. It does the comparison automatically while you browse normally. You just watch the results come in.

This is a full breakdown of what Autorize is, how to install it, how to use it properly, a real attack scenario, a custom extension you can build on top of it, and where to practice legally.

## What Is Autorize?

![Image](https://miro.medium.com/v2/resize:fit:700/1*EXB6L0i2AuVrsOsRnpfIMw.png)

Autorize is a free Burp Suite extension built specifically to detect broken access control and IDOR vulnerabilities in web applications. It was created by Barak Tawily, an application security researcher, and is available directly from Burp Suite’s BApp Store.

The core idea is straightforward. You give Autorize the session cookie of a low-privilege user. You browse the application as a high-privilege user. Autorize intercepts every request, replays it silently with the low-privilege cookie, and compares both responses.

If the server returns the same data to both users, that endpoint has a broken access control issue.

Here is the type of vulnerabilities it catches:

*   **IDOR (Insecure Direct Object Reference):** Changing a user ID in the URL and getting back someone else’s data. Example: /api/profile?id=101 returns your profile. Change it to 102 and it returns a stranger’s.
*   **Broken Access Control:** A regular user accessing admin-only pages or functions.
*   **Horizontal Privilege Escalation:** User A accessing User B’s resources at the same privilege level.
*   **Vertical Privilege Escalation:** A low-privilege user performing actions reserved for admins.
*   **Unauthenticated Access:** Endpoints returning sensitive data even with no session cookie at all.

IDOR and broken access control have been the number one vulnerability in the OWASP Top 10 since 2021. Autorize is built to find them fast.

## How to Install Autorize

![Image](https://miro.medium.com/v2/resize:fit:700/1*4LnSDRsn1OoR9qPpEPFmmg.png)

Installation is quick. Here are the steps:

1.  Open Burp Suite Community or Professional Edition.
2.  Click the **Extensions** tab at the top of the Burp window.
3.  Click **BApp Store**.
4.  Type **Autorize** in the search bar.
5.  Click **Install**.

Once done, a new **Autorize** tab appears in your Burp toolbar. That is where everything happens.

One thing worth knowing: Autorize is written in Python. On newer versions of Burp Suite this works automatically. If you are on an older version and get a Python error, you need to install Jython (a Java implementation of Python). Download the standalone JAR from jython.org, then go to Extensions, Extension Settings, Python Environment, and add the file path there.

## How to Use Autorize Step by Step

![Image](https://miro.medium.com/v2/resize:fit:700/1*PA1U0G03tUljYz60RNG2_w.png)

This is the step most people find confusing the first time. Here is the exact process.

**Step 1: Set your target scope**

Before anything else, go to the Target tab in Burp, right-click your target domain, and add it to scope. This stops Autorize from replaying requests to Google, CDNs, and analytics scripts and cluttering your results table with noise.

**Step 2: Log in as the low-privilege user and grab the cookie**

Open a separate browser or check Burp’s HTTP history to log in as the regular user. Copy their full session cookie. It will look something like:

Cookie: session=lowprivilege\_token\_456

**Step 3: Paste the cookie into Autorize**

Click the Autorize tab. At the bottom of the panel you will see a text field. Paste the low-privilege cookie there exactly as it appears.

**Step 4: Turn Autorize on**

Click the button that reads **Autorize is off**. It turns green and switches to **Autorize is on**.

**Step 5: Browse as the high-privilege user**

Now log into the application as the admin in Burp’s built-in browser and use it normally. Visit every feature, every settings page, every API endpoint you can find. Autorize runs silently in the background, replaying each request with the low-privilege cookie and filling up the results table in real time.

**Step 6: Read the results**

Each row in the Autorize table is color coded:

*   **Red — Bypassed!** The low-privilege user received the same response as the admin. Investigate this endpoint.
*   **Orange — Is Enforced?** The responses differ but not conclusively. Verify manually.
*   **Green — Enforced!** Access control is working correctly here.

Do not trust every red result automatically. Some will be false positives. Open each red row, compare both response bodies side by side, check the status codes and content, and confirm with your own eyes before calling it a finding.

## Real-World Attack Scenario

![Image](https://miro.medium.com/v2/resize:fit:700/1*ZCpFxvrjPspCOAUvk3BWMg.png)

Here is a real scenario that shows how this plays out during a pentest.

You are testing a fintech platform with two user roles: Admin and Regular User. You configure Autorize with the Regular User’s session cookie and start browsing as the Admin.

After ten minutes of clicking through the dashboard, you check the Autorize table. Most rows are green. Two are red.

You click the first red row. The endpoint is:

GET /api/v1/users/reports/export?userId=2047

On the left side: the Admin’s response. A full salary and financial report for userId 2047.

On the right side: the Regular User’s response. The exact same report.

The server never checked who was asking. It just returned the data.

That is a critical IDOR vulnerability. Any regular user could pull up the financial records of any other person in the system just by changing a number in the URL.

Without Autorize, you might have spotted that endpoint manually and thought to test it, or you might have moved on. With Autorize running in the background, it flagged itself while you were clicking through unrelated pages.

## Custom Extension: Auto-Log Every Bypass to a File

This Python extension builds on top of Autorize. It watches every HTTP response and automatically saves each bypassed endpoint to a text file on your machine. When your pentest session is done, you have a timestamped list of findings ready for your report without writing anything down manually.

from burp import IBurpExtender, IHttpListener  
import datetime  
  
class BurpExtender(IBurpExtender, IHttpListener):  
    def registerExtenderCallbacks(self, callbacks):  
        self.\_callbacks = callbacks  
        self.\_helpers = callbacks.getHelpers()  
        \# Name shown in the Extensions tab inside Burp Suite  
        callbacks.setExtensionName("Autorize Bypass Logger")  
        \# Register to receive all HTTP messages passing through Burp  
        callbacks.registerHttpListener(self)  
        \# Open log file in append mode - old findings are never overwritten  
        self.\_log\_file = open("bypass\_findings.txt", "a")  
        print("\[\*\] Bypass Logger is running.")  
    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):  
        \# Skip requests - we only care about server responses  
        if messageIsRequest:  
            return  
        response = messageInfo.getResponse()  
        if response is None:  
            return  
        \# Parse the response and pull all headers into a list  
        analyzed = self.\_helpers.analyzeResponse(response)  
        headers = analyzed.getHeaders()  
        \# When Autorize detects a bypass it adds this custom header to the response  
        for header in headers:  
            if "X-Autorize-Status: Bypassed" in header:  
                \# Extract the full URL of the bypassed request  
                url = self.\_helpers.analyzeRequest(  
                    messageInfo.getHttpService(),  
                    messageInfo.getRequest()  
                ).getUrl()  
                \# Create a timestamped log line  
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
                entry = "\[{}\] BYPASSED: {}\\n".format(timestamp, url)  
                \# Write immediately so nothing is lost if Burp crashes  
                self.\_log\_file.write(entry)  
                self.\_log\_file.flush()  
                print(entry.strip())

**How to load this in Burp:**

1.  Go to Extensions and click Add.
2.  Set Extension Type to Python.
3.  Select this file and click Next.
4.  Run your Autorize session as normal.

Every bypassed endpoint saves to **bypass\_findings.txt** in your working directory with a timestamp. Open it after your session and your findings list is already started.

## Where to Practice Legally

Never run Autorize on any website without written permission to test it. In India, the IT Act 2000 makes unauthorized access to computer systems a criminal offence.

Use these legal environments instead:

**PortSwigger Web Security Academy** at portswigger.net/web-security/access-control. Thirteen free labs covering every type of access control vulnerability. Built by the same team that makes Burp Suite and designed to work directly with Autorize. This is where you should start.

**DVWA (Damn Vulnerable Web Application).** Install it locally on your machine and practice IDOR in a fully controlled environment with zero legal risk.

**TryHackMe.** Has beginner-friendly rooms covering access control and IDOR. Good for guided practice with hints when you get stuck.

**HackTheBox.** Has retired machines where Autorize is the right tool. Better once you have some experience and want a more realistic challenge.

Work through all 13 PortSwigger labs first. After that, move to HackTheBox. The gap in difficulty between the two will teach you more than any course.

## Final Thoughts

Broken access control is not a glamorous vulnerability. It does not involve complex payloads or clever multi-step exploits. Most of the time it is just a missing check on the server side.

But it consistently causes some of the most serious data breaches in real applications. Salary data exposed. Medical records accessible to anyone. Admin functions open to regular users.

Autorize finds these fast. Install it, set up two accounts on a PortSwigger lab, turn it on, and browse. You will see what it does within the first five minutes.

Next in this series: **Param Miner**, the extension that uncovers hidden parameters and cache poisoning vulnerabilities that most scanners miss completely.