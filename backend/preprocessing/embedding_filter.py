"""
Tier 2: Embedding-based relevance filter.

Uses Gemini's text-embedding-004 model to embed each email and compare
against BRD-relevant seed queries via cosine similarity.

Cost: ~$0.10 for 50K emails (embeddings are 1000x cheaper than generative).
Speed: ~5 minutes for 50K emails with batching + concurrency.
"""

import asyncio
import logging
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .heuristic_filter import FilterResult

logger = logging.getLogger(__name__)

# ─── Embedding model config ─────────────────────────────────────────

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768
BATCH_SIZE = 100          # Emails per API call (Gemini supports up to 100)
MAX_CONCURRENT = 5        # Parallel API calls (respect rate limits)
MAX_TEXT_LENGTH = 2000    # Chars per email to embed (subject + body preview)


# ─── Seed queries ────────────────────────────────────────────────────
# These define what "BRD-relevant" means. The embedding filter scores
# each email by its similarity to these queries.

BRD_SEED_QUERIES: List[str] = [
    "project requirements and technical specifications for software development",
    "stakeholder decision on feature prioritization and scope changes",
    "timeline and deadline discussion for project milestones and deliverables",
    "budget allocation, resource planning, and cost estimation for a project",
    "technical architecture decision and system design review",
    "business requirements gathering meeting with stakeholder feedback",
    "risk assessment and mitigation strategy for project delivery",
    "user requirements, acceptance criteria, and functional specifications",
    "project status update with blockers, action items, and next steps",
    "contract negotiation, service level agreement, and compliance requirements",
]


@dataclass
class EmbeddingResult:
    """Email with its embedding similarity score."""
    filter_result: FilterResult        # From Tier 1
    embedding_score: float             # Max cosine similarity to seed queries
    combined_score: float              # Weighted combo of heuristic + embedding
    best_matching_query: str           # Which seed query it matched best


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors. No numpy needed."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _prepare_email_text(fr: FilterResult) -> str:
    """Prepare email text for embedding: subject + body preview."""
    em = fr.email
    text = f"Subject: {em.subject}\n\n{em.body}"
    return text[:MAX_TEXT_LENGTH]


async def _embed_batch(
    client: object,
    texts: List[str],
    semaphore: asyncio.Semaphore,
) -> List[List[float]]:
    """Embed a batch of texts using Gemini embedding API."""
    async with semaphore:
        try:
            result = await asyncio.to_thread(
                client.models.embed_content,
                model=EMBEDDING_MODEL,
                contents=texts,
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            logger.warning(f"Embedding batch failed: {e}, returning zeros")
            return [[0.0] * EMBEDDING_DIMENSION] * len(texts)


async def _embed_seed_queries(
    client: object,
    seed_queries: Optional[List[str]] = None,
) -> List[List[float]]:
    """Embed seed queries (one small batch). Uses BRD_SEED_QUERIES if none provided."""
    queries = seed_queries or BRD_SEED_QUERIES
    logger.info(f"Embedding {len(queries)} seed queries...")
    result = await asyncio.to_thread(
        client.models.embed_content,
        model=EMBEDDING_MODEL,
        contents=queries,
    )
    return [e.values for e in result.embeddings]


async def apply_embedding_filter(
    filter_results: List[FilterResult],
    top_k: int = 2000,
    heuristic_weight: float = 0.3,
    embedding_weight: float = 0.7,
    api_key: Optional[str] = None,
    seed_queries: Optional[List[str]] = None,
) -> Tuple[List[EmbeddingResult], dict]:
    """
    Apply embedding-based relevance scoring to heuristic-filtered emails.

    Args:
        filter_results: Emails that passed Tier 1 heuristic filter
        top_k: Keep top K emails by combined score
        heuristic_weight: Weight for Tier 1 score in combined score
        embedding_weight: Weight for embedding similarity in combined score
        api_key: Gemini API key (falls back to GEMINI_API_KEY env var)
        seed_queries: Custom seed queries (falls back to BRD_SEED_QUERIES)

    Returns:
        (top_k_results, stats)
    """
    if not filter_results:
        return [], {"total": 0, "kept": 0}

    # Init Gemini client
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY not set. Pass api_key or set the env var."
        )
    from google import genai
    client = genai.Client(api_key=key)

    # Step 1: Embed seed queries
    queries = seed_queries or BRD_SEED_QUERIES
    seed_embeddings = await _embed_seed_queries(client, queries)

    # Step 2: Embed all emails in batches
    logger.info(f"Embedding {len(filter_results):,} emails in batches of {BATCH_SIZE}...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    email_texts = [_prepare_email_text(fr) for fr in filter_results]

    # Create batches
    batches = [
        email_texts[i:i + BATCH_SIZE]
        for i in range(0, len(email_texts), BATCH_SIZE)
    ]

    # Run batches concurrently (limited by semaphore)
    tasks = [_embed_batch(client, batch, semaphore) for batch in batches]
    batch_results = await asyncio.gather(*tasks)

    # Flatten embeddings
    all_embeddings: List[List[float]] = []
    for batch_embs in batch_results:
        all_embeddings.extend(batch_embs)

    logger.info(f"Embedded {len(all_embeddings):,} emails")

    # Step 3: Score each email against seed queries
    results: List[EmbeddingResult] = []
    for i, (fr, emb) in enumerate(zip(filter_results, all_embeddings)):
        # Max similarity across all seed queries
        similarities = [
            _cosine_similarity(emb, seed_emb)
            for seed_emb in seed_embeddings
        ]
        max_sim = max(similarities)
        best_idx = similarities.index(max_sim)

        # Combined score
        combined = (
            heuristic_weight * fr.score +
            embedding_weight * max_sim
        )

        results.append(EmbeddingResult(
            filter_result=fr,
            embedding_score=round(max_sim, 4),
            combined_score=round(combined, 4),
            best_matching_query=queries[best_idx],
        ))

        if (i + 1) % 10000 == 0:
            logger.info(f"  Scored {i+1:,}/{len(filter_results):,} emails")

    # Step 4: Sort by combined score, take top K
    results.sort(key=lambda r: r.combined_score, reverse=True)
    top_results = results[:top_k]

    # Stats
    all_scores = [r.combined_score for r in results]
    top_scores = [r.combined_score for r in top_results]
    stats = {
        "total": len(filter_results),
        "kept": len(top_results),
        "top_k": top_k,
        "all_avg_score": round(sum(all_scores) / max(len(all_scores), 1), 4),
        "top_avg_score": round(sum(top_scores) / max(len(top_scores), 1), 4),
        "top_min_score": min(top_scores) if top_scores else 0,
        "top_max_score": max(top_scores) if top_scores else 0,
    }

    logger.info(
        f"  Embedding filter: kept {stats['kept']:,}/{stats['total']:,} "
        f"(top_avg={stats['top_avg_score']}, min={stats['top_min_score']})"
    )

    return top_results, stats
