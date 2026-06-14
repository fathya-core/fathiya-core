# The Rules NASA Uses to Write Code That Can’t Fail. Your AI Tools Break All of Them.

**Published:** 2026-03-18


![Image](https://miro.medium.com/v2/resize:fit:700/1*wwiktzUTgtVuGPMNT5aqaw.jpeg)

*Computer scientist Margaret Hamilton poses with the Apollo guidance software she and her team developed at MIT. Photos: MIT Museum*

_In 2006, a NASA engineer wrote ten rules for writing code where lives depended on correctness. They still apply. And they’re more urgent now than ever._

Gerard Holzmann had a problem. He was writing flight software at NASA’s Jet Propulsion Laboratory, and the existing coding guidelines — hundreds of rules, assembled over years — weren’t working. Developers ignored them. Tools couldn’t check them. Bugs still shipped.

His solution was radical in its simplicity: throw almost everything out and keep only ten rules. Not a hundred. Ten. Small enough to memorize. Strict enough to enforce mechanically. Targeted at C, the language JPL used for mission-critical systems — but grounded in principles that hold for any language, any stack, any era.

That era is now. The difference is that today, a significant portion of production code is being written by AI — quickly, fluently, and with a striking blindness to the things that make software actually reliable. Holzmann’s rules were designed for engineers who might cut corners under deadline pressure. They apply equally well to language models that have no concept of corners at all.

> _“When it really counts, it may be worth going the extra mile and living within stricter limits than may be desirable.” — Gerard Holzmann, NASA/JPL_

![Image](https://miro.medium.com/v2/resize:fit:700/1*jXOu6HArf0jQNUwU9zMwmg.png)

*https://www.youtube.com/watch?v=wZpDV-1P9uM*

What follows are twelve rules distilled from his original ten, generalized beyond C, extended for AI-assisted development, and written for engineers who want their software to actually work.

> If you want the unabridged version — rabbit holes, edge cases, and all — I went deeper on my personal blog:

[

## NASA's Rules for Code That Can't Fail: Revisited for AI-Generated Systems

### Applying NASA's legendary JPL flight software discipline to modern backend infrastructure and the era of AI-generated…

leestack.dev


](https://leestack.dev/writing/nasa-rules-for-code-that-cant-fail/?source=post_page-----8d0377998efb---------------------------------------)

## **CONTROL & STRUCTURE**

### **01\. Keep it linear.**

No deep nesting. No hidden jumps. No control flow that requires a diagram to understand. Code should read top to bottom like a well-constructed argument — premise, reasoning, conclusion. The moment you need to hold five conditions in your head simultaneously to understand one function, it has failed the test.

Holzmann banned recursion entirely. That’s probably too strict for most modern codebases. But the instinct is right: the more paths execution can take, the harder it is to prove that the one path that matters actually works.

_AI guardrail: AI loves deeply nested conditionals and early-exit chains. Ask it explicitly to flatten the logic — one level deep where possible. If the generated function has more than two levels of nesting, push back._

### **02\. Bound every loop.**

Every iteration needs a ceiling. Not an implied one, not a “this will practically never exceed N” one — a real, explicit, enforced maximum. Unbounded loops are the software equivalent of a structural calculation that assumes ideal conditions. They work beautifully until they don’t, and when they don’t, they take everything with them.

_AI guardrail: AI-generated polling loops, retry logic, and recursive crawlers routinely lack caps. Always ask: what is the maximum number of times this runs, and what happens when we hit it?_

## **MEMORY & RESOURCES**

### **03\. Know what you own.**

Every resource you open, you close. Every connection you borrow, you return. Resource lifetime must be declared, not assumed — and it must be correct on the error path too, not just the happy one. The original rule prohibited dynamic memory allocation after initialization. The spirit applies broadly: don’t acquire what you can’t account for.

_AI guardrail: AI-generated code opens database connections and file handles without cleanup, especially in error branches. Follow the code through every exit path and confirm it closes what it opened._

### **04\.** **One function, one job.**

Each function should do exactly one thing — small enough to hold in your head, describable in a sentence without the word “and.” Holzmann’s rule was blunt: nothing longer than what fits on a single printed page, roughly 60 lines. The rationale isn’t aesthetic. It’s epistemic. You cannot reason about what you cannot comprehend at once.

Long functions are almost always a sign that the decomposition hasn’t happened yet — that the thinking is still in progress, just wearing the costume of implementation.

_AI guardrail: AI generates monolithic functions that do many things at once because it’s optimizing for task completion, not maintainability. Set a hard line before you prompt: no function longer than 40–60 lines. Ask for decomposition upfront, not as a refactoring afterthought._

## **CORRECTNESS & OBSERVABILITY**

### **05\. State your assumptions.**

Every function has preconditions. Every data structure has invariants. Every API has a contract. These don’t belong in a README — they belong in the code, as assertions that execute at runtime and fail loudly when violated. Holzmann required a minimum of two assertions per function. The point isn’t the number; it’s the discipline of making implicit assumptions explicit and checkable.

_AI guardrail:_ _AI-generated code skips validation almost universally__. Prompt explicitly: add assertions for expected preconditions before this runs, and postconditions after. Make the assumptions visible and loud._

### **06\. Never swallow errors.**

This is possibly the most violated rule in existence, and Holzmann said so explicitly. Every failure path must be handled, logged, or propagated. A bare `except: pass` is not error handling — it is active suppression of information you will desperately want later. Silent failures corrupt state silently. They surface months later, in production, in ways that are nearly impossible to trace.

_AI guardrail: AI routinely generates empty catch blocks and unchecked return values._ _Enforce one rule with no exceptions: every error must be logged, raised, or explicitly returned. Nothing gets swallowed. Ever._

### **07\. Narrow your state.**

Data should live as close to its use as possible. The wider the scope, the more code can touch a variable — and the more code that can touch it, the harder it is to find the one line that broke it. This is the principle of least privilege applied to data. Global state is the fastest path to a debugging session that feels like archaeology.

_AI guardrail: AI leans on class-level state and module-level globals because they’re easier to generate. Ask it to scope state locally and pass dependencies explicitly — make the data flow visible at every call site._

### **08\. Surface your side effects.**

I/O, mutations, and network calls should be obvious at the call site. Not hidden inside helpers, not wrapped in abstractions with innocent-looking names, not four layers deep in a chain of decorators. If a function writes to a database, its name and call site should make that clear. A function that looks pure but has side effects is the most dangerous kind of technical debt.

_AI guardrail: AI buries writes and API calls inside what appear to be utility functions. Ask for a clear structural separation between pure computation and side-effectful operations. The dangerous stuff should be visible, named, and obvious._

## **ABSTRACTION & INDIRECTION**

### **09\. One layer of magic.**

Abstraction is one of programming’s most powerful tools and one of its most common weapons of self-destruction. Every layer of indirection — every middleware, every dynamic dispatch, every callback chain — makes it harder to answer the question: _what actually runs when I call this?_ Holzmann restricted pointer indirection to a single level for exactly this reason. The deeper the chain, the harder the trace.

_AI guardrail: AI stacks abstractions eagerly. After every generation, ask: can this be written more directly? Favour composition you can read linearly over elegance you have to decode. When something breaks at 2am, you want to be able to read the code._

### **10\. Warnings are errors.**

Holzmann required zero compiler warnings from day one — not zero errors, zero _warnings_. The distinction matters. A warning is a future bug that the tools have already found. Treating it as advisory is choosing to leave a known problem unresolved. Type checkers, linters, and static analyzers should run on every change, and their output should be a hard gate, not a soft suggestion.

_AI guardrail: AI-generated code almost never sets up linting or static analysis. These must be part of your project scaffold — wired into CI, configured to fail the build on violations. Set them up before the AI starts writing code, not after._

## **WORKING WITH AI**

### **11\. Read every line.**

This is the rule that most people working with AI tools are currently violating. AI-generated code is not peer-reviewed code. It has not been tested by someone who cares about whether it works. It has been generated by a system that is very good at producing code that looks correct — and that is precisely the problem. The gap between _looks correct_ and _is correct_ is where bugs live.

Treat every AI output like a PR from a brilliant but reckless contractor who will not be around when it breaks. Read it. All of it. Especially the error paths and the edge cases. Especially anything touching authentication, money, or user data.

_AI guardrail: Never commit code you haven’t read in full. You are still the engineer of record. The AI has no skin in the game._

### **12\. Tests first.**

Ask the AI to write the tests before — or alongside — the implementation. If the AI cannot articulate what correct behaviour looks like in the form of a test, the requirements aren’t clear enough to build from. Tests make the specification explicit. They make correctness checkable. They make future changes safe.

“Write failing tests for this feature, then make them pass” is a fundamentally different — and safer — prompt than “implement this feature.” The first forces reasoning about correctness before writing production code. The second does not.

_AI guardrail: AI optimizes for the happy path._ _Tests force it to reason about edge cases and failure modes_ _— which is exactly where AI-generated code tends to be weakest._

Holzmann’s original paper ends with an image: these rules are like a seat belt. Initially uncomfortable. Quickly second-nature. And eventually, you can’t imagine not using them.

The parallel for AI-assisted engineering is this: the tools are genuinely powerful, and the productivity gains are real. But power without discipline is just a faster way to make the same mistakes. The rules above are not obstacles to moving quickly. They are what make it safe to move quickly — because the code you ship with them is code you can reason about, debug, and trust.

Pick the twelve. Automate what you can. Enforce the rest in review. The AI will write the code. You are still responsible for whether it works.

> This piece is part of what I’m building at [**leestack.dev**](http://leestack.dev/) — a space where I get obsessive about system design, architecture, and engineering strategy. Interactive labs are in the works. Probably worth a tab you won’t close.

![Image](https://miro.medium.com/v2/resize:fit:700/1*8VYMhNLTKTCUWULDmQaaiA.png)

*https://leestack.dev/*

_Adapted from: Holzmann, G.J. (2006). The Power of Ten — Rules for Developing Safety Critical Code. NASA/JPL Laboratory for Reliable Software._