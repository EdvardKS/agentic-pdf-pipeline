import os
from dotenv import load_dotenv
import ollama

load_dotenv()

HOST = os.getenv("PICASSO")
if not HOST:
    raise RuntimeError("Falta PICASSO en .env (host de Ollama)")

client = ollama.Client(host=HOST)