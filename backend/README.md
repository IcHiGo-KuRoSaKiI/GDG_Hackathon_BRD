# BRD Generator - Backend

FastAPI backend for the BRD Generator system. Uses Gemini AI with an agentic tool-calling architecture to generate structured Business Requirements Documents from uploaded project files.

## Tech Stack

- **Framework:** FastAPI (async)
- **Database:** Google Cloud Firestore
- **Storage:** Google Cloud Storage
- **AI/LLM:** Google Gemini 2.5 Pro (via LiteLLM)
- **Auth:** JWT (access + refresh tokens)
- **Deployment:** Google Cloud Run (via Terraform)

## Local Development

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Required variables:
| Variable | Description |
|---|---|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key (empty = ADC) |
| `STORAGE_BUCKET` | GCS bucket for document uploads |
| `GEMINI_API_KEY` | Gemini API key |
| `GEMINI_MODEL` | Model name (e.g. `gemini-2.5-pro`) |
| `GEMINI_MAX_OUTPUT_TOKENS` | Max output tokens (recommended: `65536`) |
| `JWT_SECRET_KEY` | Secret for signing JWTs |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |

### 3. Run Development Server

```bash
python main.py
```

Server runs at http://localhost:8080

## API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc

## API Endpoints

### Auth
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT tokens
- `POST /auth/refresh` - Refresh access token

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List user's projects
- `GET /api/v1/projects/{id}` - Get project details

### Documents
- `POST /api/v1/projects/{id}/documents/upload` - Upload documents
- `GET /api/v1/projects/{id}/documents` - List project documents
- `DELETE /api/v1/projects/{id}/documents/{doc_id}` - Delete document

### BRDs
- `POST /api/v1/projects/{id}/brds/generate` - Generate BRD (agentic, background)
- `GET /api/v1/projects/{id}/brds` - List project BRDs
- `GET /api/v1/projects/{id}/brds/{brd_id}` - Get BRD details
- `POST /api/v1/projects/{id}/brds/{brd_id}/chat` - Chat (refine text, ask questions, trigger generation)
- `PUT /api/v1/projects/{id}/brds/{brd_id}/sections/{key}` - Update BRD section
- `PUT /api/v1/projects/{id}/brds/{brd_id}/conflicts/{idx}` - Resolve conflict

### Deletion
- `POST /api/v1/projects/{id}/delete` - Delete project and all related data

## Architecture

### Agentic BRD Generation

BRDs are generated via a fully agentic loop (not Python-orchestrated). The AI agent:
1. Reads uploaded documents using file-system tools (`read_document`, `list_documents`)
2. Analyzes content and extracts requirements
3. Calls `submit_brd_section` (virtual tool) for each of the 13 BRD sections
4. Calls `submit_analysis` (virtual tool) with conflicts, sentiments, and citations

**Virtual Tool Pattern:** Gemini's `tools` parameter and `response_mime_type: "application/json"` cannot coexist. Virtual tools are defined as function declarations, intercepted before execution, and their arguments extracted as structured data.

### Unified Chat

A single `/chat` endpoint handles three intents:
- **Refinement** - Edit specific BRD section text
- **Answer** - General questions about the BRD/project
- **Generation** - Trigger full BRD generation from chat

The AI classifies intent via the `submit_response` virtual tool.

## Project Structure

```
backend/
├── main.py                  # FastAPI app entry point
├── requirements.txt         # Python dependencies
├── prompts.json             # AI system prompts
├── agent/
│   └── tools.py             # Virtual tool schemas (BRD generation + chat)
├── config/
│   ├── settings.py          # Pydantic BaseSettings (env vars)
│   ├── firebase.py          # Firestore + Firebase init (ADC fallback)
│   └── gemini.py            # Gemini/LiteLLM client config
├── models/
│   ├── brd.py               # BRD Pydantic models (13 sections)
│   ├── document.py          # Document models
│   ├── project.py           # Project models
│   └── user.py              # User/auth models
├── routes/
│   ├── auth.py              # JWT auth endpoints
│   ├── brds.py              # BRD CRUD + chat + conflicts
│   ├── documents.py         # Document upload/list
│   ├── projects.py          # Project CRUD
│   └── deletions.py         # Cascade deletion
└── services/
    ├── agent_service.py     # Legacy orchestration + entry point
    ├── brd_generation_service.py  # Agentic BRD generation loop
    ├── text_refinement_service.py # Unified chat (refine/answer/generate)
    ├── firestore_service.py # Firestore CRUD operations
    ├── document_service.py  # Document processing
    ├── storage_service.py   # GCS upload/download
    ├── auth_service.py      # JWT token management
    └── gemini_service.py    # Gemini API wrapper
```

## Deployment (Cloud Run via Terraform)

```bash
# From project root
./deploy.sh [image-tag]
```

This builds the Docker image via Cloud Build, pushes to Artifact Registry, and deploys to Cloud Run using Terraform. See root `deploy.sh` and `infra/` for details.

To update env vars (CORS, model, etc.) without rebuilding:
```bash
cd infra
terraform apply -auto-approve
```
