"""
Tier 1: Heuristic noise filter for Enron emails.

Zero AI, zero cost, runs in seconds. Uses regex, keyword matching,
header analysis, and folder/subject patterns to score each email's
relevance to BRD content.

Scoring approach: each email gets a 0.0-1.0 relevance score based on
weighted signals. High score = likely contains project requirements,
decisions, or stakeholder feedback. Low score = likely noise.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Set, Tuple

from .enron_loader import EnronEmail

logger = logging.getLogger(__name__)


# ─── Signal definitions ──────────────────────────────────────────────

# Keywords that suggest BRD-relevant content (requirements, decisions, etc.)
BRD_POSITIVE_KEYWORDS: Set[str] = {
    # Requirements
    "requirement", "requirements", "specification", "specifications",
    "scope", "deliverable", "deliverables", "milestone", "milestones",
    # Decisions
    "decision", "decided", "approved", "approve", "approval",
    "rejected", "agreed", "agreement", "consensus",
    # Project management
    "project", "timeline", "deadline", "schedule", "priority",
    "priorities", "roadmap", "phase", "sprint", "release",
    # Stakeholder
    "stakeholder", "sponsor", "budget", "cost", "resource",
    "resources", "allocation", "funding",
    # Technical
    "architecture", "design", "implementation", "integration",
    "infrastructure", "platform", "system", "feature", "features",
    "functionality", "interface", "module", "component",
    # Business
    "business case", "proposal", "strategy", "objective", "objectives",
    "goal", "goals", "constraint", "constraints", "risk", "risks",
    "compliance", "regulation", "policy",
    # Action
    "action item", "action items", "follow up", "follow-up",
    "next steps", "todo", "to-do", "assigned", "responsible",
}

# Keywords that suggest noise
NOISE_KEYWORDS: Set[str] = {
    "lunch", "dinner", "happy hour", "birthday", "potluck",
    "out of office", "ooo", "vacation", "holiday",
    "unsubscribe", "newsletter", "mailing list",
    "fantasy football", "march madness", "super bowl",
}

# Folders in Enron dataset that are typically noise
NOISE_FOLDERS: Set[str] = {
    "deleted_items", "junk", "spam", "_sent_mail",
    "calendar", "contacts", "drafts", "notes",
    "discussion_threads",  # often auto-generated
}

# Subject patterns indicating auto-generated or noise emails
NOISE_SUBJECT_PATTERNS: List[re.Pattern] = [
    re.compile(r"^(fw:\s*){3,}", re.IGNORECASE),        # FW: FW: FW: chains
    re.compile(r"^(re:\s*){5,}", re.IGNORECASE),         # Deep reply chains
    re.compile(r"out of office", re.IGNORECASE),
    re.compile(r"undeliverable", re.IGNORECASE),
    re.compile(r"delivery status", re.IGNORECASE),
    re.compile(r"auto.?reply", re.IGNORECASE),
    re.compile(r"automatic reply", re.IGNORECASE),
    re.compile(r"calendar:", re.IGNORECASE),
    re.compile(r"invitation:", re.IGNORECASE),
]


@dataclass
class FilterResult:
    """Result of heuristic filtering on a single email."""
    email: EnronEmail
    score: float               # 0.0-1.0 relevance score
    passed: bool               # Whether it passed the threshold
    signals: List[str]         # Human-readable reasons for the score


def _count_keyword_hits(text: str, keywords: Set[str]) -> int:
    """Count how many keywords from the set appear in the text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def score_email(em: EnronEmail) -> FilterResult:
    """
    Score a single email for BRD relevance.

    Scoring weights:
      +0.30  BRD keyword density in body (scaled: 1 hit=0.10, 3+=0.30)
      +0.20  BRD keywords in subject line
      +0.15  Reasonable recipient count (1-10 = targeted discussion)
      +0.15  Substantial body (50-500 words = real content)
      +0.10  Contains questions or action language
      +0.10  From a relevant folder (inbox, sent, business)
      -0.30  Noise keywords present
      -0.20  Noise subject pattern match
      -0.20  Mass email (20+ recipients)
      -0.15  Noise folder
      -0.10  Trivially short body (<15 words)
    """
    score = 0.0
    signals: List[str] = []
    combined_text = f"{em.subject} {em.body}"

    # ── Positive signals ──

    # Body keyword hits
    body_hits = _count_keyword_hits(em.body, BRD_POSITIVE_KEYWORDS)
    if body_hits >= 3:
        score += 0.30
        signals.append(f"+0.30 body_keywords({body_hits} hits)")
    elif body_hits >= 1:
        kw_score = round(body_hits * 0.10, 2)
        score += kw_score
        signals.append(f"+{kw_score} body_keywords({body_hits} hits)")

    # Subject keyword hits
    subj_hits = _count_keyword_hits(em.subject, BRD_POSITIVE_KEYWORDS)
    if subj_hits >= 1:
        score += 0.20
        signals.append(f"+0.20 subject_keywords({subj_hits} hits)")

    # Targeted discussion (1-10 recipients)
    if 1 <= em.total_recipients <= 10:
        score += 0.15
        signals.append(f"+0.15 targeted({em.total_recipients} recipients)")

    # Substantial body length
    if 50 <= em.word_count <= 500:
        score += 0.15
        signals.append(f"+0.15 substantial_body({em.word_count} words)")
    elif em.word_count > 500:
        score += 0.10  # Very long = might be a forward/thread dump
        signals.append(f"+0.10 long_body({em.word_count} words)")

    # Questions or action language
    action_patterns = [r"\?", r"please\s+(review|approve|confirm|update|provide)",
                       r"action item", r"next step", r"follow.?up", r"assigned to"]
    action_count = sum(
        1 for pat in action_patterns
        if re.search(pat, combined_text, re.IGNORECASE)
    )
    if action_count >= 1:
        score += 0.10
        signals.append(f"+0.10 action_language({action_count} patterns)")

    # Good folder
    good_folders = {"inbox", "sent", "sent_items", "business", "projects",
                    "all_documents", "notes_inbox"}
    if em.folder.lower() in good_folders:
        score += 0.10
        signals.append(f"+0.10 good_folder({em.folder})")

    # ── Negative signals ──

    # Noise keywords
    noise_hits = _count_keyword_hits(combined_text, NOISE_KEYWORDS)
    if noise_hits >= 1:
        score -= 0.30
        signals.append(f"-0.30 noise_keywords({noise_hits} hits)")

    # Noise subject pattern
    for pattern in NOISE_SUBJECT_PATTERNS:
        if pattern.search(em.subject):
            score -= 0.20
            signals.append(f"-0.20 noise_subject({pattern.pattern[:30]})")
            break  # Only penalize once

    # Mass email
    if em.total_recipients > 20:
        score -= 0.20
        signals.append(f"-0.20 mass_email({em.total_recipients} recipients)")

    # Noise folder
    if em.folder.lower() in NOISE_FOLDERS:
        score -= 0.15
        signals.append(f"-0.15 noise_folder({em.folder})")

    # Trivially short
    if em.word_count < 15:
        score -= 0.10
        signals.append(f"-0.10 too_short({em.word_count} words)")

    # Clamp to [0.0, 1.0]
    score = max(0.0, min(1.0, score))

    return FilterResult(
        email=em,
        score=round(score, 3),
        passed=False,  # Set by the batch filter
        signals=signals,
    )


