# from pipeline.ollama_client import client
# from pipeline.ollama_client import EMBED_MODEL

# import time

# def embed_text(text: str):

#     for attempt in range(3):

#         try:

#             response = client.embeddings(
#                 model=EMBED_MODEL, # type: ignore
#                 prompt=text
#             )

#             return response["embedding"]

#         except Exception as e:

#             print("⚠ Error embedding, retry...", e)

#             time.sleep(2)

#     raise RuntimeError("Embedding failed after retries")


# def embed_chunks(doc):

#     vectors = []

#     for i, chunk in enumerate(doc["chunks"]):

#         emb = embed_text(chunk)

#         vectors.append({
#             "doc_id": doc.get("sha256"),
#             "chunk_id": i,
#             "text": chunk,
#             "embedding": emb
#         })

#         time.sleep(0.1)  

#     return vectors