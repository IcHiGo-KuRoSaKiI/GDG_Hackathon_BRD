"""
Documents API routes.
Handles document upload and retrieval with authentication.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from typing import List
import logging

from ..models import Document, User, DeletePreview, DeleteConfirmRequest, DeleteResponse, DeleteJob
from ..services.document_service import document_service
from ..services.firestore_service import firestore_service
from ..services.storage_service import storage_service
from ..services.deletion_service import deletion_service
from ..utils import validate_project_id, validate_doc_id, validate_deletion_id
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


@router.get("/{doc_id}/text")
async def get_document_text(
    project_id: str,
    doc_id: str,
    user: User = Depends(get_current_user)
):
    """
    Get parsed text content of a document from Cloud Storage.

    Returns the full extracted text that was stored during document processing.
    """
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    if not validate_doc_id(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    try:
        # Verify project ownership
        project = await firestore_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="You don't have access to this project")

        # Fetch document metadata to get text_path
        document = await firestore_service.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        if document.project_id != project_id:
            raise HTTPException(status_code=404, detail="Document not found in this project")

        if not document.text_path:
            raise HTTPException(
                status_code=404,
                detail="Document text not available (still processing or failed)"
            )

        # Read text from Cloud Storage
        text = await storage_service.download_text(document.text_path)
        return text

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document text {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document text: {str(e)}")


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


@router.delete("/{doc_id}/preview", response_model=DeletePreview)
async def preview_document_deletion(
    project_id: str,
    doc_id: str,
    user: User = Depends(get_current_user)
):
    """
    Preview document deletion (Step 1 of 2-step delete).

    Returns what will be deleted without actually deleting anything.
    Preview expires after 5 minutes.

    Args:
        project_id: Project ID containing the document
        doc_id: Document ID to delete

    Returns:
        DeletePreview with counts and deletion_id for confirmation

    Raises:
        400: Invalid IDs
        404: Document not found
        409: Deletion already in progress
    """
    # Validate IDs
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    if not validate_doc_id(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    try:
        # Verify ownership
        project = await firestore_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="You don't have access to this project")

        # Verify document belongs to project
        document = await firestore_service.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        if document.project_id != project_id:
            raise HTTPException(status_code=404, detail="Document not found in this project")

        # Generate preview
        preview = await deletion_service.preview_document_deletion(
            project_id=project_id,
            doc_id=doc_id,
            user_id=user.user_id
        )

        return preview

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview document deletion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}", status_code=202, response_model=DeleteResponse)
async def delete_document(
    project_id: str,
    doc_id: str,
    request: DeleteConfirmRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """
    Confirm and execute document deletion (Step 2 of 2-step delete).

    Requires valid deletion_id from preview and confirmation="DELETE".
    Deletion runs in background. Client should poll status endpoint.

    Args:
        project_id: Project ID containing the document
        doc_id: Document ID to delete
        request: Confirmation with deletion_id and "DELETE"
        background_tasks: FastAPI background tasks

    Returns:
        202 Accepted with deletion_id for status polling

    Raises:
        400: Invalid deletion_id or confirmation
        404: Preview not found or expired
        409: Deletion already in progress
    """
    # Validate IDs
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    if not validate_doc_id(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")
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

        # Verify it matches the requested document
        if job.project_id != project_id or job.doc_id != doc_id:
            raise HTTPException(status_code=400, detail="Deletion ID does not match document")

        # Check if preview expired
        from datetime import datetime
        if datetime.fromisoformat(job.preview.expires_at) < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="Preview expired. Please generate a new preview."
            )

        # Check if already queued or deleting
        if job.status != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Deletion already {job.status.value}"
            )

        # Update status to QUEUED
        from ..models import DeleteStatus
        await firestore_service.update_deletion_job(job.deletion_id, {
            "status": DeleteStatus.QUEUED.value
        })

        # Queue background task
        background_tasks.add_task(
            deletion_service.execute_deletion,
            job.deletion_id
        )

        logger.info(f"Queued deletion {job.deletion_id} for document {doc_id}")

        return DeleteResponse(
            status="deleting",
            deletion_id=job.deletion_id,
            message="Document deletion started",
            note=f"Poll GET /deletions/{job.deletion_id} to check status"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute document deletion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
