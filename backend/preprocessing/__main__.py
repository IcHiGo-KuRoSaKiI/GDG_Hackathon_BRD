"""
CLI entry point for the preprocessing pipeline.

Usage:
    # Full pipeline: filter + create project + upload (one command does everything)
    python -m backend.preprocessing \
        --enron-csv enron_dataset/emails.csv \
        --output-dir filtered_emails \
        --top-k 2000 \
        --upload \
        --project-name "Enron Energy Trading BRD" \
        --auth-token <jwt_token>

    # Tier 1 only (no API key needed, instant, just see the numbers)
    python -m backend.preprocessing \
        --enron-csv enron_dataset/emails.csv \
        --output-dir filtered_emails \
        --skip-embeddings

    # Filter + export only (no upload, no project creation)
    python -m backend.preprocessing \
        --enron-csv enron_dataset/emails.csv \
        --output-dir filtered_emails \
        --top-k 2000
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.preprocessing.enron_loader import load_enron_csv
from backend.preprocessing.heuristic_filter import apply_heuristic_filter
from backend.preprocessing.bulk_importer import (
    export_to_directory,
    create_project_and_upload,
    login,
)


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_pipeline(args: argparse.Namespace):
    """Execute the full preprocessing pipeline."""
    start_time = time.time()
    all_stats = {}

    # ── Banner ──
    print("\n" + "=" * 60)
    print("  ENRON EMAIL PREPROCESSING PIPELINE")
    print("=" * 60)
    print(f"\n  Input:       {args.enron_csv}")
    print(f"  Output:      {args.output_dir}")
    print(f"  Max emails:  {args.max_emails:,}" if args.max_emails else "  Max emails:  ALL")
    print(f"  Top-K:       {args.top_k}")
    print(f"  Tier 2:      {'ENABLED' if not args.skip_embeddings else 'SKIPPED'}")
    print(f"  Upload:      {'YES → create project + upload' if args.upload else 'NO (export only)'}")
    if args.upload:
        print(f"  Project:     \"{args.project_name}\"")
    print()

    # ── Tier 1: Load + Heuristic Filter ──
    print("[Tier 0+1] Loading Enron CSV + heuristic filtering...")
    tier1_start = time.time()

    all_passed = []
    combined_heuristic_stats = {
        "total": 0, "passed": 0, "dropped": 0,
    }

    for batch in load_enron_csv(args.enron_csv, chunk_size=args.chunk_size):
        passed, stats = apply_heuristic_filter(
            batch, threshold=args.heuristic_threshold
        )
        all_passed.extend(passed)
        combined_heuristic_stats["total"] += stats["total"]
        combined_heuristic_stats["passed"] += stats["passed"]
        combined_heuristic_stats["dropped"] += stats["dropped"]

        # Early exit if we've hit --max-emails cap
        if args.max_emails and combined_heuristic_stats["total"] >= args.max_emails:
            print(f"  [Cap] Reached --max-emails {args.max_emails:,}, stopping early.")
            break

    tier1_elapsed = time.time() - tier1_start
    combined_heuristic_stats["pass_rate"] = (
        f"{combined_heuristic_stats['passed'] / max(combined_heuristic_stats['total'], 1) * 100:.1f}%"
    )
    all_stats["tier1_heuristic"] = combined_heuristic_stats

    print(f"\n[Tier 1] Heuristic Filter Results:")
    print(f"  Total emails:  {combined_heuristic_stats['total']:,}")
    print(f"  Passed:        {combined_heuristic_stats['passed']:,}")
    print(f"  Dropped:       {combined_heuristic_stats['dropped']:,}")
    print(f"  Pass rate:     {combined_heuristic_stats['pass_rate']}")
    print(f"  Time:          {tier1_elapsed:.1f}s")

    # ── Tier 2: Embedding Filter ──
    if not args.skip_embeddings and all_passed:
        from backend.preprocessing.embedding_filter import apply_embedding_filter

        print(f"\n[Tier 2] Embedding Filter (top {args.top_k:,} from {len(all_passed):,})...")
        tier2_start = time.time()

        top_results, embed_stats = await apply_embedding_filter(
            all_passed,
            top_k=args.top_k,
            api_key=args.gemini_api_key,
        )
        tier2_elapsed = time.time() - tier2_start
        embed_stats["time_seconds"] = round(tier2_elapsed, 1)
        all_stats["tier2_embedding"] = embed_stats

        print(f"\n[Tier 2] Embedding Filter Results:")
        print(f"  Input:         {embed_stats['total']:,}")
        print(f"  Kept (top-k):  {embed_stats['kept']:,}")
        print(f"  Avg score:     {embed_stats['top_avg_score']}")
        print(f"  Score range:   {embed_stats['top_min_score']} - {embed_stats['top_max_score']}")
        print(f"  Time:          {tier2_elapsed:.1f}s")
    else:
        # Skip embeddings — take top by heuristic score
        all_passed.sort(key=lambda r: r.score, reverse=True)
        top_results = [
            type('EmbeddingResult', (), {
                'filter_result': r,
                'embedding_score': 0.0,
                'combined_score': r.score,
                'best_matching_query': 'N/A (embeddings skipped)',
            })()
            for r in all_passed[:args.top_k]
        ]
        all_stats["tier2_embedding"] = {"skipped": True, "kept": len(top_results)}
        print(f"\n[Tier 2] Skipped — using top {len(top_results):,} by heuristic score")

    if not top_results:
        print("\nNo emails passed the filters. Try lowering thresholds.")
        return

    # ── Export + Upload ──
    if args.upload:
        # Step 0: Login to get JWT token
        auth_token = args.auth_token
        if not auth_token:
            print(f"\n[Auth]    Logging in as {args.email}...")
            auth_token = await login(
                email=args.email,
                password=args.password,
                api_base_url=args.api_url,
            )
            print(f"[Auth]    Logged in successfully")

        # Full lifecycle: create project → export → upload
        print(f"[Project] Creating project \"{args.project_name}\"...")
        print(f"[Export]  Writing {len(top_results):,} emails to {args.output_dir}/")
        print(f"[Upload]  Uploading to {args.api_url}...")

        lifecycle_stats = await create_project_and_upload(
            results=top_results,
            project_name=args.project_name,
            project_description=args.project_description,
            output_dir=args.output_dir,
            api_base_url=args.api_url,
            auth_token=auth_token,
            batch_size=args.upload_batch_size,
            delay_between_batches=args.upload_delay,
        )
        all_stats["project"] = {
            "project_id": lifecycle_stats["project_id"],
            "project_name": lifecycle_stats["project_name"],
        }
        all_stats["export"] = lifecycle_stats["export"]
        all_stats["upload"] = lifecycle_stats["upload"]
    else:
        # Export only (no project creation, no upload)
        print(f"\n[Export] Writing {len(top_results):,} emails to {args.output_dir}/...")
        export_stats = await export_to_directory(top_results, args.output_dir)
        all_stats["export"] = export_stats

    # ── Summary ──
    total_elapsed = time.time() - start_time
    all_stats["total_time_seconds"] = round(total_elapsed, 1)

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Total time:    {total_elapsed:.1f}s")
    print(f"  Funnel:        {combined_heuristic_stats['total']:,}"
          f" -> {combined_heuristic_stats['passed']:,}"
          f" -> {len(top_results):,}")
    print(f"  Output:        {args.output_dir}/")

    if args.upload and "project" in all_stats:
        pid = all_stats["project"]["project_id"]
        print(f"  Project ID:    {pid}")
        print(f"  Project name:  {all_stats['project']['project_name']}")
        uploaded = all_stats.get("upload", {}).get("uploaded", 0)
        print(f"  Uploaded:      {uploaded:,} emails")
        print(f"\n  >> Open your frontend and go to project: {pid}")
        print(f"  >> Documents will be processing in the background")
        print(f"  >> Once done, hit 'Generate BRD' to create the report!")
    print()

    # Save stats
    stats_path = Path(args.output_dir) / "_pipeline_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(all_stats, indent=2, default=str))
    print(f"  Stats saved to: {stats_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess Enron email dataset for BRD generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test (Tier 1 only, see the numbers)
  python -m backend.preprocessing \\
      --enron-csv enron_dataset/emails.csv \\
      --output-dir filtered --skip-embeddings --top-k 500

  # Full filter pipeline (export only, no upload)
  python -m backend.preprocessing \\
      --enron-csv enron_dataset/emails.csv \\
      --output-dir filtered --top-k 2000

  # Full pipeline + create project + upload (one command)
  python -m backend.preprocessing \\
      --enron-csv enron_dataset/emails.csv \\
      --output-dir filtered --top-k 2000 \\
      --upload \\
      --project-name "Enron Energy Trading BRD" \\
      --auth-token YOUR_JWT_TOKEN
        """,
    )

    # Required
    parser.add_argument(
        "--enron-csv", required=True,
        help="Path to Enron emails.csv file"
    )
    parser.add_argument(
        "--output-dir", default="filtered_emails",
        help="Directory for exported filtered emails (default: filtered_emails)"
    )

    # Tier 1 config
    parser.add_argument(
        "--max-emails", type=int, default=0,
        help="Max emails to process (0 = all). Use 50000 for quick tests."
    )
    parser.add_argument(
        "--heuristic-threshold", type=float, default=0.15,
        help="Minimum heuristic score to pass Tier 1 (default: 0.15)"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=5000,
        help="CSV reading batch size (default: 5000)"
    )

    # Tier 2 config
    parser.add_argument(
        "--top-k", type=int, default=2000,
        help="Number of emails to keep after embedding filter (default: 2000)"
    )
    parser.add_argument(
        "--skip-embeddings", action="store_true",
        help="Skip Tier 2 (embedding filter) — useful for quick testing"
    )
    parser.add_argument(
        "--gemini-api-key",
        help="Gemini API key (falls back to GEMINI_API_KEY env var)"
    )

    # Project + Upload config
    parser.add_argument(
        "--upload", action="store_true",
        help="Create a project and upload filtered emails to the BRD system"
    )
    parser.add_argument(
        "--project-name", default="Enron Email Analysis",
        help="Name for the new project (default: 'Enron Email Analysis')"
    )
    parser.add_argument(
        "--project-description",
        default="Auto-generated from Enron email dataset. Filtered using ML preprocessing pipeline (heuristic + embedding scoring).",
        help="Description for the new project"
    )
    parser.add_argument(
        "--api-url", default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--email",
        help="Login email (or set PIPELINE_EMAIL in .env)"
    )
    parser.add_argument(
        "--password",
        help="Login password (or set PIPELINE_PASSWORD in .env)"
    )
    parser.add_argument(
        "--auth-token",
        help="JWT auth token (skip login — or set PIPELINE_AUTH_TOKEN in .env)"
    )
    parser.add_argument(
        "--upload-batch-size", type=int, default=5,
        help="Files per upload request (default: 5)"
    )
    parser.add_argument(
        "--upload-delay", type=float, default=2.0,
        help="Seconds between upload batches (default: 2.0)"
    )

    # General
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Load .env files (project root .env + preprocessing .env)
    try:
        from dotenv import load_dotenv
        # Load project root .env first (has GEMINI_API_KEY)
        root_env = Path(__file__).parent.parent.parent / ".env"
        if root_env.exists():
            load_dotenv(root_env)
        # Load preprocessing-specific .env (overrides)
        preproc_env = Path(__file__).parent / ".env"
        if preproc_env.exists():
            load_dotenv(preproc_env, override=True)
            logging.info(f"Loaded preprocessing .env")
    except ImportError:
        pass

    # Fill args from env vars if not provided via CLI
    if not args.email:
        args.email = os.environ.get("PIPELINE_EMAIL")
    if not args.password:
        args.password = os.environ.get("PIPELINE_PASSWORD")
    if not args.auth_token:
        args.auth_token = os.environ.get("PIPELINE_AUTH_TOKEN")
    if not args.gemini_api_key:
        args.gemini_api_key = os.environ.get("GEMINI_API_KEY")

    # Validate: --upload requires either (email + password) or auth-token
    if args.upload and not args.auth_token and not (args.email and args.password):
        parser.error(
            "--upload requires either (--email + --password) or --auth-token.\n"
            "Or set PIPELINE_EMAIL + PIPELINE_PASSWORD in backend/preprocessing/.env"
        )

    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
