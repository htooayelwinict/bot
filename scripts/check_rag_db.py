#!/usr/bin/env python3
"""Check Qdrant RAG database for similar workflows."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import AsyncQdrantClient
from src.storage.qdrant_client import QdrantManager
from src.storage.embeddings import embed_trajectory


async def main():
    """Check the RAG database for similar workflows."""
    print("=" * 80)
    print("🔍 CHECKING RAG DATABASE (Qdrant)")
    print("=" * 80)

    # Get DB path
    db_path = os.getenv("QDRANT_PATH", "./qdrant_db")
    print(f"\n📁 Database Path: {db_path}")
    print(f"   Exists: {Path(db_path).exists()}")

    if not Path(db_path).exists():
        print("\n❌ Database path does not exist!")
        return

    try:
        # Get client
        client = await QdrantManager.get_client()
        print("\n✅ Connected to Qdrant")

        # Get collection info
        collection_info = await client.get_collection(QdrantManager.COLLECTION_NAME)
        print(f"\n📊 Collection: {QdrantManager.COLLECTION_NAME}")
        print(f"   Points count: {collection_info.points_count}")
        print(f"   Vector size: {collection_info.config.params.vectors.size}")  # type: ignore
        print(f"   Distance metric: {collection_info.config.params.vectors.distance}")  # type: ignore

        if collection_info.points_count == 0:
            print("\n⚠️  Collection is EMPTY - no trajectories stored!")
            return

        # Query for Facebook-related tasks
        task = "go to facebook and my user profile. grab 10 recent posts"
        print(f"\n🔍 Searching for similar workflows...")
        print(f"   Query: '{task}'")

        # Embed the query
        query_embedding = await embed_trajectory(task)
        print(f"   Embedding size: {len(query_embedding)}")

        # Search without filters first to see everything
        print("\n" + "=" * 80)
        print("📋 ALL RESULTS (no filters)")
        print("=" * 80)

        response = await client.query_points(
            collection_name=QdrantManager.COLLECTION_NAME,
            query=query_embedding,
            limit=10,
        )

        if not response.points:
            print("\n⚠️  No results found!")
        else:
            for i, result in enumerate(response.points, 1):
                print(f"\n{'-' * 80}")
                print(f"Result #{i}")
                print(f"{'-' * 80}")
                print(f"📌 ID: {result.id}")
                print(f"📏 Similarity Score: {result.score:.4f}")

                if result.payload:
                    print(f"\n📝 Task: {result.payload.get('task', 'N/A')[:150]}...")
                    print(f"⭐ Success Score: {result.payload.get('score', 'N/A')}")
                    print(f"🔧 Tool Calls: {result.payload.get('tool_count', 'N/A')}")
                    print(f"✅ Success Rate: {result.payload.get('success_rate', 'N/A')}")
                    print(f"📅 Created: {result.payload.get('created_at', 'N/A')}")

                    # Show reflection
                    reflection = result.payload.get("reflection", {})
                    if reflection:
                        print(f"\n🤔 Reflection:")
                        print(f"   Critique: {reflection.get('critique', 'N/A')[:200]}...")
                        
                        successful = reflection.get("successful_patterns", [])
                        if successful:
                            print(f"\n   ✅ Successful Patterns ({len(successful)}):")
                            for pattern in successful[:3]:
                                print(f"      • {pattern[:100]}...")
                        
                        failed = reflection.get("failed_patterns", [])
                        if failed:
                            print(f"\n   ❌ Failed Patterns ({len(failed)}):")
                            for pattern in failed[:3]:
                                print(f"      • {pattern[:100]}...")

        # Now search with min_score filter (0.47 as in code)
        print("\n\n" + "=" * 80)
        print("📋 FILTERED RESULTS (score >= 0.47, similarity >= 0.4)")
        print("=" * 80)

        from qdrant_client.models import Filter, Range

        score_filter = Filter(must=[{"key": "score", "range": Range(gte=0.47)}])

        response_filtered = await client.query_points(
            collection_name=QdrantManager.COLLECTION_NAME,
            query=query_embedding,
            query_filter=score_filter,
            limit=10,
        )

        filtered_results = [r for r in response_filtered.points if r.score >= 0.4]

        print(f"\n🎯 Found {len(filtered_results)} results meeting criteria")

        if not filtered_results:
            print("\n⚠️  NO RESULTS AFTER FILTERING!")
            print("\nPossible reasons:")
            print("   1. All trajectories have score < 0.47 (low quality)")
            print("   2. Similarity scores < 0.4 (not similar enough)")
            print("   3. Wrong task embedding (different keywords)")
        else:
            for i, result in enumerate(filtered_results, 1):
                print(f"\n{i}. Score={result.score:.3f}, Success={result.payload.get('score', 'N/A')}")  # type: ignore
                print(f"   Task: {result.payload.get('task', 'N/A')[:100]}...")  # type: ignore

        # Show score distribution
        print("\n\n" + "=" * 80)
        print("📊 SCORE DISTRIBUTION")
        print("=" * 80)

        all_points = await client.scroll(
            collection_name=QdrantManager.COLLECTION_NAME,
            limit=100,
        )

        scores = [p.payload.get("score", 0) for p in all_points[0] if p.payload]  # type: ignore
        if scores:
            print(f"\n📈 Statistics for {len(scores)} trajectories:")
            print(f"   Min: {min(scores):.3f}")
            print(f"   Max: {max(scores):.3f}")
            print(f"   Avg: {sum(scores)/len(scores):.3f}")
            print(f"   >= 0.47: {len([s for s in scores if s >= 0.47])}")
            print(f"   < 0.47: {len([s for s in scores if s < 0.47])}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await QdrantManager.close()


if __name__ == "__main__":
    asyncio.run(main())
