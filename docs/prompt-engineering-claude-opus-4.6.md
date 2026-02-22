# Prompt Engineering Guide for Claude Opus 4.6

## Why This Guide Exists

Claude Opus 4.6 is significantly more capable and instruction-sensitive than earlier models. Techniques that worked for GPT-3.5 or even Claude 3 can actively backfire here. The model is better at understanding intent, which means blunt-force prompting creates more problems than it solves.

This guide documents patterns that produce reliable, high-quality outputs with Opus 4.6 specifically.

---

## 1. Drop the Shouting

**The principle:** Opus 4.6 treats emphasis markers as strong behavioral signals. ALL-CAPS urgency markers (CRITICAL, MUST, NEVER, ALWAYS) cause the model to overtrigger on those rules, applying them in situations where they shouldn't apply and distorting the balance of the overall prompt.

**Why it happens:** Earlier models needed emphasis to pay attention to important rules buried in long prompts. Opus 4.6 has much better instruction recall across its full context window. Adding emphasis doesn't help it notice a rule; it tells the model to weight that rule above everything else, often at the cost of nuance.

**The pattern:** State rules plainly. Use natural sentence structure and trust that the model reads the entire prompt.

```markdown
# Good
Confirm with the user before sending emails, tweets, or any public-facing content.

# Good (when priority genuinely matters)
Priority: always confirm before sending external communications.
```

If you find yourself reaching for CAPS, ask whether the rule is actually more important than every other rule in the prompt. Usually it isn't. You just want the model to follow it, which it will do from a plain statement.

---

## 2. Explain Why, Not Just What

**The principle:** Opus 4.6 generalizes from reasoning better than from rigid rules. When you explain the purpose behind an instruction, the model can apply the spirit of the rule to novel situations it hasn't seen before. Without the "why," it follows the letter of the rule and fails on edge cases.

**Why it matters:** A rule like "keep responses under 200 words" gets followed literally, even when a 210-word response would be clearly better. But "keep responses concise because the user reads these on a phone screen and long messages get ignored" lets the model make intelligent length decisions across different situations.

**The pattern:** Pair each significant instruction with its rationale.

```markdown
# Good
Reply in the user's language. Users interact through mobile messaging apps
where language-switching feels jarring and breaks conversational flow.

# Good
Avoid markdown tables in Discord messages. Discord's mobile client doesn't
render tables properly, so they appear as broken ASCII to most users.
Use bullet lists instead.
```

The model doesn't need a rationale for every trivial instruction. Reserve explanations for rules where you want intelligent generalization, or rules that might seem arbitrary without context.

---

## 3. Show the Target, Not the Trap

**The principle:** Only include examples of desired behavior. When you show anti-patterns (even labeled "bad" or "don't do this"), the model sometimes latches onto them and reproduces the exact behavior you're trying to prevent.

**Why it happens:** The model processes examples as behavioral demonstrations. Labels like "bad" or "wrong" are weaker signals than the structural pattern of the example itself. The model sees "here is a pattern in this prompt" and may reproduce it, especially under ambiguity.

**The pattern:** Demonstrate what you want. If a behavior needs to be discouraged, describe it abstractly without providing a concrete template.

```markdown
# Good
When summarizing articles, lead with the key finding in one sentence,
then provide 3-5 supporting points:

"Inflation fell to 2.1% in Q3, driven primarily by energy price
corrections. Key factors:
- Energy prices dropped 12% following OPEC production increases
- Housing costs stabilized after 18 months of growth
- Core goods inflation remained flat at 0.3%"

# Good (discouraging a behavior without demonstrating it)
Avoid opening summaries with generic throat-clearing phrases.
Start with the specific finding or conclusion.
```

This principle extends to error handling examples, conversation templates, and any structured output format. If you show it, assume the model will do it.

---

## 4. Don't Create Default Tool Triggers

**The principle:** Remove "if in doubt, use this tool" or "when unsure, default to X" instructions. These create a low-confidence trigger that fires far more often than intended because the model's uncertainty threshold is lower than you expect.

**Why it happens:** Opus 4.6 maintains calibrated uncertainty about most decisions. "If in doubt" matches a huge portion of the model's decision space. The instruction effectively becomes "use this tool most of the time," which is rarely what you want.

**The pattern:** Specify positive trigger conditions. Describe the situations where a tool should be used, not the emotional state (doubt, uncertainty) that should trigger it.

