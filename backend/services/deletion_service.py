"""
Deletion service for two-step delete functionality.

Handles preview generation and background deletion execution.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from google.cloud.firestore import Increment

from ..models import (
    DeleteScope,
    DeleteStatus,
    DeletePreview,
    DeletionProgress,
    DeleteJob,
    Document
)
from ..services.firestore_service import firestore_service
from ..services.storage_service import storage_service
from ..utils.id_generator import generate_deletion_id

logger = logging.getLogger(__name__)


class DeletionService:
    """Service for handling two-step deletion with background processing."""

    def __init__(self):
        """Initialize deletion service."""
        self.firestore = firestore_service
        self.storage = storage_service

    # ============================================================
    # PREVIEW OPERATIONS
    # ============================================================

    async def preview_document_deletion(
        self,
        project_id: str,
        doc_id: str,
        user_id: str
    ) -> DeletePreview:
        """
        Generate preview of document deletion.

        Args:
            project_id: Project ID containing the document
            doc_id: Document ID to delete
            user_id: User initiating deletion

        Returns:
            DeletePreview with counts and estimated time

        Raises:
            HTTPException: If document not found or active deletion exists
        """
        # Check for active deletions
        await self._check_active_deletions(project_id, doc_id)

        # Fetch document and project info
        document = await self.firestore.get_document(doc_id)
        if not document:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Document not found")

        project = await self.firestore.get_project(project_id)
        if not project:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Project not found")

        # Count chunks
        chunks = await self.firestore.get_chunks(doc_id)
        chunks_to_delete = len(chunks)

        # Count storage files (original + parsed text)
        storage_files_to_delete = 1  # Original file
        if document.text_path:
            storage_files_to_delete += 1

        # Create preview
        deletion_id = generate_deletion_id()
        now = datetime.utcnow()
        preview = DeletePreview(
            deletion_id=deletion_id,
            scope=DeleteScope.DOCUMENT,
            project_id=project_id,
            project_name=project.name,
            doc_id=doc_id,
            filename=document.filename,
            documents_to_delete=1,
            chunks_to_delete=chunks_to_delete,
            brds_to_delete=0,  # BRDs remain (citations are denormalized)
            storage_files_to_delete=storage_files_to_delete,
            estimated_time_seconds=max(5, chunks_to_delete + storage_files_to_delete),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=5)).isoformat()
        )

        # Create deletion job in PENDING status
        job = DeleteJob(
            deletion_id=deletion_id,
            user_id=user_id,
            scope=DeleteScope.DOCUMENT,
            status=DeleteStatus.PENDING,
            project_id=project_id,
            doc_id=doc_id,
            preview=preview,
            created_at=datetime.utcnow().isoformat()
        )

        await self.firestore.create_deletion_job(job)

        logger.info(
            f"Created deletion preview {deletion_id} for document {doc_id} "
            f"({chunks_to_delete} chunks, {storage_files_to_delete} files)"
        )

        return preview

    async def preview_project_deletion(
        self,
        project_id: str,
        user_id: str
    ) -> DeletePreview:
        """
        Generate preview of project deletion.

        Args:
            project_id: Project ID to delete
            user_id: User initiating deletion

        Returns:
            DeletePreview with counts and estimated time

        Raises:
            HTTPException: If project not found, has processing documents, or active deletion exists
        """
        from fastapi import HTTPException

        # Check for active deletions
        await self._check_active_deletions(project_id)

        # Fetch project
        project = await self.firestore.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Fetch all documents
        documents = await self.firestore.list_documents(project_id)

        # Check for processing documents
        processing_docs = [d for d in documents if d.status == "processing"]
        if processing_docs:
            raise HTTPException(
                status_code=409,
                detail=f"{len(processing_docs)} document(s) still processing. "
                       "Wait for completion before deleting project."
            )

        # Count chunks across all documents
        total_chunks = 0
        total_storage_files = 0

        for doc in documents:
            chunks = await self.firestore.get_chunks(doc.doc_id)
            total_chunks += len(chunks)

            # Count storage files
            total_storage_files += 1  # Original file
            if doc.text_path:
                total_storage_files += 1  # Parsed text

        # Count BRDs
        brds = await self.firestore.list_brds(project_id)
        brds_to_delete = len(brds)

        # Create preview
        deletion_id = generate_deletion_id()
        now = datetime.utcnow()
        preview = DeletePreview(
            deletion_id=deletion_id,
            scope=DeleteScope.PROJECT,
            project_id=project_id,
            project_name=project.name,
            documents_to_delete=len(documents),
            chunks_to_delete=total_chunks,
            brds_to_delete=brds_to_delete,
            storage_files_to_delete=total_storage_files,
            estimated_time_seconds=max(5, total_chunks + total_storage_files + brds_to_delete),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=5)).isoformat()
        )

        # Create deletion job in PENDING status
        job = DeleteJob(
            deletion_id=deletion_id,
            user_id=user_id,
            scope=DeleteScope.PROJECT,
            status=DeleteStatus.PENDING,
            project_id=project_id,
            preview=preview,
            created_at=datetime.utcnow().isoformat()
        )

        await self.firestore.create_deletion_job(job)

        logger.info(
            f"Created deletion preview {deletion_id} for project {project_id} "
            f"({len(documents)} docs, {total_chunks} chunks, {total_storage_files} files)"
        )

        return preview

    async def _check_active_deletions(
        self,
        project_id: str,
        doc_id: Optional[str] = None
    ) -> None:
        """
        Check for active deletion jobs, auto-cancelling expired PENDING ones.

        Args:
            project_id: Project ID to check
            doc_id: Optional document ID to check

        Raises:
            HTTPException: If active deletion exists
        """
        from fastapi import HTTPException

        # Get all deletion jobs for this project
        jobs = await self.firestore.list_deletion_jobs(project_id=project_id)

        now = datetime.utcnow()
        active_statuses = {DeleteStatus.PENDING, DeleteStatus.QUEUED, DeleteStatus.DELETING}

        for job in jobs:
            if job.status not in active_statuses:
                continue

            # Auto-expire stale PENDING jobs (preview was never confirmed)
            if job.status == DeleteStatus.PENDING:
                expired = False
                if job.preview and job.preview.expires_at:
                    try:
                        expires = datetime.fromisoformat(job.preview.expires_at)
                        expired = now > expires
                    except (ValueError, TypeError):
                        expired = True  # Bad date → treat as expired
                else:
                    # No expiry info — check created_at, expire after 5 min
                    try:
                        created = datetime.fromisoformat(job.created_at)
                        expired = (now - created).total_seconds() > 300
                    except (ValueError, TypeError):
                        expired = True

                if expired:
                    logger.info(f"Auto-cancelling expired PENDING job {job.deletion_id}")
                    await self.firestore.update_deletion_job(job.deletion_id, {
                        "status": DeleteStatus.CANCELLED.value,
                        "completed_at": now.isoformat(),
                        "error_message": "Expired: preview was never confirmed"
                    })
                    continue  # Skip — no longer blocks

            # Still active — block the new deletion
            if doc_id and job.doc_id == doc_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Deletion already in progress for this document (job: {job.deletion_id})"
                )
            elif not doc_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Deletion already in progress for this project (job: {job.deletion_id})"
                )

    # ============================================================
    # EXECUTION OPERATIONS
    # ============================================================

    async def execute_deletion(self, deletion_id: str) -> None:
        """
        Execute deletion in background.

        This runs as a background task after user confirms deletion.

        Args:
            deletion_id: Deletion job ID to execute
        """
        try:
            # Get deletion job
            job = await self.firestore.get_deletion_job(deletion_id)
            if not job:
                logger.error(f"Deletion job {deletion_id} not found")
                return

            # Update status to DELETING
            await self.firestore.update_deletion_job(deletion_id, {
                "status": DeleteStatus.DELETING.value,
                "started_at": datetime.utcnow().isoformat()
            })

            logger.info(f"Starting deletion {deletion_id} (scope: {job.scope.value})")

            # Execute based on scope
            if job.scope == DeleteScope.DOCUMENT:
                await self._delete_document(job)
            elif job.scope == DeleteScope.PROJECT:
                await self._delete_project(job)

            # Mark complete
            await self.firestore.update_deletion_job(deletion_id, {
                "status": DeleteStatus.COMPLETE.value,
                "completed_at": datetime.utcnow().isoformat()
            })

            logger.info(f"Deletion {deletion_id} completed successfully")

        except Exception as e:
            logger.error(f"Deletion {deletion_id} failed: {e}", exc_info=True)

            # Mark failed
            await self.firestore.update_deletion_job(deletion_id, {
                "status": DeleteStatus.FAILED.value,
                "completed_at": datetime.utcnow().isoformat(),
                "error_message": str(e)
            })

    async def _delete_document(self, job: DeleteJob) -> None:
        """
        Execute document deletion (4 steps).

        Steps:
        1. Delete all chunks
        2. Delete storage files
        3. Delete document record
        4. Decrement project.document_count

        Args:
            job: DeleteJob with document deletion details
        """
        doc_id = job.doc_id
        project_id = job.project_id
        errors = []

        # Initialize progress
        progress = DeletionProgress(
            chunks_total=job.preview.chunks_to_delete,
            storage_files_total=job.preview.storage_files_to_delete,
            documents_total=1,
            current_step="deleting_chunks"
        )

        try:
            # Step 1: Delete all chunks
            logger.info(f"[{job.deletion_id}] Step 1: Deleting chunks for {doc_id}")
            chunks = await self.firestore.get_chunks(doc_id)
            chunk_ids = [c.chunk_id for c in chunks]

            if chunk_ids:
                await self.firestore.delete_chunks_batch(chunk_ids)
                progress.chunks_deleted = len(chunk_ids)
                logger.info(f"[{job.deletion_id}] Deleted {len(chunk_ids)} chunks")
            else:
                logger.info(f"[{job.deletion_id}] No chunks to delete")

            # Update progress
            progress.current_step = "deleting_storage"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict()
            })

        except Exception as e:
            error_msg = f"Failed to delete chunks: {e}"
            errors.append(error_msg)
            logger.warning(f"[{job.deletion_id}] {error_msg}")

        try:
            # Step 2: Delete storage files
            logger.info(f"[{job.deletion_id}] Step 2: Deleting storage files")
            document = await self.firestore.get_document(doc_id)

            if document:
                # Delete original file
                try:
                    await self.storage.delete_file(document.storage_path)
                    progress.storage_files_deleted += 1
                    logger.info(f"[{job.deletion_id}] Deleted original file: {document.storage_path}")
                except Exception as e:
                    error_msg = f"Failed to delete original file: {e}"
                    errors.append(error_msg)
                    logger.warning(f"[{job.deletion_id}] {error_msg}")

                # Delete parsed text file
                if document.text_path:
                    try:
                        await self.storage.delete_file(document.text_path)
                        progress.storage_files_deleted += 1
                        logger.info(f"[{job.deletion_id}] Deleted text file: {document.text_path}")
                    except Exception as e:
                        error_msg = f"Failed to delete text file: {e}"
                        errors.append(error_msg)
                        logger.warning(f"[{job.deletion_id}] {error_msg}")

            # Update progress
            progress.current_step = "deleting_document"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict()
            })

        except Exception as e:
            error_msg = f"Failed to delete storage files: {e}"
            errors.append(error_msg)
            logger.warning(f"[{job.deletion_id}] {error_msg}")

        try:
            # Step 3: Delete document record
            logger.info(f"[{job.deletion_id}] Step 3: Deleting document record")
            await self.firestore.delete_document(doc_id)
            progress.documents_deleted = 1
            logger.info(f"[{job.deletion_id}] Deleted document record")

            # Update progress
            progress.current_step = "updating_counters"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict()
            })

        except Exception as e:
            error_msg = f"Failed to delete document record: {e}"
            errors.append(error_msg)
            logger.error(f"[{job.deletion_id}] {error_msg}")
            raise  # Critical error - stop execution

        try:
            # Step 4: Decrement project.document_count
            logger.info(f"[{job.deletion_id}] Step 4: Decrementing document count")
            await self.firestore.update_project(project_id, {
                "document_count": Increment(-1)
            })
            logger.info(f"[{job.deletion_id}] Decremented document count")

            # Update progress
            progress.current_step = "complete"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict(),
                "errors": errors
            })

        except Exception as e:
            error_msg = f"Failed to decrement document count: {e}"
            errors.append(error_msg)
            logger.warning(f"[{job.deletion_id}] {error_msg}")

        if errors:
            logger.warning(f"[{job.deletion_id}] Completed with {len(errors)} non-critical errors")

    async def _delete_project(self, job: DeleteJob) -> None:
        """
        Execute project deletion (6 steps).

        Steps:
        1. Delete all chunks (across all documents)
        2. Delete all storage files
        3. Delete all document records
        4. Delete all BRDs
        5. Delete project record
        6. Decrement user.project_count

        Args:
            job: DeleteJob with project deletion details
        """
        project_id = job.project_id
        errors = []

        # Initialize progress
        progress = DeletionProgress(
            chunks_total=job.preview.chunks_to_delete,
            storage_files_total=job.preview.storage_files_to_delete,
            documents_total=job.preview.documents_to_delete,
            brds_total=job.preview.brds_to_delete,
            current_step="deleting_chunks"
        )

        # Fetch all documents
        documents = await self.firestore.list_documents(project_id)

        try:
            # Step 1: Delete all chunks
            logger.info(f"[{job.deletion_id}] Step 1: Deleting all chunks")

            for doc in documents:
                try:
                    chunks = await self.firestore.get_chunks(doc.doc_id)
                    chunk_ids = [c.chunk_id for c in chunks]

                    if chunk_ids:
                        await self.firestore.delete_chunks_batch(chunk_ids)
                        progress.chunks_deleted += len(chunk_ids)
                        logger.info(f"[{job.deletion_id}] Deleted {len(chunk_ids)} chunks for {doc.doc_id}")

                except Exception as e:
                    error_msg = f"Failed to delete chunks for {doc.doc_id}: {e}"
                    errors.append(error_msg)
                    logger.warning(f"[{job.deletion_id}] {error_msg}")

            # Update progress
            progress.current_step = "deleting_storage"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict()
            })

        except Exception as e:
            error_msg = f"Failed during chunk deletion: {e}"
            errors.append(error_msg)
            logger.warning(f"[{job.deletion_id}] {error_msg}")

        try:
            # Step 2: Delete all storage files
            logger.info(f"[{job.deletion_id}] Step 2: Deleting all storage files")

            for doc in documents:
                # Delete original file
                try:
                    await self.storage.delete_file(doc.storage_path)
                    progress.storage_files_deleted += 1
                    logger.info(f"[{job.deletion_id}] Deleted: {doc.storage_path}")
                except Exception as e:
                    error_msg = f"Failed to delete {doc.storage_path}: {e}"
                    errors.append(error_msg)
                    logger.warning(f"[{job.deletion_id}] {error_msg}")

                # Delete parsed text file
                if doc.text_path:
                    try:
                        await self.storage.delete_file(doc.text_path)
                        progress.storage_files_deleted += 1
                        logger.info(f"[{job.deletion_id}] Deleted: {doc.text_path}")
                    except Exception as e:
                        error_msg = f"Failed to delete {doc.text_path}: {e}"
                        errors.append(error_msg)
                        logger.warning(f"[{job.deletion_id}] {error_msg}")

            # Update progress
            progress.current_step = "deleting_documents"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict()
            })

        except Exception as e:
            error_msg = f"Failed during storage deletion: {e}"
            errors.append(error_msg)
            logger.warning(f"[{job.deletion_id}] {error_msg}")

        try:
            # Step 3: Delete all document records
            logger.info(f"[{job.deletion_id}] Step 3: Deleting all documents")

            for doc in documents:
                try:
                    await self.firestore.delete_document(doc.doc_id)
                    progress.documents_deleted += 1
                    logger.info(f"[{job.deletion_id}] Deleted document: {doc.doc_id}")
                except Exception as e:
                    error_msg = f"Failed to delete document {doc.doc_id}: {e}"
                    errors.append(error_msg)
                    logger.error(f"[{job.deletion_id}] {error_msg}")

            # Update progress
            progress.current_step = "deleting_brds"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict()
            })

        except Exception as e:
            error_msg = f"Failed during document deletion: {e}"
            errors.append(error_msg)
            logger.error(f"[{job.deletion_id}] {error_msg}")

        try:
            # Step 4: Delete all BRDs
            logger.info(f"[{job.deletion_id}] Step 4: Deleting all BRDs")
            brds = await self.firestore.list_brds(project_id)

            for brd in brds:
                try:
                    await self.firestore.delete_brd(brd.brd_id)
                    progress.brds_deleted += 1
                    logger.info(f"[{job.deletion_id}] Deleted BRD: {brd.brd_id}")
                except Exception as e:
                    error_msg = f"Failed to delete BRD {brd.brd_id}: {e}"
                    errors.append(error_msg)
                    logger.warning(f"[{job.deletion_id}] {error_msg}")

            # Update progress
            progress.current_step = "deleting_project"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict()
            })

        except Exception as e:
            error_msg = f"Failed during BRD deletion: {e}"
            errors.append(error_msg)
            logger.warning(f"[{job.deletion_id}] {error_msg}")

        try:
            # Step 5: Delete project record
            logger.info(f"[{job.deletion_id}] Step 5: Deleting project")
            await self.firestore.delete_project(project_id)
            logger.info(f"[{job.deletion_id}] Deleted project: {project_id}")

            # Update progress
            progress.current_step = "updating_counters"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict()
            })

        except Exception as e:
            error_msg = f"Failed to delete project: {e}"
            errors.append(error_msg)
            logger.error(f"[{job.deletion_id}] {error_msg}")
            raise  # Critical error - stop execution

        try:
            # Step 6: Decrement user.project_count
            logger.info(f"[{job.deletion_id}] Step 6: Decrementing project count")
            await self.firestore.update_user(job.user_id, {
                "project_count": Increment(-1)
            })
            logger.info(f"[{job.deletion_id}] Decremented project count")

            # Update progress
            progress.current_step = "complete"
            await self.firestore.update_deletion_job(job.deletion_id, {
                "progress": progress.to_dict(),
                "errors": errors
            })

        except Exception as e:
            error_msg = f"Failed to decrement project count: {e}"
            errors.append(error_msg)
            logger.warning(f"[{job.deletion_id}] {error_msg}")

        if errors:
            logger.warning(f"[{job.deletion_id}] Completed with {len(errors)} non-critical errors")

    # ============================================================
    # STATUS OPERATIONS
    # ============================================================

    async def get_deletion_status(self, deletion_id: str) -> Optional[DeleteJob]:
        """
        Get deletion job status.

        Args:
            deletion_id: Deletion job ID

        Returns:
            DeleteJob or None if not found
        """
        return await self.firestore.get_deletion_job(deletion_id)


# Global service instance
deletion_service = DeletionService()
