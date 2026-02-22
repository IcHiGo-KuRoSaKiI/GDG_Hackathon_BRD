"""
Project Curation: Extract, deduplicate, rank, and export emails per project.

Reads projects_discovered.json from eda_discover.py, scans the full CSV once,
matches emails against all projects simultaneously, deduplicates, ranks with
Gemini embeddings, and exports curated .txt files per project folder.

Usage:
    python -m backend.preprocessing.curate_project \
        --enron-csv enron_dataset/emails.csv \
        --discovery-file eda_output/projects_discovered.json

    # Fast mode (no API cost):
    python -m backend.preprocessing.curate_project \
        --enron-csv enron_dataset/emails.csv \
        --discovery-file eda_output/projects_discovered.json \
        --skip-embeddings
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ─── Imports from existing pipeline ─────────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.preprocessing.enron_loader import EnronEmail, load_enron_csv, load_enron_csv_parallel
from backend.preprocessing.heuristic_filter import FilterResult, score_email
from backend.preprocessing.embedding_filter import (
    EmbeddingResult,
    apply_embedding_filter,
)
from backend.preprocessing.bulk_importer import export_to_directory
from backend.preprocessing.eda_discover import normalize_subject, JUNK_FOLDERS

logger = logging.getLogger(__name__)


# ─── Data structures ────────────────────────────────────────────

@dataclass
class ProjectConfig:
    """Configuration for a single project's curation."""
    name: str
    slug: str
    keywords: List[str]
    seed_queries: List[str]
    is_deep: bool
    top_k: int
    discovery_score: float


@dataclass(frozen=True)
class DedupeKey:
    """Deduplication identity for an email."""
    normalized_subject: str
    sender: str
    date_prefix: str  # first 16 chars (e.g. "Mon, 25 Jun 2001")


# ─── Discovery file loading ─────────────────────────────────────

