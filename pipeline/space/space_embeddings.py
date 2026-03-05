import hashlib
import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from pipeline.space.space_client import get_space_client

SPACE_CLIENT = get_space_client()
CACHE_DB_PATH = os.getenv("EMBED_CACHE_DB", "./tmp/embed_cache.sqlite3")
DB_LOCK = threading.Lock()


def _stable_chunk_id(doc_path: str, chunk_text: str, idx: int) -> str:
    h = hashlib.sha256()
    h.update(doc_path.encode("utf-8", errors="ignore"))
    h.update(b"::")
    h.update(str(idx).encode("utf-8"))
    h.update(b"::")
    h.update(chunk_text.encode("utf-8", errors="ignore"))
    return h.hexdigest()


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(CACHE_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(CACHE_DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings_cache (
            text_hash TEXT PRIMARY KEY,
            embedding_json TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


CONN = _connect()


def _cache_get_many(hashes: List[str]) -> Dict[str, List[float]]:
    if not hashes:
        return {}
    placeholders = ",".join(["?"] * len(hashes))
    with DB_LOCK:
        rows = CONN.execute(
            f"SELECT text_hash, embedding_json FROM embeddings_cache WHERE text_hash IN ({placeholders})",
            hashes,
        ).fetchall()
    out: Dict[str, List[float]] = {}
    for h, emb_json in rows:
        out[h] = [float(x) for x in emb_json.split(",") if x]
    return out


def _cache_put_many(items: List[Tuple[str, List[float]]]) -> None:
    if not items:
        return
    rows = [(h, ",".join(str(x) for x in emb)) for h, emb in items]
    with DB_LOCK:
        CONN.executemany(
            """
            INSERT INTO embeddings_cache (text_hash, embedding_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(text_hash) DO UPDATE SET
                embedding_json = excluded.embedding_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            rows,
        )
        CONN.commit()


def embed_text(text: str) -> List[float]:
    return SPACE_CLIENT.embed(text)["embedding"]


def embed_chunks(
    doc: Dict[str, Any],
    *,
    max_chunks: Optional[int] = None,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
) -> List[Dict[str, Any]]:
    if "path" not in doc:
        raise ValueError("doc debe incluir 'path'")
    if "chunks" not in doc or not isinstance(doc["chunks"], list):
        raise ValueError("doc debe incluir 'chunks' (list[str])")

    workers = max_workers or int(os.getenv("SPACE_EMBED_WORKERS", "8"))
    group_size = batch_size or int(os.getenv("SPACE_EMBED_BATCH_SIZE", "16"))

    chunks = doc["chunks"]
    if max_chunks is not None:
        chunks = chunks[:max_chunks]

    items: List[Tuple[int, str, str]] = []
    for i, chunk in enumerate(chunks):
        if not chunk or not chunk.strip():
            continue
        h = _text_hash(chunk)
        items.append((i, chunk, h))

    if not items:
        return []

    hashes = [h for _, _, h in items]
    cache = _cache_get_many(hashes)

    missing: List[Tuple[int, str, str]] = [it for it in items if it[2] not in cache]
    if missing:
        groups = [missing[i : i + group_size] for i in range(0, len(missing), group_size)]

        def _embed_group(group: List[Tuple[int, str, str]]) -> List[Tuple[str, List[float]]]:
            texts = [chunk for _, chunk, _ in group]
            vectors = SPACE_CLIENT.embed_many(texts)
            return [(group[idx][2], vectors[idx]) for idx in range(len(group))]

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for pairs in executor.map(_embed_group, groups):
                _cache_put_many(pairs)
                for h, emb in pairs:
                    cache[h] = emb

    vectors: List[Dict[str, Any]] = []
    for i, chunk, h in items:
        emb = cache[h]
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
