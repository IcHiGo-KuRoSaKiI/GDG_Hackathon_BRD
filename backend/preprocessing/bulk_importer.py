"""
Bulk importer: creates a project and uploads filtered emails to the BRD system.

Full lifecycle:
  1. Creates a new project via POST /projects
  2. Uploads filtered emails via POST /projects/{id}/documents/upload
  3. Exports files locally as backup

Rate limited to avoid overwhelming the server and Gemini API.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .embedding_filter import EmbeddingResult

logger = logging.getLogger(__name__)


async def login(
    email: str,
    password: str,
    api_base_url: str = "http://localhost:8000",
) -> str:
    """
    Login via the API and return a JWT token.

    Args:
        email: User email
        password: User password
        api_base_url: Backend API URL

    Returns:
        JWT token string
    """
    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for API operations. Install with: pip install httpx"
        )

    url = f"{api_base_url}/auth/login"
    payload = {"email": email, "password": password}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            token = data["token"]
            user_email = data.get("user", {}).get("email", email)
            logger.info(f"Logged in as: {user_email}")
            return token
        else:
            raise RuntimeError(
                f"Login failed: {response.status_code} — {response.text}"
            )


async def create_project(
    project_name: str,
    project_description: str,
    api_base_url: str = "http://localhost:8000",
    auth_token: Optional[str] = None,
) -> str:
    """
    Create a new project via the API and return its project_id.

    Args:
        project_name: Name for the new project
        project_description: Description of the project
        api_base_url: Backend API URL
        auth_token: JWT auth token

    Returns:
        project_id of the newly created project

    Raises:
        RuntimeError: If project creation fails
    """
    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for API operations. Install with: pip install httpx"
        )

    url = f"{api_base_url}/projects"
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    payload = {
        "name": project_name,
        "description": project_description,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 201:
            data = response.json()
            project_id = data["project_id"]
            logger.info(
                f"Created project: {project_id} — \"{project_name}\""
            )
            return project_id
        else:
            raise RuntimeError(
                f"Failed to create project: {response.status_code} — {response.text}"
            )


async def create_project_and_upload(
    results: List[EmbeddingResult],
    project_name: str,
    project_description: str,
    output_dir: str,
    api_base_url: str = "http://localhost:8000",
    auth_token: Optional[str] = None,
    batch_size: int = 5,
    delay_between_batches: float = 2.0,
) -> Dict:
    """
    Full lifecycle: create project → export files → upload to project.

    This is the main entry point for the pipeline's import step.
    Returns the project_id and all stats.

    Args:
        results: Filtered emails from the embedding stage
        project_name: Name for the new project
        project_description: Project description
        output_dir: Local directory for exported files (backup)
        api_base_url: Backend API URL
        auth_token: JWT auth token
        batch_size: Files per upload request
        delay_between_batches: Seconds between upload batches

    Returns:
        Dict with project_id, export stats, and upload stats
    """
    # Step 1: Create project
    project_id = await create_project(
        project_name=project_name,
        project_description=project_description,
        api_base_url=api_base_url,
        auth_token=auth_token,
    )

    # Step 2: Export locally (backup + metadata)
    export_stats = await export_to_directory(results, output_dir)

    # Step 3: Upload to the new project
    upload_stats = await upload_to_api(
        results=results,
        project_id=project_id,
        api_base_url=api_base_url,
        auth_token=auth_token,
        batch_size=batch_size,
        delay_between_batches=delay_between_batches,
    )

    return {
        "project_id": project_id,
        "project_name": project_name,
        "export": export_stats,
        "upload": upload_stats,
    }


async def export_to_directory(
    results: List[EmbeddingResult],
    output_dir: str,
    include_metadata: bool = True,
) -> dict:
    """
    Export filtered emails as individual .txt files for upload.

    Each email becomes a .txt file with headers + body. A metadata
    JSON sidecar file is created with scores and signals.

    Args:
        results: Filtered emails from the embedding stage
        output_dir: Directory to write files to
        include_metadata: Whether to write a _metadata.json sidecar

    Returns:
        Stats dict with counts
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    exported = 0
    for i, result in enumerate(results):
        em = result.filter_result.email

        # Build filename from subject or index
        safe_subject = "".join(
            c if c.isalnum() or c in " -_" else "_"
            for c in (em.subject or "no_subject")
        )[:60].strip()
        filename = f"{i:04d}_{safe_subject}.txt"

        # Write email as plain text with headers
        content = (
            f"From: {em.sender}\n"
            f"To: {', '.join(em.recipients_to)}\n"
            f"Cc: {', '.join(em.recipients_cc)}\n"
            f"Date: {em.date}\n"
            f"Subject: {em.subject}\n"
            f"Folder: {em.folder}\n"
            f"---\n"
            f"{em.body}"
        )

        file_path = out_path / filename
        file_path.write_text(content, encoding="utf-8")
        exported += 1

    # Write combined metadata
    if include_metadata:
        metadata = []
        for i, result in enumerate(results):
            em = result.filter_result.email
            metadata.append({
                "index": i,
                "file_path": em.file_path,
                "subject": em.subject,
                "sender": em.sender,
                "date": em.date,
                "word_count": em.word_count,
                "heuristic_score": result.filter_result.score,
                "embedding_score": result.embedding_score,
                "combined_score": result.combined_score,
                "best_matching_query": result.best_matching_query,
                "signals": result.filter_result.signals,
            })

        meta_path = out_path / "_pipeline_metadata.json"
        meta_path.write_text(
            json.dumps(metadata, indent=2, default=str),
            encoding="utf-8",
        )

    logger.info(f"Exported {exported:,} emails to {output_dir}")
    return {"exported": exported, "output_dir": str(output_dir)}


