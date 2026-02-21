"""
Deletions API routes.
Handles deletion job status and management.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging

from ..models import DeleteJob, User
from ..services.deletion_service import deletion_service
from ..utils import validate_deletion_id
from ..utils.auth_dependency import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/deletions", tags=["deletions"])


@router.get("/{deletion_id}", response_model=DeleteJob)
async def get_deletion_status(
    deletion_id: str,
    user: User = Depends(get_current_user)
):
    """
    Get deletion job status.

    Use this endpoint to poll deletion progress after confirming deletion.

    Args:
        deletion_id: Deletion job ID

    Returns:
        DeleteJob with current status and progress

    Raises:
        400: Invalid deletion ID
        404: Deletion job not found
        403: User doesn't own this deletion
    """
    # Validate deletion ID
    if not validate_deletion_id(deletion_id):
        raise HTTPException(status_code=400, detail="Invalid deletion ID format")

    try:
        # Get deletion job
        job = await deletion_service.get_deletion_status(deletion_id)
        if not job:
            raise HTTPException(status_code=404, detail="Deletion job not found")

        # Verify ownership
        if job.user_id != user.user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this deletion"
            )

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deletion status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[DeleteJob])
async def list_deletion_jobs(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """
    List deletion jobs for the authenticated user.

    Args:
        project_id: Filter by project ID (optional)
        status: Filter by status (pending/queued/deleting/complete/failed) (optional)
        limit: Maximum number of jobs to return (default: 50)

    Returns:
        List of DeleteJob objects

    Raises:
        400: Invalid parameters
    """
    # Validate limit
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100"
        )

    try:
        # List deletion jobs for this user
        jobs = await deletion_service.firestore.list_deletion_jobs(
            user_id=user.user_id,
            project_id=project_id,
            status=status,
            limit=limit
        )

        return jobs

    except Exception as e:
        logger.error(f"Failed to list deletion jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
