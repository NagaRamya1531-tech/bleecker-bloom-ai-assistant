"""Build (or refresh) the local vector index and try a sample query.

Usage, from python_code/api:
    python -m rag.ingest
    python -m rag.ingest "is the almond croissant safe for nut allergies?"
"""
import sys

from .config import build_retriever


def main():
    retriever = build_retriever()
    print(f"Loaded {len(retriever.chunks)} chunks; vector search "
          f"{'enabled' if retriever.vector_enabled else 'DISABLED (BM25 only)'}")

    query = " ".join(sys.argv[1:]) or "Do you have anything dairy-free?"
    print(f"\nQuery: {query}")
    for result in retriever.search(query):
        print(f"  {result.score:.4f}  {result.chunk.id}")


if __name__ == "__main__":
    main()
