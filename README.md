# Sybil — AI-Powered BRD Generator

AI-powered platform that automatically generates Business Requirements Documents from uploaded project files. Upload emails, meeting transcripts, Slack exports, specs, or any document — the AI agent reads them, extracts requirements, detects conflicts, and produces a structured 13-section BRD with full citation tracking.

**Live:** [gdg-hackathon-brd.vercel.app](https://gdg-hackathon-brd.vercel.app)

---

## Table of Contents

- [Architecture](#architecture)
  - [Infrastructure](#1-infrastructure-architecture)
  - [AI Agent Flow](#2-ai-agent-flow--brd-generation--editing)
  - [Enron Data Preprocessing](#3-enron-data-preprocessing-pipeline)
- [Tech Stack](#tech-stack)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Enron Preprocessing — Deep Dive](#enron-preprocessing--deep-dive)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Sample Documents](#sample-documents)
- [Team](#team)

---

## Architecture

### 1. Infrastructure Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │              GOOGLE CLOUD PLATFORM          │
                         │                                             │
┌──────────────┐  HTTPS  │  ┌──────────────────┐                       │
│              │────────────>│   Cloud Run      │                       │
│   Frontend   │         │  │   (FastAPI)       │                       │
│   Next.js 14 │<────────────│   Port 8080      │                       │
│              │         │  └──────┬───────┬────┘                       │
│   Vercel     │         │         │       │                            │
│   (CDN)      │         │         │       │                            │
│              │         │    ┌────┘       └────┐                       │
└──────────────┘         │    v                 v                       │
       │                 │ ┌────────────┐  ┌──────────────┐             │
       │                 │ │ Firestore  │  │Cloud Storage │             │
       │                 │ │ (NoSQL DB) │  │ (Documents)  │             │
       │                 │ │            │  │              │             │
       │                 │ │ - projects │  │ - originals  │             │
       │                 │ │ - documents│  │ - parsed txt │             │
       │                 │ │ - brds     │  │              │             │
       │                 │ │ - chunks   │  └──────────────┘             │
       │                 │ │ - users    │                               │
       │                 │ └────────────┘                               │
       │                 │         │                                    │
       │                 │    ┌────┘                                    │
       │                 │    v                                         │
       │                 │ ┌──────────────────┐                         │
       │                 │ │   Gemini 2.5 Pro │                         │
       │                 │ │   (AI Engine)    │                         │
       │                 │ │                  │                         │
       │                 │ │ - Classification │                         │
       │                 │ │ - BRD Generation │                         │
       │                 │ │ - Chat/Refine    │                         │
       │                 │ │ - Embeddings     │                         │
       │                 │ └──────────────────┘                         │
       │                 │                                             │
       │                 │ ┌──────────────────┐                         │
       │                 │ │ Artifact Registry│                         │
       │                 │ │ (Docker Images)  │                         │
       │                 │ └──────────────────┘                         │
       │                 │                                             │
       │                 └─────────────────────────────────────────────┘
       │
       │                 ┌─────────────────────────────────────────────┐
       │                 │              INFRASTRUCTURE AS CODE         │
       └────────────────>│  Terraform (Cloud Run + Artifact Registry)  │
                         │  deploy.sh (Build + Push + Apply)           │
                         └─────────────────────────────────────────────┘
```

**Monorepo Structure:**
```
sybil/
├── backend/              # FastAPI + Gemini AI agent
│   ├── agent/            #   Agentic tools + virtual tool schemas
│   ├── config/           #   Firebase, Gemini, settings
│   ├── models/           #   Pydantic data models
│   ├── routes/           #   API endpoints
│   ├── services/         #   Business logic
│   ├── preprocessing/    #   Enron email pipeline
│   └── utils/            #   Prompts, sanitization, auth
├── frontend/             # Next.js 14 + shadcn/ui
│   ├── app/              #   App Router pages
│   ├── components/       #   UI components
│   ├── hooks/            #   Custom React hooks
│   └── lib/              #   API client, stores, utils
├── infra/                # Terraform (Cloud Run, Artifact Registry)
├── Dockerfile            # Backend container
├── deploy.sh             # One-command deployment
└── sample-documents/     # 33 test docs across 3 projects
```

---

### 2. AI Agent Flow — BRD Generation & Editing

#### BRD Generation (Fully Agentic)

```
  User clicks "Generate BRD"
            │
            v
  ┌─────────────────────────┐
  │  POST /brds/generate    │
  │  (fire-and-forget)      │
  │  Returns 202 Accepted   │
  └────────────┬────────────┘
               │
               v
  ┌─────────────────────────────────────────────────────────┐
  │              AGENTIC LOOP  (max 30 iterations)          │
  │              65,536 output tokens per turn               │
  │                                                         │
  │  ┌───────────────────────────────────────────────────┐  │
  │  │  Iteration 1: AI calls list_project_documents()   │  │
  │  │  → Returns doc list with AI metadata              │  │
  │  └──────────────────────┬────────────────────────────┘  │
  │                         v                               │
  │  ┌───────────────────────────────────────────────────┐  │
  │  │  Iterations 2-5: AI calls get_full_document_text()│  │
  │  │  → Reads FULL text of each document (not chunks)  │  │
  │  │  → No RAG — agent reads everything directly       │  │
  │  └──────────────────────┬────────────────────────────┘  │
  │                         v                               │
  │  ┌───────────────────────────────────────────────────┐  │
  │  │  Iterations 6-7: AI calls search_documents_*()    │  │
  │  │  → Topic search, content type search              │  │
  │  │  → Cross-references between documents             │  │
  │  └──────────────────────┬────────────────────────────┘  │
  │                         v                               │
  │  ┌───────────────────────────────────────────────────┐  │
  │  │  Iterations 8-20: AI calls submit_brd_section()   │  │
  │  │  → VIRTUAL TOOL (intercepted, not executed)       │  │
  │  │  → Submits 13 sections one by one:                │  │
  │  │    executive_summary, business_objectives,        │  │
  │  │    stakeholders, functional_requirements,         │  │
  │  │    non_functional_requirements, assumptions,      │  │
  │  │    success_metrics, timeline, project_background, │  │
  │  │    project_scope, dependencies, risks,            │  │
  │  │    cost_benefit                                   │  │
  │  │  → Each section includes citations to source docs │  │
  │  └──────────────────────┬────────────────────────────┘  │
  │                         v                               │
  │  ┌───────────────────────────────────────────────────┐  │
  │  │  Final iteration: AI calls submit_analysis()      │  │
  │  │  → VIRTUAL TOOL (intercepted)                     │  │
  │  │  → Conflicts detected across documents            │  │
  │  │  → Stakeholder sentiment analysis                 │  │
  │  │  → Key concerns extracted                         │  │
  │  └──────────────────────┬────────────────────────────┘  │
  │                         │                               │
  └─────────────────────────┼───────────────────────────────┘
                            v
  ┌─────────────────────────────────────────────────────────┐
  │  ASSEMBLY: Build BRD from collected sections + analysis │
  │  → Store in Firestore (flat section fields)             │
  │  → Frontend polls GET /brds → detects new BRD          │
  └─────────────────────────────────────────────────────────┘
```

**Virtual Tool Pattern** — Why?
> Gemini API cannot combine `tools` (function calling) with `response_mime_type: "application/json"` (structured output) in the same request. Our workaround: define virtual tools (`submit_brd_section`, `submit_analysis`, `submit_response`) that the AI "calls" — but the backend intercepts the function call arguments as structured data instead of executing them. This gives us both agentic tool-calling AND structured output in one pipeline.

#### BRD Editing via Natural Language (Unified Chat)

```
  User selects text in BRD viewer
            │
            v
  ┌──────────────────────┐     ┌───────────────────────┐
  │  Floating toolbar:   │────>│  Chat panel opens     │
  │  "Refine with AI"    │     │  with selected text   │
  └──────────────────────┘     │  as context            │
                               └───────────┬───────────┘
                                           │
            User types instruction         │
        (e.g., "Make this more concise")   │
                                           v
  ┌─────────────────────────────────────────────────────┐
  │  POST /brds/{id}/chat                               │
  │  {                                                  │
  │    message: "Make this more concise",               │
  │    section_context: "executive_summary",            │
  │    selected_text: "OAuth 2.0 authentication...",    │
  │    conversation_history: [...]                      │
  │  }                                                  │
  └──────────────────────┬──────────────────────────────┘
                         │
                         v
  ┌─────────────────────────────────────────────────────┐
  │            3-LAYER SECURITY                         │
  │  1. Pydantic validation (length limits)             │
  │  2. Regex injection detection                       │
  │  3. Defensive prompts (<user_input> wrapping)       │
  └──────────────────────┬──────────────────────────────┘
                         │
                         v
  ┌─────────────────────────────────────────────────────┐
  │  UNIFIED AGENTIC WORKFLOW (max 8 iterations)        │
  │                                                     │
  │  AI can call document tools to reference sources    │
  │  AI MUST call submit_response() to finish:          │
  │                                                     │
  │  submit_response({                                  │
  │    content: "revised text...",                       │
  │    response_type: "refinement" | "answer" |         │
  │                   "generation"                      │
  │  })                                                 │
  │                                                     │
  │  AI self-classifies its response:                   │
  │  • refinement → user selected text + asked to edit  │
  │  • answer → user asked a question (no edit)         │
  │  • generation → user asked to create new content    │
  └──────────────────────┬──────────────────────────────┘
                         │
                         v
  ┌─────────────────────────────────────────────────────┐
  │  FRONTEND RESPONSE                                  │
  │                                                     │
  │  if response_type = "refinement" or "generation":   │
  │    → Show "Accept & Replace" bar                    │
  │    → User can Accept (patches section via API)      │
  │    → Or Iterate (continue chatting)                 │
  │                                                     │
  │  if response_type = "answer":                       │
  │    → Display response as chat message               │
  │    → No accept bar (informational only)             │
  └─────────────────────────────────────────────────────┘
```

---

### 3. Enron Data Preprocessing Pipeline

```
  ┌──────────────────────────────────────────┐
  │  Kaggle Enron Email Dataset              │
  │  517,401 emails  •  375 MB CSV           │
  │  Format: RFC 822 (headers + body)        │
  └──────────────────────┬───────────────────┘
                         │
                    STREAMING
                  (5000 emails/batch,
                  never loads full CSV)
                         │
                         v
  ┌─────────────────────────────────────────────────────────────┐
  │  TIER 0: PARSING & DEDUPLICATION          enron_loader.py  │
  │                                                            │
  │  • Parse RFC 822 headers (From, To, Subject, Date)         │
  │  • Extract body text                                       │
  │  • Extract folder path (inbox, sent, deleted_items...)     │
  │  • Deduplicate by: normalized_subject + sender + date      │
  └──────────────────────┬──────────────────────────────────────┘
                         │
                         v
  ┌─────────────────────────────────────────────────────────────┐
  │  PHASE 1: AUTO-DISCOVER PROJECTS         eda_discover.py   │
  │                                                            │
  │  Purpose: Find project threads in 500K emails              │
  │                                                            │
  │  Filters applied:                                          │
  │  ├─ Skip junk folders (deleted_items, spam, calendar)      │
  │  ├─ Normalize subjects (strip Re:/FW: prefixes)            │
  │  ├─ Drop generic subjects ("hi", "lunch", "fyi", etc.)    │
  │  ├─ Drop newsletters (regex: "daily report", etc.)         │
  │  └─ Group remaining by normalized subject                  │
  │                                                            │
  │  Scoring formula:                                          │
  │  score = email_count × capped_senders × log2(avg_words)   │
  │          × project_indicator_bonus (10x)                   │
  │          × brd_signal_density_bonus (1-4x)                 │
  │          × blast_email_penalty (0.5x)                      │
  │                                                            │
  │  Output: Top N project threads ranked by score             │
  │  + Keywords (TF, no IDF) + 5 seed queries per project      │
  └──────────────────────┬──────────────────────────────────────┘
                         │
                         v
  ┌─────────────────────────────────────────────────────────────┐
  │  TIER 1: HEURISTIC FILTER (free, instant)                  │
  │                                            heuristic_filter │
  │  Positive signals:                                         │
  │  ├─ +0.30  BRD keywords in body (requirements, scope...)   │
  │  ├─ +0.20  BRD keywords in subject                        │
  │  ├─ +0.15  Targeted (1-10 recipients)                     │
  │  ├─ +0.15  Substantial body (50-500 words)                │
  │  ├─ +0.10  Action language ("please review", "?")         │
  │  └─ +0.10  Good folder (inbox, sent, projects)            │
  │                                                            │
  │  Negative signals:                                         │
  │  ├─ -0.30  Noise keywords (lunch, birthday, fantasy)      │
  │  ├─ -0.20  Noise subject patterns (FW: FW: FW:)           │
  │  ├─ -0.20  Mass email (20+ recipients)                    │
  │  ├─ -0.15  Noise folder (deleted_items, spam)             │
  │  └─ -0.10  Trivially short (<15 words)                    │
  │                                                            │
  │  Result: 517K → ~78K emails (15% pass rate)                │
  └──────────────────────┬──────────────────────────────────────┘
                         │
                         v
  ┌─────────────────────────────────────────────────────────────┐
  │  TIER 2: EMBEDDING FILTER (semantic)    embedding_filter   │
  │                                                            │
  │  1. Embed 10 BRD seed queries via Gemini text-embedding-004│
  │  2. Embed each email (batched, 100/batch, 5 concurrent)   │
  │  3. Cosine similarity: each email vs all seed queries      │
  │  4. Combined score: 0.3 × heuristic + 0.7 × embedding     │
  │  5. Rank by combined score, take top_k                     │
  │                                                            │
  │  Cost: ~$0.10 for 50K emails                               │
  │  Speed: ~5 minutes (batching + concurrency)                │
  │                                                            │
  │  Result: 78K → 2K emails (top 2.5%)                        │
  └──────────────────────┬──────────────────────────────────────┘
                         │
                         v
  ┌─────────────────────────────────────────────────────────────┐
  │  TIER 3: EXPORT & UPLOAD                 bulk_importer     │
  │                                                            │
  │  1. Export filtered emails as .txt files                   │
  │  2. Login to Sybil API (JWT auth)                          │
  │  3. Create project                                         │
  │  4. Upload in batches (5 files/batch, 2s delay)            │
  │  5. Backend: Chomper parses → Gemini classifies → store    │
  │                                                            │
  │  Result: Curated project in Sybil, ready for BRD gen       │
  └────────────────────────────────────────────────────────────┘
```

**ML Techniques Used:**

| Technique | Location | Purpose |
|---|---|---|
| Gemini text-embedding-004 (768-dim) | embedding_filter.py | Semantic email representation |
| Cosine similarity | embedding_filter.py | Relevance scoring vs seed queries |
| Term frequency (TF, no IDF) | eda_discover.py | Keyword extraction |
| Weighted feature scoring | heuristic_filter.py | Rule-based relevance |
| Hybrid ranking | curate_project.py | 0.3 heuristic + 0.7 embedding |

> **Note:** No custom models were trained. The pipeline uses pre-trained Gemini embeddings combined with hand-crafted heuristic features. This is a standard NLP approach when labeled training data is unavailable.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, shadcn/ui, Tailwind CSS, Zustand, Framer Motion |
| Backend | FastAPI, Python 3.11, Pydantic v2 |
| AI Engine | Google Gemini 2.5 Pro (agentic tool-calling, structured output) |
| Embeddings | Gemini text-embedding-004 (768-dim) |
| Database | Google Cloud Firestore (NoSQL) |
| File Storage | Google Cloud Storage |
| File Parsing | Chomper (36+ formats: PDF, DOCX, PPTX, XLSX, CSV, HTML, TXT) |
| Authentication | JWT (HS256, bcrypt password hashing) |
| Infrastructure | Terraform, Cloud Run, Artifact Registry, Cloud Build |
| Frontend Hosting | Vercel (CDN + Edge) |
| Security | 3-layer prompt injection defense (validation + regex + defensive prompts) |

---

## Key Features

- **Multi-format document upload** — PDF, DOCX, TXT, CSV, PPTX, HTML with drag-and-drop
- **Agentic BRD generation** — AI reads all documents autonomously, generates 13-section BRD with citations
- **Natural language editing** — Select any text, describe changes in plain English, accept or iterate
- **Conflict detection** — Automatically finds contradictions across source documents
- **AI-assisted conflict resolution** — One-click "Resolve with AI" generates fixes
- **Citation tracking** — Every requirement links back to its source document and quote
- **Unified AI chat** — Ask questions, refine text, or generate new content from one chat panel
- **Sentiment analysis** — Stakeholder sentiment extracted from communications
- **Real-time progress** — Polling-based generation progress with stage indicators
- **Two-step deletion** — Preview what will be deleted before confirming (projects & documents)
- **Domain-agnostic** — Works for any industry (tech, healthcare, finance, construction)

---

## How It Works

### Document Processing Pipeline

```
Upload files  →  Cloud Storage  →  Chomper Parser  →  Gemini Classification
                                        │                      │
                                        v                      v
                                  Parsed text           Document type,
                                  + metadata            summary, tags,
                                        │               topics, entities
                                        v
                                  Firestore (documents collection)
                                  Cloud Storage (parsed text)
```

1. **Upload**: Files go to Cloud Storage (original preserved)
2. **Parse**: Chomper extracts text from 36+ formats (PDF, DOCX, etc.)
3. **Classify**: Gemini determines document type with confidence score
4. **Metadata**: Gemini generates summary, tags, topic relevance, key entities, sentiment
5. **Store**: Parsed text + AI metadata stored for BRD generation

### BRD Generation

The AI agent operates in a **fully agentic loop** — it decides what to read, what to search, and when to write each section. No Python code orchestrates the section order; the AI plans its own workflow.

1. **Discovery**: Agent lists documents, reads AI metadata summaries
2. **Deep Read**: Agent reads full document text (not chunked — no RAG context loss)
3. **Cross-Reference**: Agent searches by topic and content type across documents
4. **Section Writing**: Agent writes 13 BRD sections with inline citations
5. **Analysis**: Agent detects conflicts and analyzes stakeholder sentiment
6. **Assembly**: Backend collects submitted sections into complete BRD

### Natural Language Editing

Users can edit any BRD section using natural language:

1. **Select text** in the BRD viewer
2. **Describe the change** in the chat panel ("make this more concise", "add acceptance criteria")
3. **AI generates revision** using document context + conversation history
4. **Accept & Replace** patches the section via API, or continue iterating

The AI self-classifies its response as `refinement`, `answer`, or `generation` — the UI adapts accordingly (showing "Accept" bar only when there's content to apply).

---

## Enron Preprocessing — Deep Dive

The preprocessing pipeline transforms 500K raw Enron emails into curated, BRD-relevant project datasets. It was built to demonstrate the platform's ability to handle real-world, noisy communication data.

### Why Heuristics + Embeddings (Not Pure ML)?

1. **No labeled data** — We had no "this email is BRD-relevant" labels to train a classifier
2. **Cost efficiency** — Heuristics are free; embeddings cost ~$0.10 for 50K emails; a fine-tuned model would cost orders of magnitude more
3. **Interpretability** — Every filtering decision can be traced to specific rules and scores
4. **Speed** — Full pipeline runs in ~10 minutes on 500K emails

### The Multi-Tier Funnel

```
517,401 emails (100%)
    │
    ├── Tier 0: Parse + Deduplicate
    │
    ├── Tier 1: Heuristic Filter (free, instant)
    │   → 78,320 emails (15.1%)
    │
    ├── Tier 2: Embedding Filter (~$0.10, ~5 min)
    │   → 2,000 emails (0.4%)
    │
    └── Tier 3: Upload to Sybil → Full AI processing
        → Curated project dataset
```

### What's Hardcoded and Why

| Component | Hardcoded Items | Purpose |
|---|---|---|
| Junk folders (9) | deleted_items, spam, calendar... | Skip obviously irrelevant emails |
| Generic subjects (50+) | "hi", "lunch", "meeting", "fyi"... | Filter social/admin chatter |
| Newsletter patterns (12) | "daily report", "press release"... | Filter automated mass-sends |
| BRD keywords (47) | "requirements", "stakeholder"... | Boost project-relevant content |
| Noise patterns (12) | "out of office", "FW: FW:"... | Penalize noise |
| Scoring weights | 0.30, 0.20, 0.15... | Balance signal vs noise factors |

**This is standard feature engineering** — the same approach used in production NLP systems before fine-tuned models became common. The keyword lists encode domain knowledge about what makes an email relevant to BRD generation.

### Key Design Decisions

- **Streaming**: CSV is read in 5000-row batches — never loads 375MB into memory
- **Parallel parsing**: `multiprocessing.Pool` for CPU-bound RFC 822 parsing
- **Full text, not RAG**: Agent reads complete documents (no chunking = no context loss)
- **Hybrid scoring**: `0.3 × heuristic + 0.7 × embedding` — heuristics catch obvious signals, embeddings catch semantic relevance
- **Seed queries**: 10 BRD-specific queries drive the embedding similarity search, plus 5 auto-generated per discovered project

---

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

### 3. Enron Preprocessing (Optional)

```bash
# Download Enron dataset from Kaggle first
# https://www.kaggle.com/datasets/wcukierski/enron-email-dataset

# Full pipeline (heuristic + embedding + upload)
python -m backend.preprocessing \
    --enron-csv emails.csv \
    --top-k 2000 \
    --upload \
    --project-name "Enron Trading Analysis"

# Quick test (heuristic only, no API key needed)
python -m backend.preprocessing \
    --enron-csv emails.csv \
    --skip-embeddings \
    --top-k 500
```

---

## Deployment

### Backend (Cloud Run)

```bash
./deploy.sh    # Builds image, pushes to Artifact Registry, deploys via Terraform
```

Requires: `gcloud` CLI authenticated, Terraform installed, `infra/terraform.tfvars` populated.

### Frontend (Vercel)

1. Import repo on Vercel, set root directory to `frontend`
2. Add env var: `NEXT_PUBLIC_API_URL` = Cloud Run URL
3. Deploy

After frontend deploy, add Vercel URL to `allowed_origins` in `infra/terraform.tfvars` and run `terraform apply` to update CORS.

---

## Sample Documents

Includes 33 realistic sample documents across 3 projects:

- **E-commerce Checkout Redesign** (13 files) — budget conflicts, stakeholder disagreements
- **Mobile Authentication** (10 files) — timeline slips, technical blockers
- **Internal Dashboard** (10 files) — conflicting requirements, scope creep

---

## Team

- **Vedansh** - Full Stack Developer
- **Vanshika** - Full Stack Developer

Built for GDG Hackathon 2026
