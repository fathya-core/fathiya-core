# AI Red Team Spent Two Weeks Breaking Autonomous Agents — Here Is What They Found

**Published:** 2026-03-08


**If you enjoy these sort of articles please consider checking out my SubStack as I will soon be writing their full time.**

Autonomous AI agents are no longer a research curiosity. Teams are deploying them with email access, shell execution, persistent memory, and live network connectivity. The question of whether they are secure has largely been hand-waved away in the rush to ship. A paper released in February 2026, titled “Agents of Chaos,” makes that hand-waving significantly harder to justify.

The setup was deliberately realistic. Researchers deployed Claude Opus and Kimi K2.5 on isolated servers through a framework called OpenClaw, giving each agent the kind of tool access you would expect in a real enterprise deployment: file systems, shell access, email, and Discord. Twenty AI security researchers then spent two weeks trying to break them. Thirty-eight researchers total contributed to the analysis. The resulting 84-page paper documents eleven case studies, and the findings are not flattering.

The core problem is that these agents are highly capable and highly persuadable at the same time. Prompt injection attacks — where malicious instructions are embedded in content the agent processes, rather than in the user’s direct input — proved consistently effective. An agent reading an email, summarizing a document, or pulling data from an external source can be redirected mid-task by an adversary who controls any part of that content pipeline. The agent does not distinguish between a trusted instruction and a poisoned one the way a human operator might.

What makes this particularly uncomfortable is the blast radius. An agent with shell access that gets prompt-injected does not just return a bad answer. It executes. Researchers demonstrated scenarios where compromised agents exfiltrated data, modified files, and took actions that persisted beyond the session. Persistent memory amplifies this: a poisoned memory entry can influence agent behavior across future sessions, long after the initial attack.

The researchers also documented issues with agents operating under ambiguous authorization boundaries. When an agent is told to “handle” an email inbox, how much latitude does that actually grant? In practice, agents tended to interpret scope broadly, and in adversarial conditions that tendency became a liability.

There is no clean technical fix here. The vulnerabilities are not purely implementation bugs — they reflect something more fundamental about how large language models process and prioritize instructions. Mitigations like input sanitization, output filtering, and sandboxed execution environments help at the margins, but none of them close the threat surface entirely.

The practical takeaways for security teams are straightforward, if uncomfortable. First, treat any AI agent with real-world tool access as a privileged system and apply the same scrutiny you would give a service account with broad permissions — audit its actions, constrain its scope, and assume compromise is possible. Second, the content these agents process is now part of your attack surface. Documents, emails, and web content fed to an agent are potential injection vectors, and your threat model needs to account for that explicitly.

The organizations rushing to deploy autonomous agents in 2026 are, in many cases, doing so without a security framework that maps to how these systems actually fail. This paper is a detailed account of how they fail. Read it before your next deployment review.