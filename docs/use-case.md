# Use case — analyze an unknown FastAPI repository

## Objective

Given a repository the agent has never seen, produce a **verifiable analysis
report**: its architecture and how routes are wired, its dependencies, its risks
or issues, and the useful commands to run it and its tests. The results are
written to a documentation folder, one file per contributing agent.

This was chosen over a feature-addition ("add endpoint X") use case for one
reason: **binary verifiability**. Whether an added feature is "good" is a matter
of taste; whether the report correctly names the entry point, the router wiring,
and the test command is checkable against the repository. A checkable objective
makes the evidence (see [`evidence/task-evidence.md`](evidence/task-evidence.md))
gradable rather than impressionistic.

## Why FastAPI, framework-level

The RAG corpus is **framework-level** (FastAPI docs), not language-level (all of
Python). Rationale: retrieval quality is a ranking / top-k problem, and a focused
corpus buys high precision for free — it avoids the metadata-filtering and
re-ranking machinery a huge corpus would demand. The slogan is *"specialized
knowledge (the RAG corpus), general targets (any unknown repo on that
framework)."* FastAPI specifically keeps harness friction low (Python) while
having enough surface (routers, dependencies, lifespan, testing) to make the
analysis non-trivial. See [`rag-base.md`](rag-base.md).

## How the team fulfills it

The principal is a **coordinator** that owns no tools; it delegates to five
role-scoped analysis subagents, then a run-boundary **Scribe** writes the results.

| Agent | Tools | Role in this use case |
| --- | --- | --- |
| Explorer | `read_file`, `list_files` | Map structure, architecture, dependencies, conventions. |
| Researcher | `rag_search` (RAG-first), `web_search` (fallback) | Confirm the relevant FastAPI conventions against the corpus. |
| Implementer | `read_file` | *Propose* remediations as text — never applies them (a deliberate safety choice). |
| Tester | `read_file`, `run_command` | Run the target's tests/build/lint to gather real evidence. |
| Reviewer | `read_file` | Check the findings actually answer the request. |
| **Scribe** | `write_file`, `list_files` | The **only** writer; confined to the docs folder; documents each agent's findings after the run. |

## Success criteria

A run is successful when the produced report and per-agent documents:

1. Name the **entry point** and how routes are wired (e.g. `app.include_router`).
2. List the **dependencies** (from the requirements/manifest).
3. State the **command to run the tests** and, where the Tester ran them, the result.
4. Surface at least one **real risk** (e.g. in-memory storage, missing config layer).
5. Cite **sources** by origin (RAG vs. repo vs. web), so claims are traceable.

The two committed runs over `scripts/sample_app` meet these — see the evidence
index. Both correctly identified the `APIRouter` wiring, the in-memory store
risk, and the `PYTHONPATH=… pytest -q` test command; the Tester ran the suite
(PASS) in one run.

## Boundaries

- The agent **reads** the target and **writes only** into its documentation
  folder — it never modifies the analyzed repository (enforced by policy, not
  just prompt; see [`architecture.md`](architecture.md#security--policy)).
- The report is only as good as the model's coordination. With a small model
  (`gpt-5-nano`) subagents sometimes hit their iteration cap; they then return
  **partial findings** (what they found + why partial) rather than nothing.
