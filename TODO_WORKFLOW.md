# TODO Workflow
- status: active
- type: plan
- id: adk_playground.todo_workflow
- description: Cross-session task backlog; each task is self-contained and can be picked up by a coding agent with kb_mcp MCP tool access.
- label: [planning, agent]
- injection: excluded
- volatility: evolving
- owner: agent
- last_checked: 2026-05-11
<!-- content -->
Cross-session task backlog. Tasks are added here when work started in a session cannot be completed immediately. Each task must be fully self-contained — a fresh agent should be able to pick it up using only the task body and the kb_mcp tools, with no additional context required.

This file is the per-repository instance of the `TODO_WORKFLOW_TEMPLATE.md` pattern. It lives at the root of the working repository alongside `WORKLOG.md` and is intentionally **not registered with kb_mcp** — agents access it via the regular filesystem `Read`/`Edit` tools, not via `knowledge_base_*` calls.

**Agent rules (picking up tasks):**
1. Read each task in full before starting. If its preconditions are unmet, skip it and note the blocker.
2. After completing a task, delete its entire block from this file (from the `---` divider above the `##` header through the `---` divider below the last line of the task body).
3. After completing one or more tasks, assess whether a WORKLOG.md entry is warranted — see Phase 5 of `content/workflows/CODING_AGENT_MAIN_WORKFLOW.md`.
4. Confirm a task is still valid before executing; conditions may have changed since it was written.

**Adding tasks (session authors):**
- Copy the template below (without fences), fill in all fields, and insert it as a new `##` block above the Template section, preceded and followed by `---`.
- Be precise: include target file paths, specific tool calls, expected outcomes, and a verification step.

---

## Verify chatbot_template latency instrumentation in production
- status: todo
- type: task
- id: todo.verify_chatbot_latency_logs
- description: Probe the production /chat endpoint and confirm structured-JSON [LATENCY] lines reach Cloud Logging at NOTICE severity, then assess whether `thinking_budget=0` + `maximum_remote_calls=3` actually moved per-trip latency.
- owner: agent
- blocked_by: []
- last_checked: 2026-05-11
<!-- content -->
**Context:** Backend revision `chatbot-template-app-backend-00003-9db` (image `cb1a9e5`) was deployed at the end of the 2026-05-11 session with: (a) `log_latency` context manager emitting structured JSON at `severity=NOTICE`, (b) `GenerateContentConfig` on the LlmAgent setting `thinking_budget=0` and `maximum_remote_calls=3`. The project's `_Default` log sink exclusion was updated from `severity < WARNING` to `severity < NOTICE` so NOTICE+ entries are ingested. The probe + log verification was not completed in-session because the user had to wrap up. See WORKLOG.md entry for 2026-05-11.

**Preconditions:**
- Authenticated gcloud session: `gcloud auth print-access-token` succeeds.
- Backend revision serving 100% traffic is `00003-9db` or later (confirm with `gcloud run services describe chatbot-template-app-backend --project=chatbot-template-eikasia --region=us-central1 --format='value(status.latestReadyRevisionName)'`).

**Steps:**
1. Mint an ID token and probe `/chat` 3–5 times with distinct messages (mix of off-topic, RPS round-start, RPS pick). Capture client-side `time_total` for each.
   ```bash
   BACKEND="https://chatbot-template-app-backend-207274917577.us-central1.run.app"
   TOKEN="$(gcloud auth print-identity-token)"
   SID="latency-verify-$(date +%s)"
   for msg in "hello" "let's play" "rock" "scissors" "stats"; do
     curl -sS -X POST "$BACKEND/chat" \
       -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
       -d "{\"message\":\"$msg\",\"session_id\":\"$SID\"}" \
       -w "\n  client_total=%{time_total}s\n"
     sleep 2
   done
   ```
2. Wait ~15s for log ingestion, then pull `[LATENCY]` entries from Cloud Logging. Severity is `NOTICE`, payload arrives as `jsonPayload.message` (not `textPayload`):
   ```bash
   gcloud logging read \
     'resource.type="cloud_run_revision" AND resource.labels.service_name="chatbot-template-app-backend" AND jsonPayload.message=~"\\[LATENCY\\]"' \
     --project=chatbot-template-eikasia --limit=80 \
     --format='value(timestamp,jsonPayload.message)' --freshness=15m
   ```
3. Analyze. For each request you expect three or four lines per turn: `ensure_session`, `make_runner`, `chat:runner_run` (and `stream:time_to_first_chunk` + `stream:total` for `/stream`). The dominant cost should be `chat:runner_run` (per the round-trip-dominance mental model in `content/how-to/LLM_LATENCY_SKILL.md`). If `make_runner` is non-trivial (>200ms), that's the MCP-subprocess-respawn-per-request hypothesis from the session analysis — investigate ADK's McpToolset lifecycle.
4. Compare against a baseline. The pre-change client wall times observed in the 2026-05-11 session were 2.4s / 3.9s / 2.9s for `/chat`. If post-change times are materially lower, the knobs worked. If not, the next lever is likely tool-call dedupe in the MCP server or prompt shrink — both deferred pending data.

**Verification:** Step 2 returns at least one `[LATENCY] chat:runner_run: <Nms>` line. Step 4 produces a defensible answer: knobs worked, or further work needed.

**On completion:** Delete this entire task block from TODO_WORKFLOW.md (from the `---` above the `##` header to the `---` below the last line). If further latency work is warranted (e.g., MCP lifecycle investigation, dedupe, prompt shrink), add a follow-up task block.

---

## Task Template

Copy the block below (without the outer fences), fill in all fields, and insert it as a new `## [Task Title]` task block.

````markdown
## [Task Title]
- status: todo
- type: task
- id: todo.[short_id]
- description: One-sentence description of what this task accomplishes.
- owner: agent
- blocked_by: []
- last_checked: {{YYYY-MM-DD}}
<!-- content -->
**Context:** Why this task exists and what triggered it. Include the KB path or repo file path it operates on.

**Preconditions:** Any state that must be true before starting (prior tasks complete, files present, etc.). Write `none` if there are none.

**Steps:**
1. (Include specific tool calls where possible, e.g., `knowledge_base_read(path="content/...", sections=["..."])`)
2. ...

**Verification:** How to confirm the task is complete (e.g., a grep that should return one match, a status field that should read `done`).

**On completion:** Delete this entire task block from TODO_WORKFLOW.md (from the `---` above the `##` header to the `---` below the last line).
````
