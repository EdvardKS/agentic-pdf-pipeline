import os
from dotenv import load_dotenv
import ollama

load_dotenv()

HOST = os.getenv("PICASSO")

CHAT_MODEL = os.getenv("CHAT_MODEL")
EMBED_MODEL = os.getenv("EMBED_MODEL")
VISION_MODEL = os.getenv("VISION_MODEL")

if not HOST:
    raise RuntimeError("Falta PICASSO en .env (host de Ollama)")

client = ollama.Client(host=HOST)

# ---- comprobación de modelos ----

missing = []

for var, value in {
    "CHAT_MODEL": CHAT_MODEL,
    "EMBED_MODEL": EMBED_MODEL,
    "VISION_MODEL": VISION_MODEL
}.items():
    if not value:
        missing.append(var)

if missing:
    raise RuntimeError(
        f"Faltan variables en .env: {', '.join(missing)}"
    )

try:
    models = client.list()["models"]
    available = {m["model"] for m in models}

except Exception as e:
    raise RuntimeError(f"No se pudo conectar a Ollama en {HOST}: {e}")

required_models = {CHAT_MODEL, EMBED_MODEL, VISION_MODEL}

missing_models = required_models - available

if missing_models:
    raise RuntimeError(
        f"Los siguientes modelos no están instalados en Ollama: {missing_models}"
    )