"""Run all checks against a traces JSON file and print a results table.

Usage:
    python evals/runner.py                          # evals/traces.json
    python evals/runner.py --traces evals/traces_render.json
    python evals/runner.py --traces evals/traces_after.json --compare evals/traces.json
"""

import argparse
import json
from pathlib import Path

from evals.checks import ALL_CHECKS, run_checks


def score_file(traces: list[dict]) -> list[dict]:
    results = []
    for trace in traces:
        checks = run_checks(trace)
        results.append({
            "id": trace["id"],
            "question": trace["question"][:55] + "..." if len(trace["question"]) > 55 else trace["question"],
            "strategy": trace.get("response", {}).get("strategy", "n/a"),
            "checks": {name: {"passed": passed, "reason": reason}
                       for name, (passed, reason) in checks.items()},
            "passed": sum(1 for passed, _ in checks.values() if passed),
            "total": len(checks),
        })
    return results


def print_table(results: list[dict], label: str = "") -> None:
    check_names = list(ALL_CHECKS.keys())
    col_w = 26

    if label:
        print(f"\n{'=' * 10} {label} {'=' * 10}")

    header = f"{'#':>3}  {'Question':<55}  {'Strategy':<18}  " + \
             "  ".join(f"{n[:col_w]:<{col_w}}" for n in check_names)
    print(header)
    print("-" * len(header))

    for r in results:
        row = f"{r['id']:>3}  {r['question']:<55}  {r['strategy']:<18}  "
        for name in check_names:
            check = r["checks"][name]
            cell = "PASS" if check["passed"] else "FAIL"
            row += f"{cell:<{col_w}}  "
        print(row)

    print()
    total_checks = sum(r["total"] for r in results)
    total_passed = sum(r["passed"] for r in results)
    print(f"Overall: {total_passed}/{total_checks} checks passed "
          f"({100 * total_passed / total_checks:.0f}%)")

    print("\nPer-check:")
    for name in check_names:
        passed = sum(1 for r in results if r["checks"][name]["passed"])
        print(f"  {name:<35} {passed}/{len(results)} passed")

    failures = [(r["id"], r["question"], name, r["checks"][name]["reason"])
                for r in results
                for name, c in r["checks"].items()
                if not c["passed"]]

    if failures:
        print(f"\nFailures ({len(failures)}):")
        for fid, q, check, reason in failures:
            print(f"  [{fid}] {check}: {reason}")


def load(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces", default="evals/traces.json")
    parser.add_argument("--compare", default=None,
                        help="Optional second traces file to compare against")
    args = parser.parse_args()

    traces = load(args.traces)
    results = score_file(traces)
    print_table(results, label=args.traces)

    if args.compare:
        traces_b = load(args.compare)
        results_b = score_file(traces_b)
        print_table(results_b, label=args.compare)
