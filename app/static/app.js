// Minimal vanilla-JS helper for repeating table rows (trial balance, PPE, loans, etc.)
// and simple client-side number validation feedback.

function addRow(tableId, templateId) {
  const table = document.getElementById(tableId);
  const template = document.getElementById(templateId);
  const tbody = table.tBodies[0];
  const clone = template.content.cloneNode(true);
  tbody.appendChild(clone);
  reindexRows(tableId);
}

function removeRow(button) {
  const row = button.closest("tr");
  const tableId = row.closest("table").id;
  row.remove();
  reindexRows(tableId);
}

function reindexRows(tableId) {
  const table = document.getElementById(tableId);
  const checkboxes = table.querySelectorAll('input[type="checkbox"][data-row-index]');
  checkboxes.forEach((cb, i) => {
    cb.value = String(i);
  });
}

document.addEventListener("input", function (e) {
  if (e.target.matches('input[type="number"], input.numeric')) {
    const val = e.target.value;
    if (val !== "" && isNaN(Number(val))) {
      e.target.style.borderColor = "#b02a2a";
    } else {
      e.target.style.borderColor = "";
    }
  }
});

// Tab switching for the financial-year detail page.
document.addEventListener("DOMContentLoaded", function () {
  const tabs = document.querySelectorAll(".tabs a[data-tab]");
  const panels = document.querySelectorAll(".tab-panel[data-panel]");
  if (!tabs.length) return;

  function activate(name) {
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    panels.forEach((p) => (p.style.display = p.dataset.panel === name ? "block" : "none"));
  }

  tabs.forEach((t) => {
    t.addEventListener("click", function (e) {
      e.preventDefault();
      window.location.hash = t.dataset.tab;
      activate(t.dataset.tab);
    });
  });

  const initial = window.location.hash ? window.location.hash.slice(1) : tabs[0].dataset.tab;
  activate(initial);
});
