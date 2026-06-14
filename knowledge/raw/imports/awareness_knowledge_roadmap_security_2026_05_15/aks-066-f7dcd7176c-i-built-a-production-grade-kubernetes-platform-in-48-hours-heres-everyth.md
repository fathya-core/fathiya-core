# I Built a Production-Grade Kubernetes Platform in 48 Hours. Here’s Everything That Went Wrong (And How I Fixed It)

**Published:** 2026-01-16


Last week, I challenged myself to build a complete DevSecOps infrastructure from scratch. Not a toy project with a single nginx pod, but the real thing: a multi-node Kubernetes cluster with GitOps, secrets management, observability, and automated deployments.

The kind of setup you would actually find in production.

I gave myself 48 hours. I hit every wall imaginable. And I learned more in those two days than in months of tutorials.

This is that story.

## Why I Did This

I was tired of the gap between what DevOps tutorials teach and what companies actually expect. Every job posting asks for “production Kubernetes experience,” but how do you get that without already having the job?

So I decided to build my own production environment. Something I could point to and say: “I designed this. I debugged this. I understand how all these pieces fit together.”

The goal was simple: deploy a complete platform that demonstrates real-world DevSecOps practices. Infrastructure as Code. Configuration management. GitOps workflows. Centralized secrets. Full observability.

No shortcuts. No managed services doing the heavy lifting.

## The Architecture

Here is what I set out to build:

**Infrastructure Layer**

*   Three EC2 instances on AWS (one master, two workers)
*   Private subnet with bastion access
*   Terraform for provisioning everything

**Cluster Layer**

*   Kubernetes installed via kubeadm
*   Calico for pod networking
*   MetalLB for load balancing in a bare-metal-style environment

**Platform Layer**

*   Traefik as the ingress controller
*   cert-manager for TLS automation
*   HashiCorp Vault for secrets
*   External Secrets Operator to sync Vault secrets into Kubernetes

**Delivery Layer**

*   ArgoCD for GitOps deployments
*   A custom three-tier application (frontend, backend, database)

**Observability Layer**

*   Prometheus for metrics collection
*   Grafana for visualization
*   Traefik metrics integration

