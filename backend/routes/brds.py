"""
BRD API routes.
Handles BRD generation and retrieval.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
import logging

from ..models import BRD, BRDGenerateRequest
from ..services.agent_service import agent_service
from ..services.firestore_service import firestore_service
from ..utils import validate_project_id, validate_brd_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/brds", tags=["brds"])


async def _generate_and_store_brd(project_id: str):
    """
    Background task to generate and store BRD.

    Args:
        project_id: Project ID to generate BRD for
    """
    try:
        logger.info(f"Starting BRD generation for project {project_id}")

        # Generate BRD using agent service
        brd = await agent_service.generate_brd(project_id)

        # Store in Firestore
        await firestore_service.create_brd(brd)

        logger.info(f"BRD generation complete: {brd.brd_id}")

    except Exception as e:
        logger.error(f"BRD generation failed for project {project_id}: {e}", exc_info=True)
        # TODO: Store error status in Firestore for client to poll


@router.post("/generate", status_code=202)
async def generate_brd(
    project_id: str,
    request: BRDGenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate BRD for a project.

    Processing happens in background. Client should poll GET /brds
    to check when generation is complete.

    Args:
        project_id: Project to generate BRD for
        request: Generation options
        background_tasks: FastAPI background tasks

    Returns:
        Status message with estimated time

    Raises:
        400: Invalid project ID
        404: Project not found
    """
    # Validate project ID
    if not validate_project_id(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID format"
        )

    # Verify project exists
    project = await firestore_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found"
        )

    # Check if project has documents
    documents = await firestore_service.list_documents(project_id)
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="Project has no documents. Upload documents first."
        )

    # Check if all documents are processed
    processing_docs = [d for d in documents if d.status == "processing"]
    if processing_docs:
        raise HTTPException(
            status_code=400,
            detail=f"{len(processing_docs)} documents are still processing. Wait for completion."
        )

    try:
        # Start background BRD generation
        background_tasks.add_task(_generate_and_store_brd, project_id)

        logger.info(f"Started BRD generation for project {project_id}")

        return {
            "status": "processing",
            "message": "BRD generation started",
            "estimated_time": "30-60 seconds",
            "note": "Poll GET /projects/{project_id}/brds to check status"
        }

    except Exception as e:
        logger.error(f"Failed to start BRD generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start generation: {str(e)}"
        )


@router.get("", response_model=List[BRD])
async def list_brds(project_id: str):
    """
    List all BRDs for a project.

    Args:
        project_id: Project ID to query

    Returns:
        List of BRDs (newest first)

    Raises:
        400: Invalid project ID
    """
    # Validate project ID
    if not validate_project_id(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID format"
        )

    try:
        # Fetch BRDs from Firestore
        brds = await firestore_service.list_brds(project_id)

        # Sort by generated_at (newest first)
        brds.sort(key=lambda b: b.generated_at, reverse=True)

        return brds

    except Exception as e:
        logger.error(f"Failed to list BRDs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list BRDs: {str(e)}"
        )


@router.get("/{brd_id}", response_model=BRD)
async def get_brd(project_id: str, brd_id: str):
    """
    Get specific BRD details.

    Args:
        project_id: Project ID (for route consistency)
        brd_id: BRD ID to retrieve

    Returns:
        Complete BRD with all sections, citations, conflicts

    Raises:
        400: Invalid IDs
        404: If BRD not found
    """
    # Validate IDs
    if not validate_project_id(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID format"
        )

    if not validate_brd_id(brd_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid BRD ID format"
        )

    try:
        # Fetch BRD
        brd = await firestore_service.get_brd(brd_id)

        if not brd:
            raise HTTPException(
                status_code=404,
                detail=f"BRD {brd_id} not found"
            )

        # Verify BRD belongs to project
        if brd.project_id != project_id:
            raise HTTPException(
                status_code=404,
                detail=f"BRD {brd_id} not found in project {project_id}"
            )

        return brd

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get BRD {brd_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve BRD: {str(e)}"
        )