```markdown
# Good
Use web_search when the user asks about events, prices, or facts
that change over time and where your training data may be outdated.

# Good
Use memory_search before answering questions about prior conversations,
user preferences, project history, or previously made decisions.
```

Each tool should have a clear, specific activation condition. If you can't articulate when a tool should trigger without using words like "unsure" or "in doubt," the tool's role in your system isn't well-defined yet.

---

## 5. Match Prompt Format to Output Format

**The principle:** The formatting style of your prompt influences the formatting style of the model's output. If your system prompt uses dense bullet lists, the model tends to produce dense bullet lists. If your prompt uses flowing paragraphs, the model leans toward prose.

**Why it matters:** This is one of the most reliable and least-discussed levers for controlling output style. It works because the model treats the prompt as part of the same document and maintains stylistic consistency.

**The pattern:** Write your prompt in the style you want your outputs.

```markdown
# If you want concise, structured responses:
Write your system prompt with short sections, clear headers,
and minimal prose between instructions.

# If you want conversational, natural responses:
Write your system prompt in a more conversational tone, with
complete sentences and a natural flow between ideas. The model
picks up on this voice and mirrors it.
```

This also applies to:
- **Header depth:** If you use `##` headers in your prompt, the model tends to use `##` headers in its output.
- **List style:** Numbered lists in the prompt bias toward numbered lists in output.
- **Code formatting:** Heavy use of code blocks in the prompt increases code block usage in output.

Design your prompt as a template for the kind of document you want back.

---

## 6. Structure for Scannability, Not Completeness

**The principle:** Opus 4.6 retains information across its full context window, but it prioritizes instructions that are easy to parse structurally. Dense paragraphs of rules get less consistent adherence than the same rules in a scannable format.

**The pattern:** Use consistent structure. Group related instructions. Use headers as semantic anchors.

```markdown
## Tool Usage

memory_search: Run before answering questions about prior work,
decisions, dates, people, or preferences.

web_search: Run when the user asks about current events, live
prices, recent news, or anything time-sensitive.

message: Use for proactive sends and channel actions. When using
message to deliver your reply, respond with NO_REPLY to avoid
duplicates.
```

Each instruction block should be independently understandable. The model doesn't need narrative transitions between sections.

---

## 7. Contextual Rules Over Universal Rules

**The principle:** Rules scoped to specific situations get followed more reliably than broad universal rules. This is because the model can clearly evaluate whether a scoped rule applies, whereas universal rules require constant background evaluation.

**The pattern:** Attach conditions to instructions.

```markdown
# Good
In group chats, keep responses brief and only speak when directly
addressed or when you can add genuine value. In direct messages,
be more conversational and thorough.

# Good
When the user sends a URL without commentary, ingest it to the
knowledge base. When the user sends a URL with a question, answer
the question using the URL content.
```

Universal rules ("always be concise") create tension with situational needs. Contextual rules let the model adapt without feeling like it's violating instructions.

---

## 8. Trust the Model's Judgment

**The principle:** Opus 4.6 makes better decisions when given decision-making frameworks than when given exhaustive decision trees. Over-specifying behavior for every possible scenario makes the prompt brittle and the model rigid.

**The pattern:** Define principles and boundaries. Let the model handle the space between them.

```markdown
# Good
You have access to the user's files, messages, and calendar.
Internal actions (reading, organizing, searching) are fine to do
freely. External actions (sending emails, posting publicly,
contacting others) require user confirmation first.

The distinction: anything that leaves the user's private
environment needs approval. Anything inside it doesn't.
```

This gives the model a clear mental model for classifying new situations, rather than a lookup table that will inevitably have gaps.

---

## 9. Subagent Delegation: Keep the Main Thread Alive

**The principle:** Anything beyond a simple reply should be offloaded to a background worker. The main conversation stays responsive while complex work (search, data processing, API calls, multi-step tasks) runs in parallel.

**Why it matters:** Users don't want to wait 45 seconds staring at a typing indicator. Spawning a subagent lets the model acknowledge the request immediately and continue the conversation naturally. The result gets delivered when it's ready.

**The pattern:** Define a clear delegation threshold and failure policy.

