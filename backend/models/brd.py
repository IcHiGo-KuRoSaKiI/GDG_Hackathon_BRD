"""
BRD (Business Requirements Document) data models.
Models for generated BRDs with citations and metadata.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


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


class ConflictStatusEnum(str, Enum):
    """Status of a detected conflict."""
    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"
    DEFERRED = "deferred"


class Conflict(BaseModel):
    """Detected requirement conflict."""
    conflict_type: str  # "budget", "timeline", "technical", "scope", etc.
    description: str
    affected_requirements: List[str]
    severity: str = Field(..., pattern="^(high|medium|low)$")
    sources: List[str]  # doc_ids
    status: ConflictStatusEnum = ConflictStatusEnum.OPEN
    resolution: Optional[str] = None  # AI resolution text when resolved


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


class UpdateConflictStatusRequest(BaseModel):
    """Request to update a conflict's status."""
    status: ConflictStatusEnum
    resolution: Optional[str] = None


class BRDGenerateRequest(BaseModel):
    """Request model for BRD generation."""
    project_id: str
    include_conflicts: bool = True
    include_sentiment: bool = True
    max_citations_per_section: int = Field(10, ge=1, le=50)


class UpdateBRDSectionRequest(BaseModel):
    """Request model for updating a single BRD section's content."""
    content: str = Field(..., min_length=1, max_length=50000)


# ============================================================================
# TEXT REFINEMENT MODELS (Inline BRD Editing)
# ============================================================================

class TextRefinementMode(str, Enum):
    """Mode for text refinement/generation."""
    SIMPLE = "simple"  # Direct refinement without document access
    AGENTIC = "agentic"  # Uses tools to access documents


class BRDSectionEnum(str, Enum):
    """All 13 standard BRD sections."""
    EXECUTIVE_SUMMARY = "executive_summary"
    BUSINESS_OBJECTIVES = "business_objectives"
    STAKEHOLDERS = "stakeholders"
    FUNCTIONAL_REQUIREMENTS = "functional_requirements"
    NON_FUNCTIONAL_REQUIREMENTS = "non_functional_requirements"
    ASSUMPTIONS = "assumptions"
    SUCCESS_METRICS = "success_metrics"
    TIMELINE = "timeline"
    PROJECT_BACKGROUND = "project_background"
    PROJECT_SCOPE = "project_scope"
    DEPENDENCIES = "dependencies"
    RISKS = "risks"
    COST_BENEFIT = "cost_benefit"


class RefineTextRequest(BaseModel):
    """
    Request to refine or generate text in a BRD section.

    Security: All user inputs are validated and sanitized before being
    passed to AI prompts to prevent prompt injection attacks.
    """
    selected_text: str = Field(
        "",
        max_length=5000,
        description="Text selected for refinement (can be empty for generation)"
    )
    instruction: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's instruction for refinement/generation"
    )
    section_context: BRDSectionEnum = Field(
        ...,
        description="Which BRD section this text belongs to"
    )
    mode: TextRefinementMode = Field(
        TextRefinementMode.SIMPLE,
        description="Refinement mode: simple (direct) or agentic (with document access)"
    )

    @validator("instruction")
    def validate_instruction_security(cls, v):
        """Validate instruction for prompt injection attacks."""
        # Import directly from module to avoid circular imports
        import sys
        import os
        import importlib.util

        # Get path to sanitization module
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        san_path = os.path.join(backend_dir, 'utils', 'sanitization.py')

        # Load module
        spec = importlib.util.spec_from_file_location("sanitization", san_path)
        san = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(san)

        return san.validate_refinement_instruction(v)

    @validator("selected_text")
    def validate_selected_text_security(cls, v):
        """Validate selected text for malicious content."""
        # Import directly from module to avoid circular imports
        import sys
        import os
        import importlib.util

        # Get path to sanitization module
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        san_path = os.path.join(backend_dir, 'utils', 'sanitization.py')

        # Load module
        spec = importlib.util.spec_from_file_location("sanitization", san_path)
        san = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(san)

        return san.validate_selected_text(v)


class RefineTextResponse(BaseModel):
    """Response containing refined/generated text."""
    original: str = Field(..., description="Original selected text")
    refined: str = Field(..., description="Refined/generated text")
    sources_used: List[str] = Field(
        default_factory=list,
        description="Document filenames used (agentic mode only)"
    )
    tool_calls_made: List[str] = Field(
        default_factory=list,
        description="Tools called during generation (agentic mode only)"
    )
    mode: TextRefinementMode = Field(..., description="Mode used for refinement")


# ============================================================================
# AI STRUCTURED OUTPUT MODELS (for Gemini response parsing)
# ============================================================================

class SimpleRefinementResult(BaseModel):
    """
    Structured output from Gemini for simple text refinement.
    Used with response_schema to ensure AI returns valid JSON.
    """
    refined_text: str = Field(
        ...,
        description="The refined text based on the user's instruction"
    )
    changes_made: str = Field(
        ...,
        description="Brief description of what was changed (1-2 sentences)"
    )


class AgenticGenerationResult(BaseModel):
    """
    Structured output from Gemini for agentic text generation.
    Used with response_schema after function calling completes.
    """
    generated_text: str = Field(
        ...,
        description="The generated or refined text"
    )
    sources_cited: List[str] = Field(
        default_factory=list,
        description="List of document filenames/IDs used as sources"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of how the text was generated (2-3 sentences)"
    )


# ============================================================================
# UNIFIED CHAT MODELS (Agentic chat with virtual tool classification)
# ============================================================================

class ResponseType(str, Enum):
    """AI-classified response type — drives frontend UI behavior."""
    REFINEMENT = "refinement"   # Text was refined → show Accept bar
    ANSWER = "answer"           # Question answered → no Accept bar
    GENERATION = "generation"   # New content generated → show Accept bar


class ChatRequest(BaseModel):
    """
    Request for unified agentic chat.

    Supports both text refinement (selected_text provided) and
    general questions (selected_text empty). The AI classifies its
    own response via the submit_response virtual tool.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's message or instruction"
    )
    section_context: BRDSectionEnum = Field(
        ...,
        description="Which BRD section the user is viewing"
    )
    selected_text: str = Field(
        "",
        max_length=5000,
        description="Text selected for refinement (empty for general chat)"
    )

    @validator("message")
    def validate_message_security(cls, v):
        """Validate message for prompt injection attacks."""
        import os
        import importlib.util
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        san_path = os.path.join(backend_dir, 'utils', 'sanitization.py')
        spec = importlib.util.spec_from_file_location("sanitization", san_path)
        san = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(san)
        return san.validate_refinement_instruction(v)

    @validator("selected_text")
    def validate_selected_text_chat(cls, v):
        """Validate selected text for malicious content."""
        if not v:
            return v
        import os
        import importlib.util
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        san_path = os.path.join(backend_dir, 'utils', 'sanitization.py')
        spec = importlib.util.spec_from_file_location("sanitization", san_path)
        san = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(san)
        return san.validate_selected_text(v)


class ChatResponse(BaseModel):
    """Response from unified agentic chat."""
    content: str = Field(..., description="The AI's response text (markdown)")
    response_type: ResponseType = Field(
        ...,
        description="AI-classified response type"
    )
    sources_used: List[str] = Field(
        default_factory=list,
        description="Document filenames accessed during generation"
    )
    tool_calls_made: List[str] = Field(
        default_factory=list,
        description="Tool names called during generation"
    )
