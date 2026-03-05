import numpy as np
from pipeline.space.space_embeddings import embed_text
from pipeline.vector_store import get_vectors


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search(query, top_k=5):

    query_embedding = embed_text(query)

    vectors = get_vectors()
    if not vectors:
        return []

    scored = []

    for v in vectors:

        score = cosine_similarity(query_embedding, v["embedding"])

        scored.append({
            "score": score,
            "text": v["text"],
            "doc_id": v.get("doc_id") or v.get("doc_path") or v.get("id")
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[:top_k]
