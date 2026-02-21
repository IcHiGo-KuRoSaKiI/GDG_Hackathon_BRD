"""
ID generation utilities for entities.
"""
import secrets
import string


def _generate_id(prefix: str, length: int = 12) -> str:
    """
    Generate random ID with prefix.

    Args:
        prefix: ID prefix (e.g., 'proj', 'doc', 'brd')
        length: Length of random portion

    Returns:
        Generated ID in format: {prefix}_{random}
    """
    alphabet = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}_{random_part}"


def generate_project_id() -> str:
    """
    Generate unique project ID.

    Returns:
        Project ID in format: proj_<random>
    """
    return _generate_id("proj")


def generate_doc_id() -> str:
    """
    Generate unique document ID.

    Returns:
        Document ID in format: doc_<random>
    """
    return _generate_id("doc")


def generate_brd_id() -> str:
    """
    Generate unique BRD ID.

    Returns:
        BRD ID in format: brd_<random>
    """
    return _generate_id("brd")


def generate_chunk_id(doc_id: str, index: int) -> str:
    """
    Generate chunk ID from document ID and index.

    Args:
        doc_id: Parent document ID
        index: Chunk index (0-based)

    Returns:
        Chunk ID in format: {doc_id}_chunk_{index}
    """
    return f"{doc_id}_chunk_{index:04d}"
