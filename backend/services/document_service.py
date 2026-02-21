"""
Document processing service.
Complete pipeline for document upload, parsing, and AI analysis.
"""
import asyncio
import logging
from typing import Tuple, List
from datetime import datetime
from pathlib import Path
import tempfile

from ..models import (
    Document,
    DocumentStatus,
    Chunk,
    ChomperMetadata,
    AIMetadata
)
from ..utils import generate_doc_id, generate_chunk_id, sanitize_filename
from .storage_service import storage_service
from .firestore_service import firestore_service
from .gemini_service import gemini_service

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document processing pipeline."""

    def __init__(self):
        """Initialize document service."""
        self.storage = storage_service
        self.firestore = firestore_service
        self.gemini = gemini_service

    async def process_document(
        self,
        file_data: bytes,
        filename: str,
        project_id: str
    ) -> Document:
        """
        Complete document processing pipeline.

        Pipeline:
        1. Create doc record (status: uploading)
        2. Upload to Cloud Storage
        3. Parse with Chomper MCP
        4. Classify with Gemini (parallel)
        5. Generate metadata with Gemini (parallel)
        6. Store parsed text and chunks
        7. Update status (complete)

        Args:
            file_data: File bytes
            filename: Original filename
            project_id: Parent project ID

        Returns:
            Document model (status will be 'complete' or 'failed')
        """
        doc_id = generate_doc_id()
        safe_filename = sanitize_filename(filename)

        # 1. Create initial document record
        document = Document(
            doc_id=doc_id,
            project_id=project_id,
            filename=safe_filename,
            original_filename=filename,
            storage_path=f"projects/{project_id}/documents/{doc_id}/{safe_filename}",
            status=DocumentStatus.UPLOADING,
            uploaded_at=datetime.utcnow()
        )

        try:
            await self.firestore.create_document(document)

            # 2. Upload to Cloud Storage
            logger.info(f"Uploading {filename} to Cloud Storage...")
            await self.storage.upload_file(file_data, document.storage_path)

            # 3. Parse with Chomper
            document.status = DocumentStatus.PROCESSING
            await self.firestore.update_document(doc_id, {"status": "processing"})

            logger.info(f"Parsing {filename} with Chomper...")
            full_text, chunks, chomper_meta = await self._parse_with_chomper(
                file_data,
                filename
            )

            # 4 & 5. Classify and generate metadata in parallel
            logger.info(f"Running AI analysis on {filename}...")
            content_preview = full_text[:500]

            classification_task = self.gemini.classify_document(filename, content_preview)
            metadata_task = self.gemini.generate_metadata(full_text)

            classification, ai_metadata = await asyncio.gather(
                classification_task,
                metadata_task
            )

            # Update AI metadata with classification (structured response)
            ai_metadata.document_type = classification.document_type
            ai_metadata.confidence = classification.confidence

            # 6. Store parsed text and chunks
            logger.info(f"Storing parsed text and {len(chunks)} chunks...")

            # Store full text in Cloud Storage
            text_path = f"projects/{project_id}/documents/{doc_id}/text.txt"
            await self.storage.upload_text(full_text, text_path)

            # Store chunks in Firestore
            await self.firestore.store_chunks(chunks)

            # 7. Update document with complete status
            document.status = DocumentStatus.COMPLETE
            document.processed_at = datetime.utcnow()
            document.text_path = text_path
            document.chomper_metadata = chomper_meta
            document.ai_metadata = ai_metadata
            document.chunk_count = len(chunks)

            await self.firestore.update_document(doc_id, {
                "status": "complete",
                "processed_at": datetime.utcnow().isoformat(),
                "text_path": text_path,
                "chomper_metadata": chomper_meta.model_dump(),
                "ai_metadata": ai_metadata.model_dump(),
                "chunk_count": len(chunks)
            })

            logger.info(f"Document {filename} processed successfully!")
            return document

        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}", exc_info=True)

            # Update document with failed status
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)

            await self.firestore.update_document(doc_id, {
                "status": "failed",
                "error_message": str(e)
            })

            return document

    async def _parse_with_chomper(
        self,
        file_data: bytes,
        filename: str
    ) -> Tuple[str, List[Chunk], ChomperMetadata]:
        """
        Parse document using Chomper MCP or document-parser.

        Args:
            file_data: File bytes
            filename: Original filename

        Returns:
            Tuple of (full_text, chunks, chomper_metadata)
        """
        # Write file to temp location for MCP tool
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            tmp_file.write(file_data)
            tmp_path = tmp_file.name

        try:
            # Use document-parser MCP tool
            # This is a placeholder - actual implementation depends on MCP availability
            # For now, we'll use a simple text extraction fallback

            logger.warning("Using fallback text extraction (Chomper MCP not integrated yet)")

            # Simple text extraction (fallback)
            try:
                full_text = file_data.decode('utf-8')
            except UnicodeDecodeError:
                # Try latin-1 as fallback
                full_text = file_data.decode('latin-1', errors='ignore')

            # Create chunks (simple word-based chunking)
            chunks = self._create_chunks(full_text, filename)

            # Create basic metadata
            chomper_meta = ChomperMetadata(
                format=Path(filename).suffix.lstrip('.'),
                word_count=len(full_text.split()),
                char_count=len(full_text),
                has_images=False,
                has_tables=False
            )

            return full_text, chunks, chomper_meta

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def _create_chunks(
        self,
        full_text: str,
        filename: str,
        chunk_size: int = 1000,
        overlap: int = 100
    ) -> List[Chunk]:
        """
        Create text chunks for citation tracking.

        Args:
            full_text: Full document text
            filename: Original filename
            chunk_size: Words per chunk
            overlap: Words overlap between chunks

        Returns:
            List of Chunk models
        """
        from ..config import settings

        # Use settings if available
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap

        words = full_text.split()
        chunks = []

        doc_id = generate_doc_id()

        i = 0
        chunk_index = 0
        while i < len(words):
            # Get chunk words
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)

            # Calculate character positions
            start_pos = full_text.find(chunk_words[0]) if chunk_words else 0
            end_pos = start_pos + len(chunk_text)

            chunk = Chunk(
                chunk_id=generate_chunk_id(doc_id, chunk_index),
                doc_id=doc_id,
                chunk_index=chunk_index,
                text=chunk_text,
                word_count=len(chunk_words),
                start_position=start_pos,
                end_position=end_pos
            )

            chunks.append(chunk)

            # Move to next chunk with overlap
            i += chunk_size - overlap
            chunk_index += 1

        return chunks


# Global service instance
document_service = DocumentService()
