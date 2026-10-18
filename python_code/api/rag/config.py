import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from .retriever import HybridRetriever, OpenAICompatibleEmbedder

load_dotenv()

API_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_BASE_DIR = API_DIR.parent / "knowledge_base"
PERSIST_DIR = API_DIR / "rag" / ".chroma"


def build_retriever():
    """Create the local hybrid retriever from environment settings.

    EMBEDDING_MODEL_NAME (default nomic-embed-text) is served from
    RUNPOD_EMBEDDING_URL, falling back to RUNPOD_CHATBOT_URL (Ollama locally).
    EMBEDDING_API_KEY lets embeddings use a different provider than chat
    (e.g. chat on a RunPod vLLM endpoint, embeddings on OpenAI).
    """
    embedder = OpenAICompatibleEmbedder(
        OpenAI(
            api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("RUNPOD_TOKEN", "ollama"),
            base_url=os.getenv("RUNPOD_EMBEDDING_URL") or os.getenv("RUNPOD_CHATBOT_URL"),
        ),
        os.getenv("EMBEDDING_MODEL_NAME", "nomic-embed-text"),
    )
    return HybridRetriever(KNOWLEDGE_BASE_DIR, PERSIST_DIR, embedder)
