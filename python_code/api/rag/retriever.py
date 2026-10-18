"""Hybrid retrieval over the knowledge base: BM25 keyword search plus vector
search in a local Chroma store, merged with Reciprocal Rank Fusion (RRF).

BM25 catches exact item names ("Ginger Scone"); vectors catch paraphrases
("something without milk"). If the embedding endpoint is unavailable the
retriever falls back to BM25 only, so the chatbot keeps working.
"""
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import re

import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi

from .documents import Chunk, load_chunks

logger = logging.getLogger(__name__)
# chromadb 0.5 logs a harmless error on every call when a newer posthog is installed.
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

STOPWORDS = {
    "a", "an", "the", "and", "or", "is", "are", "do", "does", "you", "your", "i",
    "me", "my", "we", "our", "of", "to", "in", "on", "for", "with", "it", "can",
    "what", "how", "any", "have", "has", "there", "this", "that", "be", "at",
}
RRF_K = 60


def tokenize(text):
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    # Light plural stemming so "scones" matches "scone".
    return [token[:-1] if len(token) > 3 and token.endswith("s") else token
            for token in tokens if token not in STOPWORDS]


@dataclass
class SearchResult:
    chunk: Chunk
    score: float


class OpenAICompatibleEmbedder:
    """Embeds text with any OpenAI-compatible endpoint (Ollama, RunPod, OpenAI)."""

    def __init__(self, client, model_name, batch_size=32):
        self.client = client
        self.model_name = model_name
        self.batch_size = batch_size
        # nomic-embed-text is trained with task prefixes.
        self.uses_prefixes = "nomic" in model_name

    def _embed(self, texts):
        embeddings = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            response = self.client.embeddings.create(input=batch, model=self.model_name)
            embeddings += [item.embedding for item in response.data]
        return embeddings

    def embed_documents(self, texts):
        if self.uses_prefixes:
            texts = [f"search_document: {text}" for text in texts]
        return self._embed(texts)

    def embed_query(self, text):
        if self.uses_prefixes:
            text = f"search_query: {text}"
        return self._embed([text])[0]


class HybridRetriever:
    def __init__(self, knowledge_base_dir, persist_dir, embedder=None, collection_name="knowledge_base"):
        self.chunks = load_chunks(knowledge_base_dir)
        self.chunks_by_id = {chunk.id: chunk for chunk in self.chunks}
        self.bm25 = BM25Okapi([tokenize(chunk.text) for chunk in self.chunks])
        self.embedder = embedder
        self.collection = None

        if embedder is not None:
            try:
                self.collection = self._load_or_build_collection(Path(persist_dir), collection_name)
            except Exception as error:
                logger.warning("Vector index unavailable, using BM25 only: %s", error)
                self.embedder = None

    def _fingerprint(self):
        digest = hashlib.sha256(self.embedder.model_name.encode())
        for chunk in self.chunks:
            digest.update(chunk.id.encode())
            digest.update(chunk.text.encode())
        return digest.hexdigest()

    def _load_or_build_collection(self, persist_dir, collection_name):
        client = chromadb.PersistentClient(path=str(persist_dir), settings=Settings(anonymized_telemetry=False))
        fingerprint = self._fingerprint()
        collection = client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})

        # Re-embed only when the knowledge base or embedding model changed.
        if (collection.metadata or {}).get("fingerprint") == fingerprint and collection.count() == len(self.chunks):
            return collection

        logger.info("Building vector index for %d chunks", len(self.chunks))
        client.delete_collection(collection_name)
        collection = client.create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine", "fingerprint": fingerprint},
        )
        collection.add(
            ids=[chunk.id for chunk in self.chunks],
            documents=[chunk.text for chunk in self.chunks],
            metadatas=[chunk.metadata() for chunk in self.chunks],
            embeddings=self.embedder.embed_documents([chunk.text for chunk in self.chunks]),
        )
        return collection

    @property
    def vector_enabled(self):
        return self.collection is not None

    def _matches(self, chunk, filters):
        if not filters:
            return True
        for key, value in filters.items():
            if key == "tags":
                if value not in chunk.tags:
                    return False
            elif getattr(chunk, key) != value:
                return False
        return True

    def bm25_search(self, query, limit):
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        return [(self.chunks[i].id, float(scores[i])) for i in ranked[:limit] if scores[i] > 0]

    def vector_search(self, query, limit):
        result = self.collection.query(
            query_embeddings=[self.embedder.embed_query(query)],
            n_results=min(limit, len(self.chunks)),
        )
        return [(chunk_id, 1 - distance)
                for chunk_id, distance in zip(result["ids"][0], result["distances"][0])]

    def search(self, query, top_k=4, mode="hybrid", filters=None):
        """Return the top_k chunks for a query.

        mode: "hybrid" (default), "bm25", or "vector".
        filters: exact-match metadata, e.g. {"doc_type": "menu", "tags": "vegan"}.
        """
        if mode != "bm25" and not self.vector_enabled:
            mode = "bm25"

        # The corpus is small, so rank everything and filter afterwards.
        candidate_limit = len(self.chunks)
        ranked_lists = []
        if mode in ("hybrid", "bm25"):
            ranked_lists.append(self.bm25_search(query, candidate_limit))
        if mode in ("hybrid", "vector"):
            ranked_lists.append(self.vector_search(query, candidate_limit))

        if len(ranked_lists) == 1:
            scores = dict(ranked_lists[0])
        else:
            scores = {}
            for ranked in ranked_lists:
                for rank, (chunk_id, _) in enumerate(ranked):
                    scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)

        results = [SearchResult(self.chunks_by_id[chunk_id], score)
                   for chunk_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
                   if self._matches(self.chunks_by_id[chunk_id], filters)]
        return results[:top_k]
