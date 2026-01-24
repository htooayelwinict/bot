"""Qdrant client manager for trajectory storage.

Provides singleton access to AsyncQdrantClient with persistent storage.
"""

import os
from typing import ClassVar

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams


class QdrantManager:
    """Qdrant client singleton with persistent storage.

    Manages the Qdrant vector database connection and collection lifecycle.
    Uses a singleton pattern to ensure a single client instance across
    the application.
    """

    # Collection and vector configuration
    COLLECTION_NAME = "agent_trajectories"
    VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small
    DISTANCE = Distance.COSINE

    # Singleton instance
    _instance: ClassVar[AsyncQdrantClient | None] = None

    @classmethod
    async def get_client(cls) -> AsyncQdrantClient:
        """Get or create the Qdrant client instance.

        Returns:
            AsyncQdrantClient: Configured Qdrant client with ensured collection.

        Examples:
            >>> client = await QdrantManager.get_client()
            >>> collections = await client.get_collections()
        """
        if cls._instance is None:
            # Get storage path from env or use default
            storage_path = os.getenv("QDRANT_PATH", "./qdrant_db")

            # Initialize async client with persistent storage
            cls._instance = AsyncQdrantClient(path=storage_path)

            # Ensure collection exists
            await cls._ensure_collection(cls._instance)

        return cls._instance

    @classmethod
    async def close(cls) -> None:
        """Close the Qdrant client connection.

        Should be called on application shutdown to clean up resources.
        """
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None

    @staticmethod
    async def _ensure_collection(client: AsyncQdrantClient) -> None:
        """Ensure the agent_trajectories collection exists.

        Creates the collection with appropriate vector configuration if it
        doesn't already exist.

        Args:
            client: Qdrant client instance.
        """
        collections = await client.get_collections()

        # Check if collection already exists
        if not any(c.name == QdrantManager.COLLECTION_NAME for c in collections.collections):
            await client.create_collection(
                collection_name=QdrantManager.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=QdrantManager.VECTOR_SIZE,
                    distance=QdrantManager.DISTANCE,
                ),
            )

    @classmethod
    async def reset_collection(cls) -> None:
        """Delete and recreate the collection.

        Useful for testing or clearing all stored trajectories.
        """
        client = await cls.get_client()

        # Delete collection if it exists
        try:
            await client.delete_collection(cls.COLLECTION_NAME)
        except Exception:
            # Collection might not exist, ignore
            pass

        # Recreate collection
        await cls._ensure_collection(client)
