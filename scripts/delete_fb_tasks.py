#!/usr/bin/env python3
"""Delete top 5 Facebook post-retrieval trajectories from Qdrant."""

import asyncio
from src.storage.qdrant_client import QdrantManager
from src.storage.embeddings import embed_trajectory
from qdrant_client.models import PointIdsList

QUERY = (
    "go to facebook and my user profile. grab 10 recent posts(last) by Htoo Aye Lwin "
    "and print here, make sure you greap unique 10 recent post by Htoo Aye Lwin. "
    "not overlap or forge"
)

async def main() -> None:
    client = await QdrantManager.get_client()
    emb = await embed_trajectory(QUERY)
    resp = await client.query_points(
        collection_name=QdrantManager.COLLECTION_NAME,
        query=emb,
        limit=10,
    )

    print(f"Found {len(resp.points)} points")
    for idx, p in enumerate(resp.points, 1):
        task = (p.payload or {}).get("task", "") if p.payload else ""
        print(f"{idx}. id={p.id} sim={p.score:.3f} task={task[:120]}...")

    ids_to_delete = [p.id for p in resp.points[:5]]
    print(f"\nDeleting {len(ids_to_delete)} points: {ids_to_delete}")
    if ids_to_delete:
        await client.delete(
            collection_name=QdrantManager.COLLECTION_NAME,
            points_selector=PointIdsList(points=ids_to_delete),
        )
        print("Deleted.")

    await QdrantManager.close()

if __name__ == "__main__":
    asyncio.run(main())
