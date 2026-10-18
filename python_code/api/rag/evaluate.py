"""Retrieval evaluation: compares BM25, vector, and hybrid search.

Each line of eval_questions.jsonl has a question and the chunk ids that answer
it. A question counts as a hit@k if any relevant chunk is in the top k results.

Usage, from python_code/api:
    python -m rag.evaluate            # summary table
    python -m rag.evaluate --misses   # also list hybrid questions missed at k=4
"""
import json
from pathlib import Path
import sys

from .config import build_retriever

EVAL_FILE = Path(__file__).with_name("eval_questions.jsonl")
TOP_K = 4


def evaluate(retriever, examples, mode):
    hits_at_1 = hits_at_k = reciprocal_rank_sum = 0
    misses = []
    for example in examples:
        result_ids = [result.chunk.id for result in retriever.search(example["question"], top_k=TOP_K, mode=mode)]
        ranks = [rank for rank, chunk_id in enumerate(result_ids, start=1) if chunk_id in example["relevant"]]
        if ranks:
            hits_at_k += 1
            hits_at_1 += ranks[0] == 1
            reciprocal_rank_sum += 1 / ranks[0]
        else:
            misses.append((example["question"], result_ids))

    total = len(examples)
    return {
        "hit@1": hits_at_1 / total,
        f"hit@{TOP_K}": hits_at_k / total,
        "MRR": reciprocal_rank_sum / total,
    }, misses


def main():
    examples = [json.loads(line) for line in EVAL_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    retriever = build_retriever()

    # Fail loudly if an eval label points at a chunk that no longer exists.
    unknown = {chunk_id for example in examples for chunk_id in example["relevant"]} - set(retriever.chunks_by_id)
    if unknown:
        sys.exit(f"Unknown chunk ids in {EVAL_FILE.name}: {sorted(unknown)}")

    modes = ["bm25", "vector", "hybrid"] if retriever.vector_enabled else ["bm25"]
    print(f"{len(examples)} questions, {len(retriever.chunks)} chunks\n")
    print(f"{'mode':<8} {'hit@1':>7} {f'hit@{TOP_K}':>7} {'MRR':>7}")
    hybrid_misses = []
    for mode in modes:
        metrics, misses = evaluate(retriever, examples, mode)
        print(f"{mode:<8} " + " ".join(f"{value:>7.1%}" if key != "MRR" else f"{value:>7.3f}"
                                       for key, value in metrics.items()))
        if mode == modes[-1]:
            hybrid_misses = misses

    if "--misses" in sys.argv:
        print(f"\nMissed by {modes[-1]} at k={TOP_K}:")
        for question, result_ids in hybrid_misses:
            print(f"  {question}\n    got: {result_ids}")


if __name__ == "__main__":
    main()
