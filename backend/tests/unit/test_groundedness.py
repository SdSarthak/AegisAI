import pytest
from unittest.mock import patch, MagicMock
from app.modules.rag.groundedness import compute_groundedness, cosine_similarity

def test_cosine_similarity():
    """Test basic cosine similarity calculations."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(vec1, vec2) == 1.0

    vec3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(vec1, vec3) == 0.0
    
    vec4 = [0.0, 0.0, 0.0]
    assert cosine_similarity(vec1, vec4) == 0.0

@patch("app.modules.rag.groundedness.get_embeddings")
def test_compute_groundedness(mock_get_embeddings):
    """Test groundedness calculation with mock embeddings."""
    mock_embed_query = MagicMock(side_effect=[
        [1.0, 0.0, 0.0],  # Answer embedding
        [0.9, 0.1, 0.0]   # Chunks embedding
    ])
    mock_model = MagicMock()
    mock_model.embed_query = mock_embed_query
    mock_get_embeddings.return_value = mock_model

    answer = "The system is high-risk."
    chunks = ["According to Article 6, the system is high-risk.", "It requires an assessment."]
    
    score = compute_groundedness(answer, chunks)
    
    assert score > 0.8
    assert score <= 1.0
    mock_embed_query.assert_any_call(answer)
    mock_embed_query.assert_any_call("According to Article 6, the system is high-risk.\n\nIt requires an assessment.")

@patch("app.modules.rag.groundedness.get_embeddings")
def test_compute_groundedness_empty(mock_get_embeddings):
    """Test groundedness with empty answer or chunks."""
    assert compute_groundedness("", ["chunk"]) == 0.0
    assert compute_groundedness("answer", []) == 0.0

@patch("app.modules.rag.groundedness.get_embeddings")
def test_compute_groundedness_exception(mock_get_embeddings):
    """Test groundedness handles exceptions by returning 0.0 (low confidence)."""
    mock_get_embeddings.side_effect = Exception("API error")
    
    score = compute_groundedness("answer", ["chunk"])
    assert score == 0.0
