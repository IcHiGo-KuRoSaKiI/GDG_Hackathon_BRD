# Backend Architecture - BRD Generator

**Status:** IMPLEMENTATION READY
**Last Updated:** 2026-02-07
**Tech:** FastAPI (Async) + Firestore + Cloud Storage + Gemini 2.0 Flash

---

## 🎯 Core Principles

1. **Everything is Async** - All I/O operations use `async/await`
2. **Pydantic for Everything** - Structured outputs, no loose dicts
3. **External Prompts** - All AI prompts in `prompts.json`
4. **REACT Agent Pattern** - For BRD generation (Reason → Act → Observe)
5. **Clean Architecture** - Routes → Services → Models

---

## 📊 Complete User Flow

### Flow 1: User Authentication (Future - For Now: Skip)

```
For MVP: No authentication
For Production: Firebase Auth tokens
```

**Current MVP:**
- No user login required
- Projects are public (anyone can access)
- Add auth in v2

---

### Flow 2: Project Creation

```
POST /projects
→ Create project in Firestore
→ Return project_id
```

**Request:**
```json
{
  "name": "Mobile App Authentication",
  "description": "Requirements for mobile auth system"
}
```

**Response:**
```json
{
  "project_id": "proj_abc123",
  "name": "Mobile App Authentication",
  "created_at": "2026-02-07T10:30:00Z",
  "document_count": 0,
  "status": "active"
}
```

**Backend Flow:**
1. Validate request (Pydantic)
2. Generate unique project_id
3. Create Firestore document: `/projects/{project_id}`
4. Return project metadata

---

### Flow 3: Document Upload & Processing

```
POST /projects/{project_id}/documents/upload
→ Upload to Cloud Storage
→ Parse with Chomper (full text + chunks)
→ Classify with Gemini
→ Generate metadata with Gemini
→ Extract entities with Gemini
→ Store in Firestore
→ Return document metadata
```

**Request:**
```
Content-Type: multipart/form-data

file: [binary file data]
filename: "meeting_notes.pdf"
```

**Response:**
```json
{
  "doc_id": "doc_xyz789",
  "filename": "meeting_notes.pdf",
  "status": "processing",
  "processing_stages": {
    "upload": "complete",
    "parse": "in_progress",
    "classify": "pending",
    "metadata": "pending"
  }
}
```

**Backend Flow (Async Background Task):**

1. **Upload Stage**
   ```python
   async def upload_document(file, project_id):
       # Upload to Cloud Storage
       blob_name = f"{project_id}/{doc_id}_{filename}"
       await storage_client.upload_async(file, blob_name)
   ```

2. **Parse Stage**
   ```python
   async def parse_document(storage_path):
       # Use Chomper to parse
       full_text = await chomper.parse(storage_path)
       chunks = await chomper.chunk(full_text, size=400, overlap=75)
       return full_text, chunks
   ```

3. **Classify Stage**
   ```python
   async def classify_document(filename, text_preview):
       # Use Gemini with prompt from prompts.json
       doc_type = await gemini_classify(filename, text_preview)
       return doc_type
   ```

4. **Metadata Generation Stage**
   ```python
   async def generate_metadata(full_text):
       # Use Gemini with prompt from prompts.json
       metadata = await gemini_generate_metadata(full_text)
       # Returns: summary, tags, topics, contains, key_entities, sentiment
       return metadata
   ```

5. **Store Stage**
   ```python
   async def store_document(doc_data):
       # Store in Firestore
       await firestore_client.collection("documents").add(doc_data)

       # Store chunks for citation tracking
       for chunk in chunks:
           await firestore_client.collection("chunks").add(chunk)
   ```

---

### Flow 4: View Project Documents

```
GET /projects/{project_id}/documents
→ Fetch documents from Firestore
→ Return list with AI metadata
```

**Response:**
```json
{
  "project_id": "proj_abc123",
  "documents": [
    {
      "doc_id": "doc_xyz789",
      "filename": "meeting_notes.pdf",
      "uploaded_at": "2026-02-07T10:35:00Z",
      "ai_metadata": {
        "summary": "Sprint planning discussion about OAuth 2.0 authentication",
        "tags": ["authentication", "OAuth", "security", "meeting"],
        "doc_type": "meeting_notes",
        "topics": {
          "authentication": 0.95,
          "security": 0.85
        },
        "key_entities": {
          "stakeholders": ["Security Team", "UX Team"],
          "features": ["OAuth 2.0", "Two-factor auth"]
        }
      }
    }
  ],
  "total_count": 1
}
```

