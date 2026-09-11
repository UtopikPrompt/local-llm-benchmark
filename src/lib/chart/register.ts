// Chart.js 4.x does not auto-register scales/controllers/elements/plugins when
// you `import { Chart } from 'chart.js'`. The ESM/UMD entry exports a bare
// `Chart` class whose internal registry is empty, so building a chart that uses
// a category/x scale throws `"category" is not a registered scale.`
//
import { Chart } from "chart.js";
import type { Chart as ChartType } from "chart.js";

// Chart.js 4.x does not auto-register scales/controllers/elements/plugins when
// you `import { Chart } from 'chart.js'`. The ESM/UMD entry exports a bare
// `Chart` class whose internal registry is empty, so building a chart that uses
// a category/x scale throws `"category" is not a registered scale.`
//
// We register the registerables (controllers, elements, plugins, scales) into
// the Chart class registry so every component is available. This must run
// before `new Chart(...)` is called.
export function registerChart(): void {
  const chartClass = Chart as unknown as {
    registerables: unknown[];
    register: (...items: unknown[]) => void;
  };
  if (chartClass.register) {
    chartClass.registerables.forEach((item) => chartClass.register(item));
  }
}

export { Chart };
export type { ChartType };
