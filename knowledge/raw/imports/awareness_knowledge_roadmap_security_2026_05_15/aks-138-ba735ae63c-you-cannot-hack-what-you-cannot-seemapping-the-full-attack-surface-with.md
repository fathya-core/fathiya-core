# You Cannot Hack What You Cannot See—Mapping the Full Attack Surface with Burp Suite

**Published:** 2026-04-01


> Before exploitation comes reconnaissance. This is how the pros do it.

## First—Spider Is Dead. Here Is What Replaced It.

*   Old Spider = HTML parser. Blind to JavaScript. Missed 70% of modern apps.
*   New **Crawler** = headless Chromium browser. Runs JavaScript. Clicks buttons. Submits forms.
*   Lives inside the **Dashboard tab**—not the Target tab
*   Coverage difference on a React or Angular app? Old Spider finds 20 endpoints. Crawler finds 200.
*   **Bottom line:** forget Spider ever existed. The Crawler is superior in every way.

## The Target Tab — Your Hacker’s Mission Control

![Image](https://miro.medium.com/v2/resize:fit:700/0*XH_GwUr3ZNZIs-Gi)

*Photo by Eugene Uhanov on Unsplash*

> _One tab. Everything Burp knows about your target. All in one place._

## What the Site Map Shows You

*   **Tree on the left**—domains → directories → endpoints
*   **Bold black node** = visited and responded
*   **Grey node** = discovered but not yet visited—your unexplored territory
*   **Right panel** = every request and response for that path, sortable and clickable
*   **Params column checked** = that endpoint has parameters = injection point. Test it.

## The Three Things That Fill the Site Map

1.  **Passive proxy traffic** — everything your browser loads automatically
2.  **Active crawler** — proactively follows links, submits forms, executes JavaScript
3.  **Manual additions**—you add known endpoints directly

## Scope—Set This Before You Touch Anything

> _No scope = noise. Scope = signal. This is non-negotiable._

## Why It Matters

*   Every page load hits 20+ domains—Google Analytics, Stripe, CDNs, trackers
*   Without scope, your HTTP History is a garbage pile
*   With scope, it is a clean, focused feed of just your target

## How to Set It

![Image](https://miro.medium.com/v2/resize:fit:700/1*reQ4__rpu77t9TLazoH9aQ.png)

*Image by Burp Suite*![Image](https://miro.medium.com/v2/resize:fit:700/1*pPYXJ2R6RT5Jw7qFMFBM4g.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*okKVubgrHIx69-U6eqWeyg.png)

*   Go to **Target → Scope → Add**
*   Include: `https://app.target.com` and any related subdomains
*   Exclude: `google-analytics.com`, `stripe.com`, `cdn.cloudflare.com`
*   Then go to **HTTP History → Filter → Show only in-scope items**

## Pro Scope Rules Worth Knowing

*   Use regex for wildcards: `.*\.targetcompany\.com` scopes all subdomains at once
*   Exclude by file extension to hide noise: `.jpg`, `.png`, `.woff`, `.css`
*   Always add new subdomains to scope as you discover them during testing

## Manual Browsing—The Step Everyone Skips and Regrets

> _Automated tools follow logic. Applications have human behavior. You need both._

## What Manual Browsing Captures That Crawlers Miss

*   **Button clicks, not links, caused JavaScript API calls. Never in HTML.**
*   **Features that are only available to authenticated users, such as role-gated, tier-gated, and condition-gated content**
*   **Multiple steps, like resetting a password, checking out, or verifying an email address, each step is a different request.**
*   **What requests are sent when you upload a file?** What happens to the file?
*   **Requests for background polling—session keep-alives, notification checks, and analytics pings**

## The Manual Browse List

*   Log in and visit every page
*   Change account settings
*   Upload a file
*   Complete a transaction or checkout
*   Request a password reset
*   Change your email address
*   Export data if available
*   Invite or manage other users
*   Submit every form with valid data first

**Minimum time:** 30 minutes on any real application. No shortcuts.

## Using the Crawler to Map Active Applications

> _This is what the old Spider wished it could be._

## How to Start It

1.  Click **Dashboard → New Scan**
2.  Select **Crawl** (not audit).
3.  Enter your target starting URL
4.  Configure **login handling** — give it credentials or record a login sequence
5.  Set the scope to match your Target scope
6.  Choose strategy: **Fast** for most cases, **Thorough** for complex apps
7.  Click OK and watch the Site Map grow in real time

## What to Watch For as It Runs

*   Grey nodes turning black = the crawler visited them
*   New paths appearing that you never saw manually
*   API routes are showing up under `/api/v1/`, `/api/v2/`
*   Admin-sounding paths appearing unexpectedly

**Always configure login. Always.**

## Content Discovery — Finding What Was Never Meant to Be Found

> _Backup files. Admin panels. Debug endpoints. Configuration files. They are on production servers right now._

## Two Ways to Run Content Discovery in Burp

**Method 1**

**Built-in tool:** Right-click any host in Site Map → **Engagement tools → Discover content.** Fast, integrated, adds results directly to Site Map

**Method 2**

**Intruder:** `GET /§FUZZ§ HTTP/1.1` With a quality wordlist More control, better lists, and more thorough

## Best Wordlists to Use (from SecLists on GitHub)

*   `common.txt` — 4,700 entries, fast, high signal, start here
*   `raft-medium-directories.txt` — curated for modern apps
*   `api-endpoints.txt` — dedicated to API route discovery
*   `directory-list-2.3-medium.txt` — 220,000 entries, thorough but slow

## The High-Value Files Every Tester Looks For

> _These files are on production servers right now. Most developers never check._

## Version Control Leaks

*   `.git/config` — exposed Git repo. Full source code potentially downloadable.
*   `.git/HEAD` — confirms Git exposure
*   `.svn/entries` — SVN equivalent

## Credential Files

*   `.env` — database URLs, API keys, secret tokens. Critical find.
*   `.env.production`, `.env.local` — same, just named differently
*   `config.php`, `config.json`, `settings.py` — application config with credentials

## Information Disclosure

*   `robots.txt` — developer's list of paths to hide from Google = your list of sensitive areas
*   `sitemap.xml` — complete URL map of the application
*   `phpinfo.php` — full PHP server configuration exposed
*   `swagger.json` / `openapi.json` — complete API blueprint. Every endpoint. Every parameter.

## Backup Files

*   `backup.sql`, `db.sql`, `dump.sql` — database backup. Critical severity. Assessment-ending find.
*   `backup.zip`, `backup.tar.gz` — full application backup
*   `old/`, `backup/`, `archive/` — directories worth always checking

## Engagement Tools — The Menu Nobody Talks About

> _Right-click any host in Site Map → Engagement tools. Four tools. All underused. All powerful._

## Find Comments

*   Scans every collected response for HTML comments
*   Finds: internal paths, endpoint references, debug notes, TODO items, hardcoded credentials
*   Takes 10 seconds to run. Run it on every target without exception.

## Find Scripts

*   Lists every JavaScript file collected
*   JS files contain: API endpoint URLs, parameter names, auth token logic, hardcoded API keys, feature flags
*   Read every JS file listed. Every single one.

## Search

*   Text search across all collected responses
*   **Terms to always search:** `password`, `secret`, `token`, `api_key`, `admin`, `debug`, `TODO`, `FIXME`, `bearer`, `private`, `internal`, `credentials`
*   One search. Scans everything Burp has collected. Takes seconds.

## Analyze Target

*   Produces a complete list of every parameter seen across all requests
*   Your master injection point list in one click
*   Sort by frequency—parameters that appear in many requests are central to the application’s logic

## The Seven-Phase Reconnaissance Workflow

> _Do this on every target. In this order. Without skipping steps._

**Phase 1 — Set scope** before you touch anything

**Phase 2 — Manually browse** every feature, every flow, every page. 30 minutes minimum.

**Phase 3—Review HTTP History** for API calls, parameters, Auth Tokens, and interesting content types

**Phase 4 — Run the Crawler** with authentication configured. Watch the site map grow.

**Phase 5—Content discovery** with built-in tool and Intruder wordlist enumeration

**Phase 6 — Engagement tools** — Find comments, Find scripts, Search, Analyze target

**Phase 7 — Prioritize attack surface** — file uploads, search endpoints, ID parameters, admin paths, API routes go to the top of the list

**Only after all seven phases do you open Repeater and start testing.**

*   The Crawler replaced Spider and it is not even close — use the Crawler
*   Scope first. Always. No exceptions.
*   Manual browsing beats automated crawling for authenticated and JavaScript-driven content
*   Content discovery finds what links and crawlers never will
*   `robots.txt`, `.env`, `swagger.json`, and `.git` are your highest-priority discovery targets
*   Engagement tools run in seconds and consistently surface critical findings
*   Reconnaissance quality determines finding quality. Every time.

## Coming Up in Blog #6

**Decoder and Comparer — Reading What Applications Hide Inside Encoded Data**

*   Base64, URL encoding, HTML encoding, hex—decoded and explained
*   How to spot a JWT token and crack it open
*   Using a comparer to find the one response in a thousand that is different
*   How encoding knowledge lets you bypass input validation filters
*   Session token analysis — is your target generating predictable tokens?

_Follow the series. Blog #6 drops next._

**Tags:** BurpSuite — Reconnaissance — ContentDiscovery — EthicalHacking — PenTesting — BugBounty — WebSecurity — CyberSecurity — PortSwigger — AttackSurface

_← Blog #4: Burp Intruder — Automating Attacks at Scale_ _→ Blog #6: Decoder and Comparer — Coming Soon_