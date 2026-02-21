"""
Gemini AI service via LiteLLM.
All AI operations using LiteLLM's unified interface with built-in retry logic.
"""
import json
import logging
from typing import Dict, List, Any
from litellm import acompletion
from ..config import litellm_router, settings
from ..utils import prompts
from ..models import (
    AIMetadata,
    DocumentType,
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

    async def _generate_with_retry(self, prompt: str) -> str:
        """
        Generate content using LiteLLM (retry logic built-in).

        Args:
            prompt: Prompt to send to Gemini

        Returns:
            Generated text response

        Raises:
            Exception: If generation failed after retries
        """
        try:
            # Use router's async completion with built-in retries
            response = await self.router.acompletion(
                model="gemini-flash",  # Friendly name from router config
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract text from response
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LiteLLM generation failed: {e}", exc_info=True)
            raise Exception(f"AI generation failed: {str(e)}")

    async def classify_document(
        self,
        filename: str,
        content_preview: str
    ) -> Dict[str, Any]:
        """
        Classify document type and confidence.

        Args:
            filename: Original filename
            content_preview: First ~500 characters of document

        Returns:
            Dict with 'document_type' and 'confidence'
        """
        prompt = prompts.format(
            "document_classification",
            filename=filename,
            content_preview=content_preview
        )

        response = await self._generate_with_retry(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response (may have markdown code blocks)
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            result = json.loads(json_str)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification JSON: {e}\nResponse: {response}")
            # Return default classification
            return {
                "document_type": "other",
                "confidence": 0.5
            }

    async def generate_metadata(self, doc_text: str) -> AIMetadata:
        """
        Generate complete AI metadata for document.

        Args:
            doc_text: Full document text

        Returns:
            AIMetadata model with all fields populated
        """
        prompt = prompts.format("metadata_generation", doc_text=doc_text)

        response = await self._generate_with_retry(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            data = json.loads(json_str)

            # Construct AIMetadata from parsed data
            return AIMetadata(
                document_type=DocumentType(data.get("document_type", "other")),
                confidence=data.get("confidence", 0.5),
                summary=data.get("summary", ""),
                key_points=data.get("key_points", []),
                tags=data.get("tags", []),
                topic_relevance=TopicRelevance(**data.get("topic_relevance", {})),
                content_indicators=ContentIndicators(**data.get("content_indicators", {})),
                key_entities=KeyEntities(**data.get("key_entities", {})),
                stakeholder_sentiments=[
                    StakeholderSentiment(**s) for s in data.get("stakeholder_sentiments", [])
                ]
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse metadata JSON: {e}\nResponse: {response}")
            # Return minimal metadata
            return AIMetadata(
                document_type=DocumentType.OTHER,
                confidence=0.5,
                summary="Error generating metadata",
                key_points=[],
                tags=[],
                topic_relevance=TopicRelevance(),
                content_indicators=ContentIndicators(),
                key_entities=KeyEntities(),
                stakeholder_sentiments=[]
            )

    async def extract_requirements(self, doc_text: str) -> List[Dict[str, Any]]:
        """
        Extract requirements from document text.

        Args:
            doc_text: Full document text

        Returns:
            List of requirement dicts with 'id', 'type', 'description', 'priority'
        """
        prompt = prompts.format("requirement_extraction", doc_text=doc_text)

        response = await self._generate_with_retry(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            result = json.loads(json_str)
            return result.get("requirements", [])

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse requirements JSON: {e}\nResponse: {response}")
            return []

    async def detect_conflicts(self, requirements_json: str) -> List[Dict[str, Any]]:
        """
        Detect conflicts in requirements.

        Args:
            requirements_json: JSON string of all requirements

        Returns:
            List of conflict dicts
        """
        prompt = prompts.format("conflict_detection", requirements_json=requirements_json)

        response = await self._generate_with_retry(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            result = json.loads(json_str)
            return result.get("conflicts", [])

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse conflicts JSON: {e}\nResponse: {response}")
            return []

    async def analyze_sentiment(
        self,
        doc_text: str,
        stakeholders: str
    ) -> Dict[str, Any]:
        """
        Analyze sentiment across documents.

        Args:
            doc_text: Combined text from all documents
            stakeholders: JSON string of stakeholder list

        Returns:
            Sentiment analysis dict
        """
        prompt = prompts.format(
            "sentiment_analysis",
            doc_text=doc_text,
            stakeholders=stakeholders
        )

        response = await self._generate_with_retry(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse sentiment JSON: {e}\nResponse: {response}")
            return {
                "overall_sentiment": "neutral",
                "confidence": 0.5,
                "stakeholder_breakdown": {},
                "key_concerns": []
            }

    async def generate_brd_section(
        self,
        section_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a single BRD section with citations.

        Args:
            section_name: Name of section (e.g., 'executive_summary')
            context: Context dict with requirements, docs, conflicts, etc.

        Returns:
            Dict with 'content', 'citations', 'subsections'
        """
        # Get section-specific prompt
        prompt_key = f"brd_section_{section_name}"

        # Format context as JSON for prompt
        context_json = json.dumps(context, indent=2)

        prompt = prompts.format(prompt_key, context=context_json)

        response = await self._generate_with_retry(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse BRD section JSON: {e}\nResponse: {response}")
            return {
                "content": "Error generating section",
                "citations": [],
                "subsections": None
            }


# Global service instance (no args needed, uses litellm_router)
gemini_service = GeminiService()
