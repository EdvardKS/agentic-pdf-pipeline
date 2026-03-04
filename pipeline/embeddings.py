from pipeline.ollama_client import client


def embed_text(text: str):

    response = client.embeddings(
        model="bge-m3",
        prompt=text
    )

    return response["embedding"]


def embed_chunks(doc):

    vectors = []

    for i, chunk in enumerate(doc["chunks"]):

        emb = embed_text(chunk)

        vectors.append({
            "doc_id": doc.get("sha256"),
            "chunk_id": i,
            "text": chunk,
            "embedding": emb
        })

    return vectors