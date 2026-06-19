# AI Agents: Complete Course

**Published:** 2025-12-06


## From beginner to intermediate to production.


![Image](https://miro.medium.com/v2/resize:fit:700/1*PvPPSGJ9779FTWmtK_Yeyw.png)

If you’ve been paying attention to AI in 2025, you’ve probably noticed that everyone is talking about agents. And for good reason. AI agents can handle everything from simple everyday tasks to complex, multi-agent workflows at enterprise scale.

And this is just the beginning. We’re about to see a lot more innovation in this space.

If you’re new here, I’m Marina. I’m a Senior Applied Scientist at Amazon working on Gen AI, and today I’m breaking down everything you need to know about building and working with AI agents.

I’ve gone deep on my research for this topic. I took a bunch of different courses, read books, and built my own agents. My research notes ended up being about 150 pages long, and I’ve distilled all this down for you into one post.

Here’s how we’re going to break it down:

**First, the basics.** What is an AI agent, what are the core concepts, and where can you actually use them? We’ll also cover some no-code options if you want to start experimenting without writing any code.

**Then, intermediate level.** We’ll get into building and evaluating multi-agent systems that solve real problems. I’ll do a demo of an agentic system I made that is currently saving me several hours of work a week.

**Then advanced.** What does it actually take to build reliable agent systems in production?

**And finally, a bonus section** for the devs who want to go deep and understand the nitty gritty of how tools like Claude Code actually work under the hood.

Whether you’re a non-technical person just trying to automate parts of your own workflow or you’re building production AI systems for your company, this post has something for you.

Let’s dive in.

## BEGINNER

### What is an Agent?

Alright, let’s start with the basics: what actually _is_ an AI agent?

Here’s the simplest way to think about it. Imagine you need to write an essay. If you use a traditional LLM prompt, you’d basically say, “Hey ChatGPT, write me an essay about how to get started in the gym,” and it just writes the whole thing in one shot from start to finish.

But that’s not how you or I would actually write an essay, right? We don’t just create a perfect first draft in one go. We plan, outline, do some research, write a messy draft, read it over and and revise. It’s a process.

That’s what agentic AI does. Instead of asking the AI to do everything in one linear pass, you let it work iteratively the way a human would.

![Image](https://miro.medium.com/v2/resize:fit:700/1*M4zkBp0_iDS4cxkxzxxPCQ.png)

So what does that actually look like?

Let’s stick with our essay example. Here’s how an agent would tackle it:

First, it starts with an outline. It figures out the structure before diving into writing. What are the main points? What order makes sense?

Then it figures out what information it needs from the outline, and actually gets that information.

It might search the web, pull from APIs, or download relevant sources, and then use this information to write the first draft of the essay.

![Image](https://miro.medium.com/v2/resize:fit:700/1*LnYu1985dYkYMI_VUlUz8Q.png)

But the neat part is that it doesn’t stop there. The agent reflects on its own work and revises to do things like tighten up weak arguments, add missing information, or improve the flow.

This is what people call the ReAct loop. The model reasons about what to do next, acts (often by calling a tool, which we’ll talk about later), observes the result, then either gives you an answer or loops back to reason again.

![Image](https://miro.medium.com/v2/resize:fit:700/1*Ox7qd-sAk5SsOQ58mOFz6A.png)

This works because each pass adds depth. You get stronger reasoning, fewer hallucinations, and better organization, which is all the stuff that gets lost when you try to do everything in one shot.

This approach works well anywhere you need careful, accurate work with proper sourcing. You can think about domains like legal research where you need to cite specific cases, healthcare documentation, or customer support systems that need to look up account details before responding.

Of course, the extra specialization and accuracy come with costs in terms of complexity. So that raises an obvious question: what kinds of tasks are actually worth building agents for?

### What kinds of tasks are agents good for?

Some tasks make sense for agents, and some don’t. Let’s take a look at some examples, from simplest to most complex.

A really simple example of an agentic system could be extracting key fields from invoices, then saving them to a database. Tasks with clear, repeatable processes like this are perfect for agents.

A mid-complexity could be responding to customer emails. The agent looks up the order, checks the customer record, and drafts a response for a human to review.

One level up is a full customer service agent that handles questions like “Do you have blue jeans in stock?” or “How do I return this purchase?” For returns, the agent needs to verify the purchase, check the policy, confirm if a return is allowed, then walk through the whole return process which has a lot of steps. The agent has to figure out what the steps are, not just follow a script.

A helpful way to think about which use cases make sense for agents is with a matrix that has two axes: complexity and precision.

Some problems have both high complexity and a need for high precision like filling out tax forms.

Others are complex but don’t need perfect accuracy. In this case you could think about something like writing and checking summaries of lecture notes.

![Image](https://miro.medium.com/v2/resize:fit:700/1*J2A-l0pWred9hFfBxRfN3A.png)

The biggest value often comes from high-complexity work, and the fastest early wins tend to be on the lower-precision side. That’s why the high-complexity, low-precision quadrant is often the smart starting point. You get leverage from automating something tricky without being blocked by needing perfect output every time.

So to summarize, agents really shine when tasks need iteration, research, or multi-step processes. It often makes sense to start with complex tasks that can handle slightly less accuracy.

### Spectrum of Autonomy

Okay, now that you know what agents are good for, let’s talk about how to actually build them. And the first big decision you need to make is how much autonomy do you want to give your agent?

Think of this as a spectrum.

![Image](https://miro.medium.com/v2/resize:fit:700/1*eMnkOy0LzFH-igI1xGA_wQ.png)

On one end, you have scripted agents where you hard-code every step. Like for our essay-writing example that might be first generate search terms, call web search, fetch pages, then write the essay. Done. It’s deterministic, predictable, and easy to control. The model’s only job is generating the actual text because you’ve decided everything else.

On the other end, you have **highly autonomous agents**. Now the LLM decides whether to search Google, news sites, or research papers. It figures out how many pages to fetch, whether to convert PDFs, and whether to reflect and revise. It might even write new functions and run them. This is more powerful, but it’s also unpredictable and harder to control.

In practice, most real-world agents sit somewhere in the middle and are semi-autonomous. The agent picks from tools you’ve defined and makes decisions within guardrails you set.

### Context Engineering

But how does an agent know what tools are available or how to make decisions?

This is something called “context engineering,” which is when you decide what information the agent has. This includes things like background of the task, the agent’s role, memory of past actions, and available tools.

If you put all of this context together, this context steers a non-deterministic model toward consistent, high-quality outputs.

![Image](https://miro.medium.com/v2/resize:fit:700/1*y3eU7GqDn5Q56vuOZ1saqQ.png)

That’s the practical foundation of “intelligence” in agents. It’s not the model alone. It’s how you engineer the context around it. We’ll talk more about these components throughout the course.

### Task Decomposition

Once the agent has its context, it’s time to define the tasks it is supposed to do. Figuring out these tasks is arguably the most important thing you’ll learn about building agents.

Start with how _you’d_ do the task. Then for each step, ask: “Can an LLM do this? A small bit of code? An API?” If the answer is no, split it smaller until it is.

Let’s stick with our example of building an agent to write an essay.

Think about how you’d actually write, then figure out how an AI might do that task. It might go something like:

*   **Outline** using an LLM
*   **Generate search terms** using an LLM, then call a search API
*   **Fetch pages** using a Tool
*   **Write draft** with an LLM using those sources
*   **Self-critique** the draft using an LLM to reflect and list gaps
*   **And revise using an LLM**

Each step is small, checkable, and clear. When the output isn’t good enough, you know exactly which step to improve.

## INTERMEDIATE

### Evaluation

Alright, now that we have the fundamentals and we’re moving into intermediate territory.

We’re going to start with something really boring. But, this is the stuff that separates hobbyists from professionals: How you measure its performance.

Sometimes, evaluations can be as simple as measuring the number of times your output is correct. If I ask my customer service chatbot if we have a certain item in stock, does it get that

But not everything is that clean-cut, though. Let’s think about our essay-writing agent. How do you measure if the essay is actually _good_?

One approach is to use a second LLM to judge the output. Have it rate each essay on a 1-to-5 scale for quality using a consistent grading rubric.

![Image](https://miro.medium.com/v2/resize:fit:700/1*aQJZlDtYhPBTlPzCPKyyVg.png)

You can evaluate your system at the component level to make sure each individual step is working, and end-to-end to judge the final quality of the whole system.

If you find the system isn’t working as well as you’d like, one first step is to examine the intermediate steps, which are called the trace. This includes things like the search queries the agent wrote, drafts, and thinking steps. If you read through this you may notice patterns like overly-generic queries, or that the revision step isn’t getting passed the critique properly.

Those observations become your next evals or your next fixes.

It’s important that you start evaluating right away, but also that you don’t worry about having a perfect evaluation system from the get-go. You can get something working quickly and iterate over time.

### Memory

Now that we have a simple system set up and some way to measure performance, it’s time to actually work on improving that performance. Memory is a really common way to do this.

Memory is what lets an agent remember what worked, what failed, and what to do differently next time, so it actually improves on each run. You might have short-term memory that agents use to write down their work as they go. In multi-agent systems, other agents can read those notes. After the agent finishes a task, it can reflect on what it did, compare the result to what was expected, figure out what went well and what didn’t, and store those lessons in long-term memory.

Next time it runs, it loads up those lessons and applies them.

This can be used to “train” agents, similar to supervised learning. You can give the agent feedback on its work so that over time each run improves in quality. I’ll show an example of that in the demo at the end of this section.

So memory is dynamic and is updated on each run. Knowledge, on the other hand, is static reference material you load up front. PDFs, CSVs, documentation, or access to your database. You give it to the agent once, and it can pull from that library whenever it needs to cite something accurate.

### Guardrails

Once we have an agent set up with its task, knowledge, and memory, we’re ready to let it go bananas! Right?

Not quite. There’s a really important step we haven’t talked about.

Because LLMs are non-deterministic, they can make mistakes. Maybe they write something that is factually wrong, or in the wrong format.

To prevent issues, we need to add guardrails to the system.

Guardrails are basically a quality gate between what the agent says is done and the task actually being finalized.

There are three main approaches to guardrails, and most production systems use at least two.

For deterministic stuff like output format and length, we can just use standard code snippets. These are fast and cheap and should be preferred when possible.

![Image](https://miro.medium.com/v2/resize:fit:700/1*kksGZ1HlaPmRw4t4Nh_XqQ.png)

Sometimes we’re checking for more nuanced things like “Is this response factually consistent with the sources?” or “Is the tone positive and professional?”

![Image](https://miro.medium.com/v2/resize:fit:700/1*2QYV5kEbCNbhWYn2GLJ0BQ.png)

In this case, we can use another LLM to judge the output. If the LLM judge says “no, this fails,” it explains why. That feedback gets sent back to your agent, and the agent revises and tries again.

Finally, sometimes you just need a human to check the work.

Instead of the agent finishing and shipping the result automatically, you can make it stop and ask for approval first. You can give feedback and ask the agent to try again.

### Design Patterns

Alright, so we’ve covered a lot about how to make the system function. Now let’s talk about how to make the system better quality.

There are four core patterns that reliably boost quality and capability: reflection, tool use, planning, and multi-agent collaboration.

Let’s start with the easiest and most effective one: Reflection.

**Reflection**

In a nutshell, reflection basically just means we don’t stop at the first draft.

When you use reflection, the model produces something, critiques it, then rewrites it if needed. That second pass — guided by a prompt that asks it to find and fix problems — almost always makes things better.

Let me show you a quick example with an email.

_Version 1 (first draft): “Hey, let’s meet next month to discuss the project. Thanks”_

What’s wrong with this? The date is vague (“next month”), there’s no signature, and “Thanks” feels abrupt.

_Reflection step: The model reads v1 and spots these issues — unclear timeline, missing sign-off, tone feels rushed._

_Version 2 (revised): “Hi Alex, let’s meet between January 5–7 to discuss the project timeline. Let me know what works for you. Best, Marina”_

This has the same content but is cleaner, more specific, more professional.

Reflection gets really powerful with code because you can add external feedback. You can write the code, have a critic agent review it, and then actually run it. This allows you to capture errors, test results, and outputs, and feed that back to the model. The model can use that concrete information to produce a much better v2.

![Image](https://miro.medium.com/v2/resize:fit:700/1*3JvW624QePu0y4Pa_fDg6w.png)

Reflection is particularly useful when you have structured outputs like JSON, procedural instructions like the steps to brew tea where the reflection can catch missing steps, creative work, and long-form writing.

In particular, reflection works well when you can incorporate external feedback. Like running a schema validator on JSON or checking for missing citations in a research task.

The drawback is that it adds latency and cost because you’re doing multiple passes. So, make sure to test with and without reflection to ensure it is actually helping.

**Tool Use**

Alright, let’s talk about the second design pattern: tool use.

Here’s the core idea: you give the LLM a menu of functions it can call. This can be things like web search, database queries, code execution, calendar access, or whatever your application needs. And then the model decides when and which tools to use.

This is important because an LLM by itself is just a text generator. It doesn’t know what time it is right now or anything about your company’s sales data. It can’t execute code to compute exact answers.

But if you give it tools it can do things like search the web, query a database, write to a CRM, or run code.

So if I were to ask the agent “What time is it?” the LLM calls getCurrentTime() function, gets back “3:20 PM,” and responds with that.

![Image](https://miro.medium.com/v2/resize:fit:700/1*zjBo41GmCEN4CaoYIrA0-Q.png)

Or we might ask it to search for local restaurants, query the database, or do a math calculation. In each case, the model recognizes it needs external information or computation, picks the right tool, and uses the result to answer.

When you give the model multiple tools, it can chain them together. For example, let’s say you’re building a calendar assistant. You’ve exposed three tools: checkCalendar, makeAppointment, and deleteAppointment.

The user asks: “Schedule a meeting with Alice for this week.”

The model thinks through the steps:

1.  Check my calendar for availability
2.  Find an open slot — looks like 3 PM on Thursday works
3.  Call makeAppointment with Alice and that time
4.  Confirm back to the user

![Image](https://miro.medium.com/v2/resize:fit:700/1*RGfHAl2tcRG_zzrm4Sl1QQ.png)

The key thing here is the LLM is choosing which tool to invoke next based on what it learned from the previous tool’s output. It’s not a fixed pipeline — it’s dynamic.

Okay, but here’s the thing: LLMs only generate text. They don’t execute code. So how do they “call” a function?

They actually don’t. They _request_ a function call.

Here’s the loop under the hood:

1.  The user sends a prompt
2.  LLM looks at its available tools and decides if it needs one
3.  If it does, it outputs a special request like “I want to call getCurrentTime with timezone Pacific/Auckland”
4.  Your code sees that request, actually runs the function, and gets the result
5.  You feed that result back to the LLM as new context
6.  The LLM uses it to finish its answer — or to request another tool if needed

It’s as simple as that. The LLM requests but doesn’t actually execute code.

**Designing Good Tools**

In order for the LLM to be able to find and request tools, we need a consistent way to define them. Every tool has two parts:

1.  The interface for the agent. This includes a tool name, a plain-English description of when to use it, and a typed input schema.

_For example: “ReadWebsiteContent” with description “Fetch and return the text of a webpage” and one input: url (string)._

2\. And the implementation code. Whatever you need like SQL queries, auth, retries, throttling, and parsing.

The agent only sees the interface. All the messy implementation details are hidden.

Good tools also consider things like error-handling, self-recovery, and rate limiting. They may use caching to memoize results for identical inputs to reduce latency, cost, and external API load. And they should have async support so the agent (or other agents) can keep working while a long tool request completes.

Tools should be built like products with versioning, proper documentation, and sufficient tests. It’s useful to maintain an internal registry of vetted tools with docs, versions, and ownership.

Put all that together, and you have now given your agent a way to interact with the world. Which is rad! But we need to make sure that the agent knows what it needs to do in the real world, which leads us to the third design pattern: planning.

**Planning**

Here’s the idea with planning: instead of hard-coding a fixed sequence of steps, you let the LLM decide what to do and in what order.

![Image](https://miro.medium.com/v2/resize:fit:700/1*9ATAePuyFUE4dzTOyQDj_Q.png)

Let’s say you’re building a customer service agent for a retail store. You could hard-code flows for every scenario: “If it’s a pricing question, do X. If it’s a return, do Y. If it’s inventory, do Z.”

But what happens when someone asks something you didn’t anticipate? Or when the same question needs different steps depending on context?

With planning, you give the agent a toolkit of functions like get\_item\_descriptions, check\_inventory, get\_item\_price, process\_return and let it figure out which tools to use and when.

The basic loop looks like this:

1.  You give the agent access to tools
2.  You prompt it to create a plan: “List the step-by-step actions to answer this question”
3.  You execute the plan step by step — the LLM picks the right tool, you run it, feed the result back
4.  Repeat until you’re done

It’s basically “plan → act → observe → continue,” but with your tools.

**A Concrete Example: Retail Sunglasses**

The user asks: “Any round sunglasses in stock under $100?”

The agent might plan:

**Step 1**: Use get\_item\_descriptions to find round frames  
**Step 2**: Run check\_inventory on that list  
**Step 3**: Call get\_item\_price on the in-stock items and filter to under $100  
**Step 4**: Compose the answer

You didn’t predefine this exact recipe. The LLM chose it from the available tools.

Now a different question comes in: “I want to return the gold-frame sunglasses I bought, not the metal ones.”

The plan changes completely in this case:

**Step 1**: Identify the user’s prior purchases  
**Step 2**: Match the gold-frame product  
**Step 3**: Call process\_item\_return  
**Step 4**: Confirm the outcome

It can be helpful to ask the model to output a structured plan in JSON.

![Image](https://miro.medium.com/v2/resize:fit:700/1*UhAmS5U7a8puqu9d9-1VQw.png)

Or, you can let it write actual code, usually Python that encodes the entire plan.

![Image](https://miro.medium.com/v2/resize:fit:700/1*Z8-YvsAyvPhwUfWDZX0hdQ.png)

_What to Watch For with Planning_

Planning increases autonomy, which means it also increases unpredictability. You need guardrails on things like permissions, validation on tool calls, and managing passing the outputs of one step to the next.

Today, the strongest use case for planning is highly agentic coding systems. The model breaks down a programming task into steps and works through it.

For other domains, planning absolutely works, but it’s harder to control because you don’t know in advance what plan the model will create. The tooling and guardrails are improving fast, though, and adoption is growing.

But what if you have a system where you need to do lots of different things, possibly simultaneously? That’s where multi-agent collaboration comes in.

**Multi-Agent**

Think about how you’d tackle a complex project in real life. You don’t hire one super-generalist to do everything. You build a team. You have specialists who are really good at their specific thing, and they hand work off to each other.

Multi-agent systems borrow that same mindset.

Each agent has a clear role. Each one focuses on what it’s good at. The output is better because you’ve got specialization at each step.

Besides specialization, there are some other advantages to multi-agent systems:

*   It avoids any one agent having a huge context window.
*   You can use multiple LLMs. You can mix faster, cheaper models for high-volume simple and reserve larger, more capable models for precision tasks like strategy, delicate customer replies, or long-form writing. This gives you flexibility on both cost and performance.
*   You can parallelize work.
*   And if you have really long-running operations you can split up the work and see which agents are working on what to help users understand what is happening.

If you have a simple task, skip multi-agent systems. They can slow things down and make debugging more difficult.

This is because multi-agent systems introduce a whole new layer of complexity. You can have resource conflicts if two agents try to modify the same file, there’s communication overhead between agents, and complex task dependencies. There are also issues like API rate limits, and what to do if one agent fails — do the others keep going or do you roll back? And how do you combine what multiple agents produced into one coherent output?

This isn’t impossible to manage, but you need to design for it. You need robust orchestration, good error handling, and clear protocols for how agents communicate.

### Multi-agent System Design

So let’s talk more about how to design these multi-agent systems. Let’s use the example of creating a marketing brochure to illustrate our options.

**The Roles Model**

The first step is defining your agents by role. Each agent gets a clear job description and only the tools it needs to do that job.

For our marketing brochure, you might have:

**A researcher agent** who finds market trends and competitor moves. This agent might have tools for web search, retrieval, and maybe note-taking.

**A graphic Designer agent** who creates charts and visual assets with tools for image generation, image manipulation, or code execution to plot charts.

**And a writer agent** who turns findings and assets into final copy. This agent could just be the LLM itself with no external tools needed.

![Image](https://miro.medium.com/v2/resize:fit:700/1*ntydH6u3-VkPZ1GpvfRySA.png)

You implement each agent by prompting it with a role, like “you are a research agent specialized in market analysis” and giving it only the tools that role should have.

Once you’ve defined your agents, you need to decide how they communicate. There are four main patterns which we’ll discuss, from simplest to most complex.

**Pattern 1: Sequential**

This is the simplest and most predictable. Each agent finishes its work, then passes the output to the next agent in line.

![Image](https://miro.medium.com/v2/resize:fit:700/1*h4HqmQtYXe60bltaX0v7tA.png)

For our brochure it could look like this: The researcher finishes → hands off to Designer → Designer finishes → hands off to Writer → done.

It’s like an assembly line. It’s easy to debug and has predictable timing and cost.

This is where you should start. Depending on your use case this may be sufficient.

**Pattern 2: Parallel**

But sequential isn’t the only option. You can also run agents in parallel when steps don’t depend on each other which is great for reducing latency.

![Image](https://miro.medium.com/v2/resize:fit:700/1*8Ptqj-upab5tGf1s1_jfWw.png)

For example, your Researcher and Designer could work simultaneously on independent parts of the brochure, then the Writer combines their outputs.

This speeds things up but adds coordination complexity.

**Pattern 3: Single Manager Hierarchy**

If you start getting into more complex workflows, it can be helpful to add a manager agent that plans and coordinates. The specialist agents do their work and report back to the manager, not to each other.

![Image](https://miro.medium.com/v2/resize:fit:700/1*Qhll5r0-71eScrt5JFA5Ig.png)

This keeps control tight while giving you flexibility. The manager can reorder steps, skip things that aren’t needed, or ask agents to redo work. It’s more adaptable than a linear flow without being chaotic.

This is probably the most common pattern in production multi-agent systems today.

For even more complex workflows, you could have deeper hierarchies where some of the agents manage their own sub-agents.

![Image](https://miro.medium.com/v2/resize:fit:700/1*11BZbp6kEM1e0DPiCEGSLg.png)

For example, your Researcher agent might orchestrate a Web-Researcher sub-agent and a Fact-Checker sub-agent. Your Writer agent might have a Style-Writer and a Citation-Checker working under it. This is helpful for very complex tasks but of course adds a bit more chaos.

**Pattern 4: All-to-All (Free-for-All Chat)**

Finally, we have the all-to-all model, which can be SUPER chaotic. In this model, any agent can message any other agent at any time. This is rare in production because it’s hard to predict and control. Outputs can vary wildly run-to-run.

![Image](https://miro.medium.com/v2/resize:fit:700/1*EV6Y3LKSwHUeWp17R5BFNg.png)

But it can work for more brainstormy, creative, or low-stakes tasks. Like generating multiple variations of ad copy where if one run produces garbage, you can just try again.

**Coordination Pitfalls**

We’ve talked about challenges with coordination a couple of times. Here are two of the most common pitfalls.

First, redundant work. Multiple agents may redo the same searches or call the same tools. This can be addressed by tightening task scopes and having a clear division of labor between the agents.

Second, unnecessary serialization. Chaining steps that could run concurrently slows everything down. To address this, identify truly independent tasks and run them asynchronously, then route just the pieces of context the next step needs.

In general, you’ll want to start with the simplest coordination method you can, and only add complexity as needed.

**Best Practices**

Regardless of which pattern you choose, here are four key best practices to keep in mind when designing your system:

_1\. Define interfaces, not vibes._

Each agent needs a clear schema for inputs and outputs. It needs to know things like: What fields? What types? What IDs or references get passed along?

Handoffs break more often than the models do. If your Researcher returns an unstructured blob and your Designer doesn’t know how to parse it, the whole system fails.

_2\. Scope tools per agent._

Give each agent only the tools it actually needs. Least-privilege access.

This helps with security and makes the system easier to reason about, easier to audit, and easier to debug.

_3\. Log the trace._

Keep per-step artifacts. What did each agent plan? What prompts did it use? What tool calls did it make? What results came back?

When something breaks this trace makes error analysis fast. You can see exactly where things went wrong.

_4\. Evaluate components AND end-to-end_

You need two types of evals:

Component-level: Is the research relevant? Are the images high quality? Is the copy tone appropriate?

And end-to-end: Is the final brochure good? Does it meet the requirements?

If your end-to-end eval shows problems but your component evals all look fine, you know it’s a handoff or integration issue. If a specific component eval fails, you know which agent to improve.

## ADVANCED

Alright, welcome to the advanced section. If you’ve made it this far, you’re serious about building real agent systems that could work in the real world.

The techniques that got you from zero to prototype won’t get you from prototype to production. You need different tools, different mindsets, and more discipline.

Let’s get into those now.

### Advanced Task Decomposition for Multi-Agent Systems

We’ve already talked about task decomposition. But this gets increasingly complex when you’re working with multi-agent systems.

There are four main patterns you can use to guide you to do this well. BTW, I adapted this from [this awesome blog](https://gerred.github.io/building-an-agentic-system/core-architecture.html) — check it out for more detail!)

**Pattern 1: Functional Decomposition**

In this pattern, we split the tasks by technical domain or expertise. This is what we’ve been using in our examples so far — breaking tasks by what kind of work needs to be done.

![Image](https://miro.medium.com/v2/resize:fit:700/1*7vElcVMqAp2P0JW5nlxtyA.png)

For example, you could think about full-stack feature development. You’ve got frontend work, backend logic, database changes, and maybe API updates. Each of these requires different knowledge and different tools. So you create agents specialized in each domain.

**Pattern 2: Spatial Decomposition**

You can also split by file or directory structure. This is especially powerful when you’re working with large codebases with many files that could be processed independently.

Let’s say you’re doing a large-scale refactoring — maybe updating all your API endpoints to a new authentication system, and you’ve got dozens of files across different services.

You decompose spatially:

*   Agent 1 handles /services/users/\*
*   Agent 2 handles /services/orders/\*
*   Agent 3 handles /services/payments/\*
*   Agent 4 handles /services/notifications/\*

In this case, you minimize conflicts by ensuring agents work on separate parts of the codebase. They can work in parallel. But if your files have complex dependencies on each other, spatial decomposition breaks down.

**Pattern 3: Temporal Decomposition**

Pattern 3 is about breaking tasks into sequential stages where later stages depend on earlier ones being complete.

Let’s use a product launch as an example. You can’t just wake up one day and start sending promotional emails. There’s a logical sequence:

**Phase 1: Market Research** — Analyze competitors, survey target customers, identify positioning opportunities  
**Phase 2: Launch Planning** — Define messaging, set pricing, create timeline, identify channels  
**Phase 3: Asset Creation** — Write copy, design graphics, build landing pages, prepare email sequences  
**Phase 4: Launch & Monitor** — Execute campaign, track metrics, respond to feedback, adjust in real-time

Each phase gets its own agent or team of agents. Phase 2 doesn’t start until Phase 1 is done and reviewed.

**Pattern 4: Data-Driven Decomposition**

And finally, we can split by data partitions. This one’s less common but really powerful for certain use cases, especially tasks involving large datasets where you can partition the data and process chunks independently.

Let’s say you’re analyzing application logs to identify performance issues. You’ve got gigabytes of logs from the last month.

You partition by time or by service:

*   Agent 1 processes Week 1 logs
*   Agent 2 processes Week 2 logs
*   Agent 3 processes Week 3 logs
*   Agent 4 processes Week 4 logs

Each agent runs analysis independently, then you aggregate results at the end.

You could also mix these patterns. For example, a full-stack feature might use functional decomposition for the main structure (frontend, backend, database), but the backend agent uses temporal decomposition internally (design API → implement logic → add tests).

### Improving Quality

Alright so at this point let’s say we have a working system, we’ve done a comprehensive evaluation to find errors, and we’re still just not happy with the performance. Here’s what to do.

The first thing to understand is that you’re working with two fundamentally different types of components, and they need different improvement strategies.

First we have non-LLM components. These are things like web search, RAG retrieval, code execution, speech recognition, vision models, PDF parsers.

These can be improved in two main ways:

*   **Tune the knobs.** Fiddle with things like web search date ranges, top-k results, RAG chunk size, similarity thresholds, and so on.
*   **Or, swap providers.** Try alternative web search APIs. Different OCR or vision models, and so on.

Then we have LLM components. These are used for generation, extraction, reasoning — anywhere you’re using the language model itself.

There’s a lot we can do to improve this part:

*   **Prompt better.** Add explicit instructions, constraints, schemas. Use few-shot input-output pairs to show the model what you want.
*   **Try another model.** Some models are better at following instructions, others excel at code or factual recall. Don’t assume one model is best for everything.
*   **Decompose hard tasks into smaller pieces.**
*   **And fine-tune as a last resort.** Fine-tuning is powerful but costly. Save it for mature systems where you need those last few percentage points of quality and you’ve exhausted everything else.

### Reducing Latency

Nailing the output quality should be your first step. After that, let’s talk about reducing latency.

1.  Get a baseline

The first step is to time each step in your workflow. You might find something like, it takes 7 seconds for the LLM to generate search terms. Web search takes 5 seconds. Drafting the essay takes 11 seconds, and so on.

This gives you a baseline so you know what you should be optimizing.

2\. Parallelize

Next, run anything in parallel that you can. Examples might be web fetches, multiple searches, or parsing multiple documents. This is often the easiest win.

3\. Right-size the model

Use a smaller, faster LLM where tasks are simple like keyword generation, and reserve the heavyweight model for synthesis and reasoning.

4\. Try faster providers.

Throughput and token streaming speeds vary a lot. A provider with optimized serving can cut seconds without any prompt changes.

5\. Finally, trim context.

Shorter prompts and contexts mean faster decoding, so try to keep only what the step truly needs.

### Reducing Cost

With quality high and latency under control, you’re ready to look at costs. To kick off, you’ll want to measure the cost of each step just like with latency.

Agent systems have several cost sources:

**LLM calls:** This is determined by input tokens and output tokens. These are usually priced separately (input tokens are cheaper and output tokens cost more).

**API calls:** Things like web search, PDF conversion, image generation, speech-to-text. These often have per-call or per-unit pricing.

**Infrastructure:** If you’re running your own retrieval systems, vector databases, or compute for code execution.

Say you’re building a research agent that writes essays. Here’s what one run might cost:

![Image](https://miro.medium.com/v2/resize:fit:700/1*YQTTxukdutJ9H4sQRt7Heg.png)

If you’re running this 1,000 times a day, that’s $80/day or $2,400/month.

![Image](https://miro.medium.com/v2/resize:fit:700/1*QC18ssJMEVp2GVv0nfz8GA.png)

Once you know how much each step costs, here’s what you can do to optimize:

*   **Attack the big buckets first.** If web search costs 2 cents per call and you’re calling it 10 times per run, that’s 20 cents right there. Do your best to reduce calls, cache results, or batch queries.
*   **Tier your models.** Use cheap models for easy tasks and frontier models only where it really matters.
*   **Cache aggressively.** Deterministic results like search responses, embeddings, chunk retrievals, or intermediate summaries shouldn’t be recomputed every time.
*   **Constrain outputs.** Ask for structured, concise results with instructions like “Return JSON with these required fields.” “Give me 5 bullets max.” Fewer tokens, lower bill.
*   **And batch.** If you’re processing many similar items, bundle operations when possible. On AWS batch processing is 50% the cost of on-demand, for example.

### Observability and Monitoring

So you have a system with quality, latency, and cost that you’re happy with. Now we need to make sure it continues to behave as expected once it scales.

This is where monitoring and observability come in. Observability covers debuggability, quality monitoring, and hallucination tracking. Basically, anything that helps you watch the agent’s behavior and performance.

The tricky bit is that observability for AI systems is fundamentally different from traditional software.

With traditional software, you can trace a clear execution path. Function A calls Function B, which queries the database, returns data, renders a page. That kind of thing.

AI systems don’t work that way, for many different reasons:

*   They’re non-deterministic. The same input can produce different outputs based on model responses. You can’t just replay a request and expect the same result.
*   They have distributed execution with tools running in parallel, agents spawning sub-agents, and so on.
*   Lots of external dependencies with potential failure points that are outside of your control.
*   And more!

To manage all this, we need two kinds of visibility:

*   **“Zoom-in” metrics** help you debug single runs. This is your full trace: prompts, tool calls, token usage, retry attempts, and every decision point. Basically everything required to reproduce an error and see exactly where it went wrong.
*   **“Zoom-out” metrics** tell you how the whole system is doing over many runs. This includes automated quality checks (often with an LLM-as-judge), hallucination rates, success/ROI measures, and trend lines that show whether changes are helping or hurting.

You’ll want to log not only what an agent did, but why it did it. For example, you might log things like: “Agent chose to use web search instead of RAG because query contained ‘recent’” or “Reflection pass identified 3 issues: missing citation, vague date, wrong tone”

When you’re running thousands of agents at once, you can’t manually watch each trace. This is where **quality sampling** comes in. Instead of deeply inspecting every single execution, you define a sampling rate — say, a certain percentage of total runs — to be evaluated for quality and hallucination. The system then uses that subset of executions to compute an overall quality score and a hallucination score for your agents.

This lets you prioritize fixes and areas for improvement.

Beyond technical metrics, you need to understand user behavior.

*   **What are people actually asking for?** Are they using your agent as intended, or have they found creative workarounds?
*   **Where do they get stuck?** Do they rephrase and retry? That’s a signal that the first attempt didn’t work.
*   **What do they do with the output?** If they immediately ask for revisions, the initial quality wasn’t good enough.
*   **How long are sessions?** Very short sessions might mean quick success or immediate failure. Very long sessions might mean the agent is capable but inefficient.

This qualitative data guides your product roadmap as much as your technical metrics do.

### Security

Finally, we need to talk about one of the least exciting and most important pieces of building a robust system: Security.

Just like observability, security for AI agents isn’t like traditional application security. You’re not just protecting against external attackers — you actually have to protect against your OWN system making dangerous decisions or being manipulated into harmful actions.

These are the kinds of things to watch out for:

*   **Prompt injection:** Malicious content in user input or external data that hijacks your agent’s instructions
*   **Unsafe code generation:** Agents writing code that accesses sensitive data or executes dangerous operations
*   **Data leakage:** PII or proprietary information exposed through agent outputs or tool calls
*   **Resource exhaustion:** Agents spinning up expensive operations or infinite loops

Let’s dive into code execution in particular. Code execution is the ultimate tool for agents. It’s incredibly powerful because agents can write code to generate charts, create markdown files, process data, and generally do “anything they want” within the boundaries you give them.

This is a double-edged sword.

Many tasks can be covered by well-defined custom tools, so your system doesn’t always need to fall back to free-form coding. But when you do enable it, you need guardrails.

Here’s how to do code execution safely:

*   **Sandbox execution.** Use Docker or a restricted runner environment. Isolate code execution completely from your main application. The code should run in a container that gets destroyed after each execution.
*   **Resource limits.** Set timeouts, memory caps, CPU limits. Block dangerous imports, network access unless explicitly needed, and file system writes outside a designated temp directory.
*   **Whitelist libraries only.** Allow specific, safe libraries like pandas, numpy, or datetime. Don’t allow arbitrary installs. If an agent needs a library, you add it to the whitelist explicitly.
*   **Validation plus reflection loop.** If code execution errors, capture the traceback and let the model fix the code. Give it one or two attempts and make sure you have a circuit breaker in place.
*   **Deterministic I/O.** Have the code return a small, structured result — a number, a list, a JSON object. Then you format that for the user. Don’t let the code directly output to the user or write to files they can access.
*   And **input and output sanitation** so all inputs are validated before they reach the agent, and all outputs are scanned for sensitive data like API keys or PII.

That wraps up the advanced section! With all of this, you’re ready to build real systems that scale and serve users in production.

## BONUS

But as promised, we have one more bonus for the super advanced folks.

Most of what we talked about today assumes you’re using a framework like LangGraph or CrewAI. But if you’re a developer interested in understanding the internal workings of agentic tools like Claude Code, I highly recommend this blog on agentic system design: [https://gerred.github.io/building-an-agentic-system/core-architecture.html](https://gerred.github.io/building-an-agentic-system/core-architecture.html)

It walks through things like the three core layers (terminal UI, LLM “intelligence” layer, and tool layer), how to structure a reactive command loop with async generators, patterns for streaming + tool calling, and even a parallel execution engine and smart tool scheduling (read vs. write) that looks a lot like what powers Claude Code and Cursor under the hood.

— — —

If you’re feeling like you need some support with your AI/ML career, here are some ways I can help:

*   Subscribe to [my YouTube channel](https://www.youtube.com/@MarinaWyssAI) for weekly videos on technical topics, interviewing strategies, and more.
*   Sign up for [my newsletter](https://www.gratitudedriven.com/subscribe) for a weekly post on a mix of technical topics and mindset/motivation for challenging fields.
*   Want to level up your AI/ML career? Join the [AI/ML Career Launchpad](https://aiml-career-launchpad.circle.so/aiml-launchpad) community
*   Interested in working with me 1:1? Learn more about my [strategic advisory sessions](https://www.marinawyss.com/coaching)

Many of the slides and examples were adapted from the [Agentic AI](https://learn.deeplearning.ai/courses/agentic-ai/information) and [Multi-Agent Systems](https://www.deeplearning.ai/courses/design-develop-and-deploy-multi-agent-systems-with-crewai/) courses from Deeplearning.AI. Check them out for more detail!