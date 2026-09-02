/* Progressive enhancement only: every page works without this file.
   No build step, no dependencies. */
(function () {
  "use strict";

  /* ---------------------------------------------------- live filter */

  document.querySelectorAll("input[data-filter]").forEach(function (input) {
    var body = document.querySelector(input.dataset.filter);
    if (!body) return;

    var rows = Array.prototype.slice.call(body.rows);
    var panel = body.closest(".panel");
    var count = panel && panel.querySelector("[data-filter-count]");
    var label = count && count.textContent.replace(/^\S+\s*/, "");

    function apply() {
      var q = input.value.trim().toLowerCase();
      var shown = 0;
      rows.forEach(function (tr) {
        if (tr.querySelector(".empty")) return;
        var hay = (tr.dataset.filterText || tr.textContent).toLowerCase();
        var hit = !q || hay.indexOf(q) !== -1;
        tr.classList.toggle("hidden", !hit);
        if (hit) shown++;
      });
      if (count) count.textContent = shown + " " + label;
    }

    input.addEventListener("input", apply);
    if (input.value) apply();
  });

  /* ------------------------------------------------- sortable table */

  function cellValue(row, index, kind) {
    var cell = row.cells[index];
    if (!cell) return kind === "num" ? -Infinity : "";
    var text = cell.textContent.trim();
    if (kind !== "num") return text.toLowerCase();
    var match = text.replace(/,/g, "").match(/-?\d+(\.\d+)?/);
    return match ? parseFloat(match[0]) : -Infinity;
  }

  document.querySelectorAll("table[data-sortable]").forEach(function (table) {
    var head = table.tHead && table.tHead.rows[0];
    var body = table.tBodies[0];
    if (!head || !body) return;

    Array.prototype.forEach.call(head.cells, function (th, index) {
      if (!th.classList.contains("sortable")) return;
      th.tabIndex = 0;
      th.setAttribute("role", "button");

      function sort() {
        var kind = th.dataset.sort || "text";
        var desc = !th.classList.contains("desc");

        Array.prototype.forEach.call(head.cells, function (other) {
          if (other !== th) other.classList.remove("asc", "desc");
        });
        th.classList.toggle("desc", desc);
        th.classList.toggle("asc", !desc);

        var rows = Array.prototype.slice.call(body.rows).filter(function (tr) {
          return !tr.querySelector(".empty");
        });
        rows.map(function (tr, i) {
          return { tr: tr, key: cellValue(tr, index, kind), i: i };
        }).sort(function (a, b) {
          if (a.key < b.key) return desc ? 1 : -1;
          if (a.key > b.key) return desc ? -1 : 1;
          return a.i - b.i;                       /* stable */
        }).forEach(function (item) {
          body.appendChild(item.tr);
        });
      }

      th.addEventListener("click", sort);
      th.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          sort();
        }
      });
    });
  });

  /* ------------------------------------------------------- shortcut */

  document.addEventListener("keydown", function (event) {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    var tag = document.activeElement && document.activeElement.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") return;
    var input = document.querySelector("input[data-filter]");
    if (input) {
      event.preventDefault();
      input.focus();
      input.select();
    }
  });
})();
