"""LangChain retrieval-augmented generation chain for regulatory queries."""

import logging
from typing import Any

from app.core.config import settings

from .groundedness import GroundednessConfig, HybridGroundednessChecker

logger = logging.getLogger(__name__)
ChatOpenAI = None


class GroundedRetrievalQA:
    """Callable wrapper that adds groundedness scores to RetrievalQA results."""

    def __init__(self, qa_chain: Any, embeddings_fn: Any) -> None:
        """Store the underlying chain and embedding callable."""
        self.qa_chain = qa_chain
        self.embeddings_fn = embeddings_fn

    def __call__(self, payload: Any) -> dict[str, Any]:
        """Run the QA chain and append groundedness fields to the result dict."""
        result = self.qa_chain(payload)
        query = _extract_query(payload)
        answer = str(result.get("result", ""))
        source_documents = result.get("source_documents", [])
        chunks = [doc.page_content for doc in source_documents]

        try:
            checker = HybridGroundednessChecker(
                embeddings_fn=self.embeddings_fn,
                config=GroundednessConfig(),
            )
            groundedness = checker.check(answer=answer, chunks=chunks, query=query)
            result["groundedness_score"] = groundedness.groundedness_score
            result["low_confidence"] = groundedness.low_confidence
            result["confidence_tier"] = groundedness.confidence_tier
            result["per_verifier_scores"] = groundedness.per_verifier_scores
            result["flagged_reason"] = groundedness.flagged_reason
        except Exception:
            logger.exception("Groundedness check failed for RAG response")
            result["groundedness_score"] = 0.0
            result["low_confidence"] = True
            result["confidence_tier"] = "unknown"
            result["per_verifier_scores"] = {}
            result["flagged_reason"] = "Groundedness check failed."

        return result

    def __eq__(self, other: object) -> bool:
        """Compare equal to the wrapped chain for compatibility with tests."""
        return self.qa_chain == other

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the wrapped LangChain chain."""
        return getattr(self.qa_chain, name)


def load_vector_store() -> Any:
    """Lazy wrapper around vector-store loading for lighter module imports."""
    from .vector_store import load_vector_store as loader

    return loader()


def get_qa_chain():
    """
    Build and return a RetrievalQA chain backed by the persisted FAISS index.

    Raises:
        FileNotFoundError: if the vector store has not been ingested yet
    """
    global ChatOpenAI

    from langchain.chains import RetrievalQA

    if ChatOpenAI is None:
        from langchain_openai import ChatOpenAI as LangChainChatOpenAI

        ChatOpenAI = LangChainChatOpenAI

    vector_store = load_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    embeddings_fn = _get_embeddings_fn(vector_store)

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL or None,
        temperature=0,
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )

    return GroundedRetrievalQA(qa_chain=qa_chain, embeddings_fn=embeddings_fn)


def _get_embeddings_fn(vector_store: Any) -> Any:
    embeddings = vector_store.embedding_function
    if hasattr(embeddings, "embed_documents"):
        return embeddings.embed_documents
    return embeddings


def _extract_query(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("query", ""))
    return str(payload)
