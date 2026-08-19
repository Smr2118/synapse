"""MCP server exposing NIH MedlinePlus health topic search as a callable tool.

Run (stdio mode):
    python mcp_server/nih.py

The server exposes one tool:
    search_nih(query, max_results) -> list of {title, url, summary, organization}

Source: NLM MedlinePlus web search API (no API key required).
Use this for official dietary recommendations and government health guidelines,
as opposed to search_pubmed which returns research study abstracts.
"""

import re
import xml.etree.ElementTree as ET

import httpx
from fastmcp import FastMCP

mcp = FastMCP(
    name="nih-search",
    instructions=(
        "Search NIH MedlinePlus for official health guidelines, dietary "
        "recommendations, and safe intake levels. Use this when the question "
        "asks about recommended amounts, safety, or official guidance — not "
        "just what research studies show."
    ),
)

_SEARCH_URL = "https://wsearch.nlm.nih.gov/ws/query"
_SUMMARY_CAP = 1200  # chars — keep context manageable


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


@mcp.tool()
def search_nih(query: str, max_results: int = 3) -> list[dict]:
    """Search NIH MedlinePlus for official health guidelines and recommendations.

    Use this when the question asks about recommended intake levels, safety
    thresholds, or official dietary guidance. For research study evidence,
    use search_pubmed instead.

    Args:
        query: Search terms (e.g. "vitamin D recommended daily intake").
        max_results: Number of results to return. Default 3, max 10.

    Returns:
        List of dicts with keys: title (str), url (str), summary (str),
        organization (str). Returns empty list if no results found.
    """
    max_results = min(max_results, 10)

    response = httpx.get(
        _SEARCH_URL,
        params={"db": "healthTopics", "term": query, "retmax": max_results},
        timeout=30.0,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    results = []

    for doc in root.findall(".//document"):
        title = ""
        summary = ""
        organization = ""
        url = doc.get("url", "")

        for content in doc.findall("content"):
            name = content.get("name", "")
            text = content.text or ""
            if name == "title":
                title = text
            elif name == "FullSummary":
                summary = _strip_html(text)[:_SUMMARY_CAP]
            elif name == "organizationName":
                organization = text

        if title:
            results.append(
                {"title": title, "url": url, "summary": summary, "organization": organization}
            )

    return results


if __name__ == "__main__":
    mcp.run()
