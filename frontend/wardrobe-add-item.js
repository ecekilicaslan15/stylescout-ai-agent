/**
 * Wardrobe add-item form — POST /api/wardrobe/items and grid refresh.
 */
(function () {
  const STYLE_OPTIONS = ["casual", "elegant"];
  const EVENT_OPTIONS = ["everyday", "daily", "office"];

  function formatValidationErrors(detail) {
    if (!Array.isArray(detail)) {
      return typeof detail === "string" ? detail : "Could not add item.";
    }
    return detail
      .map((entry) => {
        const field = Array.isArray(entry.loc) ? entry.loc.slice(1).join(".") : "field";
        return `${field}: ${entry.msg}`;
      })
      .join(" ");
  }

  function buildCategoryOptions(labels) {
    return labels
      .filter((label) => label !== "All")
      .map((label) => `<option value="${label}">${label}</option>`)
      .join("");
  }

  function bind(config) {
    const {
      apiBaseUrl,
      getFilterCategories,
      getWardrobeItems,
      setWardrobeItems,
      render,
    } = config;

    const dialog = document.getElementById("addItemDialog");
    const form = document.getElementById("addItemForm");
    const errorEl = document.getElementById("addItemError");
    const categorySelect = document.getElementById("addItemCategory");
    const openBtn = document.getElementById("addItemBtn");
    const emptyBtn = document.getElementById("addItemEmptyBtn");

    if (!dialog || !form || !categorySelect) {
      return;
    }

    function refreshCategoryOptions() {
      categorySelect.innerHTML = buildCategoryOptions(getFilterCategories());
    }

    function openForm() {
      refreshCategoryOptions();
      form.reset();
      errorEl.hidden = true;
      errorEl.textContent = "";
      dialog.classList.add("show");
    }

    function closeForm() {
      dialog.classList.remove("show");
    }

    function readPayload(confirmDuplicate) {
      return {
        name: form.name.value.trim(),
        category: form.category.value,
        color: form.color.value.trim(),
        style: form.style.value,
        event: form.event.value,
        image_url: form.image_url.value.trim() || null,
        confirm_duplicate: confirmDuplicate,
      };
    }

    async function submitPayload(payload) {
      const response = await fetch(`${apiBaseUrl}/api/wardrobe/items`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const body = await response.json().catch(() => ({}));

      if (response.status === 409 && body.error === "duplicate_name") {
        if (window.confirm(body.message)) {
          return submitPayload({ ...payload, confirm_duplicate: true });
        }
        return { cancelled: true };
      }

      if (!response.ok) {
        errorEl.textContent = formatValidationErrors(body.detail);
        errorEl.hidden = false;
        return { failed: true };
      }

      setWardrobeItems([...getWardrobeItems(), body]);
      render();
      closeForm();
      return { created: true };
    }

    openBtn?.addEventListener("click", openForm);
    emptyBtn?.addEventListener("click", openForm);
    dialog.querySelector(".add-item-cancel")?.addEventListener("click", closeForm);
    dialog.querySelector(".add-item-scrim")?.addEventListener("click", closeForm);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      errorEl.hidden = true;
      errorEl.textContent = "";

      try {
        await submitPayload(readPayload(false));
      } catch (error) {
        console.error(error);
        errorEl.textContent = "Network error — could not add item.";
        errorEl.hidden = false;
      }
    });

    const styleSelect = form.querySelector('[name="style"]');
    if (styleSelect && !styleSelect.options.length) {
      styleSelect.innerHTML = STYLE_OPTIONS.map(
        (value) => `<option value="${value}">${value}</option>`
      ).join("");
    }

    const eventSelect = form.querySelector('[name="event"]');
    if (eventSelect && !eventSelect.options.length) {
      eventSelect.innerHTML = EVENT_OPTIONS.map(
        (value) => `<option value="${value}">${value}</option>`
      ).join("");
    }
  }

  window.WardrobeAddItem = { bind, STYLE_OPTIONS, EVENT_OPTIONS };
})();
