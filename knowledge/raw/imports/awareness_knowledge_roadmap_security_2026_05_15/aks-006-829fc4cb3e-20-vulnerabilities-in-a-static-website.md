# 20+ Vulnerabilities in a Static Website

**Published:** 2025-11-18


Bug Bounty Cheat Codes

If you have been into application security and doing bug bounty then you must have faced this → **A Static Website.**

> Good to test but what to find..

What’s a static website ? Well for the non-tech folks…

A Web application with **No Database. No Backend. No APIs**. **No login form.**  
Not even a button that pretends to do something!!!

![Image](https://miro.medium.com/v2/resize:fit:1000/1*jJ5-6zmfCDldKx5g1gj-Jg.png)

But still we have few things to look at.

## Reconnaissance & Information Disclosure

This phase focuses on gathering intelligence and identifying assets or sensitive data leaked unintentionally.

1.  **Directory & File Busting:** Run tools (like Gobuster or Dirsearch) to identify exposed configuration and hidden files.

*   **Check for :**

/robots.txt   
/sitemap.xml   
/security.txt   
.env   
.git/   
.DS\_Store (macOS)   
.vscode/  
.idea/ (IntelliJ).

*   **Example:** Accessing `example.com/.git/config` might reveal repository URLs.

**2\. Directory Listing:** Check if the web server allows listing file contents in directories without an index file.

*   **Target Paths:** `/assets/`, `/uploads/`, `/js/`, `/images/` etc.

**3\. Source Code Analysis:** Manually inspect `View Source` and script files.

*   **Developer Comments:** Look for \`\` or commented-out credentials.
*   **Debugging Info:** Check for variable dumps or stack traces left in the HTML.
*   **Hardcoded Secrets:** Inspect JavaScript files for API keys, tokens (AWS, Stripe), or hardcoded credentials.
*   **Hidden URLs:** Look for references to staging (`staging.api.com`) or test URLs (`test.example.com`) inside JS files.

**4\. Metadata Extraction:**

*   **Files:** Analyze Exif data in images or PDF metadata for usernames, OS versions, or internal system paths.
*   **Page:** Check `<meta>` tags for exposed emails, cloud storage links, or software versions.
*   **Tech Stack:** Identify “Built with…” signatures (e.g., Gatsby, Next.js) which might reveal specific framework vulnerabilities.
*   **Analytics:** Extract Google Analytics or Facebook Pixel IDs to reverse-search for other domains owned by the same entity.

**5\. OSINT (Open Source Intelligence):**

*   **Google Dorking:** `site:example.com inurl:admin` or `site:example.com filetype:json`.
*   **Archive.org:** Check the Wayback Machine for older versions of the site that may have exposed sensitive data that is now hidden.

## Infrastructure, Cloud & Deployment

Focuses on the hosting environment, cloud configurations, and deployment artifacts.

1.  **Cloud Storage Misconfigurations:**

*   **S3 Buckets:** Check if the underlying S3 bucket is public (`s3.amazonaws.com/<bucket-name>`).
*   **CloudFront:** Attempt to list the distribution content directly if misconfigured.

**2\. Deployment & Config Files:**

*   **Platform Configs:** Look for exposed `.toml` (Netlify) or `vercel.json` files.
*   **Static Configs:** Review JSON files (e.g., `config.json`, `manifest.json`) for S3 bucket names or CloudFront IDs.

**3\. Backup & Old Files:**

*   **Version Control Backups:** Scan for `.bak`, `.old`, `.zip`, `.rar` files.
*   **Editor Backups:** Ensure `index.html~` or `index_bak.html` (created by editors like Vim or Nano) are not accessible.

**4\. Environment Segregation:**

*   Verify that staging or test environments (`staging.example.com`) are not publicly accessible or indexing.

**5\. Caching:**

*   Review `Cache-Control` headers to ensure sensitive data is not being cached publicly (e.g., `Cache-Control: public` on a profile page).

## HTTP Headers & Transport Security

Validates that the server is enforcing security policies during data transport.

1.  **Encryption (HTTPS):**

*   **Enforcement:** Verify HTTP redirects to HTTPS automatically.
*   **HSTS:** Check for the `Strict-Transport-Security` header.

**2\. Security Headers:**

*   **Clickjacking Protection:** Ensure `X-Frame-Options` is set (e.g., `DENY` or `SAMEORIGIN`).

**3\. MIME Sniffing:** Check for `X-Content-Type-Options: nosniff`.

*   **Content Security Policy (CSP):** Verify a robust `Content-Security-Policy` is present to mitigate XSS and injection attacks.
*   **MIME Types:** Verify the server sets proper MIME types (e.g., ensuring executable content isn’t served as `text/plain` or ensuring JS is not served as `text/html`).

**4\. Cookie Security:**

*   **Flags:** Ensure `Secure` (HTTPS only) and `HttpOnly` (cannot be accessed via JS) flags are set.
*   **Scope:** Check if `Cookie: Path` is strictly defined (not just set to root `/` if unnecessary).

## Client-Side & JavaScript Security

Focuses on the logic executed within the user’s browser.

1.  **Vulnerable Libraries:** Identify outdated JS libraries with known CVEs using tools like `npm audit`, `Retire.js`, or Burp DOM Invader.

**2\. Cross-Site Scripting (XSS):**

*   **Untrusted Input:** Check if URL parameters, hash fragments, or query strings are executed as code.
*   **DOM-Based:** Test search bars or feedback forms where input is reflected in the DOM without sanitization.
*   **Inline Handlers:** Analyze `onload`, `onclick`, or `onerror` events for unsafe string concatenation vulnerabilities.

**3\. Script Integrity:**

*   **3rd Party Scripts:** Review scripts loaded from unknown domains.
*   **CSP Compliance:** Check for inline scripts that do not have a corresponding `nonce` or `hash` in the CSP.

## Access Control & Browser Isolation

Ensures that resources are restricted to authorized users and contexts.

1.  **CORS (Cross-Origin Resource Sharing):**

*   **Wildcards:** Check for insecure `Access-Control-Allow-Origin: *`.
*   **Methods:** Verify the absence of dangerous methods in CORS preflight (e.g., `PUT`, `DELETE` enabled for cross-origin).

**2\. Isolation Policies:** Ensure correct settings for `Cross-Origin-Resource-Policy` (CORP) and `Cross-Origin-Embedder-Policy` (COEP) to prevent data leaks (e.g., Spectre/Meltdown mitigations).

**3\. Service Workers:** Check for misconfigured Service Workers that might be caching sensitive assets excessively.

**4\. Authorization Bypass:**

*   **403 Bypass:** Attempt to access restricted pages directly (e.g., via forced browsing) to see if the 403 Forbidden status can be bypassed.

## Content Manipulation & Logic

Tests how the application handles user input to prevent manipulation of the UI or flow.

1.  **Clickjacking:** Try loading the site in an `<iframe>` to see if it renders. If `X-Frame-Options` is missing, an attacker can overlay invisible layers to trick users.

*   **Example:** `<iframe src="https://target.com"></iframe>`

**2\. Open Redirects:** Check parameters like `?redirect=`, `?next=`, or `?url=` to see if they can redirect the user to an external, malicious site.

*   **Example:** `[https://example.com/login?next=http://evil.com](https://example.com/login?next=http%3A%2F%2Fevil.com)`

**3\. Content Injection:** Attempt to inject query string data to manipulate displayed content (Parameter Pollution).

## Automation that can boost your findings:

*   **Burp Suite Professional** → For header analysis & JS inspection
*   **Retire.js** → Detect vulnerable JS libraries
*   **Nmap + Nikto** → Quick baseline checks
*   **Gitleaks / Trufflehog** → Detect secrets in static assets
*   **Wappalyzer** → Identify exposed tech stack
*   **DOM Invader (Burp)** → For DOM-based XSS testing
*   **Nuclei → O**pen-Source Vulnerability Scanner

![Image](https://miro.medium.com/v2/resize:fit:700/1*6bNKGK83s35ZKeV6sIg02A.png)