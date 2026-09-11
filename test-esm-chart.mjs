import * as m from "chart.js";

console.log("version:", m.version);
console.log("has Chart:", !!m.Chart);
console.log("registerables type:", typeof m.registerables);
if (m.registerables && typeof m.registerables === "object") {
  console.log("registerables keys:", Object.keys(m.registerables));
  console.log("CategoryScale:", typeof m.registerables.CategoryScale);
  console.log("BarController:", typeof m.registerables.BarController);
}
console.log("Chart.isScaleRegistered:", typeof m.Chart.isScaleRegistered);
