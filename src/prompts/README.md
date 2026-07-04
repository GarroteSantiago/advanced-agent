# `prompts` — role prompts (wording kept out of behavior)

The system/role prompts for the principal coordinator and each subagent, as
module-level string constants. Isolated in their own package **so wording can
change without touching behavior** — nothing here imports anything; everything
else imports these.

> Up one level: [`../README.md`](../README.md).

## The prompts

| Constant | Used by | Gist |
| --- | --- | --- |
| `PRINCIPAL_PROMPT` | the coordinator ([`agent/cli.py`](../agent/cli.py)) | "You own no tools; delegate to the five subagents and synthesize. The Scribe persists findings after the run — you don't call it." |
| `EXPLORER_PROMPT` | `explore` subagent | Map structure, architecture, deps, conventions with `read_file`/`list_files`; name the files relied on. |
| `RESEARCHER_PROMPT` | `research` subagent | `rag_search` FIRST, `web_search` only as fallback; cite sources. |
| `IMPLEMENTER_PROMPT` | `implement` subagent | Read code, **propose** changes as text; never write files. |
| `TESTER_PROMPT` | `test` subagent | Run build/tests/lint with `run_command`; report pass/fail; don't modify the repo. |
| `REVIEWER_PROMPT` | `review` subagent | Judge whether findings answer the request; flag gaps/contradictions. |
| `SCRIBE_PROMPT` | the Scribe ([`agent/team.py`](../agent/team.py)) | The only writer; write ONE file per contributing agent; writes outside the docs folder are refused. |

The prompts encode the **division of labor** the code enforces structurally: the
principal has no tools, the implementer's toolset excludes `write_file`, the
Scribe is policy-confined. Prompt and mechanism agree — the prompt states the
contract, the [`tools`](../harness/tools/) policy enforces it.
