# Linux Security Cheat Sheet

**Published:** 2026-01-01


> If you are not a Medium Premium member and cannot access this content, you can read the full version of this article for free on **postgresqlblog.com**. Click [**here**](https://postgresqlblog.com/posts/2026-01-01_Linux-Security-Cheat-Sheet-0fd019ef4fcf.html) to read.

> **A practical, copy-paste friendly guide to hardening Linux servers.**

![Image](https://miro.medium.com/v2/resize:fit:700/1*4C9A9DrKaf708bi6mkX3ug.png)

## Table of Contents

## Part 1 — The Essentials

_Fundamental hygiene and startup configurations._

1.  **System Updates** (`apt`, `yum`, `dnf`)
2.  **User Management** (`useradd`, `usermod`)
3.  **Password Policies** (`chage`, `passwd`)
4.  **Locking Root Account** (`passwd -l root`)
5.  **Basic SSH Config** (`Port`, `PermitRootLogin`)
6.  **Firewall Basics** (`ufw`, `firewalld`)
7.  **Disabling Services** (`systemctl disable`)
8.  **File Permissions 101** (`chmod`, `chown`)
9.  **Time Synchronization** (`timedatectl`, `ntp`)
10.  **Checking Active Sessions** (`w`, `last`, `who`)
11.  **Shell History Hygiene** (`history -c`)

## Part 2 — Advanced Hardening (Production Ready)

_Turning your server into a fortress with pro-level tools._

1.  **Mastering Sudoers** (`visudo`, `NOPASSWD`)
2.  **Advanced SSH Security** (`SSH Keys`, `2FA`)
3.  **Intrusion Prevention** (`fail2ban`, `jail.local`)
4.  **Immutable Files** (`chattr +i`, `lsattr`)
5.  **Access Control Lists** (`setfacl`, `getfacl`)
6.  **Port & Socket Auditing** (`ss -tulpn`, `lsof`)
7.  **Kernel Hardening** (`sysctl.conf`, `IP Spoofing`)
8.  **Process Limits** (`ulimit`, `limits.conf`)
9.  **Log Analysis & Forensics** (`journalctl`, `/var/log`)
10.  **Rootkit Scanning** (`rkhunter`, `lynis`)
11.  **Cron Job Security** (`crontab`, `/etc/cron.*`)
12.  **Legal Warning Banners** (`/etc/issue.net`)

## Part 1 — The Essentials (Day 0 Setup)

_Fundamental hygiene and startup configurations. Perform these steps immediately after provisioning a new server._

## 1\. System Updates

Security starts with patching. Never run a server with outdated packages.

\# Debian / Ubuntu  
sudo apt update && sudo apt upgrade -y  
  
\# RHEL / CentOS / AlmaLinux  
sudo yum update -y

## 2\. User Management

**Never** run applications or log in as `root`. Create a privileged user instead.

\# Create user 'oz' with a home directory and bash shell  
sudo useradd -m -s /bin/bash oz  
  
\# Set a strong password  
sudo passwd oz  
  
\# Grant Sudo privileges  
\# Debian/Ubuntu:  
sudo usermod -aG sudo oz  
  
\# RHEL/CentOS:  
sudo usermod -aG wheel oz

## 3\. Password Policies

Force users to change passwords regularly and expire old accounts.

\# Check current password aging for user 'oz'  
sudo chage -l oz  
  
\# Force password change every 90 days  
sudo chage -M 90 oz  
  
\# Lock account after 30 days of inactivity  
sudo chage -I 30 oz

## 4\. Locking Root Account

Once your sudo user is ready, lock the root account to prevent direct login.

\# Lock the root account (disables password login)  
sudo passwd -l root  
  
\# (Optional) To unlock if absolutely necessary:  
\# sudo passwd -u root

## 5\. Basic SSH Config

Edit `/etc/ssh/sshd_config` to secure the front door. _Always backup config first:_ `cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak`

\# Open config  
sudo nano /etc/ssh/sshd\_config

**Key Configuration Changes:**

Port 2222                   \# Change default port (Security through obscurity)  
PermitRootLogin no          \# The most important line!  
PasswordAuthentication no   \# Disable if using SSH Keys (Recommended)  
PermitEmptyPasswords no     \# Never allow empty passwords  
MaxAuthTries 3              \# Disconnect after 3 failed attempts  
LoginGraceTime 60           \# Disconnect if login takes > 60 secs

\# Restart SSH to apply  
sudo systemctl restart sshd

## 6\. Firewall Basics

Close all doors, then open only what you need.

**Option A: UFW (Ubuntu/Debian — Recommended for simplicity)**

\# 1. Deny everything incoming by default  
sudo ufw default deny incoming  
  
\# 2. Allow outgoing traffic  
sudo ufw default allow outgoing  
  
\# 3. Allow SSH (Adjust port if you changed it in Step 5!)  
sudo ufw allow 2222/tcp  
  
\# 4. Allow Web Traffic (If needed)  
sudo ufw allow 80/tcp  
sudo ufw allow 443/tcp  
  
\# 5. Enable Firewall  
sudo ufw enable

**Option B: Firewalld (RHEL/CentOS)**

\# Add SSH port (if custom)  
sudo firewall-cmd --permanent --add-port=2222/tcp  
  
\# Reload firewall  
sudo firewall-cmd --reload

## 7\. Disabling Services

Reduce attack surface by stopping unused services.

\# List all enabled services  
systemctl list-unit-files --state=enabled  
  
\# Stop and disable a service (e.g., postfix if not needed)  
sudo systemctl stop postfix  
sudo systemctl disable postfix

## 8\. File Permissions 101

Standardize permissions to prevent unauthorized access.

\# 755: Owner(RWX), Group(R-X), Others(R-X) -> Directories/Scripts  
chmod 755 script.sh  
  
\# 644: Owner(RW), Group(R), Others(R) -> Config files  
chmod 644 config.yaml  
  
\# 600: Owner(RW), Others(None) -> Private Keys (CRITICAL)  
chmod 600 id\_rsa

## 9\. Time Synchronization

Logs are useless if timestamps are wrong. Ensure NTP is running.

\# Enable NTP synchronization  
sudo timedatectl set\-ntp on  
  
\# Check status  
timedatectl status

## 10\. Checking Active Sessions

Before maintenance, check if anyone else is connected.

\# Who is logged in right now?  
w  
  
\# Who logged in recently?  
last -n 10  
  
\# Who failed to log in? (Brute-force check)  
sudo lastb -n 10

## 11\. Shell History Hygiene

Don’t leave sensitive commands (like passwords passed in CLI) in your history.

\# Clear current session history  
history -c  
  
\# Clear history file permanently  
cat /dev/null > ~/.bash\_history  
  
\# Prevent history logging for current session  
export HISTSIZE=0


_Turning your server into a fortress with pro-level tools and configurations._

## 12\. Mastering Sudoers (`visudo`)

Fine-tune privileges. Never edit `/etc/sudoers` directly; always use `visudo` to prevent syntax errors.

sudo visudo

**Common Configurations:**

\# 1. Passwordless Sudo (Use with caution, good for scripts/automation)  
\# User 'deploy' can run any command without password  
deploy ALL\=(ALL) NOPASSWD: ALL  
  
\# 2. Command Restriction (Least Privilege)  
\# User 'junior' can ONLY restart Nginx, nothing else  
junior ALL\=(ALL) /usr/bin/systemctl restart nginx  
  
\# 3. Group Privileges  
\# Members of 'sysadmin' group have full access  
%sysadmin ALL\=(ALL) ALL

## 13\. Advanced SSH Security

Move beyond passwords. Use Keys and Multi-Factor Authentication (MFA).

**Step A: Enforce SSH Keys Only** Ensure you have copied your key (`ssh-copy-id`) before doing this!

\# In /etc/ssh/sshd\_config  
PasswordAuthentication no  
PubkeyAuthentication yes  
ChallengeResponseAuthentication no

**Step B: 2FA (Google Authenticator)** Add a second layer of defense.

sudo dnf install libpam-google-authenticator  
google-authenticator  \# Follow on-screen setup

## 14\. Intrusion Prevention (Fail2Ban)

Automatically ban IPs that show malicious behavior (brute-force).

\# Install  
sudo dnf install fail2ban -y  
  
\# Create a local config (Never edit jail.conf directly)  
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local  
sudo nano /etc/fail2ban/jail.local  

**Key** `**jail.local**` **Settings:**

\[sshd\]  
enabled = true  
port    = ssh (or your custom port 2222)  
logpath = %(sshd\_log)s  
backend = %(sshd\_backend)s  
maxretry = 3  
bantime = 1h

\# Restart and Check Status  
sudo systemctl restart fail2ban  
sudo fail2ban-client status sshd

## 15\. Immutable Files (`chattr`)

**The Hidden Weapon.** Make critical files undeletable, even by root.

\# Lock the file (Immutable bit)  
sudo chattr +i /etc/passwd  
sudo chattr +i /etc/shadow  
  
\# Verify attributes (Look for 'i')  
lsattr /etc/passwd  
  
\# Try to delete it (Will fail: Operation not permitted)  
rm /etc/passwd  
  
\# Unlock the file (To make edits)  
sudo chattr -i /etc/passwd

## 16\. Access Control Lists (ACLs)

When standard `chmod` (User/Group/Other) isn't enough.

\# Grant 'rwx' strictly to user 'john' on a specific file,  
\# regardless of who owns it.  
setfacl -m u:john:rwx /var/www/html/index.php  
  
\# Remove ACL  
setfacl -x u:john /var/www/html/index.php  
\# View ACLs  
getfacl /var/www/html/index.php

## 17\. Port & Socket Auditing

Detect backdoors or unauthorized listeners.

\# Show all listening ports (TCP/UDP) with Process ID (PID)  
sudo ss -tulpn  
  
\# Who is holding port 8080?  
sudo lsof -i :8080  
  
\# Monitor network bandwidth per process  
sudo nethogs eth0

## 18\. Kernel Hardening (`sysctl`)

Harden the network stack against IP Spoofing and Man-in-the-Middle attacks.

sudo nano /etc/sysctl.conf

**Add/Uncomment these lines:**

\# Disable IP Packet Forwarding (If not a router)  
net.ipv4.ip\_forward = 0  
  
\# Ignore ICMP Echo Requests (Disable Ping response - Stealth Mode)  
net.ipv4.icmp\_echo\_ignore\_all = 1  
\# Protect against IP Spoofing  
net.ipv4.conf.all.rp\_filter = 1  
net.ipv4.conf.default.rp\_filter = 1  
\# Disable IPv6 (If not used)  
net.ipv6.conf.all.disable\_ipv6 = 1  
  
\# Apply changes immediately  
sudo sysctl -p

## 19\. Process Limits

Prevent DoS (Denial of Service) by limiting resources per user.

\# nano /etc/security/limits.conf  
  
\# User 'oz' can only have 50 processes  
oz hard nproc 50  
  
\# Increase open file limit for database user  
postgres soft nofile 4096  
postgres hard nofile 10240

## 20\. Log Analysis & Forensics

Finding the needle in the haystack.

\# Real-time monitoring of Auth logs  
tail -f /var/log/auth.log  
  
\# Journalctl: Show logs for SSH service only  
journalctl -u sshd --since "1 hour ago"  
  
\# Journalctl: Show only Critical and Error messages  
journalctl -p err -b

## 21\. Rootkit Scanning

Automated security auditing.

\# Install RKHunter  
sudo dnf install rkhunter \-y  
  
\# Update database  
sudo rkhunter \--propupd  
  
\# Run check  
sudo rkhunter \--check

## 22\. Cron Job Security

Malware often hides in scheduled tasks to survive reboots.

\# List current user's cron  
crontab -l  
  
\# Check system-wide crons (Inspect these folders!)  
ls -la /etc/cron.daily/  
ls -la /etc/cron.hourly/  
cat /etc/crontab

## 23\. Legal Warning Banners

Scare off script kiddies and provide legal standing.

\# Edit the banner file  
sudo nano /etc/issue.net

_Add text like: “UNAUTHORIZED ACCESS PROHIBITED. ALL ACTIVITY IS LOGGED.”_

\# Enable Banner in SSH config  
sudo nano /etc/ssh/sshd\_config  
\# Add/Uncomment:  
Banner /etc/issue.net

**Don’t try to memorize this.** Instead, **bookmark this page** or print it out.