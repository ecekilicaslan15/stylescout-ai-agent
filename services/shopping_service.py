"""Deterministic marketplace deep-link generation for suggested outfit items."""

from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urlencode

from models.search_spec import SearchSpec, build_search_spec

# Human-readable category tokens appended to the Vinted search query.
CATEGORY_QUERY_TERMS: dict[str, str] = {
    "top": "top",
    "bottom": "trousers",
    "shoes": "shoes",
    "outerwear": "jacket",
    "accessory": "accessory",
}


class DeepLinkProvider(ABC):
    """Builds a marketplace search URL from a SearchSpec (no API/scraping)."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider key (e.g. vinted)."""

    @abstractmethod
    def build_search_url(self, spec: SearchSpec) -> str:
        """Return a public catalog/search page URL for the spec."""


class VintedDeepLinkProvider(DeepLinkProvider):
    """Vinted catalog search via the public search_text query parameter."""

    BASE_CATALOG_URL = "https://www.vinted.com/catalog"

    @property
    def provider_id(self) -> str:
        return "vinted"

    def build_search_url(self, spec: SearchSpec) -> str:
        query = build_search_query(spec)
        params = urlencode({"search_text": query})
        return f"{self.BASE_CATALOG_URL}?{params}"


def build_search_query(spec: SearchSpec) -> str:
    """Compose a deterministic keyword query from spec fields."""
    category_term = CATEGORY_QUERY_TERMS.get(spec.category, spec.category)
    parts = [spec.color, spec.style, category_term, spec.name]
    if spec.size:
        parts.append(f"size {spec.size}")
    if spec.max_price is not None:
        parts.append(f"under {spec.max_price:g}")
    return " ".join(part for part in parts if part).strip()


class ShoppingService:
    """Build search specs and marketplace deep-links for suggested items."""

    def __init__(self, providers: list[DeepLinkProvider] | None = None) -> None:
        self._providers = providers or [VintedDeepLinkProvider()]

    def build_search_spec(self, item: dict, preferences: dict | None = None) -> SearchSpec:
        return build_search_spec(item, preferences=preferences)

    def build_deep_links(self, spec: SearchSpec) -> dict[str, str]:
        return {provider.provider_id: provider.build_search_url(spec) for provider in self._providers}

    def primary_shopping_link(self, item: dict, preferences: dict | None = None) -> str:
        spec = self.build_search_spec(item, preferences=preferences)
        links = self.build_deep_links(spec)
        return links.get("vinted") or next(iter(links.values()))

    def enrich_suggested_item(self, item: dict, preferences: dict | None = None) -> dict:
        """Attach shopping_link to a copy of item when it is suggested/unowned."""
        enriched = dict(item)
        if enriched.get("source") == "suggested" and enriched.get("owned") is False:
            enriched["shopping_link"] = self.primary_shopping_link(enriched, preferences=preferences)
        return enriched
