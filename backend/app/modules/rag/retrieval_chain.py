"""LangChain retrieval-augmented generation chain for regulatory queries."""

from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from app.core.config import settings
from .vector_store import load_vector_store


def get_qa_chain():
    """
    Build and return a RetrievalQA chain backed by the persisted FAISS index.

    Raises:
        FileNotFoundError: if the vector store has not been ingested yet
    """
    vector_store = load_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL or None,
        temperature=0,
    )

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )
