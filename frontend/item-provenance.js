/**
 * Shared owned/suggested badges and marketplace search links (SCOUT-014).
 */
(function () {
  const FALLBACK_REASON_SNIPPET =
    "Could not validate an outfit for your selected styling mode";
  const REPAIR_REASON_SUFFIX = " Adjusted after a validation issue.";

  function provenanceLabel(item, options) {
    const assumeWardrobeOwned = options && options.assumeWardrobeOwned;
    if (!item) return null;
    if (item.source === "wardrobe" || item.owned === true) return "owned";
    if (item.source === "suggested" || item.owned === false) return "suggested";
    if (assumeWardrobeOwned) return "owned";
    return null;
  }

  function provenanceBadgeHtml(item, options) {
    const label = provenanceLabel(item, options);
    if (label === "owned") {
      return '<span class="provenance-badge provenance-owned">Owned</span>';
    }
    if (label === "suggested") {
      return '<span class="provenance-badge provenance-suggested">Suggested</span>';
    }
    return "";
  }

  function shoppingLinkHtml(item) {
    if (!item || !item.shopping_link) return "";
    const safeUrl = String(item.shopping_link).replace(/"/g, "&quot;");
    const name = item.name || "this item";
    return (
      `<a class="shop-link-btn" href="${safeUrl}" target="_blank" rel="noopener noreferrer" ` +
      `aria-label="Search for ${name} on Vinted (opens marketplace search, not a product listing)" ` +
      `onclick="event.stopPropagation()">↗ Search on Vinted</a>`
    );
  }

  function wardrobeDisplayItem(item) {
    return { ...item, source: "wardrobe", owned: true };
  }

  function validationNoticeKind(reason) {
    const text = (reason || "").trim();
    if (!text) return null;
    if (text.includes(FALLBACK_REASON_SNIPPET)) return "fallback";
    if (text.includes(REPAIR_REASON_SUFFIX)) return "repaired";
    return null;
  }

  function validationNoticeHtml(reason) {
    const kind = validationNoticeKind(reason);
    if (!kind) return "";
    const cleaned = textEscape(reason);
    const title =
      kind === "fallback"
        ? "Fallback result"
        : "Adjusted after validation";
    const cssClass =
      kind === "fallback"
        ? "validation-notice validation-notice-fallback"
        : "validation-notice validation-notice-repaired";
    return (
      `<div class="${cssClass}" role="status" aria-live="polite">` +
      `<strong>${title}</strong><p>${cleaned}</p></div>`
    );
  }

  function textEscape(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  window.ItemProvenance = {
    provenanceLabel,
    provenanceBadgeHtml,
    shoppingLinkHtml,
    wardrobeDisplayItem,
    validationNoticeKind,
    validationNoticeHtml,
    FALLBACK_REASON_SNIPPET,
    REPAIR_REASON_SUFFIX,
  };
})();
