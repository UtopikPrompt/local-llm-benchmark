/* dashboard.js — the dashboard view provider.
   Mirrors the reference dashboard.ts provider: it owns all view logic
   (config form, run button, KPI cards, results table) and talks to the
   FastAPI backend. Kept separate from charts.js and designSystem.css so the
   dashboard has no bundled design tokens or chart code of its own. */

(function () {
    "use strict";

    function $(id) {
        return document.getElementById(id);
    }

    /**
     * Load the server defaults for the configuration form.
     */
    async function loadConfig() {
        const response = await fetch("/defaults");
        if (!response.ok) return;
        const defaults = await response.json();
        document.getElementById("engine-select").value = defaults.engine || "";

        const base = defaults.engine_base_url || "";
        const model = defaults.engine_model || "";
        document.getElementById("engine-base-url").value = base;
        document.getElementById("engine-model").value = model;
        toggleManualFields();
    }

    /**
     * Show or hide the manual base-url/model fields depending on whether an
     * engine preset is selected.
     */
    function toggleManualFields() {
        const engine = $("engine-select").value;
        const show = engine === "";
        const group = document.querySelector(".manual-group");
        if (group) group.style.display = show ? "" : "none";
    }

    /**
     * Run the benchmark and then render the results.
     */
    async function runBenchmark() {
        const payload = {
            engine: $("engine-select").value,
            base_url: $("engine-base-url").value,
            model: $("engine-model").value,
            max_concurrent: parseInt($("max-concurrent").value, 10) || undefined,
            timeout: parseInt($("timeout").value, 10) || undefined,
            trials: parseInt($("trials").value, 10) || undefined,
            tasks: $("tasks").value,
        };

        const button = $("run-button");
        button.disabled = true;
        button.textContent = "Running...";

        try {
            const response = await fetch("/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!response.ok) throw new Error("Benchmark failed");

            const rows = await response.json();
            renderResults(rows);
        } catch (error) {
            alert("Benchmark failed: " + error.message);
        } finally {
            button.disabled = false;
            button.textContent = "Run benchmark";
        }
    }

    /**
     * Render the KPI cards from benchmark rows.
     */
    function renderKpis(rows) {
        const avgTtft = rows.length
            ? (rows.reduce((s, r) => s + r.ttft_s, 0) / rows.length).toFixed(2)
            : "—";
        const avgTps = rows.length
            ? (rows.reduce((s, r) => s + r.tok_per_s, 0) / rows.length).toFixed(0)
            : "—";
        const passRate = rows.length
            ? Math.round((rows.filter((r) => r.quality_passed).length / rows.length) * 100)
            : 0;

        const setCard = (valueId, labelId, value) => {
            $("" + valueId).textContent = value;
            const label = $("" + labelId);
            if (label) label.textContent = label.textContent.replace(/:\s*[^:]+$/, "");
        };

        setCard("card-ttft-value", "card-ttft-label", avgTtft + " s");
        setCard("card-tps-value", "card-tps-label", avgTps + " tok/s");
        setCard("card-pass-value", "card-pass-label", passRate + "%");
    }

    /**
     * Render the results table from benchmark rows.
     */
    function renderResults(rows) {
        renderKpis(rows);

        const tbody = document.getElementById("results-table-body");
        tbody.innerHTML = "";

        rows.forEach((row) => {
            const tr = document.createElement("tr");
            tr.innerHTML =
                "<td>" + escapeHtml(row.engine) + "</td>" +
                "<td>" + escapeHtml(row.model) + "</td>" +
                "<td class='data-text'>" + escapeHtml(row.task_id) + "</td>" +
                "<td>" + escapeHtml(row.category) + "</td>" +
                "<td class='data-text'>" + formatNumber(row.tok_per_s) + "</td>" +
                "<td class='data-text'>" + formatNumber(row.ttft_s) + "</td>" +
                "<td>" + (row.quality_passed ? "✓" : "✗") + "</td>";
            tbody.appendChild(tr);
        });

        renderThroughput("throughput-canvas", {
            engines: [...new Set(rows.map((r) => r.engine))],
            values: [...new Set(rows.map((r) => r.engine))].map((engine) =>
                rows.filter((r) => r.engine === engine).reduce((s, r) => s + r.tok_per_s, 0) /
                    rows.filter((r) => r.engine === engine).length
            ),
        });

        renderPassRate("passrate-canvas", {
            categories: [...new Set(rows.map((r) => r.category))],
            values: [...new Set(rows.map((r) => r.category))].map((category) => {
                const group = rows.filter((r) => r.category === category);
                return group.length
                    ? group.filter((r) => r.quality_passed).length / group.length
                    : 0;
            }),
        });
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function formatNumber(value) {
        return Number(value).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 4,
        });
    }

    function bindEvents() {
        document.getElementById("engine-select").addEventListener("change", toggleManualFields);
        document.getElementById("run-button").addEventListener("click", runBenchmark);
    }

    document.addEventListener("DOMContentLoaded", function () {
        bindEvents();
        loadConfig();
    });
})();
