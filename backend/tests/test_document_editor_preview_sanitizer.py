from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_PATH = REPO_ROOT / "frontend" / "src" / "components" / "DocumentEditor.tsx"


def test_document_editor_sanitizes_markdown_preview():
    editor_source = EDITOR_PATH.read_text(encoding="utf-8")

    assert "DOMPurify" in editor_source
    assert "DOMPurify.sanitize" in editor_source
    assert "dangerouslySetInnerHTML" in editor_source
    assert "previewHtml" in editor_source
    assert "marked.parse(content, { async: false })" in editor_source


def test_document_editor_does_not_use_custom_preview_sanitizer():
    editor_source = EDITOR_PATH.read_text(encoding="utf-8")

    assert "sanitizePreviewHtml" not in editor_source
