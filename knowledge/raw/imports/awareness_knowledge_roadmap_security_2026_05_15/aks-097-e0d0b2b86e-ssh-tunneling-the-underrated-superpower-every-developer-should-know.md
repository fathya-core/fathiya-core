# SSH Tunneling: The Underrated Superpower Every Developer Should Know

**Published:** 2026-04-23

## LINUX | DEVOPS | SECURITY | CLOUD | TECHNOLOGY


## Local, Remote, Bastion, SOCKS, and Beyond


![Image](https://miro.medium.com/v2/resize:fit:700/1*T6gkFasj4_naGrfwuNy-5w.png)

## Most developers use SSH only to log into servers.

SSH is best known as a way to log into remote servers, but that barely scratches the surface, SSH is far more than just a remote access tool. Under the hood, it acts as a powerful, encrypted transport layer capable of securely carrying arbitrary TCP traffic across networks.

SSH can do much more than give us a shell. It can quietly become a secure pathway for databases, web apps, and internal services without ever exposing them to the public internet.

In this article, we’ll explore SSH tunneling: what it is, how it works, and why it’s such a versatile tool for developers and operators.

## Introduction to SSH Tunneling

### What Is SSH Tunneling

SSH tunneling (or SSH port forwarding) lets us securely send network traffic through an encrypted SSH connection. Instead of exposing services to the internet, we can tunnel them through SSH so they’re only accessible via a secure channel.

### Why It Matters

Tunneling is useful when a server is hidden behind a firewall, private network, or NAT, so we can’t access it directly. With SSH tunneling, we can still reach that service by using an existing SSH connection, without complex solutions like VPNs or firewall reconfiguration.

With a single SSH command, we can securely access remote resources, work around restrictive network rules, and keep our services hidden from the public internet.

### How It Works

SSH tunneling works by creating an encrypted connection between our local machine and a remote server, then forwarding traffic through it. This lets us access remote or internal services as if they were running locally, without exposing them to the internet.

## Local Port Forwarding (-L)

Local port forwarding lets us access a service running on a remote server as if it were on our own machine. This is commonly used to securely access things like databases or internal web apps without exposing them to the internet.

\# Example: Forwarding a PostgreSQL Database  
ssh -N -L 5432:localhost:5432 user@remote-server

*   `-L 5432:localhost:5432` → forwards our local port `5432` to remote server’s `localhost:5432`
*   `-N` → don’t run a remote shell (just tunnel)
*   `user@remote-server` → SSH login target

Now, when we connect to `localhost:5432` on our local machine, the traffic is securely forwarded through SSH to the remote server’s PostgreSQL instance.

In other words, we’re accessing the database on the remote server as if it were running locally. Even if a firewall blocks direct access to a port (like `5432` for PostgreSQL), we can still reach it through SSH.

**Verifying the Tunnel  
**We can verify the SSH tunnel by checking if the SSH process is running and if local port `5432` is listening using `lsof -i :5432`.

\# Checking the SSH process (is the tunnel even alive?)  
ps aux | grep ssh  
  
\# Checking the port (is local forwarding active?)  
lsof -i :8080  
  
\# Verify the tunnel is actually working (Listening ≠ working)  
psql -h localhost -p 5432 -U your\_db\_user your\_db\_name \# connect to psql server

**Common Problem:**

*   **Port already in use locally** → another service is using , so the tunnel can’t bind. We’ll need a different local port:

\# use a different local port  
ssh -N -L 15432:localhost:5432 user@remote-server

*   **Remote PostgreSQL not listening on localhost** → database isn’t reachable via `localhost` on the remote server

ss -lntp | grep 5432  
  
\# We should see Postgres bound to 127.0.0.1:5432 or 0.0.0.0:5432

*   **Firewall or DB config issue** → connection blocked or PostgreSQL not configured to accept connections. Check PostgreSQL config:  
    `postgresql.conf` → `listen_addresses   pg_hba.conf` → allows local connections

### Why This Is Useful

Local port forwarding isn’t just convenient, it solves real security and access problems in a simple way:

*   **Secure access without exposure —** Access services without opening them to the public internet.
*   **Bypass firewall restrictions —** Even if a port (like `5432`) is blocked, SSH can still carry the traffic.
*   **Keep sensitive services private —** Databases and internal apps stay bound to `localhost` on the server.
*   **No extra infrastructure needed —** Avoid setting up VPNs or changing firewall configurations.
*   **Works like a local connection —** Our tools connect to `localhost`, with no special configuration required.

**Tip:  
**SSH tunnels normally run in the foreground and tie up our terminal. We can run one in the background by adding `-f`:

ssh -f -N -L 5432:localhost:5432 user@remote-server

*   `-f` → sends SSH to the background after authentication, so our terminal stays free. To stop it we need to find and kill the process:

lsof -i :5432  
kill <PID>

## Remote Port Forwarding (-R)

Remote port forwarding is the opposite of local forwarding. Instead of exposing a remote service to our local machine, it exposes something that lives on our laptop to the outside world (remote server).

ssh -N -R 9000:localhost:3000 user@remote-server

*   `-R` →reverse tunnel (remote → local)
*   `9000` → port on remote server
*   `localhost:3000` → service running on our local machine

Now when we visit `http://localhost:9000` on the remote server will display the application running on our local machine’s port `3000`. In other words, the remote server acts as an entry point, but the actual service is coming from our local environment.

**Important:  
**By default, a reverse SSH tunnel only exposes the forwarded port (like `9000`) on the remote server itself at `http://localhost:9000`. It will not work at `http://remote-server.com:9000` because the port is not publicly exposed for security reasons.

If external access is needed, we must enable `GatewayPorts yes` in the SSH server configuration (`sshd_config`). This allows the forwarded port to be accessible from outside the remote server.


Remote port forwarding lets us expose a service from our local machine to a remote server, even if our machine is behind NAT or a firewall.

*   **Access local services from a remote server →** Make our local app or service reachable from the remote machine.
*   **Work around NAT and firewall limits →** No need for port forwarding or public IP on our local machine.
*   **Share local development easily →** Let others access your local app through a remote server.
*   **No deployment required →** Test or demo apps without pushing them to a public environment.
*   **Secure connection over SSH →** All traffic is encrypted and goes through a trusted channel.

## Dynamic Port Forwarding (-D)

Local (`-L`) and remote (`-R`)forwarding connect a fixed source port to a fixed destination. Dynamic forwarding turns SSH into a SOCKS5 proxy — our local port can route traffic to _any_ destination, as decided at connection time.

Dynamic port forwarding turns SSH into a SOCKS proxy which instead of sending traffic to just one fixed destination, it lets our local machine route traffic through SSH to any destination we choose while we are connected.

ssh -N -D 1080 user@remote-server

*   `-D 1080` → Creates a dynamic port forward (SOCKS proxy) on our local machine at port `1080`
*   `user@remote-server` → The SSH user and remote server

Our apps (like a browser) are configured to send their traffic to `localhost:1080` instead of going directly to the internet. Setting port `1080` as a SOCKS proxy means the browser first sends its traffic to port `1080`, and then SSH forwards it through the remote server to reach the internet.

\# Normally  
Our machine → Internet (direct)  
  
\# With SOCKS proxy:  
Our machine → SSH tunnel → Remote server → Internet → back again

Here SSH is acting like a secure middle proxy that decides where to send traffic only when the request happens.


Dynamic port forwarding turns SSH into a flexible proxy, making it useful in a variety of situations:

*   **Secure browsing on untrusted networks →** Encrypt our traffic when using public Wi-Fi.
*   **Bypass network restrictions →** Access blocked websites or services through a trusted server.
*   **Route all kinds of traffic →** Works with more than just web traffic (unlike HTTP proxies).
*   **Hide your real IP address →** Traffic appears to come from the remote server.
*   **Lightweight alternative to a VPN →** No extra setup — just a single SSH command.

## SSH Through Bastion Server

A bastion server (or jump host) is a secure gateway that sits between the public internet and a private network. Instead of exposing internal servers directly, we connect to the bastion first, then access other machines from there.

This setup is commonly used in production environments where internal servers are not publicly accessible.

ssh -J user@bastion user@private-server

*   `-J user@bastion` → Connects through the bastion (jump host)
*   `user@private-server` → The internal server we want to access

**With Port Forwarding  
**We can also combine this with tunneling. For example, accessing a database on a private server:

ssh -L 5432:localhost:5432 -J user@bastion user@private-server

*   This forwards our local port `5432` to the private server’s database through the bastion.


Using an SSH jump host (bastion) gives us a secure and controlled way to access private servers:

*   **Protect internal servers →** Private machines are never exposed to the public internet.
*   **Single entry point →** All access goes through the bastion, making it easier to monitor and control.
*   **Works with restricted networks →** Reach servers that are only accessible from inside a private network.
*   **Simplifies access management →** We only need to allow SSH access to the bastion, not every server.
*   **Combine with tunneling →** Securely access internal services (like databases) through one trusted gateway.

## Making It Permanent: `~/.ssh/config`

Instead of typing long SSH commands every time, we can store our configuration in `~/.ssh/config`. This lets us define shortcuts and reuse settings for hosts, jump servers, and port forwarding.

Host db-tunnel  
  HostName bastion.example.com  
  User deploy  
  IdentityFile ~/.ssh/id\_ed25519  
  LocalForward 5432 db.internal:5432  
  ServerAliveInterval 60  
  ServerAliveCountMax 3  
  ExitOnForwardFailure yes  
  
Host dev-expose  
  HostName public-server.com  
  User deploy  
  RemoteForward 9000 localhost:3000  
  ServerAliveInterval 60  
  
Host bastion  
  HostName bastion.example.com  
  User user  
  
Host private-server  
  HostName private.internal  
  User user  
  ProxyJump bastion

Now we can just run `ssh -fN db-tunnel` and `ssh -fN dev-expose` to start both tunnels using the SSH config we defined.

*   `db-tunnel` → Sets up local forwarding for the database,
*   `dev-expose` → Sets up reverse forwarding to expose our local app on the remote server.
*   `ssh private-server` → Connects to a private internal server through a bastion (jump) host

## AutoSSH: Persistent Tunnels

`AutoSSH` is a tool that automatically keeps our SSH tunnels alive. If the connection drops (due to network issues, timeouts, etc.), `AutoSSH` will detect it and reconnect for us.

\# Install  
apt install autossh           \# Ubuntu/Debian  
  
\# Run (same flags as ssh, just prefixed)  
autossh -M 0 -fNL 5432:db.internal:5432 deploy@bastion

*   `-M 0` → disables autossh's own monitoring port and relies instead on SSH's built-in keepalives (set via `ServerAliveInterval` in our config). This is the recommended approach for modern OpenSSH versions.

**Why This Is Useful**

*   **Keeps tunnels alive automatically →** Reconnects if the connection drops
*   **Ideal for long-running tasks →** Great for persistent database or proxy access
*   **Less manual intervention →** No need to restart SSH tunnels manually
*   **More reliable in unstable networks →** Handles intermittent connectivity issues gracefully

### Running AutoSSH as a systemd Service

To keep our SSH tunnel running in the background and survive reboots, we can run AutoSSH as a systemd service.

[

## Mastering systemd: Take Control of Your Linux System

### A practical guide to managing startup, services, and core processes.

blog.devops.dev


](https://blog.devops.dev/mastering-systemd-take-control-of-your-linux-system-5970bf6efe25?source=post_page-----e1399bf7e9ea---------------------------------------)

\# /etc/systemd/system/ssh-db-tunnel.service  
\[Unit\]  
Description=SSH tunnel to db.internal  
After=network.target  
  
\[Service\]  
User=deploy  
ExecStart=/usr/bin/autossh -M 0 -N \\  
  -o "ServerAliveInterval=60" \\  
  -o "ServerAliveCountMax=3" \\  
  -L 5432:db.internal:5432 \\  
  bastion.example.com  
Restart=always  
RestartSec=10  
  
\[Install\]  
WantedBy=multi-user.target

systemctl enable --now ssh-db-tunnel

## Best Practices

SSH tunneling is powerful, but it’s easy to misuse or leave insecure if we’re not careful. These practices help keep things safe and reliable:

*   **Use SSH keys (disable password login) →** Prefer key-based authentication for better security and automation.
*   **Limit access on the server →** Bind services to `localhost` and restrict which users can create tunnels.
*   **Avoid exposing unnecessary ports →** Only forward the ports we actually need.
*   **Use** `**~/.ssh/config**` **for consistency →** Keep configurations clean, reusable, and less error-prone.
*   **Add** `**-N**` **and** `**-f**` **for background tunnels →** Run tunnels without opening a shell when not needed.
*   **Monitor and log connections →** Especially important when using bastion (jump) hosts.
*   **Use AutoSSH or systemd for reliability →** Keep tunnels alive in unstable networks or production setups.
*   **Be careful with remote forwarding (**`**-R**`**) →** We might unintentionally expose local services to others.
*   **Prefer bastion (jump host) for private networks →** Avoid direct access to internal servers.
*   **Close tunnels when not needed →** Don’t leave unnecessary open connections running.

## Quick reference

*   `-L local:host:remote` → Local forward. Reach a remote service locally
*   `-R remote:host:local` → Remote forward. Expose a local service remotely
*   `-D port` → Dynamic / SOCKS5. Route any traffic through SSH
*   `-N` → No shell. Forward only, no command
*   `-f` → Fork to background. Combine with `-N` for fire-and-forget tunnels.
*   `ServerAliveInterval` → Keepalive. Prevent idle disconnects
*   `-C` → Enable compression. Useful on slow or high-latency links.
*   `-g` → Allow non-localhost clients to connect to our local forwarded port. Useful on shared machines.
*   `-v` → Verbose output. Run this first when something isn't working.

## Final Thoughts

Think of SSH Tunnel like a secret underground passage: Our data enters the tunnel on one end (our machine), travels securely through the SSH server, and exits at the destination.

With just a single command, SSH tunneling lets us securely access internal services, avoid exposing ports to the public internet, and route traffic through trusted paths, often replacing more complex setups like VPNs in many cases.

In this article, we’ve explored how SSH tunneling works and how to use it in practice, from local and remote port forwarding to dynamic proxies and jump hosts.

Thanks for reading! hope this article gave us a solid foundation to start using SSH tunneling in our own workflows.