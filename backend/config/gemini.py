"""
Google Gemini AI configuration.
Provides configured GenerativeModel for all AI operations.
"""
import google.generativeai as genai
from .settings import settings


# Configure Gemini API with API key
genai.configure(api_key=settings.gemini_api_key)

# Create GenerativeModel instance with configuration
generation_config = {
    "temperature": settings.gemini_temperature,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    },
]

# Global GenerativeModel instance
gemini_model = genai.GenerativeModel(
    model_name=settings.gemini_model,
    generation_config=generation_config,
    safety_settings=safety_settings
)
