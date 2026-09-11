import * as chart from 'chart.js';

console.log('Chart:', typeof chart.Chart);
console.log('Chart.version:', (chart.Chart && (chart.Chart as any).version));
console.log('Chart.register type:', typeof (chart.Chart && (chart.Chart as any).register));
console.log('registerables type:', typeof (chart as any).registerables);

const chartClass = chart.Chart as any;
console.log('registerables present:', !!chartClass.registerables);
console.log('register present:', !!chartClass.register);
