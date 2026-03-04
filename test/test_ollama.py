import os
from dotenv import load_dotenv
import ollama

load_dotenv()

OLLAMA_HOST = os.getenv("PICASSO")

print("Host:", OLLAMA_HOST)

client = ollama.Client(host=OLLAMA_HOST)

response = client.chat(
    model="mistral:7b",
    messages=[
        {"role": "user", "content": "Say hello in one sentence"}
    ]
)
print("Response:")
print("res: ",response["message"]["content"])