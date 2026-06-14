# Claude Code is No Longer the King of Coding

**Published:** 2026-02-16

## AI


![Image](https://miro.medium.com/v2/resize:fit:700/1*aBvA1bLv2C5P9CvNjLR0OQ.png)

Claude Code changed everything. It was the first coding agent that enabled you to generate and review code seamlessly in your terminal with abundant token usage. All at a reasonable price.

Nothing else came close.

That shift reshaped how many developers approached coding, and paved the way for every agent that followed.

Today, it is far from alone. There are many third-party providers giving access to multiple models, such as Droid, Cursor, Amp, and others. But also first-party providers, such as OpenAI (Codex), Gemini CLI, and Mistral AI.

The difference is:

*   ​​Third-party providers: “we give you models from multiple providers for a higher price”
*   First-party providers: “we give you a ton of usage, but just for our models”

The winner, though, at the moment, is without a doubt **Codex**.

Codex is incredibly capable with the integrated GPT-5 family of models. It also comes with excellent usage limits, even the $20 / month subscription of ChatGPT gives good limits, and with the Pro subscription you can run it almost all the time.

In addition, with the Pro subscription you get the Pro model in ChatGPT, which is very useful for the hardest of problems. Although you cannot run the Pro model in Codex, you will have to paste your code into the ChatGPT editor, which at times is worth it due to its sheer intelligence.​

## A Brief Note on Gemini 3

When Gemini 3 Pro came out, I tried it immediately, as there was a lot of hype around it. But it instantly started to do weird things. For instance, it immediately pushed changes that it did, without me approving nor asking for it.

Codex, on the other hand, is very good at following instructions and avoiding harmful actions, like unsolicited git operations or database migrations, unless you explicitly ask for them.

At the same time, the performance of Gemini 3 wasn’t very impressive either. For this reason I’ve abandoned it.

## When to Prefer Claude Code

The real competition to Codex is Claude Code. As mentioned earlier, it was the pioneering terminal agent, but has since been surpassed by Codex. That being said, there are a few areas where Claude Code comes out ahead.

For one, Claude’s personality is better. It feels more friendly and less “robotic”. This makes it feel nicer to work with.

The second benefit is speed. Generally, if you use the best model of OpenAI, which is the xhigh version (as I’m typing this GPT-5.3 Codex xhigh), then it is very slow. For this reason, [I run multiple agents in parallel](https://medium.com/itnext/vibe-coding-with-4-computers-07516ebba57b). But Claude Code’s best model (Opus 4.6 at the moment) still remains quite fast.

The third benefit is UI design and creation. It usually provides more versatile and interesting designs. Codex tends to always give the same theme and font for some reason.

Despite all these benefits Codex remains my primary choice. Let me explain why.

## Intelligence

While Claude Code has a few benefits, for real complex tasks, Codex is unmatched. It’s precise, careful, and does not produce “slop” around the codebase. It understands complex instructions and outputs high-quality code consistently, even for huge codebases and while running for hours, handling context compactions with ease.

For the most complex tasks I’ve worked with, which includes custom parsers, it has been very useful. For simpler tasks, it has enabled a more “hands-off” style of coding, in other words, “vibe coding”.

## Slop and more slop

One of the primary reasons not to use Claude Code too much is that it adds “slop”. Slop is essentially code of low quality that is poorly designed, unstructured or bug-prone.

Slop can be difficult to detect and remove, because it may seem like the code works for the moment, but then if you start reviewing the bits and pieces you’ll notice undesirable patterns.

The issue with continuously using Claude Code is that the slop compounds, meaning that over time, the codebase becomes harder to understand and debug. It turns into a maintenance nightmare, even if you continue to use agents.

This “compounding of slop”-problem may ultimately decide the race between OpenAI and Anthropic. If Anthropic relies heavily on Claude Code internally, the slop could seep into their own tooling. Claude Code can already consume gigabytes of RAM with just 2-3 sessions (built in TypeScript). Meanwhile, OpenAI uses Codex internally and it is built in Rust.

## Root Cause Finding vs. Guessing

As I have little knowledge about how Anthropic and OpenAI internally train their model, I have a feeling there is some stark difference in ideas, something fundamental that generates a behavioral difference.

If you task Claude (latest Opus/Sonnet) with solving an issue, it often just keeps adding things.

*   _​Maybe it’s this thing_ … \*adds some code\*,
*   _Hmm, no, maybe it’s this thing_ … \*adds some more code\*

It feels like guesses. And if the guesses don’t solve the problem, it often keeps adding more artifacts over the codebase.

Meanwhile, Codex more carefully analyzes the problem, sometimes not making a change for 10-20 minutes. It acts more like a real engineer would. Trying to understand the root cause of the problem.

What could easily fool you to think Claude Code is better is if it produces a quick solution that works. The fact is that sometimes it does work, and if so, it will naturally have solved the problem more quickly than Codex. But often it doesn’t, and it keeps guessing.

When it comes to programming though, the biggest time sink is usually the hardest problems. Having a model that can actually tackle them is the real differentiator.

If I were to formulate the difference I experience, I’d say it’s like Codex is trying to solve an equation, while Claude is looking at what seems reasonable.

## Conclusion

In the end, the real difference isn’t speed or personality, it’s how well an agent handles complexity over time. For simple tasks, many tools perform well, but when the codebase grows and become more complex, the ability to reason carefully and avoid generating poor code is what ultimately matters most. This is where Codex wins at the moment.

If you enjoyed this, you should definitely check out this technique:

[

## Dead Simple Prompt To Improve Your Code & Software — Works with Agents like Claude Code and Codex…

### I’m hesitant in just calling this “a prompt”. It’s more of a research workflow. It instructs the agent clearly what to…

levelup.gitconnected.com


](/dead-simple-prompt-to-improve-your-code-software-works-with-agents-like-claude-code-and-codex-193903b37239?source=post_page-----75a22f95ddd2---------------------------------------)