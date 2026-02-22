"""
EDA Discovery: Scan full Enron dataset and auto-discover top project threads.

Streams all ~500K emails, groups by normalized subject, scores threads
by email count × unique senders × log2(avg word count), and outputs
the top N project candidates with keywords and seed queries.

Usage:
    python -m backend.preprocessing.eda_discover \
        --enron-csv enron_dataset/emails.csv
"""

import argparse
import json
import logging
import math
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# ─── Imports from existing pipeline ─────────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.preprocessing.enron_loader import EnronEmail, load_enron_csv, load_enron_csv_parallel

logger = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────

JUNK_FOLDERS: Set[str] = {
    "all_documents", "discussion_threads", "deleted_items",
    "calendar", "contacts", "drafts", "junk", "spam",
    "notes",
    # NOTE: _sent_mail is the Notes-era sent folder — contains real project emails
}

_RE_FW_PREFIX = re.compile(r"^(re|fw|fwd)\s*:\s*", re.IGNORECASE)

# Generic subjects that are NOT projects — just common greetings/noise
GENERIC_SUBJECTS: Set[str] = {
    "hi", "hello", "hey", "lunch", "dinner", "fyi", "meeting", "thanks",
    "thank you", "update", "question", "help", "info", "information",
    "follow up", "followup", "reminder", "request", "urgent",
    "congratulations", "congrats", "welcome", "goodbye", "good morning",
    "happy holidays", "happy birthday", "invitation", "rsvp",
    "out of office", "vacation", "schedule", "calendar",
    "test", "testing", "draft", "misc", "stuff", "things",
    "heads up", "heads-up", "note", "notes", "memo",
    "happy hour", "contact info", "attached files", "phone list",
    "phone numbers", "new hire", "goodbye enron",
}

# Subjects that indicate newsletters/automated/corporate-wide content
NEWSLETTER_PATTERNS: List[re.Pattern] = [
    re.compile(r"enron mentions", re.IGNORECASE),
    re.compile(r"news\s*(letter|flash|brief)", re.IGNORECASE),
    re.compile(r"daily\s+(report|update|summary|briefing)", re.IGNORECASE),
    re.compile(r"press\s+(release|clipping|review)", re.IGNORECASE),
    re.compile(r"organi[sz]ation(al)?\s+(announcement|changes?)", re.IGNORECASE),
    re.compile(r"(weekly|monthly|quarterly)\s+(report|summary|update)", re.IGNORECASE),
    re.compile(r"market\s+(report|update|commentary)", re.IGNORECASE),
    re.compile(r"confidentiality\s+(agreement|notice)", re.IGNORECASE),
    re.compile(r"enron\s+center\s+garage", re.IGNORECASE),
    re.compile(r"your\s+approval\s+is\s+overdue", re.IGNORECASE),
    re.compile(r"expense\s+report", re.IGNORECASE),
    re.compile(r"action\s+required.{0,5}invoice", re.IGNORECASE),
]

# Words in subject that indicate a real project/initiative
PROJECT_INDICATOR_WORDS: Set[str] = {
    "project", "implementation", "requirements", "requirement",
    "specification", "design", "phase", "launch", "integration",
    "migration", "platform", "system", "proposal", "architecture",
    "rollout", "deployment", "prototype", "pilot", "kickoff",
    "kick-off", "deliverable", "milestone", "scope",
    "model", "infrastructure", "development",
    "testing", "release", "version", "upgrade", "plan",
    "strategy", "initiative", "program", "analysis", "assessment",
    "simulation", "restructuring", "re-start", "restart",
    # NOTE: "agreement" and "contract" removed — they're document types, not project activities
}

# Noise subject patterns — threads that look "projecty" but are actually corporate noise
NOISE_SUBJECT_PATTERNS: List[str] = [
    "organizational announcement", "organizational changes",
    "sap", "outage", "unsubscribe", "out of office",
    "energy issues", "enron mentions", "news digest",
    "program changes", "benefits", "holiday", "parking",
    "conference call", "time sensitive", "all hands",
    "succession plan", "isda master", "master netting",
    "2002 plan", "2001 plan", "401k", "health insurance",
    "direct deposit", "payroll", "it support", "help desk",
    "password reset", "system maintenance", "server downtime",
]

