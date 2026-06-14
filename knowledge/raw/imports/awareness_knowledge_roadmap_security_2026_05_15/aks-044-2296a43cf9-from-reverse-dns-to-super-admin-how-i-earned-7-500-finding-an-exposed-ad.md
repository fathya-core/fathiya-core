# From Reverse DNS to Super Admin: How I Earned $7,500 Finding an Exposed Admin Panel

**Published:** 2025-12-28


![Image](https://miro.medium.com/v2/resize:fit:700/1*pBBd9DLWyuc1nWDx98TeSA.png)

**Severity:** Critical (10.0)

**Bounty:** $7,500

**Time to Fix:** 2 Days

## Introduction

In the world of bug bounty hunting, the low-hanging fruit is often picked within minutes. To find high-severity vulnerabilities on well-hardened targets, you have to look where others aren’t looking.

Recently, I focused on a target that had been heavily scoured by other hunters. By pivoting from standard subdomain enumeration to **Reverse IP and Reverse DNS analysis**, I uncovered a “private” subdomain that led straight to an unauthenticated Super Admin panel. This discovery granted me full control over the company and its subsidiaries, along with access to over 54,000 sensitive files.

Here is the breakdown of how I found it.

## Phase 1: Initial Reconnaissance

My workflow usually starts with the basics. I gathered a list of subdomains using **Subfinder** to build an initial attack surface.

subfinder -d target.com -all -o subdomains.txt

Once I had the list, I piped it through **httpx** to filter out the dead hosts and focus only on the working HTTP servers.

cat subdomains.txt | httpx -sc -title -o alive.txt

At this stage, I had a standard list of assets. However, rely solely on these tools usually means you are looking at the same assets as everyone else. I needed to dig deeper.

## Phase 2: The Pivot (Reverse IP & DNS)

One of my favorite techniques to find “hidden” or developer-only assets is analyzing the IP space. Often, companies host internal or staging subdomains on the same IP addresses as their public assets, but these subdomains don’t appear in standard certificate logs or wordlists.

**The Technique:**

1.  I accessed a valid subdomain from the target.
2.  I identified the hosting IP address using the [**Shodan extension**](https://chromewebstore.google.com/detail/shodan/jjalcfnidlmpjhdfepjhjbhnhkbgleap).
3.  I performed a **Reverse DNS lookup** on that IP to see _what else_ was hosted there.

![Image](https://miro.medium.com/v2/resize:fit:349/1*o0QlT-v2IFkgm6XCIS9uaA.png)

*for example*

While Shodan is excellent, it doesn’t always show every connected domain, especially if the asset is behind a WAF like Cloudflare. To bypass this blind spot, I turned to [**SecurityTrails**](https://securitytrails.com/).

I took the IP address of the target’s main application and searched it on **SecurityTrails**.

> **_Tip:_** _Always cross-reference IP addresses on multiple platforms._ **_SecurityTrails_** _often indexes historical DNS data that can reveal “shadow” assets connected to an IP._

## Phase 3: The Discovery

The **SecurityTrails** results list revealed a specific subdomain that looked interesting. It didn’t follow the standard naming convention of the main site. It looked like an internal management portal.

I navigated to the URL: `https://admin-internal.target.com` (redacted).

I expected a login prompt or a 403 Forbidden error. Instead, the page loaded, and I was greeted with a full dashboard. No login page. No authentication.

**I was in.**

## Phase 4: Impact Analysis

I immediately verified the privileges associated with this session. It wasn’t just a read-only view; it was a **Super Admin** session.

*   **Full Control:** I had full privileges over the main company and its subsidiaries.
*   **User Management:** I could add, delete, or edit other admin accounts.
*   **Data Leak:** The panel provided direct access to approximately **54,000 confidential files**.

This was a Textbook CVSS 10.0 Critical vulnerability. The “security through obscurity” (hiding the subdomain) had completely failed.

## Reporting & Resolution

I wrote the report immediately, detailing the Reverse DNS technique used to locate the asset and providing screenshots of the admin panel (with sensitive data redacted).

*   **Reported:** Day 0
*   **Triaged:** 2 Hours later
*   **Resolved:** Day 2
*   **Bounty Awarded:** $7,500

![Image](https://miro.medium.com/v2/resize:fit:607/1*sO5KJBUCpFgbQPTcKYgBWQ.png)

## Key Takeaways for Hunters

1.  **Don’t stop at Subfinder:** Everyone runs `subfinder` and `amass`. The real treasure is often found by pivoting off the assets those tools find.
2.  **Follow the IPs:** If you find one valid asset, check the IP. Who are the neighbors? Tools like SecurityTrails are invaluable for this.
3.  **Check for “Hidden” Assets:** Developers often spin up admin panels on obscure subdomains thinking, “No one knows this URL exists, so it doesn’t need a password yet.” They are wrong.