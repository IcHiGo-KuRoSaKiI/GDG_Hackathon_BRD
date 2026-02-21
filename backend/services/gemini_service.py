"""
Gemini AI service using factory pattern with Pydantic models.
Automatically uses native Gemini SDK for structured outputs.
"""
import logging
from typing import List
from .ai_service import ai_service
from ..utils import prompts
from ..models import (
    AIMetadata,
    DocumentClassificationResponse,
    SentimentAnalysisResponse,
    MetadataGenerationResponse,
    RequirementsExtractionResponse,
    ConflictDetectionResponse,
    BRDSectionResponse,
    TopicRelevance,
    ContentIndicators,
    KeyEntities,
    StakeholderSentiment
)

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for AI operations using factory pattern with Pydantic models."""

    def __init__(self):
        """Initialize Gemini service."""
        self.ai = ai_service

    async def classify_document(
        self,
        filename: str,
        content_preview: str
    ) -> DocumentClassificationResponse:
        """Classify document type using Pydantic structured output."""
        prompt = prompts.format(
            "document_classification",
            filename=filename,
            content_preview=content_preview
        )

        try:
            result = await self.ai.generate_structured(
                prompt=prompt,
                response_model=DocumentClassificationResponse
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
        """Generate comprehensive metadata using Pydantic structured output."""
        prompt = prompts.format("metadata_generation", doc_text=doc_text)

        try:
            result = await self.ai.generate_structured(
                prompt=prompt,
                response_model=MetadataGenerationResponse
            )

            # Convert stakeholder sentiment dict to list of StakeholderSentiment objects
            stakeholder_sentiments = []
            stakeholder_dict = result.sentiment.get("stakeholder_sentiment", {})
            for name, data in stakeholder_dict.items():
                # Handle both string and dict formats from Gemini
                if isinstance(data, str):
                    # Simple string sentiment
                    stakeholder_sentiments.append(StakeholderSentiment(
                        name=name,
                        sentiment=data,
                        concerns=[],
                        confidence=0.7
                    ))
                elif isinstance(data, dict):
                    # Detailed sentiment object
                    stakeholder_sentiments.append(StakeholderSentiment(
                        name=name,
                        sentiment=data.get("sentiment", "neutral"),
                        concerns=data.get("concerns", []),
                        confidence=data.get("confidence", 0.5)
                    ))
                else:
                    logger.warning(f"Unexpected sentiment data type for {name}: {type(data)}")

            # Convert to AIMetadata model
            # Note: document_type will be updated from classification in document_service
            return AIMetadata(
                document_type="other",  # Temp value, will be overwritten
                confidence=0.0,
                summary=result.summary,
                key_points=[],  # Not in current response
                tags=result.tags,
                topic_relevance=TopicRelevance(topics=result.topics),
                content_indicators=ContentIndicators(indicators=result.contains),
                key_entities=KeyEntities(**result.key_entities),
                stakeholder_sentiments=stakeholder_sentiments
            )

        except Exception as e:
            logger.error(f"Metadata generation failed: {e}", exc_info=True)
            raise Exception(f"AI generation failed: {str(e)}")

    async def extract_requirements(self, doc_text: str) -> List[dict]:
        """Extract requirements using Pydantic structured output."""
        prompt = prompts.format("requirement_extraction", doc_text=doc_text)

        try:
            result = await self.ai.generate_structured(
                prompt=prompt,
                response_model=RequirementsExtractionResponse
            )

            logger.info(f"Extracted {len(result.requirements)} requirements")
            return [req.model_dump() for req in result.requirements]

        except Exception as e:
            logger.error(f"Requirements extraction failed: {e}", exc_info=True)
            return []

    async def detect_conflicts(self, requirements_json: str) -> List[dict]:
        """Detect conflicts using Pydantic structured output."""
        prompt = prompts.format("conflict_detection", requirements_json=requirements_json)

        try:
            result = await self.ai.generate_structured(
                prompt=prompt,
                response_model=ConflictDetectionResponse
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
        """Analyze sentiment using Pydantic structured output."""
        prompt = prompts.format(
            "sentiment_analysis",
            doc_text=doc_text,
            stakeholders_list=stakeholders
        )

        try:
            result = await self.ai.generate_structured(
                prompt=prompt,
                response_model=SentimentAnalysisResponse
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
        """Generate BRD section using Pydantic structured output."""
        prompt_key = f"brd_section_{section_name}"
        prompt = prompts.format(prompt_key, **context)

        try:
            result = await self.ai.generate_structured(
                prompt=prompt,
                response_model=BRDSectionResponse
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
