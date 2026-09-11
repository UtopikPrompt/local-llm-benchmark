const m = require("chart.js");
console.log("has registerables:", !!m.registerables);
console.log("has Chart:", !!m.Chart);
if (m.registerables) {
  console.log(
    "registerables keys:",
    Object.keys(m.registerables).slice(0, 40).join(","),
  );
}
if (m.Chart) {
  console.log("Chart.version:", m.Chart.version);
  console.log(
    "isScaleRegistered category:",
    m.Chart.isScaleRegistered("category"),
  );
  console.log(
    "isDatasetTypeRegistered bar:",
    m.Chart.isDatasetTypeRegistered("bar"),
  );
}
