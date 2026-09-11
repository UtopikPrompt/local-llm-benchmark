// Test creating a real Chart instance in a DOM-like environment
import * as m from "chart.js";
console.log("version:", m.version);

// jsdom provides a canvas
const { JSDOM } = await import("jsdom");
const dom = new JSDOM("<!DOCTYPE html><body></body>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.navigator = dom.window.navigator;

const canvas = document.createElement("canvas");
document.body.appendChild(canvas);
const ctx = canvas.getContext("2d");
console.log("ctx:", !!ctx);

try {
  const chart = new m.Chart(ctx, {
    type: "bar",
    data: {
      labels: ["a", "b", "c"],
      datasets: [{ label: "x", data: [1, 2, 3] }],
    },
    options: {
      scales: {
        x: { stacked: true },
        y: { type: "logarithmic", stacked: true },
      },
    },
  });
  console.log("Chart created OK");
  console.log(
    "chart config scales x type:",
    chart.config.options.scales.x.type,
  );
  await chart.update();
  console.log("chart.update() OK");
  chart.destroy();
  console.log("chart.destroy() OK");
} catch (e) {
  console.log("ERROR:", e.message);
}