# BRD-signal words — indicate real project content in email bodies
BRD_SIGNAL_WORDS: Set[str] = {
    "requirements", "deliverables", "timeline", "milestone",
    "budget", "scope", "stakeholder", "specification",
    "proposal", "implementation", "rollout", "deployment",
    "approval", "sign-off", "phase", "deadline",
    "vendor", "contractor", "resource", "risk",
    "architecture", "design", "integration", "migration",
    "schedule", "cost", "estimate", "feasibility",
    "prototype", "pilot", "capacity", "infrastructure",
    "regulatory", "compliance", "contract", "pricing",
    "negotiate", "tariff", "pipeline", "turbine",
    "generator", "transmission", "substation", "voltage",
}

MIN_SUBJECT_WORDS = 2       # Require at least 2 words in normalized subject
MIN_SUBJECT_CHARS = 8       # Require at least 8 characters

STOPWORDS: Set[str] = {
    # English stopwords
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "and", "but", "or", "if", "while", "that", "this", "these", "those",
    "it", "its", "i", "me", "my", "we", "our", "you", "your", "he",
    "him", "his", "she", "her", "they", "them", "their", "what", "which",
    "who", "whom", "up", "about", "just", "also", "new", "one", "two",
    # Enron-specific noise
    "enron", "corp", "ect", "hou", "com", "net", "subject", "message",
    "email", "sent", "please", "thanks", "thank", "hi", "hello", "dear",
    "regards", "cc", "bcc", "forwarded", "original", "attached",
    "attachment", "meeting", "call", "let", "know", "get", "us",
}

SEED_QUERY_TEMPLATES: List[str] = [
    "project requirements and stakeholder decisions about {topic}",
    "technical specifications and implementation details for {topic}",
    "budget allocation and resource planning for {topic}",
    "risk assessment and compliance requirements for {topic}",
    "status updates, action items, and next steps regarding {topic}",
]


# ─── Data structures ────────────────────────────────────────────

@dataclass
class ThreadStats:
    """Accumulated stats for a normalized subject thread."""
    normalized_subject: str
    email_count: int = 0
    senders: Set[str] = field(default_factory=set)
    earliest_date: str = ""
    latest_date: str = ""
    total_word_count: int = 0
    brd_signal_hits: int = 0          # count of BRD-signal words across all bodies
    total_body_words: int = 0         # total words in all bodies (for density calc)
    sample_subjects: List[str] = field(default_factory=list)
    sample_body_snippets: List[str] = field(default_factory=list)


@dataclass
class DiscoveredProject:
    """A ranked project discovered from thread analysis."""
    rank: int
    name: str
    discovery_score: float
    email_count: int
    unique_senders: int
    avg_word_count: float
    date_range: str
    keywords: List[str]
    seed_queries: List[str]
    is_deep_project: bool = False


# ─── Subject normalization ──────────────────────────────────────

def normalize_subject(subject: str) -> str:
    """Strip Re:/FW:/Fwd: prefixes iteratively, collapse whitespace."""
    if not subject:
        return "(no subject)"
    s = subject.strip()
    # Strip prefixes in a loop
    prev = None
    while prev != s:
        prev = s
        s = _RE_FW_PREFIX.sub("", s).strip()
    return s if s else "(no subject)"


def is_project_worthy_subject(normalized: str) -> bool:
    """Check if a normalized subject looks like a real project thread, not noise."""
    if normalized == "(no subject)":
        return False

    lower = normalized.lower().strip()

    # Reject generic single-word/short subjects
    if lower in GENERIC_SUBJECTS:
        return False

    # Reject known noise subjects
    for noise in NOISE_SUBJECT_PATTERNS:
        if noise in lower:
            return False

    # Reject newsletters
    for pattern in NEWSLETTER_PATTERNS:
        if pattern.search(lower):
            return False

    # Require minimum length
    if len(lower) < MIN_SUBJECT_CHARS:
        return False

    # Require minimum word count
    words = lower.split()
    if len(words) < MIN_SUBJECT_WORDS:
        return False

    return True


# ─── Thread accumulation ────────────────────────────────────────

