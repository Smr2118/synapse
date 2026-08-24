"""Code-based assertions for Synapse agentic traces.

Each check takes a trace dict (one entry from traces.json) and returns
(passed: bool, reason: str).

Checks are tied directly to the failure taxonomy from open-coding:
  1. assert_grounded          — ungrounded answer failure (Q13)
  2. assert_sources_needed    — sources_needed contradiction (Q20)
  3. assert_no_duplicate_tools — duplicate tool calls (Q3, Q14)
  4. assert_strategy_label    — strategy=refused when LLM actually answered
"""


def assert_grounded(trace: dict) -> tuple[bool, str]:
    """Fail if an in-scope question was answered with no sources.

    Skips out-of-scope questions (expected=refuse) — having no sources
    for those is correct behaviour.

    Catches:
    - Ungrounded answer: no tools called, no sources, high confidence (Q13)
    - Silent tool miss: tools called, returned nothing, answered anyway (Q15, Q20)
    """
    if trace.get("expected") == "refuse":
        return True, "out-of-scope question — grounding not required"

    response = trace.get("response", {})
    answer = response.get("answer", {})
    sources = response.get("sources", [])
    tool_calls = response.get("tool_calls", [])
    confidence = answer.get("confidence", 0.0)
    answer_text = answer.get("answer", "")

    if not answer_text:
        return True, "no answer text — skip"

    # Tools were called but nothing came back — silent tool miss
    if tool_calls and not sources:
        return False, (
            f"Tools called {[tc['tool'] for tc in tool_calls]} "
            f"but sources=[] — ungrounded answer after tool miss"
        )

    # No tools called, no sources, but a confident answer — answered from memory
    if not tool_calls and not sources and confidence >= 0.5:
        return False, (
            f"No tools called, sources=[], confidence={confidence} "
            f"— answered from training data without grounding"
        )

    return True, "ok"


def assert_sources_needed_consistent(trace: dict) -> tuple[bool, str]:
    """Fail if sources_needed=false but tools returned nothing.

    Catches Q20: tool_calls populated, sources=[], sources_needed=false.
    When tools were tried and came back empty, the answer is by definition
    under-evidenced — sources_needed must be true.
    """
    response = trace.get("response", {})
    answer = response.get("answer", {})
    sources = response.get("sources", [])
    tool_calls = response.get("tool_calls", [])
    sources_needed = answer.get("sources_needed", True)

    if tool_calls and not sources and not sources_needed:
        return False, (
            f"sources_needed=false but {len(tool_calls)} tool(s) were called "
            f"and returned nothing — field contradicts reality"
        )

    return True, "ok"


def assert_no_duplicate_tools(trace: dict) -> tuple[bool, str]:
    """Fail if the same tool was called more than once in a single request.

    Catches Q3 (nih called twice locally) and Q14 (pubmed called twice on Render).
    Duplicate calls waste tokens and latency without adding new information.
    """
    tool_calls = trace.get("response", {}).get("tool_calls", [])
    seen = []
    duplicates = []

    for tc in tool_calls:
        name = tc.get("tool", "")
        if name in seen:
            duplicates.append(name)
        seen.append(name)

    if duplicates:
        return False, f"Duplicate tool calls: {duplicates}"

    return True, "ok"


def assert_strategy_label(trace: dict) -> tuple[bool, str]:
    """Fail if strategy=refused on an in-scope question that was answered.

    Skips out-of-scope questions (expected=refuse) — strategy=refused is
    correct for those.

    Catches Q13, Q15, Q20: in-scope question, LLM answered with text and
    confidence > 0, but strategy says refused because no sources were found.
    """
    if trace.get("expected") == "refuse":
        return True, "out-of-scope question — strategy=refused is correct"

    response = trace.get("response", {})
    strategy = response.get("strategy", "")
    answer = response.get("answer", {})
    answer_text = answer.get("answer", "")
    confidence = answer.get("confidence", 0.0)

    if strategy == "refused" and answer_text and confidence > 0:
        return False, (
            f"strategy=refused but answer is non-empty with confidence={confidence} "
            f"— mislabelled: this is an ungrounded answer, not a refusal"
        )

    return True, "ok"


ALL_CHECKS = {
    "grounded": assert_grounded,
    "sources_needed_consistent": assert_sources_needed_consistent,
    "no_duplicate_tools": assert_no_duplicate_tools,
    "strategy_label_accurate": assert_strategy_label,
}


def run_checks(trace: dict) -> dict[str, tuple[bool, str]]:
    """Run all checks against a single trace. Returns {check_name: (passed, reason)}."""
    return {name: fn(trace) for name, fn in ALL_CHECKS.items()}
