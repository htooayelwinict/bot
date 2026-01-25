#!/usr/bin/env python3
"""Test retrieval with the fixed filters."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.qdrant_client import QdrantManager
from src.storage.retrieval import retrieve_similar_trajectories


async def main():
    """Test retrieval."""
    print("=" * 80)
    print("🧪 TESTING FIXED RETRIEVAL")
    print("=" * 80)

    task = "go to facebook and my user profile. grab 10 recent posts(last) and print here, make sure you greap unique 10 recent post. not overlap or forge"
    
    print(f"\n🔍 Task: {task[:100]}...")
    
    # Get client
    client = await QdrantManager.get_client()
    
    # Test retrieval with new settings
    results = await retrieve_similar_trajectories(
        task=task,
        top_k=3,
        min_score=0.4,
        min_similarity=0.4,
        exclude_failed_patterns=True,
        client=client,
    )
    
    print(f"\n📊 RESULTS: {len(results)} similar workflows found")
    
    if not results:
        print("\n❌ STILL NO RESULTS! Check filters.")
    else:
        print("\n✅ SUCCESS! Found similar workflows:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. Task: {result['task'][:80]}...")
            print(f"   Score: {result['score']:.3f}")
            print(f"   Similarity: {result['similarity']:.3f}")
            print(f"   Quality Rank: {result['quality_rank']:.3f}")
            print(f"   Failed Patterns: {result['failed_pattern_count']}")
            
            # Show reflection
            reflection = result.get('reflection', {})
            if reflection:
                critique = reflection.get('critique', '')[:150]
                print(f"   Critique: {critique}...")
                
                failed = reflection.get('failed_patterns', [])
                if failed:
                    print(f"   ❌ {len(failed)} failed patterns:")
                    for pattern in failed[:2]:
                        print(f"      • {pattern[:100]}...")
            print()
    
    await QdrantManager.close()


if __name__ == "__main__":
    asyncio.run(main())
