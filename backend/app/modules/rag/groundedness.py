"""Groundedness validation for RAG responses.

Computes semantic similarity between the LLM's generated answer and
the retrieved source chunks to flag potential hallucinations.
"""

import numpy as np
import logging
from app.modules.rag.vector_store import get_embeddings

logger = logging.getLogger(__name__)

def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def compute_groundedness(answer: str, chunks: list[str]) -> float:
    """
    Compute a groundedness score for the generated answer based on source chunks.
    
    Embeds the answer and the combined source chunks, then computes their
    cosine similarity.
    
    Args:
        answer: The generated answer from the LLM.
        chunks: List of retrieved source document strings.
        
    Returns:
        float: A groundedness score between 0.0 and 1.0.
               Returns 0.0 if no chunks are provided or if an error occurs.
    """
    if not answer or not chunks:
        return 0.0

    try:
        embeddings_model = get_embeddings()
        
        # We combine all chunks into a single string to represent the "context"
        # Alternatively, we could compute similarity against each chunk and take the max,
        # but combined context is often more representative of the overall support.
        combined_context = "\n\n".join(chunks)
        
        # Embed both the answer and the combined context
        # embed_query is usually used for a single string in LangChain OpenAIEmbeddings
        answer_embedding = embeddings_model.embed_query(answer)
        context_embedding = embeddings_model.embed_query(combined_context)
        
        score = cosine_similarity(answer_embedding, context_embedding)
        
        # Ensure score is bound between 0.0 and 1.0 (cosine similarity can be [-1, 1])
        return max(0.0, min(1.0, score))
        
    except Exception as e:
        logger.error(f"Error computing groundedness: {str(e)}")
        # Fail open with a 0.0 score (which will flag as low confidence)
        return 0.0
