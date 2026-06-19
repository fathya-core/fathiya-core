# 🔓 Burp-Only IDOR Hunting — Find Broken Authorization Without Fancy Tools

**Published:** 2026-04-01


_By Ghostyjoe_

![Image](https://miro.medium.com/v2/resize:fit:700/1*IdHwAdsbF4Q3zmRBNGSxpw.png)

## 🧠 Why This Matters

Most beginners overcomplicate IDOR hunting.

They install 10 tools, run scripts, and miss the **simplest bugs sitting right in front of them**.

Here’s the truth:

> _🔥 You can find high/critical IDORs using_ **_only Burp Suite_** _— no automation required._

This guide shows you **exactly how to do that**, step-by-step, with real methodology and screenshots.

## ⚠️ Ethical Use Disclaimer

This guide is for **educational and authorized bug bounty testing only**.  
Only test targets you are permitted to test.

## 🎯 What Is IDOR (Quickly)

**IDOR = Insecure Direct Object Reference**

It happens when:

*   An app exposes an identifier (ID, UUID, filename, etc.)
*   And **fails to check if you’re allowed to access it**

## Example

GET /api/user/1234

👉 Change to:

GET /api/user/1235

If it returns another user’s data → 💥 **IDOR**

## 🧰 Setup — Burp Only

## Step 1 — Configure Burp Proxy

![Image](https://miro.medium.com/v2/resize:fit:700/0*LysOBBqsoyNMkKml.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*RuhHUYdPO4i2q6Ny.png)![Image](https://miro.medium.com/v2/resize:fit:500/0*e5qvWW41tnpT2pjd.jpg)

*   Open Burp Suite
*   Go to **Proxy → Intercept ON**
*   Configure browser to use:
*   `127.0.0.1:8080`

## Step 2 — Browse Like a Normal User

👉 Log in  
👉 Click everything  
👉 Generate traffic

**Goal:** Build a request history

## 🔍 Step 1 — Find IDOR Candidates

## Where to Look (CRITICAL)

Look inside Burp → **HTTP History**

Focus on requests containing:

*   `id=`
*   `user_id=`
*   `account=`
*   `file=`
*   `document=`
*   `order=`

## Example Request

GET /api/orders/78452

👉 That number = your attack surface

## 🖥️ Screenshot — HTTP History Filtering

![Image](https://miro.medium.com/v2/resize:fit:700/0*JplYJN3-L9Pd8Sfc.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*dqdQ1LZ2rBq748iF.png)![Image](https://miro.medium.com/v2/resize:fit:500/0*jEB4YqMZy90BnacP.png)

## 🔁 Step 2 — Send to Repeater

Right-click → **Send to Repeater**

Now you control the request.

## 🧪 Step 3 — Manipulate IDs

## Change Values Manually

GET /api/orders/78452   ❌ original  
GET /api/orders/78453   ✅ test  
GET /api/orders/78454   ✅ test

## What You’re Looking For

ResponseMeaning200 + data🚨 IDOR FOUND403Access control working404Maybe exists but hiddenDifferent user data💥 CRITICAL

## 🖥️ Screenshot — Repeater Testing

![Image](https://miro.medium.com/v2/resize:fit:700/0*IdU5e7o_ynR-qUuV.png)![Image](https://miro.medium.com/v2/resize:fit:700/0*KKzNd3KT6ni5Imzx.png)![Image](https://miro.medium.com/v2/resize:fit:500/0*T_bXQTDlCGj0Xuvb.png)

## 🧠 Step 4 — Go Beyond Numbers

Most beginners stop here.

That’s why they miss bugs.

## 🔑 Test Different ID Types

## 1\. Sequential IDs

1001 → 1002 → 1003

## 2\. UUIDs

b7f3-92af-... → try another user's UUID

## 3\. Emails / Usernames

GET /api/user?email\=test@mail.com

## 4\. File Names

/download?file=invoice\_123.pdf

## 🔥 Step 5 — Test Privilege Escalation

Switch accounts.

## Scenario

*   Account A → normal user
*   Account B → another user

## Test

1.  Capture request as **User A**
2.  Replay request accessing **User B’s resource**

## If it works:

💀 You just found:

> **_Horizontal Privilege Escalation (High Severity)_**

## 🔁 Step 6 — Try Method Changes

Developers often secure GET but forget POST/PUT.


Change:

GET /api/user/123

To:

POST /api/user/123

👉 Sometimes bypasses controls entirely.

## 🧪 Step 7 — Parameter Pollution

Add extra parameters:

/api/user/123?user\_id=124

Or:

/api/user?id\=123&id\=124

👉 Backend confusion = potential bypass

## 💣 Real Bug Pattern (What I Look For)

Here’s a simple winning combo:

1.  Find request with `user_id`
2.  Send to Repeater
3.  Change ID
4.  Response returns data
5.  No auth check

👉 That’s it.

No scanners needed.

## 🧠 Pro Tips (This Is Where You Win)

## ✔ Focus on these endpoints:

*   `/api/`
*   `/account/`
*   `/user/`
*   `/documents/`
*   `/download/`

## ✔ Look for these actions:

*   View profile
*   Download file
*   View invoice
*   Access messages

## ✔ Watch for:

*   Same response size, different data
*   JSON responses with user info
*   Hidden endpoints (mobile APIs)

## ⚡ Common Mistakes

❌ Only testing +1 / -1 IDs  
❌ Ignoring POST requests  
❌ Not switching accounts  
❌ Trusting 403 too quickly

## 🧠 Mental Model

> _“If I can guess it… I can probably access it.”_

## 🏁 Final Workflow (Burp Only)

1.  Intercept traffic
2.  Find ID parameters
3.  Send to Repeater
4.  Change ID
5.  Compare responses
6.  Test across accounts
7.  Confirm unauthorized access

## 💰 Why This Works

Because most developers:

*   Check authentication ❌
*   Forget authorization ❌

## 🚀 Final Thoughts

You don’t need automation to find real bugs.

You need:

*   Observation
*   Curiosity
*   Manual testing

> _🔥 Some of the highest-paying bugs come from_ **_simple IDORs like this_**

## 👏 If This Helped

*   Give it a clap
*   Follow for more real bug bounty tactics
*   Support: 👉 [https://buymeacoffee.com/ghostyjoe](https://buymeacoffee.com/ghostyjoe)