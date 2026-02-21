"""
Firestore database service.
Async CRUD operations for all entities.
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from google.cloud.firestore_v1 import AsyncClient
from google.cloud.firestore import Increment
from ..config import firestore_client
from ..models import Project, Document, BRD, Chunk, DeleteJob, User


class FirestoreService:
    """Service for Firestore database operations."""

    def __init__(self, client: AsyncClient = firestore_client):
        """
        Initialize Firestore service.

        Args:
            client: Firestore AsyncClient instance
        """
        self.client = client

    # ============================================================
    # PROJECTS
    # ============================================================

    async def create_project(self, project: Project) -> None:
        """
        Create a new project in Firestore.

        Args:
            project: Project model to store
        """
        doc_ref = self.client.collection('projects').document(project.project_id)
        await doc_ref.set(project.model_dump(mode='json'))

    async def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get project by ID.

        Args:
            project_id: Project ID to retrieve

        Returns:
            Project model or None if not found
        """
        doc_ref = self.client.collection('projects').document(project_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        # Convert ISO strings back to datetime
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return Project(**data)

    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> None:
        """
        Update project fields.

        Args:
            project_id: Project ID to update
            updates: Dictionary of fields to update
        """
        doc_ref = self.client.collection('projects').document(project_id)
        updates['updated_at'] = datetime.utcnow().isoformat()
        await doc_ref.update(updates)

    # ============================================================
    # DOCUMENTS
    # ============================================================

    async def create_document(self, document: Document) -> None:
        """
        Create a new document in Firestore.

        Args:
            document: Document model to store
        """
        doc_ref = self.client.collection('documents').document(document.doc_id)
        await doc_ref.set(document.model_dump(mode='json'))

        # Increment project document count
        await self.update_project(document.project_id, {'document_count': Increment(1)})

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Get document by ID.

        Args:
            doc_id: Document ID to retrieve

        Returns:
            Document model or None if not found
        """
        doc_ref = self.client.collection('documents').document(doc_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        # Convert ISO strings back to datetime
        data['uploaded_at'] = datetime.fromisoformat(data['uploaded_at'])
        if data.get('processed_at'):
            data['processed_at'] = datetime.fromisoformat(data['processed_at'])
        return Document(**data)

    async def update_document(self, doc_id: str, updates: Dict[str, Any]) -> None:
        """
        Update document fields.

        Args:
            doc_id: Document ID to update
            updates: Dictionary of fields to update
        """
        doc_ref = self.client.collection('documents').document(doc_id)
        await doc_ref.update(updates)

    async def list_documents(self, project_id: str) -> List[Document]:
        """
        List all documents for a project.

        Args:
            project_id: Project ID to query

        Returns:
            List of Document models
        """
        query = self.client.collection('documents').where('project_id', '==', project_id)
        docs = query.stream()

        documents = []
        async for doc in docs:
            data = doc.to_dict()
            # Convert ISO strings back to datetime
            data['uploaded_at'] = datetime.fromisoformat(data['uploaded_at'])
            if data.get('processed_at'):
                data['processed_at'] = datetime.fromisoformat(data['processed_at'])
            documents.append(Document(**data))

        return documents

    # ============================================================
    # CHUNKS
    # ============================================================

    async def store_chunks(self, chunks: List[Chunk]) -> None:
        """
        Store document chunks in batch.

        Args:
            chunks: List of Chunk models to store
        """
        # Use batch write for efficiency
        batch = self.client.batch()

        for chunk in chunks:
            doc_ref = self.client.collection('chunks').document(chunk.chunk_id)
            batch.set(doc_ref, chunk.model_dump(mode='json'))

        await batch.commit()

    async def get_chunks(self, doc_id: str) -> List[Chunk]:
        """
        Get all chunks for a document.

        Args:
            doc_id: Document ID to query

        Returns:
            List of Chunk models, sorted by chunk_index
        """
        query = self.client.collection('chunks').where('doc_id', '==', doc_id).order_by('chunk_index')
        docs = query.stream()

        chunks = []
        async for doc in docs:
            data = doc.to_dict()
            chunks.append(Chunk(**data))

        return chunks

    async def get_project_chunks_with_embeddings(self, project_id: str) -> List[Dict]:
        """
        Load all chunks for a project that have embeddings.

        Joins through documents collection to find all chunks belonging
        to a project, then filters for those with embeddings.

        Args:
            project_id: Project ID

        Returns:
            List of chunk dicts with embedding vectors included
        """
        # Get all doc_ids for this project
        docs_query = self.client.collection("documents").where("project_id", "==", project_id)
        doc_ids = []
        doc_metadata = {}

        async for doc in docs_query.stream():
            data = doc.to_dict()
            doc_ids.append(doc.id)
            doc_metadata[doc.id] = {
                "filename": data.get("filename", ""),
                "doc_id": doc.id,
            }

        if not doc_ids:
            return []

        # Firestore 'in' queries support max 30 values
        all_chunks = []
        batch_size = 30

        for i in range(0, len(doc_ids), batch_size):
            batch_ids = doc_ids[i:i + batch_size]
            chunks_query = self.client.collection("chunks").where("doc_id", "in", batch_ids)

            async for chunk_doc in chunks_query.stream():
                chunk_data = chunk_doc.to_dict()
                if chunk_data.get("embedding"):
                    chunk_data["filename"] = doc_metadata.get(
                        chunk_data.get("doc_id", ""), {}
                    ).get("filename", "")
                    all_chunks.append(chunk_data)

        all_chunks.sort(key=lambda c: (c.get("doc_id", ""), c.get("chunk_index", 0)))
        return all_chunks

    async def update_chunks_embeddings_batch(
        self, chunk_embedding_pairs: List[Tuple[str, List[float]]]
    ) -> None:
        """
        Batch update embeddings for multiple chunks (for backfill).

        Args:
            chunk_embedding_pairs: List of (chunk_id, embedding_vector) tuples
        """
        batch_size = 500

        for i in range(0, len(chunk_embedding_pairs), batch_size):
            batch = self.client.batch()
            batch_pairs = chunk_embedding_pairs[i:i + batch_size]

            for chunk_id, embedding in batch_pairs:
                doc_ref = self.client.collection("chunks").document(chunk_id)
                batch.update(doc_ref, {"embedding": embedding})

            await batch.commit()

    # ============================================================
    # BRDS
    # ============================================================

    async def create_brd(self, brd: BRD) -> None:
        """
        Create a new BRD in Firestore.

        Args:
            brd: BRD model to store
        """
        doc_ref = self.client.collection('brds').document(brd.brd_id)
        await doc_ref.set(brd.model_dump(mode='json'))

        # Increment project BRD count
        await self.update_project(brd.project_id, {'brd_count': Increment(1)})

    async def get_brd(self, brd_id: str) -> Optional[BRD]:
        """
        Get BRD by ID.

        Args:
            brd_id: BRD ID to retrieve

        Returns:
            BRD model or None if not found
        """
        doc_ref = self.client.collection('brds').document(brd_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        # Convert ISO strings back to datetime
        data['generated_at'] = datetime.fromisoformat(data['generated_at'])
        return BRD(**data)

    async def list_brds(self, project_id: str) -> List[BRD]:
        """
        List all BRDs for a project.

        Args:
            project_id: Project ID to query

        Returns:
            List of BRD models
        """
        query = self.client.collection('brds').where('project_id', '==', project_id)
        docs = query.stream()

        brds = []
        async for doc in docs:
            data = doc.to_dict()
            # Convert ISO strings back to datetime
            data['generated_at'] = datetime.fromisoformat(data['generated_at'])
            brds.append(BRD(**data))

        return brds

    # ============================================================
    # DELETION JOBS
    # ============================================================

    async def create_deletion_job(self, job: DeleteJob) -> None:
        """
        Create a new deletion job in Firestore.

        Args:
            job: DeleteJob model to store
        """
        doc_ref = self.client.collection('deletion_jobs').document(job.deletion_id)
        await doc_ref.set(job.to_dict())

    async def get_deletion_job(self, deletion_id: str) -> Optional[DeleteJob]:
        """
        Get deletion job by ID.

        Args:
            deletion_id: Deletion job ID to retrieve

        Returns:
            DeleteJob model or None if not found
        """
        doc_ref = self.client.collection('deletion_jobs').document(deletion_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        return DeleteJob.from_dict(data)

    async def update_deletion_job(self, deletion_id: str, updates: Dict[str, Any]) -> None:
        """
        Update deletion job fields.

        Args:
            deletion_id: Deletion job ID to update
            updates: Dictionary of fields to update
        """
        doc_ref = self.client.collection('deletion_jobs').document(deletion_id)
        await doc_ref.update(updates)

    async def list_deletion_jobs(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[DeleteJob]:
        """
        List deletion jobs with optional filters.

        Args:
            user_id: Filter by user ID (optional)
            project_id: Filter by project ID (optional)
            status: Filter by status (optional)
            limit: Maximum number of jobs to return

        Returns:
            List of DeleteJob models
        """
        query = self.client.collection('deletion_jobs')

        if user_id:
            query = query.where('user_id', '==', user_id)
        if project_id:
            query = query.where('project_id', '==', project_id)
        if status:
            query = query.where('status', '==', status)

        query = query.order_by('created_at', direction='DESCENDING').limit(limit)
        docs = query.stream()

        jobs = []
        async for doc in docs:
            data = doc.to_dict()
            jobs.append(DeleteJob.from_dict(data))

        return jobs

    # ============================================================
    # DELETE OPERATIONS
    # ============================================================

    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a document from Firestore.

        Args:
            doc_id: Document ID to delete
        """
        doc_ref = self.client.collection('documents').document(doc_id)
        await doc_ref.delete()

    async def delete_chunks_batch(self, chunk_ids: List[str]) -> None:
        """
        Delete chunks in batch (max 500 per batch).

        Args:
            chunk_ids: List of chunk IDs to delete
        """
        # Firestore batch limit is 500 operations
        batch_size = 500

        for i in range(0, len(chunk_ids), batch_size):
            batch = self.client.batch()
            batch_chunk_ids = chunk_ids[i:i + batch_size]

            for chunk_id in batch_chunk_ids:
                doc_ref = self.client.collection('chunks').document(chunk_id)
                batch.delete(doc_ref)

            await batch.commit()

    async def update_brd_section(self, brd_id: str, section_key: str, content: str) -> dict:
        """
        Update a single BRD section's content using Firestore dot-notation.

        Args:
            brd_id: BRD ID to update
            section_key: Section key (e.g. 'executive_summary')
            content: New content for the section

        Returns:
            Updated section data dict
        """
        doc_ref = self.client.collection('brds').document(brd_id)
        await doc_ref.update({
            f'{section_key}.content': content,
            'updated_at': datetime.utcnow().isoformat(),
        })
        # Read back the updated section
        doc = await doc_ref.get()
        data = doc.to_dict()
        return data.get(section_key, {})

    async def update_conflict_status(
        self, brd_id: str, conflict_index: int, status: str, resolution: str | None = None
    ) -> dict:
        """
        Update a single conflict's status within a BRD.

        Firestore arrays can't be updated by index, so we read the full
        conflicts list, patch the target item, and write it back.

        Args:
            brd_id: BRD document ID
            conflict_index: 0-based index into the conflicts array
            status: New status value
            resolution: Optional resolution text

        Returns:
            The updated conflict dict

        Raises:
            ValueError: If index is out of range
        """
        doc_ref = self.client.collection('brds').document(brd_id)
        doc = await doc_ref.get()
        if not doc.exists:
            raise ValueError(f"BRD {brd_id} not found")

        data = doc.to_dict()
        conflicts = data.get('conflicts', [])

        if conflict_index < 0 or conflict_index >= len(conflicts):
            raise ValueError(
                f"Conflict index {conflict_index} out of range (0-{len(conflicts) - 1})"
            )

        conflicts[conflict_index]['status'] = status
        if resolution is not None:
            conflicts[conflict_index]['resolution'] = resolution

        await doc_ref.update({
            'conflicts': conflicts,
            'updated_at': datetime.utcnow().isoformat(),
        })
        return conflicts[conflict_index]

    async def delete_brd(self, brd_id: str) -> None:
        """
        Delete a BRD from Firestore.

        Args:
            brd_id: BRD ID to delete
        """
        doc_ref = self.client.collection('brds').document(brd_id)
        await doc_ref.delete()

    async def delete_project(self, project_id: str) -> None:
        """
        Delete a project from Firestore.

        Args:
            project_id: Project ID to delete
        """
        doc_ref = self.client.collection('projects').document(project_id)
        await doc_ref.delete()

    # ============================================================
    # USER OPERATIONS
    # ============================================================

    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID to retrieve

        Returns:
            User model or None if not found
        """
        doc_ref = self.client.collection('users').document(user_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        # Convert ISO strings back to datetime
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return User(**data)

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> None:
        """
        Update user fields.

        Args:
            user_id: User ID to update
            updates: Dictionary of fields to update
        """
        doc_ref = self.client.collection('users').document(user_id)
        await doc_ref.update(updates)


# Global service instance
firestore_service = FirestoreService()
