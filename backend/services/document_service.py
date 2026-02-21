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
from ..utils.token_tracking import log_usage
from ..config.firebase import firestore_client
from ..config import settings
from .storage_service import storage_service
from .firestore_service import firestore_service
from .gemini_service import gemini_service
from .embedding_service import embedding_service

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
            logger.info(f"📤 [1/6] Uploading {filename} to Cloud Storage...")
            await self.storage.upload_file(file_data, document.storage_path)
            logger.info(f"✅ Upload complete: {document.storage_path}")

            # 3. Parse with Chomper
            document.status = DocumentStatus.PROCESSING
            await self.firestore.update_document(doc_id, {"status": "processing"})

            logger.info(f"📄 [2/6] Parsing {filename} with Chomper...")
            full_text, chunks, chomper_meta = await self._parse_with_chomper(
                file_data,
                filename,
                doc_id
            )
            logger.info(f"✅ Parsed {len(full_text)} chars into {len(chunks)} chunks")

            # 4 & 5. Classify and generate metadata in parallel
            logger.info(f"🤖 [3/6] Running AI analysis on {filename} (2 parallel tasks)...")
            content_preview = full_text[:500]

            logger.info(f"  → Starting document classification...")
            logger.info(f"  → Starting metadata generation...")

            classification_task = self.gemini.classify_document(filename, content_preview)
            metadata_task = self.gemini.generate_metadata(full_text)

            classification, ai_metadata = await asyncio.gather(
                classification_task,
                metadata_task
            )

            logger.info(f"✅ AI analysis complete:")
            logger.info(f"  → Document type: {classification.document_type} (confidence: {classification.confidence:.2f})")
            logger.info(f"  → Summary: {ai_metadata.summary[:100]}...")
            logger.info(f"  → Tags: {', '.join(ai_metadata.tags[:5])}")

            # Log AI token usage (both calls ran through ai_service)
            usage = getattr(self.gemini.ai, 'last_usage', None)
            if usage:
                # Log combined usage for both parallel calls (approximate)
                asyncio.create_task(log_usage(
                    firestore_client, project_id, "ai_metadata",
                    settings.gemini_model,
                    usage["input_tokens"] * 2,  # 2 parallel calls
                    usage["output_tokens"] * 2,
                ))

            # Update AI metadata with classification (structured response)
            ai_metadata.document_type = classification.document_type
            ai_metadata.confidence = classification.confidence

            # 6. Generate embeddings for chunks (RAG)
            logger.info(f"🧠 [4/6] Generating embeddings for {len(chunks)} chunks...")
            try:
                chunk_texts = [chunk.text for chunk in chunks]
                embeddings = await embedding_service.embed_texts(chunk_texts)
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding
                logger.info(f"✅ Generated {len(embeddings)} embeddings ({settings.embedding_dimensions}-dim)")
            except Exception as e:
                logger.warning(f"⚠️ Embedding generation failed (non-fatal): {e}")

            # 7. Store parsed text and chunks (with embeddings)
            logger.info(f"💾 [5/6] Storing parsed text and {len(chunks)} chunks...")

            # Store full text in Cloud Storage
            text_path = f"projects/{project_id}/documents/{doc_id}/text.txt"
            await self.storage.upload_text(full_text, text_path)

            # Store chunks in Firestore
            await self.firestore.store_chunks(chunks)
            logger.info(f"✅ Storage complete")

            # 8. Update document with complete status
            logger.info(f"📝 [6/6] Finalizing document record...")
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

            logger.info(f"🎉 Document {filename} processed successfully! ({doc_id})")
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
        filename: str,
        doc_id: str
    ) -> Tuple[str, List[Chunk], ChomperMetadata]:
        """
        Parse document using Chomper library.

        Supports 36+ formats: PDF, DOCX, PPTX, XLSX, HTML, TXT, CSV, etc.

        Args:
            file_data: File bytes
            filename: Original filename
            doc_id: Document ID for chunk association

        Returns:
            Tuple of (full_text, chunks, chomper_metadata)
        """
        from ..config import settings
        import chomper

        # Parse document bytes (sync call → offload to thread pool)
        result = await asyncio.to_thread(
            chomper.parse_bytes, file_data, filename
        )
        full_text = result.text

        # Chunk document (needs file path, so write temp file)
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(filename).suffix
        ) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name

        try:
            chunk_results = await asyncio.to_thread(
                chomper.chunk,
                tmp_path,
                strategy="auto",
                chunk_size=settings.chunk_size,
                overlap=settings.chunk_overlap,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # Convert Chomper ChunkResult → our Chunk model
        chunks = []
        for cr in chunk_results:
            chunks.append(Chunk(
                chunk_id=generate_chunk_id(doc_id, cr.chunk_id),
                doc_id=doc_id,
                chunk_index=cr.chunk_id,
                text=cr.text,
                word_count=cr.word_count,
                start_position=cr.start_char,
                end_position=cr.end_char,
                keywords=getattr(cr, 'keywords', []),
                section_name=getattr(cr, 'section_name', None),
            ))

        # Build metadata from parse result
        chomper_meta = ChomperMetadata(
            format=result.format,
            page_count=result.metadata.get('page_count'),
            word_count=result.word_count,
            char_count=result.char_count,
            has_images=len(result.images) > 0,
            has_tables='table' in full_text.lower(),
        )

        logger.info(f"Chomper parsed {filename}: {result.format}, {result.word_count} words")
        return full_text, chunks, chomper_meta


# Global service instance
document_service = DocumentService()
