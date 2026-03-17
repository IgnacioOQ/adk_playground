# Markdown-JSON Hybrid Schema Conventions (Diátaxis Edition)
- status: active
- type: reference
- id: mddia_conventions
- label: [core, normative]
- last_checked: 2026-03-10
- injection: directive
- volatility: stable
<!-- content -->

This document defines the strict conventions for the **Markdown-JSON Hybrid Schema** used in this project for hierarchical task coordination, agentic planning, and context injection.

Every Markdown file following this schema can be **losslessly converted to JSON** and back. This enables:
- Clear, abstract protocol definitions
- Programmatic manipulation via JSON
- Human-readable documentation via Markdown
- Intelligent context assembly for LLM prompt injection

This edition integrates the **Diátaxis** technical documentation framework ([diataxis.fr](https://diataxis.fr/)) and an **injection role** axis designed for knowledge bases whose primary function is context injection into AI agent prompts.

## Core Principle
The system uses **Markdown headers** to define the structural hierarchy (the nodes) and **YAML-style metadata blocks** (immediately following the header) to define structured attributes. The entire tree can be serialized to JSON with a `content` field preserving the prose.

Every file self-describes along four orthogonal dimensions:

1. **Content function** (`type`) — *How to read* the document. Derived from Diátaxis for content files, or from workflow role for operational files.
2. **Domain and audience** (`label`) — *Who it's for* and *what area it covers*. Additive tags for filtering and routing. Governed by a central `label_registry.json`.
3. **Injection role** (`injection`) — *What role the document plays* when injected into an agent's context window. Guides the context assembly pipeline.
4. **Change velocity** (`volatility`) — *How quickly the document's content is expected to become stale*. Informs cache invalidation and re-verification priority.

## Filename Naming Convention
Every file in `content/` MUST follow the pattern `TOPIC_SUFFIX.md`, where `TOPIC` is `SCREAMING_SNAKE_CASE` and `SUFFIX` is derived directly from the file's `type` field:

| `type` | Required suffix | Example |
|:---|:---|:---|
| `tutorial` | `_TUTORIAL` | `ADK_AGENT_TUTORIAL.md` |
| `how-to` | `_SKILL` | `GCLOUD_SKILL.md` |
| `reference` | `_REF` | `MCP_REF.md` |
| `explanation` | `_EXPLANATION` | `ENGINE_EXPLANATION.md` |
| `plan` | `_PLAN` | `MASTER_PLAN.md` |
| `log` | `_LOG` | `AGENTS_LOG.md` |
| `task` | `_TASK` | `DEPLOY_TASK.md` |

**Rules:**
- The suffix encodes the `type` unambiguously. A reader can determine a file's Diátaxis category from the filename alone, without opening it.
- When two files share the same topic under the same type, disambiguate by appending a qualifier before the suffix: `MCP_REF.md` (protocol overview) vs. `MCP_TOOLS_REF.md` (data tools spec).
- Root-level operational files (`AGENTS.md`, `MD_CONVENTIONS.md`, `README.md`, `HOUSEKEEPING.md`) are exempt from this convention — they follow project-standard names.
- The folder a file lives in (`tutorials/`, `how-to/`, `reference/`, `explanations/`, `plans/`, `logs/`) MUST match its `type`. File and folder together are redundant by design — this catches misplaced files immediately.

## Schema Rules
### 1. Hierarchy & Nodes
- **Headers**: Use standard Markdown headers (`#`, `##`, `###`) to define the hierarchy.
- **Nesting**:
    - `#` is the Root/Document Title (usually only one per file).
    - `##` are Top-Level Tasks/Features.
    - `###` are Subtasks.
    - And so on.
- **Implicit Dependency**: A header is implicitly dependent on its parent header.
- **Explicit Dependency (DAG)**:
    - Use the `blocked_by` metadata field to define dependencies on other nodes (siblings, cousins, etc.).
    - Pass a list of IDs or relative paths to allow a single node to depend on multiple prior nodes.
    - **Example**: `blocked_by: [task-a, task-b]` implies this node cannot start until both 'task-a' and 'task-b' are done.

### 2. Metadata Blocks
- **Location**: Metadata MUST be placed **immediately** after the header.
- **Separator**: There MUST be a `<!-- content -->` line between the metadata block and the content. This HTML comment acts as an unambiguous separator that is invisible when rendered but easy for parsers to detect.
- **Format**: A strict list of key-value pairs as a bulleted list.

**Example:**

```markdown
## Implement User Auth
- status: in-progress
- type: how-to
- id: project.user_auth
- label: [backend]
- injection: procedural
- volatility: evolving
- owner: dev-1
- estimate: 3d
- blocked_by: []
<!-- content -->
This section describes the implementation details...
```

#### Metadata Placement Policy
Where metadata blocks appear depends on the document's `type`. The goal is to minimize token overhead for context injection while preserving the per-node tracking that operational documents need.

**Content documents** (`tutorial`, `how-to`, `reference`, `explanation`):

- Metadata is placed **only on the root `#` header**. Subsections (`##`, `###`, etc.) use standard Markdown headers without metadata blocks.
- Rationale: content documents are the atomic unit for context injection. The pipeline cares about the document-level classification (`type`, `injection`, `volatility`, `label`), not about individual subsections. Eliminating per-subsection metadata reduces token overhead — often by hundreds of tokens — which matters directly for the agent attention budget (see the Document Sizing section). When the agent receives a content document, it sees one metadata block at the top and then clean prose from that point onward.
- Subsections remain structurally meaningful — the parser still builds a node tree from headers — but subsection nodes inherit the root's metadata and carry no independent metadata fields.

**Operational documents** (`plan`, `task`, `log`):

- Metadata is placed **on every node** that requires independent tracking. Each subtask within a plan genuinely needs its own `status`, `owner`, `estimate`, and `blocked_by` fields.
- Rationale: operational documents are hierarchical task trees where each node is an independent work unit. The value of per-node metadata outweighs the token cost because these documents are typically queried for specific node status rather than injected as full-text context.

**Why the distinction matters for agents:**

When a content document is injected into an agent's context window, every metadata block that is not at the root is wasted attention. The agent sees `- status: active` and `- type: reference` repeated dozens of times but gains no actionable signal from any of them — the root metadata already told it everything it needs to know about how to consume the file. Removing this repetition frees tokens for actual content and keeps the agent's attention on the material that matters.

For operational documents the calculus reverses: an agent querying "what tasks are blocked?" needs per-node `status` and `blocked_by` fields to answer the question. Here the metadata IS the content.

**Migration note:** Existing content documents with per-subsection metadata should be migrated by stripping metadata from all headers except `#`. The parser maintains backward compatibility — files with per-subsection metadata will still parse — but all new content documents and all files undergoing revision should follow the top-level-only policy.

### 3. Allowed Fields
The following fields are standard. The schema allows extensibility, but extended fields must follow the conventions at the end of this section.

| Field | Type | Description |
|:---|:---|:---|
| `status` | `enum` | `todo`, `in-progress`, `done`, `blocked`, `recurring`, `active` **(Mandatory)** |
| `type` | `enum` | `tutorial`, `how-to`, `reference`, `explanation`, `plan`, `task`, `log` **(Mandatory)** |
| `id` | `string` | Unique identifier for the node (e.g., `project.component.task`). Used for robust merging and dependency tracking. **(Optional but strongly recommended)** |
| `label` | `list` | Array of strings for filtering and routing (e.g., `[core, normative, backend]`). Values MUST be drawn from `label_registry.json` unless explicitly extending it. **(Optional)** |
| `injection` | `enum` | `directive`, `informational`, `procedural`, `background`, `excluded`. Describes the document's role when injected as agent context. **(Optional)** |
| `volatility` | `enum` | `stable`, `evolving`, `ephemeral`. How quickly the document's content is expected to become stale. **(Optional)** |
| `owner` | `string` | The agent or user assigned to this (e.g., `dev-1`, `claude`). **(Optional)** |
| `estimate` | `string` | Time estimate (e.g., `1d`, `4h`). **(Optional)** |
| `blocked_by` | `list` | List of explicit dependencies (IDs or relative paths). **(Optional)** |
| `priority` | `enum` | `draft`, `low`, `medium`, `high`, `critical`. **(Optional)** |
| `last_checked` | `string` | Date of the last modification (ISO-8601). **(Optional)** |

For extended fields:
- The key is entirely lowercase.
- The key has no spaces (words separated with dash or underscore).
- The value is single line.

### Type Definitions (Diátaxis + Operational)
The `type` field classifies every node by its content function. Seven values are organized into two groups.

#### Diátaxis Content Types (How to Read)
These four types tell the reader (human or agent) *what kind of document this is* and *how to consume it*. They derive from the Diátaxis framework ([diataxis.fr/start-here](https://diataxis.fr/start-here/)).

| Type | Function | Writing Style | Reader Posture |
|:---|:---|:---|:---|
| `tutorial` | **(Learning)** A step-by-step guided experience. Takes the reader through a process from start to finish with guaranteed outcomes. | Imperative, hand-holding, ordered steps. Minimal theory. | "Teach me." |
| `how-to` | **(Problem-solving)** Goal-oriented instructions for solving a specific problem. Assumes the reader already has baseline competence. | Direct, focused on the goal, may list prerequisites. | "Help me do X." |
| `reference` | **(Lookup)** Factual, structured technical information designed for non-linear access. API specs, schema definitions, field tables, conventions. | Precise, consistent structure, no narrative. | "What is X exactly?" |
| `explanation` | **(Understanding)** Conceptual discussion that builds mental models. Answers "why" questions, provides context, explores alternatives. | Discursive, may include diagrams, analogies, history. | "Help me understand." |

**Choosing the correct Diátaxis type — decision test:**

```
1. Does the reader consume this LINEARLY to build understanding?
   (analogies, "why", conceptual depth)
   → type: explanation

2. Does the reader LOOK UP specific facts, rules, or definitions
   while working? (tables, specs, constraints)
   → type: reference

3. Does the reader FOLLOW this to solve a specific problem or
   complete a goal? (steps, procedures, workflows)
   → type: how-to

4. Does the reader follow this as a GUIDED LEARNING experience
   from scratch? (hands-on, guaranteed outcomes)
   → type: tutorial
```

**Counterexamples — "This looks like X but is actually Y":**

The decision test works well for clear-cut cases. The hard cases are documents that superficially match one type but actually belong to another. These counterexamples target the most common misclassifications:

1. **A changelog looks like `explanation` but is actually `log`.** A changelog is consumed linearly and builds understanding of what changed — which pattern-matches to `explanation`. But a changelog does not build a *conceptual model*. It records *historical facts* in chronological order. The reader posture is "what happened?" not "help me understand why." It is `log` (operational), not `explanation` (Diátaxis). The test: if you removed the chronological ordering, would the document lose its purpose? If yes, it is a log.

2. **A configuration spec with sequential steps looks like `how-to` but is actually `reference`.** A configuration spec often reads "set X to Y, then set Z to W" — which pattern-matches to step-by-step instructions. But the reader's posture is "what is the correct value for this setting?" not "help me achieve a goal." The steps are an artifact of the spec's structure, not a problem-solving workflow. If the reader would open this document, jump to one setting, read its value, and close the document, it is `reference`. If they would follow the entire document from top to bottom to achieve a particular outcome, it is `how-to`.

3. **An architecture decision record (ADR) looks like `reference` but is actually `explanation`.** An ADR contains structured, factual information (decision, status, context, consequences) — which pattern-matches to `reference`. But the document's core purpose is to answer *why* a decision was made. The reader consumes it linearly to build understanding of the tradeoffs and reasoning. An ADR is `explanation` with a structured format, not `reference` with narrative prose. The test: is the reader looking up a fact, or understanding a rationale?

4. **A troubleshooting FAQ looks like `reference` but is actually `how-to`.** A FAQ is structured for lookup (question → answer), which pattern-matches to `reference`. But each entry is a mini-procedure: "if you see error X, do Y." The reader's posture is "help me solve this problem," not "what is X exactly?" A troubleshooting FAQ is a collection of `how-to` entries. If it grows large enough, consider splitting into individual how-to documents grouped by topic.

**Key insight from Diátaxis: mixing these modes in a single document degrades all of them.** A tutorial that stops to explain theory loses momentum. A reference page that tries to teach loses precision. When a document mixes modes, assign the `type` of the **dominant** mode — the one that best describes how the reader will engage with it on first open. If the modes are roughly equal and the file is large, consider splitting.

#### Operational Workflow Types (What it Does in the Project)
These three types exist outside the Diátaxis model. They serve a **project management** function, not a documentation function:

| Type | Function |
|:---|:---|
| `plan` | **(Finite)** A high-level objective with a clear beginning and end. Usually the root node of a project tree. |
| `task` | **(Finite)** A specific, actionable unit of work. Usually a sub-node of a plan. |
| `log` | **(Historical)** Append-only records of actions, decisions, or outputs. Not prescriptive. |

#### Removed Types (Migration Reference)
The following types from the previous schema are no longer valid:

| Old Type | Migrate To | Guidance |
|:---|:---|:---|
| `agent_skill` | `tutorial`, `how-to`, `reference`, or `explanation` | Classify by actual content function. Add `label: [agent, skill]` to preserve the audience signal. |
| `guideline` | `reference`, `how-to`, or `explanation` | Apply the decision test above. Many "guidelines" are actually `explanation` (conceptual explainers), not `reference` (normative rules). |
| `documentation` | `reference` or `explanation` | Is it for lookup or for understanding? |

### Injection Role Definitions
The `injection` field describes the document's **operational role when injected into an agent's context window**. This is the dimension that distinguishes a knowledge base built for context injection from standard documentation.

```
injection: directive | informational | procedural | background | excluded
```

| Value | Meaning | Agent Behavior When Injected |
|:---|:---|:---|
| `directive` | Contains rules, constraints, or conventions the agent MUST follow. | Agent treats content as behavioral constraints. Compliance is mandatory. |
| `informational` | Provides factual knowledge the agent may use for reasoning. | Agent uses content as working knowledge. Reference is optional. |
| `procedural` | Contains step-by-step processes the agent should execute. | Agent follows content as an action script. Sequence matters. |
| `background` | Provides conceptual depth for improved reasoning quality. | Agent absorbs content into its working model. No direct action required. |
| `excluded` | Deliberately excluded from the context injection pipeline. | The pipeline MUST NOT inject this document. It exists for human readers or archival purposes only. |

**The distinction between absent and `excluded`:**

- **Field absent**: The file has not yet been classified for injection. The pipeline should treat it as unprocessed — a candidate for future labeling, flagged during audits.
- **`injection: excluded`**: The file has been reviewed and deliberately marked as not suitable for injection. The pipeline should never inject it and should not flag it during audits. Examples: meeting notes intended only for human readers, deprecated documents kept for archival reference, or draft documents not yet ready for agent consumption.

This distinction matters for automated quality checks. A script that audits for "files missing injection labels" should flag absent fields but skip `excluded` ones.

**Typical correlations with Diátaxis types** (these are defaults, not rules — override when the content warrants it):

| Diátaxis Type | Typical Injection Role | Why |
|:---|:---|:---|
| `tutorial` | `procedural` | Tutorials are step-by-step scripts. |
| `how-to` | `procedural` or `directive` | How-tos guide action; some contain mandatory rules. |
| `reference` | `directive` or `informational` | Normative references constrain; descriptive references inform. |
| `explanation` | `background` | Explanations build the agent's conceptual model. |
| `plan` / `task` | `informational` | Operational context about project state. |
| `log` | `informational` | Historical records informing current decisions. |

#### Atypical Combination Warnings
The parser (and any validation tooling) SHOULD emit a **soft warning** — not a rejection — when a document's `type` × `injection` combination deviates from the typical correlations listed above. The purpose is to catch misclassifications early without being overly rigid.

**Combinations that trigger a warning:**

| Combination | Warning Message | Common Reason It Might Be Intentional |
|:---|:---|:---|
| `tutorial` + `directive` | "Tutorials are typically `procedural`. Is this file constraining agent behavior or teaching through guided steps?" | A tutorial that also establishes mandatory patterns (e.g., "Tutorial: How We Write Tests" where the patterns are normative). |
| `explanation` + `directive` | "Explanations are typically `background`. Does this file contain rules the agent must follow, or concepts it should absorb?" | A conceptual document that also establishes architectural constraints (e.g., "Why We Use Event Sourcing" where the pattern is mandatory). |
| `explanation` + `procedural` | "Explanations are typically `background`. Does this file contain step-by-step procedures, or does it build conceptual understanding?" | Rare. Usually indicates the file should be reclassified as `how-to`. |
| `reference` + `background` | "Reference docs are typically `directive` or `informational`. Does this file build conceptual models, or provide facts for lookup?" | A reference table that also serves as a conceptual map (e.g., a taxonomy that helps the agent reason about categories). |
| `log` + `directive` | "Logs are typically `informational`. Does this log contain rules, or historical records?" | Very rare. Almost always a misclassification. |

**Implementation guidance:**

- The warning should include the document's file path and current `type` + `injection` values.
- The warning should be non-blocking: the file parses successfully, but the user is prompted to confirm the combination is intentional.
- A `# atypical-confirmed` comment in the metadata block (or an `atypical_confirmed: true` extended field) suppresses the warning permanently for that file.

**Context assembly implications:**

1. **Priority ordering**: `directive` documents are injected first (closest to system prompt). `background` next (conceptual frame). `informational` and `procedural` follow as needed. `excluded` documents are never injected.
2. **Context window budgeting**: `directive` documents are never dropped when the window is tight. `background` can be summarized. `informational` can be selectively included by relevance. `excluded` documents are skipped entirely.
3. **Agent self-awareness**: An agent seeing `injection: directive` knows "I must comply." An agent seeing `injection: background` knows "this shapes my understanding but doesn't prescribe specific actions." The metadata block at the top of the document provides this signal directly to the agent at runtime — this is why content documents retain their root metadata block even though subsection metadata is stripped (see Metadata Placement Policy).

The field is optional. Pure project management files (`plan`, `task`) or human-only docs may not need it. But for any file that enters the context injection pipeline, it provides a critical operational signal.

### Volatility Definitions
The `volatility` field describes **how quickly a document's content is expected to become stale**. It informs cache invalidation, re-verification priority, and trust decisions in the context assembly pipeline.

```
volatility: stable | evolving | ephemeral
```

| Value | Meaning | Expected Freshness Window | Pipeline Behavior |
|:---|:---|:---|:---|
| `stable` | Content changes rarely. Core conventions, foundational explanations, settled architecture decisions. | Months to years. | Cache aggressively. Low re-verification priority. Trust injected content without re-fetching. |
| `evolving` | Content is updated periodically as the project develops. Feature docs, deployment guides, configuration references. | Weeks to months. | Cache with moderate TTL. Medium re-verification priority. Prefer fresh fetch when possible but tolerate cached versions. |
| `ephemeral` | Content changes rapidly or is expected to become outdated within days. Active plans, sprint tasks, logs, meeting notes. | Days to weeks. | Minimize caching. High re-verification priority. Stale `directive` documents are worse than missing documents — injecting an outdated rule set can cause the agent to produce confidently wrong output. |

**Why this matters for context injection:**

The `last_checked` field captures when a document was last reviewed, but it does not express *intent about freshness*. A document last checked yesterday with `volatility: stable` is fine to inject next month. A document last checked yesterday with `volatility: ephemeral` may already be outdated today.

The combination of `last_checked` + `volatility` gives the pipeline enough information to make smart decisions: if `last_checked` is more than one freshness window old for the document's volatility level, the pipeline should either re-verify the document or inject it with a staleness warning.

**Typical correlations with types:**

| Type | Typical Volatility | Why |
|:---|:---|:---|
| `reference` (normative) | `stable` | Conventions and rules change infrequently by design. |
| `explanation` | `stable` | Conceptual models are long-lived. |
| `how-to` | `evolving` | Procedures change as tools and infrastructure evolve. |
| `tutorial` | `evolving` | Tutorials track product changes. |
| `plan` | `ephemeral` | Plans are consumed and completed. |
| `task` | `ephemeral` | Tasks move through statuses quickly. |
| `log` | `ephemeral` | Individual entries are time-stamped; the log as a whole grows but old entries become less relevant. |

The field is optional. If absent, the pipeline should default to `evolving` as a safe middle ground.

### Standard Labels and Label Governance
Labels are lists of strings, allowing multiple keywords for a single node. All label values MUST be drawn from the central `label_registry.json` file unless explicitly extending it through the registration process described below.

**Audience & Role:**

| Label | Purpose |
|:---|:---|
| `agent` | Content primarily consumed by AI agents (prompt context, skill definitions). |
| `human` | Content primarily for human readers (onboarding docs, strategy notes). |
| `skill` | Defines a capability, persona, or specialized toolset for an agent. |
| `normative` | Contains rules, constraints, or conventions that MUST be followed. |

**Domain:**

| Label | Purpose |
|:---|:---|
| `infrastructure` | Deployment, CI/CD, cloud resources. |
| `frontend` | Client-side application, UI, UX. |
| `backend` | Server-side logic, data processing, MCP servers. |

**Status & Structure:**

| Label | Purpose |
|:---|:---|
| `core` | Essential foundational document for the repository. |
| `template` | General content that needs specialization for particular projects. |
| `draft` | Incomplete, under construction, or lacking clarity. |
| `planning` | Project plans, roadmaps, objective outlines. |
| `source-material` | Textbooks, external manuals, or deep-dive materials brought in for context injection. |

#### The Label Registry (`label_registry.json`)
All valid labels are enumerated in a central `label_registry.json` file at the repository root. This prevents label sprawl — the gradual accumulation of synonymous or overlapping labels (e.g., `api`, `api-server`, `backend-api`) that degrades the filtering and routing system.

**Registry format:**

```json
{
  "version": "1.0",
  "last_updated": "2026-03-10",
  "categories": {
    "audience_role": {
      "description": "Who the document is for and what role it serves.",
      "labels": {
        "agent": "Content primarily consumed by AI agents.",
        "human": "Content primarily for human readers.",
        "skill": "Defines a capability, persona, or specialized toolset for an agent.",
        "normative": "Contains rules, constraints, or conventions that MUST be followed."
      }
    },
    "domain": {
      "description": "What technical area the document covers.",
      "labels": {
        "infrastructure": "Deployment, CI/CD, cloud resources.",
        "frontend": "Client-side application, UI, UX.",
        "backend": "Server-side logic, data processing, MCP servers."
      }
    },
    "status_structure": {
      "description": "Document maturity and structural role.",
      "labels": {
        "core": "Essential foundational document for the repository.",
        "template": "General content that needs specialization.",
        "draft": "Incomplete, under construction, or lacking clarity.",
        "planning": "Project plans, roadmaps, objective outlines.",
        "source-material": "External materials brought in for context injection."
      }
    }
  }
}
```

**Validation rule:**

The parser MUST validate all values in the `label` field against `label_registry.json`. If a label is not found in the registry, the parser MUST emit an error:

```
ERROR: Unknown label 'api-server' in file 'DEPLOY_HOW_TO.md'.
       Valid labels: agent, human, skill, normative, infrastructure,
       frontend, backend, core, template, draft, planning, source-material.
       To add a new label, register it in label_registry.json first.
```

**Adding a new label:**

1. Add the label to the appropriate category in `label_registry.json` with a one-line description.
2. If no existing category fits, create a new category with a `description` field.
3. Commit the registry update BEFORE committing files that use the new label. This ensures the parser never encounters an unregistered label in CI.

**Why a registry instead of free-form tags:**

Free-form tagging systems degrade predictably: within months, the tag space contains synonyms (`api` / `api-server` / `backend-api`), typos (`infrastucture`), and abandoned one-off labels that match nothing. A small upfront cost (adding a line to a JSON file) prevents a large ongoing cost (auditing and deduplicating a sprawling tag space).

### 4. Dependencies
Dependencies are managed centrally in `dependency_registry.json`.

**Do not add `context_dependencies` metadata to files.**

To add a dependency:
1. Use `python manager/dependency_manager.py add <file> <dependency>` (if available).
2. Or manually edit `dependency_registry.json`.

**Resolution Protocol**:
1. **Registry First**: Tools and agents look up the current file in the registry to find its dependencies.
2. **Recursive Resolution**: Dependencies are resolved recursively to build the full context.

### 5. Context & Description
- Any text following the metadata block (after the `<!-- content -->` separator) is considered "Context" or "Description".
- It can contain free-form Markdown, code blocks, images, etc.

## Examples
### Valid Node (Reference with Directive Injection)
```markdown
## Coding Standards
- status: active
- type: reference
- id: project.coding_standards
- label: [core, normative, backend]
- injection: directive
- volatility: stable
- last_checked: 2026-03-10
<!-- content -->
All Python code must use type hints. Docstrings follow Google style.
Functions over 30 lines must be refactored.
```

### Valid Node (Explanation with Background Injection)
```markdown
## Why We Use the Engine Pattern
- status: active
- type: explanation
- id: architecture.engine_pattern
- label: [backend, agent]
- injection: background
- volatility: stable
<!-- content -->
The engine pattern provides continuous availability, mediation between
subsystems, and pluggable internals. This section explains why the MCP
Client Engine follows this pattern and how it compares to database and
workflow engines.
```

### Valid Node (How-to with Procedural Injection)
```markdown
## Deploy to Cloud Run
- status: active
- type: how-to
- id: ops.deploy_cloud_run
- label: [infrastructure]
- injection: procedural
- volatility: evolving
- owner: dev-1
- estimate: 30m
<!-- content -->
Prerequisites: Docker installed, `gcloud` CLI authenticated.

1. Build the image: `docker build -t app .`
2. Push to Artifact Registry: `docker push us-central1-docker.pkg.dev/...`
3. Deploy: `gcloud run deploy ...`
```

### Valid Node (Excluded from Injection)
```markdown
## Weekly Team Meeting Notes
- status: active
- type: log
- id: team.meeting_notes
- label: [human]
- injection: excluded
- volatility: ephemeral
<!-- content -->
### 2026-03-07
Discussed Q2 roadmap priorities. Agreed to defer the monitoring
dashboard to Q3. Action items assigned via task tracker.
```

Note: `injection: excluded` signals that this file has been reviewed and deliberately excluded from the context injection pipeline. It will not be flagged during audits for missing injection labels.

### Valid Node (Task, Operational — Per-Node Metadata)
```markdown
# User Authentication System
- status: in-progress
- type: plan
- id: project.user_auth
- label: [backend, planning]
- injection: informational
- volatility: ephemeral
<!-- content -->
Implement full authentication stack with OAuth2 support.

## Database Schema
- status: done
- type: task
- id: project.user_auth.db_schema
- owner: dev-2
- estimate: 1d
<!-- content -->
Set up PostgreSQL schema for users and sessions.

## API Endpoints
- status: in-progress
- type: task
- id: project.user_auth.api_endpoints
- owner: dev-1
- estimate: 3d
- blocked_by: [project.user_auth.db_schema]
<!-- content -->
Implement login, logout, and token refresh endpoints.
```

Note: Operational documents (`plan`, `task`, `log`) retain per-node metadata because each node is an independent work unit with its own status, owner, and dependencies.

### Invalid Node (Metadata not immediate)
```markdown
### Database Schema
- status: active
<!-- content -->
Some text here first.

- status: done
```

*Error: Metadata block must immediately follow the header.*

### Invalid Node (Missing separator)
```markdown
## Title
- status: active
- type: reference
Content starts here...
```

*Error: Missing `<!-- content -->` separator between metadata and content.*

### Invalid Node (Old type values)
```markdown
## Some Document
- status: active
- type: guideline
<!-- content -->
```

*Error: `guideline` is not a valid type. Use `reference`, `how-to`, or `explanation` depending on content function. See "Type Definitions" and the decision test.*

```markdown
## Some Skill
- status: active
- type: agent_skill
<!-- content -->
```

*Error: `agent_skill` is not a valid type. Use `tutorial`, `how-to`, `reference`, or `explanation`. Add `label: [agent, skill]` to preserve the audience signal.*

### Invalid Node (Unregistered label)
```markdown
## API Gateway Config
- status: active
- type: reference
- label: [api-server, backend]
<!-- content -->
```

*Error: Unknown label `api-server`. Valid labels are defined in `label_registry.json`. Did you mean `backend`? To add a new label, register it in the registry first.*

## Parsing Logic (for Developers)
1. **Scan for Headers**.
2. **Look ahead** at the lines immediately following the header.
3. **Parse lines** that match the METADATA key-value pattern (`- key: value`) until the `<!-- content -->` separator or a non-matching line is found.
4. **Everything else** until the next header of equal or higher level is "Content".

> [!NOTE]
> The parser maintains backward compatibility with files using a blank line as separator, but all new files and migrations should use `<!-- content -->`.

**Validation rules for `type`:**
- The parser MUST reject the old values `agent_skill`, `guideline`, and `documentation` with a clear error message pointing to the migration guidance in this document.
- Valid values: `tutorial`, `how-to`, `reference`, `explanation`, `plan`, `task`, `log`.

**Validation rules for `injection`:**
- The field is optional. If present, the parser should validate against: `directive`, `informational`, `procedural`, `background`, `excluded`.
- If absent, no error — the field is only required for files entering the context injection pipeline.

**Validation rules for `volatility`:**
- The field is optional. If present, the parser should validate against: `stable`, `evolving`, `ephemeral`.
- If absent, the pipeline defaults to `evolving` as a safe middle ground.

**Validation rules for `label`:**
- The field is optional. If present, every value in the list MUST exist in `label_registry.json`.
- If a value is not found, the parser MUST emit an error with the unrecognized label, the list of valid labels, and a prompt to register the new label in the registry.

**Atypical combination warnings:**
- After parsing `type` and `injection`, the parser SHOULD check the combination against the typical correlations table (see "Atypical Combination Warnings" section).
- If the combination is atypical, emit a non-blocking warning unless the file contains `atypical_confirmed: true` in its metadata block.

**Metadata placement enforcement (content documents):**
- For files with a Diátaxis content `type` (`tutorial`, `how-to`, `reference`, `explanation`), the parser SHOULD emit a warning if metadata blocks are found on non-root headers.
- This is a soft warning, not a hard error, to maintain backward compatibility during migration.

## Tooling Reference
The following Python scripts are available in `language/` to interact with this schema:

### 1. `language/md_parser.py`
- **Purpose**: The core parser enabling **bidirectional MD ↔ JSON** transformation.
- **Key Classes**:
    - `MarkdownParser`: Parses `.md` files into a `Node` tree
    - `Node`: Tree node with `to_dict()`, `from_dict()`, and `to_markdown()` methods
- **Transformations**:
    - **MD → JSON**: `parser.parse_file("file.md")` → `root.to_dict()` → `json.dumps()`
    - **JSON → MD**: `json.loads()` → `Node.from_dict(data)` → `root.to_markdown()`
- **CLI Usage**: `python3 language/md_parser.py <file.md>`
- **Output**: JSON representation of the tree or validation errors.
- **Required updates**:
    - The type enum validation must accept the seven valid values and reject the three removed values.
    - The `injection` field must be recognized as a valid optional metadata key with five values: `directive`, `informational`, `procedural`, `background`, `excluded`.
    - The `volatility` field must be recognized as a valid optional metadata key with three values: `stable`, `evolving`, `ephemeral`.
    - Label validation must check values against `label_registry.json`.
    - Atypical `type` × `injection` combinations must trigger a soft warning.
    - For content-type documents, metadata on non-root headers must trigger a soft warning.

### 2. `language/visualization.py`
- **Purpose**: Visualizes the task tree in the terminal with metadata.
- **Usage**: `python3 language/visualization.py <file.md>`
- **Output**: Unicode tree visualization.

### 3. `language/operations.py`
- **Purpose**: Manipulate task trees (merge, extend).
- **Usage**:
    - **Merge**: `python3 language/operations.py merge <target.md> <source.md> "<Target Node Title>" [--output <out.md>]`
        - Inserts the source tree as children of the specified target node.
    - **Extend**: `python3 language/operations.py extend <target.md> <source.md> [--output <out.md>]`
        - Appends the source tree's top-level items to the target tree's top level.

### 4. `language/migrate.py`
- **Purpose**: Heuristically adds default metadata to standard Markdown headers to make them schema-compliant.
- **Usage**: `python3 language/migrate.py <file.md> [file2.md ...]`
- **Effect**: Modifies files in-place by injecting `- status: active` after headers that lack metadata.
- **Required update**: Should inject `- type: explanation` as a safe default (explanation is the most general content type). The old default of `documentation` is no longer valid.

### 5. `language/importer.py`
- **Purpose**: Converts legacy documents (`.docx`, `.pdf`, `.doc`) into Markdown and auto-applies the Protocol.
- **Usage**: `python3 language/importer.py <file.docx> [file.pdf ...]`
- **Capabilities**:
    - **DOCX**: Preserves headers (Heading 1-3) if `python-docx` is installed. Fallbacks to text extraction.
    - **PDF**: Extracts text if `pypdf` or `pdftotext` is available.
    - **DOC**: Uses MacOS `textutil` for text extraction.

## Migration Guidelines
### Migrating from MD_CONVENTIONS.md (Pre-Diátaxis)
If your repository was using the previous `MD_CONVENTIONS.md` schema, follow these steps:

#### Step 1: Update the Parser
Update `md_parser.py` to:
- Accept the new `type` enum: `tutorial | how-to | reference | explanation | plan | task | log`.
- Reject the old values (`agent_skill`, `guideline`, `documentation`) with actionable error messages.
- Recognize `injection` as a valid optional metadata field with values: `directive | informational | procedural | background | excluded`.
- Recognize `volatility` as a valid optional metadata field with values: `stable | evolving | ephemeral`.
- Load `label_registry.json` and validate all `label` values against it.
- Recognize `source-material` as a valid label (replacing the old `reference` label).
- Implement atypical `type` × `injection` combination warnings.

#### Step 2: Create the Label Registry
Create `label_registry.json` at the repository root using the format defined in the "Label Registry" section. Populate it with all standard labels. This must be committed before any files are validated against it.

#### Step 3: Reclassify Existing Files
For each file using an old `type` value, apply the decision test:

```
┌─────────────────────────────────────────────────────────────────┐
│  MIGRATION DECISION TEST                                        │
│                                                                 │
│  1. Does the reader consume this LINEARLY to build             │
│     understanding? (analogies, "why", conceptual depth)         │
│     → type: explanation                                         │
│                                                                 │
│  2. Does the reader LOOK UP specific facts, rules, or          │
│     definitions while working? (tables, specs, constraints)     │
│     → type: reference                                           │
│                                                                 │
│  3. Does the reader FOLLOW this to solve a specific problem    │
│     or complete a goal? (steps, procedures, workflows)          │
│     → type: how-to                                              │
│                                                                 │
│  4. Does the reader follow this as a GUIDED LEARNING           │
│     experience from scratch? (hands-on, guaranteed outcomes)    │
│     → type: tutorial                                            │
└─────────────────────────────────────────────────────────────────┘
```

**Critical warning:** The old `guideline` type was used for three genuinely different content categories. Do NOT default all guidelines to `reference`. Many files titled "guideline" are actually conceptual explainers (`explanation`). The test: if the document builds understanding through analogies, comparisons, and discursive prose — and the reader would never open it to "look up" a specific fact — it is `explanation`, not `reference`.

**Watch for the counterexample patterns** described in the "Type Definitions" section: changelogs that look like explanations, config specs that look like how-tos, ADRs that look like references, and troubleshooting FAQs that look like references. Apply the reader posture test, not the surface format test.

#### Step 4: Add Injection Roles and Volatility
For each file that enters the context injection pipeline, add the `injection` field. Ask:

- Does this file contain rules the agent must obey? → `directive`
- Does this file provide facts the agent may reference? → `informational`
- Does this file contain steps the agent should execute? → `procedural`
- Does this file build a mental model the agent should absorb? → `background`
- Should this file never be injected? → `excluded`

For each file, add the `volatility` field. Ask:

- Does this file change rarely (conventions, foundational concepts)? → `stable`
- Does this file change periodically (feature docs, guides)? → `evolving`
- Does this file change rapidly or expire quickly (plans, tasks, notes)? → `ephemeral`

#### Step 5: Strip Subsection Metadata from Content Documents
For files with a Diátaxis content type (`tutorial`, `how-to`, `reference`, `explanation`), remove metadata blocks from all headers except the root `#` header. Keep the `<!-- content -->` separator on the root and remove it from subsections, letting subsections be plain Markdown headers.

This step is not strictly required — the parser maintains backward compatibility — but it is strongly recommended to reduce token overhead for context injection.

#### Step 6: Rename Labels
Replace any `label: [... reference ...]` with `label: [... source-material ...]`. This avoids confusion with `type: reference`.

#### Step 7: Validate
Run the updated parser on all files:
```bash
for f in $(find content/ -name "*.md"); do
    python3 language/md_parser.py "$f"
done
```

Fix any validation errors before merging. Review any atypical combination warnings and either reclassify or add `atypical_confirmed: true` where the combination is intentional.

### Migrating Existing Standard Documentation
When migrating existing documentation to this schema for the first time:
1. **Run the Migration Script**: Use `language/migrate.py` to add baseline metadata.
2. **Review and Refine**: Apply the decision test to assign correct `type` values. Update `status` fields where appropriate. Add `injection` roles for files entering the context pipeline. Add `volatility` signals.
3. **Structure Check**: Ensure the hierarchy makes sense as a task/node tree.

## Best Practices for AI Generation
When generating or modifying files in this repository, AI agents MUST adhere to the following best practices to ensure system stability and parsing accuracy:

1. **Always Generate IDs**: When creating new nodes, always generate a unique `id` in the metadata (e.g., `id: component.subcomponent.task`). This ensures that references remain stable even if titles change.

2. **Update Timestamps**: When modifying a node, update the `last_checked` field to the current date (ISO-8601).

3. **Strict Spacing**: You **MUST** add a `<!-- content -->` separator line between the metadata block and the content. This is critical for the parser to distinguish between metadata and content lists.
    - *Correct*:
        ```markdown
        ## Title
        - status: active
        - type: reference
        <!-- content -->
        Content starts here...
        ```
    - *Incorrect*:
        ```markdown
        ## Title
        - status: active
        - type: reference
        Content starts here...
        ```

4. **Use Valid Types Only**: Only use the seven valid `type` values: `tutorial`, `how-to`, `reference`, `explanation`, `plan`, `task`, `log`. Never use the removed values (`agent_skill`, `guideline`, `documentation`).

5. **Assign Injection Roles**: When creating files that will be injected into agent context, always include the `injection` field. Choose the value that best describes the operational role:
    - `directive` → Rules the agent must obey.
    - `informational` → Facts the agent may use.
    - `procedural` → Steps the agent should execute.
    - `background` → Concepts the agent should absorb.
    - `excluded` → Deliberately excluded from injection.

6. **Assign Volatility**: Always include the `volatility` field. When in doubt, default to `evolving`.

7. **Choose Types via the Decision Test**: Before assigning a `type`, apply the decision test from the Type Definitions section. Do not guess. The most common mistake is labeling a conceptual explainer as `reference` — if the reader consumes the document linearly to build understanding, it is `explanation`. Review the counterexamples section if the classification feels ambiguous.

8. **Use Registered Labels Only**: Only use label values that exist in `label_registry.json`. If a new label is needed, register it in the registry first.

9. **Content Documents: Root Metadata Only**: For content-type documents (`tutorial`, `how-to`, `reference`, `explanation`), place metadata only on the root `#` header. Subsections use plain Markdown headers without metadata blocks.

10. **Operational Documents: Per-Node Metadata**: For operational-type documents (`plan`, `task`, `log`), place metadata on every node that requires independent tracking.

## Document Sizing: How Much Should a Markdown Contain?
Every document in this knowledge base has three consumers: the **schema parser** (which doesn't care about size), **human readers** (constrained by working memory and attention), and **AI agents** (constrained by context window dynamics and instruction compliance). The parser imposes no size limit. The other two consumers impose real, different, and sometimes competing constraints. This section provides sizing guidance that accounts for both.

### The Core Principle: One Coherent Semantic Unit per File
The right unit of size is not a word count — it is the **coherent semantic unit**. A document should cover one concept, one problem, one rule set, or one workflow. When a document starts covering a second independent unit, it should probably become two files.

The test is simple: can you describe what this document is about in one sentence without using "and" to join two unrelated topics? If you need "and," consider splitting.

This principle applies differently across Diátaxis types:

- For `explanation`: one concept, one mental model. `ENGINE_EXPLANATION.md` covers the engine pattern across seven domains — but it's one coherent concept (the engine abstraction) explored from multiple angles. That's fine. An explanation covering both the engine pattern AND the observer pattern would be two semantic units and should be two files.
- For `how-to`: one problem, one goal. A how-to covering "Deploy to Cloud Run" is one unit. A how-to covering "Deploy to Cloud Run and Set Up CI/CD" is two units — even though they're related.
- For `reference`: one schema, one API, one rule set. A reference covering all allowed metadata fields is one unit. A reference covering both metadata fields AND Python tooling APIs would be two units (this document keeps them in separate sections under one file because they share the same normative authority, but splitting would also be defensible).
- For `tutorial`: one learning arc. A tutorial can span multiple steps and be longer than other types, but it should take the learner through one complete experience with one coherent outcome.

### Sizing by Type and Injection Role
Optimal document size varies by the `type` × `injection` combination because different consumption patterns have different cognitive and computational constraints.

#### Directive Documents: Shorter Is Better
This is the strongest sizing claim in this section: **documents with `injection: directive` should be as short as possible while remaining complete.**

The reason is attention economics. When an agent receives a directive document, every rule competes with every other rule for limited attention. A 500-word coding standard gets followed. A 5,000-word coding standard gets partially followed, with rules near the middle silently dropped. Humans exhibit the same behavior — compliance degrades as the rule set grows.

Practical guidance for directive documents:

- **Target**: 500–1,500 words (roughly 700–2,000 tokens). This is the zone where both humans and agents can hold the full rule set in active working memory.
- **Hard ceiling**: 3,000 words. Beyond this, split into focused sub-documents (e.g., `CODING_CONVENTIONS.md` and `NAMING_CONVENTIONS.md` rather than one monolithic `CONVENTIONS.md`).
- **If you can't shorten it**: Prioritize. Put the most critical rules first. Both humans and agents attend most strongly to the beginning of a document.
- **Exception**: `type: reference` + `injection: directive` (like this document) can be longer because reference documents are accessed non-linearly — the reader looks up the specific rule they need, not the whole set at once. But even here, individual sections should be concise.

#### Background Documents: Moderate, Focused Depth
Documents with `injection: background` build the agent's conceptual model. They can be longer than directives because the reader is absorbing understanding rather than memorizing rules. But they are not unlimited.

For agents, the "lost in the middle" problem is real: LLMs attend strongly to the first ~2,000–4,000 tokens and the last ~1,000–2,000 tokens of their context, with degraded attention to material in between (see Liu et al., 2023 — "Lost in the Middle: How Language Models Use Long Contexts," *Transactions of the Association for Computational Linguistics*, Vol. 12). A background explanation that buries its key insight on page 4 of a 6-page document risks having that insight ignored.

> **Freshness note:** The specific token ranges cited above (2,000–4,000 high-attention zone, 1,000–2,000 recency zone) are empirical findings from the Liu et al. study conducted on models available in mid-2023. Newer architectures with improved attention mechanisms (e.g., extended context windows, ring attention, or instruction-tuned long-context models) may shift these boundaries. The `last_checked` and `volatility` fields on this document help track when these numbers should be re-calibrated against current model benchmarks. The structural principle — that attention is unevenly distributed across the context window — remains stable across architectures even as the specific boundaries move.

Practical guidance for background documents:

- **Target**: 1,500–4,000 words (roughly 2,000–5,500 tokens).
- **Structure matters more than length**: Front-load the core insight. Use the opening paragraph to state the conceptual takeaway. Then develop it. Summarize at the end. This ensures the key ideas land in the high-attention zones of the context window.
- **For humans**: Cognitive load research suggests that reading comprehension degrades after roughly 2,500 words of continuous prose without a structural break (new section header, diagram, concrete example). Use structural resets — they benefit both human readers and agent attention.
- **If the explanation exceeds 4,000 words**: Ask whether it's truly one concept. `MCP_REF.md` at ~3,500 words covers MCP architecture as one coherent system — that's fine. If it also covered A2A protocol, that would be two concepts and should split.

#### Procedural Documents: Compact Action Scripts
Documents with `injection: procedural` are action scripts — the agent (or human) follows them step by step. Each additional step is cognitive overhead, and irrelevant context between steps increases the chance of skipping or misinterpreting a step.

Practical guidance for procedural documents:

- **Target**: 500–2,000 words. One workflow, one goal.
- **Step count**: Aim for 5–12 steps. Fewer than 5 usually means the document is too high-level to be actionable. More than 12 usually means the procedure has sub-procedures that should be extracted into their own files and linked.
- **No theory in the middle**: If a step requires conceptual background, provide that in a separate `explanation` document and link to it. A procedural document that pauses to explain why a step works is mixing Diátaxis modes and degrades both the procedure and the explanation.

#### Informational Documents: Size Varies by Access Pattern
Documents with `injection: informational` provide facts the agent may reference. Their sizing depends heavily on the Diátaxis `type`:

- `type: reference` + `injection: informational` — Can be longer (2,000–6,000+ words) because they're accessed non-linearly. A component enumeration table, a list of gcloud commands, a schema definition — these are scanned, not read. The important thing is internal organization (consistent structure, clear headers) rather than total length.
- `type: log` + `injection: informational` — Grows over time by nature. Keep individual entries concise (3–5 sentences per log entry). The log as a whole can be long because it's always read from the top (most recent first).

### The Agent Attention Budget
When multiple documents are injected into an agent's context window simultaneously, they compete for a shared attention budget. Understanding this budget is essential for context assembly.

#### The Attention Degradation Curve
Current LLMs (as of early 2026) exhibit a well-documented attention pattern, first rigorously characterized by Liu et al. (2023) in "Lost in the Middle: How Language Models Use Long Contexts":

- **High attention zone**: The first ~2,000–4,000 tokens of the context (system prompt and early injections) receive strong, reliable attention. Instruction compliance in this zone is high.
- **Degraded middle zone**: Material injected in the middle of a large context receives reduced attention. The agent may use it if prompted, but is less likely to proactively apply it. This is the "lost in the middle" phenomenon.
- **Recency zone**: The last ~1,000–2,000 tokens (including the user's most recent message) receive strong attention again.

> **Reference:** Liu, N.F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2023). Lost in the Middle: How Language Models Use Long Contexts. *Transactions of the Association for Computational Linguistics*, 12, 157–173.

> **Freshness advisory:** These token-range estimates are derived from experiments on models available in 2023. Post-2023 architectures have made incremental improvements in mid-context recall, but the U-shaped attention curve remains a robust finding across model families. Re-calibrate the specific numbers against your current model stack when the `last_checked` date on this document exceeds 6 months. The `volatility: stable` rating on this document refers to the structural principle; the specific numbers within it are `evolving` and should be verified.

This has direct implications for how the context assembly pipeline should order injected documents. `directive` documents should occupy the high-attention zone. `background` documents can go in the middle if their key insights are front-loaded. `informational` documents can go anywhere since they're queried on-demand rather than proactively applied.

#### Total Context Budget
There is a practical ceiling on how much injected context an agent can use effectively, well below the theoretical context window size. A model with a 200,000-token window does not produce 200,000 tokens worth of reliable instruction-following.

As a working rule of thumb:

- **Reliable instruction compliance**: ~4,000–8,000 tokens of directive content. Beyond this, rules start getting silently dropped.
- **Effective working knowledge**: ~15,000–30,000 tokens of combined background + informational content. Beyond this, the agent starts confusing details across documents or ignoring some entirely.
- **Theoretical maximum**: The full context window. The agent can technically "see" everything, but attention is diluted.

These numbers are approximate and shift with model architecture advances. The structural principle is stable, though: agents have a finite attention budget, and every document you inject draws from it.

#### Implication: Fewer, Focused Documents Beat Many Sprawling Ones
If you inject three 1,000-word directive documents, the agent can hold all three rule sets. If you inject one 5,000-word directive document, the middle third gets degraded attention. If you inject ten 2,000-word documents of mixed types, the agent starts confusing which rules are mandatory and which are background.

The practical takeaway: keep individual documents focused and short, and be selective about how many you inject simultaneously. The context assembly pipeline should use the `injection` field to prioritize — inject all relevant `directive` docs, then fill remaining budget with `background` and `informational` as needed. Documents marked `injection: excluded` are skipped entirely.

### The Human Reading Budget
Humans face a different but related set of constraints. These matter because many documents in this knowledge base serve both human readers and agent context injection.

#### Working Memory
Miller's Law (1956) established that human working memory holds roughly 7 ± 2 chunks of information at a time. More recent research (Cowan, 2001) revises this down to about 4 chunks for most practical tasks.

What counts as a "chunk" depends on expertise. For someone familiar with the knowledge base, "the MCP tool-call loop" is one chunk. For a newcomer, that phrase decomposes into many sub-concepts. This means:

- **Normative documents** (rules the reader must follow while working) should contain no more than 7–10 rules per section. If a coding standard has 25 rules, group them into 3–4 thematic sections of 6–8 rules each. The reader's working memory can handle one section at a time.
- **Explanations** should introduce no more than 3–5 new concepts before providing a concrete example or structural reset. `ENGINE_EXPLANATION.md` does this well: it introduces 5 core engine properties, then immediately grounds them with 7 concrete examples. Each example is a chance for the reader to consolidate the abstract concepts before new ones arrive.
- **Procedures** should have no more than 12 steps visible at once. Beyond that, the reader loses track of where they are in the sequence.

#### Sustained Attention
Humans can sustain focused reading for roughly 15–25 minutes before attention quality drops. At an average reading speed of 200–250 words per minute for technical prose, this translates to:

- **~3,000–6,000 words** of continuous technical reading before the reader needs a break or structural reset.
- This does NOT mean every document should be under 6,000 words. It means that documents longer than that should provide clear "re-entry points" — section headers, summaries, tables — so the reader can stop, return, and find their place without re-reading from the beginning.
- `reference` documents can be much longer than 6,000 words because they're scanned, not read. A 10,000-word API reference is fine if it has a clear structure. A 10,000-word explanation is too long.

#### The Compliance Gradient
For normative documents (`label: [normative]`), there is a well-known inverse relationship between length and compliance. A 1-page style guide gets followed. A 10-page style guide gets bookmarked and forgotten. A 50-page style guide gets actively resented.

This is not about laziness — it's about the cognitive cost of holding rules in working memory while doing substantive work. The reader's attention is primarily on their task (writing code, deploying infrastructure), not on the rule set. The fewer rules they need to remember, the more likely each rule gets followed.

For this knowledge base, the implication is: if a normative reference exceeds ~2,000 words, consider whether it can be split into a "core rules" document (short, always injected) and an "extended rules" document (longer, consulted when relevant).

### Sizing Recommendations Summary
| Type × Injection | Target Length | Hard Ceiling | Rationale |
|:---|:---|:---|:---|
| `reference` + `directive` | 500–1,500 words per rule section | 3,000 words total | Rules compete for attention; shorter = higher compliance. Non-linear access permits longer totals if sections are focused. |
| `how-to` + `directive` | 500–1,500 words | 2,000 words | Mandatory procedures must be fully absorbed. |
| `how-to` + `procedural` | 500–2,000 words | 2,500 words | One workflow, one goal. 5–12 steps. |
| `explanation` + `background` | 1,500–4,000 words | 5,000 words | Front-load the insight. Structural resets every ~800 words. |
| `reference` + `informational` | 2,000–6,000 words | No hard ceiling | Non-linear access; internal organization matters more than total length. |
| `tutorial` + `procedural` | 2,000–5,000 words | 6,000 words | Sequential, guided; can be longer but should have one learning arc. |
| `log` + `informational` | 3–5 sentences per entry | No hard ceiling | Grows over time. Newest first. Individual entries concise. |
| `plan` / `task` + `informational` | 200–1,000 words | 2,000 words | Operational context should be concise and scannable. |
| Any type + `excluded` | No constraint | No constraint | Not injected into agent context. Size for human readers only. |

These are guidelines, not rules. A 4,500-word explanation that is genuinely one coherent concept is better than two 2,250-word fragments that lose their thread. The semantic unit test (Section "The Core Principle") takes precedence over word counts.

### When to Split a Document
Split a document when ANY of the following are true:

1. **Two semantic units**: The document covers two independent concepts, problems, or rule sets that could be understood without each other.
2. **Mixed injection roles**: Part of the document is `directive` (agent must obey) and part is `background` (agent should absorb). These need different positions in the context assembly pipeline and different attention priorities.
3. **Mixed Diátaxis types at the root level**: The document is half `reference` and half `explanation` with neither clearly dominant. (Mixed types within subsections are normal and acceptable.)
4. **Over the hard ceiling**: The document exceeds the hard ceiling for its type × injection combination and cannot be shortened without losing essential content.
5. **The "findability" test fails**: A reader (human or agent) looking for a specific piece of information in this document would have to scan through unrelated material to find it.
6. **Mixed volatility**: Part of the document is `stable` (core conventions) and part is `ephemeral` (current sprint tasks). These have different cache and re-verification needs and should be separated so the pipeline can handle them independently.

Do NOT split a document just because it is long if it is one coherent unit. A 5,000-word explanation of a complex architecture that holds together as a single narrative is better than three disconnected 1,700-word fragments. The dependency resolver can handle large files; what it cannot handle is semantic fragmentation across files that should have been one.

## Quick Reference Card
### Valid `type` Values
```
type: tutorial | how-to | reference | explanation | plan | task | log
```

| Type | Diátaxis Quadrant | One-Line Description |
|:---|:---|:---|
| `tutorial` | Action + Acquisition | Step-by-step guided learning experience. |
| `how-to` | Action + Application | Goal-oriented instructions for a specific problem. |
| `reference` | Cognition + Application | Factual, structured information for lookup. |
| `explanation` | Cognition + Acquisition | Conceptual discussion that builds understanding. |
| `plan` | (Operational) | High-level objective with beginning and end. |
| `task` | (Operational) | Specific actionable unit of work. |
| `log` | (Operational) | Append-only historical record. |

### Valid `injection` Values
```
injection: directive | informational | procedural | background | excluded
```

| Value | Agent Behavior | Mnemonic |
|:---|:---|:---|
| `directive` | MUST comply | "Obey this." |
| `informational` | MAY use | "Know this." |
| `procedural` | Should EXECUTE | "Do this." |
| `background` | Should ABSORB | "Understand this." |
| `excluded` | MUST NOT inject | "Skip this." |

### Valid `volatility` Values
```
volatility: stable | evolving | ephemeral
```

| Value | Freshness Window | Mnemonic |
|:---|:---|:---|
| `stable` | Months to years | "Set and forget." |
| `evolving` | Weeks to months | "Check periodically." |
| `ephemeral` | Days to weeks | "Verify before trusting." |

### Valid Labels
All labels must be registered in `label_registry.json`. Current standard labels:

**Audience/role:** `agent`, `human`, `skill`, `normative`

**Domain:** `infrastructure`, `frontend`, `backend`

**Status/structure:** `core`, `template`, `draft`, `planning`, `source-material`

### Mandatory Fields
Every node must have: `status`, `type`.

### Metadata Template (Copy-Paste)
**For content documents** (metadata on root `#` header only):

```markdown
# [Document Title]
- status: active
- type: [tutorial | how-to | reference | explanation]
- id: [parent.child.node]
- label: [label1, label2]
- injection: [directive | informational | procedural | background | excluded]
- volatility: [stable | evolving | ephemeral]
- last_checked: YYYY-MM-DD
<!-- content -->
```

**For operational documents** (metadata on every node):

```markdown
# [Project Title]
- status: in-progress
- type: plan
- id: [project_id]
- label: [label1, label2]
- injection: informational
- volatility: ephemeral
- last_checked: YYYY-MM-DD
<!-- content -->

## [Task Title]
- status: todo
- type: task
- id: [project_id.task_id]
- owner: [agent-or-user]
- estimate: [time]
- blocked_by: [dependency_ids]
<!-- content -->
```
