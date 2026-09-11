import { Chart, registerables } from "chart.js";

console.log("registerables len:", registerables.length);
console.log("register type:", typeof Chart.register);

console.log(
  "before category:",
  Chart.isScaleRegistered && Chart.isScaleRegistered("category"),
);
Chart.register(...registerables);
console.log("after category:", Chart.isScaleRegistered("category"));
console.log("after linear:", Chart.isScaleRegistered("linear"));
console.log("after bar controller:", Chart.isDatasetTypeRegistered("bar"));
console.log("after title plugin:", Chart.isPluginTypeRegistered("title"));
