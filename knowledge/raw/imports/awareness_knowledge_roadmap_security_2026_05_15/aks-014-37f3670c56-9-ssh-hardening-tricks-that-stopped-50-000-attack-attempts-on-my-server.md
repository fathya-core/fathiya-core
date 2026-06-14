# 9 SSH Hardening Tricks That Stopped 50,000 Attack Attempts on My Server

**Published:** 2026-02-17

![Image](https://miro.medium.com/v2/resize:fit:700/1*kk0Ab93-_Ux5-ovCAwJfgA.png)


## How I went from dozens of daily breach attempts to virtually zero intrusions using these battle-tested configurations


When I checked my server logs last January, my heart sank.

Over **50,000 failed SSH login attempts in just 30 days**.

![Image](https://miro.medium.com/v2/resize:fit:700/1*If5YxvgUXI9pWx2wpdsJsA.png)

Bots were hammering my default port 22 with common usernames and passwords, trying to brute-force their way in.

That day changed everything about how I approached SSH security.

Today, I’m sharing the **nine hardening techniques** that transformed my server from a constant target into a digital fortress. These aren’t theoretical best practices — they’re **battle-tested configurations** I’ve refined over the past year across dozens of production servers.

**Let’s dive in.**

## 1\. Kill Root Login (The First Rule of SSH Club)

**The wake-up call:** 98% of automated attacks target the `root` user.

Here’s the brutal truth: if you allow root login over SSH, you’re basically leaving your front door wide open with a neon **“WELCOME HACKERS”** sign.

### Why this matters

Direct root access means attackers only need to crack **one account** to own your entire system.  
No audit trail. No accountability. No second chances.

### The fix

\# /etc/ssh/sshd\_config  
PermitRootLogin no

That’s it. **One line. Massive impact.**

### What I do instead

I use a regular user with sudo privileges. This creates an audit trail and forces attackers to compromise **two layers** instead of one.

\# If root is needed for automation  
PermitRootLogin prohibit-password

**Pro tip:** Always confirm sudo access before disabling root login.  
I once locked myself out of a VPS at 2 AM. Never again.

## 2\. SSH Keys or GTFO (Disable Passwords)

After this change alone, my failed authentication attempts dropped **99.7%**.

### Why passwords are terrible

Passwords are vulnerable to:

*   Brute force attacks
*   Dictionary attacks
*   Credential stuffing
*   Human memory (we choose awful passwords)

SSH keys eliminate password guessing entirely.

### The configuration

\# /etc/ssh/sshd\_config  
PubkeyAuthentication yes  
PasswordAuthentication no  
PermitEmptyPasswords no  
ChallengeResponseAuthentication no  
UsePAM yes

### Proper setup

**Generate a modern key**

ssh-keygen -t ed25519 -a 100 -C "your\_email@example.com"

ED25519 is fast, secure, and the modern standard.

**Copy it to your server**

ssh\-copy\-id \-i ~/.ssh/id\_ed25519.pub user@server

**Test in a second terminal**

ssh -i ~/.ssh/id\_ed25519 user@server

Never disable passwords until this works.

## My key strategy

*   Work servers → password-protected key
*   Personal servers → separate key
*   CI/CD → restricted key with forced commands

## 3\. Move SSH Off Port 22 (Yes, It Works)

Yes, it’s “security through obscurity.”  
And yes — it **dramatically reduces attacks**.

### Real numbers

*   Port 22 → 50,000+ attacks/month
*   Custom port → 12 attacks/month
*   Reduction → **99.98%**

### Configuration

Port 2849

### Firewall update (critical)

sudo ufw allow 2849/tcp  
sudo ufw delete allow 22/tcp  
sudo ufw enable

**Always test from another session first.**

## 4\. Rate Limiting: Slow Attackers to a Crawl

MaxAuthTries 3  
MaxSessions 2  
LoginGraceTime 30  
MaxStartups 10:30:60

This configuration turns brute-force attacks into multi-month efforts instead of hours.

## 5\. Whitelist Who Can SSH

Only users who **need SSH** should have it.

AllowGroups sshusers admins

sudo groupadd sshusers  
sudo usermod -aG sshusers alice

I use:

*   `sshusers` → normal access
*   `admins` → privileged access
*   `DenyUsers` → compromised accounts

## 6\. Disable Everything You Don’t Use

X11Forwarding no  
AllowTcpForwarding no  
AllowAgentForwarding no  
PermitTunnel no  
GatewayPorts no  
IgnoreRhosts yes  
HostbasedAuthentication no

### Conditional access (recommended)

Match User developer  
    AllowTcpForwarding yes  
    PermitOpen localhost:5432 localhost:3306

Default locked down. Exceptions only where needed.

## 7\. Use Modern Cryptography

Old SSH defaults still allow **broken algorithms**.

### Secure configuration

Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com  
MACs hmac-sha2-512\-etm@openssh.com,hmac-sha2-256\-etm@openssh.com  
KexAlgorithms curve25519-sha256  
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512  
PubkeyAcceptedAlgorithms ssh-ed25519,rsa-sha2-512

### Regenerate host keys

sudo rm /etc/ssh/ssh\_host\_dsa\_key\*  
sudo ssh-keygen -t ed25519 -f /etc/ssh/ssh\_host\_ed25519\_key -N ""

Clients will see a warning once. That’s expected.

## 8\. Logging: Your Security Cameras

LogLevel VERBOSE

Logs:

*   Ubuntu/Debian → `/var/log/auth.log`
*   RHEL/CentOS → `/var/log/secure`

### fail2ban (mandatory)

sudo apt install fail2ban

\[sshd\]  
enabled = true  
port = 2849  
maxretry = 3  
bantime = 3600

This blocks repeat offenders automatically.

## 9\. Two-Factor Authentication (Final Boss)

Perfect for:

*   Production servers
*   Internet-facing hosts
*   Bastion servers

### Enable key + 2FA

AuthenticationMethods publickey,keyboard\-interactive

sudo apt install libpam-google-authenticator  
google-authenticator

### Selective enforcement

Match Group admins  
    AuthenticationMethods publickey,keyboard\-interactive

Admins get 2FA. Service accounts don’t.

## 🎯 Production-Ready `sshd_config`

Port   
PermitRootLogin no  
PubkeyAuthentication yes  
PasswordAuthentication no  
AllowGroups sshusers admins  
MaxAuthTries   
LogLevel VERBOSE  
X11Forwarding no  
AllowTcpForwarding no

## 💭 Final Thoughts

SSH hardening isn’t about perfection.  
It’s about making your server **not worth the effort**.

Implement **one change today**. Then another tomorrow.

Security compounds.

Stay safe. 🔒

## Quick Reference

sudo sshd \-t  
sudo systemctl restart sshd  
ssh \-vvv user@server \-p 2849  
sudo fail2ban\-client status sshd

[

## 10 Hidden Linux Admin Gems I Wish I Knew Earlier (And You Should Too)

### A practical guide to lesser-known Linux administration features and commands that can dramatically improve your…

blog.stackademic.com


](/10-hidden-linux-admin-gems-i-wish-i-knew-earlier-and-you-should-too-f7a31ba092a0?source=post_page-----6499b7b756bf---------------------------------------)