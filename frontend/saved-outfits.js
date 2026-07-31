/**
 * Saved outfits panel — POST /api/outfits/save and GET /api/outfits/history.
 */
(function () {
  function formatDate(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function itemSummary(outfit) {
    const items = outfit?.items || [];
    if (!items.length) return "No items";
    const names = items.slice(0, 3).map((item) => item.name || item.category);
    const suffix = items.length > 3 ? ` +${items.length - 3} more` : "";
    return `${names.join(", ")}${suffix}`;
  }

  function bind(config) {
    const {
      apiBaseUrl,
      getCurrentOutfit,
      showPanel,
      hidePanel,
      isSavedPanelVisible,
    } = config;

    const panel = document.getElementById("savedOutfitsPanel");
    const listEl = document.getElementById("savedOutfitsList");
    const emptyEl = document.getElementById("savedOutfitsEmpty");
    const saveBtn = document.getElementById("saveOutfitBtn");
    const railBtn = document.getElementById("savedOutfitsRailBtn");
    const wardrobeMain = document.getElementById("wardrobeMain");

    if (!panel || !listEl || !saveBtn) {
      return;
    }

    let savedOutfits = [];

    async function loadHistory() {
      const response = await fetch(`${apiBaseUrl}/api/outfits/history`, {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(`Failed to load saved outfits (${response.status})`);
      }
      savedOutfits = await response.json();
      renderList();
    }

    function renderList() {
      if (!savedOutfits.length) {
        listEl.innerHTML = "";
        emptyEl.hidden = false;
        return;
      }

      emptyEl.hidden = true;
      listEl.innerHTML = savedOutfits
        .map(
          (entry) => `
        <article class="saved-outfit-card">
          <div class="saved-outfit-meta">
            <span class="saved-outfit-date">${formatDate(entry.created_at)}</span>
            <span class="saved-outfit-count">${entry.item_count} piece${entry.item_count === 1 ? "" : "s"}</span>
          </div>
          <p class="saved-outfit-summary">${itemSummary(entry.outfit)}</p>
          ${
            entry.outfit?.reason
              ? `<p class="saved-outfit-reason">${entry.outfit.reason}</p>`
              : ""
          }
        </article>`
        )
        .join("");
    }

    async function saveCurrentOutfit() {
      const outfit = getCurrentOutfit();
      if (!outfit?.items?.length) {
        window.alert("Generate an outfit before saving.");
        return;
      }

      saveBtn.disabled = true;
      saveBtn.textContent = "Saving…";

      try {
        const response = await fetch(`${apiBaseUrl}/api/outfits/save`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ outfit }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(body.detail || `Save failed (${response.status})`);
        }
        saveBtn.textContent = "Saved ✓";
        await loadHistory();
        setTimeout(() => {
          saveBtn.textContent = "Save outfit";
        }, 1800);
      } catch (error) {
        console.error(error);
        window.alert(error.message || "Could not save outfit.");
        saveBtn.textContent = "Save outfit";
      } finally {
        saveBtn.disabled = false;
      }
    }

    function openSavedPanel() {
      showPanel();
      wardrobeMain.hidden = true;
      panel.hidden = false;
      if (railBtn) railBtn.classList.add("active");
      loadHistory().catch((error) => {
        console.error(error);
        emptyEl.hidden = false;
        emptyEl.textContent = "Could not load saved outfits.";
      });
    }

    function closeSavedPanel() {
      hidePanel();
      wardrobeMain.hidden = false;
      panel.hidden = true;
      if (railBtn) railBtn.classList.remove("active");
    }

    saveBtn.addEventListener("click", saveCurrentOutfit);
    if (railBtn) {
      railBtn.addEventListener("click", () => {
        if (isSavedPanelVisible()) {
          closeSavedPanel();
        } else {
          openSavedPanel();
        }
      });
    }

    return {
      loadHistory,
      openSavedPanel,
      closeSavedPanel,
    };
  }

  window.SavedOutfits = { bind };
})();
