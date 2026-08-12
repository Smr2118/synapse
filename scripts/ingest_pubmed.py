"""Ingest all PubMed abstracts into Pinecone via the /ingest endpoint.

Usage:
    # Against local server (must be running):
    python scripts/ingest_pubmed.py

    # Against Render:
    python scripts/ingest_pubmed.py --url https://synapse-5w9z.onrender.com

Resumable: already-ingested PMIDs are tracked in data/pubmed/ingested.log
"""

import argparse
import time
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "pubmed"
LOG_FILE = DATA_DIR / "ingested.log"

DEFAULT_URL = "http://127.0.0.1:8000"
DELAY = 0.5  # seconds between requests — stay within OpenAI embedding rate limits


def load_ingested() -> set[str]:
    if not LOG_FILE.exists():
        return set()
    return set(LOG_FILE.read_text().splitlines())


def mark_ingested(pmid: str) -> None:
    with LOG_FILE.open("a") as f:
        f.write(pmid + "\n")


def ingest(base_url: str, document_id: str, text: str) -> dict:
    response = httpx.post(
        f"{base_url.rstrip('/')}/ingest",
        json={"document_id": document_id, "text": text},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    args = parser.parse_args()

    files = sorted(DATA_DIR.glob("*.txt"))
    if not files:
        print("No abstracts found in data/pubmed/ — run collect_pubmed.py first")
        return

    already_ingested = load_ingested()
    pending = [f for f in files if f.stem not in already_ingested]

    print(f"Total abstracts: {len(files)}")
    print(f"Already ingested: {len(already_ingested)}")
    print(f"Pending: {len(pending)}")
    print(f"Target: {args.url}\n")

    if not pending:
        print("All abstracts already ingested.")
        return

    success = 0
    failed = 0

    for i, path in enumerate(pending, 1):
        pmid = path.stem
        text = path.read_text(encoding="utf-8")

        try:
            result = ingest(args.url, f"pubmed_{pmid}", text)
            mark_ingested(pmid)
            success += 1
            print(f"[{i}/{len(pending)}] pubmed_{pmid} — {result['chunks']} chunks, {result['tokens_used']} tokens")
        except Exception as exc:
            failed += 1
            print(f"[{i}/{len(pending)}] pubmed_{pmid} — FAILED: {exc}")

        time.sleep(DELAY)

    print(f"\nDone — {success} ingested, {failed} failed")


if __name__ == "__main__":
    main()