![Image](https://miro.medium.com/v2/resize:fit:700/1*LF2C78eZXTgXrES_CDK_2Q.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*qcUM_BHs8b22nqy6NVepSQ.png)

Sounds straightforward on paper. Reality had other plans.

## Hour 1–4: The Foundation Crumbles

Terraform did its job beautifully. Within twenty minutes, I had three EC2 instances running in a private subnet, security groups configured, and SSH access through the master node acting as a bastion.

Then came kubeadm.

The first cluster initialization failed silently. No error messages, just a control plane that never became ready. After thirty minutes of staring at kubectl logs, I discovered the culprit: t3.small instances do not have enough memory to run a Kubernetes control plane.

**Lesson learned:** Kubernetes has real resource requirements. The master node needs at least 2GB of RAM. I upgraded to t3.medium instances and watched the cluster come alive.

![Image](https://miro.medium.com/v2/resize:fit:700/1*DV7YBru6Ztgp-P1WahZhzw.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*gaOLgl_5V6rU8N_xP1VvAA.png)

## Hour 5–12: The Networking Nightmare

With a working cluster, I moved on to the platform services. MetalLB installed without issues. Traefik deployed successfully. I created my first Ingress resource, configured a nip.io hostname, and tried to access my service.

Nothing.

The curl request just hung. No timeout, no error, no response.

This began a six-hour debugging session that taught me more about Kubernetes networking than any course ever could.

The problem was layered. First, Traefik was configured to listen only on the websecure entrypoint, but I was making HTTP requests. Then, when I fixed that, I discovered the Ingress was referencing a TLS secret that did not exist, causing Traefik to silently fail to configure the route.

The fix was embarrassingly simple once I understood it:

apiVersion: networking.k8s.io/v1  
kind: Ingress  
metadata:  
  name: my-service  
  annotations:  
    traefik.ingress.kubernetes.io/router.entrypoints: web  
spec:  
  ingressClassName: traefik  
  rules:  
  \- host: myapp.10.0.1.200.nip.io  
    http:  
      paths:  
      \- path: /  
        pathType: Prefix  
        backend:  
          service:  
            name: my-service  
            port:  
              number: 80

No TLS block. Explicit HTTP entrypoint. Simple routing.

![Image](https://miro.medium.com/v2/resize:fit:700/1*0dHUabkogEfOToXXJIT0BQ.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*86zPW1NDBHBUzBC8a_9fKA.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*RIGlcpsdQyyu4XKTNfOOMg.png)

**Lesson learned:** When something fails silently in Kubernetes, check the controller logs. Traefik was logging the TLS secret error the entire time. I just was not looking in the right place.

## Hour 13–18: Secrets That Refuse to Sync

HashiCorp Vault installed easily in dev mode. I stored some secrets, verified they were there, and set up External Secrets Operator to pull them into Kubernetes.

The ExternalSecret resource showed “SecretSynced: True” but the actual Kubernetes Secret was empty.

Another debugging rabbit hole.

The issue was the Vault path. When you use Vault’s KV v2 secrets engine, the actual data lives at `secret/data/mypath`, not `secret/mypath`. The API path includes an extra `data` segment that the UI hides from you.

apiVersion: external-secrets.io/v1  
kind: ExternalSecret  
metadata:  
  name: taskapp-secrets  
  namespace: taskapp  
spec:  
  refreshInterval: 1h  
  secretStoreRef:  
    name: vault-backend  
    kind: ClusterSecretStore  
  target:  
    name: taskapp-secrets  
  data:  
    \- secretKey: DB\_PASSWORD  
      remoteRef:  
        key: secret/data/taskapp/config  \# Note the /data/ segment  
        property: DB\_PASSWORD

Once I fixed the path, secrets flowed from Vault into my application pods automatically.

![Image](https://miro.medium.com/v2/resize:fit:700/1*uADIxqsThJwK-7Y1dFl_8w.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*7pPdiXhoc1NzhkEpjtqC8A.png)

**Lesson learned:** Always check the actual API paths, not just what the UI shows you. Documentation can be misleading when different versions of a tool behave differently.

## Hour 19–30: ArgoCD and the GitOps Revelation

Installing ArgoCD was the easy part. Getting it accessible from my browser was not.

My setup used SSH tunnels for access since the cluster lived in a private subnet. When I tunneled port 9090 to the MetalLB IP and tried to access ArgoCD, I got a 404 error.

The problem was subtle. Traefik routes based on the Host header. When you access `argocd.10.0.1.200.nip.io:9090`, your browser sends a Host header that includes the port number. But the Ingress was configured to match just the hostname without the port.

The solution was to tunnel on port 80 directly:

sudo ssh -i k8s-key.pem ubuntu@master-ip -L 80:10.0.1.200:80 -N

Then add entries to my local hosts file pointing to 127.0.0.1. The Host header now matched exactly, and ArgoCD appeared.

![Image](https://miro.medium.com/v2/resize:fit:700/1*NeraZbE38vNxE88gXMbJow.png)

With ArgoCD working, I finally experienced the magic of GitOps. I pushed a change to my GitHub repository, updating the container image tag from v1 to v2. Within seconds, ArgoCD detected the change and rolled out the new version automatically.

No kubectl commands. No manual intervention. Just git push and watch.

**Lesson learned:** Host-based routing and SSH tunnels do not mix well unless you handle the port issue. For demos, always tunnel on the standard ports.

## Hour 31–40: The Observability Gap

Prometheus and Grafana deployed through the kube-prometheus-stack Helm chart. But the Traefik dashboard in Grafana showed nothing but “No data” panels.

The issue was that Prometheus was not scraping Traefik. I needed to create a ServiceMonitor, but ServiceMonitors only work if the Prometheus Operator is running. And the operator had been scaled to zero replicas due to memory pressure earlier in the project.

Scaling it back up revealed another problem: the operator was crash-looping due to a missing TLS certificate for one of its own ServiceMonitors. This was a pre-existing issue in the Helm chart installation that I had to work around.

Eventually, I got the operator stable enough to process my Traefik ServiceMonitor:

apiVersion: monitoring.coreos.com/v1  
kind: ServiceMonitor  
metadata:  
  name: traefik  
  namespace: traefik  
  labels:  
    release: prometheus  \# This label is critical  
spec:  
  selector:  
    matchLabels:  
      app.kubernetes.io/name: traefik  
  endpoints:  
    \- port: metrics  
      interval: 15s

The `release: prometheus` label was the key. Without it, the Prometheus Operator ignores the ServiceMonitor entirely.

![Image](https://miro.medium.com/v2/resize:fit:700/1*B-ESiTXtf2Jypfyj0hYJqQ.png)

**Lesson learned:** The Prometheus Operator uses label selectors to discover ServiceMonitors. Always check what labels your Prometheus instance expects.

## Hour 41–48: Putting It All Together

With all the pieces working, I deployed my actual application through the GitOps pipeline:

1.  Pushed the Kubernetes manifests to GitHub
2.  Created an ArgoCD Application pointing to the repository
3.  Watched ArgoCD sync the resources automatically
4.  Verified the application was accessible through Traefik
5.  Confirmed the secrets were injected from Vault
6.  Checked the metrics were flowing in Grafana

Everything worked together. A change to the Git repository triggered a deployment. Secrets stayed out of Git and flowed securely from Vault. Metrics showed request rates and response times in real-time.

![Image](https://miro.medium.com/v2/resize:fit:700/1*zI_MNwdbgfMQaVpEJppUDw.png)

## What I Would Do Differently

**Start with larger instances.** The time I spent debugging memory-related issues was not valuable learning. It was just frustration.

**Set up observability first.** Having Prometheus and Grafana running from the beginning would have made debugging much easier. You cannot fix what you cannot see.

**Read the controller logs immediately.** Every Kubernetes controller logs its errors. Traefik, cert-manager, ArgoCD, External Secrets Operator. When something does not work, the answer is almost always in the logs.

**Test each component in isolation.** I tried to install everything at once and debug the interactions. It would have been faster to verify each piece worked independently first.

## The Final Stack

Here is what I ended up with:

Component Purpose Status Terraform Infrastructure provisioning Working Ansible Node configuration Working kubeadm Cluster installation Working Calico Pod networking Working MetalLB Load balancer Working Traefik Ingress controller Working cert-manager TLS automation Working HashiCorp Vault Secrets storage Working External Secrets Operator Secrets sync Working ArgoCD GitOps deployments Working Prometheus Metrics collection Working Grafana Visualization Working

![Image](https://miro.medium.com/v2/resize:fit:700/1*V_w-Fvmp6V8GPaxpweCbXw.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*Xd-FAspioKg9QuN-NQ17pQ.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*A-_41HiEjEJUFOxk-if0jA.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*C9d0RD2j0CP9tpV0HFhfIw.png)![Image](https://miro.medium.com/v2/resize:fit:700/1*U6DB4PSlVEZf4bQBw5FYVA.png)

## Was It Worth It?

Absolutely.

I now have a GitHub repository that demonstrates actual production practices. Not theoretical knowledge from a course, but a working system I built and debugged myself.

More importantly, I understand why these tools exist. I know what problems Vault solves because I tried managing secrets without it. I understand why GitOps matters because I experienced the alternative. I appreciate observability because I spent hours debugging without it.

If you are trying to break into DevOps or level up your skills, I cannot recommend this approach enough. Pick an ambitious project, give yourself a deadline, and build it.

You will hit walls. You will get frustrated. You will learn.

The code is available on my GitHub if you want to try it yourself or use it as a reference: [github.com/NanaGyamfiPrempeh30/k8s-devsecops](https://github.com/NanaGyamfiPrempeh30/k8s-devsecops)

## What is Next

I am planning to extend this project with:

*   Istio service mesh for advanced traffic management
*   Velero for backup and disaster recovery
*   GitHub Actions for CI pipeline integration
*   Network policies with Calico for pod-level security

Follow me if you want to see how those additions go. I suspect there will be more debugging stories to tell.

_If you found this useful, consider following me for more hands-on DevOps content. I write about the messy reality of building infrastructure, not just the polished tutorials._

**Tags:** DevOps, Kubernetes, GitOps, ArgoCD, HashiCorp Vault, Terraform, Infrastructure as Code, Platform Engineering, Cloud Native, AWS