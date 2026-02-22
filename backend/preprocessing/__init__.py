"""
Preprocessing pipeline for large datasets (Enron emails, AMI transcripts).

Multi-tier ML funnel:
  Tier 1: Heuristic filter (free, instant) — regex, keywords, header analysis
  Tier 2: Embedding filter (pennies, minutes) — Gemini text-embedding + cosine similarity
  Tier 3: Existing AI pipeline — upload filtered docs to the BRD system

Usage:
    python -m backend.preprocessing --enron-csv emails.csv --output-dir ./filtered --top-k 2000
"""
