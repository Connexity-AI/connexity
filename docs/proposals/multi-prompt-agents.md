# Multi-Prompt Agent Support — Research & Implementation Plan

**Status**: Proposal
**Audience**: Engineering, Product, OSS contributors
**Scope**: Adding modular / multi-prompt agent support for Custom (BYO inference endpoint) agents on connexity-evals

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Industry Landscape: How Modular Prompting Works Today](#2-industry-landscape-how-modular-prompting-works-today)
   - 2.1 [Vocabulary across platforms](#21-vocabulary-across-platforms)
   - 2.2 [How transitions are decided](#22-how-transitions-are-decided)
   - 2.3 [Tool scoping](#23-tool-scoping)
   - 2.4 [API export and import](#24-api-export-and-import)
   - 2.5 [Per-turn observability — the universal weak spot](#25-per-turn-observability--the-universal-weak-spot)
   - 2.6 [Takeaways](#26-takeaways)
3. [Scope](#3-scope)
4. [Current State and Required Adjustments](#4-current-state-and-required-adjustments)
   - 4.1 [Current state of connexity-evals](#41-current-state-of-connexity-evals)
   - 4.2 [Description schema (high level)](#42-description-schema-high-level)
   - 4.3 [Mockup updates required](#43-mockup-updates-required)
   - 4.4 [Test case generation (high level)](#44-test-case-generation-high-level)
   - 4.5 [Evaluation engine (high level)](#45-evaluation-engine-high-level)
   - 4.6 [Node attribution: how we know which prompt was active](#46-node-attribution-how-we-know-which-prompt-was-active)
   - 4.7 [Tools, versioning, and observe tab](#47-tools-versioning-and-observe-tab)
5. [Advanced: Implementation Specification](#5-advanced-implementation-specification)
   - 5.1 [Data model and schema](#51-data-model-and-schema)
   - 5.2 [Backend changes](#52-backend-changes)
   - 5.3 [Frontend changes](#53-frontend-changes)
   - 5.4 [Test case generator changes](#54-test-case-generator-changes)
   - 5.5 [Evaluator changes](#55-evaluator-changes)
   - 5.6 [Migration and rollout](#56-migration-and-rollout)
6. [Bonus: Third-Party Importers](#6-bonus-third-party-importers)
   - 6.1 [Why importers matter](#61-why-importers-matter)
   - 6.2 [Provider-to-Connexity schema mapping](#62-provider-to-connexity-schema-mapping)
   - 6.3 [Recommended order](#63-recommended-order)
   - 6.4 [Claude Code prompt: Retell importer (reference implementation)](#64-claude-code-prompt-retell-importer-reference-implementation)
7. [Open Questions and Decisions to Lock](#7-open-questions-and-decisions-to-lock)
8. [Sources](#8-sources)

---

## 1. Executive Summary

The single-prompt path on connexity-evals works because we receive enough information to drive both test case generation and evaluation: the customer hands us a system prompt and tool definitions, and we evaluate against their inference endpoint with full context.

Modular ("multi-prompt") agents break that flow. The customer's endpoint runs a state machine internally, but we have no description of its structure on our side, so our generator and evaluator are blind to it.

This proposal adds a **description-only** multi-prompt model: customers describe their graph (nodes + edges) in our UI, and we use that description to (a) generate path-aware test cases and (b) score graph-aware evaluations against the existing endpoint contract. We do **not** simulate the graph — execution stays on the customer's side.

The data model converges with industry practice (adjacency-list of nodes with per-node transition edges). The attribution problem — *which node was active at each turn* — is solved through two non-exclusive cooperation tiers that ride on the existing `AgentRequest`/`AgentResponse` envelope:

- **Tier A** (transition tool signal): we observe tool calls in the response and treat configured transition-tool calls as ground truth.
- **Tier B** (response metadata): we read `response.metadata.connexity` for explicit `active_node_id` / transition records.

Without either tier, the graph still drives test case generation and node-aware judging of the transcript; only fine-grained transition metrics are unavailable.

---

## 2. Industry Landscape: How Modular Prompting Works Today

### 2.1 Vocabulary across platforms

Despite different brand names, every modular construct surveyed reduces to **nodes + edges over a shared agent context**. The naming differs:

| Platform | Modular construct | Node term | Edge term |
|---|---|---|---|
| Retell (Multi-Prompt) | Multi-Prompt Agent | `state` | `edge` (with `description`) |
| Retell (Conversation Flow) | Conversation Flow | `node` (13 typed) | `edge` (prompt- or equation-based) |
| VAPI | Squad of Assistants (recommended) | `assistant` | "Handoff" tool call |
| VAPI | Workflow (legacy) | `node` (Conversation / API / Tool / Transfer / End / Global) | `edge` (AI / Liquid / combined) |
| ElevenLabs Agents | Workflow | `subagent` / `tool` / `say` / `agent_transfer` / `end` / `start` | `edge` (LLM Condition / Expression / None / tool-success/failure) |
| ElevenLabs Agents | Cross-agent transfer | n/a (separate agents) | `transfer_to_agent` system tool with `condition` |
| Bland | Conversational Pathway | `node` (Default / End / Transfer / KB / Webhook) | `edge` with `label` + `conditions` |
| Synthflow | Flow Designer | `node` (Greeting / Conversation / Branch / Transfer / Trigger Subflow) | Branch routing on variables/results |
| Pipecat Flows | `FlowConfig` | `NodeConfig` (role_messages, task_messages, functions) | Consolidated handler returns `(result, next_node)` |
| OpenAI Agents SDK | Agent + handoffs | `agent` | `handoff` exposed as a tool |
| LangGraph | `StateGraph` | `node` over typed `state` | `add_edge` / `add_conditional_edges` / node-returned `Command` |

Three design "shapes" exist underneath:

1. **Visual / declarative graph** with explicit edges and condition DSL — Retell Conversation Flow, VAPI Workflows, Bland Pathways, ElevenLabs Workflows, Synthflow. Aimed at non-engineers; easy to diff and simulate per edge.
2. **Multi-agent handoff** where each "agent" is a complete persona and transitions are routing tool calls — VAPI Squads, OpenAI Agents SDK handoffs, ElevenLabs `transfer_to_agent`. Best for cleanly separated specialists.
3. **Code-defined graph** where nodes are objects and transitions are functions or returned commands — Pipecat Flows consolidator, LangGraph. Most flexible; hardest to evaluate as data.

### 2.2 How transitions are decided

Every platform combines some subset of these mechanisms:

- **LLM-judged**: a natural-language predicate on the edge ("when the user confirms the booking"), evaluated by the model per turn. Universal.
- **Logical / DSL**: variable comparisons (VAPI Liquid `{{ total_orders > 50 }}`, Retell equation-based, ElevenLabs Expression, Bland conditions).
- **Function-call-driven**: tool nodes route via success/failure outcomes; the act of calling a tool implies a transition (ElevenLabs tool nodes, Retell function nodes, Pipecat consolidated handlers).
- **Hidden meta-tool**: in handoff models, the platform injects a tool like `transfer_to_<agent>` and the LLM "picks" the destination by tool selection (VAPI Squads, ElevenLabs `transfer_to_agent` with `agent_number`, OpenAI handoffs).

None of these expose a generic public `switch_node()` tool callable from a BYO LLM — routing is always internal to the platform.

### 2.3 Tool scoping

| Platform | Global tools | Per-node tools |
|---|---|---|
| Retell Multi-Prompt | `general_tools[]` | `states[].tools[]` |
| Retell Conversation Flow | top-level `tools[]` | only on `subagent`/`function` nodes |
| VAPI Squads | per-Assistant | n/a (Assistant is the unit) |
| VAPI Workflows | tool library | per Tool/API node |
| ElevenLabs Workflows | `agent_config.prompt.tool_ids[]` | subagent `additional_tools` / overrides |
| Pipecat Flows | none global | per `NodeConfig.functions` |

The dominant pattern is **global with optional per-node overrides**. That matches our current agent-scoped tools model and is forward-compatible with adding per-node subsets later.

### 2.4 API export and import

Every hosted platform exposes the full graph as JSON via REST:

- **Retell**: `GET /get-retell-llm/{id}` (multi-prompt) and `GET/POST /create-conversation-flow` (CF). Round-trippable. Versioned.
- **VAPI**: `PATCH /workflow/{id}` (BETA) returns `{ nodes, edges, model, voice, transcriber }`. Squads via assistants API. Workflow versioning not documented.
- **ElevenLabs**: `GET/POST/PUT /v1/convai/agents/...` returns the full `conversation_config.workflow` tree. Branch-based versioning with traffic split.
- **Bland**: `GET /v1/pathway/{id}` + `POST /update_pathways`. Versioned.
- **Synthflow / OpenAI / Pipecat / LangGraph**: declarative export less complete or in-code only.

Importers are mechanical to build (mostly schema mapping). See [Section 6](#6-bonus-third-party-importers).

### 2.5 Per-turn observability — the universal weak spot

This is where the field is **weak across the board**:

- **Retell**: no documented per-turn-active-state field on the call object.
- **VAPI**: call logs reference "conversation flow" but no documented per-turn-node-id field.
- **ElevenLabs**: `visited_agents[]` array + `is_workflow_node_transfer` flag exist, but per-turn node tagging is not explicitly documented.
- **Bland**: trajectories visible in UI; not in a documented per-turn API field.

Nobody in the public market evaluates transitions rigorously from external data. **There is room to differentiate here.**

### 2.6 Takeaways

- A simple **adjacency-list** model (`main_prompt + nodes + per-node transitions`) covers every modular construct we surveyed without inventing new vocabulary.
- A **free-text condition** on each edge plus **LLM-as-judge for evaluation** sidesteps DSL design without losing fidelity.
- **Tools should remain agent-scoped** initially; per-node subsets are an additive future change.
- **Per-turn attribution is solvable** via the existing endpoint contract — see [Section 4.6](#46-node-attribution-how-we-know-which-prompt-was-active).

---

## 3. Scope

This proposal targets **Custom** agents only — i.e., agents in `endpoint` mode where the customer hosts their own OpenAI-compatible inference endpoint conforming to our [agent contract](../agent-contract.md). Connexity-evals acts as the simulated caller; the customer's endpoint runs the prompt, the tool loop, and (in the multi-prompt case) any internal routing between sub-prompts.

**In scope**:
- A description schema for multi-prompt agents on the platform side.
- Updates to test case generation so it can target paths through the graph.
- Updates to evaluation so it can score node-aware and transition-aware behavior.
- Two non-exclusive attribution mechanisms riding on the existing endpoint contract.
- UI updates to author and review multi-prompt agents.

**Explicitly out of scope** (for v1):
- Running / simulating multi-prompt execution on connexity-evals (no first-party state-machine runtime).
- Mocking tools on our side for endpoint-mode agents (the customer continues to own the tool loop, per the existing contract).
- Versioning / deployment lifecycle for multi-prompt graphs (matches the original mockup's "observe and evaluate only" posture; flat-versioned schema is acceptable for v1).
- Per-node tool subsets (forward-compatible; not authored in v1).
- Importing multi-prompt agents from external providers (covered as a Bonus in [Section 6](#6-bonus-third-party-importers)).

---

## 4. Current State and Required Adjustments

### 4.1 Current state of connexity-evals

Verified by reading the codebase:

- **Agent model** ([`backend/app/models/agent.py`](../../backend/app/models/agent.py)): two modes — `endpoint` (customer's URL) and `platform` (our simulator). `Agent.system_prompt` is a single string; `Agent.tools` is agent-scoped JSONB.
- **Versioning** ([`backend/app/models/agent_version.py`](../../backend/app/models/agent_version.py)): each `AgentVersion` snapshots `system_prompt`, `tools`, model config, and a `change_description`.
- **Endpoint contract** ([`docs/agent-contract.md`](../agent-contract.md), [`backend/app/models/agent_contract.py`](../../backend/app/models/agent_contract.py)): `AgentRequest = { messages, metadata? }`; `AgentResponse = { messages, model?, provider?, usage?, metadata? }`. Customer's endpoint runs the entire internal turn (including any tool calls) and returns the unrolled `messages` array. Both `metadata` envelopes are open dicts.
- **Test case generator** ([`backend/app/services/test_case_generator/`](../../backend/app/services/test_case_generator/)): consumes `agent_prompt` + `tools`. No graph awareness.
- **Evaluator** ([`backend/app/services/judge_metrics.py`](../../backend/app/services/judge_metrics.py)): scores from a flat transcript. No node-attribution awareness.

### 4.2 Description schema (high level)

Customers describe their multi-prompt agent as an adjacency list:

- **Main prompt** — shared context across all sub-prompts (persona, hard rules, tone).
- **Nodes** — each has an `id`, `name`, and `prompt` (task-specific instructions for that sub-prompt).
- **Transitions** — per node, a list of outgoing edges, each with a target `to` node and a free-text `when` condition.
- **Start node** — exactly one node is marked as the entry point.
- **Terminal nodes** — any node with no outgoing transitions is terminal (no extra flag required).

Four concepts total. Forward-compatible: structured conditions, per-node tool subsets, and explicit `is_terminal` can be added later without breaking changes.

### 4.3 Mockup updates required

The original mockup proposed a flat list of additional prompts with a free-text "transition" string per prompt. This loses structure required for both test case generation and evaluation. The mockup should be updated as follows:

- **Replace** the single `Transition` textarea on each prompt card with a **`Transitions out`** list. Each row contains:
  - A dropdown selecting the target node (the other nodes in the agent).
  - A free-text `When:` condition.
  - Add / remove / reorder controls.
- **Add a start indicator** — a "Start" badge or radio on one node card. Defaults to the first card; users can change it.
- **(Optional, future)** A read-only graph view side-panel that auto-renders the topology from the schema (React Flow / Mermaid). Not load-bearing for v1.

The Tools and Settings tabs are unchanged. The Instructions tab is the only screen that changes shape.

### 4.4 Test case generation (high level)

The generator should walk the graph and produce test cases that target paths, not just isolated turns:

- **Path coverage** — for each path from start to a terminal node, generate at least one persona/scenario whose natural conversation should drive that path.
- **Edge-targeting cases** — generate scenarios designed to trigger each individual outgoing transition (so every `when` condition is exercised at least once).
- **Adversarial / edge-case** — generate inputs designed to ambiguously straddle two nodes (mid-flow topic switches, partial information, retractions) — empirically the failure modes that matter for modular agents.

Each generated test case carries an **expected path** (sequence of node IDs) so the evaluator can score trajectory match.

### 4.5 Evaluation engine (high level)

Existing flat-transcript metrics (resolution, tone, accuracy, custom metrics) continue to apply unchanged. Three new metric families are introduced for multi-prompt agents:

| Metric family | What it measures | Inputs |
|---|---|---|
| **Path correctness** | Did the agent visit the expected sequence of nodes? | `expected_path` (from test case) + actual node sequence (from attribution) |
| **Transition correctness** | At each transition, was it the right destination at the right time? | Per-edge inspection with the edge's `when` condition + transcript window |
| **Per-node objective completion** | While in node X, did the agent accomplish node X's task? | The node's `prompt` + the slice of transcript while that node was active |

A fourth, lighter heuristic (**stuck / loop detection**) flags pathological trajectories for human review.

All three families require **node attribution** (which node was active per turn). See next section.

### 4.6 Node attribution: how we know which prompt was active

Because we do not run the customer's graph and do not modify their prompts, attribution must come from the data the endpoint already returns. The existing contract gives us two cooperation channels:

- **Tier A — Transition-tool signal** (opt-in; zero or near-zero customer code). Most modular agents internally use a tool (e.g., `goto_state`, `switch_node`, `set_phase`, etc.) to change sub-prompts. Because the contract has the customer's endpoint return the full unrolled `messages` array (assistant tool calls included), those tool calls are already visible to us. UX: an optional `transition_tool_name` field on the agent. If set, we treat tool_calls with that name as ground-truth transitions.

- **Tier B — Response metadata convention** (opt-in; ~2 lines of customer code). The contract already declares `AgentResponse.metadata` as an open dict for "agent-defined metadata echoed for observability." We document a Connexity-namespaced convention so customers can populate `metadata.connexity.active_node_id` (or a transitions list) per turn. We treat this as ground truth.

**The two tiers are non-exclusive.** A customer can wire up both; if both are present, the metadata field wins (it's the most explicit). Either tier alone is enough.

**Graceful degradation**: if a customer enables neither, the multi-prompt graph still drives **test case generation** and **node-aware test case authoring** unchanged. The three new metric families ([Section 4.5](#45-evaluation-engine-high-level)) become "Not available" on that agent's eval runs; existing flat-transcript metrics continue to work normally. This is a clean, predictable degradation rather than a silent quality drop.

We do not use post-hoc LLM classification of turns. It is unreliable at scale and wastes tokens; we prefer to be honest about what we can and cannot score.

### 4.7 Tools, versioning, and observe tab

**Tools** stay agent-scoped in v1 — matching the dominant industry pattern (Retell, VAPI, ElevenLabs all treat tools as global with optional per-node overrides). Per-node tool subsets are a forward-compatible additive change for a future version; the v1 schema is structured so it can carry an optional `tools_subset: string[]` per node without a migration when needed.

**Versioning** is intentionally not extended to multi-prompt graphs in v1, matching the mockup's "observe and evaluate only" stance. The multi-prompt graph lives on the agent (or on a flat `AgentVersion`-shaped row without the publish/deploy lifecycle). Full versioning + deployment can be added later if customer demand emerges.

**Observe tab** (Retell-imported call records) benefits identically from the two attribution tiers — for Retell specifically, we can extract tool-call-style transitions from their call objects, which acts as Tier A "for free" once an importer exists. See [Section 6](#6-bonus-third-party-importers).

---

## 5. Advanced: Implementation Specification

> This section is intentionally written as a self-contained specification suitable for handing to Claude Code (or any implementing engineer). All file paths are repo-relative.

### 5.1 Data model and schema

#### 5.1.1 Add a `prompt_mode` discriminator

Add `prompt_mode: Literal["single", "multi"]` to both [`backend/app/models/agent.py`](../../backend/app/models/agent.py) (`AgentBase`) and [`backend/app/models/agent_version.py`](../../backend/app/models/agent_version.py) (`AgentVersion`). Default `"single"` so existing rows are unaffected.

#### 5.1.2 Add multi-prompt fields

On `AgentBase` and `AgentVersion`, add:

```python
main_prompt: str | None = Field(
    default=None,
    description="Shared context across all sub-prompts (multi-prompt agents).",
)

prompt_nodes: list[PromptNode] | None = Field(
    default=None,
    sa_column=Column(JSONB),
    description="Multi-prompt graph as adjacency list. Required when prompt_mode='multi'.",
)

transition_tool_name: str | None = Field(
    default=None,
    max_length=128,
    description=(
        "Optional. The name of the tool the customer's endpoint emits when "
        "transitioning between sub-prompts. If set, Connexity treats matching "
        "tool_calls in AgentResponse.messages as ground-truth transitions."
    ),
)
```

`PromptNode` is a Pydantic model (not a SQLModel table — stored inside the JSONB blob):

```python
class PromptNodeTransition(BaseModel):
    to: str = Field(..., description="Target node id within the same agent.")
    when: str = Field(..., description="Free-text natural-language condition.")

class PromptNode(BaseModel):
    id: str = Field(..., max_length=64, regex=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(..., max_length=128)
    prompt: str
    is_start: bool = Field(default=False)
    transitions: list[PromptNodeTransition] = Field(default_factory=list)
    # Forward-compatible (not authored in v1, ignored by v1 code):
    tools_subset: list[str] | None = None
    is_terminal: bool | None = None
```

#### 5.1.3 Validation rules

Add a Pydantic root-validator on the agent / version model:

- If `prompt_mode == "single"`: `main_prompt` and `prompt_nodes` must be `None`; `system_prompt` is required.
- If `prompt_mode == "multi"`:
  - `main_prompt` is required.
  - `prompt_nodes` must contain ≥ 1 node.
  - Exactly one node has `is_start=True`.
  - All `transitions[].to` references must resolve to an `id` in `prompt_nodes`.
  - Node IDs are unique within the agent.
  - `system_prompt` must be `None` (the single-prompt field is unused in this mode).

#### 5.1.4 Alembic migration

Create a new migration in `backend/app/alembic/versions/`:

- Adds the four columns above (`prompt_mode`, `main_prompt`, `prompt_nodes`, `transition_tool_name`) to both `agent` and `agent_version` tables.
- Backfills `prompt_mode = 'single'` for existing rows.
- No backfill needed for the other three columns (default `NULL`).

Run with `cd backend && bash scripts/prestart.sh` after generating; review the SQL before applying.

### 5.2 Backend changes

#### 5.2.1 Schemas (`backend/app/schemas/agent.py` or equivalent)

Update `AgentCreate`, `AgentUpdate`, `AgentRead` to surface the new fields. The TypeScript SDK is regenerated downstream — do not hand-edit `frontend/apps/web/src/client/`.

After the schema change, run:

```bash
bash scripts/generate-client.sh
```

#### 5.2.2 Endpoint contract (no shape change required)

The existing contract at [`backend/app/models/agent_contract.py`](../../backend/app/models/agent_contract.py) already supports both attribution tiers via the open `metadata` envelopes. **Do not modify the request/response shape.**

Document the Connexity-namespaced metadata convention in [`docs/agent-contract.md`](../agent-contract.md):

- **Request side** (optional, courtesy hook for customer observability): when running multi-prompt evals, Connexity may include `request.metadata.connexity = { test_case_id, expected_path? }`.
- **Response side** (Tier B): customer endpoint may include `response.metadata.connexity = { active_node_id?, transitions?: [{ from, to, turn_index }] }`. When present, Connexity uses this as ground truth.

#### 5.2.3 Attribution service

Add a small module `backend/app/services/attribution/multi_prompt.py` exposing:

```python
def attribute_turns(
    agent_version: AgentVersion,
    response_messages: list[ChatMessage],
    response_metadata: dict | None,
) -> list[NodeAttribution]:
    """Returns one NodeAttribution per assistant message in response_messages.

    Resolution order (Tier B beats Tier A):
      1. If response_metadata.connexity.transitions or .active_node_id is set,
         use it.
      2. Else, if agent_version.transition_tool_name is set, scan tool_calls
         in response_messages for matching name and infer node sequence.
      3. Else, return attributions with node_id=None for all turns.
    """
```

`NodeAttribution = { turn_index: int, node_id: str | None, source: Literal["metadata", "tool_call", "unknown"] }`.

Call this function once per `AgentResponse` during eval runs and store the resulting list alongside the existing transcript on `TestCaseResult`.

#### 5.2.4 Storage of attribution

Extend [`backend/app/models/test_case_result.py`](../../backend/app/models/test_case_result.py) with:

```python
node_attribution: list[NodeAttribution] | None = Field(
    default=None,
    sa_column=Column(JSONB),
    description=(
        "Per-turn node attribution for multi-prompt agents. None for "
        "single-prompt agents or when neither attribution tier is wired up."
    ),
)
```

Migration adds the column. No backfill.

### 5.3 Frontend changes

#### 5.3.1 New-agent dialog

In the agent-creation dialog, the "Prompt mode" radio (Single / Multi) writes `prompt_mode` on the new agent. No additional fields required at create time.

#### 5.3.2 Instructions tab — multi-prompt mode

Update [`frontend/apps/web/src/app/(app)/(agent)/agents/[agentId]/edit/page.tsx`](../../frontend/apps/web/src/app/(app)/(agent)/agents/[agentId]/edit/page.tsx) so the Instructions tab branches on `prompt_mode`:

- **Single (existing)**: the current single-textarea form.
- **Multi (new)**: render `<MultiPromptInstructions />`:
  - **Main prompt** — textarea bound to `main_prompt`.
  - **Additional prompts** — vertical list of `<PromptNodeCard />`. Each card:
    - Name input (bound to `node.name`).
    - Prompt textarea (bound to `node.prompt`).
    - "Start" radio (exactly one across all cards, bound to `is_start`).
    - **Transitions out** subsection: a list of `{ to: <select of other nodes>, when: <text> }`. Add/remove rows; reorder via drag handle.
    - Delete-node button.
  - **Add prompt** button at the bottom.

Form values shape:

```ts
type AgentInstructions =
  | { promptMode: "single"; prompt: string }
  | {
      promptMode: "multi";
      mainPrompt: string;
      nodes: {
        id: string;
        name: string;
        prompt: string;
        isStart: boolean;
        transitions: { to: string; when: string }[];
      }[];
    };
```

Validation runs client-side before save (mirroring [Section 5.1.3](#513-validation-rules)).

#### 5.3.3 Settings tab

Add an `Attribution` section with one optional input: `Transition tool name (optional)`. Bound to `transition_tool_name`. Help text: "If your endpoint emits a tool call to switch between sub-prompts, set the tool's name here so Connexity can score transitions."

#### 5.3.4 Tools tab

Unchanged in v1.

#### 5.3.5 Read-only graph view (optional, post-v1)

A `<MultiPromptGraph />` component that renders the topology from `nodes + transitions`. Place to the right of the Instructions tab list. React Flow recommended. Not required to ship v1.

### 5.4 Test case generator changes

In [`backend/app/services/test_case_generator/`](../../backend/app/services/test_case_generator/), the generator branches on `agent_version.prompt_mode`:

- **Single**: unchanged.
- **Multi**: the generator's prompt to its own LLM is augmented with the full graph (main prompt + all node prompts + all transitions). The system instruction asks the LLM to:

  1. Enumerate the distinct paths from start to a terminal node.
  2. For each path, generate one persona/scenario whose natural utterances should drive that path.
  3. Additionally, generate one scenario per outgoing transition that explicitly triggers its `when` condition.
  4. Generate a small number of adversarial scenarios (mid-flow topic switches, partial info, retractions).

Each test case stores its **expected path** (`list[str]` of node IDs) on the test case row. Add this column to [`backend/app/models/test_case.py`](../../backend/app/models/test_case.py):

```python
expected_path: list[str] | None = Field(
    default=None,
    sa_column=Column(JSONB),
    description="Expected sequence of node IDs (multi-prompt agents only).",
)
```

Migration adds the column. No backfill.

### 5.5 Evaluator changes

In [`backend/app/services/judge_metrics.py`](../../backend/app/services/judge_metrics.py), add three new metric implementations gated on:

```python
agent_version.prompt_mode == "multi"
and test_case_result.node_attribution is not None
and any(a.node_id is not None for a in test_case_result.node_attribution)
```

If the gate fails, all three metrics return `Unavailable` (a new verdict status alongside `pass` / `fail`) with an explanatory message. The existing flat-transcript metrics are unaffected.

The three metrics:

1. **Path correctness** — derive the actual path from `node_attribution` (deduplicated successive duplicates), compare against `test_case.expected_path`. Two flavors: strict equality and LLM-judged "semantic equivalence."
2. **Transition correctness** — for each transition in the actual path, locate the boundary turn in the transcript, evaluate the source node's outgoing edge condition (`when`) against the transcript window before and after the boundary using an LLM judge, and score correctness + timing.
3. **Per-node objective completion** — for each unique node visited, slice the transcript to turns attributed to that node and judge against the node's `prompt` using an LLM rubric.

All three reuse the existing `RunConfig.judge` infrastructure; surface them as built-in metric types selectable in the eval config UI.

### 5.6 Migration and rollout

- **Backwards compatibility**: all changes are additive. `prompt_mode` defaults to `"single"`; existing agents and test cases are unchanged.
- **Feature flag**: gate the new agent-creation option (Multi-prompt) behind a feature flag for the first release. Hide the option for users not in the rollout cohort.
- **Documentation**:
  - Update [`docs/agent-contract.md`](../agent-contract.md) with the metadata convention (Tier B) and the transition-tool config (Tier A).
  - Update [`docs/test-case-schema.md`](../test-case-schema.md) with `expected_path`.
  - Update [`docs/judge-criteria.md`](../judge-criteria.md) with the three new metric families and their unavailability semantics.
  - Update [`docs/data-model.md`](../data-model.md) with the new fields.
- **Acceptance criteria**:
  - Customer can create a multi-prompt agent, author main prompt + ≥ 2 nodes with transitions, save without server errors.
  - Test case generation produces test cases with non-null `expected_path` for multi-prompt agents.
  - Eval run against a customer endpoint with neither attribution tier wired up produces a result whose three new metrics show `Unavailable`, while existing metrics complete normally.
  - Eval run against an endpoint with Tier A or Tier B wired up produces non-null `node_attribution` and the three new metrics return scored verdicts.
  - Existing single-prompt tests continue to pass with no changes.

---

## 6. Bonus: Third-Party Importers

### 6.1 Why importers matter

The biggest commercial moat is letting customers **bring their existing modular agent into Connexity in one click** rather than re-author it. Every major hosted provider exposes the full graph as JSON via REST, so importers are mostly schema mapping. The mapping table below shows how cleanly each maps onto our description schema.

### 6.2 Provider-to-Connexity schema mapping

| Connexity field | Retell Multi-Prompt | Retell Conversation Flow | VAPI Squad | ElevenLabs Workflow |
|---|---|---|---|---|
| `main_prompt` | `general_prompt` | `global_prompt` | none (per-Assistant) | `agent_config.prompt.prompt` (top-level) |
| `prompt_nodes[].id` | `state.name` | `node.id` | `assistant.id` | `node.id` |
| `prompt_nodes[].name` | `state.name` | `node.name` or `node.label` | `assistant.name` | `node.label` |
| `prompt_nodes[].prompt` | `state.state_prompt` | `node` (subagent / conversation) prompt | `assistant.model.messages[0].content` | `subagent.system_prompt` / `additional_prompt` |
| `prompt_nodes[].is_start` | matches `starting_state` | matches `start_node_id` | the entry assistant | matches `start` node successor |
| `transitions[].to` | `edge.destination_state_name` | `edge.target_node_id` | `handoff.targetAssistantId` | `edge.to` |
| `transitions[].when` | `edge.description` | `edge.condition` (or compiled equation) | `handoff.condition` (LLM description) | `edge.condition` (LLM condition) |
| `transition_tool_name` | n/a (Retell internal) | n/a | `handoff_tool_name` if exposed | `transfer_to_agent` for cross-agent |

Some provider features have no v1 mapping and are dropped (with a warning surfaced to the importing user):

- Retell Conversation Flow node types beyond conversation/subagent (branch, function, code, extract_dynamic_variables, etc.).
- VAPI Workflow Liquid expressions on edges.
- ElevenLabs tool nodes with success/failure routing.

This is acceptable for v1: we import the conversational structure and skip control-flow primitives we can't represent. Customers who need richer features can author them manually after import.

### 6.3 Recommended order

1. **Retell** first. Justification: we already have a Retell integration for call sync ([`backend/app/services/integrations/retell/`](../../backend/app/services/integrations/) — confirm path), the JSON shape is the cleanest fit, and customer overlap is highest.
2. **VAPI** second. Squads map cleanly; Workflows partially. Worth shipping Squads-only initially.
3. **ElevenLabs** third. Workflow shape is rich; subset import covers most use.

### 6.4 Claude Code prompt: Retell importer (reference implementation)

> The following is a complete, self-contained prompt suitable for handing to Claude Code in a fresh session.

````markdown
# Task: Implement Retell multi-prompt agent importer

## Context

connexity-evals (the repo I'm working in) has just added support for multi-prompt agents — see `docs/proposals/multi-prompt-agents.md`, especially Section 5 ("Advanced: Implementation Specification") and Section 6 ("Bonus: Third-Party Importers"). Read those before starting.

The platform already has a Retell integration for call syncing. We now want to let users import their existing Retell **Multi-Prompt agents** and **Conversation Flow agents** into Connexity as native multi-prompt agents.

## Goal

Add an `Import from Retell` flow that, given a Retell agent ID and a Retell API key (already stored in our `Integration` table), fetches the agent's full structure and creates a Connexity Agent with `prompt_mode='multi'`.

## Connexity-side schema (read-only reference)

A Connexity multi-prompt agent (`Agent` + `AgentVersion`) carries:
- `prompt_mode: 'multi'`
- `main_prompt: str`
- `prompt_nodes: list[PromptNode]` — see `backend/app/models/agent.py` for the Pydantic shape.
- `transition_tool_name: str | None`

Each `PromptNode` has: `id` (lowercase slug), `name`, `prompt`, `is_start`, `transitions: [{to, when}]`.

Exactly one node must have `is_start=True`. All `transitions[].to` must reference a node `id` defined in the same agent.

## Retell API endpoints

- Agent metadata: `GET https://api.retellai.com/get-agent/{agent_id}`. Returns `response_engine.type` (`'retell-llm'` or `'conversation-flow'`) and `response_engine.llm_id` or `response_engine.conversation_flow_id`.
- Multi-Prompt LLM: `GET https://api.retellai.com/get-retell-llm/{llm_id}`. Returns `general_prompt`, `general_tools`, `states[]`, `starting_state`. Each state: `name`, `state_prompt`, `tools[]`, `edges[]`. Each edge: `destination_state_name`, `description`, `parameters`.
- Conversation Flow: `GET https://api.retellai.com/get-conversation-flow/{conversation_flow_id}`. Returns `global_prompt`, `tools[]`, `nodes[]`, `start_node_id`. Each node has `id`, `name`, `type`, and type-specific fields. Edges may live on the node (`node.edges[]`) or as a top-level array depending on Retell's current shape — check the live response.

Auth header: `Authorization: Bearer {RETELL_API_KEY}`.

## Mapping rules

### Multi-Prompt → Connexity

- `main_prompt = general_prompt`
- For each `state` in `states[]`:
  - `id = slugify(state.name)` (lowercase, alphanumeric + dashes; reject if collision).
  - `name = state.name`
  - `prompt = state.state_prompt`
  - `is_start = (state.name == starting_state)`
  - `transitions = [{to: slugify(edge.destination_state_name), when: edge.description} for edge in state.edges]`

### Conversation Flow → Connexity

- `main_prompt = global_prompt`
- For nodes of type `conversation` and `subagent`: map directly (use `node.id` as the `id`, `node.name` or `node.label` as `name`, the node's prompt field as `prompt`).
- For node types we cannot represent (`branch`, `function`, `code`, `extract_dynamic_variables`, `mcp`, `agent_swap`, etc.): **skip the node** and log a warning that surfaces to the user in the import result. If skipping a node leaves the graph disconnected, surface a hard error and abort the import.
- `is_start` matches `start_node_id`.
- Transitions: walk node edges, set `to = slugify(target_node_id)`, `when = edge.condition_description` (use whatever natural-language field Retell exposes; fall back to the empty string if none).

### Tools

- Tools are imported into `Agent.tools` (agent-scoped) using existing tool-import logic (look for `agent_tool_definitions.py`).
- `transition_tool_name` is left `None` (Retell's transition mechanism is internal and not surfaced as a tool call in their public API).

## Implementation steps

1. Add a service module: `backend/app/services/integrations/retell/import_agent.py`. Implement two functions:
   - `import_multi_prompt_agent(retell_llm_id: str, *, api_key: str, db: Session) -> Agent`
   - `import_conversation_flow_agent(flow_id: str, *, api_key: str, db: Session) -> Agent`
   Plus a top-level dispatcher `import_retell_agent(retell_agent_id: str, *, api_key: str, db: Session) -> ImportResult` that fetches the agent metadata, dispatches based on `response_engine.type`, and returns an `ImportResult` containing the new Agent + a list of warnings.

2. Add a FastAPI route: `POST /api/v1/integrations/retell/import-agent` accepting `{ retell_agent_id: str, integration_id: UUID }`. Returns the new agent ID + warnings.

3. Add tests at `backend/app/tests/services/integrations/retell/test_import_agent.py`:
   - Fixtures: a Multi-Prompt example payload and a Conversation Flow example payload (use `respx` or similar to mock the Retell API).
   - Cases: happy path for each agent type; dropped-node warning surfacing; disconnected-graph error; `is_start` correctness; transition `to` references resolve.

4. Frontend: in the agents list page, add an "Import" dropdown next to "New agent" with a "From Retell" option. The form takes a Retell Agent ID and (if multiple) the Retell integration. On submit, call the new endpoint, show warnings inline, navigate to the imported agent's edit page on success.

5. Update `docs/proposals/multi-prompt-agents.md` Section 6.3 to mark Retell as shipped, and add a row to the Integrations docs.

## Testing

Run before committing:
```bash
cd backend
uv run ruff check app
uv run ruff format --check app
uv run pyright
uv run pytest app/tests/services/integrations/retell -v
```

If you change the route or any schema, also run:
```bash
bash scripts/generate-client.sh
cd frontend && pnpm lint && pnpm turbo check-types
```

## Out of scope for this task

- Importing Retell tools that have no Connexity equivalent (just warn, don't fail).
- Round-tripping (Connexity → Retell export). One-way only for v1.
- Versioning sync (Retell's `is_published` versions are flattened to the latest version on import).
- Real-time sync (re-imports overwrite the existing Connexity agent only if explicitly re-triggered).

## Acceptance

- An import of a known-good Retell Multi-Prompt agent produces a Connexity agent whose `prompt_nodes` count, names, and transition edges exactly match the Retell source.
- An import of a Conversation Flow agent containing one unsupported node type produces a Connexity agent with that node skipped and a warning returned in the API response.
- The imported agent loads in the Multi-Prompt UI without validation errors and is usable as the target of test case generation.
- All quality checks (ruff, pyright, pytest, frontend lint + typecheck) pass.
````

The same prompt template (with provider-specific endpoint URLs and mapping rules) is the basis for the VAPI and ElevenLabs importers in subsequent phases.

---

## 7. Open Questions and Decisions to Lock

These are flagged for explicit reviewer sign-off before implementation begins:

1. **Start-node UX**: explicit `is_start` radio per node, *or* always-first-in-list with drag reordering? (Recommendation: explicit radio — clearer intent, survives reordering.)
2. **Schema version field**: should `prompt_nodes` carry a top-level `schema_version` for forward compatibility? (Recommendation: yes — `multi_prompt_v1`. Cheap insurance.)
3. **Read-only graph view in v1**: ship with the form, or follow-on? (Recommendation: follow-on. Form is sufficient.)
4. **Test case generator path coverage strategy**: enumerate all paths up to depth N, or sample? Cycles in the graph are possible (booking → revise → booking). (Recommendation: cap at depth 6 with cycle detection; document the limit.)
5. **Where attribution metadata is read from**: only from `response.metadata.connexity.transitions` / `.active_node_id`, or also accept top-level `response.metadata.active_node_id` for ergonomics? (Recommendation: namespaced only — avoids collisions with customers' existing metadata uses.)
6. **Versioning of the multi-prompt graph**: confirm v1 stance is "no versioning / no deployments" matching the original mockup. Worth re-confirming with product.
7. **Importer scope on day one**: Retell only, or Retell + VAPI Squads? (Recommendation: Retell only; ship VAPI in a follow-up so we can incorporate import-flow learnings.)

---

## 8. Sources

### Retell
- [Single/Multi Prompt overview](https://docs.retellai.com/build/single-multi-prompt/prompt-overview)
- [Conversation Flow overview](https://docs.retellai.com/build/conversation-flow/overview)
- [Get Retell LLM API](https://docs.retellai.com/api-references/get-retell-llm)
- [Custom LLM WebSocket](https://docs.retellai.com/api-references/llm-websocket)
- [Agent versioning](https://docs.retellai.com/agent/version)

### VAPI
- [Workflows overview](https://docs.vapi.ai/workflows/overview)
- [Workflows quickstart (deprecation note)](https://docs.vapi.ai/workflows/quickstart)
- [Squads](https://docs.vapi.ai/squads)
- [Handoff tool](https://docs.vapi.ai/squads/handoff)
- [Update Workflow API (BETA)](https://docs.vapi.ai/api-reference/workflow/workflow-controller-update)
- [Custom LLM](https://docs.vapi.ai/customization/custom-llm/using-your-server)

### ElevenLabs
- [Agent Workflows](https://elevenlabs.io/docs/agents-platform/customization/agent-workflows)
- [Agent transfer system tool](https://elevenlabs.io/docs/eleven-agents/customization/tools/system-tools/agent-transfer)
- [Create Agent API](https://elevenlabs.io/docs/api-reference/agents/create)
- [Custom LLM](https://elevenlabs.io/docs/agents-platform/customization/llm/custom-llm)
- [Agent versioning](https://elevenlabs.io/docs/eleven-agents/operate/versioning)

### Other
- [Bland Pathways tutorial](https://docs.bland.ai/tutorials/pathways)
- [Bland Get Pathway API](https://docs.bland.ai/api-v1/get/pathway)
- [Synthflow Flow Designer](https://docs.synthflow.ai/flow-designer)
- [Pipecat Flows docs](https://docs.pipecat.ai/guides/features/pipecat-flows)
- [OpenAI Agents SDK Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [agentevals (graph trajectory eval)](https://github.com/langchain-ai/agentevals)
