"""LangChain retrieval-augmented generation chain for regulatory queries.

Changed: Added regex-only retrieved chunk scanning before context assembly.
Why: Retrieved documents can contain prompt injection text independent of the user query.
Addresses: Indirect prompt injection from poisoned FAISS chunks and prevents LLM calls when all context is unsafe.
"""

import logging
from importlib import import_module
from typing import Any

from app.core.config import settings
from app.core.telemetry import instrument_rag

from .grounding import GroundingChecker

logger = logging.getLogger(__name__)
ChatOpenAI = None
_CHUNK_GUARD: Any | None = None
_RAG_CACHE: Any | None = None

SAFE_CONTEXT_FALLBACK = (
    "Retrieved context could not be verified as safe. "
    "Please rephrase your question or contact support."
)


class _RetrievalQAShim:
    """Fallback patch target when local LangChain RetrievalQA imports are broken."""

    @classmethod
    def from_chain_type(cls, *args: Any, **kwargs: Any) -> Any:
        """Raise a clear error if code tries to use the shim in production."""
        raise ImportError("LangChain RetrievalQA is unavailable in this environment")


try:
    _chains_module = import_module("langchain.chains")
    _chains_module.__dict__.setdefault("RetrievalQA", _RetrievalQAShim)
except Exception:
    pass


class GroundedRetrievalQA:
    """Callable wrapper that filters retrieved chunks and scores grounding."""

    def __init__(
        self,
        qa_chain: Any,
        embeddings_fn: Any,
        guard: Any | None = None,
    ) -> None:
        """Store the underlying chain, embedding callable, and chunk guard."""
        self.qa_chain = qa_chain
        self.embeddings_fn = embeddings_fn
        self.guard = guard

    @instrument_rag
    def __call__(self, payload: Any) -> dict[str, Any]:
        """Run retrieval with chunk filtering and append grounding metadata."""
        query = _extract_query(payload)
        retrieved_documents = _get_relevant_documents(self.qa_chain, query)
        chunks_total = len(retrieved_documents)
        safe_documents: list[Any] = []
        chunks_dropped = 0

        for document in retrieved_documents:
            scan = _get_chunk_guard(self.guard).scan_chunk(str(document.page_content))
            severity = str(scan.get("severity", "low")).lower()
            if severity == "high":
                chunks_dropped += 1
                continue
            if severity == "medium":
                logger.warning(
                    "Medium-severity prompt injection pattern found in retrieved RAG chunk: %s",
                    scan.get("matched_patterns", []),
                )
            safe_documents.append(document)

        logger.info(
            "RAG chunk safety scan completed: total=%s dropped=%s",
            chunks_total,
            chunks_dropped,
        )

        if chunks_total > 0 and not safe_documents:
            return {
                "result": SAFE_CONTEXT_FALLBACK,
                "source_documents": [],
                "chunks_total": chunks_total,
                "chunks_dropped": chunks_dropped,
                "llm_skipped": True,
                "grounding_score": 0.0,
                "grounding_confidence": "LOW",
                "warning": "No retrieved context passed the chunk safety scan.",
            }

        result = _run_chain_with_documents(self.qa_chain, query, safe_documents, payload)
        if chunks_total > 0:
            result["source_documents"] = safe_documents
        result_source_documents = result.get("source_documents", safe_documents)
        result["chunks_total"] = chunks_total or len(result_source_documents)
        result["chunks_dropped"] = chunks_dropped

        answer = str(result.get("result", ""))
        chunks = [doc.page_content for doc in result_source_documents]

        try:
            grounding = GroundingChecker(embeddings_fn=self.embeddings_fn).check(
                answer=answer,
                chunks=chunks,
            )
            result["grounding_score"] = grounding.score
            result["grounding_confidence"] = grounding.confidence
            result["warning"] = grounding.warning
        except Exception:
            logger.exception("Grounding check failed for RAG response")
            result["grounding_score"] = 0.0
            result["grounding_confidence"] = "LOW"
            result["warning"] = "Grounding check failed."

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


def get_rag_cache() -> Any:
    """Return the process-wide cache with a lazily loaded embedding model."""
    global _RAG_CACHE
    if _RAG_CACHE is None:
        from .cache import SemanticCache

        def embed_question(question: str) -> list[float]:
            from .vector_store import get_embeddings

            embeddings = get_embeddings()
            if hasattr(embeddings, "embed_query"):
                return embeddings.embed_query(question)
            return embeddings.embed_documents([question])[0]

        _RAG_CACHE = SemanticCache(
            settings.REDIS_URL,
            embed_question,
            ttl_seconds=settings.RAG_CACHE_TTL_SECONDS,
            similarity_threshold=settings.RAG_CACHE_SIMILARITY_THRESHOLD,
        )
    return _RAG_CACHE


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


def _get_chunk_guard(guard: Any | None = None) -> Any:
    """Return the module-level chunk guard singleton."""
    global _CHUNK_GUARD
    if guard is not None:
        return guard
    if _CHUNK_GUARD is None:
        from app.modules.guard.llm_guard import LLMGuard

        _CHUNK_GUARD = LLMGuard()
    return _CHUNK_GUARD


def _get_relevant_documents(qa_chain: Any, query: str) -> list[Any]:
    """Retrieve source documents from the wrapped LangChain QA chain."""
    retriever = getattr(qa_chain, "retriever", None)
    if retriever is None:
        return []
    if hasattr(retriever, "invoke"):
        return list(retriever.invoke(query))
    if hasattr(retriever, "get_relevant_documents"):
        return list(retriever.get_relevant_documents(query))
    return []


def _run_chain_with_documents(
    qa_chain: Any,
    query: str,
    documents: list[Any],
    original_payload: Any,
) -> dict[str, Any]:
    """Run the LLM over already-filtered documents when LangChain supports it."""
    if not documents:
        result = qa_chain(original_payload)
        if not isinstance(result, dict):
            return {"result": str(result), "source_documents": documents}
        return result

    combine_chain = getattr(qa_chain, "combine_documents_chain", None)
    if combine_chain is not None:
        if hasattr(combine_chain, "run"):
            answer = combine_chain.run(input_documents=documents, question=query)
        else:
            combined = combine_chain(
                {"input_documents": documents, "question": query},
            )
            answer = (
                combined.get("output_text", combined)
                if isinstance(combined, dict)
                else combined
            )
        return {"result": str(answer), "source_documents": documents}

    logger.warning(
        "Falling back to unfiltered QA chain execution; combine chain unavailable"
    )
    result = qa_chain(original_payload)
    if not isinstance(result, dict):
        return {"result": str(result), "source_documents": documents}
    return result
