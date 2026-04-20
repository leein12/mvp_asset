/**
 * 각 .table-scroll 안의 .grid-table 헤더 오른쪽 가장자리를 드래그해 열 너비 조절.
 */
(function () {
    const MIN_W = 36;
    const MAX_W = 960;

    function setColumnWidth(table, colIndex, widthPx) {
        const w = Math.max(MIN_W, Math.min(MAX_W, widthPx));
        const sel = `thead tr:first-child > th:nth-child(${colIndex + 1}), tbody tr > td:nth-child(${colIndex + 1})`;
        table.querySelectorAll(sel).forEach((cell) => {
            cell.style.width = `${w}px`;
            cell.style.minWidth = `${w}px`;
            cell.style.maxWidth = `${w}px`;
        });
    }

    function initTable(table) {
        const thead = table.querySelector("thead");
        if (!thead) return;
        const headerRow = thead.querySelector("tr:first-child");
        if (!headerRow) return;
        const ths = [...headerRow.querySelectorAll(":scope > th")];
        if (!ths.length) return;

        ths.forEach((th, colIndex) => {
            if (th.querySelector(":scope > .col-resize-grip")) return;
            const grip = document.createElement("span");
            grip.className = "col-resize-grip";
            grip.title = "열 너비 조절";
            grip.setAttribute("aria-hidden", "true");
            th.appendChild(grip);

            grip.addEventListener("mousedown", (downEv) => {
                downEv.preventDefault();
                downEv.stopPropagation();
                const sample = table.querySelector(`tbody tr:first-child > td:nth-child(${colIndex + 1})`) || th;
                const startX = downEv.pageX;
                const startW = sample.getBoundingClientRect().width;

                const onMove = (moveEv) => {
                    const dx = moveEv.pageX - startX;
                    setColumnWidth(table, colIndex, startW + dx);
                };

                const onUp = () => {
                    document.removeEventListener("mousemove", onMove);
                    document.removeEventListener("mouseup", onUp);
                    document.body.style.removeProperty("cursor");
                    document.body.style.removeProperty("user-select");
                };

                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
                document.addEventListener("mousemove", onMove);
                document.addEventListener("mouseup", onUp);
            });
        });
    }

    function initAll() {
        document.querySelectorAll(".table-scroll table.grid-table").forEach(initTable);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAll);
    } else {
        initAll();
    }
})();
