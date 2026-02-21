"""
Utilities module exports.
Provides easy access to all utility functions.
"""
from .prompts import prompts, PromptManager
from .validators import (
    validate_project_id,
    validate_doc_id,
    validate_brd_id,
    validate_deletion_id,
    sanitize_filename
)
from .id_generator import (
    generate_project_id,
    generate_doc_id,
    generate_brd_id,
    generate_chunk_id,
    generate_deletion_id
)
from .auth_dependency import get_current_user, get_optional_user
from .sanitization import (
    escape_user_input,
    detect_prompt_injection,
    validate_refinement_instruction,
    validate_selected_text
)

__all__ = [
    # Prompt management
    "prompts",
    "PromptManager",
    # Validators
    "validate_project_id",
    "validate_doc_id",
    "validate_brd_id",
    "validate_deletion_id",
    "sanitize_filename",
    # ID generators
    "generate_project_id",
    "generate_doc_id",
    "generate_brd_id",
    "generate_chunk_id",
    "generate_deletion_id",
    # Auth dependencies
    "get_current_user",
    "get_optional_user",
    # Security - Input sanitization
    "escape_user_input",
    "detect_prompt_injection",
    "validate_refinement_instruction",
    "validate_selected_text"
]
