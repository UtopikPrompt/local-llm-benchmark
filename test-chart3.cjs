const m = require("chart.js");
console.log("registerables keys:", Object.keys(m.registerables).join(","));
const r = m.registerables;
console.log("r.Chart:", typeof r.Chart);
console.log("r.CategoryScale:", typeof r.CategoryScale);
console.log("r.LinearScale:", typeof r.LinearScale);
console.log("r.BarController:", typeof r.BarController);
console.log("r.BarElement:", typeof r.BarElement);
