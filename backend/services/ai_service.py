"""
AI Service with factory pattern.
- Uses native Google Genai SDK for Gemini models (structured outputs)
- Uses LiteLLM for other models (unified interface)
"""
import asyncio
import logging
from typing import List, Type, TypeVar
from pydantic import BaseModel
from ..config import genai_client, litellm_router, settings
from ..utils.token_tracking import extract_gemini_usage
from ..utils.retry import with_retry

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class AIService:
    """Factory pattern AI service supporting multiple backends."""

    def __init__(self):
        """Initialize AI service with both Gemini SDK and LiteLLM."""
        self.genai_client = genai_client
        self.litellm_router = litellm_router
        self.model = settings.gemini_model
        self.last_usage = None  # Token usage from last Gemini call

    def _is_gemini_model(self, model: str = None) -> bool:
        """Check if model is a Gemini model."""
        model = model or self.model
        return "gemini" in model.lower()

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        model: str = None
    ) -> T:
        """
        Generate structured output using appropriate backend.

        Args:
            prompt: The prompt to send
            response_model: Pydantic model for response validation
            model: Model to use (defaults to configured model)

        Returns:
            Validated Pydantic model instance
        """
        model = model or self.model

        if self._is_gemini_model(model):
            return await self._generate_gemini_structured(prompt, response_model, model)
        else:
            return await self._generate_litellm_structured(prompt, response_model, model)

    async def _generate_gemini_structured(
        self,
        prompt: str,
        response_model: Type[T],
        model: str
    ) -> T:
        """Generate using native Gemini SDK with structured outputs."""
        try:
            logger.info(f"🤖 Calling Gemini {model} for {response_model.__name__}...")
            logger.debug(f"Prompt length: {len(prompt)} chars")

            # Run sync Gemini SDK call in thread pool with timeout
            config = {
                "response_mime_type": "application/json",
                "response_json_schema": response_model.model_json_schema(),
                "temperature": settings.gemini_temperature,
                "max_output_tokens": settings.gemini_max_output_tokens,
            }
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._call_gemini_structured, model, prompt, config
                ),
                timeout=120.0  # 120 second timeout for complex metadata
            )

            logger.info(f"✅ Gemini response received for {response_model.__name__}")

            # Track token usage (accessible via ai_service.last_usage)
            self.last_usage = extract_gemini_usage(response)

            # Check finish_reason for MAX_TOKENS bug
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = getattr(response.candidates[0], 'finish_reason', None)
                if finish_reason == 'MAX_TOKENS':
                    logger.error(f"❌ Response hit MAX_TOKENS limit for {response_model.__name__}")
                    raise Exception(f"Response exceeded max_output_tokens ({settings.gemini_max_output_tokens}). Try simplifying the prompt or increasing token limit.")

            # Extract text from response (handle different response structures)
            response_text = None
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                # Try to get content from candidates
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    response_text = candidate.content.parts[0].text

            if not response_text:
                logger.error(f"❌ Empty response from Gemini for {response_model.__name__}")
                logger.debug(f"Response object: {response}")
                raise Exception("Empty response from Gemini API")

            logger.debug(f"Response length: {len(response_text)} chars")

            # Parse and validate with Pydantic
            result = response_model.model_validate_json(response_text)
            logger.info(f"✅ Validated {response_model.__name__} successfully")
            return result

        except asyncio.TimeoutError:
            logger.error(f"❌ Gemini API timeout after 60s for {response_model.__name__}")
            raise Exception(f"AI generation timeout after 60 seconds")
        except Exception as e:
            logger.error(f"❌ Gemini SDK generation failed for {response_model.__name__}: {e}", exc_info=True)
            raise Exception(f"AI generation failed: {str(e)}")

    async def _generate_litellm_structured(
        self,
        prompt: str,
        response_model: Type[T],
        model: str
    ) -> T:
        """Generate using LiteLLM (for non-Gemini models)."""
        try:
            response = await self.litellm_router.acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.gemini_temperature,
            )

            # Extract JSON from response (may have markdown code blocks)
            content = response.choices[0].message.content
            content = self._extract_json(content)

            # Parse and validate with Pydantic
            result = response_model.model_validate_json(content)
            logger.debug(f"LiteLLM generated structured output for {response_model.__name__}")
            return result

        except Exception as e:
            logger.error(f"LiteLLM generation failed: {e}", exc_info=True)
            raise Exception(f"AI generation failed: {str(e)}")

    @with_retry()
    def _call_gemini_structured(self, model: str, contents: str, config: dict):
        """Sync Gemini call with retry — used via asyncio.to_thread."""
        return self.genai_client.models.generate_content(
            model=model, contents=contents, config=config
        )

    def _extract_json(self, text: str) -> str:
        """Extract JSON from markdown code blocks if present."""
        text = text.strip()
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text


# Global service instance
ai_service = AIService()