def _make_slug(name: str) -> str:
    """Convert project name to filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:50]


def load_discovery(
    discovery_path: str,
    deep_top_k: int = 30,
    other_top_k: int = 10,
) -> List[ProjectConfig]:
    """Load projects_discovered.json into ProjectConfig list."""
    with open(discovery_path) as f:
        data = json.load(f)

    projects = []
    for p in data["projects"]:
        is_deep = p.get("is_deep_project", False)
        projects.append(ProjectConfig(
            name=p["name"],
            slug=_make_slug(p["name"]),
            keywords=[kw.lower() for kw in p["keywords"]],
            seed_queries=p["seed_queries"],
            is_deep=is_deep,
            top_k=deep_top_k if is_deep else other_top_k,
            discovery_score=p.get("discovery_score", 0),
        ))

    return projects


# ─── Email matching ─────────────────────────────────────────────

def matches_project(email: EnronEmail, project: ProjectConfig) -> bool:
    """Check if an email belongs to a project via subject matching.

    Matches when the normalized subject contains (or is contained by) the
    project name, or when 60%+ of the project name's significant words
    appear in the email subject. Body-only matching is intentionally
    excluded to avoid false positives from generic keywords.
    """
    norm_subject = normalize_subject(email.subject).lower()
    project_name_lower = project.name.lower()

    # Exact containment: project name in subject or vice versa
    if project_name_lower in norm_subject or norm_subject in project_name_lower:
        return True

    # Significant-word overlap: 60%+ of the project name words in the subject
    filler = {"the", "a", "an", "of", "for", "and", "or", "in", "to", "with", "at", "by", "on"}
    name_words = set(project_name_lower.split()) - filler
    if not name_words:
        return False
    subject_words = set(norm_subject.split())
    overlap = name_words & subject_words
    if len(overlap) / len(name_words) >= 0.6:
        return True

    return False


# ─── Deduplication ───────────────────────────────────────────────

def make_dedupe_key(email: EnronEmail) -> DedupeKey:
    """Create dedup key from normalized subject + sender + date prefix."""
    return DedupeKey(
        normalized_subject=normalize_subject(email.subject),
        sender=(email.sender or "").lower().strip(),
        date_prefix=(email.date or "")[:16],
    )


# ─── Single-pass extraction ─────────────────────────────────────

def extract_all_projects(
    csv_path: str,
    projects: List[ProjectConfig],
    chunk_size: int = 5000,
    parallel: bool = False,
) -> Dict[str, List[FilterResult]]:
    """
    Single pass through CSV, extract emails for ALL projects simultaneously.
    Deduplicates within each project. Scores with heuristic filter.
    """
    # Per-project state
    project_emails: Dict[str, List[FilterResult]] = {p.slug: [] for p in projects}
    project_seen: Dict[str, Set[DedupeKey]] = {p.slug: set() for p in projects}

    total = 0
    matched_total = 0
    batch_num = 0

    loader = (
        load_enron_csv_parallel(csv_path, chunk_size=chunk_size)
        if parallel
        else load_enron_csv(csv_path, chunk_size=chunk_size)
    )
    for batch in loader:
        batch_num += 1
        for em in batch:
            total += 1

            # Skip junk folders
            folder_lower = (em.folder or "").lower()
            if folder_lower in JUNK_FOLDERS:
                continue

            # Check against each project
            for project in projects:
                if matches_project(em, project):
                    key = make_dedupe_key(em)
                    if key not in project_seen[project.slug]:
                        project_seen[project.slug].add(key)
                        fr = score_email(em)
                        project_emails[project.slug].append(fr)
                        matched_total += 1

        if batch_num % 20 == 0:
            logger.info(
                f"  Scanned {total:,} emails, {matched_total:,} matches across all projects"
            )

    logger.info(f"  Extraction complete: {total:,} scanned, {matched_total:,} total matches")

    for p in projects:
        count = len(project_emails[p.slug])
        logger.info(f"    {p.name[:40]:40s} → {count:>5,} emails (deduped)")

    return project_emails


# ─── Ranking ─────────────────────────────────────────────────────

async def rank_project_emails(
    project: ProjectConfig,
    filter_results: List[FilterResult],
    skip_embeddings: bool = False,
    api_key: Optional[str] = None,
) -> List[EmbeddingResult]:
    """Rank a project's emails. Uses embeddings or falls back to heuristic-only."""
    if not filter_results:
        return []

    if skip_embeddings:
        # Sort by heuristic score, take top_k, wrap as EmbeddingResult
        sorted_results = sorted(filter_results, key=lambda r: r.score, reverse=True)
        top = sorted_results[:project.top_k]
        return [
            EmbeddingResult(
                filter_result=fr,
                embedding_score=0.0,
                combined_score=fr.score,
                best_matching_query="N/A (embeddings skipped)",
            )
            for fr in top
        ]

    # Use embedding filter with project-specific seed queries
    results, stats = await apply_embedding_filter(
        filter_results=filter_results,
        top_k=project.top_k,
        seed_queries=project.seed_queries,
        api_key=api_key,
    )

    logger.info(
        f"    {project.name[:30]:30s} — "
        f"ranked {stats.get('total', 0)} → kept {stats.get('kept', 0)}"
    )
    return results


# ─── Export ──────────────────────────────────────────────────────

async def export_project(
    project: ProjectConfig,
    results: List[EmbeddingResult],
    base_output_dir: str,
) -> Dict[str, Any]:
    """Export a project's curated emails as .txt files."""
    if not results:
        return {"project": project.name, "exported": 0}

    output_dir = str(Path(base_output_dir) / project.slug)
    stats = await export_to_directory(results, output_dir)

    logger.info(f"    Exported {stats['exported']} emails to {output_dir}/")
    return {"project": project.name, "slug": project.slug, **stats}


# ─── Main pipeline ──────────────────────────────────────────────

