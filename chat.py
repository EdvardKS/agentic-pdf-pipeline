from pipeline.rag_chat import ask


def start_chat():

    print("Chat RAG iniciado. Escribe 'exit' para salir.\n")

    while True:

        q = input("> ")

        if q == "exit":
            break

        response = ask(q)

        print("\n", response, "\n")


if __name__ == "__main__":
    start_chat()