def apply_heuristic_filter(
    emails: List[EnronEmail],
    threshold: float = 0.15,
) -> Tuple[List[FilterResult], dict]:
    """
    Apply heuristic scoring to a batch of emails.

    Args:
        emails: List of parsed EnronEmail objects
        threshold: Minimum score to pass (default 0.15 — very permissive,
                   since Tier 2 embeddings will refine further)

    Returns:
        (passed_results, stats) where stats has counts for logging
    """
    results = []
    passed = []
    dropped = 0

    for em in emails:
        result = score_email(em)
        if result.score >= threshold:
            result.passed = True
            passed.append(result)
        else:
            dropped += 1
        results.append(result)

    # Score distribution for logging
    scores = [r.score for r in results]
    stats = {
        "total": len(emails),
        "passed": len(passed),
        "dropped": dropped,
        "pass_rate": f"{len(passed)/max(len(emails),1)*100:.1f}%",
        "avg_score": round(sum(scores) / max(len(scores), 1), 3),
        "max_score": max(scores) if scores else 0,
        "min_score": min(scores) if scores else 0,
    }

    logger.info(
        f"  Heuristic filter: {stats['passed']:,}/{stats['total']:,} passed "
        f"(threshold={threshold}, avg_score={stats['avg_score']})"
    )

    return passed, stats
