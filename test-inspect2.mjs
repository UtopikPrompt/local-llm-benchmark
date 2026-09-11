import * as chart from "chart.js";

const c = chart.Chart;
console.log("Chart typeof:", typeof c);
console.log("Chart is function:", c && typeof c === "function");
console.log("Chart.register:", c && typeof c.register);
console.log("Chart.version:", c && c.version);
console.log("top-level register:", typeof chart.register);
console.log(
  "top-level registerables:",
  Array.isArray(chart.registerables)
    ? "array len " + chart.registerables.length
    : typeof chart.registerables,
);
console.log("Chart has registerables static:", c && typeof c.registerables);
