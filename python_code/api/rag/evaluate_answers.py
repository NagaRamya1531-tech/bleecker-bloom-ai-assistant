"""End-to-end answer evaluation for the Details Agent (retrieval + generation).

Each line of eval_answers.jsonl is either:
  - answerable: "must_include" is a list of any-of groups; every group needs at
    least one phrase in the answer. Optional "must_not_include" phrases fail it.
  - unanswerable: the knowledge base has no answer, so the agent should say it
    does not know instead of inventing one.

Checks are simple case-insensitive phrase matches, so results are reproducible
and do not depend on a second LLM acting as a judge.

Usage, from python_code/api (needs the chat model running in Ollama):
    python -m rag.evaluate_answers
    python -m rag.evaluate_answers --show   # print every answer
"""
import json
from pathlib import Path
import sys
import time

from agents import DetailsAgent

EVAL_FILE = Path(__file__).with_name("eval_answers.jsonl")
ABSTAIN_PHRASES = [
    "don't know", "do not know", "not sure", "no information", "don't have information",
    "do not have information", "unable to", "can't say", "cannot say", "not mentioned",
    "don't have details", "do not have details", "isn't something i", "not able to",
    "cannot answer", "can't answer",
]


def contains(answer, phrase):
    return phrase.lower() in answer.lower()


def grade(example, answer):
    if example.get("unanswerable"):
        return any(contains(answer, phrase) for phrase in ABSTAIN_PHRASES)
    groups_ok = all(any(contains(answer, phrase) for phrase in group) for group in example["must_include"])
    forbidden = any(contains(answer, phrase) for phrase in example.get("must_not_include", []))
    return groups_ok and not forbidden


def main():
    examples = [json.loads(line) for line in EVAL_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    agent = DetailsAgent()
    if agent.retriever is None:
        sys.exit("Retriever is not active (RAG dependencies missing: pip install -r requirements.txt).")

    results = {"answerable": [], "unanswerable": []}
    latencies = []
    for example in examples:
        started = time.perf_counter()
        answer = agent.get_response([{"role": "user", "content": example["question"]}])["content"]
        latencies.append(time.perf_counter() - started)

        passed = grade(example, answer)
        results["unanswerable" if example.get("unanswerable") else "answerable"].append(passed)
        if "--show" in sys.argv or not passed:
            print(f"[{'PASS' if passed else 'FAIL'}] {example['question']}\n    {answer.strip()[:300]}\n")

    print(f"Model: {agent.model_name}")
    for kind, label in [("answerable", "Correct answers"), ("unanswerable", "Says 'don't know' when it should")]:
        print(f"{label:<34} {sum(results[kind])}/{len(results[kind])}")
    print(f"{'Median latency':<34} {sorted(latencies)[len(latencies) // 2]:.1f}s")


if __name__ == "__main__":
    main()