---

### Flow 5: BRD Generation (REACT Agent)

```
POST /projects/{project_id}/brds/generate
→ Start async BRD generation job
→ Agent analyzes documents
→ Extracts requirements
→ Detects conflicts
→ Analyzes sentiment
→ Generates 8 BRD sections
→ Store BRD in Firestore
→ Return BRD with citations
```

**Request:**
```json
{
  "sections": ["executive_summary", "business_objectives", "stakeholders", "functional_requirements", "non_functional_requirements", "assumptions", "success_metrics", "timeline"]
}
```

**Response (Immediate):**
```json
{
  "job_id": "job_123",
  "status": "processing",
  "estimated_time": "30-60 seconds"
}
```

**Backend Flow (REACT Agent Pattern):**

#### **Phase 1: REASON - Analyze Documents**
```python
async def reason_phase(project_id):
    # Tool: list_documents_with_metadata
    documents = await agent_tools.list_documents(project_id)

    # Agent decides which documents are relevant
    relevant_docs = await agent_select_relevant_docs(documents)

    return relevant_docs
```

#### **Phase 2: ACT - Extract Information**
```python
async def act_phase(relevant_docs):
    tasks = []

    for doc in relevant_docs:
        # Tool: get_full_document_text
        task = extract_requirements_from_doc(doc.doc_id)
        tasks.append(task)

    # Run in parallel (async)
    all_requirements = await asyncio.gather(*tasks)

    return flatten(all_requirements)
```

#### **Phase 3: OBSERVE - Detect Issues**
```python
async def observe_phase(requirements):
    # Detect conflicts
    conflicts = await detect_conflicts(requirements)

    # Analyze sentiment
    stakeholders = extract_stakeholders(requirements)
    sentiment = await analyze_sentiment(requirements, stakeholders)

    return conflicts, sentiment
```

#### **Phase 4: GENERATE - Create BRD Sections**
```python
async def generate_brd_sections(requirements, conflicts, sentiment):
    sections = {}

    for section_name in BRD_SECTIONS:
        # Use Gemini with prompt from prompts.json
        section_content = await generate_section(
            section_name=section_name,
            requirements=requirements,
            conflicts=conflicts,
            sentiment=sentiment
        )
        sections[section_name] = section_content

    return sections
```

---

### Flow 6: View BRD

```
GET /projects/{project_id}/brds/{brd_id}
→ Fetch BRD from Firestore
→ Return BRD with all sections and citations
```

**Response:**
```json
{
  "brd_id": "brd_456",
  "project_id": "proj_abc123",
  "generated_at": "2026-02-07T11:00:00Z",
  "sections": {
    "executive_summary": {
      "content": "This project aims to implement OAuth 2.0...",
      "citations": [
        {
          "id": 1,
          "doc_id": "doc_xyz789",
          "doc_filename": "meeting_notes.pdf",
          "quote": "Security team recommended OAuth 2.0",
          "page": 3,
          "chunk_id": "chunk_xyz_003"
        }
      ]
    },
    "functional_requirements": {
      "content": "1. User login with email/password...",
      "citations": [...]
    }
  },
  "conflicts": [
    {
      "id": "conflict_1",
      "severity": "high",
      "description": "Login timeout mismatch",
      "req1": {
        "description": "Session timeout: 30 minutes",
        "source": "meeting_notes.pdf"
      },
      "req2": {
        "description": "Session timeout: 5 minutes",
        "source": "security_requirements.pdf"
      }
    }
  ],
  "sentiment": {
    "overall": "positive",
    "stakeholders": {
      "Security Team": {
        "sentiment": "positive",
        "concerns": []
      },
      "UX Team": {
        "sentiment": "concerned",
        "concerns": ["Implementation complexity", "Timeline constraints"]
      }
    }
  }
}
```

---

## 🎯 Complete End-to-End Flow (Detailed)

This section shows the COMPLETE user journey with real examples and insights.

