"""
Enron Email Dataset loader.

Parses the Kaggle Enron CSV (columns: file, message) into structured
email objects. Streams in chunks to handle the 375 MB file without
blowing up memory.

The raw `message` column contains RFC 822 formatted emails with headers
(From, To, Subject, Date, etc.) followed by the body. Python's built-in
email.parser handles this natively.
"""

import csv
import email
import email.policy
import logging
import multiprocessing
import os
import sys
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Generator, List, Optional, Tuple

# Enron dataset has some extremely large email fields (forwarded threads)
csv.field_size_limit(sys.maxsize)

logger = logging.getLogger(__name__)


@dataclass
class EnronEmail:
    """Parsed email with extracted fields."""
    file_path: str                          # Original path in Enron dataset
    sender: str = ""
    recipients_to: List[str] = field(default_factory=list)
    recipients_cc: List[str] = field(default_factory=list)
    recipients_bcc: List[str] = field(default_factory=list)
    subject: str = ""
    date: str = ""
    body: str = ""
    folder: str = ""                        # e.g. "allen-p/sent_items"
    word_count: int = 0
    total_recipients: int = 0

    @property
    def all_recipients(self) -> List[str]:
        return self.recipients_to + self.recipients_cc + self.recipients_bcc


def _parse_address_list(raw: Optional[str]) -> List[str]:
    """Parse comma-separated email addresses, handling Enron's messy formatting."""
    if not raw:
        return []
    # Split on comma, strip whitespace, drop empty strings
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def _parse_single_email(file_path: str, raw_message: str) -> Optional[EnronEmail]:
    """Parse a single raw RFC 822 email string into an EnronEmail."""
    try:
        msg = email.message_from_string(raw_message, policy=email.policy.default)

        body = msg.get_body(preferencelist=("plain",))
        body_text = body.get_content() if body else ""

        # Fallback: if get_body returns nothing, extract from payload
        if not body_text and msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body_text = part.get_content()
                    break
        elif not body_text:
            body_text = msg.get_payload(decode=True)
            if isinstance(body_text, bytes):
                body_text = body_text.decode("utf-8", errors="replace")
            elif body_text is None:
                body_text = ""

        to_list = _parse_address_list(msg.get("To"))
        cc_list = _parse_address_list(msg.get("Cc"))
        bcc_list = _parse_address_list(msg.get("X-bcc") or msg.get("Bcc"))

        # Extract folder from file path (e.g. "allen-p/sent_items/1." → "sent_items")
        parts = file_path.split("/")
        folder = parts[1] if len(parts) >= 2 else ""

        words = body_text.split()

        return EnronEmail(
            file_path=file_path,
            sender=msg.get("From", ""),
            recipients_to=to_list,
            recipients_cc=cc_list,
            recipients_bcc=bcc_list,
            subject=msg.get("Subject", ""),
            date=msg.get("Date", ""),
            body=body_text,
            folder=folder,
            word_count=len(words),
            total_recipients=len(to_list) + len(cc_list) + len(bcc_list),
        )
    except Exception as e:
        logger.debug(f"Failed to parse email {file_path}: {e}")
        return None


def load_enron_csv(
    csv_path: str,
    chunk_size: int = 5000,
) -> Generator[List[EnronEmail], None, None]:
    """
    Stream-load the Enron CSV in chunks to avoid memory blowup.

    The Kaggle Enron CSV has columns: file, message
    - file: path like "allen-p/all_documents/1."
    - message: raw RFC 822 email text

    Args:
        csv_path: Path to the Enron emails.csv
        chunk_size: Number of rows per batch (default 5000)

    Yields:
        List[EnronEmail] — one batch at a time
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Enron CSV not found: {csv_path}")

    file_size_mb = csv_path.stat().st_size / (1024 * 1024)
    logger.info(f"Loading Enron CSV: {csv_path} ({file_size_mb:.1f} MB)")

    # Use csv.reader directly for robustness with messy email content
    # pandas chokes on some rows due to unescaped quotes in email bodies
    total_parsed = 0
    total_failed = 0

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        batch: List[EnronEmail] = []

        for row in reader:
            file_path = row.get("file", "")
            message = row.get("message", "")

            if not message:
                total_failed += 1
                continue

            parsed = _parse_single_email(file_path, message)
            if parsed:
                batch.append(parsed)
                total_parsed += 1
            else:
                total_failed += 1

            if len(batch) >= chunk_size:
                logger.info(f"  Loaded {total_parsed:,} emails so far...")
                yield batch
                batch = []

        # Yield remaining
        if batch:
            yield batch

    logger.info(
        f"Enron loading complete: {total_parsed:,} parsed, "
        f"{total_failed:,} failed/skipped"
    )


def _parse_row(args: Tuple[str, str]) -> Optional[EnronEmail]:
    """Parse a single (file_path, message) tuple. Top-level for multiprocessing pickling."""
    file_path, message = args
    return _parse_single_email(file_path, message)


def load_enron_csv_parallel(
    csv_path: str,
    chunk_size: int = 10000,
    workers: int = 0,
) -> Generator[List[EnronEmail], None, None]:
    """
    Parallel version of load_enron_csv — uses multiprocessing to parse emails.

    Reads CSV rows sequentially (I/O-bound), but distributes the CPU-bound
    email.message_from_string() parsing across multiple processes.

    Args:
        csv_path: Path to the Enron emails.csv
        chunk_size: Rows per batch to submit to the pool (default 10000)
        workers: Number of worker processes (0 = cpu_count - 1)
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Enron CSV not found: {csv_path}")

    if workers <= 0:
        workers = max(1, (os.cpu_count() or 4) - 1)

    file_size_mb = csv_path.stat().st_size / (1024 * 1024)
    logger.info(f"Loading Enron CSV (parallel, {workers} workers): {csv_path} ({file_size_mb:.1f} MB)")

    total_parsed = 0
    total_failed = 0

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        with multiprocessing.Pool(workers) as pool:
            raw_batch: List[Tuple[str, str]] = []

            for row in reader:
                file_path = row.get("file", "")
                message = row.get("message", "")

                if not message:
                    total_failed += 1
                    continue

                raw_batch.append((file_path, message))

                if len(raw_batch) >= chunk_size:
                    results = pool.map(_parse_row, raw_batch, chunksize=500)
                    parsed = [r for r in results if r is not None]
                    total_parsed += len(parsed)
                    total_failed += len(raw_batch) - len(parsed)
                    logger.info(f"  Loaded {total_parsed:,} emails so far...")
                    yield parsed
                    raw_batch = []

            # Remaining rows
            if raw_batch:
                results = pool.map(_parse_row, raw_batch, chunksize=500)
                parsed = [r for r in results if r is not None]
                total_parsed += len(parsed)
                total_failed += len(raw_batch) - len(parsed)
                yield parsed

    logger.info(
        f"Enron loading complete: {total_parsed:,} parsed, "
        f"{total_failed:,} failed/skipped"
    )


def load_all_enron(csv_path: str) -> List[EnronEmail]:
    """Load all emails into memory at once. Only use for small/filtered CSVs."""
    all_emails = []
    for batch in load_enron_csv(csv_path):
        all_emails.extend(batch)
    return all_emails
