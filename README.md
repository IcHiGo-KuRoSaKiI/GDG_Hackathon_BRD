# BRD Generator

AI-powered platform that automatically generates Business Requirements Documents from uploaded project files. Upload emails, meeting transcripts, Slack exports, specs, or any document — the AI agent reads them, extracts requirements, detects conflicts, and produces a structured 13-section BRD.

**Live:** [gdg-hackathon-brd.vercel.app](https://gdg-hackathon-brd.vercel.app)

## Architecture

```
┌────────────────┐         ┌────────────────────┐
│   Frontend     │  HTTPS  │     Backend         │
│   Next.js 14   │────────>│     FastAPI         │
│   Vercel       │         │     Cloud Run       │
└────────────────┘         └──────┬───────┬──────┘
                                  │       │
                           ┌──────┘       └──────┐
                           v                     v
                    ┌─────────────┐     ┌──────────────┐
                    │  Firestore  │     │ Cloud Storage │
                    │  (database) │     │  (documents)  │
                    └─────────────┘     └──────────────┘
                                  │
                           ┌──────┘
                           v
                    ┌─────────────┐
                    │  Gemini AI  │
                    │  2.5 Pro    │
                    └─────────────┘
```

**Monorepo Structure:**
```
brd-generator/
├── backend/          # FastAPI + Gemini AI agent
├── frontend/         # Next.js 14 + shadcn/ui
├── infra/            # Terraform (Cloud Run, Artifact Registry)
├── Dockerfile        # Backend container (built from root)
├── deploy.sh         # One-command backend deployment
└── sample-documents/ # Test data (3 realistic projects)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, shadcn/ui, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.11, Pydantic |
| AI | Google Gemini 2.5 Pro (agentic tool-calling) |
| Database | Google Cloud Firestore |
| Storage | Google Cloud Storage |
| Auth | JWT (access + refresh tokens) |
| Infra | Terraform, Cloud Run, Artifact Registry, Cloud Build |
| Frontend Hosting | Vercel |

## Key Features

- **Multi-format document upload** — PDF, DOCX, TXT, CSV, PPTX with drag-and-drop
- **Agentic BRD generation** — AI reads all documents, generates 13-section BRD with citations
- **Inline text refinement** — Select any text in the BRD, chat with AI to refine it
- **Conflict detection** — Automatically finds contradictions across source documents
- **Conflict resolution** — Accept/reject conflicts with persistent status tracking
- **Citation tracking** — Every requirement links back to its source document
- **Unified AI chat** — Ask questions, refine text, or trigger generation from one chat panel

## Quick Start

### Prerequisites
- Node.js 18+, Python 3.11+
- GCP project with Firestore + Cloud Storage
- Gemini API key

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in your credentials
python main.py         # http://localhost:8080
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # Set NEXT_PUBLIC_API_URL
npm run dev                         # http://localhost:3000
```

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for detailed setup.

## Deployment

### Backend (Cloud Run)

```bash
./deploy.sh    # Builds image, pushes to Artifact Registry, deploys via Terraform
```

Requires: `gcloud` CLI authenticated, Terraform installed, `infra/terraform.tfvars` populated. See [deploy.sh](deploy.sh).

### Frontend (Vercel)

1. Import repo on Vercel, set root directory to `frontend`
2. Add env var: `NEXT_PUBLIC_API_URL` = Cloud Run URL
3. Deploy

After frontend deploy, add Vercel URL to `allowed_origins` in `infra/terraform.tfvars` and run `terraform apply` to update CORS.

## Sample Documents

Includes 33 realistic sample documents across 3 projects:
- **E-commerce Checkout Redesign** (13 files) — budget conflicts, stakeholder disagreements
- **Mobile Authentication** (10 files) — timeline slips, technical blockers
- **Internal Dashboard** (10 files) — conflicting requirements, scope creep

## Team

- **Vedansh** - Full Stack Developer
- **Vanshika** - Full Stack Developer

Built for GDG Hackathon 2026