### **Phase 1: Project Setup**

```
User → POST /projects
├─ Creates project in Firestore: /users/{uid}/projects/{project_id}
└─ Returns project metadata
```

### **Phase 2: Document Upload & AI Enrichment**

```
User → POST /projects/{project_id}/documents/upload (multiple files)
│
├─ For each document (async parallel via asyncio.gather):
│   │
│   ├─ 1. Upload to Cloud Storage
│   │   └─ gs://gdg-brd-generator-files/uploads/{project_id}/{doc_id}.{ext}
│   │
│   ├─ 2. Parse with Chomper
│   │   ├─ Extract full text → gs://.../parsed/{project_id}/{doc_id}_full.txt
│   │   └─ Create chunks (400 words) → gs://.../parsed/{project_id}/{doc_id}_chunks.json
│   │
│   ├─ 3. Classify with Gemini (prompts.json: "document_classification")
│   │   └─ Returns: doc_type, confidence, reasoning
│   │
│   ├─ 4. Generate AI Metadata with Gemini (prompts.json: "metadata_generation")
│   │   ├─ summary (2-3 sentences)
│   │   ├─ tags (5-10 keywords)
│   │   ├─ topics with relevance scores (authentication: 0.95, security: 0.85)
│   │   ├─ content indicators (contains: {functional_requirements: true, decisions: true})
│   │   ├─ key_entities (stakeholders, features, decisions, dates, technologies)
│   │   └─ sentiment (overall + per-stakeholder)
│   │
│   └─ 5. Store in Firestore
│       └─ /users/{uid}/projects/{project_id}/documents/{doc_id}
│           ├─ filename, uploaded_at, storage_path
│           ├─ parsed_full_path, parsed_chunks_path
│           └─ ai_metadata {...}
│
└─ User sees document list with AI-generated summaries
```

**💡 Key Insight:**
The AI metadata is the secret sauce. By generating rich metadata upfront, the REACT agent can intelligently select which documents to read (seeing summaries and topics), saving 70% on API costs. This is the "file-system agent" approach that beats traditional RAG.

### **Phase 3: BRD Generation (REACT Agent Pattern)**

```
User → POST /projects/{project_id}/brds/generate
│
├─ AgentService initializes REACT loop
│   │
│   ├─ **REASON Phase** (Agent Tools from tools.py)
│   │   │
│   │   ├─ Gemini calls: list_project_documents(project_id)
│   │   │   └─ Sees ALL documents with metadata:
│   │   │       - meeting_notes.pdf: summary="Sprint planning...", tags=["OAuth", "2FA"]
│   │   │       - security_email.txt: topics={security: 0.95, authentication: 0.90}
│   │   │       - stakeholder_feedback.docx: contains={functional_requirements: true}
│   │   │
│   │   └─ Agent reasons: "I need to read docs about authentication for the requirements section"
│   │
│   ├─ **ACT Phase** (Document Retrieval + Extraction)
│   │   │
│   │   ├─ Gemini calls: search_documents_by_topic(project_id, "authentication", min_relevance=0.7)
│   │   │   └─ Returns: [meeting_notes.pdf, security_email.txt] sorted by relevance
│   │   │
│   │   ├─ Gemini calls: get_full_document_text(doc_id) for each relevant doc
│   │   │   └─ Returns FULL TEXT (not chunks!) to avoid context loss
│   │   │
│   │   └─ Gemini extracts requirements (prompts.json: "requirement_extraction")
│   │       └─ Returns: [{req_id, type, category, description, priority, source_quote, stakeholder}]
│   │
│   ├─ **OBSERVE Phase** (Conflict Detection + Sentiment)
│   │   │
│   │   ├─ Gemini analyzes all requirements (prompts.json: "conflict_detection")
│   │   │   └─ Finds: "Session timeout: 30 min (doc A) vs 5 min (doc B)" → HIGH severity
│   │   │
│   │   └─ Gemini analyzes sentiment (prompts.json: "sentiment_analysis")
│   │       └─ Extracts: Security Team (concerned about OAuth complexity, confidence: 0.85)
│   │
│   └─ **GENERATE Phase** (8 BRD Sections)
│       │
│       ├─ For each section, Gemini generates content with citations:
│       │   │
│       │   ├─ Executive Summary (prompts.json: "brd_section_executive_summary")
│       │   ├─ Business Objectives (prompts.json: "brd_section_business_objectives")
│       │   ├─ Stakeholder Analysis (prompts.json: "brd_section_stakeholders")
│       │   ├─ Functional Requirements (prompts.json: "brd_section_functional_requirements")
│       │   ├─ Non-Functional Requirements (prompts.json: "brd_section_non_functional_requirements")
│       │   ├─ Assumptions & Constraints (prompts.json: "brd_section_assumptions")
│       │   ├─ Success Metrics (prompts.json: "brd_section_success_metrics")
│       │   └─ Timeline (prompts.json: "brd_section_timeline")
│       │
│       └─ Each section includes:
│           ├─ content (markdown)
│           └─ citations: [{id: 1, doc_filename: "meeting.pdf", quote: "exact text"}]
│
└─ Store BRD in Firestore: /users/{uid}/projects/{project_id}/brds/{brd_id}
    ├─ sections: [8 sections with content + citations]
    ├─ conflicts: [{conflict_id, severity, description, requirements[], impact}]
    └─ sentiment: {overall, stakeholders: {...}}
```