def accumulate_thread_stats(
    emails: List[EnronEmail],
    threads: Dict[str, ThreadStats],
    eda: Dict[str, Any],
    seen_messages: Set[str],
) -> None:
    """Process a batch of emails into thread stats. Mutates threads, eda, seen in-place."""
    for em in emails:
        eda["total_emails"] += 1

        # Skip junk folders
        folder_lower = (em.folder or "").lower()
        if folder_lower in JUNK_FOLDERS:
            eda["junk_skipped"] += 1
            continue

        # Track folder distribution
        eda["folder_counts"][folder_lower] = eda["folder_counts"].get(folder_lower, 0) + 1

        # Normalize subject and filter
        norm = normalize_subject(em.subject)
        if not is_project_worthy_subject(norm):
            eda["no_subject"] += 1
            continue

        # Deduplicate: same sender + date[:16] + normalized subject = same email in diff folders
        sender_lower = (em.sender or "").lower()
        date_prefix = (em.date or "")[:16]
        dedup_key = f"{norm}|{sender_lower}|{date_prefix}"
        if dedup_key in seen_messages:
            eda["duplicates_skipped"] = eda.get("duplicates_skipped", 0) + 1
            continue
        seen_messages.add(dedup_key)

        if norm not in threads:
            threads[norm] = ThreadStats(normalized_subject=norm)

        ts = threads[norm]
        ts.email_count += 1
        ts.total_word_count += em.word_count
        if em.sender:
            ts.senders.add(sender_lower)

        # Count BRD-signal words in body
        if em.body:
            body_words = set(em.body.lower().split())
            ts.brd_signal_hits += len(body_words & BRD_SIGNAL_WORDS)
            ts.total_body_words += len(body_words)

        # Track date range
        date_str = em.date or ""
        if date_str:
            if not ts.earliest_date or date_str < ts.earliest_date:
                ts.earliest_date = date_str
            if not ts.latest_date or date_str > ts.latest_date:
                ts.latest_date = date_str

        # Keep samples (up to 5)
        if len(ts.sample_subjects) < 5 and em.subject:
            ts.sample_subjects.append(em.subject)
        if len(ts.sample_body_snippets) < 5 and em.body:
            ts.sample_body_snippets.append(em.body[:300])


# ─── Scoring ────────────────────────────────────────────────────

def score_thread(ts: ThreadStats) -> float:
    """Score a thread for project-worthiness.

    Factors:
    - email_count: more emails = more discussion
    - unique_senders (capped at 25): too many senders = company-wide blast
    - log2(avg_word_count): substance, dampened to avoid long-forward bias
    - project_bonus: 10x multiplier if subject contains project-indicator words
    - signal_bonus: 1x–4x based on BRD-signal word density in bodies
    - sender_ratio_penalty: penalize if ratio of senders/emails is very high (blast)
    """
    avg_wc = ts.total_word_count / max(ts.email_count, 1)
    capped_wc = min(avg_wc, 500)  # cap to avoid forwarded-chain bias
    unique_senders = min(len(ts.senders), 25)  # cap to avoid blast-email bias

    base = ts.email_count * unique_senders * math.log2(capped_wc + 1)

    # Bonus for project-indicator words in subject
    subject_lower = ts.normalized_subject.lower()
    subject_words = set(subject_lower.split())
    has_project_word = bool(subject_words & PROJECT_INDICATOR_WORDS)
    project_bonus = 10.0 if has_project_word else 1.0

    # Bonus for BRD-signal words in email bodies (content quality)
    signal_density = ts.brd_signal_hits / max(ts.total_body_words, 1)
    signal_bonus = 1.0 + min(signal_density * 50, 3.0)  # 1x to 4x

    # Penalty for blast emails (many senders relative to emails = everyone gets it once)
    sender_ratio = len(ts.senders) / max(ts.email_count, 1)
    blast_penalty = 0.5 if sender_ratio > 0.6 else 1.0  # >60% unique = blast

    return base * project_bonus * signal_bonus * blast_penalty


# ─── Keyword extraction ────────────────────────────────────────

