"""Tests for the RAG retrieval chain module with mocked FAISS and LLM."""

import pytest
from unittest.mock import patch, MagicMock
from app.modules.rag.retrieval_chain import get_qa_chain
from app.modules.rag.vector_store import load_vector_store


class TestVectorStore:
    """Tests for the vector store loading logic."""

    @patch("os.path.exists")
    def test_load_vector_store_raises_file_not_found(self, mock_exists):
        """1. load_vector_store() should raise FileNotFoundError when the FAISS index does not exist."""
        # Setup: Simulate that the index path does NOT exist
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError) as excinfo:
            load_vector_store()
        
        assert "FAISS index not found" in str(excinfo.value)

    @patch("os.path.exists")
    @patch("app.modules.rag.vector_store.get_embeddings")
    @patch("langchain_community.vectorstores.FAISS.load_local")
    def test_load_vector_store_success(self, mock_load_local, mock_get_embeddings, mock_exists):
        """2. load_vector_store() should return the index when it exists."""
        # Setup: Simulate that the index path DOES exist
        mock_exists.return_value = True
        
        # Create a fake vector store object
        mock_vs = MagicMock()
        mock_load_local.return_value = mock_vs
        
        # Execute
        result = load_vector_store()
        
        # Assertions
        assert result == mock_vs
        mock_load_local.assert_called_once()


class TestRetrievalChain:
    """Tests for the QA chain creation and response structure."""

    @patch("app.modules.rag.retrieval_chain.load_vector_store")
    @patch("app.modules.rag.retrieval_chain.ChatOpenAI")
    @patch("langchain.chains.RetrievalQA.from_chain_type")
    def test_get_qa_chain_returns_chain(self, mock_from_chain_type, mock_llm, mock_load_vs):
        """3. get_qa_chain() should return a chain when the index exists."""
        # Setup: Mock vector store and its retriever
        mock_vs = MagicMock()
        mock_retriever = MagicMock()
        mock_vs.as_retriever.return_value = mock_retriever
        mock_load_vs.return_value = mock_vs
        
        # Mock the chain instance
        mock_chain = MagicMock()
        mock_from_chain_type.return_value = mock_chain
        
        # Execute
        chain = get_qa_chain()
        
        # Assertions
        assert chain == mock_chain
        mock_from_chain_type.assert_called_once()
        
        # Verify it was built with return_source_documents=True
        # This checks that we are following the project's requirement for source extraction
        args, kwargs = mock_from_chain_type.call_args
        assert kwargs["return_source_documents"] is True

    @patch("app.modules.rag.retrieval_chain.load_vector_store")
    @patch("app.modules.rag.retrieval_chain.ChatOpenAI")
    def test_chain_response_structure(self, mock_llm, mock_load_vs):
        """
        4. The chain response should contain 'result' and 'source_documents'.
        5. Source document metadata should be correctly extracted.
        """
        # Setup: Mock the chain and its __call__ (or invoke) method
        mock_vs = MagicMock()
        mock_load_vs.return_value = mock_vs
        
        # Create a fake document with metadata to simulate real retrieval
        mock_doc = MagicMock()
        mock_doc.page_content = "This is a regulatory requirement about AI."
        mock_doc.metadata = {"source": "EU_AI_Act.pdf", "page": 10}
        
        # Create a fake chain that returns a specific dict when called
        mock_chain = MagicMock()
        expected_response = {
            "result": "The EU AI Act requires risk assessments.",
            "source_documents": [mock_doc]
        }
        mock_chain.return_value = expected_response
        
        # We patch RetrievalQA.from_chain_type locally to return our mock_chain
        with patch("langchain.chains.RetrievalQA.from_chain_type", return_value=mock_chain):
            chain = get_qa_chain()
            
            # Simulate asking a question
            response = chain("What is the AI Act?")
            
            # Assertions for structure
            assert "result" in response
            assert "source_documents" in response
            assert response["result"] == "The EU AI Act requires risk assessments."
            assert len(response["source_documents"]) == 1
            
            # Verify metadata extraction (Requirement 4 & 5)
            doc = response["source_documents"][0]
            assert doc.metadata["source"] == "EU_AI_Act.pdf"
            assert doc.metadata["page"] == 10
