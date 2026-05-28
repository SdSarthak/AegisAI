"""LangChain retrieval-augmented generation chain for regulatory queries."""

import logging
from typing import Any

from app.core.config import settings

from .groundedness import GroundednessConfig, HybridGroundednessChecker

logger = logging.getLogger(__name__)
ChatOpenAI = None
load_qa_chain = None


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


def load_vector_store(user_id: int | None = None) -> Any:
    """Lazy wrapper around vector-store loading for lighter module imports."""
    from .vector_store import load_vector_store as loader

    return loader(user_id=user_id)


def get_qa_chain(user_id: int | None = None):
    """
    Build and return a RetrievalQA chain backed by the persisted FAISS index.

    Args:
        user_id: Optional user ID for tenant-isolated vector store.

    Raises:
        FileNotFoundError: if the vector store has not been ingested yet
    """
    global ChatOpenAI

    from langchain.chains import RetrievalQA

    if ChatOpenAI is None:
        from langchain_openai import ChatOpenAI as LangChainChatOpenAI

        ChatOpenAI = LangChainChatOpenAI

    vector_store = load_vector_store(user_id=user_id)
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


def query_with_guard(question: str, guard: Any) -> dict[str, Any]:
    """
    Retrieve document chunks, filter them through the Guard pipeline,
    and generate a grounded answer from the safe subset only.

    Implements Layer 2 protection (chunk-level scanning) for issue #748.
    Layer 1 (query-level scanning) is performed by the RAG endpoint
    before this function is called.

    Args:
        question: The (possibly sanitized) user question.
        guard: An ``LLMGuard`` instance used to scan each retrieved chunk.

    Returns:
        dict matching the shape returned by ``GroundedRetrievalQA.__call__``:
        ``result``, ``source_documents``, ``groundedness_score``,
        ``low_confidence``, ``confidence_tier``, ``per_verifier_scores``,
        ``flagged_reason``.

    Raises:
        FileNotFoundError: if the FAISS index has not been built yet.
    """
    global ChatOpenAI, load_qa_chain

    if load_qa_chain is None:
        from langchain.chains.question_answering import load_qa_chain as chain_loader

        load_qa_chain = chain_loader

    if ChatOpenAI is None:
        from langchain_openai import ChatOpenAI as LangChainChatOpenAI

        ChatOpenAI = LangChainChatOpenAI

    vector_store = load_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    embeddings_fn = _get_embeddings_fn(vector_store)

    raw_docs = retriever.get_relevant_documents(question)

    safe_docs = [
        doc for doc in raw_docs if guard.scan_chunk(doc.page_content) != "block"
    ]

    if not safe_docs:
        logger.warning("query_with_guard: all retrieved chunks blocked by Guard")
        return {
            "result": (
                "Your question could not be answered safely. "
                "All retrieved context was flagged by the security pipeline."
            ),
            "source_documents": [],
            "groundedness_score": 0.0,
            "low_confidence": True,
            "confidence_tier": "unsafe",
            "per_verifier_scores": {},
            "flagged_reason": "All retrieved chunks were blocked by the Guard pipeline.",
        }

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL or None,
        temperature=0,
    )

    qa_chain = load_qa_chain(llm, chain_type="stuff")
    raw_result = qa_chain.invoke({"input_documents": safe_docs, "question": question})
    answer = raw_result.get("output_text", raw_result.get("result", ""))
    chunks = [doc.page_content for doc in safe_docs]

    try:
        checker = HybridGroundednessChecker(
            embeddings_fn=embeddings_fn,
            config=GroundednessConfig(),
        )
        groundedness = checker.check(answer=answer, chunks=chunks, query=question)
        return {
            "result": answer,
            "source_documents": safe_docs,
            "groundedness_score": groundedness.groundedness_score,
            "low_confidence": groundedness.low_confidence,
            "confidence_tier": groundedness.confidence_tier,
            "per_verifier_scores": groundedness.per_verifier_scores,
            "flagged_reason": groundedness.flagged_reason,
        }
    except Exception:
        logger.exception("Groundedness check failed in query_with_guard")
        return {
            "result": answer,
            "source_documents": safe_docs,
            "groundedness_score": 0.0,
            "low_confidence": True,
            "confidence_tier": "unknown",
            "per_verifier_scores": {},
            "flagged_reason": "Groundedness check failed.",
        }
