from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_PATH = REPO_ROOT / "frontend" / "src" / "components" / "DocumentEditor.tsx"
SANITIZER_PATH = REPO_ROOT / "frontend" / "src" / "utils" / "sanitizePreviewHtml.ts"


def test_document_editor_sanitizes_markdown_preview():
    editor_source = EDITOR_PATH.read_text(encoding="utf-8")

    assert "sanitizePreviewHtml" in editor_source
    assert "dangerouslySetInnerHTML" in editor_source
    assert "previewHtml" in editor_source
    assert "marked.parse(content, { async: false })" in editor_source


def test_preview_sanitizer_blocks_scriptable_content():
    sanitizer_source = SANITIZER_PATH.read_text(encoding="utf-8")

    assert "name.startsWith('on')" in sanitizer_source
    assert "name === 'style'" in sanitizer_source
    assert "name === 'srcdoc'" in sanitizer_source
    assert "URL_ATTRIBUTES" in sanitizer_source
    assert "SAFE_URL_PATTERN" in sanitizer_source

    for tag_name in ("'script'", "'iframe'", "'object'", "'embed'", "'svg'"):
        assert tag_name in sanitizer_source
