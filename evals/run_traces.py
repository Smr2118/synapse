"""Run 15-20 queries against /agentic/ask and save responses to JSON.

Usage:
    python evals/run_traces.py                        # default: localhost:8005
    python evals/run_traces.py --url https://synapse-5w9z.onrender.com

Output:
    evals/traces.json  — one entry per query with full response + metadata
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import httpx

# Each entry: (question, expected)
# expected = "answer"  → should call tools and return grounded answer
# expected = "refuse"  → out-of-scope, should return no sources, no tools
QUESTIONS = [
    # In-scope — nutrition
    ("How much protein do I need to build muscle?", "answer"),
    ("Does creatine supplementation improve strength and power output?", "answer"),
    ("What is the recommended daily intake of vitamin D for athletes?", "answer"),
    ("Does intermittent fasting cause muscle loss?", "answer"),
    ("How do omega-3 fatty acids affect exercise-induced inflammation?", "answer"),
    ("What are the best foods to eat before a workout?", "answer"),
    ("Does caffeine improve athletic performance?", "answer"),
    ("How does sleep affect athletic recovery?", "answer"),
    ("What is the role of carbohydrates in endurance performance?", "answer"),

    # In-scope — exercise
    ("What exercises target the biceps?", "answer"),
    ("What exercises build the chest and what does research say about optimal training volume?", "answer"),
    ("How many sets per week are needed for muscle hypertrophy?", "answer"),
    ("What is the difference between compound and isolation exercises?", "answer"),

    # In-scope — supplementation
    ("Does NMN supplementation improve athletic performance?", "answer"),
    ("Is ashwagandha effective for reducing cortisol in athletes?", "answer"),
    ("Does berberine improve insulin sensitivity?", "answer"),

    # Out-of-scope — should be refused
    ("What is the best programming language to learn in 2025?", "refuse"),
    ("Who won the FIFA World Cup in 2022?", "refuse"),
    ("What is the capital of France?", "refuse"),

    # Edge cases
    ("Can I take 10g of creatine daily? Is it safe?", "answer"),
]


def run(base_url: str, output_path: Path) -> None:
    traces = []
    total = len(QUESTIONS)

    print(f"Running {total} queries against {base_url}/agentic/ask")
    print(f"Output: {output_path}\n")

    for i, (question, expected) in enumerate(QUESTIONS, 1):
        print(f"[{i}/{total}] {question[:70]}...")
        try:
            start = time.perf_counter()
            response = httpx.post(
                f"{base_url}/agentic/ask",
                json={"question": question},
                timeout=120.0,
            )
            wall_ms = int((time.perf_counter() - start) * 1000)

            if response.status_code == 200:
                data = response.json()
                status = "ok"
            else:
                data = {"error": response.text}
                status = f"http_{response.status_code}"

        except Exception as exc:
            data = {"error": str(exc)}
            status = "error"
            wall_ms = 0

        trace = {
            "id": i,
            "expected": expected,
            "question": question,
            "status": status,
            "wall_ms": wall_ms,
            "response": data,
            "notes": "",  # fill in manually during open-coding
        }
        traces.append(trace)
        print(f"       status={status} | strategy={data.get('strategy', 'n/a')} | "
              f"tools={[tc['tool'] for tc in data.get('tool_calls', [])]} | "
              f"confidence={data.get('answer', {}).get('confidence', 'n/a')}")

        time.sleep(0.5)  # be polite to the API

    output_path.write_text(json.dumps(traces, indent=2), encoding="utf-8")
    print(f"\nDone — {total} traces saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8005")
    parser.add_argument("--output", default="evals/traces.json")
    args = parser.parse_args()

    run(
        base_url=args.url.rstrip("/"),
        output_path=Path(args.output),
    )
