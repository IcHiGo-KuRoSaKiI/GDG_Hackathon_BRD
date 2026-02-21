"""
Documents API routes.
Handles document upload and retrieval.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from typing import List
import logging

from ..models import Document
from ..services.document_service import document_service
from ..services.firestore_service import firestore_service
from ..utils import validate_project_id
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.post("/upload", status_code=202)
async def upload_document(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload document for processing.

    Processing happens in background. Client should poll GET /documents
    to check status.

    Args:
        project_id: Project to associate document with
        background_tasks: FastAPI background tasks
        file: File to upload

    Returns:
        Status message with processing info

    Raises:
        400: Invalid project ID or file too large
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

    try:
        # Read file data
        file_data = await file.read()

        # Check file size
        max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        if len(file_data) > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
            )

        # Start background processing
        background_tasks.add_task(
            document_service.process_document,
            file_data,
            file.filename,
            project_id
        )

        logger.info(f"Started background processing for {file.filename}")

        return {
            "status": "processing",
            "message": f"Document {file.filename} is being processed",
            "note": "Poll GET /projects/{project_id}/documents to check status"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("", response_model=List[Document])
async def list_documents(project_id: str):
    """
    List all documents in a project.

    Args:
        project_id: Project ID to query

    Returns:
        List of documents with processing status

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
        # Fetch documents from Firestore
        documents = await firestore_service.list_documents(project_id)

        return documents

    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/{doc_id}", response_model=Document)
async def get_document(project_id: str, doc_id: str):
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