def extract_keywords(ts: ThreadStats, max_keywords: int = 10) -> List[str]:
    """Extract representative keywords from a thread's subjects and body snippets."""
    text = " ".join(ts.sample_subjects + ts.sample_body_snippets).lower()
    # Tokenize: keep alphanumeric words 3+ chars
    tokens = re.findall(r"[a-z]{3,}", text)
    # Remove stopwords
    filtered = [t for t in tokens if t not in STOPWORDS]
    # Count and return top
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(max_keywords)]


# ─── Seed query generation ──────────────────────────────────────

def generate_seed_queries(project_name: str, keywords: List[str]) -> List[str]:
    """Generate 5 BRD-relevant seed queries for a discovered project."""
    topic_parts = [project_name] + keywords[:3]
    topic = ", ".join(topic_parts)
    return [t.format(topic=topic) for t in SEED_QUERY_TEMPLATES]


# ─── Main discovery pipeline ────────────────────────────────────

def discover_projects(
    csv_path: str,
    top_n: int = 7,
    min_thread_size: int = 3,
    chunk_size: int = 5000,
    parallel: bool = False,
) -> Tuple[List[DiscoveredProject], Dict[str, Any]]:
    """Stream entire CSV, discover and rank top project threads."""
    start = time.time()

    threads: Dict[str, ThreadStats] = {}
    seen_messages: Set[str] = set()
    eda: Dict[str, Any] = {
        "total_emails": 0,
        "junk_skipped": 0,
        "no_subject": 0,
        "duplicates_skipped": 0,
        "folder_counts": {},
    }

    # Stream through CSV — parallel or sequential
    loader = (
        load_enron_csv_parallel(csv_path, chunk_size=chunk_size)
        if parallel
        else load_enron_csv(csv_path, chunk_size=chunk_size)
    )

    batch_num = 0
    for batch in loader:
        batch_num += 1
        accumulate_thread_stats(batch, threads, eda, seen_messages)
        if batch_num % 5 == 0:
            logger.info(
                f"  Processed {eda['total_emails']:,} emails, "
                f"{len(threads):,} unique threads so far..."
            )

    elapsed = time.time() - start
    processed = eda["total_emails"] - eda["junk_skipped"] - eda["no_subject"]

    # Filter threads by minimum size + quality gates
    candidates = [
        ts for ts in threads.values()
        if ts.email_count >= min_thread_size
        and len(ts.senders) >= 2                              # multi-person conversation
        and (ts.total_word_count / max(ts.email_count, 1)) >= 30  # not one-liners
    ]

    # Score and rank
    scored = [(score_thread(ts), ts) for ts in candidates]
    scored.sort(key=lambda x: x[0], reverse=True)

    # Build top N projects
    projects: List[DiscoveredProject] = []
    for i, (score, ts) in enumerate(scored[:top_n]):
        avg_wc = ts.total_word_count / max(ts.email_count, 1)
        keywords = extract_keywords(ts)
        name = ts.normalized_subject

        projects.append(DiscoveredProject(
            rank=i + 1,
            name=name,
            discovery_score=round(score, 1),
            email_count=ts.email_count,
            unique_senders=len(ts.senders),
            avg_word_count=round(avg_wc, 1),
            date_range=f"{ts.earliest_date} to {ts.latest_date}",
            keywords=keywords,
            seed_queries=generate_seed_queries(name, keywords),
            is_deep_project=(i == 0),
        ))

    # Sort folder distribution
    top_folders = dict(
        sorted(eda["folder_counts"].items(), key=lambda x: x[1], reverse=True)[:20]
    )

    eda_stats = {
        "total_emails": eda["total_emails"],
        "junk_skipped": eda["junk_skipped"],
        "duplicates_skipped": eda.get("duplicates_skipped", 0),
        "no_subject": eda["no_subject"],
        "processed": processed,
        "noise_pct": round(eda["junk_skipped"] / max(eda["total_emails"], 1) * 100, 1),
        "unique_normalized_subjects": len(threads),
        "threads_above_min_size": len(candidates),
        "folder_distribution": top_folders,
        "processing_time_seconds": round(elapsed, 1),
    }

    return projects, eda_stats


# ─── Output ─────────────────────────────────────────────────────

