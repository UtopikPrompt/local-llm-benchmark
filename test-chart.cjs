const { registerables } = require("chart.js");
const { Chart } = registerables;
console.log("version:", Chart.version);
console.log("category registered:", Chart.isScaleRegistered("category"));
console.log("bar registered:", Chart.isDatasetTypeRegistered("bar"));
