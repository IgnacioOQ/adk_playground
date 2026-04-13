# Chatbot Template

A minimal production-ready ADK chatbot:

- **Backend**: Python 3.11 + FastAPI + Google ADK (`gemini-2.5-flash`). Endpoints: `POST /chat`, `GET /stream` (SSE), `GET /health`.
- **Frontend**: Next.js 14 (App Router, TypeScript, SSR). Server-side proxy routes call the backend with OIDC ID tokens minted via the GCP metadata server.

See `ADK_CHATBOT_SKILL.md` for the development pattern and `A2UI_REF.md` for the agent-to-UI protocol.

## Architecture (production)

```
[Browser]
   |  HTTPS
   v
[Firebase App Hosting]  (Next.js SSR + Cloud CDN)
   |  fetch + OIDC ID token (via metadata server)
   v
[Cloud Run: chatbot-template-app-backend]  (IAM-only)
   |
   +-- Secret Manager: GOOGLE_API_KEY
   +-- Gemini API (AI Studio)
```

The browser **never** calls Cloud Run directly. All backend traffic flows through `frontend/src/app/api/chat/route.ts` and `…/stream/route.ts`. The Next.js server holds `roles/run.invoker` on the backend service via the App Hosting runtime SA.

For full infrastructure details see `knowledge_base/content/reference/INFRASTRUCTURE_CHATBOT_TEMPLATE_REF.md`.

## Production branch

Production deploys are sourced **exclusively** from the **`chatbot-template`** branch of `eikasia-llc/adk_playground`:

- Frontend: Firebase App Hosting auto-deploys on every push to `chatbot-template` (root: `chatbot_template/frontend/`).
- Backend: `./deploy.sh` refuses to run from any other branch.

`main` is unaffected by this app's lifecycle.

## Local development

```bash
./dev.sh
```

This starts:
- Backend on `http://localhost:8080` (uvicorn with reload)
- Frontend on `http://localhost:3000` (Next.js dev server)

The Next.js proxy routes detect `BACKEND_URL=http://localhost:*` and skip OIDC ID token minting (which only works inside GCP).

Backend env (`backend/.env`):
```
GOOGLE_API_KEY=AIza...
ALLOWED_ORIGINS=http://localhost:3000
```

Frontend env (`frontend/.env.local`):
```
BACKEND_URL=http://localhost:8080
```

## Production deploy

### Backend (Cloud Run)
```bash
git checkout chatbot-template
./deploy.sh
```
or via Cloud Build:
```bash
gcloud builds submit --config cloudbuild.yaml --project=chatbot-template .
```

### Frontend (Firebase App Hosting)
```bash
git checkout chatbot-template
git push origin chatbot-template
```
A push to `chatbot-template` triggers an automatic App Hosting rollout.

For detailed runbook, log access, and console deep links see (in the knowledge base):
- `content/how-to/CHATBOT_TEMPLATE_DEPLOY_SKILL.md`
- `content/how-to/CHATBOT_TEMPLATE_LOGS_SKILL.md`
- `content/how-to/CHATBOT_TEMPLATE_CONSOLE_SKILL.md`

## Alternative frontend deploy: Cloud Run

`frontend/Dockerfile` is kept as an audited, multi-stage alternative for deploying the frontend as a plain Cloud Run service (without Firebase App Hosting). It uses Next.js standalone output and runs as a non-root user. Not used by the production path.
