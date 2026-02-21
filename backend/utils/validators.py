"""
Validation utilities for input sanitization.
"""
import re
from pathlib import Path


def validate_project_id(project_id: str) -> bool:
    """
    Validate project ID format.

    Args:
        project_id: Project ID to validate

    Returns:
        True if valid, False otherwise
    """
    # Format: proj_<alphanumeric>
    pattern = r'^proj_[a-zA-Z0-9]+$'
    return bool(re.match(pattern, project_id))


def validate_doc_id(doc_id: str) -> bool:
    """
    Validate document ID format.

    Args:
        doc_id: Document ID to validate

    Returns:
        True if valid, False otherwise
    """
    # Format: doc_<alphanumeric>
    pattern = r'^doc_[a-zA-Z0-9]+$'
    return bool(re.match(pattern, doc_id))


def validate_brd_id(brd_id: str) -> bool:
    """
    Validate BRD ID format.

    Args:
        brd_id: BRD ID to validate

    Returns:
        True if valid, False otherwise
    """
    # Format: brd_<alphanumeric>
    pattern = r'^brd_[a-zA-Z0-9]+$'
    return bool(re.match(pattern, brd_id))


def validate_deletion_id(deletion_id: str) -> bool:
    """
    Validate deletion job ID format.

    Args:
        deletion_id: Deletion ID to validate

    Returns:
        True if valid, False otherwise
    """
    # Format: del_<alphanumeric>
    pattern = r'^del_[a-z0-9]+$'
    return bool(re.match(pattern, deletion_id))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and special characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Get base name (remove any path components)
    filename = Path(filename).name

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Remove any non-alphanumeric characters except dots, dashes, underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)

    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed_file'

    # Limit length
    if len(filename) > 200:
        # Preserve extension
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:195] + ('.' + ext if ext else '')

    return filename
