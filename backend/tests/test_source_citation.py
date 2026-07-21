"""Unit tests for _build_source_citation helper."""
from unittest.mock import MagicMock
from app.modules.rag.retrieval_chain import _build_source_citation


def _make_doc(metadata: dict, content: str = "") -> MagicMock:
    doc = MagicMock()
    doc.metadata = metadata
    doc.page_content = content
    return doc


def test_extracts_filename():
    doc = _make_doc({"source": "/data/eu_ai_act.pdf"})
    result = _build_source_citation(doc)
    assert result["filename"] == "eu_ai_act.pdf"


def test_extracts_explicit_article_and_paragraph():
    doc = _make_doc({"source": "eu_ai_act.pdf", "article": "Article 10", "paragraph": 2})
    result = _build_source_citation(doc)
    assert result["article"] == "Article 10"
    assert result["paragraph"] == 2


def test_parses_article_from_content():
    doc = _make_doc(
        {"source": "eu_ai_act.pdf"},
        content="Article 13 sets out transparency obligations..."
    )
    result = _build_source_citation(doc)
    assert result.get("article") == "Article 13"


def test_missing_metadata_returns_empty_filename():
    doc = _make_doc({})
    result = _build_source_citation(doc)
    assert result["filename"] == ""
    assert "article" not in result
