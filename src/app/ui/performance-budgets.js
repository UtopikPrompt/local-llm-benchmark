/**
 * Performance Budget Configuration
 * 
 * Defines thresholds for various performance metrics.
 * Violations are logged and can trigger alerts.
 */

const PERFORMANCE_BUDGETS = {
  // Bundle size budgets (in bytes)
  bundleSize: {
    main: { limit: 500 * 1024, warning: 400 * 1024, budget: '500KB' },
    ui: { limit: 200 * 1024, warning: 150 * 1024, budget: '200KB' },
    api: { limit: 100 * 1024, warning: 80 * 1024, budget: '100KB' },
    helpers: { limit: 50 * 1024, warning: 40 * 1024, budget: '50KB' }
  },
  
  // Runtime performance budgets (in milliseconds)
  runtime: {
    init: { limit: 3000, warning: 2000, budget: '3s' },
    render: { limit: 1000, warning: 750, budget: '1s' },
    interaction: { limit: 200, warning: 150, budget: '200ms' },
    network: { limit: 5000, warning: 3000, budget: '5s' }
  },
  
  // Web Vitals thresholds (in seconds/milliseconds)
  webVitals: {
    fcp: { limit: 2000, warning: 1500, budget: '2s' },
    lcp: { limit: 2500, warning: 2000, budget: '2.5s' },
    tid: { limit: 800, warning: 500, budget: '800ms' },
    cls: { limit: 0.1, warning: 0.125, budget: '125ms' },
    fid: { limit: 100, warning: 200, budget: '100ms' }
  }
};

/**
 * Check if a metric violates its budget
 * @param {string} metric - The metric name
 * @param {number} value - The measured value
 * @param {string} unit - The unit of measurement
 * @returns {{violated: boolean, warning: boolean, budget: string}}
 */
function checkBudget(metric, value, unit) {
  const budget = PERFORMANCE_BUDGETS[metric];
  if (!budget) {
    console.warn(`No budget defined for metric: ${metric}`);
    return { violated: false, warning: false, budget: 'N/A' };
  }
  
  const { limit, warning: warningLimit, budget: budgetStr } = budget;
  const violated = value > limit;
  const warning = value > warningLimit && !violated;
  
  return { violated, warning, budget: budgetStr };
}

/**
 * Log a performance budget violation
 * @param {string} metric - The metric name
 * @param {number} value - The measured value
 * @param {string} unit - The unit of measurement
 */
function logBudgetViolation(metric, value, unit) {
  const budget = PERFORMANCE_BUDGETS[metric];
  if (budget) {
    const { limit } = budget;
    const violation = value > limit ? 'VIOLATED' : 'WARNING';
    console.warn(`[Performance Budget] ${violation}: ${metric} = ${value}${unit} (limit: ${limit}${unit})`);
  }
}

export { PERFORMANCE_BUDGETS, checkBudget, logBudgetViolation };
