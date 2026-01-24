"""OpenRouter embeddings wrapper for trajectory text.

Provides async embedding creation using OpenRouter's embedding models.
Compatible with OpenAI embedding models proxied through OpenRouter.
"""

import asyncio
import os
from typing import Awaitable

from langchain_openai import OpenAIEmbeddings


# Singleton instance
_emb_instance: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    """Get or create the OpenRouter embeddings instance.

    Uses OpenRouter as the provider, compatible with OpenAI embedding models.
    Falls back to direct OpenAI API if OPENROUTER_API_KEY is not set.

    Returns:
        OpenAIEmbeddings: Configured embeddings client.

    Raises:
        ValueError: If no API key is configured.

    Examples:
        >>> emb = get_embeddings()
        >>> vector = emb.embed_query("test text")
    """
    global _emb_instance

    if _emb_instance is None:
        # Try OpenRouter first (preferred), fall back to OpenAI
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY environment variable."
            )

        # Configure for OpenRouter if using OpenRouter key
        if os.getenv("OPENROUTER_API_KEY"):
            _emb_instance = OpenAIEmbeddings(
                model="openai/text-embedding-3-small",
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/htooayelwinict/bot",
                    "X-Title": "FacebookSurferAgent-Embeddings",
                },
            )
        else:
            # Fall back to direct OpenAI
            _emb_instance = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=api_key,
            )

    return _emb_instance


async def embed_trajectory(text: str) -> list[float]:
    """Create embedding from trajectory text.

    Args:
        text: The trajectory summary or task description to embed.

    Returns:
        List of floats representing the embedding vector (1536 dimensions).

    Raises:
        ValueError: If no API key is configured.
        Exception: If the embedding API call fails.

    Examples:
        >>> vector = await embed_trajectory("browser_snapshot -> browser_click")
        >>> len(vector)
        1536
    """
    emb = get_embeddings()

    # Use async embedding for non-blocking operation
    try:
        result = await asyncio.to_thread(emb.embed_query, text)
        return result
    except Exception as e:
        raise RuntimeError(f"Failed to create embedding: {e}") from e


async def embed_trajectories_batch(texts: list[str]) -> list[list[float]]:
    """Create embeddings for multiple trajectory texts.

    More efficient than calling embed_trajectory multiple times.

    Args:
        texts: List of trajectory summaries to embed.

    Returns:
        List of embedding vectors, one per input text.

    Raises:
        ValueError: If no API key is configured.
        Exception: If the embedding API call fails.

    Examples:
        >>> vectors = await embed_trajectories_batch(["task1", "task2"])
        >>> len(vectors)
        2
    """
    emb = get_embeddings()

    try:
        results = await asyncio.to_thread(emb.embed_documents, texts)
        return results
    except Exception as e:
        raise RuntimeError(f"Failed to create embeddings: {e}") from e
