"""Tests for honest wardrobe images (image_verified / category silhouettes)."""

from api.main import serialize_wardrobe_item
from wardrobe.category_images import CATEGORY_IMAGES


class TestWardrobeImageHonesty:
    def test_flagged_beige_blazer_uses_category_silhouette(self):
        payload = serialize_wardrobe_item(
            {
                "id": "itm_test_beige_blazer",
                "name": "Beige Blazer",
                "category": "outerwear",
                "color": "beige",
                "style": "elegant",
                "image_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=520&q=80",
                "image_verified": False,
            }
        )

        assert payload["image_url"] == CATEGORY_IMAGES["outerwear"]
        assert "1594938298603" not in payload["image_url"]

    def test_verified_item_renders_its_own_image_url(self):
        shirt_url = "https://images.unsplash.com/photo-1596755094514-f87e34085b2b?w=520&q=80"
        payload = serialize_wardrobe_item(
            {
                "id": "itm_test_white_shirt",
                "name": "White Elegant Shirt",
                "category": "tops",
                "color": "white",
                "style": "elegant",
                "image_url": shirt_url,
            }
        )

        assert payload["image_url"] == shirt_url

    def test_missing_image_url_falls_back_to_category_placeholder(self):
        payload = serialize_wardrobe_item(
            {
                "id": "itm_test_white_shirt",
                "name": "White Elegant Shirt",
                "category": "tops",
                "color": "white",
                "style": "elegant",
            }
        )

        assert payload["image_url"] == CATEGORY_IMAGES["tops"]