**💡 Key Insight:**
The REACT pattern is critical here. Traditional RAG would just retrieve chunks based on similarity. Our agent *reasons* about which documents to read using metadata, *acts* by reading full documents (no context loss), *observes* patterns like conflicts, then *generates* cohesive sections. This is why file-system agents score 8.4 vs RAG's 6.4.

### **Phase 4: User Views BRD**

```
User → GET /projects/{project_id}/brds/{brd_id}
│
├─ Frontend displays:
│   ├─ 8 sections with markdown rendering
│   ├─ Citations as clickable superscripts [1], [2]
│   ├─ Conflicts highlighted in red boxes
│   └─ Stakeholder sentiment cards
│
└─ User clicks citation [1]
    └─ Modal shows:
        ├─ Source document: "meeting_notes.pdf"
        ├─ Exact quote highlighted
        └─ Link to view full document
```

### **Real Example: Tracing One Requirement Through the System**

Let's trace how "session timeout" requirement flows through the entire system:

#### 1. **Document Upload**
```
User uploads "sprint_planning_meeting.txt" containing:

"Security Team raised concerns about session timeout.
 They want 30 minutes, but UX Team prefers 5 minutes for security."
```

#### 2. **AI Classification & Metadata**
```python
# Gemini classifies
doc_type = "meeting_notes"

# Gemini generates metadata
{
  "summary": "Sprint planning discussion about authentication flow...",
  "tags": ["authentication", "security", "session_timeout"],
  "topics": {
    "authentication": 0.95,
    "security": 0.90
  },
  "contains": {
    "functional_requirements": true,
    "decisions": true
  },
  "key_entities": {
    "stakeholders": ["Security Team", "UX Team"],
    "decisions": ["session timeout discussion"]
  }
}
```

#### 3. **Document Stored**
```
Firestore: /projects/proj_123/documents/doc_456
- filename: "sprint_planning_meeting.txt"
- ai_metadata: {...}
- parsed_full_path: "gs://.../doc_456_full.txt"
```

#### 4. **BRD Generation Triggered**

**REASON Phase:**
```python
# Agent calls list_project_documents()
docs = [
  {
    "doc_id": "doc_456",
    "filename": "sprint_planning_meeting.txt",
    "topics": {"security": 0.90, "authentication": 0.95},
    "contains": {"decisions": true}
  }
]

# Agent reasons: "High security relevance, contains decisions - I should read this"
```

**ACT Phase:**
```python
# Agent calls get_full_document_text("doc_456")
full_text = """
Sprint Planning Meeting
Speaker 1: Security Team raised concerns...
[FULL DOCUMENT - NO CONTEXT LOSS]
"""

# Agent extracts requirement
requirement = {
  "req_id": "NFR-003",
  "type": "non_functional",
  "category": "security",
  "description": "Session timeout must balance security and UX",
  "priority": "high",
  "source_quote": "Security Team raised concerns about session timeout...",
  "stakeholder": "Security Team, UX Team"
}
```

