import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.ingestion.processor import process_document
from app.rag.vectorstore import add_chunks, search, COLLECTION_NAME
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_chroma_db(tmp_path, monkeypatch):
    """Isolate ChromaDB for testing."""
    test_db_dir = tmp_path / "test_chroma_db"
    monkeypatch.setattr("app.rag.vectorstore.settings.chroma_db_path", str(test_db_dir))
    
    from app.rag.vectorstore import _get_client
    _get_client.cache_clear()
    
    yield
    
    _get_client.cache_clear()


@patch("app.ingestion.processor.Groq")
def test_process_document_with_contextual_retrieval(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "This chunk describes basic FastAPI features."
    mock_client.chat.completions.create.return_value = mock_completion
    
    text = "FastAPI is a modern, fast (high-performance) web framework for building APIs with Python."
    
    # Enable contextual retrieval
    with patch("app.ingestion.processor.settings") as mock_settings:
        mock_settings.groq_api_key = "fake_key"
        mock_settings.default_model = "llama-3.1-8b-instant"
        
        chunks = process_document(
            text, 
            source="test_doc.txt", 
            source_type="txt", 
            chunk_size=1000, 
            use_contextual=True
        )
        
        assert len(chunks) == 1
        assert "This chunk describes basic FastAPI features." in chunks[0]["text"]
        assert chunks[0]["original_text"] == text
        assert chunks[0]["context"] == "This chunk describes basic FastAPI features."
        mock_client.chat.completions.create.assert_called_once()


@patch("app.ingestion.processor.Groq")
@patch("app.api.routes_ingest._extract_and_store_graph")
def test_ingest_endpoint_contextual_flag(mock_extract_graph, mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "This situates the test document."
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("app.ingestion.processor.settings") as mock_settings:
        mock_settings.groq_api_key = "fake_key"
        mock_settings.default_model = "llama-3.1-8b-instant"

        # Call the /ingest/text API endpoint with use_contextual=True
        response = client.post(
            "/ingest/text",
            json={
                "text": "FastAPI is a fast web framework.",
                "source_name": "api_test.txt",
                "use_contextual": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chunks_created"] == 1
        
        # Verify vector store retains original text and contextual text
        results = search("FastAPI", top_k=1)
        assert len(results) == 1
        assert "This situates the test document." in results[0]["text"]
        assert "FastAPI is a fast web framework." in results[0]["original_text"]
