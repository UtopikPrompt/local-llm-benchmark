/* charts.js — Chart.js rendering provider for the dashboard.
   Mirrors the reference charts.ts provider: it owns the chart instances and
   the shared color palette, and writes into the <canvas> elements the
   dashboard markup defines.

   The design tokens come from designSystem.css (:root), so chart colors are
   consistent with the rest of the UI without duplicating the palette. */

const CHART_COLORS = [
    "#007AFF",
    "#39FF14",
    "#FF4D4D",
    "#f093fb",
    "#00d2ff",
    "#ffd700",
    "#4ecdc4",
    "#ff8c94",
];

const CHART_FONT = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";

function palette() {
    return CHART_COLORS;
}

const CHART_STYLE = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500 },
    plugins: {
        legend: {
            labels: {
                color: "var(--text-primary)",
                font: { family: CHART_FONT, size: 12 },
                usePointStyle: true,
                padding: 16,
            },
        },
        tooltip: {
            backgroundColor: "rgba(15, 18, 24, 0.95)",
            titleColor: "var(--text-primary)",
            bodyColor: "var(--text-secondary)",
            borderColor: "var(--border-strong)",
            borderWidth: 1,
            cornerRadius: 8,
            font: { family: CHART_FONT, size: 12 },
        },
    },
};

/**
 * Render a bar chart for throughput (tokens/second) grouped by engine.
 */
function renderThroughput(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx.chart) ctx.chart.destroy();

    const labels = data.engines;
    const values = data.values;

    const chart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Tokens/second",
                    data: values,
                    backgroundColor: CHART_COLORS.map((c) => c + "cc"),
                    borderColor: CHART_COLORS,
                    borderWidth: 1,
                    borderRadius: 6,
                },
            ],
        },
        options: {
            ...CHART_STYLE,
            scales: {
                x: {
                    stacked: false,
                    grid: { color: "rgba(148,163,184,0.10)" },
                    ticks: { color: "var(--text-secondary)", font: { family: CHART_FONT, size: 11 } },
                },
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(148,163,184,0.10)" },
                    ticks: {
                        color: "var(--text-secondary)",
                        font: { family: CHART_FONT, size: 11 },
                        callback: (v) => v.toLocaleString() + "/s",
                    },
                },
            },
        },
    });

    ctx.chart = chart;
    ctx.chart.data = { labels, values };
}

/**
 * Render a bar chart for pass rate by task category.
 */
function renderPassRate(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx.chart) ctx.chart.destroy();

    const labels = data.categories;
    const values = data.values;

    const chart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Pass rate",
                    data: values,
                    backgroundColor: labels.map((label, i) =>
                        label === "code" ? "#f38ba8" : CHART_COLORS[i % CHART_COLORS.length]
                    ),
                    borderColor: CHART_COLORS,
                    borderWidth: 1,
                    borderRadius: 6,
                },
            ],
        },
        options: {
            ...CHART_STYLE,
            indexAxis: "y",
            scales: {
                x: {
                    stacked: false,
                    grid: { color: "rgba(148,163,184,0.10)" },
                    ticks: {
                        color: "var(--text-secondary)",
                        font: { family: CHART_FONT, size: 11 },
                        callback: (v) => Math.round(v * 100) + "%",
                    },
                },
                y: {
                    grid: { color: "rgba(148,163,184,0.10)" },
                    ticks: { color: "var(--text-secondary)", font: { family: CHART_FONT, size: 11 } },
                },
            },
        },
    });

    ctx.chart = chart;
    ctx.chart.data = { labels, values };
}
