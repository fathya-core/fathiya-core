# Your Password Manager Just Got Hacked. The Bitwarden Supply Chain Attack.

**Published:** 2026-04-23


## **A self-replicating worm named after a Dune monster just hijacked one of the most trusted tools in security. Here’s what it stole, how it spread, and what you need to do right now.**


![Image](https://miro.medium.com/v2/resize:fit:700/0*KYQODJsgH2nduH4A.jpg)

I need to be blunt with you.

If you installed the **Bitwarden CLI** from npm anytime on April 22, 2026, between 5:57 PM and 7:30 PM Eastern, your SSH keys, cloud credentials, GitHub tokens, npm tokens, environment variables, shell history and possibly your AI coding tool configurations have been stolen.

Not “might have been.” Were.

The malicious code ran automatically on install. No click required. No prompt. No warning. The moment `npm install @bitwarden/cli` executed, a preinstall hook fired and your machine was compromised before the install even finished.

Bitwarden. The password manager that security professionals recommend to everyone. The tool I’ve personally recommended to colleagues. That Bitwarden.

Let me explain what happened, because this is not just another npm attack. This one is genuinely different, and the implications go further than any headline I’ve seen has captured.

## What Actually Happened

Version `@bitwarden/cli@2026.4.0` was published to npm with malicious code injected into it. This was not a typosquat. This was not a lookalike package with a similar name. This was the real, official Bitwarden CLI package, published under the legitimate `@bitwarden` scope, through Bitwarden's own CI/CD pipeline.

The attackers didn’t break into Bitwarden’s source code. They broke into something more dangerous: the pipeline that publishes the code to npm.

Here’s the attack chain:

**Step 1: The Checkmarx campaign.**

This Bitwarden compromise is part of a larger, ongoing campaign that previously hit Checkmarx’s own infrastructure, including their Docker Hub projects and a VS Code extension. The attackers gained access to secrets and tokens during that campaign.

**Step 2: CI/CD pipeline injection.**

Using credentials acquired from the Checkmarx compromise, the attackers infiltrated Bitwarden’s GitHub Actions workflow. Specifically, they modified `publish-cli.yml` in the `bitwarden/clients` repository. This is the workflow that builds and publishes the CLI to npm.

**Step 3: Malicious package published under the real name.**

Because the attackers controlled the publishing pipeline itself, the malicious package was published under the legitimate `@bitwarden/cli` name. It passed npm's trusted publishing controls. It looked completely authentic because, from npm's perspective, it was published by Bitwarden's own infrastructure.

As security researcher Adnan Khan noted:

> “I believe this is the first time a package using NPM trusted publishing has been compromised.”

That line should stop you cold. Trusted publishing was supposed to be the solution to this exact problem. And it was bypassed not by breaking the trust mechanism, but by compromising the system that uses it.

## The Worm Inside: “Shai-Hulud: The Third Coming”

The malicious code inside the hijacked package is not a simple credential stealer. It’s a fully featured, self-propagating worm, and its creators gave it a name straight out of science fiction.

Embedded in the payload is the string: **“Shai-Hulud: The Third Coming.”**

Shai-Hulud is the giant sandworm from Frank Herbert’s _Dune_. The attackers have used Dune theming throughout: exfiltration repositories are named with randomized Dune vocabulary like `fremen-sandworm-441` and `harkonnen-melange-7`. The public commit messages used to exfiltrate stolen data start with `LongLiveTheResistanceAgainstMachines`.

This is not their first time. The original Shai-Hulud worm was first detected in September 2025. A second wave hit in late 2025. This Bitwarden compromise represents the third generation, and it’s significantly more sophisticated than its predecessors.

## What It Steals (The Full List)

When the malicious preinstall hook fires, it downloads the legitimate Bun JavaScript runtime from GitHub, then uses it to execute a 10 MB obfuscated payload called `bw1.js`.

![Image](https://miro.medium.com/v2/resize:fit:700/1*J5bTJHukY9B9podFnlZ86g.jpeg)

That payload scans your machine for the following files:

**SSH and Git credentials:**

*   `~/.ssh/id*` and `~/.ssh/id_*` (your SSH private keys)
*   `~/.ssh/known_hosts` (SSH host fingerprints)
*   `.git/config` (Git remote URLs and credentials)
*   `.git-credentials` (stored Git passwords)

**Cloud provider credentials:**

*   `~/.aws/credentials` (AWS access keys)
*   `~/.config/gcloud/credentials.db` (Google Cloud credentials)
*   Azure Key Vault credentials (accessed via ambient tokens)

**Developer tokens:**

*   `~/.npmrc` (npm authentication tokens)
*   `.env` files (environment variables with API keys)
*   GitHub tokens (Personal Access Tokens, Actions secrets)

**AI coding tool configurations:**

*   `~/.claude.json` (Claude Code authentication token)
*   `~/.claude/mcp.json` (Claude Code MCP server configs, which can contain API keys and database credentials)
*   `~/.kiro/settings/mcp.json` (Kiro MCP server configurations)
*   Cursor, Codex CLI, and Aider configurations

**Shell history:**

*   `~/.bash_history`
*   `~/.zsh_history`

And it doesn’t stop at local files. The malware also runs collectors against cloud secret managers using whatever ambient credentials it finds. AWS SSM Parameter Store. AWS Secrets Manager. Azure Key Vault. GCP Secret Manager. If you ran this on a cloud-connected development machine or CI runner, your entire secrets infrastructure was harvested.

## How It Spreads: The Self-Propagating Mechanism

This is where it gets truly alarming.

Regular malware steals your data and sends it to an attacker. This malware steals your data and then uses your own identity to infect others.

Here’s how the propagation works:

**1.** The worm steals your GitHub token.

**2.** Using your token, it creates a new public repository under your GitHub account. The repository name follows the Dune-themed naming scheme (`<dune-word>-<dune-word>-<digits>`).

![Image](https://miro.medium.com/v2/resize:fit:700/0*PMDESKdIuTP3r_wq)

*Shai-hulud Worm from the Movie Dune*

**3.** Your stolen credentials are encrypted with AES-256-GCM and committed to that repository.

**4.** If you don’t have GitHub organization membership, your GitHub token is also published into a public commit “dead-drop” where other infected machines can find and reuse it.

**5.** If the attacker’s primary command-and-control server is down, the worm searches GitHub for fallback instructions using a specific search query.

The genius, and I use that word with deep discomfort, is that the exfiltration happens through GitHub’s own infrastructure. Security tools typically don’t flag data being sent to GitHub. It looks like normal development activity. A new repo, a new commit. Nothing suspicious on the surface.

But underneath, your credentials are sitting in a public repository that anyone can find.

As OX Security’s research team put it:

> “Anyone searching GitHub can potentially find and access those credentials. At that point, sensitive data is no longer in the hands of a single threat actor. It’s exposed to anyone.”

A single developer who installs the malicious package can become the entry point for a broader supply chain compromise. The attacker gains persistent workflow injection access to every CI/CD pipeline that developer’s token can reach.

One install. One developer. And the blast radius expands from there.

## The Crypto Connection

For cryptocurrency users, this attack is particularly dangerous.

The malware targets `.env` files and cloud credentials that frequently contain wallet private keys, exchange API tokens, and DeFi protocol access keys. If you were running a crypto-related project and installed the compromised Bitwarden CLI, your wallet keys may have been exfiltrated.

The previous Shai-Hulud campaigns explicitly used TruffleHog to scan infected systems for cryptocurrency keys and secrets. While the exact crypto-specific capabilities of this third wave are still being analyzed, the credential harvesting scope is broad enough to capture any crypto keys stored in standard developer locations.

If you build or interact with cryptocurrency projects and installed this package, treat every wallet key and exchange credential on that machine as compromised. Move funds immediately.

## One Detail That Should Terrify You

The malware has a locale check. It quits execution on systems where the locale corresponds to Russia.

This is a well-known pattern in cybercrime. Malware operators based in certain jurisdictions deliberately exclude systems in their own region to avoid attention from local law enforcement. It’s not proof of origin, but it’s a strong operational signal.

The attackers also embedded an anti-AI manifesto that the malware attempts to write to victims’ shell configuration files. The messaging, combined with the “LongLiveTheResistanceAgainstMachines” commit tags, suggests an ideological dimension to the campaign. Whether that ideology is genuine or a diversion is unclear.

## Bitwarden’s Official Response

Bitwarden confirmed the incident and published the following statement:

> “The Bitwarden security team identified and contained a malicious package that was briefly distributed through the npm delivery path for @bitwarden/cli@2026.4.0 between 5:57 PM and 7:30 PM (ET) on April 22, 2026.”

Key points from their response:

*   **No vault data was accessed.** Your Bitwarden password vault, your stored passwords, your login credentials inside Bitwarden itself were not compromised. The attack targeted the CLI tool’s npm distribution, not Bitwarden’s vault infrastructure.
*   **The window was 93 minutes.** The malicious version was available on npm for roughly an hour and a half before it was detected and removed.
*   **No production systems were compromised.** The attack was limited to the npm distribution mechanism. The Bitwarden browser extension, desktop app, and web vault were not affected.
*   **A CVE is being issued** for `@bitwarden/cli@2026.4.0`.

This matters: if you use Bitwarden through the browser extension, desktop app, or web interface and never installed the CLI from npm, you are not affected. The passwords stored in your Bitwarden vault are safe.

## Who Is Actually Affected

Let me be specific about who needs to act and who doesn’t.

**You ARE affected if:**

*   You installed `@bitwarden/cli` from npm on April 22, 2026, between approximately 5:57 PM and 7:30 PM ET
*   Your CI/CD pipeline pulls `@bitwarden/cli` from npm without version pinning and ran during that window
*   You have `@bitwarden/cli@2026.4.0` in any `node_modules` directory on any machine

**You are NOT affected if:**

*   You use Bitwarden only through the browser extension, desktop app, or web vault
*   You installed the CLI through a method other than npm (such as the standalone binary, Snap, Homebrew, or Chocolatey)
*   You have the CLI installed but your version is anything other than `2026.4.0`
*   You did not install or update the CLI during the 93-minute attack window

## Action Items: What to Do Right Now

If you fall into the affected group, here is your immediate response checklist:

**1\. Check your installed version.**

npm ls @bitwarden/cli

If it shows `2026.4.0`, you were hit. Uninstall it immediately:

npm uninstall @bitwarden/cli

**2\. Rotate every credential on that machine.**

Assume everything the malware targeted is compromised. That means:

*   All SSH keys (generate new key pairs, update `authorized_keys` on every server)
*   GitHub Personal Access Tokens (revoke and regenerate)
*   npm tokens (revoke in npm settings, regenerate)
*   AWS access keys (rotate in IAM console)
*   GCP credentials (revoke and regenerate service account keys)
*   Azure credentials (rotate all affected keys)
*   Any API keys stored in `.env` files
*   Any secrets in your shell history (yes, that means any credential you ever typed in a terminal command)

**3\. Audit your GitHub account.**

Look for:

*   New repositories you didn’t create (especially with Dune-themed names)
*   New or modified GitHub Actions workflows in your repositories
*   Unfamiliar branches or commits
*   New deploy keys or OAuth apps

**4\. Audit your CI/CD pipelines.**

Check every GitHub Actions workflow in repositories your token has access to. Look for injected steps, new workflows, or modified publishing actions.

**5\. Check for the command-and-control domain.**

Search your network logs or DNS queries for connections to `audit.checkmarx[.]cx`. Note: this is NOT the real Checkmarx domain. The `.cx` TLD is Christmas Island. The real Checkmarx uses `.com`. If you see connections to this domain, the malware executed on your network.

**6\. If you work with cryptocurrency.**

Move funds out of any wallet whose keys were stored on the affected machine. Do this before rotating anything else. Stolen wallet keys can be used immediately.

**7\. Monitor for ongoing compromise.**

The self-propagating nature of this worm means the attacker may have persistent access through injected workflows. Even after rotating credentials, monitor your GitHub and npm accounts for suspicious activity over the coming weeks.

## The Bigger Picture: Trust Is the Attack Surface

This attack succeeded not because Bitwarden’s security was weak. It succeeded because the attackers found a way to abuse trust at the infrastructure level.

npm’s trusted publishing exists specifically to prevent unauthorized package publications. It worked exactly as designed. The problem is that the system publishing the package was itself compromised. The trust was misplaced not in the mechanism, but in the assumption that the upstream CI/CD pipeline was clean.

This is the same pattern we’ve seen over and over in 2025 and 2026:

*   **Lovable** exposed user data through broken authorization that sat unpatched for 48 days
*   **Vercel** was breached through a compromised third-party AI tool that an employee gave broad OAuth permissions to
*   **Checkmarx** itself was compromised, and that compromise cascaded into Bitwarden’s pipeline

[

## Vercel and Lovable Got Breached in the Same Week. Your API Keys Might Be in Both.

### Lovable exposed your AI chat history and database credentials. Vercel leaked your environment variables. Here’s exactly…

dhanushnehru.medium.com


](https://dhanushnehru.medium.com/vercel-and-lovable-got-breached-in-the-same-week-your-api-keys-might-be-in-both-6b653dbd2a2f?source=post_page-----e5a83ede7e51---------------------------------------)

Each attack exploits a different point of trust in the developer supply chain. The package registry. The CI/CD pipeline. The third-party integration. The OAuth permission. Every point where one system trusts another is a potential entry point.

And the blast radius is expanding. The Shai-Hulud worm doesn’t just steal from one victim. It weaponizes each victim’s identity to attack the next link in the chain. One compromised developer becomes a vector for compromising every project they contribute to.

This is what software supply chain attacks look like in 2026. Not one-off incidents. Campaigns. Evolving, self-replicating campaigns that get more sophisticated with each iteration.

## What You Should Change Going Forward

Beyond the immediate response, here are the structural changes that this incident demands:

**Pin your dependency versions.** Never use `latest` or unpinned ranges for critical tools in CI/CD. Pin exact versions and verify checksums.

**Use lockfiles religiously.** `package-lock.json` exists for this reason. Commit it. Review changes to it in every PR. I built a tool called [lockcheck](https://github.com/DhanushNehru/lockcheck) specifically for this purpose.

**Limit CI/CD token permissions.** GitHub Actions tokens should have the minimum permissions required. If a workflow only needs to read code, it should not have write access to packages or workflows.

**Audit preinstall hooks.** Before installing any npm package, check whether it has preinstall or postinstall scripts. Use `npm install --ignore-scripts` when appropriate and run scripts manually after review.

**Monitor your published packages.** If you maintain npm packages, set up alerts for any new version publications. An unexpected version appearing should trigger an immediate investigation.

**Never store secrets in AI tool configs.** The fact that this malware explicitly targets Claude, Kiro, and Cursor configuration files tells you that attackers know developers are storing credentials in AI tool configs. Stop doing that.

## Final Thought

Ninety-three minutes. That’s how long the malicious version was live on npm.

![Image](https://miro.medium.com/v2/resize:fit:700/0*mChEZcRk6z7yB0_u.jpg)

*Image from the movie Dune*

In that window, a self-replicating worm named after a science fiction monster stole developer credentials, cloud secrets, AI tool configurations, and cryptocurrency keys from an unknown number of machines. It used the victims’ own GitHub accounts to spread itself further. And it did all of this by publishing under the name of one of the most trusted security tools in the industry.

The passwords in your Bitwarden vault are safe. But the trust model that the entire npm ecosystem relies on just took its most serious hit yet.

Stay sharp. Check your versions. Rotate your keys. And remember: in software supply chain security, the most dangerous attack is the one that comes from a name you trust.

## Who Am I ?

Hi, I’m [Dhanush Nehru](https://youtu.be/UaNYT-5fLRw?si=Zl-8xrsQ1LmOexX9) an Engineer, Cybersecurity Enthusiast, Youtuber and Content creator. I document my journey through articles and videos, sharing real-world insights about DevOps, automation, security, cloud engineering and more.