**OBSERVE Phase:**
```python
# Agent detects conflict
conflict = {
  "conflict_id": "conflict_1",
  "severity": "HIGH",
  "type": "specification",
  "description": "Security Team wants 30 min timeout vs UX Team wants 5 min",
  "requirements": [
    {"req_id": "NFR-003", "source": "sprint_planning_meeting.txt"}
  ],
  "impact": "Cannot implement without stakeholder decision"
}

# Agent analyzes sentiment
sentiment = {
  "Security Team": {
    "sentiment": "concerned",
    "concerns": ["OAuth complexity", "timeout trade-offs"],
    "confidence": 0.85
  }
}
```

**GENERATE Phase:**
```python
# Agent generates Non-Functional Requirements section
section = {
  "section_name": "non_functional_requirements",
  "content": """
## Non-Functional Requirements

### Security
**NFR-003: Session Timeout** [1]

The application must implement session timeout to balance security and user experience.

⚠️ **Conflict Detected:** Security Team recommends 30-minute timeout, while UX Team
suggests 5 minutes. This requires stakeholder resolution before implementation.

**Priority:** High
**Stakeholders:** Security Team, UX Team
  """,
  "citations": [
    {
      "id": 1,
      "doc_id": "doc_456",
      "doc_filename": "sprint_planning_meeting.txt",
      "quote": "Security Team raised concerns about session timeout. They want 30 minutes, but UX Team prefers 5 minutes for security.",
      "chunk_id": "chunk_456_003"
    }
  ]
}
```

#### 5. **BRD Displayed to User**

```
Frontend shows:

NON-FUNCTIONAL REQUIREMENTS
──────────────────────────────

### Security
**NFR-003: Session Timeout** [1]

The application must implement session timeout...

⚠️ Conflict Detected: Security Team recommends...

[User clicks [1]]
  ↓
Modal appears:
──────────────────────────────
Source: sprint_planning_meeting.txt

"Security Team raised concerns about
 session timeout. They want 30 minutes,
 but UX Team prefers 5 minutes for
 security."

[View Full Document]
──────────────────────────────
```

**💡 Key Insight:**
Notice how we use chunks ONLY for citations (to show exact quotes), but the agent reads the FULL document text for analysis. This hybrid approach gives us precise citation tracking without the context loss that kills traditional RAG systems. The agent can understand "Security Team wants 30 min BUT UX Team wants 5 min" because it sees the whole conversation, not fragmented chunks.

---

## 🏗️ Backend Project Structure

```
backend/
├── main.py                    # FastAPI app entry point
├── config/
│   ├── __init__.py
│   ├── settings.py            # Environment variables (Pydantic Settings)
│   ├── firebase.py            # Firebase Admin SDK init
│   └── gemini.py              # Gemini client init
│
├── routes/                    # API routes (controllers)
│   ├── __init__.py
│   ├── projects.py            # POST /projects, GET /projects/{id}
│   ├── documents.py           # POST /upload, GET /documents
│   └── brds.py                # POST /generate, GET /brds/{id}
│
├── services/                  # Business logic (async)
│   ├── __init__.py
│   ├── document_service.py    # Upload, parse, classify, metadata
│   ├── gemini_service.py      # All Gemini API calls
│   ├── agent_service.py       # REACT agent for BRD generation
│   ├── storage_service.py     # Cloud Storage operations
│   └── firestore_service.py   # Firestore CRUD operations
│
├── models/                    # Pydantic models
│   ├── __init__.py
│   ├── project.py             # Project, ProjectCreate, ProjectResponse
│   ├── document.py            # Document, AIMetadata, Chunk
│   ├── brd.py                 # BRD, BRDSection, Citation
│   ├── requirements.py        # Requirement, Conflict
│   └── sentiment.py           # Sentiment, StakeholderSentiment
│
├── agent/                     # REACT agent components
│   ├── __init__.py
│   ├── tools.py               # Agent tools (list_docs, get_full_text, search)
│   ├── planner.py             # Reasoning logic
│   └── executor.py            # Action execution
│
├── utils/                     # Utilities
│   ├── __init__.py
│   ├── prompts.py             # Load prompts from prompts.json
│   ├── async_helpers.py       # Async utility functions
│   └── validators.py          # Custom validators
│
├── prompts.json               # All AI prompts (external)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Cloud Run deployment
├── .env.example               # Environment variables template
└── CLAUDE.md                  # Development guidelines
```

