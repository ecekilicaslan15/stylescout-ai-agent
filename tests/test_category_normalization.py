"""Tests for canonical wardrobe category normalization."""

import pytest

from wardrobe.constants import CATEGORIES, DISPLAY_LABELS, FILTER_LABELS
from wardrobe.normalization import normalize_stored_category, to_display_category


class TestCategoryNormalization:
    @pytest.mark.parametrize("raw", ["tops", "Tops", "top", "TOP"])
    def test_aliases_normalize_to_tops(self, raw: str):
        assert normalize_stored_category(raw) == "tops"

    def test_display_label_for_storage_key(self):
        assert to_display_category("tops") == "Tops"

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown wardrobe category"):
            normalize_stored_category("dress")

    def test_filter_labels_include_all_and_display_order(self):
        assert FILTER_LABELS[0] == "All"
        assert FILTER_LABELS[1:] == [DISPLAY_LABELS[key] for key in CATEGORIES]
