import * as m from "chart.js";
console.log("version BEFORE register:", m.version);

// Standard fix: register all registerables
m.Chart.register(...m.registerables);

console.log("version AFTER register:", m.Chart.version);

function makeCtx() {
  const noop = () => {};
  return {
    canvas: {},
    setTransform: noop,
    rotate: noop,
    translate: noop,
    scale: noop,
    lineDash: noop,
    addEventListener: noop,
    removeEventListener: noop,
    measureText: (t) => ({ width: String(t).length }),
    save: noop,
    restore: noop,
    clip: noop,
    isPointInPath: noop,
    beginPath: noop,
    rect: noop,
    closePath: noop,
    fill: noop,
    stroke: noop,
    fillRect: noop,
    clearRect: noop,
    createLinearGradient: () => ({ addColorStop: noop }),
    createRadialGradient: () => ({ addColorStop: noop }),
  };
}
const canvas = { getContext: () => makeCtx() };

try {
  const c = new m.Chart(canvas, {
    type: "bar",
    data: {
      labels: ["a", "b", "c"],
      datasets: [{ label: "x", data: [1, 2, 3] }],
    },
    options: {
      responsive: false,
      plugins: {
        legend: { display: true },
        title: { display: true, text: "t" },
      },
      scales: {
        x: { stacked: true },
        y: { type: "logarithmic", stacked: true },
      },
    },
  });
  console.log("CREATED_OK");
  c.update();
  console.log("UPDATE_OK");
  c.destroy();
  console.log("DESTROY_OK");
} catch (e) {
  console.log("ERROR:", e.message);
}
