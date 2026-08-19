"""MCP server exposing the Wger exercise database as a callable tool.

Run (stdio mode):
    python mcp_server/exercise.py

The server exposes one tool:
    search_exercises(query, max_results) -> list of {name, category, muscles, description}

Source: wger.de REST API (no API key required).
Uses the exerciseinfo list endpoint with client-side name filtering.
"""

import html
import re

import httpx
from fastmcp import FastMCP

mcp = FastMCP(
    name="exercise-search",
    instructions=(
        "Search the Wger exercise database for exercises by name or muscle group. "
        "Use this when the question is about which exercises to perform, what muscles "
        "an exercise targets, equipment needed, or how to structure a workout."
    ),
)

_LIST_URL = "https://wger.de/api/v2/exerciseinfo/"
_DESC_CAP = 600


def _clean(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(text)).strip()


def _parse_exercise(ex: dict) -> dict | None:
    name = ""
    description = ""
    for t in ex.get("translations", []):
        if t.get("language") == 2:  # English
            name = t.get("name", "").strip()
            description = _clean(t.get("description", ""))[:_DESC_CAP]
            break

    if not name:
        return None

    return {
        "name": name,
        "category": ex.get("category", {}).get("name", ""),
        "muscles_primary": [m.get("name_en", "") for m in ex.get("muscles", [])],
        "muscles_secondary": [m.get("name_en", "") for m in ex.get("muscles_secondary", [])],
        "equipment": [e.get("name", "") for e in ex.get("equipment", [])],
        "description": description,
    }


@mcp.tool()
def search_exercises(query: str, max_results: int = 5) -> list[dict]:
    """Search the Wger exercise database for exercises by name or muscle group.

    Use this when the question is about which exercises to do, what muscles an
    exercise targets, equipment needed, or how to structure a workout. For
    research on training methods, use search_pubmed instead.

    Args:
        query: Exercise name or muscle group (e.g. "bicep curl", "chest", "squat").
        max_results: Number of exercises to return. Default 5, max 10.

    Returns:
        List of dicts with keys: name, category, muscles_primary, muscles_secondary,
        equipment, description. Returns empty list if no results found.
    """
    max_results = min(max_results, 10)
    query_lower = query.lower()
    results = []
    url = _LIST_URL

    while url and len(results) < max_results:
        resp = httpx.get(
            url,
            params={"format": "json", "language": 2, "limit": 100} if "?" not in url else {},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        for ex in data.get("results", []):
            for t in ex.get("translations", []):
                if t.get("language") == 2:
                    name = t.get("name", "").lower()
                    muscles = " ".join(
                        m.get("name_en", "").lower()
                        for m in ex.get("muscles", []) + ex.get("muscles_secondary", [])
                    )
                    if any(term in name or term in muscles for term in query_lower.split()):
                        parsed = _parse_exercise(ex)
                        if parsed:
                            results.append(parsed)
                    break

            if len(results) >= max_results:
                break

        url = data.get("next")  # paginate if needed

    return results[:max_results]


if __name__ == "__main__":
    mcp.run()
