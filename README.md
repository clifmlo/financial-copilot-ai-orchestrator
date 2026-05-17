# Financial Copilot AI Orchestrator

LangGraph-based AI orchestration service for the Financial Copilot platform. Independently deployable to **Azure Container Apps**.

## Role in the platform

| Responsibility | Owner |
|----------------|--------|
| User, account, portfolio, bond, transaction, tax data | [financial-copilot-api](https://github.com/clifmlo/financial-copilot-api) |
| Financial calculations, persistence, auth, business rules | financial-copilot-api |
| LangGraph workflows, multi-agent reasoning | **this repo** |
| Prompt management, tool calling, AI explanations | **this repo** |
| Report generation, scenario interpretation, recommendation narration | **this repo** |
| Dashboard UI | [financial-copilot-web](https://github.com/clifmlo/financial-copilot-web) |

This service **does not** connect to PostgreSQL or own financial data. All figures are read from versioned REST APIs on `financial-copilot-api` (`/api/v1/*`).

## Architecture

```
financial-copilot-web  ──►  financial-copilot-ai-orchestrator  ──►  financial-copilot-api
     (browser)                    (LangGraph / FastAPI)              (Spring Boot / Postgres)
```

## API (consumed by web & API gateway)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/health/dependencies` | Portfolio API connectivity |
| POST | `/api/v1/chat` | Multi-agent chat |
| GET | `/api/v1/agents` | Registered agents |

## Prerequisites

- Python 3.11+
- Running [financial-copilot-api](https://github.com/clifmlo/financial-copilot-api) on port 8080 (local)

## Local development

```powershell
cp .env.example .env
# Set OPENAI_API_KEY and PORTFOLIO_API_URL

.\scripts\run.ps1
```

Or manually:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Environment

| Variable | Description |
|----------|-------------|
| `PORTFOLIO_API_URL` | Base URL of financial-copilot-api (e.g. `http://localhost:8080`) |
| `PORTFOLIO_API_VERSION` | API version prefix (default `v1`) |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model id (default `gpt-4o-mini`) |
| `CORS_ORIGINS` | Comma-separated browser origins (default `http://localhost:3000`) |

## Docker

```bash
docker build -t financial-copilot-ai-orchestrator .
docker run -p 8000:8000 \
  -e PORTFOLIO_API_URL=http://host.docker.internal:8080 \
  -e OPENAI_API_KEY=sk-... \
  financial-copilot-ai-orchestrator
```

## Azure Container Apps

GitHub Actions workflow `.github/workflows/deploy.yml` builds the image, pushes to ACR, and deploys to Container Apps.

Configure repository **variables**: `ACR_LOGIN_SERVER`, `ACR_NAME`, `ACA_ORCHESTRATOR_APP_NAME`, `AZURE_RESOURCE_GROUP`, `PORTFOLIO_API_URL`, `OPENAI_MODEL`, `CORS_ORIGINS`.

Configure **secrets**: `ACR_USERNAME`, `ACR_PASSWORD`, `OPENAI_API_KEY`.

## Project layout

```
app/
  api/routes/       # FastAPI REST endpoints
  agents/           # Agent identifiers & routing
  clients/          # financial-copilot-api HTTP client
  graph/            # LangGraph workflow
  prompts/          # System prompts
  tools/            # API-backed tool functions
```

## Related repos

- [financial-copilot-api](https://github.com/clifmlo/financial-copilot-api) — System of record
- [financial-copilot-web](https://github.com/clifmlo/financial-copilot-web) — Dashboard UI
- [financial-copilot-infra](https://github.com/clifmlo/financial-copilot-infra) — Azure IaC
