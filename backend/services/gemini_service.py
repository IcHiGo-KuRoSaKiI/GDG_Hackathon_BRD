"""
Gemini AI service via LiteLLM with structured outputs.
All AI operations using Pydantic models for guaranteed JSON structure.
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
    """Service for Gemini AI operations via LiteLLM with structured outputs."""

    def __init__(self):
        """Initialize Gemini service with LiteLLM router."""
        self.router = litellm_router

    async def classify_document(
        self,
        filename: str,
        content_preview: str
    ) -> DocumentClassificationResponse:
        """
        Classify document type using structured output.

        Args:
            filename: Original filename
            content_preview: First ~500 characters of document

        Returns:
            DocumentClassificationResponse with type, confidence, reasoning
        """
        prompt = prompts.format(
            "document_classification",
            filename=filename,
            content_preview=content_preview
        )

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_object",
                    "response_schema": DocumentClassificationResponse.model_json_schema()
                }
            )

            # Parse response using Pydantic
            result = DocumentClassificationResponse.model_validate_json(
                response.choices[0].message.content
            )
            logger.info(f"Classified {filename} as {result.document_type} (confidence: {result.confidence})")
            return result

        except Exception as e:
            logger.error(f"Document classification failed: {e}", exc_info=True)
            # Return default classification
            return DocumentClassificationResponse(
                document_type="other",
                confidence=0.5,
                reasoning="Classification failed, using default"
            )

    async def generate_metadata(self, doc_text: str) -> AIMetadata:
        """
        Generate comprehensive metadata using structured output.

        Args:
            doc_text: Full document text

        Returns:
            AIMetadata with all structured fields
        """
        prompt = prompts.format("metadata_generation", doc_text=doc_text)

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_object",
                    "response_schema": MetadataGenerationResponse.model_json_schema()
                }
            )

            # Parse response
            result = MetadataGenerationResponse.model_validate_json(
                response.choices[0].message.content
            )

            # Convert to AIMetadata model
            return AIMetadata(
                document_type="",  # Will be set by classify_document
                confidence=0.0,    # Will be set by classify_document
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
        """
        Extract requirements using structured output.

        Args:
            doc_text: Full document text

        Returns:
            List of requirement dictionaries
        """
        prompt = prompts.format("requirement_extraction", doc_text=doc_text)

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_object",
                    "response_schema": RequirementsExtractionResponse.model_json_schema()
                }
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
        """
        Detect conflicts in requirements using structured output.

        Args:
            requirements_json: JSON string of all requirements

        Returns:
            List of conflict dictionaries
        """
        prompt = prompts.format("conflict_detection", requirements_json=requirements_json)

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_object",
                    "response_schema": ConflictDetectionResponse.model_json_schema()
                }
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
        """
        Analyze sentiment using structured output.

        Args:
            doc_text: Full document text
            stakeholders_list: Comma-separated list of stakeholders

        Returns:
            Sentiment analysis dictionary
        """
        prompt = prompts.format(
            "sentiment_analysis",
            doc_text=doc_text,
            stakeholders_list=stakeholders
        )

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_object",
                    "response_schema": SentimentAnalysisResponse.model_json_schema()
                }
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
        """
        Generate BRD section using structured output.

        Args:
            section_name: Name of section (e.g., 'executive_summary')
            context: Context dict with requirements, conflicts, etc.

        Returns:
            Dict with 'content' and 'citations'
        """
        prompt_key = f"brd_section_{section_name}"
        prompt = prompts.format(prompt_key, **context)

        try:
            response = await self.router.acompletion(
                model="gemini-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_object",
                    "response_schema": BRDSectionResponse.model_json_schema()
                }
            )

            result = BRDSectionResponse.model_validate_json(
                response.choices[0].message.content
            )

            logger.info(f"Generated {section_name} section ({len(result.content)} chars)")
            return result.model_dump()

        except Exception as e:
            logger.error(f"BRD section generation failed for {section_name}: {e}", exc_info=True)
            return {
                "content": f"# {section_name.replace('_', ' ').title()}\n\nContent generation failed.",
                "citations": []
            }


# Global service instance
gemini_service = GeminiService()
