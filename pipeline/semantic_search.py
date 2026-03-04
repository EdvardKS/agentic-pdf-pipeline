import numpy as np
from pipeline.embeddings import embed_text
from pipeline.vector_store import get_vectors


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search(query, top_k=5):

    query_embedding = embed_text(query)

    vectors = get_vectors()

    scored = []

    for v in vectors:

        score = cosine_similarity(query_embedding, v["embedding"])

        scored.append({
            "score": score,
            "text": v["text"],
            "doc_id": v["doc_id"]
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[:top_k]