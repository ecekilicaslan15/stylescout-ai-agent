"""Structural tests for SCOUT-014 transparency UI (badges, search links, notices, privacy)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVENANCE_JS = ROOT / "frontend" / "item-provenance.js"
INDEX_HTML = ROOT / "frontend" / "index.html"


class TestTransparencyUi:
    def test_item_provenance_module_exports_shared_helpers(self):
        source = PROVENANCE_JS.read_text(encoding="utf-8")
        assert "window.ItemProvenance" in source
        assert "provenanceBadgeHtml" in source
        assert "shoppingLinkHtml" in source
        assert "wardrobeDisplayItem" in source
        assert "validationNoticeHtml" in source
        assert "Search on Vinted" in source
        assert "Could not validate an outfit for your selected styling mode" in source

    def test_index_html_uses_shared_provenance_module_everywhere(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        assert 'src="item-provenance.js"' in html
        assert "window.ItemProvenance" in html
        assert "IP.wardrobeDisplayItem" in html
        assert "IP.provenanceBadgeHtml" in html
        assert "IP.shoppingLinkHtml" in html
        assert "renderValidationNotice" in html
        assert 'id="validationNotice"' in html
        assert "validation-notice-fallback" in html
        assert 'id="privacyDialog"' in html
        assert "single shared file on the server" in html
        assert "↗ Shop search" not in html

    def test_fallback_notice_is_separate_from_why_text_builder(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        assert "validationNoticeKind(reason)" in html
        assert "buildWhyText" in html
