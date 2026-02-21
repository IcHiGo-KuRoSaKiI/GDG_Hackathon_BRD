"""
AI configuration with factory pattern.
- Native Google Genai SDK for Gemini (structured outputs)
- LiteLLM for other models (unified interface)
"""
import os
from google import genai
from litellm import Router
from .settings import settings


# Set Gemini API key in environment
os.environ["GEMINI_API_KEY"] = settings.gemini_api_key

# ============================================
# NATIVE GOOGLE GENAI SDK (for Gemini)
# ============================================
genai_client = genai.Client(api_key=settings.gemini_api_key)


# ============================================
# LITELLM ROUTER (for other models)
# ============================================
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
    timeout=120,
    fallbacks=[],
)
