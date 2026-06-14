# Secure SSH Like a Pro: 7 Steps Every Linux Admin Should Know

**Published:** 2025-11-19

![Image](https://miro.medium.com/v2/resize:fit:700/1*g-R4EISz8YlOhjQf7_kE9Q.png)


> _Because “default” shouldn’t mean “defenseless.”_

SSH is the front door to your Linux server. Leaving it open invites hackers. Brute-force attacks, misconfigured ports, and lazy defaults make your server vulnerable. The fix? **7 simple steps to harden SSH** — explained clearly, with commands and why they matter.

## 1️⃣ Disable Root Login

**Because root should never be your front door**

Direct root login = hacker shortcut. Lock it down:

sudo nano /etc/ssh/sshd\_config  
#PermitRootLogin yes → PermitRootLogin no  
sudo systemctl restart ssh

**Pro Tip:** Create a sudo admin user:

sudo adduser adminuser  
sudo usermod -aG sudo adminuser

**Why it matters:** Attackers must compromise a regular user first — extra layer of defense.

## 2️⃣ Use SSH Keys Instead of Passwords

**Because passwords are yesterday’s security**

**Generate key pair locally:**

ssh-keygen -t ed25519 -C "you@example.com"  
ssh-copy-id adminuser@your\_server\_ip

**Disable password login:**

sudo nano /etc/ssh/sshd\_config  
#PasswordAuthentication yes → PasswordAuthentication no  
sudo systemctl restart ssh

**Why it matters:** Even if your username leaks, brute-force is nearly impossible.

**Pro Tip:** Protect your private key with a password or hardware key.

## 3️⃣ Change the Default SSH Port

**Because 22 is where the bots live**

sudo nano /etc/ssh/sshd\_config  
#Port 22 → Port 2222  
sudo ufw allow 2222/tcp  
sudo ufw delete allow 22/tcp  
sudo systemctl restart ssh

**Why it matters:** Fewer automated login attempts — cleaner logs, less noise.

**Pro Tip:** Document the custom port for your team.

## 4️⃣ Use Fail2Ban or CrowdSec

**Because your firewall should fight back**

Install Fail2Ban:

sudo apt install fail2ban -y  
sudo systemctl enable --now fail2ban  
sudo nano /etc/fail2ban/jail.local

Add:

\[sshd\]  
enabled = true  
port = 2222  
maxretry = 3  
bantime = 10m  
findtime = 10m

Restart:

sudo systemctl restart fail2ban

**Why it matters:** Blocks repeated failed logins automatically.

**Pro Tip:** CrowdSec can provide community-shared IP reputation.

## 5️⃣ Restrict SSH Access by IP / Firewall

**Because not everyone deserves a key**

sudo ufw allow from 203.0.113.10 to any port 2222 proto tcp  
sudo ufw default deny incoming  
sudo ufw enable

Or with Firewalld:

sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="203.0.113.10" port protocol="tcp" port="2222" accept'  
sudo firewall-cmd --reload

**Why it matters:** Unauthorized networks cannot connect, even if the port is known.

**Pro Tip:** Use VPC firewall rules or bastion hosts in cloud setups.

## 6️⃣ Enforce Idle Session Timeouts

**Because every admin forgets to log out**

sudo nano /etc/ssh/sshd\_config  
ClientAliveInterval 300  
ClientAliveCountMax 2  
sudo systemctl restart ssh

**Why it matters:** Idle sessions auto-disconnect, reducing risk from abandoned connections.

**Pro Tip:** 5-minute intervals are safer in production.

## 7️⃣ Enable Two-Factor Authentication (2FA)

**Because even keys can be stolen**

Install PAM module:

sudo apt install libpam-google-authenticator -y  
google-authenticator

Edit PAM:

sudo nano /etc/pam.d/sshd  
auth required pam\_google\_authenticator.so

Update SSH config:

sudo nano /etc/ssh/sshd\_config  
ChallengeResponseAuthentication yes  
sudo systemctl restart ssh

**Why it matters:** Even stolen keys aren’t enough — TOTP protects access.

**Pro Tip:** Backup your 2FA secrets securely.

## 🚀 Final Words

Securing SSH isn’t paranoia — it’s responsibility. Take **30 minutes today** to lock your server. Every lazy default is a hacker invitation.

**Habit > Setup**: automate, monitor, and repeat these steps regularly.