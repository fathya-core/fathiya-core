# Gmail   Chain models for complex tasks

Converted from PDF `Gmail - Chain models for complex tasks.pdf` for searchable FATHIYA retrieval.

- Pages: 2

## Page 1
<fathya.core@gmail.com>   Fathya Core
Chain models for complex tasks
رﺳﺎﻟﺔ واﺣدة
<welcome@openrouter.ai>   OpenRouter Team م5:14 ﻓﻲ2026 ﻣﺎﯾو7
fathya.core@gmail.comإﻟﻰ
Hi there,
Use a fast model for classification, a strong model for generation. Same
endpoint, same auth, different model parameter. That is the point of having 300+
models on one API: you mix them per step instead of committing to one for the whole
workload.
Browse models
PATTERN 1: CLASSIFY, THEN GENERATE
# Step 1: classify with a fast, cheap model
classify = client.chat.completions.create(
  model="openai/gpt-4o-mini",
  messages=[{"role": "user", "content": f"Classify: {query}"}],
)
# Step 2: generate with a strong model
result = client.chat.completions.create(
  model="anthropic/claude-sonnet-4.6",
  messages=[{"role": "user", "content": f"{classify.choices[0].
message.content}: {query}"}],
)
GPT-4o-mini runs around $0.15 per million input tokens. Claude Sonnet 4.6 runs
around $3 per million. Using the cheap model for routing and the expensive one only
where it earns its cost can cut total spend 5 to 10x on mixed workloads.

## Page 2
PATTERN 2: EXTRACT, THEN WRITE
# Step 1: structured extraction
extracted = client.chat.completions.create(
  model="openai/gpt-4o-mini",
  response_format={"type": "json_object"},
  messages=[{"role": "user", "content": f"Extract fields as JSON:
{doc}"}],
)
# Step 2: long-form writing from the structured fields
draft = client.chat.completions.create(
  model="anthropic/claude-sonnet-4.6",
  messages=[{"role": "user", "content": f"Write a report from:
{extracted.choices[0].message.content}"}],
)
Structured outputs are cheap and fast on small models. Long-form generation is where
the frontier models actually earn their per-token rate. Splitting the work keeps the
expensive calls short.
Why this works on OpenRouter specifically. One endpoint means no separate
SDK per provider, no second billing account, no new authentication. The model
parameter is the only thing that changes between steps, and the activity dashboard
shows both calls side by side so you can see exactly where the cost went.
openrouter.ai  ·  Discord  ·  X  ·  Docs
Manage preferences   |   Unsubscribe
