# Reflection

## What the constraints bought

Building **without an orchestration framework** was the defining constraint, and
it paid off in understanding. Every mechanism a framework would hide — the ReAct
loop, delegation, the event stream, retrieval, context windowing — had to be a
named object with a reason to exist. The result is a system whose control flow
you can read top to bottom, and whose seams (ports) are explicit rather than
convention. The dependency list is three libraries; there is nothing magic.

The two decisions that most shaped the codebase:

- **An immutable execution spine.** Making `AgentExecutionContext` and
  `TaskLedger` copy-on-write removed a whole class of bugs — phases and subagents
  share state without being able to corrupt each other's view. Sharing one ledger
  across the principal and its subagents became trivially safe.
- **A transition sum type instead of `None`.** Having the navigator return
  `Continue | Halt` (extensible to `AwaitInput`) rather than a boolean kept the
  loop honest as behavior grew. Small type choices compound.

## What was hard, and what it taught

- **Coordination with a small model.** The sharpest lesson. `gpt-5-nano`
  under-delegates: it would call the Scribe with one agent's findings, or ask the
  Reviewer to review before passing it anything. The fix was not a better prompt
  but a **structural** one — move the Scribe to a deterministic run-boundary
  `Documenter` that is *handed* the whole ledger. General principle: don't ask the
  model to reliably do orchestration you can do deterministically in code.
- **Where persistent memory plugs in.** The instinct (and an early plan note) was
  "inject via `ContextManager`." That was the wrong seam — it would make a pure
  windowing projection stateful and re-inject every turn. Keeping `ContextManager`
  pure and adding a run-boundary `ProjectMemoryService` was cleaner. The same
  boundary-seam shape then solved the Scribe problem. A pattern worth reusing.
- **Honest observability.** Getting a *single-rooted* trace meant realizing that a
  subagent's forwarded stop must not close the run root. It's the kind of bug that
  only shows up once you actually look at the trace — which is the point of
  building the observability early.

## Honest limitations

- **Structural, not semantic, context management.** `ContextManager` windows;
  it does not summarize. A model-based `Summarizer` is a designed-in seam, unbuilt.
- **Deterministic, coarse memory capture.** `ProjectMemoryService.absorb` fills
  the `summary`/`files` buckets from the ledger; sorting learnings into the finer
  §2 categories (architecture, deps, bugs…) is the noted model-*digest* seam.
- **Ledger fields not fully auto-populated.** `progress` and `observations` have
  transitions but aren't auto-filled with milestones yet; repo/web reads aren't
  auto-tagged as `Source`s the way RAG hits are.
- **"Ask for help" is latent.** The loop's sum type has room for `AwaitInput`, but
  the agent currently *changes strategy / stops* (nudge-then-stop, partial
  findings) rather than actively asking a human mid-run.
- **Model-dependent output.** Reports are only as good as the coordination on the
  day; small models sometimes leave subagents at their iteration cap (they then
  return partial findings rather than nothing).

## What I would do next

1. The **model-digest** seam for memory — categorize learnings into the finer
   buckets so a second run recalls *architecture*, not just *summaries*.
2. Auto-tag repo/web reads as ledger `Source`s and populate `progress`/`observations`.
3. Wire `AwaitInput` so the agent can genuinely ask for help when blocked.
4. A `Summarizer` behind `ContextManager` for very long runs.
5. Raise/adapt the subagent iteration cap (or feed context) so explore/test stop
   capping while still making progress.

## Meta

TDD held up well: 196 tests, the loop and subagents driven entirely by a scripted
fake model, the OTel boundary smoke-tested against a real SDK. The discipline that
mattered most was **stating uncertainty in the docs** — every "done" here carries
its caveat, and the scorecard (`TP_REQUISITS.md`) distinguishes *mechanism built*
from *live-verified* from *packaged as evidence*. That honesty is worth more than
a wall of green checkboxes.
