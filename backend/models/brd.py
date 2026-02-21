"""
BRD (Business Requirements Document) data models.
Models for generated BRDs with citations and metadata.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class Citation(BaseModel):
    """Source reference with exact quote."""
    doc_id: str
    chunk_id: str
    filename: str
    quote: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class BRDSection(BaseModel):
    """BRD section with content and citations."""
    title: str
    content: str
    citations: List[Citation] = Field(default_factory=list)
    subsections: Optional[Dict[str, str]] = None  # For structured sections


class Conflict(BaseModel):
    """Detected requirement conflict."""
    conflict_type: str  # "budget", "timeline", "technical", "scope", etc.
    description: str
    affected_requirements: List[str]
    severity: str = Field(..., pattern="^(high|medium|low)$")
    sources: List[str]  # doc_ids


class Sentiment(BaseModel):
    """Overall sentiment analysis."""
    overall_sentiment: str = Field(..., pattern="^(positive|neutral|negative|mixed|concerned)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    stakeholder_breakdown: Dict[str, str] = Field(default_factory=dict)  # name -> sentiment
    key_concerns: List[str] = Field(default_factory=list)


class BRD(BaseModel):
    """Complete Business Requirements Document."""
    brd_id: str
    project_id: str

    # Metadata
    generated_at: datetime
    document_count: int  # Number of source documents used
    total_citations: int

    # BRD Sections (13 sections - industry standard)
    # Core sections (always present)
    executive_summary: BRDSection
    business_objectives: BRDSection
    stakeholders: BRDSection
    functional_requirements: BRDSection
    non_functional_requirements: BRDSection
    assumptions: BRDSection
    success_metrics: BRDSection
    timeline: BRDSection

    # Extended sections (optional for backward compatibility with existing BRDs)
    project_background: Optional[BRDSection] = None
    project_scope: Optional[BRDSection] = None
    dependencies: Optional[BRDSection] = None
    risks: Optional[BRDSection] = None
    cost_benefit: Optional[BRDSection] = None

    # Analysis
    conflicts: List[Conflict] = Field(default_factory=list)
    sentiment: Optional[Sentiment] = None

    # Agent metadata
    generation_metadata: Dict = Field(default_factory=dict)  # REACT trace info

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BRDGenerateRequest(BaseModel):
    """Request model for BRD generation."""
    project_id: str
    include_conflicts: bool = True
    include_sentiment: bool = True
    max_citations_per_section: int = Field(10, ge=1, le=50)
