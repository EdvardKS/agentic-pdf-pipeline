import hashlib
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from pipeline.space.space_client import get_space_client

SPACE_CLIENT = get_space_client()


def _stable_chunk_id(doc_path: str, chunk_text: str, idx: int) -> str:
    """
    ID estable por chunk (útil para vector store / deduplicación).
    """
    h = hashlib.sha256()
    h.update(doc_path.encode("utf-8", errors="ignore"))
    h.update(b"::")
    h.update(str(idx).encode("utf-8"))
    h.update(b"::")
    h.update(chunk_text.encode("utf-8", errors="ignore"))
    return h.hexdigest()


def embed_text(text: str) -> List[float]:
    """
    Embedding para texto usando HF Space /embed.
    """
    resp = SPACE_CLIENT.embed(text)
    return resp["embedding"]


def embed_chunks(
    doc: Dict[str, Any],
    *,
    max_chunks: Optional[int] = None,
    max_workers: int = 8,
) -> List[Dict[str, Any]]:
    """
    Espera:
      doc["path"]  : ruta del PDF
      doc["chunks"]: lista[str] con chunks ya generados

    Devuelve una lista de vectores con metadata:
      [{
        "id": ...,
        "doc_path": ...,
        "chunk_index": ...,
        "text": ...,
        "embedding": [...],
      }, ...]
    """
    if "path" not in doc:
        raise ValueError("doc debe incluir 'path'")
    if "chunks" not in doc or not isinstance(doc["chunks"], list):
        raise ValueError("doc debe incluir 'chunks' (list[str])")

    chunks = doc["chunks"]
    if max_chunks is not None:
        chunks = chunks[:max_chunks]

    items: List[tuple[int, str]] = []

    for i, chunk in enumerate(chunks):
        if not chunk or not chunk.strip():
            continue
        items.append((i, chunk))

    if not items:
        return []

    # En este Space /embed es unitario (sin batch), así que paralelizamos llamadas.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        embeddings = list(executor.map(lambda it: embed_text(it[1]), items))

    vectors: List[Dict[str, Any]] = []
    for (i, chunk), emb in zip(items, embeddings):
        vectors.append(
            {
                "id": _stable_chunk_id(doc["path"], chunk, i),
                "doc_path": doc["path"],
                "chunk_index": i,
                "text": chunk,
                "embedding": emb,
            }
        )

    return vectors
