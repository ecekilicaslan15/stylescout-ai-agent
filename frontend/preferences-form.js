/**
 * Skippable shopping preferences form — GET/POST /api/preferences.
 * Shown after a successful outfit generation; never blocks generation.
 */
(function () {
  function bind(config) {
    const { apiBaseUrl, fetchOptions, onRevealOutfit } = config;
    const panel = document.getElementById("preferencesPanel");
    const form = document.getElementById("preferencesForm");
    const skipBtn = document.getElementById("preferencesSkipBtn");
    const errorEl = document.getElementById("preferencesError");
    const sizeInput = document.getElementById("preferencesSize");
    const maxPriceInput = document.getElementById("preferencesMaxPrice");

    if (!panel || !form || !skipBtn) {
      return { showAfterOutfit: () => {} };
    }

    let dismissedForSession = false;

    function hidePanel() {
      panel.hidden = true;
      errorEl.hidden = true;
      errorEl.textContent = "";
    }

    function showPanel() {
      if (dismissedForSession) {
        return;
      }
      panel.hidden = false;
    }

    async function loadExistingPreferences() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/preferences`, fetchOptions);
        if (!response.ok) {
          return;
        }
        const data = await response.json();
        if (sizeInput && data.size) {
          sizeInput.value = data.size;
        }
        if (maxPriceInput && data.max_price != null) {
          maxPriceInput.value = String(data.max_price);
        }
      } catch (error) {
        console.error(error);
      }
    }

    skipBtn.addEventListener("click", () => {
      dismissedForSession = true;
      hidePanel();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      errorEl.hidden = true;
      errorEl.textContent = "";

      const payload = {};
      const sizeValue = sizeInput?.value.trim();
      const maxPriceValue = maxPriceInput?.value.trim();
      if (sizeValue) {
        payload.size = sizeValue;
      }
      if (maxPriceValue) {
        const parsed = Number(maxPriceValue);
        if (!Number.isFinite(parsed)) {
          errorEl.textContent = "Enter a valid max price or leave it blank.";
          errorEl.hidden = false;
          return;
        }
        payload.max_price = parsed;
      }

      try {
        const response = await fetch(`${apiBaseUrl}/api/preferences`, {
          ...fetchOptions,
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          let message = `Could not save preferences (${response.status}).`;
          try {
            const body = await response.json();
            if (typeof body.detail === "string") {
              message = body.detail;
            } else if (Array.isArray(body.detail)) {
              message = body.detail.map((entry) => entry.msg).join(" ");
            }
          } catch (_parseError) {
            /* keep default message */
          }
          errorEl.textContent = message;
          errorEl.hidden = false;
          return;
        }
        dismissedForSession = true;
        hidePanel();
      } catch (error) {
        console.error(error);
        errorEl.textContent = "Could not reach the server. Try again later.";
        errorEl.hidden = false;
      }
    });

    function showAfterOutfit(outfitPayload) {
      const items = outfitPayload?.items || [];
      if (!items.length) {
        hidePanel();
        return;
      }
      dismissedForSession = false;
      form.reset();
      loadExistingPreferences();
      showPanel();
      if (typeof onRevealOutfit === "function") {
        onRevealOutfit(outfitPayload);
      }
    }

    hidePanel();
    return { showAfterOutfit };
  }

  window.ShoppingPreferences = { bind };
})();
