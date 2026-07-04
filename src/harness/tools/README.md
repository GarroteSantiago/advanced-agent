# `harness.tools` — the side-effect chokepoint

Everything the agent does to the world goes through one object, the
`ToolExecutor`. It is the **single chokepoint for side effects**: it resolves the
tool, consults an `Approver` (supervision + config policy) *before* invoking, and
turns every failure into a `ToolResult` so the loop always has an observation to
feed back. Nothing else invokes a tool.

> Diagram: [`tools.puml`](tools.puml). Up one level: [`../README.md`](../README.md).

## The ports

| Port | File | Contract |
| --- | --- | --- |
| `Describable` | [`tool.py`](tool.py) | `name`, `description`, `parameters()`. Both tools *and* subagents are `Describable`, so a single `ToolCatalog` renders either into a model schema. |
| `ToolInterface` | [`tool.py`](tool.py) | `Describable` + `mutates` (does invoking change the world?) + `async invoke(request) -> ToolResult`. `mutates` is what supervision gates. |
| `Approver` | [`approval.py`](approval.py) | `async review(request, *, mutating) -> Approval`. |
| `Confirmer` | [`approval.py`](approval.py) | `async confirm(request) -> bool` — asks a human. |

## Key objects

### Execution & lookup

| Type | File | Role |
| --- | --- | --- |
| `ToolExecutor` | [`executor.py`](executor.py) | `execute(call) -> ToolResult`, **never raises on tool failure**. Emits `ToolInvoked`/`ToolObserved`. Unknown tool → failure result; approver denial → failure result; exception inside a tool → failure result (the loop boundary). |
| `ToolRegistry` | [`registry.py`](registry.py) | Encapsulated `name → tool` map; the only lookup path. `register` (raises `DuplicateToolError`), `get` (raises `UnknownToolError`), `has`, `tools`, `catalog`. |
| `ToolCatalog` | [`catalog.py`](catalog.py) | Immutable set of `ToolSchema`s ready for a `ChatModel`. Owns the schema shape so no other component encodes it. `of_tools`, `for_model`. |
| `ToolRequest` | [`request.py`](request.py) | Immutable instruction handed to `invoke` (`call_id`, `tool_name`, `arguments`). |
| `ToolResult` | [`result.py`](result.py) | Carries behavior, not just data: `to_message()` renders itself as a TOOL observation; `modified` names files changed **as data**, so the loop records them in the ledger without parsing prose. `success`/`failure` factories. |

### Approval & policy — [`approval.py`](approval.py), [`policy.py`](policy.py)

| Type | Role |
| --- | --- |
| `Approval` | Verdict: `allow()` / `deny(reason)`; `denied()`. A denied reason becomes the tool observation. |
| `AutoApprover` | Approves everything — the default. |
| `SupervisionPolicy` | Human-in-the-loop: approves read-only freely; when `enabled`, asks a `Confirmer` before any **mutating** action. |
| `CompositeApprover` | Chains approvers; **first denial wins (fail-closed).** |
| `PolicyConfig` | Declarative guardrails from TOML (stdlib `tomllib`, no dependency): `workspace`, `read_deny`, `write_deny`, `command_deny`, `command_require_approval`. |
| `PolicyVerifier` | An `Approver` that maps a call to its rule: file tools' `path` vs deny-globs + workspace confinement; `run_command`'s `command` vs deny-list + require-approval. **Fails closed.** |

> **Honest caveats (from the source):** glob matching is `fnmatch` (`*` spans
> separators); command matching is substring-based — a guardrail, not a sandbox.

This is where the **Scribe's confinement** comes from: a per-agent
`PolicyVerifier` with `workspace = docs_dir` denies any write outside the docs
folder before the tool ever runs (see [`../../agent/`](../../agent/)).

### Adapters (outer ring) — [`adapters/`](adapters/)

| Tool | `mutates` | Purpose |
| --- | --- | --- |
| `read_file` | no | Read a file's contents. |
| `list_files` | no | List a directory. |
| `web_search` | no | Tavily web search. |
| `echo` | no | Trivial demo/tests tool. |
| `write_file` | **yes** | Write/replace a file; reports the path in `ToolResult.modified`. |
| `run_command` | **yes** | Run a shell command. |

## Where it sits in the onion

`approval` lives in `tools` (not `control`) on purpose: the executor consults it,
and `control` already depends on `runtime` which depends on `tools` — putting it
here keeps the dependency arrows pointing inward. Consumed by
[`loop`](../loop/)'s action phases; wired in [`assembly.py`](../assembly.py) and
the app layer.
