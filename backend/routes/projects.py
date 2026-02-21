"""
Projects API routes.
Handles project creation and retrieval with user authentication.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from typing import List
import logging

from ..models import Project, ProjectCreate, ProjectResponse, User
from ..services.firestore_service import firestore_service
from ..services.auth_service import auth_service
from ..utils import generate_project_id, validate_project_id
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
        ).order_by('created_at', direction='DESCENDING')

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