```markdown
Simple replies (factual answers, config tweaks, quick lookups):
handle directly in the main session.

Everything else (web searches, data processing, multi-step workflows,
API integrations): spawn a background worker. Acknowledge the task,
then stay available.

If a worker fails, retry once. Transient errors (timeouts, rate limits)
are common and usually resolve on retry. If the second attempt also
fails, report both errors to the user and stop. No retry loops.
```

The retry-once-then-stop rule prevents the model from burning tokens on cascading failures. Two attempts is enough to distinguish "temporary glitch" from "actually broken."

---

## 10. Coding Delegation: Right Model for the Job

**The principle:** The best conversational model isn't necessarily the best code-writing model. Split the work: conversation stays with the general model, complex coding goes to a specialized coding model or agent.

**The pattern:** Define a complexity threshold for delegation.

```markdown
Simple changes (config edits, single-line fixes, small patches):
handle directly.

Medium to major work (multi-file features, complex logic, large
additions, architectural changes): delegate to a coding agent
with a specialized model.

When a system recommendation says "fix this issue" or "implement
this feature," default to delegation unless it's clearly trivial.
```

This avoids the failure mode where a conversational model attempts a 500-line refactor and produces subtly broken code that takes longer to debug than it would have taken to write correctly with a coding-optimized model.

---

## 11. Shared Module Architecture

**The principle:** Build a library of reusable utilities that all skills, tools, and agents share. Consistency across the system matters more than local optimization.

**Why it matters:** When every component uses its own database wrapper, embedding model, retry logic, and message formatting, the system becomes impossible to maintain. A shared module library ensures:

- All vector embeddings use the same model, so similarity scores are comparable across subsystems (CRM, knowledge base, business analysis)
- Secret redaction happens in one place, not reimplemented per feature
- Error handling and retry patterns are consistent
- Telegram delivery, config management, and content sanitization follow the same conventions

```markdown
Shared modules (examples):
- database: connection pooling, migration helpers
- embeddings: single model for all vector operations
- retry: exponential backoff with jitter, configurable max attempts
- redact: API key and token masking for outbound messages
- sanitize: content cleaning for LLM input
- deliver: Telegram message formatting and sending
- config: unified config loading with environment overrides
```

The embedding model consistency point deserves emphasis: if your CRM uses `all-MiniLM-L6-v2` but your knowledge base uses `text-embedding-3-small`, you can't meaningfully compare or combine results across them.

---

## 12. Heartbeat Design: Silence Means Healthy

**The principle:** Regular health monitoring should only surface when something needs attention. No news is good news. Design heartbeats to be invisible when the system is healthy.

**The pattern:** Define check frequencies by risk level and only alert on anomalies.

```markdown
Daily checks:
- Data freshness (are collectors still running?)
- Error log scan (new errors since last check?)
- Git backup status (last commit within expected window?)
- Repo size (unexpected growth?)

Weekly checks:
- Gateway security (localhost binding, auth enabled)
- Service health (all LaunchAgents loaded and recent?)

Monthly checks:
- Memory file security scan (leaked secrets?)
- Dependency audit (known vulnerabilities?)

Alert policy: only notify when a check fails or detects an anomaly.
A quiet heartbeat means everything passed. Don't send "all clear"
messages; they train the user to ignore notifications.
```

The "silence = healthy" principle is critical. If the system sends "everything's fine" messages daily, the user stops reading them, and when a real alert comes through, it gets lost in the noise.

---

## Summary of Shifts

| Earlier Models | Opus 4.6 |
|---|---|
| Emphasis through CAPS and repetition | Plain statements, trusted recall |
| Rigid rules | Rules with rationale |
| Good and bad examples | Good examples only |
| "If in doubt, use X" | Specific trigger conditions |
| Exhaustive decision trees | Principles with boundaries |
| Format as afterthought | Format as implicit template |
| Everything in main thread | Background workers for heavy tasks |
| One model for everything | Specialized models per task type |
| Per-feature implementations | Shared module library |
| Verbose health reports | Alert on anomaly, silent when healthy |

---

## A Note on Iteration

These patterns aren't universal laws. They're observations from working with Opus 4.6 that hold across a wide range of use cases. The meta-principle is: treat the model as a capable reader who follows instructions faithfully, sometimes too faithfully. Write prompts the way you'd write instructions for a very literal, very competent colleague.

When something isn't working, the fix is almost always "be clearer about what you want" rather than "be louder about what you want."
