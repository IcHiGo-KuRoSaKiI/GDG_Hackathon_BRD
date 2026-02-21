"""
Data models module exports.
Provides easy access to all Pydantic models.
"""
from .project import Project, ProjectCreate, ProjectResponse
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
    BRDGenerateRequest
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
    ConflictResponse,
    ConflictDetectionResponse,
    BRDSectionResponse,
    AgentReasoningResponse
)

__all__ = [
    # Project models
    "Project",
    "ProjectCreate",
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
    "ConflictResponse",
    "ConflictDetectionResponse",
    "BRDSectionResponse",
    "AgentReasoningResponse"
]
