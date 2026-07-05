import os
import pytest
from unittest.mock import MagicMock, patch

from app.rag.graphstore import (
    init_db,
    add_entities_and_relations,
    get_all_graph,
    get_neighborhood,
    delete_source_graph,
    clear_graph,
)
from app.ingestion.graph_extractor import extract_graph_from_text
from app.rag.pipeline import rag_query


@pytest.fixture(autouse=True)
def temp_graph_db(tmp_path, monkeypatch):
    """Isolate DB for testing."""
    db_file = tmp_path / "test_knowledge_graph.db"
    monkeypatch.setattr("app.rag.graphstore.DB_PATH", str(db_file))
    init_db()
    yield
    # Cleanup is handled automatically by tmp_path, but close connections first
    if db_file.exists():
        try:
            os.remove(str(db_file))
        except Exception:
            pass


def test_db_init_and_crud():
    entities = [
        {"name": "FastAPI", "type": "technology", "description": "Web framework"},
        {"name": "Python", "type": "technology", "description": "Programming language"}
    ]
    relations = [
        {"source": "FastAPI", "target": "Python", "type": "uses", "description": "FastAPI is written in Python"}
    ]
    
    # Store
    add_entities_and_relations(entities, relations, "doc.txt")
    
    # Retrieve
    graph = get_all_graph()
    assert len(graph["nodes"]) == 2
    assert len(graph["links"]) == 1
    assert graph["nodes"][0]["id"] in ["FastAPI", "Python"]
    assert graph["links"][0]["source"] == "FastAPI"
    assert graph["links"][0]["target"] == "Python"
    
    # Neighborhood lookup
    neighbors = get_neighborhood(["FastAPI"])
    assert len(neighbors["facts"]) == 1
    assert "FastAPI (uses) Python" in neighbors["facts"][0]
    assert "doc.txt" in neighbors["sources"]
    
    # Delete by source
    delete_source_graph("doc.txt")
    graph = get_all_graph()
    assert len(graph["nodes"]) == 0
    assert len(graph["links"]) == 0


def test_delete_source_isolation():
    add_entities_and_relations(
        [{"name": "A", "type": "concept", "description": ""}],
        [],
        "sourceA.txt"
    )
    add_entities_and_relations(
        [{"name": "B", "type": "concept", "description": ""}],
        [],
        "sourceB.txt"
    )
    
    # Delete sourceA
    delete_source_graph("sourceA.txt")
    
    graph = get_all_graph()
    # Node B should remain
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["id"] == "B"


@patch("app.ingestion.graph_extractor.Groq")
def test_graph_extraction_success(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    
    # Setup mock completion returning JSON
    mock_message = MagicMock()
    mock_message.content = """
    {
      "entities": [
        {"name": "ChromaDB", "type": "technology", "description": "A vector database"},
        {"name": "RAG", "type": "concept", "description": "Retrieval Augmented Generation"}
      ],
      "relations": [
        {"source": "RAG", "target": "ChromaDB", "type": "uses", "description": "RAG systems often use ChromaDB for vector retrieval"}
      ]
    }
    """
    mock_client.chat.completions.create.return_value.choices = [MagicMock(message=mock_message)]
    
    res = extract_graph_from_text("Dummy text block about RAG and ChromaDB.")
    assert len(res["entities"]) == 2
    assert len(res["relations"]) == 1
    assert res["entities"][0]["name"] == "ChromaDB"
    assert res["relations"][0]["source"] == "RAG"


@patch("app.rag.pipeline.retrieve")
@patch("app.rag.pipeline.Groq")
@patch("app.rag.pipeline.get_neighborhood")
def test_rag_pipeline_with_graph_integration(mock_neighborhood, mock_groq_cls, mock_retrieve):
    # Mock retrieve to return nothing (vector store is empty)
    mock_retrieve.return_value = []
    
    # Mock neighborhood to return some facts
    mock_neighborhood.return_value = {
        "facts": ["- FastAPI (uses) Python: FastAPI is built on Python"],
        "sources": ["web_page.html"]
    }
    
    # Mock completion return
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "FastAPI uses Python as its core programming language."
    mock_groq_cls.return_value.chat.completions.create.return_value = mock_completion
    
    # Mock the entity extractor call to return something
    with patch("app.rag.pipeline._extract_entities_from_query") as mock_extract:
        mock_extract.return_value = ["FastAPI"]
        
        result = rag_query("What does FastAPI use?", use_graph=True)
        
        assert result["answer"] == "FastAPI uses Python as its core programming language."
        assert "web_page.html" in result["sources"]
        assert result["chunks_used"] == 0
        mock_neighborhood.assert_called_once_with(["FastAPI"])
