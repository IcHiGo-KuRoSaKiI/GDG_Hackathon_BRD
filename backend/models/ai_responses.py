"""
Pydantic models for structured AI responses.
Used with LiteLLM's response_format for guaranteed JSON structure.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from .document import TopicRelevance, ContentIndicators, KeyEntities, StakeholderSentiment
from .brd import Citation, Conflict


class DocumentClassificationResponse(BaseModel):
    """Response model for document classification."""
    document_type: str = Field(description="Type of document: meeting_notes, email_thread, requirements_document, etc.")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    reasoning: str = Field(description="Explanation for the classification")


class SentimentData(BaseModel):
    """Sentiment data for a stakeholder."""
    sentiment: str = Field(description="Sentiment: positive, neutral, concerned, or negative")
    concerns: List[str] = Field(default_factory=list, description="List of concerns")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in assessment")


class SentimentAnalysisResponse(BaseModel):
    """Response model for sentiment analysis."""
    overall: str = Field(description="Overall sentiment across document")
    stakeholder_sentiment: Dict[str, SentimentData] = Field(
        default_factory=dict,
        description="Sentiment for each stakeholder"
    )


class MetadataGenerationResponse(BaseModel):
    """Response model for metadata generation."""
    summary: str = Field(description="2-3 sentence summary")
    tags: List[str] = Field(description="5-10 relevant keywords")
    topics: Dict[str, float] = Field(description="Topic relevance scores 0.0-1.0")
    contains: Dict[str, bool] = Field(description="Content indicators (what doc contains)")
    key_entities: Dict[str, List[str]] = Field(description="Stakeholders, features, decisions, dates, technologies")
    sentiment: Dict[str, Any] = Field(description="Overall and stakeholder sentiment")


class RequirementResponse(BaseModel):
    """Single requirement extracted from document."""
    req_id: str
    type: str = Field(description="functional or non_functional")
    category: str
    description: str
    priority: str = Field(description="high, medium, or low")
    source_quote: str
    stakeholder: str
    acceptance_criteria: List[str] = Field(default_factory=list)


class RequirementsExtractionResponse(BaseModel):
    """Response model for requirements extraction."""
    requirements: List[RequirementResponse]


class ConflictDetectionResponse(BaseModel):
    """Response model for conflict detection."""
    conflicts: List[Conflict] = Field(default_factory=list, description="List of detected conflicts")


class BRDSectionResponse(BaseModel):
    """Response model for BRD section generation."""
    content: str = Field(description="Markdown formatted content")
    citations: List[Citation] = Field(default_factory=list, description="List of citations")


class RelevantDocument(BaseModel):
    """Document relevance for agent reasoning."""
    doc_id: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    reasoning: str


class AgentReasoningResponse(BaseModel):
    """Response model for agent reasoning phase."""
    relevant_documents: List[RelevantDocument]
    reasoning: str = Field(description="Overall reasoning for document selection")
