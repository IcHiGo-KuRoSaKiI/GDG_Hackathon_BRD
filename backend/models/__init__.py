"""
Data models module exports.
Provides easy access to all Pydantic models.
"""
from .project import Project, ProjectCreate, ProjectUpdate, ProjectResponse
from .document import (
    Document,
    DocumentStatus,
    DocumentType,
    TopicRelevance,
    ContentIndicators,
    KeyEntities,
    StakeholderSentiment,
    AIMetadata,
    ChomperMetadata,
    Chunk
)
from .brd import (
    BRD,
    BRDSection,
    Citation,
    Conflict,
    Sentiment,
    BRDGenerateRequest,
    UpdateBRDRequest,
    UpdateBRDSectionRequest,
    UpdateConflictStatusRequest,
    ConflictStatusEnum,
    # Text refinement models
    RefineTextRequest,
    RefineTextResponse,
    TextRefinementMode,
    BRDSectionEnum,
    SimpleRefinementResult,
    AgenticGenerationResult,
    # Unified chat models
    ResponseType,
    ChatRequest,
    ChatResponse
)
from .user import (
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    AuthToken
)
from .ai_responses import (
    DocumentClassificationResponse,
    SentimentAnalysisResponse,
    MetadataGenerationResponse,
    RequirementResponse,
    RequirementsExtractionResponse,
    ConflictDetectionResponse,
    BRDSectionResponse,
    AgentReasoningResponse
)
from .deletion import (
    DeleteScope,
    DeleteStatus,
    DeletePreview,
    DeletionProgress,
    DeleteJob,
    DeleteConfirmRequest,
    DeleteResponse
)

__all__ = [
    # Project models
    "Project",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    # Document models
    "Document",
    "DocumentStatus",
    "DocumentType",
    "TopicRelevance",
    "ContentIndicators",
    "KeyEntities",
    "StakeholderSentiment",
    "AIMetadata",
    "ChomperMetadata",
    "Chunk",
    # BRD models
    "BRD",
    "BRDSection",
    "Citation",
    "Conflict",
    "Sentiment",
    "BRDGenerateRequest",
    "UpdateBRDRequest",
    "UpdateBRDSectionRequest",
    "UpdateConflictStatusRequest",
    "ConflictStatusEnum",
    # Text refinement
    "RefineTextRequest",
    "RefineTextResponse",
    "TextRefinementMode",
    "BRDSectionEnum",
    "SimpleRefinementResult",
    "AgenticGenerationResult",
    # Unified chat
    "ResponseType",
    "ChatRequest",
    "ChatResponse",
    # User models
    "User",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "AuthToken",
    # AI Response models
    "DocumentClassificationResponse",
    "SentimentAnalysisResponse",
    "MetadataGenerationResponse",
    "RequirementResponse",
    "RequirementsExtractionResponse",
    "ConflictDetectionResponse",
    "BRDSectionResponse",
    "AgentReasoningResponse",
    # Deletion models
    "DeleteScope",
    "DeleteStatus",
    "DeletePreview",
    "DeletionProgress",
    "DeleteJob",
    "DeleteConfirmRequest",
    "DeleteResponse"
]