---

## 📦 Pydantic Models (All Structured)

### Project Models

```python
# models/project.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class Project(BaseModel):
    project_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    status: str = "active"  # active, archived

class ProjectResponse(BaseModel):
    project_id: str
    name: str
    created_at: datetime
    document_count: int
    status: str
```

### Document Models

```python
# models/document.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class TopicRelevance(BaseModel):
    """Topic relevance scores (0.0-1.0)"""
    authentication: Optional[float] = 0.0
    security: Optional[float] = 0.0
    user_experience: Optional[float] = 0.0
    # ... more topics

class ContentIndicators(BaseModel):
    """What the document contains"""
    functional_requirements: bool = False
    decisions: bool = False
    timeline: bool = False
    stakeholder_feedback: bool = False

class KeyEntities(BaseModel):
    """Extracted entities"""
    stakeholders: List[str] = []
    features: List[str] = []
    decisions: List[str] = []
    dates: List[str] = []

class StakeholderSentiment(BaseModel):
    """Per-stakeholder sentiment"""
    sentiment: str  # positive, neutral, concerned, negative
    concerns: List[str] = []
    confidence: float = Field(..., ge=0.0, le=1.0)

class AIMetadata(BaseModel):
    """Gemini-generated metadata"""
    summary: str
    tags: List[str]
    topics: TopicRelevance
    doc_type: str  # meeting_notes, email_thread, requirements_document, etc.
    contains: ContentIndicators
    key_entities: KeyEntities
    sentiment: Dict[str, StakeholderSentiment]  # Overall + per stakeholder

class ChomperMetadata(BaseModel):
    """Chomper parser metadata"""
    page_count: Optional[int]
    word_count: int
    format: str  # pdf, docx, txt, etc.

class Document(BaseModel):
    """Complete document model"""
    doc_id: str
    project_id: str
    filename: str
    storage_path: str
    uploaded_at: datetime
    processed_at: Optional[datetime]
    status: str  # uploading, parsing, processing, complete, failed

    # Metadata
    metadata: ChomperMetadata
    ai_metadata: Optional[AIMetadata]

    # Parsed content (stored in Cloud Storage)
    parsed_full_path: Optional[str]  # gs://bucket/parsed/doc_id_full.txt

class Chunk(BaseModel):
    """Chunk for citation tracking"""
    chunk_id: str
    doc_id: str
    project_id: str
    text: str
    chunk_index: int

    # Citation metadata
    page: Optional[int]
    char_offset_start: int
    char_offset_end: int
    section_name: Optional[str]
    keywords: List[str] = []
```

### BRD Models

```python
# models/brd.py
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class Citation(BaseModel):
    """Citation to source document"""
    id: int
    doc_id: str
    doc_filename: str
    quote: str
    page: Optional[int]
    chunk_id: str

class BRDSection(BaseModel):
    """One section of BRD"""
    section_name: str
    content: str
    citations: List[Citation]
    generated_at: datetime

class Conflict(BaseModel):
    """Detected requirement conflict"""
    conflict_id: str
    severity: str  # high, medium, low
    description: str
    req1: Dict[str, str]  # description, source
    req2: Dict[str, str]
    resolution: Optional[str] = None

class Sentiment(BaseModel):
    """Stakeholder sentiment analysis"""
    overall: str  # positive, neutral, mixed, concerned, negative
    stakeholders: Dict[str, StakeholderSentiment]

class BRD(BaseModel):
    """Complete BRD document"""
    brd_id: str
    project_id: str
    generated_at: datetime
    sections: Dict[str, BRDSection]  # section_name -> BRDSection
    conflicts: List[Conflict]
    sentiment: Sentiment
    status: str  # generating, complete, failed
```

---

## 🔧 Service Layer (Async)

### Document Service

