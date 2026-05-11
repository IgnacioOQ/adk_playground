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
