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

  // ---- 3D tilt on the converter card ------------------------------------
  const card = document.getElementById("convert-card");
  const reduceMotion =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const canHover = window.matchMedia && window.matchMedia("(hover: hover)").matches;

  if (card && canHover && !reduceMotion) {
    const MAX = 6; // degrees
    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform =
        `rotateY(${px * MAX}deg) rotateX(${-py * MAX}deg) translateZ(0)`;
    });
    card.addEventListener("mouseleave", () => {
      card.style.transform = "";
    });
  }
});