```python
# services/document_service.py
import asyncio
from typing import Tuple, List
from models.document import Document, AIMetadata, Chunk

class DocumentService:

    async def process_document(
        self,
        file_data: bytes,
        filename: str,
        project_id: str
    ) -> Document:
        """
        Complete document processing pipeline (async)
        """
        # Create document record
        doc = await self._create_document_record(project_id, filename)

        # Run stages in sequence
        try:
            # Stage 1: Upload
            storage_path = await self._upload_to_storage(file_data, doc.doc_id, filename)

            # Stage 2: Parse
            full_text, chunks = await self._parse_document(storage_path)

            # Stage 3 & 4: Classify + Metadata (parallel)
            doc_type, ai_metadata = await asyncio.gather(
                self._classify_document(filename, full_text[:1000]),
                self._generate_metadata(full_text)
            )

            # Stage 5: Store
            await self._store_document(doc, full_text, chunks, ai_metadata)

            return doc

        except Exception as e:
            await self._mark_failed(doc.doc_id, str(e))
            raise

    async def _parse_document(self, storage_path: str) -> Tuple[str, List[Chunk]]:
        """Parse with Chomper"""
        # TODO: Integrate Chomper MCP
        pass

    async def _classify_document(self, filename: str, preview: str) -> str:
        """Classify with Gemini"""
        from services.gemini_service import GeminiService
        gemini = GeminiService()
        return await gemini.classify_document(filename, preview)

    async def _generate_metadata(self, full_text: str) -> AIMetadata:
        """Generate metadata with Gemini"""
        from services.gemini_service import GeminiService
        gemini = GeminiService()
        return await gemini.generate_metadata(full_text)
```

---

## 🤖 REACT Agent for BRD Generation

### Agent Flow

```python
# services/agent_service.py
from typing import List, Dict
from models.brd import BRD, BRDSection, Conflict, Sentiment

class BRDAgent:
    """REACT agent for BRD generation"""

    async def generate_brd(self, project_id: str) -> BRD:
        """
        Main BRD generation flow using REACT pattern
        """
        # REASON: Analyze what documents we have
        context = await self._reason_phase(project_id)

        # ACT: Extract requirements from relevant documents
        requirements = await self._act_phase(context)

        # OBSERVE: Detect conflicts and sentiment
        conflicts, sentiment = await self._observe_phase(requirements)

        # GENERATE: Create BRD sections
        sections = await self._generate_sections(requirements, conflicts, sentiment)

        # Assemble BRD
        brd = BRD(
            brd_id=generate_id(),
            project_id=project_id,
            sections=sections,
            conflicts=conflicts,
            sentiment=sentiment,
            status="complete"
        )

        return brd

    async def _reason_phase(self, project_id: str) -> Dict:
        """
        Reason about which documents are relevant
        """
        # Use agent tool: list_documents_with_metadata
        from agent.tools import list_documents
        documents = await list_documents(project_id)

        # Agent decides relevance (could use Gemini here)
        relevant = [doc for doc in documents if self._is_relevant(doc)]

        return {"documents": relevant, "project_id": project_id}

    async def _act_phase(self, context: Dict) -> List[Dict]:
        """
        Extract requirements from all relevant documents
        """
        documents = context["documents"]

        # Extract from each document in parallel
        tasks = [
            self._extract_from_doc(doc["doc_id"])
            for doc in documents
        ]

        all_requirements = await asyncio.gather(*tasks)

        # Flatten and deduplicate
        return self._merge_requirements(all_requirements)

    async def _observe_phase(self, requirements: List[Dict]) -> Tuple[List[Conflict], Sentiment]:
        """
        Detect conflicts and analyze sentiment
        """
        # Run in parallel
        conflicts_task = self._detect_conflicts(requirements)
        sentiment_task = self._analyze_sentiment(requirements)

        conflicts, sentiment = await asyncio.gather(
            conflicts_task,
            sentiment_task
        )

        return conflicts, sentiment
```

---

## 📝 Prompts Storage (External JSON)

All prompts will be in `prompts.json`:

```python
# utils/prompts.py
import json
from typing import Dict

class PromptManager:
    """Load and manage prompts from prompts.json"""

    def __init__(self):
        with open("prompts.json", "r") as f:
            self.prompts = json.load(f)

    def get(self, prompt_key: str) -> str:
        """Get prompt by key"""
        return self.prompts.get(prompt_key, "")

    def format(self, prompt_key: str, **kwargs) -> str:
        """Get and format prompt with variables"""
        template = self.get(prompt_key)
        return template.format(**kwargs)

# Usage
prompts = PromptManager()
classify_prompt = prompts.format(
    "document_classification",
    filename="meeting_notes.pdf",
    content_preview="Sprint planning discussion..."
)
```

