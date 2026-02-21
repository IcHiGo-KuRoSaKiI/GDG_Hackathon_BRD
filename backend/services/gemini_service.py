"""
Gemini AI service via LiteLLM.
All AI operations using Pydantic validation after generation.
No response_format parameter - Gemini doesn't support it.
"""
import logging
from typing import List
from ..config import litellm_router
from ..utils import prompts
from ..models import (
    AIMetadata,
    DocumentClassificationResponse,
    SentimentAnalysisResponse,
    MetadataGenerationResponse,
    RequirementsExtractionResponse,
    ConflictDetectionResponse,
    BRDSectionResponse,
    AgentReasoningResponse,
    TopicRelevance,
    ContentIndicators,
    KeyEntities,
    StakeholderSentiment
)

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for Gemini AI operations via LiteLLM."""

    def __init__(self):
        """Initialize Gemini service with LiteLLM router."""
        self.router = litellm_router

    async def classify_document(
        self,
        filename: str,
        content_preview: str
    ) -> DocumentClassificationResponse:
        """Classify document type."""
        prompt = prompts.format(
            "document_classification",
            filename=filename,
            content_preview=content_preview
        )

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response using Pydantic
            result = DocumentClassificationResponse.model_validate_json(
                response.choices[0].message.content
            )
            logger.info(f"Classified {filename} as {result.document_type}")
            return result

        except Exception as e:
            logger.error(f"Document classification failed: {e}", exc_info=True)
            return DocumentClassificationResponse(
                document_type="other",
                confidence=0.5,
                reasoning="Classification failed"
            )

    async def generate_metadata(self, doc_text: str) -> AIMetadata:
        """Generate comprehensive metadata."""
        prompt = prompts.format("metadata_generation", doc_text=doc_text)

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}]
            )

            result = MetadataGenerationResponse.model_validate_json(
                response.choices[0].message.content
            )

            # Convert to AIMetadata model
            return AIMetadata(
                document_type="",
                confidence=0.0,
                summary=result.summary,
                tags=result.tags,
                topics=TopicRelevance(**result.topics),
                contains=ContentIndicators(**result.contains),
                key_entities=KeyEntities(**result.key_entities),
                sentiment=StakeholderSentiment(
                    overall=result.sentiment.get("overall", "neutral"),
                    stakeholder_sentiment=result.sentiment.get("stakeholder_sentiment", {})
                )
            )

        except Exception as e:
            logger.error(f"Metadata generation failed: {e}", exc_info=True)
            raise Exception(f"AI generation failed: {str(e)}")

    async def extract_requirements(self, doc_text: str) -> List[dict]:
        """Extract requirements."""
        prompt = prompts.format("requirement_extraction", doc_text=doc_text)

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}]
            )

            result = RequirementsExtractionResponse.model_validate_json(
                response.choices[0].message.content
            )

            logger.info(f"Extracted {len(result.requirements)} requirements")
            return [req.model_dump() for req in result.requirements]

        except Exception as e:
            logger.error(f"Requirements extraction failed: {e}", exc_info=True)
            return []

    async def detect_conflicts(self, requirements_json: str) -> List[dict]:
        """Detect conflicts in requirements."""
        prompt = prompts.format("conflict_detection", requirements_json=requirements_json)

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}]
            )

            result = ConflictDetectionResponse.model_validate_json(
                response.choices[0].message.content
            )

            logger.info(f"Detected {len(result.conflicts)} conflicts")
            return [conflict.model_dump() for conflict in result.conflicts]

        except Exception as e:
            logger.error(f"Conflict detection failed: {e}", exc_info=True)
            return []

    async def analyze_sentiment(
        self,
        doc_text: str,
        stakeholders: str
    ) -> dict:
        """Analyze sentiment."""
        prompt = prompts.format(
            "sentiment_analysis",
            doc_text=doc_text,
            stakeholders_list=stakeholders
        )

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}]
            )

            result = SentimentAnalysisResponse.model_validate_json(
                response.choices[0].message.content
            )

            return result.model_dump()

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}", exc_info=True)
            return {"overall": "neutral", "stakeholder_sentiment": {}}

    async def generate_brd_section(
        self,
        section_name: str,
        context: dict
    ) -> dict:
        """Generate BRD section."""
        prompt_key = f"brd_section_{section_name}"
        prompt = prompts.format(prompt_key, **context)

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}]
            )

            result = BRDSectionResponse.model_validate_json(
                response.choices[0].message.content
            )

            logger.info(f"Generated {section_name} section")
            return result.model_dump()

        except Exception as e:
            logger.error(f"BRD section generation failed for {section_name}: {e}", exc_info=True)
            return {
                "content": f"# {section_name.replace('_', ' ').title()}\n\nGeneration failed.",
                "citations": []
            }


# Global service instance
gemini_service = GeminiService()
