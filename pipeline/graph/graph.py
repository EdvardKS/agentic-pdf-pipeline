# pipeline/graph/graph.py

from langgraph.graph import StateGraph

from pipeline.graph.state import DocumentState
from pipeline.graph.nodes import extract_node, clean_node
from pipeline.graph.schema_extract_node import schema_extract_node
from pipeline.graph.validate_node import validate_node


def build_graph():
    """
    Construye y compila el grafo LangGraph.

    Flujo: extract → clean → schema_extract → validate
    """

    workflow = StateGraph(DocumentState)

    workflow.add_node("extract", extract_node)
    workflow.add_node("clean", clean_node)
    workflow.add_node("schema_extract", schema_extract_node)
    workflow.add_node("validate", validate_node)

    workflow.set_entry_point("extract")

    workflow.add_edge("extract", "clean")
    workflow.add_edge("clean", "schema_extract")
    workflow.add_edge("schema_extract", "validate")

    graph = workflow.compile()

    return graph