async def curate_all_projects(
    csv_path: str,
    discovery_path: str,
    output_dir: str,
    deep_top_k: int = 30,
    other_top_k: int = 10,
    skip_embeddings: bool = False,
    api_key: Optional[str] = None,
    chunk_size: int = 5000,
    parallel: bool = False,
) -> Dict[str, Any]:
    """Main curation pipeline: load → extract → rank → export."""
    start = time.time()

    # 1. Load discovery
    print("\n  Loading discovered projects...")
    projects = load_discovery(discovery_path, deep_top_k, other_top_k)
    print(f"  Found {len(projects)} projects ({sum(1 for p in projects if p.is_deep)} deep)\n")

    for p in projects:
        label = "DEEP" if p.is_deep else "    "
        print(f"  {label}  {p.name[:45]:45s}  top_k={p.top_k}  keywords={len(p.keywords)}")
    print()

    # 2. Single-pass extraction
    print(f"  Extracting emails from CSV ({'parallel' if parallel else 'sequential'})...")
    project_emails = extract_all_projects(csv_path, projects, chunk_size, parallel=parallel)
    print()

    # 3. Rank each project
    print("  Ranking emails per project...")
    project_results: Dict[str, List[EmbeddingResult]] = {}
    for project in projects:
        emails = project_emails[project.slug]
        if not emails:
            logger.warning(f"  No emails found for {project.name} — skipping")
            project_results[project.slug] = []
            continue

        results = await rank_project_emails(
            project, emails, skip_embeddings, api_key
        )
        project_results[project.slug] = results
    print()

    # 4. Export each project
    print("  Exporting curated sets...")
    export_stats = []
    for project in projects:
        results = project_results[project.slug]
        stats = await export_project(project, results, output_dir)
        stats["is_deep"] = project.is_deep
        stats["matched"] = len(project_emails[project.slug])
        export_stats.append(stats)
    print()

    elapsed = time.time() - start

    # 5. Summary
    summary = {
        "csv_path": csv_path,
        "discovery_file": discovery_path,
        "projects": export_stats,
        "totals": {
            "total_matched": sum(s.get("matched", 0) for s in export_stats),
            "total_exported": sum(s.get("exported", 0) for s in export_stats),
            "processing_time_seconds": round(elapsed, 1),
        },
    }

    # Write summary
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "_curation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print_curation_summary(summary)
    return summary


# ─── Display ─────────────────────────────────────────────────────

def print_curation_summary(summary: Dict[str, Any]) -> None:
    """Print formatted curation results."""
    print("=" * 80)
    print("  CURATION RESULTS")
    print("=" * 80)

    print(f"\n  {'Project':40s}  {'Matched':>8}  {'Exported':>9}  {'Type':>6}")
    print("  " + "-" * 70)
    for s in summary["projects"]:
        ptype = "DEEP" if s.get("is_deep") else "light"
        name = s.get("project", "?")[:40]
        print(
            f"  {name:40s}  {s.get('matched', 0):>8,}  "
            f"{s.get('exported', 0):>9,}  {ptype:>6}"
        )

    totals = summary["totals"]
    print("  " + "-" * 70)
    print(
        f"  {'TOTAL':40s}  {totals['total_matched']:>8,}  "
        f"{totals['total_exported']:>9,}"
    )
    print(f"\n  Time: {totals['processing_time_seconds']}s")
    print("=" * 80 + "\n")


# ─── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Curate Enron emails per discovered project"
    )
    parser.add_argument("--enron-csv", required=True, help="Path to emails.csv")
    parser.add_argument("--discovery-file", required=True, help="Path to projects_discovered.json")
    parser.add_argument("--output-dir", default="curated_sets", help="Base output directory")
    parser.add_argument("--deep-top-k", type=int, default=30, help="Emails for deep project")
    parser.add_argument("--other-top-k", type=int, default=10, help="Emails for other projects")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip Gemini embeddings")
    parser.add_argument("--gemini-api-key", default=None, help="Gemini API key")
    parser.add_argument("--chunk-size", type=int, default=5000, help="CSV batch size")
    parser.add_argument("--parallel", action="store_true", help="Use multiprocessing for faster CSV parsing")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()

    # Load .env for API key
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env")
        load_dotenv(Path(__file__).parent / ".env")
    except ImportError:
        pass

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    api_key = args.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not args.skip_embeddings and not api_key:
        print("  WARNING: No GEMINI_API_KEY found. Use --skip-embeddings or set the key.")
        print("  Falling back to --skip-embeddings mode.\n")
        args.skip_embeddings = True

    asyncio.run(curate_all_projects(
        csv_path=args.enron_csv,
        discovery_path=args.discovery_file,
        output_dir=args.output_dir,
        deep_top_k=args.deep_top_k,
        other_top_k=args.other_top_k,
        skip_embeddings=args.skip_embeddings,
        api_key=api_key,
        chunk_size=args.chunk_size,
        parallel=args.parallel,
    ))


if __name__ == "__main__":
    main()
