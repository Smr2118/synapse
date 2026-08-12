"""Fetch PubMed abstracts on fitness and nutrition topics and save as plain text.

Usage:
    python scripts/collect_pubmed.py

Output:
    data/pubmed/<pmid>.txt  — one file per abstract, ready for /ingest
"""

import json
import re
import time
from pathlib import Path

import httpx

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "pubmed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

TOPICS = [
    "protein intake muscle protein synthesis",
    "resistance training hypertrophy",
    "intermittent fasting weight loss",
    "carbohydrate timing athletic performance",
    "dietary fat metabolism body composition",
    "creatine supplementation exercise",
    "omega-3 fatty acids inflammation exercise",
    "sleep quality athletic recovery",
    "hydration performance endurance",
    "vitamin D deficiency athletic performance",
    "caloric deficit muscle preservation",
    "high protein diet satiety",
]

RESULTS_PER_TOPIC = 40


def search_pmids(query: str, max_results: int) -> list[str]:
    response = httpx.get(
        f"{BASE_URL}/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["esearchresult"]["idlist"]


def fetch_abstracts(pmids: list[str]) -> str:
    response = httpx.get(
        f"{BASE_URL}/efetch.fcgi",
        params={
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "text",
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.text


def parse_abstracts(raw: str) -> list[dict]:
    # Records are separated by double newlines before a new number (e.g. "\n\n1. ")
    blocks = re.split(r"\n\n(?=\d+\. )", raw.strip())
    result = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # PMID appears as "PMID: 12345678" near the end
        match = re.search(r"PMID:\s*(\d+)", block)
        if match:
            result.append({"pmid": match.group(1), "text": block})
    return result


def main() -> None:
    all_pmids: set[str] = set()
    saved = 0
    skipped = 0

    print(f"Collecting abstracts into {OUTPUT_DIR}\n")

    for topic in TOPICS:
        print(f"Searching: {topic}")
        try:
            pmids = search_pmids(topic, RESULTS_PER_TOPIC)
            new_pmids = [p for p in pmids if p not in all_pmids]
            all_pmids.update(new_pmids)
            print(f"  Found {len(pmids)} results, {len(new_pmids)} new")

            if not new_pmids:
                continue

            for i in range(0, len(new_pmids), 20):
                batch = new_pmids[i : i + 20]
                raw = fetch_abstracts(batch)
                abstracts = parse_abstracts(raw)

                for item in abstracts:
                    path = OUTPUT_DIR / f"{item['pmid']}.txt"
                    if path.exists():
                        skipped += 1
                        continue
                    path.write_text(item["text"], encoding="utf-8")
                    saved += 1

                time.sleep(0.4)

        except Exception as exc:
            print(f"  ERROR: {exc}")

        time.sleep(0.4)

    print(f"\nDone — {saved} abstracts saved, {skipped} already existed")
    print(f"Total unique PMIDs seen: {len(all_pmids)}")

    manifest = {"topics": TOPICS, "total_saved": saved, "total_pmids": len(all_pmids)}
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Manifest written to {OUTPUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
