# Worklog

Backward-looking record of non-trivial sessions on this repo. Entries are appended at the bottom of the file. Forward-looking pending work lives in `TODO_WORKFLOW.md`.

---

## 2026-05-11 — chatbot_template: deploy hygiene, cosmetic title, latency tuning groundwork

- **Task:** Three threads in one session: (1) clean up `.claude/` settings hygiene and document the Firebase App Hosting deploy flow in the READMEs; (2) ship a cosmetic title change ("Template Chatbot" → "Template Chatbot - Testing") end-to-end through the production deploy pipeline; (3) apply the first round of latency optimizations from `content/how-to/LLM_LATENCY_SKILL.md` to `chatbot_template/backend`.
- **Outcome:**
  - **Hygiene:** added `.claude/settings.local.json` and `.claude/*.json-e` to `.gitignore`; cleaned heredoc-noise entries out of `.claude/settings.json`. (Uncommitted, deliberately — these are local config and don't need a shared-branch commit.)
  - **README:** top-level [README.md](README.md) now documents the Firebase App Hosting + Cloud Run topology and the `chatbot-template`-branch deploy model; bumped `last_checked: 2026-05-11`. Fixed two real bugs in [chatbot_template/README.md](chatbot_template/README.md): `./deploy.sh` → `./deploy-backend.sh` and `--project=chatbot-template` → `--project=chatbot-template-eikasia`. (Uncommitted.)
  - **Cosmetic title:** committed and deployed as `38fc30a` on both `main` and `chatbot-template`; Firebase App Hosting auto-rolled out; verified live with `curl` (title flipped at 14:38:23).
  - **Latency:** committed `fc5d265` (knobs: `thinking_budget=0`, `maximum_remote_calls=3` on the LlmAgent; instrumentation: `log_latency` context manager on `/chat` and `/stream`). First probe revealed no logs in Cloud Logging — diagnosed as the project's `_Default` sink dropping `severity < WARNING` per cost policy. Restructured `log_latency` to emit structured JSON at `severity=NOTICE` (`cb1a9e5`), updated the sink exclusion to `severity < NOTICE`, redeployed backend as revision `00003-9db`. Probe + log verification not completed — captured in TODO_WORKFLOW.md.
- **Key decisions:**
  - **Did NOT pin `temperature=0`** on the LlmAgent despite the playbook example. The RPS agent needs varied output for random picks; temperature is left to ADK/Gemini defaults.
  - **Latency log severity = NOTICE, not WARNING.** Latency telemetry is not a warning condition; bumping it to WARNING would have polluted the warning bucket. Updated the sink exclusion to match, keeping the cost-policy intent (drop verbose INFO/DEBUG) while letting NOTICE through.
  - **Kept `main` and `chatbot-template` strictly in sync** for every commit. Both branches point to the same SHA at all times. This is the user's preference per session context.
- **KB changes:** none. `content/how-to/LLM_LATENCY_SKILL.md` was consumed (read in full) but not modified. The cost-policy exclusion's description references `INFRASTRUCTURE_DEFINITIONS_REF.md`; that KB doc was *not* updated to reflect the new `< NOTICE` filter — flag for a future session.
- **Follow-up:** see `TODO_WORKFLOW.md` task `todo.verify_chatbot_latency_logs`. Outstanding: probe production `/chat`, verify `[LATENCY]` lines ingest at NOTICE, and assess whether the latency knobs moved per-trip cost vs. the pre-change baseline (2.4s / 3.9s / 2.9s client wall-time for three exploratory probes).

---

## 2026-05-11 (later) — chatbot_template: verified latency instrumentation, knobs worked

- **Task:** Execute `todo.verify_chatbot_latency_logs` from `TODO_WORKFLOW.md`: probe production `/chat` against the deployed `00003-9db` revision, confirm `[LATENCY]` lines ingest at NOTICE, and decide whether the `thinking_budget=0` + `maximum_remote_calls=3` knobs moved per-trip latency vs. the pre-change baseline.
- **Outcome:**
  - **Logs ingest cleanly.** 15 `[LATENCY]` entries from 5 probes, all severity=NOTICE, all in the `run.googleapis.com/stdout` log stream.
  - **Knobs worked.** Warm client wall-time mean ~2.25s (1.9 / 2.7 / 2.3 / 2.1) vs. pre-change baseline ~3.0s (2.4 / 3.9 / 2.9) — ~25% improvement. `chat:runner_run` ranges 1.5–2.4s warm, well under the playbook's "5–8s per round-trip on Flash-class" floor.
  - **MCP-respawn-per-request hypothesis ruled out.** `make_runner` is consistently ~0.1ms across all 5 probes. The stdio subprocess persists at module load via the `root_agent` binding.
  - **Cold start is ~13s of invisible time.** First probe was 15.6s client wall-time but `chat:runner_run` was only 2.4s; the gap is container boot + ADK init + first MCP spawn, which happen before the FastAPI handler can instrument anything. Only addressable by `minInstances ≥ 1` — not worth the cost at current traffic (~2 users/week).
  - **Multi-tool turns don't multiply round-trips.** Turn 3 ("rock" → `record_round` + `get_stats` + A2UI synthesis) took 2.25s — only ~500ms over a single-tool turn. Gemini AFC is collapsing the two tool calls into one inference cycle, so `maximum_remote_calls=3` had headroom and wasn't the binding constraint.
- **Key decisions:**
  - **No further latency work warranted now.** The remaining playbook levers (system-prompt shrink, server-side dedupe in `rps_memory_server.py`) have diminishing returns at this scale. Don't pre-optimize.
  - **Updated the TODO recipe in passing:** the original task had `jsonPayload.message` as the filter path — Cloud Run's log forwarder actually unwraps `{"severity":..., "message":...}` into `severity=NOTICE` + `textPayload=...`, so the correct filter is `textPayload:"[LATENCY]"`. Worth knowing for next time.
- **KB changes:** none. `content/how-to/LLM_LATENCY_SKILL.md` accurately predicted both the dominant cost (LLM round-trip) and the magnitude. No correction or addition warranted.
- **Follow-up:** none. Task block deleted from `TODO_WORKFLOW.md`.
