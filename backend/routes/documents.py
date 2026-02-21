"""
Documents API routes.
Handles document upload and retrieval with authentication.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from typing import List
import logging

from ..models import Document, User
from ..services.document_service import document_service
from ..services.firestore_service import firestore_service
from ..utils import validate_project_id
from ..utils.auth_dependency import get_current_user
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.post("/upload", status_code=202)
async def upload_documents(
    project_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user)
):
    """
    Upload multiple documents for processing.

    Processing happens in background for each file. Client should poll
    GET /documents to check status.

    Args:
        project_id: Project to associate documents with
        background_tasks: FastAPI background tasks
        files: List of files to upload (supports multiple files)

    Returns:
        Status message with processing info for all files

    Raises:
        400: Invalid project ID or files too large
        404: Project not found
    """
    # Validate project ID
    if not validate_project_id(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID format"
        )

    # Verify project exists and user owns it
    project = await firestore_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found"
        )

    if project.user_id != user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this project"
        )

    try:
        max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        uploaded_files = []

        # Process each file
        for file in files:
            # Read file data
            file_data = await file.read()

            # Check file size
            if len(file_data) > max_size_bytes:
                logger.warning(f"File {file.filename} too large, skipping")
                continue

            # Start background processing for this file
            background_tasks.add_task(
                document_service.process_document,
                file_data,
                file.filename,
                project_id
            )

            uploaded_files.append(file.filename)
            logger.info(f"Started background processing for {file.filename}")

        if not uploaded_files:
            raise HTTPException(
                status_code=400,
                detail="No valid files to process (all files too large)"
            )

        return {
            "status": "processing",
            "message": f"Processing {len(uploaded_files)} document(s)",
            "files": uploaded_files,
            "note": "Poll GET /projects/{project_id}/documents to check status"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("", response_model=List[Document])
async def list_documents(
    project_id: str,
    user: User = Depends(get_current_user)
):
    """
    List all documents in a project.

    Requires: Authorization header with valid Firebase ID token
    User must own the project.

    Args:
        project_id: Project ID to query
        user: Current authenticated user

    Returns:
        List of documents with processing status

    Raises:
        400: Invalid project ID
        403: User doesn't own this project
    """
    # Validate project ID
    if not validate_project_id(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID format"
        )

    try:
        # Verify user owns project
        project = await firestore_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project.user_id != user.user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this project"
            )

        # Fetch documents from Firestore
        documents = await firestore_service.list_documents(project_id)

        return documents

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/{doc_id}", response_model=Document)
async def get_document(
    project_id: str,
    doc_id: str,
    user: User = Depends(get_current_user)
):
    """
    Get specific document details.

    Args:
        project_id: Project ID (for route consistency)
        doc_id: Document ID to retrieve

    Returns:
        Document details with AI metadata

    Raises:
        404: If document not found
    """
    try:
        # Fetch document
        document = await firestore_service.get_document(doc_id)

        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document {doc_id} not found"
            )

        # Verify document belongs to project
        if document.project_id != project_id:
            raise HTTPException(
                status_code=404,
                detail=f"Document {doc_id} not found in project {project_id}"
            )

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {doc_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}"
        )
