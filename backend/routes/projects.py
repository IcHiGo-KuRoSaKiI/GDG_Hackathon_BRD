"""
Projects API routes.
Handles project creation and retrieval with user authentication.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime
from typing import List
import logging

from ..models import Project, ProjectCreate, ProjectResponse, User, DeletePreview, DeleteConfirmRequest, DeleteResponse, DeleteStatus
from ..services.firestore_service import firestore_service
from ..services.auth_service import auth_service
from ..services.deletion_service import deletion_service
from ..utils import generate_project_id, validate_project_id, validate_deletion_id
from ..utils.auth_dependency import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    user: User = Depends(get_current_user)
):
    """
    Create a new project for authenticated user.

    Requires: Authorization header with valid Firebase ID token

    Args:
        project_data: Project creation data
        user: Current authenticated user

    Returns:
        Created project details
    """
    try:
        # Generate project ID
        project_id = generate_project_id()

        # Create project model
        now = datetime.utcnow()
        project = Project(
            project_id=project_id,
            user_id=user.user_id,  # Associate with authenticated user
            name=project_data.name,
            description=project_data.description,
            created_at=now,
            updated_at=now,
            document_count=0,
            brd_count=0
        )

        # Store in Firestore
        await firestore_service.create_project(project)

        # Increment user's project count
        await auth_service.increment_project_count(user.user_id)

        logger.info(f"Created project: {project_id} for user: {user.user_id}")

        # Return response
        return ProjectResponse(
            project_id=project.project_id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            document_count=project.document_count,
            brd_count=project.brd_count
        )

    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("", response_model=List[Project])
async def list_projects(user: User = Depends(get_current_user)):
    """
    List all projects for authenticated user.

    Requires: Authorization header with valid Firebase ID token

    Args:
        user: Current authenticated user

    Returns:
        List of user's projects (newest first)
    """
    try:
        # Fetch user's projects from Firestore
        query = firestore_service.client.collection('projects').where(
            'user_id', '==', user.user_id
        )

        projects = []
        async for doc in query.stream():
            data = doc.to_dict()
            # Convert ISO strings back to datetime
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            projects.append(Project(**data))

        logger.info(f"Retrieved {len(projects)} projects for user: {user.user_id}")
        return projects

    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user)
):
    """
    Get project by ID.

    Requires: Authorization header with valid Firebase ID token
    User must own the project.

    Args:
        project_id: Project ID to retrieve
        user: Current authenticated user

    Returns:
        Project details

    Raises:
        400: Invalid project ID format
        403: User doesn't own this project
        404: Project not found
    """
    # Validate project ID format
    if not validate_project_id(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID format"
        )

    try:
        # Fetch from Firestore
        project = await firestore_service.get_project(project_id)

        if not project:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found"
            )

        # Verify user owns this project
        if project.user_id != user.user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this project"
            )

        return project

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve project: {str(e)}"
        )


@router.delete("/{project_id}/preview", response_model=DeletePreview)
async def preview_project_deletion(
    project_id: str,
    user: User = Depends(get_current_user)
):
    """
    Preview project deletion (Step 1 of 2-step delete).

    Returns what will be deleted without actually deleting anything.
    Includes all documents, chunks, BRDs, and storage files.
    Preview expires after 5 minutes.

    Args:
        project_id: Project ID to delete

    Returns:
        DeletePreview with counts and deletion_id for confirmation

    Raises:
        400: Invalid project ID
        404: Project not found
        409: Documents still processing or deletion already in progress
    """
    # Validate project ID
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    try:
        # Verify ownership
        project = await firestore_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="You don't have access to this project")

        # Generate preview
        preview = await deletion_service.preview_project_deletion(
            project_id=project_id,
            user_id=user.user_id
        )

        return preview

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview project deletion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}", status_code=202, response_model=DeleteResponse)
async def delete_project(
    project_id: str,
    request: DeleteConfirmRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """
    Confirm and execute project deletion (Step 2 of 2-step delete).

    Requires valid deletion_id from preview and confirmation="DELETE".
    Deletion runs in background. Client should poll status endpoint.

    Deletes:
    - All chunks (across all documents)
    - All storage files (originals + parsed text)
    - All document records
    - All BRDs
    - Project record
    - Decrements user.project_count

    Args:
        project_id: Project ID to delete
        request: Confirmation with deletion_id and "DELETE"
        background_tasks: FastAPI background tasks

    Returns:
        202 Accepted with deletion_id for status polling

    Raises:
        400: Invalid deletion_id or confirmation
        404: Preview not found or expired
        409: Documents still processing or deletion already in progress
    """
    # Validate project ID
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    if not validate_deletion_id(request.deletion_id):
        raise HTTPException(status_code=400, detail="Invalid deletion ID format")

    try:
        # Get deletion job
        job = await deletion_service.get_deletion_status(request.deletion_id)
        if not job:
            raise HTTPException(status_code=404, detail="Deletion preview not found")

        # Verify ownership
        if job.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="You don't have access to this deletion")

        # Verify it matches the requested project
        if job.project_id != project_id:
            raise HTTPException(status_code=400, detail="Deletion ID does not match project")

        # Check if preview expired
        if datetime.fromisoformat(job.preview.expires_at) < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="Preview expired. Please generate a new preview."
            )

        # Check if already queued or deleting
        if job.status != DeleteStatus.PENDING:
            raise HTTPException(
                status_code=409,
                detail=f"Deletion already {job.status.value}"
            )

        # Update status to QUEUED
        await firestore_service.update_deletion_job(job.deletion_id, {
            "status": DeleteStatus.QUEUED.value
        })

        # Queue background task
        background_tasks.add_task(
            deletion_service.execute_deletion,
            job.deletion_id
        )

        logger.info(f"Queued deletion {job.deletion_id} for project {project_id}")

        return DeleteResponse(
            status="deleting",
            deletion_id=job.deletion_id,
            message="Project deletion started",
            note=f"Poll GET /deletions/{job.deletion_id} to check status"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute project deletion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
