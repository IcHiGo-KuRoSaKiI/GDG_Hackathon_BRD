"""
Embedding and RAG Retrieval Service.

Generates embeddings via text-embedding-004 and performs in-memory
cosine similarity search for chunk retrieval.
"""

import asyncio
import logging
import math
from typing import List, Dict, Any, Optional, Tuple

from ..config import genai_client, settings
from ..utils.retry import with_retry

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings and performing vector similarity search.

    Uses text-embedding-004 via the google-genai SDK (already installed).
    Performs in-memory cosine similarity — suitable for hackathon scale
    (typically <500 chunks per project).
    """

    def __init__(self):
        self.model_name = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self.top_k = settings.rag_top_k
        self.similarity_threshold = settings.rag_similarity_threshold

    # ================================================================
    # EMBEDDING GENERATION
    # ================================================================

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Batches in groups of 100 (API limit).
        """
        if not texts:
            return []

        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await asyncio.to_thread(
                self._embed_batch, batch
            )
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    @with_retry(max_attempts=3)
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Synchronous batch embedding call (runs in thread pool)."""
        result = genai_client.models.embed_content(
            model=self.model_name,
            contents=texts,
        )
        return [emb.values for emb in result.embeddings]

    # ================================================================
    # VECTOR SIMILARITY SEARCH
    # ================================================================

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Pure Python — no numpy needed. For 768-dim vectors and <500 chunks,
        this runs in <10ms.
        """
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        magnitude_a = math.sqrt(sum(a * a for a in vec_a))
        magnitude_b = math.sqrt(sum(b * b for b in vec_b))

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    async def retrieve_relevant_chunks(
        self,
        query: str,
        chunks_with_embeddings: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant chunks for a query using cosine similarity.

        Args:
            query: Search query text
            chunks_with_embeddings: Chunk dicts with 'embedding' key
            top_k: Override default top_k
            threshold: Override default similarity threshold

        Returns:
            Chunks with 'similarity_score' added, sorted by score descending
        """
        k = top_k or self.top_k
        min_score = threshold or self.similarity_threshold

        query_embedding = await self.embed_text(query)

        scored_chunks = []
        for chunk in chunks_with_embeddings:
            chunk_embedding = chunk.get("embedding")
            if not chunk_embedding:
                continue

            score = self.cosine_similarity(query_embedding, chunk_embedding)
            if score >= min_score:
                scored_chunks.append({
                    **chunk,
                    "similarity_score": round(score, 4),
                })

        scored_chunks.sort(key=lambda c: c["similarity_score"], reverse=True)
        return scored_chunks[:k]

    async def retrieve_for_multiple_queries(
        self,
        queries: List[str],
        chunks_with_embeddings: List[Dict[str, Any]],
        top_k_per_query: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for multiple queries, deduplicated by chunk_id.

        Used for BRD generation — queries for each section topic, returns
        a unified set of relevant chunks.

        Args:
            queries: List of search queries
            chunks_with_embeddings: All project chunks with embeddings
            top_k_per_query: Chunks per query (default: settings.rag_top_k)

        Returns:
            Deduplicated list of relevant chunks, sorted by best similarity score
        """
        if not chunks_with_embeddings:
            return []

        # Batch-embed all queries at once
        query_embeddings = await self.embed_texts(queries)

        # Score all chunks against all queries, keep best score per chunk
        chunk_best_scores: Dict[str, Tuple[float, Dict]] = {}

        for query_emb in query_embeddings:
            for chunk in chunks_with_embeddings:
                chunk_embedding = chunk.get("embedding")
                if not chunk_embedding:
                    continue

                score = self.cosine_similarity(query_emb, chunk_embedding)
                chunk_id = chunk["chunk_id"]

                if score >= self.similarity_threshold:
                    if chunk_id not in chunk_best_scores or score > chunk_best_scores[chunk_id][0]:
                        chunk_best_scores[chunk_id] = (score, {
                            **chunk,
                            "similarity_score": round(score, 4),
                        })

        # Sort by best score
        results = [item[1] for item in sorted(
            chunk_best_scores.values(),
            key=lambda x: x[0],
            reverse=True,
        )]

        return results


# Singleton instance
embedding_service = EmbeddingService()
