document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("qr-form");
  const urlInput = document.getElementById("url-input");
  const titleInput = document.getElementById("title-input");
  const colorInput = document.getElementById("color-input");
  const colorValue = document.getElementById("color-value");
  const transparentInput = document.getElementById("transparent-input");
  const generateBtn = document.getElementById("generate-btn");
  const formError = document.getElementById("form-error");

  const stage = document.getElementById("preview-stage");
  const qrFrame = document.getElementById("qr-frame");
  const qrImage = document.getElementById("qr-image");
  const exportBar = document.getElementById("export-bar");

  const modal = document.getElementById("card-modal");
  const cardQrImage = document.getElementById("card-qr-image");
  const cardTitle = document.getElementById("card-title");
  const cardUrl = document.getElementById("card-url");

  // Current generated QR state
  const state = { dataUrl: "", url: "", title: "" };

  // ---- Helpers ----------------------------------------------------------
  function showError(message) {
    formError.textContent = message;
    formError.hidden = !message;
  }

  function safeName(fallback) {
    try {
      const host = new URL(state.url).hostname.replace(/^www\./, "");
      return (host || fallback).replace(/[^a-z0-9.-]/gi, "_");
    } catch (e) {
      return fallback;
    }
  }

  function download(href, filename) {
    const a = document.createElement("a");
    a.href = href;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  // Flatten a (possibly transparent) PNG data URL onto a white background
  // so PDFs and cards always have a solid, scannable QR.
  function flattenToWhite(dataUrl, size = 600) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, size, size);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(img, 0, 0, size, size);
        resolve(canvas.toDataURL("image/png"));
      };
      img.src = dataUrl;
    });
  }

  // ---- Color input sync -------------------------------------------------
  if (colorInput) {
    colorInput.addEventListener("input", () => {
      colorValue.textContent = colorInput.value;
    });
  }

  // ---- Generate ---------------------------------------------------------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError("");

    const url = urlInput.value.trim();
    if (!url) {
      showError("Please enter a link or text.");
      urlInput.focus();
      return;
    }

    generateBtn.disabled = true;
    generateBtn.querySelector("span").textContent = "Generating…";

    try {
      const res = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          color: colorInput.value,
          transparent: transparentInput.checked,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        showError(data.error || "Something went wrong. Try again.");
        return;
      }

      state.dataUrl = "data:image/png;base64," + data.qr_image;
      state.url = url;
      state.title = titleInput.value.trim();

      qrImage.src = state.dataUrl;
      qrFrame.hidden = false;
      stage.dataset.empty = "false";
      exportBar.hidden = false;
      exportBar.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
      showError("Could not reach the generator. Is the server running?");
    } finally {
      generateBtn.disabled = false;
      generateBtn.querySelector("span").textContent = "Generate QR code";
    }
  });

  // ---- Export: Image ----------------------------------------------------
  document.getElementById("export-png").addEventListener("click", () => {
    if (!state.dataUrl) return;
    download(state.dataUrl, "qr-" + safeName("code") + ".png");
  });

  // ---- Export: PDF (A4, centered) --------------------------------------
  document.getElementById("export-pdf").addEventListener("click", async () => {
    if (!state.dataUrl) return;
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    const pageW = doc.internal.pageSize.getWidth();

    const flat = await flattenToWhite(state.dataUrl, 800);
    const qrSize = 110;
    const x = (pageW - qrSize) / 2;
    const y = 55;

    if (state.title) {
      doc.setFont("helvetica", "bold");
      doc.setFontSize(20);
      doc.text(state.title, pageW / 2, 40, { align: "center" });
    }

    doc.addImage(flat, "PNG", x, y, qrSize, qrSize);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(12);
    doc.setTextColor(90);
    const link = doc.splitTextToSize(state.url, pageW - 40);
    doc.text(link, pageW / 2, y + qrSize + 14, { align: "center" });

    doc.save("qr-" + safeName("code") + ".pdf");
  });

  // ---- Export: Card -----------------------------------------------------
  function openModal() {
    modal.hidden = false;
    document.body.style.overflow = "hidden";
  }
  function closeModal() {
    modal.hidden = true;
    document.body.style.overflow = "";
  }

  document.getElementById("export-card").addEventListener("click", () => {
    if (!state.dataUrl) return;
    cardQrImage.src = state.dataUrl;
    cardTitle.textContent = state.title || "Scan me";
    cardUrl.textContent = state.url;
    openModal();
  });

  modal.querySelectorAll("[data-close-modal]").forEach((el) =>
    el.addEventListener("click", closeModal)
  );
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hidden) closeModal();
  });

  document.getElementById("card-print").addEventListener("click", () => {
    window.print();
  });

  // Card as a business-card sized PDF (85.6 x 54 mm, landscape)
  document.getElementById("card-download").addEventListener("click", async () => {
    if (!state.dataUrl) return;
    const { jsPDF } = window.jspdf;
    const cardW = 85.6;
    const cardH = 54;
    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: [cardW, cardH] });

    // Card background + subtle border
    doc.setFillColor(255, 255, 255);
    doc.rect(0, 0, cardW, cardH, "F");
    doc.setDrawColor(225);
    doc.setLineWidth(0.3);
    doc.roundedRect(1, 1, cardW - 2, cardH - 2, 3, 3, "S");

    const flat = await flattenToWhite(state.dataUrl, 600);
    const qrSize = 38;
    const qrX = 6;
    const qrY = (cardH - qrSize) / 2;
    doc.addImage(flat, "PNG", qrX, qrY, qrSize, qrSize);

    const textX = qrX + qrSize + 6;
    const textW = cardW - textX - 6;

    doc.setTextColor(17, 19, 26);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    const title = doc.splitTextToSize(state.title || "Scan me", textW);
    doc.text(title, textX, 24);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(110);
    const link = doc.splitTextToSize(state.url, textW);
    doc.text(link, textX, 24 + title.length * 6 + 2);

    doc.save("qr-card-" + safeName("code") + ".pdf");
  });

  // ---- 3D tilt (converter card + info cards) ----------------------------
  const reduceMotion =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const canHover = window.matchMedia && window.matchMedia("(hover: hover)").matches;

  function attachTilt(el, max, lift) {
    let raf = 0;
    el.addEventListener("mousemove", (e) => {
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        el.style.transform =
          `perspective(1000px) rotateY(${px * max}deg) rotateX(${-py * max}deg) translateZ(0)` +
          (lift ? ` translateY(-4px)` : "");
      });
    });
    el.addEventListener("mouseleave", () => {
      if (raf) cancelAnimationFrame(raf);
      el.style.transform = "";
    });
  }

  if (canHover && !reduceMotion) {
    document.querySelectorAll(".convert-card").forEach((el) => attachTilt(el, 5, false));
    document.querySelectorAll("[data-tilt]").forEach((el) => attachTilt(el, 8, true));
  }

  // ---- Tabs --------------------------------------------------------------
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => {
        const on = t === tab;
        t.classList.toggle("is-active", on);
        t.setAttribute("aria-selected", on ? "true" : "false");
        document.getElementById(t.dataset.panel).hidden = !on;
      });
    });
  });

  // ---- Image converter ---------------------------------------------------
  const convForm = document.getElementById("conv-form");
  if (convForm) {
    const dropzone = document.getElementById("conv-dropzone");
    const fileInput = document.getElementById("conv-input");
    const pickBtn = document.getElementById("conv-pick");
    const fileList = document.getElementById("conv-filelist");
    const convBtn = document.getElementById("conv-convert-btn");
    const convError = document.getElementById("conv-error");
    const targetGroup = document.getElementById("target-group");
    const flowTarget = document.getElementById("flow-target");
    const resultsWrap = document.getElementById("conv-results");
    const resultsList = document.getElementById("conv-results-list");
    const resultsTitle = document.getElementById("conv-results-title");
    const downloadAll = document.getElementById("conv-download-all");

    let selected = [];
    let target = "png";
    let lastResults = [];

    function fmtSize(n) {
      if (n < 1024) return n + " B";
      if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
      return (n / (1024 * 1024)).toFixed(2) + " MB";
    }

    function convError_(msg) {
      convError.textContent = msg || "";
      convError.hidden = !msg;
    }

    function renderFiles() {
      fileList.innerHTML = "";
      selected.forEach((file, i) => {
        const li = document.createElement("li");
        const name = document.createElement("span");
        name.className = "fl-name";
        name.textContent = file.name;
        const size = document.createElement("span");
        size.className = "fl-size";
        size.textContent = fmtSize(file.size);
        const rm = document.createElement("button");
        rm.type = "button";
        rm.className = "fl-remove";
        rm.setAttribute("aria-label", "Remove " + file.name);
        rm.innerHTML =
          '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"></path><path d="m6 6 12 12"></path></svg>';
        rm.addEventListener("click", () => {
          selected.splice(i, 1);
          renderFiles();
        });
        li.append(name, size, rm);
        fileList.appendChild(li);
      });
      convBtn.disabled = selected.length === 0;
    }

    function addFiles(files) {
      for (const f of files) {
        if (f.type.startsWith("image/") || /\.(png|jpe?g|webp|avif)$/i.test(f.name)) {
          selected.push(f);
        }
      }
      renderFiles();
    }

    pickBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
      addFiles(fileInput.files);
      fileInput.value = "";
    });

    ["dragenter", "dragover"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.add("is-drag");
      })
    );
    ["dragleave", "drop"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.remove("is-drag");
      })
    );
    dropzone.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files) addFiles(e.dataTransfer.files);
    });

    targetGroup.addEventListener("click", (e) => {
      const btn = e.target.closest(".target-btn");
      if (!btn) return;
      target = btn.dataset.target;
      targetGroup.querySelectorAll(".target-btn").forEach((b) => {
        const on = b === btn;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      flowTarget.textContent = target.toUpperCase();
    });

    convForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      convError_("");
      if (selected.length === 0) return;

      const fd = new FormData();
      fd.append("target", target);
      selected.forEach((f) => fd.append("files", f, f.name));

      convBtn.disabled = true;
      convBtn.querySelector("span").textContent = "Converting…";

      try {
        const res = await fetch("/convert", { method: "POST", body: fd });
        const data = await res.json();
        if (!res.ok) {
          convError_(data.error || "Conversion failed.");
          return;
        }
        lastResults = data.results || [];
        renderResults(lastResults, data.errors || []);
      } catch (err) {
        convError_("Could not reach the converter. Is the server running?");
      } finally {
        convBtn.disabled = selected.length === 0;
        convBtn.querySelector("span").textContent = "Convert";
      }
    });

    function renderResults(results, errors) {
      resultsList.innerHTML = "";
      results.forEach((r) => {
        const item = document.createElement("div");
        item.className = "result-item";

        const img = document.createElement("img");
        img.className = "result-thumb";
        img.src = r.dataUrl;
        img.alt = r.name;

        const name = document.createElement("p");
        name.className = "result-name";
        name.textContent = r.name;

        const size = document.createElement("p");
        size.className = "result-size";
        size.textContent = fmtSize(r.bytes);

        const dl = document.createElement("a");
        dl.className = "result-dl";
        dl.href = r.dataUrl;
        dl.download = r.name;
        dl.innerHTML =
          '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><path d="M7 10l5 5 5-5"></path><path d="M12 15V3"></path></svg><span>Download</span>';

        item.append(img, name, size, dl);
        resultsList.appendChild(item);
      });

      resultsTitle.textContent =
        results.length + " file" + (results.length === 1 ? "" : "s") + " converted to " + target.toUpperCase();
      resultsWrap.hidden = results.length === 0;

      if (errors && errors.length) {
        convError_(errors.length + " file(s) could not be converted.");
      }
    }

    downloadAll.addEventListener("click", () => {
      lastResults.forEach((r, i) => {
        setTimeout(() => download(r.dataUrl, r.name), i * 250);
      });
    });
  }
});
