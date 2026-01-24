#!/usr/bin/env python
"""Debug RAG retrieval issue."""
from dotenv import load_dotenv
load_dotenv()

import asyncio
import numpy as np
from src.storage.qdrant_client import QdrantManager
from src.storage.embeddings import embed_trajectory

async def check():
    client = await QdrantManager.get_client()
    points = await client.scroll(
        collection_name='agent_trajectories',
        limit=1,
        with_payload=True,
        with_vectors=True
    )
    p = points[0][0]
    stored_vector = np.array(p.vector)
    
    task = p.payload.get('task', '')
    print(f"Stored task: {task}")
    
    # Re-embed just the task  
    task_emb = np.array(await embed_trajectory(task))
    
    # Compare to stored vector
    sim = np.dot(stored_vector, task_emb) / (np.linalg.norm(stored_vector) * np.linalg.norm(task_emb))
    print(f'Similarity (stored vs cats task): {sim:.4f}')
    
    # Now check stored vs query (dogs)
    query_emb = np.array(await embed_trajectory('create an onlyme facebook post about dogs'))
    sim2 = np.dot(stored_vector, query_emb) / (np.linalg.norm(stored_vector) * np.linalg.norm(query_emb))
    print(f'Similarity (stored vs dogs query): {sim2:.4f}')
    
    # Direct cats vs dogs comparison
    cats_emb = np.array(await embed_trajectory('create an onlyme facebook post about cats'))
    sim3 = np.dot(cats_emb, query_emb) / (np.linalg.norm(cats_emb) * np.linalg.norm(query_emb))
    print(f'Similarity (cats vs dogs direct): {sim3:.4f}')

asyncio.run(check())
