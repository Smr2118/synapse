"""MCP server exposing PubMed live search as a callable tool.

Run (stdio mode — for Claude Desktop / MCP clients):
    python mcp_server/pubmed.py

Run (HTTP/SSE mode — for testing with curl or agents):
    fastmcp run mcp_server/pubmed.py --transport sse --port 8001

The server exposes one tool:
    search_pubmed(query, max_results) -> list of {pmid, title, abstract}
"""

import re

import httpx
from fastmcp import FastMCP

mcp = FastMCP(
    name="pubmed-search",
    instructions=(
        "Search PubMed for peer-reviewed research on fitness, nutrition, "
        "supplementation, and recovery. Returns abstracts with PMIDs so the "
        "caller can cite sources."
    ),
)

_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_MAX_RESULTS_CAP = 20


def _search_pmids(query: str, max_results: int) -> list[str]:
    response = httpx.get(
        f"{_BASE_URL}/esearch.fcgi",
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


def _fetch_abstract_text(pmids: list[str]) -> str:
    response = httpx.get(
        f"{_BASE_URL}/efetch.fcgi",
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


def _parse_results(raw: str) -> list[dict]:
    """Parse PubMed plain-text abstract format into structured dicts."""
    blocks = re.split(r"\n\n(?=\d+\. )", raw.strip())
    results = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        pmid_match = re.search(r"PMID:\s*(\d+)", block)
        if not pmid_match:
            continue
        pmid = pmid_match.group(1)

        # Paragraphs: [0] citation line, [1] title, [2+] authors/affiliation/abstract
        paragraphs = [p.strip() for p in block.split("\n\n") if p.strip()]
        title = paragraphs[1] if len(paragraphs) > 1 else ""

        # Abstract section starts after "Abstract" label
        abstract = ""
        abstract_match = re.search(
            r"Abstract\s*\n(.*?)(?=\n\n(?:[A-Z]|\d+\.)|\nPMID:|\Z)",
            block,
            re.DOTALL,
        )
        if abstract_match:
            abstract = abstract_match.group(1).strip()
        else:
            # Fallback: use the full block minus PMID line
            abstract = re.sub(r"\nPMID:.*", "", block, flags=re.DOTALL).strip()

        results.append({"pmid": pmid, "title": title, "abstract": abstract})

    return results


@mcp.tool()
def search_pubmed(query: str, max_results: int = 5) -> list[dict]:
    """Search PubMed for peer-reviewed research abstracts.

    Use this when the user asks a fitness or nutrition question and the local
    knowledge base does not have sufficient evidence, or when up-to-date
    research is explicitly requested.

    Args:
        query: Search terms describing the topic (e.g. "creatine strength training").
        max_results: How many abstracts to return. Capped at 20. Default 5.

    Returns:
        List of dicts with keys: pmid (str), title (str), abstract (str).
        Returns an empty list if PubMed finds no matches.
    """
    max_results = min(max_results, _MAX_RESULTS_CAP)

    pmids = _search_pmids(query, max_results)
    if not pmids:
        return []

    raw = _fetch_abstract_text(pmids)
    return _parse_results(raw)


if __name__ == "__main__":
    mcp.run()
