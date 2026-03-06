# pipeline/graph/graph.py

# StateGraph es el constructor del grafo de estados de LangGraph
from langgraph.graph import StateGraph

# Importamos el tipo de estado y los nodos
from pipeline.graph.state import DocumentState
from pipeline.graph.nodes import extract_node, clean_node, chunk_node, embedding_node
from pipeline.graph.schema_extract_node import schema_extract_node

def build_graph():
    """
    Construye y compila el grafo LangGraph.
    """

    # 1) Creamos un grafo tipado con DocumentState
    workflow = StateGraph(DocumentState)

    # 2) Registramos nodos: nombre -> función
    workflow.add_node("extract", extract_node)
    workflow.add_node("clean", clean_node)
    # workflow.add_node("chunk", chunk_node)
    # workflow.add_node("embed", embedding_node)
    workflow.add_node("schema_extract", schema_extract_node)

    # 3) Definimos cuál es el nodo inicial del flujo
    workflow.set_entry_point("extract")

    # 4) Conectamos el flujo lineal entre nodos
    workflow.add_edge("extract", "clean")
    # workflow.add_edge("clean", "chunk")
    # workflow.add_edge("chunk", "embed")
    # workflow.add_edge("embed", "schema_extract")
    workflow.add_edge("clean", "schema_extract")

    # 5) Compilamos el grafo para poder hacer graph.invoke(state)
    graph = workflow.compile()

    # 6) Devolvemos el grafo listo para ejecución
    return graph