async def upload_to_api(
    results: List[EmbeddingResult],
    project_id: str,
    api_base_url: str = "http://localhost:8000",
    auth_token: Optional[str] = None,
    batch_size: int = 5,
    delay_between_batches: float = 2.0,
) -> dict:
    """
    Upload filtered emails to the BRD system via the /upload API.

    Rate-limited: uploads in small batches with delays to avoid
    overwhelming the server and Gemini API rate limits.

    Args:
        results: Filtered emails from the embedding stage
        project_id: Target project ID in the BRD system
        api_base_url: Backend API URL
        auth_token: JWT auth token
        batch_size: Files per upload request
        delay_between_batches: Seconds to wait between batches

    Returns:
        Stats dict
    """
    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for API upload. Install with: pip install httpx"
        )

    url = f"{api_base_url}/projects/{project_id}/documents/upload"
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    uploaded = 0
    failed = 0
    total_batches = (len(results) + batch_size - 1) // batch_size

    async with httpx.AsyncClient(timeout=120.0) as client:
        for batch_idx in range(0, len(results), batch_size):
            batch = results[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1

            # Build multipart files
            files = []
            for result in batch:
                em = result.filter_result.email
                safe_subject = "".join(
                    c if c.isalnum() or c in " -_" else "_"
                    for c in (em.subject or "no_subject")
                )[:60].strip()
                filename = f"{safe_subject}.txt"

                content = (
                    f"From: {em.sender}\n"
                    f"To: {', '.join(em.recipients_to)}\n"
                    f"Cc: {', '.join(em.recipients_cc)}\n"
                    f"Date: {em.date}\n"
                    f"Subject: {em.subject}\n"
                    f"---\n"
                    f"{em.body}"
                )
                files.append(
                    ("files", (filename, content.encode("utf-8"), "text/plain"))
                )

            try:
                response = await client.post(url, files=files, headers=headers)
                if response.status_code in (200, 202):
                    uploaded += len(batch)
                    logger.info(
                        f"  Batch {batch_num}/{total_batches}: "
                        f"uploaded {len(batch)} emails ({uploaded:,} total)"
                    )
                else:
                    failed += len(batch)
                    logger.warning(
                        f"  Batch {batch_num}/{total_batches}: "
                        f"failed with status {response.status_code}"
                    )
            except Exception as e:
                failed += len(batch)
                logger.error(f"  Batch {batch_num}/{total_batches}: error {e}")

            # Rate limit delay
            if batch_idx + batch_size < len(results):
                await asyncio.sleep(delay_between_batches)

    stats = {
        "uploaded": uploaded,
        "failed": failed,
        "total": len(results),
        "batches": total_batches,
    }
    logger.info(
        f"Upload complete: {uploaded:,} succeeded, {failed:,} failed "
        f"out of {len(results):,}"
    )
    return stats
