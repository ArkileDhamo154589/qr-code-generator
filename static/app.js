document.addEventListener("DOMContentLoaded", () => {
  const historyTable = document.getElementById("history-table");
  const deleteBtn = document.getElementById("delete-btn");
  const clearBtn = document.getElementById("clear-history");
  const result = document.getElementById("result");
  const urlInput = document.getElementById("url-input");

  let history = [];

  function renderHistory() {
    historyTable.innerHTML = "";
    history.forEach(item => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${item.action}</td>
        <td class="url">${item.url || "-"}</td>
        <td>${item.time}</td>
      `;
      historyTable.appendChild(tr);
    });
  }

  function addHistory(action, url = "") {
    history.unshift({
      action,
      url,
      time: new Date().toLocaleTimeString()
    });
    renderHistory();
  }

  // If QR exists (POST response)
  if (result && urlInput && urlInput.value) {
    addHistory("Generated", urlInput.value);
  }

  // Delete QR
  if (deleteBtn) {
    deleteBtn.addEventListener("click", () => {
      result.classList.add("fade-out");

      setTimeout(() => {
        result.remove();
      }, 300);

      addHistory("Deleted");
      urlInput.value = "";
    });
  }

  // Clear history manually
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      history = [];
      renderHistory();
    });
  }
});
