// Tipo form interactions:
//   1. Add/remove rows in the FieldFormSet (Django's TOTAL_FORMS in sync).
//   2. Each row is a collapsible card with a drag handle (SortableJS) and
//      ↑/↓ buttons. The visible "Orden" input is gone; the hidden ``order``
//      input is rewritten by index just before submit.
//   3. Chip-style options/extensions editor that mirrors a hidden CSV input.
//   4. Live <select> preview rendered from the SELECT field's chip list.
//   5. Predefined-extension multiselect for FILE fields.
//   6. The header summary (label + type badge) updates live so collapsed
//      cards are still scannable.
(function () {
  "use strict";

  const PREFIX = "fields";

  // ---------- formset row management ----------

  const totalFormsInput = document.querySelector(`input[name="${PREFIX}-TOTAL_FORMS"]`);
  const rowsContainer = document.getElementById("field-rows");
  const emptyTemplate = document.getElementById("empty-field-row");
  const addButton = document.getElementById("add-field-row");

  function nextIndex() {
    return parseInt(totalFormsInput.value, 10) || 0;
  }

  function addRow() {
    const idx = nextIndex();
    const html = emptyTemplate.innerHTML.replace(/__prefix__/g, String(idx));
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    const row = wrapper.firstElementChild;
    if (!row) return;
    rowsContainer.appendChild(row);
    totalFormsInput.value = String(idx + 1);
    initRow(row);
    // Collapse all others, expand the new one for editing.
    rowsContainer.querySelectorAll(".field-row").forEach((r) => {
      setOpen(r, r === row);
    });
    row.querySelector(".field-label-input")?.focus();
  }

  if (addButton && totalFormsInput && rowsContainer && emptyTemplate) {
    addButton.addEventListener("click", function (e) {
      e.preventDefault();
      addRow();
    });
  }

  // ---------- collapse / expand ----------

  function setOpen(row, open) {
    row.classList.toggle("is-open", open);
    const toggle = row.querySelector(".field-row-toggle");
    if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
    // Swap the actual icon class so the visual state survives even if CSS
    // transforms are disabled (a pure rotate would mislead users in that
    // edge case — flagged by the post-UX code review).
    const caret = row.querySelector(".field-row-caret");
    if (caret) {
      caret.classList.toggle("bi-chevron-down", open);
      caret.classList.toggle("bi-chevron-right", !open);
    }
  }

  function initToggle(row) {
    const toggle = row.querySelector(".field-row-toggle");
    if (!toggle) return;
    // Default state: open if no label yet (just added or empty), collapsed
    // otherwise — keeps existing tipos scannable on edit.
    const label = row.querySelector(".field-label-input")?.value || "";
    setOpen(row, label.trim() === "");
    toggle.addEventListener("click", () => {
      setOpen(row, !row.classList.contains("is-open"));
    });
  }

  // ---------- header summary sync ----------

  function initSummary(row) {
    const labelInput = row.querySelector(".field-label-input");
    const typeSelect = row.querySelector('select[name$="-field_type"]');
    const summaryLabel = row.querySelector(".field-row-summary-label");
    const summaryType = row.querySelector(".field-row-summary-type");

    function update() {
      if (summaryLabel) {
        const v = (labelInput?.value || "").trim();
        summaryLabel.textContent = v || "Campo sin etiqueta";
        summaryLabel.classList.toggle("text-muted", !v);
      }
      if (summaryType && typeSelect) {
        summaryType.textContent = typeSelect.value || "TEXT";
      }
    }

    labelInput?.addEventListener("input", update);
    typeSelect?.addEventListener("change", update);
    update();
  }

  // ---------- delete / move buttons ----------

  function initRowControls(row) {
    const upBtn = row.querySelector(".field-move-up");
    const downBtn = row.querySelector(".field-move-down");
    const delBtn = row.querySelector(".field-row-delete-btn");
    const deleteCheckbox = row.querySelector('input[name$="-DELETE"]');

    upBtn?.addEventListener("click", () => {
      const prev = row.previousElementSibling;
      if (prev && prev.classList.contains("field-row")) {
        rowsContainer.insertBefore(row, prev);
      }
    });

    downBtn?.addEventListener("click", () => {
      const next = row.nextElementSibling;
      if (next && next.classList.contains("field-row")) {
        rowsContainer.insertBefore(next, row);
      }
    });

    delBtn?.addEventListener("click", () => {
      // Existing rows (with a stable field_id): mark DELETE and hide.
      // New rows (no DB id yet): drop them from the DOM and renumber the
      // remaining rows so their prefixes form a contiguous 0..N-1 sequence.
      // Without renumbering, deleting a middle row leaves a hole in the
      // POST data that Django's formset reads as "row missing", silently
      // dropping every subsequent row's data.
      const fieldId = row.querySelector('input[name$="-field_id"]')?.value || "";
      if (fieldId && deleteCheckbox) {
        if (!confirm("¿Eliminar este campo? La acción se aplica al guardar.")) return;
        deleteCheckbox.checked = true;
        row.hidden = true;
      } else {
        row.remove();
        renumberRows();
      }
    });
  }

  // Walk every .field-row and rewrite all formset-prefixed attributes so the
  // i-th row carries idx ``i``. Covers ``name``, ``id``, ``for``,
  // ``aria-controls``, ``data-options-for``, and ``data-form-index``. Each
  // attribute may carry up to three idx-bearing patterns: ``fields-N-…``,
  // ``id_fields-N-…``, ``field-body-fields-N``, and ``ext-fields-N-…``. The
  // function is idempotent and safe to call after every add/delete.
  function renumberRows() {
    if (!rowsContainer || !totalFormsInput) return;
    const rows = rowsContainer.querySelectorAll(".field-row");
    const ATTRS = [
      "name",
      "id",
      "for",
      "aria-controls",
      "data-options-for",
      "data-form-index",
    ];
    rows.forEach((row, newIdx) => {
      const all = [row, ...row.querySelectorAll("*")];
      all.forEach((el) => {
        ATTRS.forEach((attr) => {
          const v = el.getAttribute(attr);
          if (v == null) return;
          const nv = v
            .replace(/(\bfields-)\d+(-)/g, `$1${newIdx}$2`)
            .replace(/(field-body-fields-)\d+/g, `$1${newIdx}`)
            .replace(/(ext-fields-)\d+(-)/g, `$1${newIdx}$2`);
          if (nv !== v) el.setAttribute(attr, nv);
        });
      });
    });
    totalFormsInput.value = String(rows.length);
  }

  // ---------- chip editor ----------

  function initChipCell(cell) {
    if (cell.dataset.chipReady === "1") return;
    cell.dataset.chipReady = "1";

    const hiddenId = cell.dataset.optionsFor;
    const hidden = document.getElementById(hiddenId);
    if (!hidden) return;

    const prefix = cell.dataset.prefix || "";
    const chipBox = cell.querySelector(".chip-input");
    const input = chipBox.querySelector(".chip-input-text");

    function readCsv() {
      return (hidden.value || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }

    function writeCsv(values) {
      hidden.value = values.join(",");
      hidden.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function normalize(raw) {
      let v = (raw || "").trim();
      if (!v) return "";
      v = v.replace(/,/g, "");
      if (prefix && !v.startsWith(prefix)) v = prefix + v;
      if (prefix === ".") v = v.toLowerCase();
      return v;
    }

    function render() {
      chipBox.querySelectorAll(".chip").forEach((c) => c.remove());
      readCsv().forEach((v) => insertChip(v));
    }

    function insertChip(value) {
      const chip = document.createElement("span");
      chip.className = "chip";
      const label = document.createElement("span");
      label.className = "chip-label";
      label.textContent = value;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", `Quitar ${value}`);
      remove.textContent = "×";
      remove.addEventListener("click", (e) => {
        e.preventDefault();
        removeValue(value);
      });
      chip.appendChild(label);
      chip.appendChild(remove);
      chipBox.insertBefore(chip, input);
    }

    function addValue(raw) {
      const v = normalize(raw);
      if (!v) return;
      const current = readCsv();
      if (current.includes(v)) return;
      current.push(v);
      writeCsv(current);
      render();
    }

    function removeValue(target) {
      writeCsv(readCsv().filter((v) => v !== target));
      render();
    }

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        addValue(input.value);
        input.value = "";
      } else if (e.key === "Backspace" && input.value === "") {
        const current = readCsv();
        if (current.length) {
          current.pop();
          writeCsv(current);
          render();
        }
      }
    });

    input.addEventListener("blur", () => {
      if (input.value.trim()) {
        addValue(input.value);
        input.value = "";
      }
    });

    chipBox.addEventListener("click", (e) => {
      if (e.target === chipBox) input.focus();
    });

    render();
  }

  // ---------- field-type / source-driven visibility ----------

  function initTypeToggle(row) {
    const typeSelect = row.querySelector('select[name$="-field_type"]');
    if (!typeSelect) return;
    const sourceSelect = row.querySelector('select[name$="-source"]');
    // Two toggle dimensions:
    //   - data-shows-for="TYPE[,TYPE...]"  → cell visible only when the
    //     field_type matches (SELECT options, FILE extensions/size,
    //     TEXT/TEXTAREA max-chars).
    //   - data-hide-when-auto-fill        → cell hidden when source is a
    //     USER_* variant. Auto-filled fields don't get an alumno-typed
    //     value, so caps/placeholders that decorate the input box have no
    //     UX surface to attach to.
    const typeCells = row.querySelectorAll("[data-shows-for]");
    const autoHideCells = row.querySelectorAll("[data-hide-when-auto-fill]");

    function update() {
      const t = typeSelect.value;
      const isAutoFill =
        !!sourceSelect && sourceSelect.value && sourceSelect.value !== "USER_INPUT";

      typeCells.forEach((cell) => {
        const allowed = (cell.dataset.showsFor || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        const matchesType = allowed.includes(t);
        const hiddenByAutoFill =
          cell.hasAttribute("data-hide-when-auto-fill") && isAutoFill;
        cell.style.display = matchesType && !hiddenByAutoFill ? "" : "none";
      });

      // Cells that have `data-hide-when-auto-fill` but no `data-shows-for`
      // (e.g. placeholder, help text) are toggled purely by source.
      autoHideCells.forEach((cell) => {
        if (cell.hasAttribute("data-shows-for")) return; // handled above
        cell.style.display = isAutoFill ? "none" : "";
      });
    }

    typeSelect.addEventListener("change", update);
    sourceSelect?.addEventListener("change", update);
    update();
  }

  // ---------- predefined-extension multiselect ----------

  function initExtCell(cell) {
    if (cell.dataset.extReady === "1") return;
    cell.dataset.extReady = "1";

    const hidden = document.getElementById(cell.dataset.optionsFor);
    if (!hidden) return;

    const checks = Array.from(cell.querySelectorAll(".ext-check"));
    const groupsHost = cell.querySelector(".ext-multiselect");

    function readCsv() {
      return (hidden.value || "")
        .split(",")
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean);
    }

    function writeCsv(values) {
      hidden.value = values.join(",");
      hidden.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function selected() {
      return checks.filter((c) => c.checked).map((c) => c.dataset.ext);
    }

    function syncFromHidden() {
      const csv = readCsv();
      const known = new Set(checks.map((c) => c.dataset.ext.toLowerCase()));
      checks.forEach((c) => {
        c.checked = csv.includes(c.dataset.ext.toLowerCase());
      });
      const customWrap =
        cell.querySelector(".ext-custom-group") || buildCustomGroup();
      const customHost = customWrap.querySelector(".d-flex");
      customHost.querySelectorAll(".btn-check").forEach((b) => {
        const lbl = customHost.querySelector(`label[for="${b.id}"]`);
        if (lbl) lbl.remove();
        b.remove();
      });
      const unknown = csv.filter((v) => !known.has(v));
      unknown.forEach((ext, i) => {
        const id = `ext-custom-${cell.dataset.optionsFor}-${i}`;
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.className = "btn-check ext-check";
        cb.id = id;
        cb.dataset.ext = ext;
        cb.autocomplete = "off";
        cb.checked = true;
        cb.addEventListener("change", onChange);
        const lbl = document.createElement("label");
        lbl.className = "btn btn-sm btn-outline-secondary";
        lbl.setAttribute("for", id);
        lbl.textContent = ext;
        customHost.appendChild(cb);
        customHost.appendChild(lbl);
        checks.push(cb);
      });
      customWrap.hidden = unknown.length === 0;
    }

    function buildCustomGroup() {
      const wrap = document.createElement("div");
      wrap.className = "ext-group ext-custom-group mt-2";
      wrap.hidden = true;
      const heading = document.createElement("div");
      heading.className = "text-muted text-uppercase small fw-semibold mb-1";
      heading.style.letterSpacing = ".05em";
      heading.textContent = "Personalizadas";
      wrap.appendChild(heading);
      const flex = document.createElement("div");
      flex.className = "d-flex flex-wrap gap-1";
      wrap.appendChild(flex);
      groupsHost.appendChild(wrap);
      return wrap;
    }

    function onChange() {
      writeCsv(selected());
    }

    checks.forEach((c) => c.addEventListener("change", onChange));
    syncFromHidden();
  }

  function initRow(row) {
    initToggle(row);
    initSummary(row);
    initRowControls(row);
    row.querySelectorAll(".chip-options-cell").forEach(initChipCell);
    row.querySelectorAll(".ext-multiselect-cell").forEach(initExtCell);
    initTypeToggle(row);
  }

  // ---------- drag-reorder ----------

  function initSortable() {
    if (!rowsContainer || typeof window.Sortable === "undefined") return;
    window.Sortable.create(rowsContainer, {
      handle: ".field-drag-handle",
      animation: 150,
      ghostClass: "is-ghost",
      chosenClass: "is-dragging",
      forceFallback: false,
    });
  }

  // ---------- order rewrite on submit ----------

  function rewriteOrderInputs() {
    // Soft-deleted rows are still in the DOM (they post DELETE=true) but
    // must not consume an order slot — `_collect_fields` skips them on the
    // server, so giving them an order would leave gaps in the persisted
    // sequence.
    const rows = rowsContainer.querySelectorAll(".field-row");
    let visibleIdx = 0;
    rows.forEach((row) => {
      if (row.hidden) return;
      const orderInput = row.querySelector('input[name$="-order"]');
      if (orderInput) orderInput.value = String(visibleIdx);
      visibleIdx++;
    });
  }

  // ---------- live preview ----------

  const previewBody = document.getElementById("tipo-preview-body");
  const tipoNombreInput = document.getElementById("id_nombre");
  const tipoDescInput = document.getElementById("id_descripcion");

  function readRowState(row) {
    if (row.hidden) return null; // soft-deleted
    const labelInput = row.querySelector(".field-label-input");
    const typeSelect = row.querySelector('select[name$="-field_type"]');
    const requiredCb = row.querySelector('input[name$="-required"]');
    const placeholder = row.querySelector('input[name$="-placeholder"]')?.value || "";
    const helpText = row.querySelector('input[name$="-help_text"]')?.value || "";
    const optionsCsv =
      row.querySelector('input[name$="-options_csv"]')?.value || "";
    const extsCsv =
      row.querySelector('input[name$="-accepted_extensions_csv"]')?.value || "";
    const maxCharsRaw = row.querySelector('input[name$="-max_chars"]')?.value || "";
    const sourceSelect = row.querySelector('select[name$="-source"]');
    return {
      label: (labelInput?.value || "").trim(),
      type: typeSelect?.value || "TEXT",
      required: !!requiredCb?.checked,
      placeholder,
      helpText,
      maxChars: maxCharsRaw ? parseInt(maxCharsRaw, 10) || null : null,
      options: optionsCsv.split(",").map((s) => s.trim()).filter(Boolean),
      extensions: extsCsv
        .split(",")
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean),
      source: sourceSelect?.value || "USER_INPUT",
    };
  }

  function renderField(state, idx) {
    const wrap = document.createElement("div");
    wrap.className = "tipo-preview-field";

    const label = document.createElement("label");
    label.className = "form-label";
    const id = `preview-field-${idx}`;
    label.setAttribute("for", id);
    label.textContent = state.label || "Campo sin etiqueta";
    if (!state.label) label.classList.add("text-muted");
    if (state.required) {
      const star = document.createElement("span");
      star.className = "tipo-preview-required-mark";
      star.setAttribute("aria-hidden", "true");
      star.textContent = "*";
      label.appendChild(star);
    }
    wrap.appendChild(label);

    // Auto-fill fields are not editable inputs at intake time; the live
    // preview shows them as a static pill so the admin can tell at a glance
    // which fields the alumno will *not* see as form controls.
    if (state.source && state.source !== "USER_INPUT") {
      const pill = document.createElement("span");
      pill.className = "badge text-bg-light border";
      const variant = state.source.replace(/^USER_/, "").toLowerCase();
      pill.textContent = `Auto · ${variant}`;
      wrap.appendChild(pill);
      return wrap;
    }

    let control;
    switch (state.type) {
      case "TEXTAREA":
        control = document.createElement("textarea");
        control.className = "form-control";
        control.rows = 3;
        if (state.maxChars) control.maxLength = state.maxChars;
        break;
      case "NUMBER":
        control = document.createElement("input");
        control.type = "number";
        control.className = "form-control";
        break;
      case "DATE":
        control = document.createElement("input");
        control.type = "date";
        control.className = "form-control";
        break;
      case "SELECT": {
        control = document.createElement("select");
        control.className = "form-select";
        const placeholderOpt = document.createElement("option");
        placeholderOpt.textContent = "Selecciona una opción";
        placeholderOpt.disabled = true;
        placeholderOpt.selected = true;
        control.appendChild(placeholderOpt);
        state.options.forEach((opt) => {
          const o = document.createElement("option");
          o.textContent = opt;
          control.appendChild(o);
        });
        break;
      }
      case "FILE":
        control = document.createElement("input");
        control.type = "file";
        control.className = "form-control";
        if (state.extensions.length) {
          control.accept = state.extensions.join(",");
        }
        break;
      case "TEXT":
      default:
        control = document.createElement("input");
        control.type = "text";
        control.className = "form-control";
        if (state.maxChars) control.maxLength = state.maxChars;
    }
    control.id = id;
    // All preview controls are interactive — the admin can try the form.
    // They have no `name` attribute, so nothing in here is submitted with
    // the editor form.
    if (state.placeholder && "placeholder" in control) {
      control.placeholder = state.placeholder;
    }
    wrap.appendChild(control);

    if (state.helpText) {
      const help = document.createElement("div");
      help.className = "form-text";
      help.textContent = state.helpText;
      wrap.appendChild(help);
    }
    return wrap;
  }

  function renderPreview() {
    if (!previewBody) return;
    previewBody.innerHTML = "";

    const heading = document.createElement("div");
    heading.className = "mb-3";
    const h = document.createElement("div");
    h.className = "fw-semibold";
    const nombre = (tipoNombreInput?.value || "").trim();
    h.textContent = nombre || "Nuevo tipo de solicitud";
    if (!nombre) h.classList.add("text-muted");
    heading.appendChild(h);
    const desc = (tipoDescInput?.value || "").trim();
    if (desc) {
      const d = document.createElement("div");
      d.className = "small text-muted";
      d.textContent = desc;
      heading.appendChild(d);
    }
    previewBody.appendChild(heading);

    const rows = Array.from(rowsContainer.querySelectorAll(".field-row"));
    const states = rows.map(readRowState).filter(Boolean);
    if (!states.length) {
      const empty = document.createElement("p");
      empty.className = "tipo-preview-empty mb-0";
      empty.textContent = "Agrega un campo para ver la vista previa.";
      previewBody.appendChild(empty);
      return;
    }
    states.forEach((s, i) => previewBody.appendChild(renderField(s, i)));
  }

  function initLivePreview() {
    if (!previewBody) return;
    // One delegated listener catches every row edit (label, type, required,
    // placeholder, help, options chips, extension toggles, hidden CSV writes).
    rowsContainer.addEventListener("input", renderPreview);
    rowsContainer.addEventListener("change", renderPreview);
    // Reorder via Sortable / up-down / add / delete also affects the preview.
    // ``subtree: true`` is forward-looking — today the rows live one level
    // deep, but a future nested formset (e.g. conditional sub-fields) would
    // silently miss the preview without it.
    new MutationObserver(renderPreview).observe(rowsContainer, {
      childList: true,
      subtree: true,
    });
    tipoNombreInput?.addEventListener("input", renderPreview);
    tipoDescInput?.addEventListener("input", renderPreview);
    renderPreview();
  }

  // Bootstrap any rows already present on initial load.
  document.querySelectorAll("#field-rows > .field-row").forEach(initRow);
  initSortable();
  initLivePreview();

  const form = rowsContainer?.closest("form");
  form?.addEventListener("submit", rewriteOrderInputs);
})();
