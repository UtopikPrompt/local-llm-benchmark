import { Chart, registerables } from "chart.js";

Chart.register(...registerables);

function makeCtx() {
  const noop = () => {};
  return {
    canvas: {},
    setTransform: noop,
    resetTransform: noop,
    rotate: noop,
    translate: noop,
    scale: noop,
    lineDash: noop,
    setLineDash: noop,
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
    moveTo: noop,
    lineTo: noop,
    bezierCurveTo: noop,
    arc: noop,
    arcTo: noop,
    quadraticCurveTo: noop,
    closePath: noop,
    save: noop,
    restore: noop,
    translate: noop,
    rotate: noop,
    scale: noop,
    transform: noop,
    rect: noop,
    clip: noop,
    beginPath: noop,
    strokeRect: noop,
    fillRect: noop,
    fillText: noop,
    strokeText: noop,
    drawImage: noop,
    quadraticCurveTo: noop,
    setLineDash: noop,
  };
}
const canvas = { getContext: () => makeCtx() };

try {
  const c = new Chart(canvas, {
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
