"""
LLM Token Usage Tracking & Cost Estimation.

Provides a centralized pricing dictionary for all supported models
and utilities to extract, calculate, and persist token usage metrics.
"""

import logging
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

from google.cloud.firestore_v1 import AsyncClient
from google.cloud.firestore_v1.transforms import Increment

logger = logging.getLogger(__name__)

# ============================================
# Model Pricing (per 1M tokens) — USD
# ============================================
# Format: "model_name": (input_price, output_price)
# Sources:
#   Gemini: https://ai.google.dev/gemini-api/docs/pricing
#   OpenAI: https://openai.com/api/pricing/
#   Claude: https://docs.anthropic.com/en/docs/about-claude/pricing

MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # Google Gemini
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-pro-preview-05-06": (1.25, 10.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-3-pro": (2.00, 12.00),
    "gemini-3-flash": (0.50, 3.00),
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "o3": (2.00, 8.00),
    "o3-mini": (1.10, 4.40),
    "o4-mini": (1.10, 4.40),
    # Anthropic Claude
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate estimated cost for a given model and token counts.

    Args:
        model: Model name (e.g., "gemini-2.5-pro")
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens

    Returns:
        Estimated cost in USD, rounded to 6 decimal places
    """
    # Try exact match first, then prefix match for versioned model names
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        for key in MODEL_PRICING:
            if model.startswith(key) or key.startswith(model):
                pricing = MODEL_PRICING[key]
                break

    if not pricing:
        logger.warning(f"No pricing found for model '{model}', using zero cost")
        return 0.0

    input_price, output_price = pricing
    cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
    return round(cost, 6)


def extract_gemini_usage(response: Any) -> Optional[Dict[str, int]]:
    """
    Extract token usage from a Gemini API response.

    Args:
        response: Gemini GenerateContentResponse

    Returns:
        Dict with input_tokens and output_tokens, or None if unavailable
    """
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return None

    input_tokens = getattr(usage, "prompt_token_count", 0) or 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


async def log_usage(
    firestore_client: AsyncClient,
    project_id: str,
    service: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """
    Log token usage to Firestore — atomic increment on project document.

    Updates project.usage with cumulative totals and per-service breakdown.

    Args:
        firestore_client: Async Firestore client
        project_id: Project to attribute usage to
        service: Service name (e.g., "brd_generation", "ai_metadata", "chat")
        model: Model name used
        input_tokens: Input tokens consumed
        output_tokens: Output tokens consumed
    """
    cost = calculate_cost(model, input_tokens, output_tokens)
    total_tokens = input_tokens + output_tokens

    try:
        project_ref = firestore_client.collection("projects").document(project_id)
        await project_ref.update({
            # Global totals
            "usage.total_input_tokens": Increment(input_tokens),
            "usage.total_output_tokens": Increment(output_tokens),
            "usage.total_tokens": Increment(total_tokens),
            "usage.total_cost_usd": Increment(cost),
            "usage.call_count": Increment(1),
            # Per-service breakdown
            f"usage.by_service.{service}.input_tokens": Increment(input_tokens),
            f"usage.by_service.{service}.output_tokens": Increment(output_tokens),
            f"usage.by_service.{service}.cost_usd": Increment(cost),
            f"usage.by_service.{service}.calls": Increment(1),
            # Last model used
            "usage.last_model": model,
            "usage.last_updated": datetime.utcnow().isoformat(),
        })

        logger.debug(
            f"Logged usage: project={project_id} service={service} "
            f"model={model} tokens={total_tokens} cost=${cost:.4f}"
        )
    except Exception as e:
        # Non-critical — don't fail the main operation
        logger.warning(f"Failed to log token usage: {e}")
