"""
Document data models.
Complex nested models for document metadata and AI-generated insights.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Document classification types."""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    MEETING_NOTES = "meeting_notes"
    EMAIL = "email"
    SPECIFICATION = "specification"
    PROPOSAL = "proposal"
    FEEDBACK = "feedback"
    OTHER = "other"


class TopicRelevance(BaseModel):
    """Relevance scores for 10 key topics (0.0-1.0)."""
    authentication: float = Field(0.0, ge=0.0, le=1.0)
    authorization: float = Field(0.0, ge=0.0, le=1.0)
    data_storage: float = Field(0.0, ge=0.0, le=1.0)
    api_integration: float = Field(0.0, ge=0.0, le=1.0)
    ui_ux: float = Field(0.0, ge=0.0, le=1.0)
    performance: float = Field(0.0, ge=0.0, le=1.0)
    security: float = Field(0.0, ge=0.0, le=1.0)
    scalability: float = Field(0.0, ge=0.0, le=1.0)
    testing: float = Field(0.0, ge=0.0, le=1.0)
    deployment: float = Field(0.0, ge=0.0, le=1.0)


class ContentIndicators(BaseModel):
    """Boolean flags for content types present in document."""
    has_requirements: bool = False
    has_technical_details: bool = False
    has_decisions: bool = False
    has_timeline: bool = False
    has_budget: bool = False
    has_stakeholder_feedback: bool = False
    has_risks: bool = False
    has_success_metrics: bool = False


class KeyEntities(BaseModel):
    """Extracted entities from document."""
    stakeholders: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class StakeholderSentiment(BaseModel):
    """Sentiment analysis for a stakeholder."""
    name: str
    sentiment: str = Field(..., pattern="^(positive|neutral|negative|mixed)$")
    concerns: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class AIMetadata(BaseModel):
    """Aggregated AI-generated metadata for document."""
    # Classification
    document_type: DocumentType
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Content Analysis
    summary: str
    key_points: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    # Topic Relevance
    topic_relevance: TopicRelevance

    # Content Indicators
    content_indicators: ContentIndicators

    # Key Entities
    key_entities: KeyEntities

    # Sentiment (if stakeholders found)
    stakeholder_sentiments: List[StakeholderSentiment] = Field(default_factory=list)


class ChomperMetadata(BaseModel):
    """Metadata from Chomper document parser."""
    format: str  # pdf, docx, txt, etc.
    page_count: Optional[int] = None
    word_count: int
    char_count: int
    has_images: bool = False
    has_tables: bool = False


class Chunk(BaseModel):
    """Text chunk for citation tracking."""
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    word_count: int
    start_position: int  # Character position in full text
    end_position: int


class Document(BaseModel):
    """Complete document model with all metadata."""
    doc_id: str
    project_id: str
    filename: str
    original_filename: str

    # Storage paths
    storage_path: str  # Original file in Cloud Storage
    text_path: Optional[str] = None  # Parsed text in Cloud Storage

    # Processing status
    status: DocumentStatus
    error_message: Optional[str] = None

    # Timestamps
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    # Chomper metadata
    chomper_metadata: Optional[ChomperMetadata] = None

    # AI-generated metadata (populated after processing)
    ai_metadata: Optional[AIMetadata] = None

    # Chunks (stored separately, loaded on-demand)
    chunk_count: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
