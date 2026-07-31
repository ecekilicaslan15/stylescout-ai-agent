/**
 * Wardrobe edit/delete — PATCH and DELETE /api/wardrobe/items/{id}.
 */
(function () {
  const STYLE_OPTIONS = ["casual", "elegant"];
  const EVENT_OPTIONS = ["everyday", "daily", "office"];

  function formatValidationErrors(detail) {
    if (!Array.isArray(detail)) {
      return typeof detail === "string" ? detail : "Could not save changes.";
    }
    return detail
      .map((entry) => {
        const field = Array.isArray(entry.loc) ? entry.loc.slice(1).join(".") : "field";
        return `${field}: ${entry.msg}`;
      })
      .join(" ");
  }

  function buildCategoryOptions(labels, selected) {
    return labels
      .filter((label) => label !== "All")
      .map(
        (label) =>
          `<option value="${label}"${label === selected ? " selected" : ""}>${label}</option>`
      )
      .join("");
  }

  function bind(config) {
    const {
      apiBaseUrl,
      getFilterCategories,
      getWardrobeItems,
      setWardrobeItems,
      render,
      getDetailItemId,
      closeDetail,
      refreshDetail,
      fetchOptions = { credentials: "include" },
    } = config;

    const editDialog = document.getElementById("editItemDialog");
    const editForm = document.getElementById("editItemForm");
    const editErrorEl = document.getElementById("editItemError");
    const editCategorySelect = document.getElementById("editItemCategory");
    const editBtn = document.getElementById("editItemBtn");
    const deleteBtn = document.getElementById("deleteItemBtn");

    const deleteDialog = document.getElementById("deleteItemDialog");
    const deleteErrorEl = document.getElementById("deleteItemError");
    const deleteNameEl = document.getElementById("deleteItemName");

    if (!editDialog || !editForm || !deleteDialog) {
      return;
    }

    let editingItemId = null;

    function currentItem() {
      const id = editingItemId || getDetailItemId();
      if (!id) return null;
      return getWardrobeItems().find((item) => item.id === id) || null;
    }

    function openEditForm() {
      const item = currentItem();
      if (!item) return;

      editingItemId = item.id;
      editCategorySelect.innerHTML = buildCategoryOptions(getFilterCategories(), item.category);
      editForm.name.value = item.name;
      editForm.color.value = item.color;
      editForm.style.value = item.style;
      editForm.event.value = item.event;
      editForm.image_url.value = item.image_url && !item.image_url.startsWith("/")
        ? item.image_url
        : "";
      editErrorEl.hidden = true;
      editErrorEl.textContent = "";
      editDialog.classList.add("show");
    }

    function closeEditForm() {
      editDialog.classList.remove("show");
      editingItemId = null;
    }

    function openDeleteConfirm() {
      const item = currentItem();
      if (!item) return;

      editingItemId = item.id;
      deleteNameEl.textContent = item.name;
      deleteErrorEl.hidden = true;
      deleteErrorEl.textContent = "";
      deleteDialog.classList.add("show");
    }

    function closeDeleteConfirm() {
      deleteDialog.classList.remove("show");
      editingItemId = null;
    }

    function readEditPayload(confirmDuplicate) {
      return {
        name: editForm.name.value.trim(),
        category: editForm.category.value,
        color: editForm.color.value.trim(),
        style: editForm.style.value,
        event: editForm.event.value,
        image_url: editForm.image_url.value.trim() || null,
        confirm_duplicate: confirmDuplicate,
      };
    }

    async function submitEdit(payload) {
      const itemId = editingItemId || getDetailItemId();
      if (!itemId) return { failed: true };

      const response = await fetch(`${apiBaseUrl}/api/wardrobe/items/${itemId}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (response.status === 409) {
        const body = await response.json().catch(() => ({}));
        if (body.error === "duplicate_name") {
          if (window.confirm(body.message)) {
            return submitEdit({ ...payload, confirm_duplicate: true });
          }
          return { cancelled: true };
        }
      }

      const body = await response.json().catch(() => ({}));

      if (!response.ok) {
        editErrorEl.textContent = formatValidationErrors(body.detail);
        editErrorEl.hidden = false;
        return { failed: true };
      }

      const items = getWardrobeItems().filter((item) => item.id !== itemId);
      setWardrobeItems([...items, body]);
      render();
      closeEditForm();
      if (getDetailItemId() === itemId) {
        refreshDetail(body.id);
      }
      return { updated: true };
    }

    async function submitDelete() {
      const itemId = editingItemId || getDetailItemId();
      if (!itemId) return;

      const response = await fetch(`${apiBaseUrl}/api/wardrobe/items/${itemId}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (response.status === 404) {
        deleteErrorEl.textContent = "Item not found — it may have already been removed.";
        deleteErrorEl.hidden = false;
        return;
      }

      if (!response.ok) {
        deleteErrorEl.textContent = "Could not delete item.";
        deleteErrorEl.hidden = false;
        return;
      }

      setWardrobeItems(getWardrobeItems().filter((item) => item.id !== itemId));
      render();
      closeDeleteConfirm();
      closeDetail();
    }

    editBtn?.addEventListener("click", openEditForm);
    deleteBtn?.addEventListener("click", openDeleteConfirm);

    editDialog.querySelector(".edit-item-cancel")?.addEventListener("click", closeEditForm);
    editDialog.querySelector(".edit-item-scrim")?.addEventListener("click", closeEditForm);

    deleteDialog.querySelector(".delete-item-cancel")?.addEventListener("click", closeDeleteConfirm);
    deleteDialog.querySelector(".delete-item-scrim")?.addEventListener("click", closeDeleteConfirm);
    deleteDialog.querySelector(".delete-item-confirm")?.addEventListener("click", () => {
      submitDelete().catch((error) => {
        console.error(error);
        deleteErrorEl.textContent = "Network error — could not delete item.";
        deleteErrorEl.hidden = false;
      });
    });

    editForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      editErrorEl.hidden = true;
      editErrorEl.textContent = "";

      try {
        await submitEdit(readEditPayload(false));
      } catch (error) {
        console.error(error);
        editErrorEl.textContent = "Network error — could not save changes.";
        editErrorEl.hidden = false;
      }
    });

    const styleSelect = editForm.querySelector('[name="style"]');
    if (styleSelect && !styleSelect.options.length) {
      styleSelect.innerHTML = STYLE_OPTIONS.map(
        (value) => `<option value="${value}">${value}</option>`
      ).join("");
    }

    const eventSelect = editForm.querySelector('[name="event"]');
    if (eventSelect && !eventSelect.options.length) {
      eventSelect.innerHTML = EVENT_OPTIONS.map(
        (value) => `<option value="${value}">${value}</option>`
      ).join("");
    }
  }

  window.WardrobeEditItem = { bind, STYLE_OPTIONS, EVENT_OPTIONS };
})();
