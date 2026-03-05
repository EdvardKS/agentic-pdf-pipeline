import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class SpaceConfig:
    base_url: str
    timeout_sec: int = 60
    retries: int = 3


class SpaceClient:
    """
    Cliente para llamar a tu HF Space (FastAPI):
      - GET  /
      - POST /embed  {text: str}
      - POST /ocr    multipart file
      - POST /chat   {prompt: str}

    Además:
      - health_check(): comprueba que el host responde
      - models_available(): devuelve nombres “disponibles” (de .env) + valida que el Space responde
        (en Spaces no hay endpoint real de list models, esto es validación de configuración)
    """

    def __init__(self, cfg: SpaceConfig):
        self.cfg = cfg
        self.session = requests.Session()
        pool_size = int(os.getenv("SPACE_HTTP_POOL_MAXSIZE", "64"))
        retries = Retry(
            total=0,
            connect=0,
            read=0,
            redirect=0,
            status=0,
            allowed_methods=frozenset(["GET", "POST"]),
        )
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=retries,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self._batch_embed_mode: Optional[str] = None

    # ---------- internals ----------

    def _url(self, path: str) -> str:
        return self.cfg.base_url.rstrip("/") + path

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        last_err: Optional[Exception] = None

        for attempt in range(1, self.cfg.retries + 1):
            try:
                resp = self.session.request(
                    method=method,
                    url=self._url(path),
                    timeout=self.cfg.timeout_sec,
                    **kwargs,
                )
                resp.raise_for_status()
                return resp

            except Exception as e:
                last_err = e
                if attempt < self.cfg.retries:
                    time.sleep(0.7 * attempt)
                else:
                    raise RuntimeError(
                        f"HF Space request failed after {self.cfg.retries} retries: {method} {path} -> {e}"
                    ) from e

        # nunca llega aquí
        raise RuntimeError(str(last_err))

    # ---------- public api ----------

    def health_check(self) -> Dict[str, Any]:
        """
        Comprueba conectividad al host.
        Espera {"status":"running"} (según tu app.py).
        """
        resp = self._request("GET", "/")
        data = resp.json()
        if data.get("status") != "running":
            raise RuntimeError(f"Space responde pero no está healthy: {data}")
        return data

    def embed(self, text: str) -> Dict[str, Any]:
        """
        Devuelve {"embedding":[...], "dim": N}
        """
        attempts = [
            {"params": {"text": text}},
            {"json": {"text": text}},
            {"json": {"input": text}},
            {"json": {"inputs": text}},
        ]

        last_error: Optional[str] = None

        for req_kwargs in attempts:
            try:
                resp = self._request("POST", "/embed", **req_kwargs)
                data = resp.json()

                # Normaliza variantes comunes de respuesta
                if isinstance(data, list):
                    return {"embedding": data, "dim": len(data)}
                if "embedding" in data:
                    return data
                if "vector" in data:
                    return {"embedding": data["vector"], "dim": len(data["vector"])}

                raise RuntimeError(f"Respuesta de /embed sin embedding reconocible: {data}")
            except Exception as e:
                last_error = str(e)
                continue

        raise RuntimeError(
            "No se pudo obtener embedding desde /embed con formatos compatibles. "
            f"Ultimo error: {last_error}"
        )

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        """
        Intenta embedding batch si el Space lo soporta; si no, cae a unitario.
        """
        if not texts:
            return []

        if self._batch_embed_mode != "unsupported":
            try:
                if self._batch_embed_mode is None:
                    vectors = self._try_batch_embed(texts)
                    self._batch_embed_mode = "supported"
                    return vectors
                if self._batch_embed_mode == "supported":
                    return self._try_batch_embed(texts)
            except Exception:
                self._batch_embed_mode = "unsupported"

        return [self.embed(t)["embedding"] for t in texts]

    def _try_batch_embed(self, texts: List[str]) -> List[List[float]]:
        attempts = [
            {"path": "/embed", "kwargs": {"json": {"texts": texts}}},
            {"path": "/embed", "kwargs": {"json": {"inputs": texts}}},
            {"path": "/embed", "kwargs": {"json": {"text": texts}}},
            {"path": "/embeddings", "kwargs": {"json": {"texts": texts}}},
            {"path": "/embeddings", "kwargs": {"json": {"inputs": texts}}},
        ]
        last_error: Optional[str] = None

        for attempt in attempts:
            try:
                resp = self._request("POST", attempt["path"], **attempt["kwargs"])
                return self._normalize_batch_response(resp.json(), len(texts))
            except Exception as e:
                last_error = str(e)
                continue

        raise RuntimeError(f"Batch embedding no soportado. Ultimo error: {last_error}")

    def _normalize_batch_response(self, data: Any, expected: int) -> List[List[float]]:
        if isinstance(data, list):
            if len(data) == expected and all(isinstance(v, list) for v in data):
                return data
            if len(data) == expected and all(isinstance(v, dict) for v in data):
                vectors = [v.get("embedding") or v.get("vector") for v in data]
                if all(isinstance(v, list) for v in vectors):
                    return vectors  # type: ignore[return-value]

        if isinstance(data, dict):
            vectors = data.get("embeddings") or data.get("vectors") or data.get("data")
            if isinstance(vectors, list):
                if len(vectors) == expected and all(isinstance(v, list) for v in vectors):
                    return vectors
                if len(vectors) == expected and all(isinstance(v, dict) for v in vectors):
                    out = [v.get("embedding") or v.get("vector") for v in vectors]
                    if all(isinstance(v, list) for v in out):
                        return out  # type: ignore[return-value]

        raise RuntimeError(f"Respuesta batch no reconocida: {type(data)}")

    def ocr_image(self, image_path: str) -> Dict[str, Any]:
        """
        Envía imagen (png/jpg) y devuelve {"text": "..."}
        """
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "application/octet-stream")}
            resp = self._request("POST", "/ocr", files=files)
        return resp.json()

    def chat(self, prompt: str) -> Dict[str, Any]:
        """
        Devuelve {"response":"..."}
        """
        # Este Space define /chat con prompt en query param.
        try:
            resp = self._request("POST", "/chat", params={"prompt": prompt})
            return resp.json()
        except Exception:
            # Fallback por si cambió el contrato a body JSON.
            resp = self._request("POST", "/chat", json={"prompt": prompt})
            return resp.json()

    def models_available(self) -> Dict[str, str]:
        """
        En HF Space no hay endpoint de modelos. Validamos:
          1) que el host responde (health_check)
          2) que en .env existen nombres de “modelos” para trazabilidad
        """
        self.health_check()

        embed = os.getenv("EMBED_MODEL")
        ocr = os.getenv("OCR_MODEL")
        chat = os.getenv("CHAT_MODEL")

        missing = [k for k, v in {"EMBED_MODEL": embed, "OCR_MODEL": ocr, "CHAT_MODEL": chat}.items() if not v]
        if missing:
            raise RuntimeError(f"Faltan variables en .env: {', '.join(missing)}")

        return {"EMBED_MODEL": embed, "OCR_MODEL": ocr, "CHAT_MODEL": chat}


def get_space_client() -> SpaceClient:
    base_url = os.getenv("SPACE_BASE_URL")
    if not base_url:
        raise RuntimeError("Falta SPACE_BASE_URL en .env")

    timeout = int(os.getenv("SPACE_TIMEOUT_SEC", "60"))
    retries = int(os.getenv("SPACE_RETRIES", "3"))

    cfg = SpaceConfig(base_url=base_url, timeout_sec=timeout, retries=retries)
    client = SpaceClient(cfg)

    # validación temprana al importar (fail fast)
    client.health_check()
    client.models_available()

    return client


# Uso rápido (manual):
# if __name__ == "__main__":
#     c = get_space_client()
#     print(c.health_check())
#     print(c.models_available())
#     print(c.embed("hola mundo")["dim"])