def save_results(
    projects: List[DiscoveredProject],
    eda_stats: Dict[str, Any],
    output_dir: str,
    csv_path: str,
) -> None:
    """Write projects_discovered.json and eda_stats.json."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Projects JSON
    projects_data = {
        "csv_path": csv_path,
        "projects": [
            {
                "rank": p.rank,
                "name": p.name,
                "discovery_score": p.discovery_score,
                "email_count": p.email_count,
                "unique_senders": p.unique_senders,
                "avg_word_count": p.avg_word_count,
                "date_range": p.date_range,
                "keywords": p.keywords,
                "seed_queries": p.seed_queries,
                "is_deep_project": p.is_deep_project,
            }
            for p in projects
        ],
    }
    with open(out / "projects_discovered.json", "w") as f:
        json.dump(projects_data, f, indent=2)

    # EDA stats JSON
    with open(out / "eda_stats.json", "w") as f:
        json.dump(eda_stats, f, indent=2)

    logger.info(f"Results saved to {output_dir}/")


def print_summary_table(
    projects: List[DiscoveredProject],
    eda_stats: Dict[str, Any],
) -> None:
    """Print formatted summary to console."""
    print("\n" + "=" * 80)
    print("  ENRON DATASET — EDA DISCOVERY RESULTS")
    print("=" * 80)
    print(f"  Total emails:       {eda_stats['total_emails']:,}")
    print(f"  Junk folders skipped: {eda_stats['junk_skipped']:,} ({eda_stats['noise_pct']}%)")
    print(f"  Duplicates removed: {eda_stats.get('duplicates_skipped', 0):,}")
    print(f"  Unique threads:     {eda_stats['unique_normalized_subjects']:,}")
    print(f"  Threads ≥ min size: {eda_stats['threads_above_min_size']:,}")
    print(f"  Processing time:    {eda_stats['processing_time_seconds']}s")
    print()

    # Folder distribution
    print("  Top folders:")
    for folder, count in list(eda_stats["folder_distribution"].items())[:8]:
        print(f"    {folder:25s} {count:>8,}")
    print()

    # Projects table
    print(f"  {'#':>2}  {'Project':40s}  {'Emails':>7}  {'Senders':>8}  {'Avg WC':>7}  {'Score':>10}  Deep?")
    print("  " + "-" * 90)
    for p in projects:
        deep = " ★" if p.is_deep_project else ""
        print(
            f"  {p.rank:>2}  {p.name[:40]:40s}  {p.email_count:>7,}  "
            f"{p.unique_senders:>8}  {p.avg_word_count:>7.0f}  "
            f"{p.discovery_score:>10,.0f}{deep}"
        )

    print()
    print("  Keywords for top project:")
    if projects:
        print(f"    {', '.join(projects[0].keywords)}")
    print("=" * 80 + "\n")


# ─── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Discover top project threads in the Enron email dataset"
    )
    parser.add_argument("--enron-csv", required=True, help="Path to emails.csv")
    parser.add_argument("--output-dir", default="eda_output", help="Output directory")
    parser.add_argument("--top-n", type=int, default=15, help="Number of projects to discover")
    parser.add_argument("--min-thread-size", type=int, default=3, help="Min emails per thread (after dedup)")
    parser.add_argument("--chunk-size", type=int, default=5000, help="CSV batch size")
    parser.add_argument("--parallel", action="store_true", help="Use multiprocessing for faster parsing")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    mode = "parallel" if args.parallel else "sequential"
    print(f"\n  Scanning {args.enron_csv} for top {args.top_n} projects ({mode})...\n")

    projects, eda_stats = discover_projects(
        csv_path=args.enron_csv,
        top_n=args.top_n,
        min_thread_size=args.min_thread_size,
        chunk_size=args.chunk_size,
        parallel=args.parallel,
    )

    save_results(projects, eda_stats, args.output_dir, args.enron_csv)
    print_summary_table(projects, eda_stats)

    print(f"  Output: {args.output_dir}/projects_discovered.json")
    print(f"  Next:   python -m backend.preprocessing.curate_project \\")
    print(f"            --enron-csv {args.enron_csv} \\")
    print(f"            --discovery-file {args.output_dir}/projects_discovered.json\n")


if __name__ == "__main__":
    main()
