/**
 * Alpine component backing the plantilla editor (HTML/CSS editor with
 * click-to-insert snippets, live HTML preview, "Ver PDF real" button, and
 * in-place asset upload modal).
 *
 * No bundler; loads as a plain <script> tag. Registers itself in alpine:init.
 */
document.addEventListener("alpine:init", () => {
  Alpine.data("plantillaEditor", (config) => ({
    // --- state ---
    html: "",
    css: "",
    activeTab: "variables",
    plantillaId: config.plantillaId || "",
    tipoId: config.tipoId || "",
    assets: { global: [], plantilla: [] },
    campos: [],
    previewLoading: false,
    previewError: null,
    uploadModalOpen: false,
    uploadBusy: false,
    uploadError: null,
    uploadForm: {
      nombre: "",
      scope: config.plantillaId ? "plantilla" : "global",
      insertAfter: true,
    },

    // --- lifecycle ---
    init() {
      const ta = this.$refs.htmlTextarea;
      this.html = ta ? ta.value : "";
      const cssEl = document.querySelector("[name=css]");
      this.css = cssEl ? cssEl.value : "";
      this.loadAssets();
      if (this.tipoId) this.loadCampos();
      // First render after a tick so refs are bound.
      this.$nextTick(() => this.refreshPreview());
    },

    // --- editor actions ---
    insert(snippet) {
      const ta = this.$refs.htmlTextarea;
      if (!ta) return;
      const focused = document.activeElement === ta;
      const start = focused ? ta.selectionStart : ta.value.length;
      const end = focused ? ta.selectionEnd : ta.value.length;
      const before = ta.value.slice(0, start);
      const after = ta.value.slice(end);
      const sep = !focused && before && !before.endsWith("\n") ? "\n" : "";
      const insertText = sep + snippet;
      ta.value = before + insertText + after;
      ta.focus();
      const cursor = (before + insertText).length;
      ta.setSelectionRange(cursor, cursor);
      this.html = ta.value;
      this.refreshPreview();
    },

    // --- preview ---
    async refreshPreview() {
      if (this.previewLoading) return;
      this.previewLoading = true;
      this.previewError = null;
      try {
        const resp = await fetch(config.previewUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": config.csrfToken,
          },
          body: JSON.stringify({
            html: this.html,
            css: this.css,
            plantilla_id: this.plantillaId || null,
          }),
        });
        const text = await resp.text();
        if (this.$refs.previewFrame) {
          this.$refs.previewFrame.srcdoc = text;
        }
      } catch (err) {
        this.previewError = String(err);
      } finally {
        this.previewLoading = false;
      }
    },

    async openPdfPreview() {
      // Persist the current draft into the session, then open the PDF endpoint
      // in a new tab.
      try {
        await fetch(config.previewUrl + "?persist=1", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": config.csrfToken,
          },
          body: JSON.stringify({
            html: this.html,
            css: this.css,
            plantilla_id: this.plantillaId || null,
          }),
        });
      } catch (err) {
        // Even if persist fails, attempt to open — endpoint will 400 cleanly.
      }
      window.open(config.previewPdfUrl, "_blank", "noopener");
    },

    // --- assets ---
    async loadAssets() {
      const qs = this.plantillaId ? `?plantilla_id=${this.plantillaId}` : "";
      try {
        const r = await fetch(`${config.assetsJsonUrl}${qs}`, {
          headers: { Accept: "application/json" },
        });
        if (!r.ok) return;
        const data = await r.json();
        this.assets.global = data.global || [];
        this.assets.plantilla = data.plantilla || [];
      } catch (err) {
        // Non-fatal — editor still usable.
      }
    },

    async loadCampos() {
      try {
        const r = await fetch(`/solicitudes/admin/tipos/${this.tipoId}/fields.json`, {
          headers: { Accept: "application/json" },
        });
        if (!r.ok) return;
        const data = await r.json();
        this.campos = data.fields || [];
      } catch (err) {
        // Non-fatal.
      }
    },

    async submitUpload(event) {
      this.uploadBusy = true;
      this.uploadError = null;
      const formData = new FormData();
      formData.append("nombre", this.uploadForm.nombre);
      const fileInput = this.$refs.uploadFile;
      if (!fileInput || !fileInput.files[0]) {
        this.uploadError = "Selecciona una imagen.";
        this.uploadBusy = false;
        return;
      }
      formData.append("imagen", fileInput.files[0]);

      const scope = this.plantillaId ? this.uploadForm.scope : "global";
      const url = scope === "plantilla" && this.plantillaId
        ? config.uploadPlantillaUrlTpl.replace("__ID__", this.plantillaId)
        : config.uploadGlobalUrl;

      try {
        const r = await fetch(url, {
          method: "POST",
          headers: {
            Accept: "application/json",
            "X-CSRFToken": config.csrfToken,
            "X-Requested-With": "XMLHttpRequest",
          },
          body: formData,
        });
        if (!r.ok) {
          const errPayload = await r.json().catch(() => ({}));
          const msg = errPayload.error || "No se pudo subir la imagen.";
          const fieldErrs = errPayload.field_errors || {};
          const first = Object.values(fieldErrs)[0];
          this.uploadError = Array.isArray(first) ? first[0] : msg;
          return;
        }
        const asset = await r.json();
        // Refresh both buckets to keep order consistent with the server.
        await this.loadAssets();
        if (this.uploadForm.insertAfter && asset.snippet) {
          this.insert(asset.snippet);
        }
        this.uploadModalOpen = false;
        this.uploadForm.nombre = "";
        if (fileInput) fileInput.value = "";
      } catch (err) {
        this.uploadError = String(err);
      } finally {
        this.uploadBusy = false;
      }
    },
  }));
});
