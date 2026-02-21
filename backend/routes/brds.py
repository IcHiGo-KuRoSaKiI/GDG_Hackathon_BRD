"""
BRD API routes.
Handles BRD generation and retrieval.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List
import logging

from ..models import BRD, BRDGenerateRequest, RefineTextRequest, RefineTextResponse, User
from ..services.agent_service import agent_service
from ..services.firestore_service import firestore_service
from ..services.text_refinement_service import text_refinement_service
from ..utils import validate_project_id, validate_brd_id, get_current_user

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


@router.post("/{brd_id}/refine-text", response_model=RefineTextResponse)
async def refine_brd_text(
    project_id: str,
    brd_id: str,
    request: RefineTextRequest,
    user: User = Depends(get_current_user)
):
    """
    Refine or generate text in a BRD section with AI assistance.

    Security: Defense-in-depth against prompt injection attacks.
    - Layer 1: Pydantic validation (request model)
    - Layer 2: Pattern detection (Python utils)
    - Layer 3: Defensive prompts (AI instruction)

    Modes:
    - Simple: Direct text refinement (2-3 seconds)
    - Agentic: AI uses tools to access documents (4-8 seconds)

    Args:
        project_id: Project ID (for route consistency)
        brd_id: BRD ID being edited
        request: Refinement request with instruction and text
        user: Authenticated user (from JWT token)

    Returns:
        Refined text with metadata (sources, tool calls)

    Raises:
        400: Invalid request (malformed data, prompt injection detected)
        404: Project or BRD not found
        403: User doesn't have access to this project
        429: Rate limit exceeded
        500: AI generation failed

    Example:
        POST /projects/proj_123/brds/brd_456/refine-text
        {
            "selected_text": "OAuth 2.0 authentication",
            "instruction": "Make this more professional",
            "section_context": "functional_requirements",
            "mode": "simple"
        }

        Response:
        {
            "original": "OAuth 2.0 authentication",
            "refined": "OAuth 2.0 authentication protocol utilizing...",
            "sources_used": [],
            "tool_calls_made": [],
            "mode": "simple"
        }
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

    # Security logging - log the request (but NOT the actual instruction content)
    logger.info(
        f"Text refinement request - User: {user.user_id}, "
        f"Project: {project_id}, BRD: {brd_id}, "
        f"Mode: {request.mode}, Section: {request.section_context}"
    )

    try:
        # Verify BRD exists and belongs to project
        brd = await firestore_service.get_brd(brd_id)

        if not brd:
            raise HTTPException(
                status_code=404,
                detail=f"BRD {brd_id} not found"
            )

        if brd.project_id != project_id:
            raise HTTPException(
                status_code=404,
                detail=f"BRD {brd_id} not found in project {project_id}"
            )

        # TODO: Add user ownership verification
        # project = await firestore_service.get_project(project_id)
        # if project.owner_id != user.user_id:
        #     raise HTTPException(status_code=403, detail="Access denied")

        # Call text refinement service
        # Note: Pydantic validation already ran (Layer 1)
        # Pattern detection runs in validator (Layer 2)
        # Defensive prompts used in service (Layer 3)
        result = await text_refinement_service.refine_text(
            project_id,
            brd_id,
            request
        )

        logger.info(
            f"Text refinement successful - Mode: {result.mode}, "
            f"Sources: {len(result.sources_used)}"
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        # Validation errors (including prompt injection detection)
        logger.warning(
            f"Text refinement validation failed - User: {user.user_id}, "
            f"Error: {str(e)}"
        )
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        # AI generation or other errors
        logger.error(
            f"Text refinement failed - User: {user.user_id}, "
            f"Project: {project_id}, BRD: {brd_id}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Text refinement failed: {str(e)}"
        )