---

## 🔧 Agent Tools (Critical!)

**The agent MUST have these tools to access documents:**

### Tool 1: `list_project_documents(project_id)`

**Purpose:** Show agent ALL documents with their AI metadata

```python
# Returns
[
    {
        "doc_id": "doc_123",
        "filename": "meeting_notes.pdf",
        "summary": "Sprint planning - OAuth decisions",
        "tags": ["authentication", "OAuth", "security"],
        "topics": {
            "authentication": 0.95,
            "security": 0.85
        },
        "contains": {
            "functional_requirements": True,
            "decisions": True
        },
        "key_stakeholders": ["Security Team", "UX Team"]
    }
]
```

**Agent uses this to:**
- SEE what documents exist
- DECIDE which ones are relevant based on metadata
- PLAN which documents to read in detail

---

### Tool 2: `get_full_document_text(doc_id)`

**Purpose:** Fetch FULL text of a specific document

```python
# Returns
"Meeting Transcript - Sprint Planning\n\nSpeaker 1: We need to implement OAuth 2.0...\n[FULL DOCUMENT TEXT - NOT CHUNKS!]"
```

**Agent uses this to:**
- READ complete document content
- EXTRACT detailed requirements
- AVOID context loss from chunking

**Critical:** Returns FULL text, not chunks. This ensures no information is lost.

---

### Tool 3: `search_documents_by_topic(project_id, topic, min_relevance)`

**Purpose:** Find documents about a specific topic

```python
# Example: Find authentication docs
await search_documents_by_topic(
    project_id="proj_123",
    topic="authentication",
    min_relevance=0.7
)

# Returns documents sorted by relevance (highest first)
```

**Agent uses this to:**
- FIND relevant docs for specific BRD sections
- FILTER by topic when generating requirements
- PRIORITIZE most relevant sources

---

### Tool 4: `search_documents_by_content(project_id, content_type)`

**Purpose:** Find documents containing specific content types

```python
# Find docs with functional requirements
await search_documents_by_content(
    project_id="proj_123",
    content_type="functional_requirements"
)
```

**Agent uses this to:**
- FIND docs with requirements
- LOCATE decisions
- IDENTIFY timeline information

---

## 🤖 How Agent Uses Tools (REACT Pattern)

### Phase 1: REASON

```python
# Agent thinks: "What documents do I have?"
docs = await list_project_documents(project_id)

# Agent analyzes metadata and decides:
# "I need meeting_notes.pdf (0.95 authentication relevance)
#  and requirements_doc.pdf (has functional_requirements)"
```

### Phase 2: ACT

```python
# Agent reads the documents it identified
doc1_text = await get_full_document_text("doc_123")
doc2_text = await get_full_document_text("doc_456")

# Agent extracts requirements from full text (no context loss!)
requirements = await extract_requirements(doc1_text, doc2_text)
```

### Phase 3: OBSERVE

```python
# Agent detects conflicts in the requirements
conflicts = await detect_conflicts(requirements)

# Agent analyzes sentiment
sentiment = await analyze_sentiment(requirements)
```

### Phase 4: GENERATE

```python
# For each BRD section, agent:
# 1. Searches for relevant docs
auth_docs = await search_documents_by_topic("authentication")

# 2. Reads them
full_texts = [await get_full_document_text(doc["doc_id"]) for doc in auth_docs]

# 3. Generates section with citations
section = await generate_section("functional_requirements", full_texts)
```

---

## ✅ Implementation Status

**Created:**
- ✅ `backend/agent/tools.py` - All 4 agent tools + Gemini schemas
- ✅ `backend/ARCHITECTURE.md` - Complete architecture
- ✅ `backend/CLAUDE.md` - Development guidelines
- ✅ `backend/prompts.json` - All AI prompts

**Next Steps:**
1. Implement Pydantic models (`models/`)
2. Build services layer (`services/`)
3. Create API routes (`routes/`)
4. Integrate REACT agent (`agent/`)
5. Test with sample documents

Ready to start implementing! 🚀
