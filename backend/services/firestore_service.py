"""
Firestore database service.
Async CRUD operations for all entities.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from google.cloud.firestore_v1 import AsyncClient
from ..config import firestore_client
from ..models import Project, Document, BRD, Chunk


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
        await self.update_project(document.project_id, {'document_count': firestore_client.field('document_count').increment(1)})

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
        await self.update_project(brd.project_id, {'brd_count': firestore_client.field('brd_count').increment(1)})

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


# Global service instance
firestore_service = FirestoreService()
