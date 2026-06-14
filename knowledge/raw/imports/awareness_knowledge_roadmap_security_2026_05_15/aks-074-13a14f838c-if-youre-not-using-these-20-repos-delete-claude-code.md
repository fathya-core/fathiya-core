# If You’re Not Using These 20 Repos, Delete CLAUDE CODE

**Published:** 2026-05-01


![Image](https://miro.medium.com/v2/resize:fit:700/1*hfE487dmFZDmicnAlWtQBQ.png)

Most people I know use Claude Code like a slightly smarter autocomplete. They open the terminal, type a vague prompt, accept whatever it spits out, repeat.

Then they wonder why the developer two desks over is shipping features five times faster with the exact same tool.

I wondered the same thing for a while. Last spring I caught myself rewriting the same prompt for the third time in a week, losing context every session, and quietly resenting the people who seemed to make Claude do anything. So I went hunting for what they were doing differently.

It wasn’t a secret model. It wasn’t a leaked feature. It was repos. Hundreds of them. Skills, plugins, hooks, subagents, memory systems, MCP servers, a whole layer of community infrastructure that quietly turns Claude Code from “fine” into “ridiculous.”

Here are the 20 I actually use. If you’re not running at least half of these, you’re paying for a Ferrari and driving it in second gear.

### Start with the official stuff

Before you go community-shopping, install what Anthropic ships.

**1\. anthropics/claude-code:** the main repo. 55k+ stars. You already have it, but the README has setup tricks most people skip.

**2\. anthropics/skills:** the official skills library (37.5k stars). PDF, DOCX, XLSX, PPTX, image generation. If you ever need Claude to produce a Word doc that doesn’t look like a hostage note, this is where you start.

**3\. anthropics/anthropic-cookbook:** recipes for tool use, RAG, agent patterns, classification. I keep going back to this one.

**4\. anthropics/claude-code-action:** a GitHub Action that lets you @claude inside a PR comment and get a code review. Took me ten minutes to set up.

### The awesome lists that save you from midnight GitHub-scrolling

**5\. hesreallyhim/awesome-claude-code:** 28.5k stars. The master index. Only Claude itself is allowed to submit PRs, which is a flex I respect.

**6\. ComposioHQ/awesome-claude-skills:** 50+ production-tested skills. Postgres, deep research, root-cause tracing. Install via `/skill add`.

**7\. ComposioHQ/awesome-claude-plugins:** same vibe for plugins. Frontend design, artifact builders, connect-apps.

### Skills that punch way above their weight

**8\. obra/superpowers:** 148k stars and the most popular skills library out there. It runs Claude through brainstorm → spec → plan → TDD → review → merge with subagent orchestration baked in. After I installed it, I stopped writing my own planning prompts entirely.

**9\. travisvn/awesome-claude-skills:** community-curated, 22k+ installs. SEO, marketing, design, security. Bonus points for actually warning you about untrusted skills.

### Subagents (the real unlock)

A single Claude session gets cluttered fast. Half-read files, stale debug output, lost context. Subagents fix this by handing you a team of specialists instead of one overworked generalist.

**10\. wshobson/agents:** 25k+ stars. Production subagents for strategy, dev, security, design, data, research. Drop-in.

**11\. baryhuang/claude-code-agents:** 59 specialized agents. TypeScript, Python, Java, Kotlin reviewers. Great if you’re onboarding a new team.

### MCP servers (the bridges to your stack)

On its own, Claude Code only reads files and runs commands. MCP servers connect it to the actual tools you work in.

**12\. github/github-mcp-server:** official, and the most-used MCP server in the ecosystem. PRs, issues, CI/CD, the whole platform.

**13\. microsoft/playwright-mcp:** browser automation through MCP. Claude can navigate, fill forms, scrape dynamic content.

**14\. crystaldba/postgres-mcp:** safe Postgres access. Read-only by default. Stop hand-typing SQL into your terminal.

**15\. upstash/context7:** pulls real-time, version-specific library docs into your prompts. No more Claude inventing APIs that don’t exist.

**16\. zilliztech/claude-context:** semantic code search for huge repos. Finds the right file without you breadcrumbing it.

### Orchestration and memory

Claude’s biggest weakness is amnesia. Every session starts from zero. These fix that.

**17\. ruvnet/claude-flow:** 11.4k stars. Multi-agent orchestration with persistent memory. Reshapes how teams build with AI.

**18\. smtg-ai/claude-squad:** 5.6k stars. Terminal multiplexer for AI coding agents. Run parallel sessions without chaos.

**19\. thedotmack/claude-mem:** long-term memory through context compression. Solves the #1 Claude Code complaint in a single repo.

### And one to keep you honest

**20\. nizos/tdd-guard:** 1.7k stars. Automated TDD enforcement. Blocks Claude from skipping tests, then explains why it blocked it. I love and hate this one in roughly equal measure.

### Bonus: AnotherWrapper

![Image](https://miro.medium.com/v2/resize:fit:700/0*bvu1TX8KZn3GTvDV.png)

Want to build your own AI apps and tools without starting from scratch?  
Now is a great time to create AI apps and print money fast.

Another Wrapper gives you 10 customizable AI demo apps to choose from. Pick one, add a feature, and you can start your startup and make money fast.

**_Try here:_** [**_Anotherwrapper.com_**](https://anotherwrapper.com/?atp=limited)

This isn’t even close to the full picture. The Claude Code ecosystem moves so fast that anything I write here will be partially outdated by the time you finish reading. If you want to keep up, ClaudeWave (claudewave/claudewave) tracks 3,800+ repos and updates every twelve hours.

But here’s the thing: install five of these, and you’ll already be ahead of 95% of the people paying for the same Claude subscription you do. They’re using a tool. You’ll be using a workshop.