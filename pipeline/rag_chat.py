# from pipeline.semantic_search import search
# from pipeline.ollama_client import client, CHAT_MODEL


# def ask(query):

#     results = search(query, top_k=5)

#     context = "\n\n".join([r["text"] for r in results])

#     prompt = f"""
# Responde usando SOLO la información del contexto.

# CONTEXTO:
# {context}

# PREGUNTA:
# {query}
# """

#     response = client.chat(
#         model=CHAT_MODEL, # type: ignore
#         messages=[{
#             "role": "user",
#             "content": prompt
#         }]
#     )

#     return response["message"]["content"]
