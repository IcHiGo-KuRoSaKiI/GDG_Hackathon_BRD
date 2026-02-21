# BRD Generator - Backend

FastAPI backend for the BRD Generator system.

## Tech Stack

- **Framework:** FastAPI
- **Database:** Google Cloud Firestore
- **Storage:** Google Cloud Storage
- **AI/LLM:** Google Gemini 2.0 Flash
- **Document Parsing:** Chomper (MCP)
- **Deployment:** Google Cloud Run

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
# Edit .env with your actual values
```

### 3. Run Development Server

```bash
python main.py
# Or
uvicorn main:app --reload
```

Server runs at: http://localhost:8080

## API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc

## Deployment to Cloud Run

```bash
# From backend directory
gcloud run deploy brd-generator-api \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 3600
```

## Project Structure

```
backend/
├── main.py              # FastAPI app entry point
├── requirements.txt     # Python dependencies
├── Dockerfile          # Cloud Run deployment
├── .env.example        # Environment variables template
├── config/             # Configuration (TODO)
├── routes/             # API routes (TODO)
├── services/           # Business logic (TODO)
├── models/             # Pydantic models (TODO)
└── utils/              # Utilities (TODO)
```

## API Endpoints (Planned)

- `GET /` - Health check
- `POST /projects` - Create project
- `POST /documents/upload` - Upload documents
- `GET /documents/{project_id}` - List documents
- `POST /brds/generate` - Generate BRD
- `GET /brds/{brd_id}` - Get BRD
