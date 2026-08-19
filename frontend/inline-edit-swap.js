/**
 * Board inline edit — free-text swap instruction for POST /api/outfits/inline-edit.
 */
(function () {
  const DEFAULT_PLACEHOLDER = "e.g. make it more casual, or a comfortable shoe for warm weather";

  function bind(config) {
    const {
      apiBaseUrl,
      getCurrentOutfit,
      getSessionOutfit,
      setSessionOutfitItem,
      updateOutfitFromResponse,
      renderBoard,
      setWhyText,
      clearExplanation,
      fetchOptions = { credentials: "include" },
    } = config;

    let activeSlot = null;

    function closeSwapInput() {
      const existing = document.querySelector(".swap-inline-form");
      if (existing) existing.remove();
      activeSlot = null;
    }

    function buildForm(slot, current) {
      closeSwapInput();
      activeSlot = slot;
      const host = document.querySelector(`.bg-item[data-slot="${slot}"]`);
      if (!host) return;

      const form = document.createElement("form");
      form.className = "swap-inline-form";
      form.innerHTML = `
        <label class="swap-inline-label">Replace ${slot.toLowerCase()}</label>
        <input type="text" class="swap-inline-input" placeholder="${DEFAULT_PLACEHOLDER}" autocomplete="off" />
        <div class="swap-inline-actions">
          <button type="button" class="swap-inline-cancel">Cancel</button>
          <button type="submit" class="swap-inline-submit">Replace</button>
        </div>
        <p class="swap-inline-error" hidden></p>
      `;

      const input = form.querySelector(".swap-inline-input");
      const errorEl = form.querySelector(".swap-inline-error");
      const cancelBtn = form.querySelector(".swap-inline-cancel");

      cancelBtn.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        closeSwapInput();
      });

      form.addEventListener("click", (event) => event.stopPropagation());
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        const instruction = input.value.trim();
        if (!instruction) {
          errorEl.textContent = "Describe how you want to change this piece.";
          errorEl.hidden = false;
          return;
        }
        await submitSwap(slot, current, instruction, host, form, errorEl);
      });

      host.appendChild(form);
      input.focus();
    }

    async function submitSwap(slot, current, instruction, host, form, errorEl) {
      const outfit = getCurrentOutfit();
      if (!outfit?.items?.length) {
        setWhyText("No active outfit to edit.");
        return;
      }

      const submitBtn = form.querySelector(".swap-inline-submit");
      submitBtn.disabled = true;
      submitBtn.textContent = "Replacing…";
      errorEl.hidden = true;
      host.classList.add("swapping");

      try {
        const response = await fetch(`${apiBaseUrl}/api/outfits/inline-edit`, {
          method: "POST",
          ...fetchOptions,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            current_outfit: outfit,
            target_item: current,
            instruction,
          }),
        });

        const body = await response.json().catch(() => ({}));

        if (!response.ok) {
          const detail =
            typeof body.detail === "string"
              ? body.detail
              : "Could not update that item. Try rephrasing your request.";
          throw new Error(detail);
        }

        if (body.outfit?.items) {
          updateOutfitFromResponse(body.outfit, slot, current, body.updated_item);
        } else if (body.updated_item) {
          setSessionOutfitItem(slot, body.updated_item);
        }

        if (body.message) setWhyText(body.message);
        if (typeof clearExplanation === "function") clearExplanation();
        closeSwapInput();
        renderBoard();
      } catch (error) {
        console.error(error);
        host.classList.remove("swapping");
        errorEl.textContent =
          error.message ||
          "Could not understand that edit — try comfort, formality, color, or weather words.";
        errorEl.hidden = false;
        submitBtn.disabled = false;
        submitBtn.textContent = "Replace";
      }
    }

    function openSwapInput(slot) {
      const current = getSessionOutfit()[slot];
      if (!current) return;
      buildForm(slot, current);
    }

    return { openSwapInput, closeSwapInput };
  }

  window.InlineEditSwap = { bind };
})();
