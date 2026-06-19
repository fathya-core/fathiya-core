# Mastering the Repeater — Your Most Powerful Manual Hacking Weapon

**Published:** 2026-03-24


## Burp Suite Learning Series Blog #3

> “Automated scanners tell you where to look. The Repeater is where you actually look.”

## Quick Recap

In **Blog #1**, we installed Burp Suite and understood its architecture. In **Blog #2**, we configured the proxy, installed the CA certificate, and intercepted our first HTTP request. You now understand how traffic flows through Burp and how to read raw HTTP.

Today, we go deeper. The **Repeater** is where real manual testing happens — where you take a captured request and interrogate it, twist it, push it to its limits, and discover how the application behaves under unexpected conditions. By the end of this blog, you’ll be using Repeater to manually probe for SQL Injection, test for Insecure Direct Object References (IDOR), and build the instincts of a real penetration tester.

## What Is the Repeater — and Why Does It Matter?

The Burp Repeater is a tool that allows you to **take any HTTP request, modify it freely, send it to the server, and instantly read the response** — as many times as you want, with full manual control.

![Image](https://miro.medium.com/v2/resize:fit:700/1*UC6IsQbdBaMMMbT9WEmZVw.png)

At first glance, this sounds simple. But consider what it means in practice: every web vulnerability — SQL Injection, Cross-Site Scripting, IDOR, SSRF, authentication bypass, business logic flaws — can be manually tested and confirmed through nothing more than carefully crafted requests in the Repeater. It is the single most used tab in Burp Suite for experienced testers, precisely because it gives you unfiltered, direct communication with the application.

The difference between Repeater and the Proxy Intercept is an important one to understand. Intercept is for capturing requests as they happen in real time, deciding whether to forward or drop them. Repeater is a dedicated workspace where you bring a request, study it at your own pace, and systematically test hypotheses. Think of Intercept as a checkpoint and Repeater as your laboratory.

## The Repeater Interface — A Complete Walkthrough

Before we start testing, let’s get oriented inside the Repeater tab.

## Sending a Request to Repeater

You will almost never type a request from scratch in Repeater. Instead, you capture it first through the Proxy and send it over with one action.

There are two ways to do this:

**From Intercept:** When a request is paused in `Proxy → Intercept`, right-click anywhere in the request panel and select **"Send to Repeater"**. Then click Forward to let the original request continue.

![Image](https://miro.medium.com/v2/resize:fit:700/1*gfA4e2Gtk6LdUCRclvdVqQ.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*rgaeeVSQWop0IgBMWxY-Cw.png)

**From HTTP History:** Go to `Proxy → HTTP History`, right-click any logged request, and select **"Send to Repeater"**. This is the more common workflow — browse an application with Intercept off, let History collect everything, then pick interesting requests to analyze.

![Image](https://miro.medium.com/v2/resize:fit:700/1*4wMKCJ9sQGBAsPPpBHvMTQ.png)

Once sent, click the **Repeater** tab. You’ll see a new numbered tab has appeared (Repeater supports multiple tabs so you can work on several requests simultaneously).

## The Four Panels

The Repeater interface is divided into four key areas:

**Request panel (left):** This is where your HTTP request lives. It is fully editable — every character, every header, every parameter. This is your primary working area.

**Response panel (right):** After clicking Send, the server’s response appears here. You can view it as raw text, rendered HTML, or a hex dump.

**Send button:** The single action that dispatches your modified request to the server and populates the response panel.

**Navigation arrows (◀ ▶):** Burp keeps a full history of every request/response pair within that Repeater tab. Use the arrows to move backward and forward through your testing history — invaluable for comparing how the application responded to different payloads.

![Image](https://miro.medium.com/v2/resize:fit:700/1*V1LFKRbB9bvhd75u3X36Hg.png)

## Understanding What You’re Testing

Before modifying anything, a disciplined tester always asks: _what is this request doing, and where could it go wrong?_

When you look at a request in Repeater, identify the following elements systematically:

**Injection points** are the places where user-controlled data enters the application. These include URL path segments (`/user/1234`), query string parameters (`?id=5&sort=asc`), POST body parameters (`username=admin&password=test`), HTTP headers (`User-Agent`, `Referer`, `X-Forwarded-For`), and cookies (`session=abc123`).

**Every injection point is a potential vulnerability.** The application takes your input and does something with it — queries a database, reads a file, makes an internal request, renders HTML. If the application doesn’t properly sanitize that input, it can be manipulated.

**Data types** also matter. A parameter that accepts an integer behaves differently from one that accepts a string. A parameter embedded in a JSON body requires different payloads than one in a URL query string.

Getting into the habit of identifying injection points before you start testing is what separates methodical testers from those who get lucky.

## Core Repeater Techniques

## Technique 1 — Baseline First, Always

Before injecting anything, send the request **exactly as captured** and study the response. This is your baseline.

Note the following from the baseline response: the HTTP status code, the response length (shown in the bottom bar), the response time, and any specific text in the body. These four data points are your reference. When you start modifying the request, deviations from these baselines are your signal that something interesting is happening.

A change in response length often means the server returned different content — possibly revealing data. A change in response time can indicate a time-based SQL injection. A status code change from 200 to 500 suggests your input caused a server-side error. None of these signals mean anything without a baseline to compare against.

## Technique 2 — Changing Parameter Values

The simplest test: change the value of a parameter and observe what happens.

If the request contains `GET /user/profile?id=42`, try changing `42` to:

*   `43`, `44`, `45` — do you see other users' profiles? (IDOR)
*   `0` or `-1` — does the application handle edge cases gracefully?
*   `99999999` — does an invalid ID crash the server? (500 error)
*   `abc` — what happens when a string is sent where a number is expected?

Each of these probes tells you something about how the application was built and where its defenses might be weak.

## Technique 3 — Using Repeater History for Comparison

After a few rounds of testing, click the back arrow (◀) in the Repeater panel to review your previous requests and responses side by side. You’ll naturally develop a feel for what “normal” looks like versus what looks anomalous.

For more systematic comparison, you can right-click on any request or response in Repeater and select **“Send to Comparer”**. Burp’s Comparer tool will highlight the exact differences between two payloads at the byte level — essential for subtle vulnerability detection.

## Real-World Application: Manual SQL Injection Testing

SQL Injection is one of the most critical web vulnerabilities in existence. The Repeater is the standard tool for manually confirming and exploiting it. Let’s walk through the methodology.

## What Is SQL Injection?

When an application takes user input and embeds it directly into a database query without proper sanitization, an attacker can “inject” SQL code that changes the query’s meaning. For example, a login query might look like this on the server:

SELECT \* FROM users WHERE username \= 'admin' AND password \= 'mypassword';

If the application doesn’t sanitize input, you can inject:

username: admin'--  
password: anything

Which transforms the server-side query into:

SELECT \* FROM users WHERE username \= 'admin'\--' AND password = 'anything';

The `--` is a SQL comment. Everything after it is ignored — including the password check. You've just bypassed authentication entirely.

## Step-by-Step in Repeater

**Step 1:** Capture a login POST request through the Proxy. Right-click → Send to Repeater.

Your request body will look something like:

POST /login HTTP/1.1  
Host: vulnerable-app.com  
Content-Type: application/x-www-form-urlencoded

username=admin&password=test123

**Step 2:** Send the baseline request. Note the response — likely a “Invalid credentials” message with a 200 status code.

**Step 3:** Add a single quote to the username parameter:

username\=admin'&password=test123

Click Send. Check the response carefully. If the application returns a **500 Internal Server Error**, a database error message, or any response different from your baseline, that is a strong indicator of SQL Injection. The single quote broke the SQL syntax on the server.

**Step 4:** Test the classic authentication bypass payload:

username\=admin'--&password=anything

Click Send. If the response changes to a successful login message or redirects you — you’ve confirmed an authentication bypass via SQL Injection.

**Step 5:** Try an OR-based bypass:

username\=admin' OR '1'='1'--&password=anything

This always evaluates to true, potentially returning all users or logging you in as the first user in the database.

> _⚠️ Only perform these tests on applications you own or on designated practice labs such as PortSwigger Web Security Academy, DVWA, or HackTheBox. Unauthorized testing is illegal._

## Reading SQL Error Messages

Error messages are gold for a tester. If the application reveals database errors, you can often determine:

*   The database type (MySQL, PostgreSQL, MSSQL, Oracle)
*   The query structure
*   Table and column names

A MySQL error looks like: `You have an error in your SQL syntax near '...'`  
A PostgreSQL error: `ERROR: unterminated quoted string at or near`  
MSSQL: `Unclosed quotation mark after the character string`

Even if full errors are suppressed, **Boolean-based blind SQL injection** is possible — a topic we’ll cover in a dedicated future blog.

## Real-World Application: Testing for IDOR

**Insecure Direct Object Reference (IDOR)** is one of the most common and highest-impact vulnerabilities found in bug bounty programs. It occurs when an application uses a user-controlled identifier (like a numeric ID) to access objects — and fails to verify that the requesting user is authorized to access that specific object.

## A Classic IDOR Scenario

Imagine you log into an application and view your profile. The request in Repeater looks like:

GET /api/user/profile/1047 HTTP/1.1  
Host: app.example.com  
Cookie: session=eyJhbGciOiJIUzI1NiJ9...

The number `1047` is your user ID. What happens if you change it?

**Step 1:** Send the baseline request with your own ID (`1047`). Confirm it returns your profile data.

**Step 2:** Increment the ID by one:

GET /api/user/profile/1048 HTTP/1.1

Click Send. If this returns another user’s profile data — name, email, address, account details — you have confirmed an IDOR vulnerability. The application authenticated you as a user but failed to verify that the requested resource belongs to you.

**Step 3:** Try a range of IDs systematically. Note how easy it would be to enumerate every user in the system. This is exactly the kind of finding that earns Critical severity ratings on bug bounty programs.

## IDORs in POST Requests

IDORs don’t only appear in URLs. They’re equally common in POST bodies:

POST /api/update-email HTTP/1.1  
Host: app.example.com  
Content-Type: application/json

{"user\_id": 1047, "new\_email": "myemail@test.com"}

Try changing `user_id` to another value. If the server updates a different user's email, that is a critical authorization failure.

## IDORs in Other Parameters

Look for IDORs in:

*   `order_id`, `invoice_id`, `ticket_id` — viewing/downloading others' documents
*   `account_id`, `customer_id` — accessing other accounts
*   `file_id`, `document_id` — reading private files
*   `message_id`, `conversation_id` — reading private messages

The pattern is always the same: a reference to a server-side object, controlled by the user, without proper authorization verification.

## Working with JSON and XML in Repeater

Modern APIs frequently communicate using JSON or XML rather than traditional form-encoded parameters. Repeater handles both seamlessly.

## JSON Requests

A typical API request might look like:

POST /api/v2/transfer HTTP/1.1  
Host: banking-app.com  
Content-Type: application/json  
Authorization: Bearer eyJhbGc...

{  
  "from\_account": "ACC-001",  
  "to\_account": "ACC-999",  
  "amount": 100.00,  
  "currency": "USD"  
}

In Repeater, you can edit the JSON body directly. Test cases worth exploring:

*   Change `amount` to a negative number — can you transfer money _to_ your account from another?
*   Change `from_account` to another user's account ID — IDOR on financial transactions
*   Add unexpected keys: `"admin": true` — does the server honor undocumented parameters?
*   Change the data type: send `"amount": "one hundred"` — how does the server handle type confusion?

## Using the Pretty/Raw Toggle

In the response panel, Burp offers a **“Pretty”** view that formats JSON and XML with proper indentation — much easier to read than minified JSON on a single line. Always use Pretty view when working with API responses. It’s the toggle at the top of the response panel.

## Managing Multiple Repeater Tabs

One of Repeater’s most practical features is its support for multiple simultaneous tabs. Each tab is an independent request/response workspace. This becomes essential when testing complex applications.

**Rename your tabs** by double-clicking on the tab name. Practical naming conventions make your work far more organised — for example: `Login-SQLi`, `Profile-IDOR`, `Transfer-Logic`, `Password-Reset`.

**Common multi-tab workflows:**

When testing an authenticated endpoint, keep one tab with a normal user’s session and another with a different user’s session. Swap cookies between tabs to test whether one user can access the other’s resources — this is cross-account IDOR testing.

When testing a multi-step process (like a checkout flow), use separate tabs for each step. Some applications only validate authorization at the first step; later steps may accept requests out of sequence, which is a business logic flaw.

## Response Time Analysis — A Hidden Signal

Response time is an often-overlooked data point visible at the bottom of the Repeater panel. It tells you how long the server took to process your request, in milliseconds.

Normal responses for a well-optimised application might be 50–200ms. Unusual spikes signal something important.

**Time-based SQL Injection** is a technique where you inject SQL that intentionally causes a delay. If the server is vulnerable, the response time increases proportionally:

username\=admin' AND SLEEP(5)--&password=test

If this request takes approximately 5 seconds longer than your baseline, the `SLEEP(5)` Command executed — confirming SQL Injection even when the application returns no error message and the same response body. This is called **Blind SQL Injection** and response time is your only signal.

## Repeater Settings Worth Knowing

A few configuration options under `Repeater → Settings` (or the gear icon in older versions) that experienced testers adjust:

**Follow redirects:** When set to “Always,” Burp automatically follows HTTP 301/302 redirects and shows you the final response. When set to “Never,” you see the raw redirect response, which can reveal sensitive information like session tokens being passed in the redirect URL. Set this to “Never” when explicitly testing redirect behavior; otherwise “In-scope only” is the safest default.

**Update Content-Length:** Always keep this enabled. When you modify a POST body, the `Content-Length` header must reflect the new byte count — if it doesn't match, many servers reject the request. Burp updates this automatically when this setting is on.

**Unpack compressed responses:** Many servers return gzip-compressed responses. With this enabled, Burp decompresses them automatically so you can read the response as plain text.

## Practical Lab: Step-by-Step IDOR Exercise

Let’s do a complete, guided exercise using PortSwigger’s free Web Security Academy.

## Setup

1.  Go to `[https://portswigger.net/web-security/access-control/lab-user-id-controlled-by-request-parameter](https://portswigger.net/web-security/access-control/lab-user-id-controlled-by-request-parameter)`
2.  Create a free PortSwigger account if you haven’t already
3.  Click **“Access the lab”** — a temporary vulnerable application spins up for you

## The Exercise

The lab gives you credentials: `wiener:peter`. Log in. Notice the URL after login — it likely contains your user ID or username as a parameter.

**Step 1:** With Burp’s HTTP History running (Intercept off), navigate through the application. Find the request that loads your account page. Send it to Repeater.

**Step 2:** In Repeater, send the baseline request. Read the response — it shows your account details and an API key.

**Step 3:** Change the `id` parameter (or whichever parameter identifies the user) from `wiener` to `carlos`.

**Step 4:** Click Send. Read the response carefully.

If the lab is working correctly, you’ll see Carlos’s account page, including his API key — data belonging to a completely different user. You’ve successfully exploited an IDOR. Copy that API key and submit it on the lab page to complete the exercise.

This is a real class of vulnerability that exists in production applications today. Bug bounty hunters have earned hundreds of thousands of dollars finding exactly this type of issue in major platforms.

## Repeater Keyboard Shortcuts

Speed matters when you’re testing dozens of requests. Memorise these:

Action Shortcut Send request `Ctrl + Enter` (Windows/Linux) / `Cmd + Enter` (Mac) Send to Comparer Right-click → Send to Comparer New Repeater tab `Ctrl + T` Go back in history `Ctrl + ←` Go forward in history `Ctrl + →` Search in response `Ctrl + F`

## What’s Coming in Blog #4

You can now intercept, analyze, and manually modify individual requests. The next natural step is **automation within manual testing**. In **Blog #4**, we cover the **Intruder** — Burp’s payload automation engine.

We’ll cover:

*   The four Intruder attack types: Sniper, Battering Ram, Pitchfork, and Cluster Bomb
*   Setting attack positions in a request
*   Configuring payload lists (wordlists, numbers, dates, brute-force sets)
*   Brute-forcing a login form
*   Fuzzing parameters to find hidden endpoints
*   Analysing results with Intruder’s grep and length filtering
*   Rate limiting in the Community Edition and how to work around it

In Blog #3, you learned:

*   What the Repeater is and how it differs from the Proxy Intercept
*   How to send requests to Repeater from HTTP History and Intercept
*   The complete Repeater interface and all four panels
*   The baseline-first methodology is the foundation of methodical testing
*   How to identify injection points in any HTTP request
*   Core techniques, including parameter manipulation, response comparison, and history navigation
*   Manual SQL Injection testing with single quotes, comment characters, and bypass payloads
*   Reading database error messages to fingerprint backend technology
*   IDOR testing in GET requests, POST bodies, and JSON APIs
*   Working with JSON and XML in Repeater
*   Managing multiple tabs for organized testing workflows
*   Response time analysis for blind injection detection
*   Repeater configuration settings that matter
*   A complete guided IDOR lab exercise

The Repeater is where intuition meets method. Automated scanners will find the obvious issues, but the creative, nuanced vulnerabilities — the ones that earn the high payouts and the critical severity ratings — are found by a tester who sits with a single request and asks, _“What happens if I change this? What about this? What if I send it out of order?”_

That curiosity, paired with the systematic methodology we’ve built in this blog, is what makes the difference between a script-kiddie running automated tools and a genuine penetration tester.

**Work through the lab. Break things. Understand why they break.** The Repeater will become your most trusted instrument.

See you in **Blog #4** — where we automate our attacks with the Intruder and test at scale.

_Found this useful? Hit clap 👏 and follow the series — Blog #4 drops next week._

**Tags:** `#BurpSuite` `#BurpRepeater` `#EthicalHacking` `#PenTesting` `#SQLInjection` `#IDOR` `#WebSecurity` `#BugBounty` `#CyberSecurity` `#PortSwigger` `#WebAppSecurity` `#ManualTesting`

_Part of the_ **_Burp Suite Learning Series_** _— Zero to Professional Web Application Penetration Testing._