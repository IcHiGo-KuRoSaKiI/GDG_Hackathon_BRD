# BRD Generator - GDG Hackathon 2026

Automatically generate comprehensive Business Requirements Documents by ingesting data from multiple communication channels (emails, meeting transcripts, Slack messages, uploaded documents).

## 🎯 Problem Statement

Business requirements are scattered across emails, meetings, chat messages, and informal documents. Manually synthesizing this information into a coherent BRD is time-consuming and error-prone.

**Solution:** AI-powered platform that automatically extracts, filters, and synthesizes requirements from multiple sources into structured, professional BRDs.

## 🏗️ Architecture

**Monorepo Structure:**
```
brd-generator/
├── backend/          # FastAPI + Cloud Run
├── frontend/         # Next.js + Vercel
├── docs/            # Documentation & planning
└── sample-documents/ # Test data (3 realistic projects)
```

## 🚀 Tech Stack

### Backend
- **Framework:** FastAPI
- **Database:** Google Cloud Firestore
- **Storage:** Google Cloud Storage
- **AI/LLM:** Google Gemini 2.0 Flash
- **Document Parser:** Chomper (36+ formats)
- **Deployment:** Google Cloud Run

### Frontend
- **Framework:** Next.js 14 (App Router)
- **UI:** Shadcn UI + Tailwind CSS
- **Language:** TypeScript
- **Deployment:** Vercel

### Infrastructure
- **Cloud:** Google Cloud Platform
- **Project:** gdg-brd-generator-2026
- **Region:** us-central1

## 📋 Key Features

### MVP (Week 1-2)
- ✅ Upload documents (PDF, DOCX, TXT, CSV, PPTX)
- ✅ Auto-classification and metadata generation
- ✅ Gemini-powered requirement extraction
- ✅ BRD generation with 8 sections
- ✅ Citation tracking (click to view source)
- ✅ Conflict detection across sources
- ✅ Stakeholder sentiment analysis

### Architecture Highlights
- **Hybrid Chunking:** Chunks for citations only, full text for analysis
- **Rich AI Metadata:** Smart document selection (70% cost savings)
- **File-System Agent:** Outperforms traditional RAG (8.4 vs 6.4 accuracy)
- **Adapter Pattern:** Extensible (Gmail, Slack, Fireflies adapters ready)

## 🛠️ Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- GCP Account with billing
- Gemini API key

### Quick Start

1. **Clone Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/brd-generator.git
   cd brd-generator
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your credentials
   python main.py
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with backend URL
   npm run dev
   ```

4. **Access**
   - Backend: http://localhost:8080
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8080/docs

## 📚 Documentation

- [Problem Statement](docs/problem-statement/hackathon-challenge.md)
- [Final MVP Architecture](docs/plans/FINAL-MVP-ARCHITECTURE.md)
- [GCP Setup Guide](docs/setup/SETUP-COMPLETE.md)
- [GCP Commands Reference](docs/setup/gcp-commands-reference.md)
- [Setup Commands Log](docs/setup/SETUP-COMMANDS-LOG.md)

## 🚢 Deployment

### Backend (Cloud Run)
```bash
cd backend
gcloud run deploy brd-generator-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Frontend (Vercel)
```bash
cd frontend
vercel deploy --prod
```

## 👥 Team

- **Vedansh** - Full Stack Developer
- **Vanshika** - Full Stack Developer

## 📊 Sample Documents

The repository includes 33 realistic sample documents across 3 projects:
- **Set 1:** E-commerce Checkout Redesign (13 files)
- **Set 2:** Mobile Authentication (10 files)
- **Set 3:** Internal Dashboard (10 files)

These demonstrate messy real-world scenarios: budget conflicts, timeline slips, technical blockers, stakeholder disagreements, and conflicting requirements.

## 🎯 Implementation Timeline

**Week 1:** Core MVP (Upload, Parsing, Basic BRD Generation)
**Week 2:** Polish (Conflicts, Sentiment, UI/UX)

See [FINAL-MVP-ARCHITECTURE.md](docs/plans/FINAL-MVP-ARCHITECTURE.md) for detailed timeline.

## 📝 License

MIT License - Built for GDG Hackathon 2026

## 🙏 Acknowledgments

- Google Cloud Platform for infrastructure
- Google Gemini for AI capabilities
- GDG community for the hackathon

---

**Built with ❤️ for GDG Hackathon 2026**
