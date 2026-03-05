from typing import List, Dict

from pipeline.space.space_client import get_space_client
from pipeline.semantic_search import search


def build_prompt(question: str, contexts: List[Dict]) -> str:
    """
    Construye el prompt final para el modelo de chat
    """

    context_text = "\n\n".join(
        [c["text"] for c in contexts]
    )

    prompt = f"""
Responde usando SOLO la informacion del contexto.

CONTEXTO
{context_text}

PREGUNTA
{question}

RESPUESTA
"""

    return prompt


def rag_query(question: str, k: int = 5) -> str:
    """
    Pipeline RAG completo
    """

    space = get_space_client()

    # 1 busqueda vectorial semantica
    results = search(question, top_k=k)

    # 2 construir prompt
    prompt = build_prompt(question, results)

    # 3 llamar chat model
    response = space.chat(prompt)

    return response["response"]

def ask(query: str) -> str:
    return rag_query(query)


def start_chat():
    """
    Chat interactivo en terminal
    """

    print("\nRAG Chat iniciado")
    print("Escribe 'exit' para salir\n")

    while True:

        question = input(">> ")

        if question.lower() in ["exit", "quit"]:
            break

        answer = rag_query(question)

        print("\nRespuesta:\n")
        print(answer)
        print("\n")
