"""
Projects API routes.
Handles project creation and retrieval.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from ..models import Project, ProjectCreate, ProjectResponse
from ..services.firestore_service import firestore_service
from ..utils import generate_project_id, validate_project_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(project_data: ProjectCreate):
    """
    Create a new project.

    Args:
        project_data: Project creation data

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
            name=project_data.name,
            description=project_data.description,
            created_at=now,
            updated_at=now,
            document_count=0,
            brd_count=0
        )

        # Store in Firestore
        await firestore_service.create_project(project)

        logger.info(f"Created project: {project_id}")

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


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """
    Get project by ID.

    Args:
        project_id: Project ID to retrieve

    Returns:
        Project details

    Raises:
        404: If project not found
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

        return project

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve project: {str(e)}"
        )
