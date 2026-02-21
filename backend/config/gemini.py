"""
Google Gemini AI configuration via LiteLLM.
Provides unified AI interface with retry logic and fallbacks.
"""
import os
from litellm import Router
from .settings import settings


# Set Gemini API key in environment for LiteLLM
os.environ["GEMINI_API_KEY"] = settings.gemini_api_key

# Configure LiteLLM router with Gemini
# Using Router for built-in retry logic and fallbacks
model_list = [
    {
        "model_name": "gemini-flash",  # Friendly name
        "litellm_params": {
            "model": f"gemini/{settings.gemini_model}",
            "api_key": settings.gemini_api_key,
            "temperature": settings.gemini_temperature,
            "top_p": 0.95,
            "max_tokens": 8192,
        }
    }
]

# Create router with retry configuration
litellm_router = Router(
    model_list=model_list,
    num_retries=settings.gemini_max_retries,
    timeout=120,  # 2 minutes timeout
    fallbacks=[],  # Can add fallback models here if needed
)
