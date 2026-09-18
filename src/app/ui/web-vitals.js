/**
 * Web Vitals Tracking
 * 
 * Monitors Core Web Vitals and logs them to the console.
 * Reports on load, interaction, and scroll events.
 */

// Storage key for Web Vitals data
const WEB_VITALS_STORAGE_KEY = 'web-vitals-data';

/**
 * Web Vitals configuration
 */
const WEB_VITALS_CONFIG = {
  // Events to track
  events: {
    load: 'page-load',
    interaction: 'user-interaction',
    scroll: 'scroll'
  },
  
  // Data retention period (in milliseconds)
  retention: 300000, // 5 minutes
  
  // Aggregation window
  aggregationWindow: 10000 // 10 seconds
};

/**
 * Web Vitals data storage
 */
const webVitalsData = new Map();

/**
 * Storage helper for Web Vitals data
 */
const storage = {
  get(key) {
    try {
      const data = localStorage.getItem(key);
      if (!data) return null;
      return JSON.parse(data);
    } catch (e) {
      console.warn('Failed to read storage:', e);
      return null;
    }
  },
  
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.warn('Failed to write storage:', e);
    }
  },
  
  cleanup() {
    const now = Date.now();
    const retention = WEB_VITALS_CONFIG.retention;
    
    for (const [key, data] of webVitalsData.entries()) {
      if (now - data.timestamp > retention) {
        webVitalsData.delete(key);
        localStorage.removeItem(key);
      }
    }
  }
};

/**
 * Record a Web Vitals measurement
 * 
 * @param {string} name - The metric name (fcp, lcp, tid, cls, fid, etc.)
 * @param {number} value - The measured value
 * @param {string} unit - The unit (ms, s, etc.)
 * @param {string} event - The event type (load, interaction, scroll)
 */
function recordWebVital(name, value, unit, event = 'load') {
  const data = storage.get(WEB_VITALS_STORAGE_KEY) || new Map();
  
  const key = `${event}:${name}`;
  const timestamp = Date.now();
  
  // Store individual measurement
  data.set(key, {
    timestamp,
    value,
    unit
  });
  
  // Store aggregated metrics
  const aggregated = {
    count: 1,
    values: [],
    timestamp
  };
  
  if (data.has(key + ':aggregated')) {
    const existing = data.get(key + ':aggregated');
    existing.count++;
    existing.values.push(value);
    existing.timestamp = timestamp;
  } else {
    data.set(key + ':aggregated', aggregated);
  }
  
  storage.set(WEB_VITALS_STORAGE_KEY, data);
  
  // Log the measurement
  console.log(`[Web Vitals] ${name}: ${value}${unit}`);
  
  // Check against budgets
  checkWebVitalBudget(name, value, unit);
  
  // Cleanup old data
  storage.cleanup();
}

/**
 * Check if a Web Vital violates its budget
 * 
 * @param {string} name - The metric name
 * @param {number} value - The measured value
 * @param {string} unit - The unit
 */
function checkWebVitalBudget(name, value, unit) {
  const budget = PERFORMANCE_BUDGETS.webVitals[name];
  if (!budget) return;
  
  const { limit, warning: warningLimit } = budget;
  const violated = value > limit;
  const warning = value > warningLimit && !violated;
  
  const message = `${name}: ${value}${unit} ${
    violated ? '❌ VIOLATED' : warning ? '⚠️ WARNING' : '✅ OK'
  } (limit: ${limit}${unit})`;
  
  if (violated) {
    console.warn(`[Web Vitals] ${message}`);
  } else if (warning) {
    console.info(`[Web Vitals] ${message}`);
  }
}

/**
 * Calculate aggregate Web Vitals metrics
 * 
 * @param {string} event - The event type
 * @returns {Object} Aggregated metrics
 */
function getAggregatedWebVitals(event) {
  const data = storage.get(WEB_VITALS_STORAGE_KEY) || new Map();
  const metrics = {};
  
  for (const [key, value] of data.entries()) {
    if (key.startsWith(event + ':')) {
      const metricName = key.replace(event + ':', '');
      
      if (key.endsWith(':aggregated')) {
        const aggregated = JSON.parse(value);
        metrics[metricName] = {
          count: aggregated.count,
          values: aggregated.values,
          min: Math.min(...aggregated.values),
          max: Math.max(...aggregated.values),
          avg: aggregated.values.reduce((a, b) => a + b, 0) / aggregated.values.length,
          sum: aggregated.values.reduce((a, b) => a + b, 0)
        };
      } else {
        // Individual measurement - compute stats
        metrics[metricName] = {
          count: 1,
          values: [value],
          min: value,
          max: value,
          avg: value,
          sum: value
        };
      }
    }
  }
  
  return metrics;
}

/**
 * Get Web Vitals summary for display
 * 
 * @returns {Object} Summary of all Web Vitals
 */
function getWebVitalsSummary() {
  const metrics = {};
  
  for (const [event, eventMetrics] of Object.entries(getAggregatedWebVitals())) {
    for (const [metricName, data] of Object.entries(eventMetrics)) {
      metrics[metricName] = {
        count: data.count,
        min: data.min,
        max: data.max,
        avg: data.avg,
        unit: data.unit
      };
    }
  }
  
  return metrics;
}

/**
 * Generate Web Vitals HTML report
 * 
 * @returns {string} HTML string with Web Vitals report
 */
function generateWebVitalsReport() {
  const summary = getWebVitalsSummary();
  let html = `
    <section class="web-vitals-report">
      <h2>📊 Web Vitals Report</h2>
      <p class="report-summary">
        <span class="report-count">Total measurements: ${Object.keys(summary).length}</span>
        <span class="report-avg">| Average values: ${Object.entries(summary)
          .map(([metric, data]) => `${metric}: ${data.avg}${data.unit}`)
          .join(', ')}</span>
      </p>
      <table class="web-vitals-table">
        <thead>
          <ttr>
            <th>Metric</th>
            <th>Count</th>
            <th>Min</th>
            <th>Avg</th>
            <th>Max</th>
          </ttr>
        <tbody>
  `;
  
  for (const [metricName, data] of Object.entries(summary)) {
    const status = getMetricStatus(data.avg, data.unit);
    html += `
      <ttr>
        <td>${metricName}</td>
        <td>${data.count}</td>
        <td>${data.min}${data.unit}</td>
        <td>${data.avg}${data.unit}</td>
        <td>${data.max}${data.unit}</td>
        <td class="${status.class}" title="${status.message}">${status.icon}</td>
      <ttr>
    `;
  }
  
  html += `
        </tbody>
      </table>
    </section>
  `;
  
  return html;
}

/**
 * Get status for a metric
 * 
 * @param {number} value - The metric value
 * @param {string} unit - The unit
 * @returns {Object} Status information
 */
function getMetricStatus(value, unit) {
  const budget = PERFORMANCE_BUDGETS.webVitals[unit.replace('s', '')];
  if (!budget) {
    return {
      icon: '📊',
      class: '',
      message: 'No budget defined'
    };
  }
  
  const { limit, warning: warningLimit } = budget;
  const violated = value > limit;
  const warning = value > warningLimit && !violated;
  
  if (violated) {
    return {
      icon: '❌',
      class: 'status-violated',
      message: `Limit ${limit}${unit} exceeded`
    };
  } else if (warning) {
    return {
      icon: '⚠️',
      class: 'status-warning',
      message: `Above warning threshold ${warningLimit}${unit}`
    };
  } else {
    return {
      icon: '✅',
      class: 'status-ok',
      message: 'Within budget'
    };
  }
}

/**
 * Initialize Web Vitals tracking
 * 
 * Tracks page load metrics and subsequent user interactions
 */
export function initializeWebVitals() {
  // Track initial paint
  const initialTime = performance.now();
  
  // Track First Contentful Paint
  if ('paintTiming' in performance) {
    performance.measure('First Contentful Paint');
    
    performance.getEntriesByName('First Contentful Paint')
      .forEach(entry => {
        recordWebVital('fcp', entry.duration, 'ms', 'load');
      });
  }
  
  // Track Largest Contentful Paint
  if ('largestContentfulPaint' in performance) {
    performance.measure('Largest Contentful Paint');
    
    performance.getEntriesByName('Largest Contentful Paint')
      .forEach(entry => {
        recordWebVital('lcp', entry.value, 'ms', 'load');
      });
  }
  
  // Track Time to Interactive
  if ('longTaskTime' in performance) {
    performance.measure('Time to Interactive');
    
    performance.getEntriesByName('longtask')
      .forEach(entry => {
        recordWebVital('tid', entry.duration, 'ms', 'load');
      });
  }
  
  // Track Cumulative Layout Shift
  if ('layoutShiftEntries' in performance) {
    performance.getEntriesByName('layout-shift')
      .forEach(entry => {
        recordWebVital('cls', entry.value, '', 'load');
      });
  }
  
  // Track First Input Delay
  if ('inputDelay' in performance) {
    performance.getEntriesByName('input-delay')
      .forEach(entry => {
        recordWebVital('fid', entry.duration, 'ms', 'interaction');
      });
  }
  
  // Track user interactions
  document.addEventListener('click', () => {
    recordWebVital('interaction', performance.now() - initialTime, 'ms', 'interaction');
  });
  
  document.addEventListener('touchstart', () => {
    recordWebVital('interaction', performance.now() - initialTime, 'ms', 'interaction');
  });
  
  // Track scroll events
  document.addEventListener('scroll', () => {
    recordWebVital('scroll', performance.now() - initialTime, 'ms', 'scroll');
  });
  
  // Log Web Vitals report on page unload
  window.addEventListener('beforeunload', () => {
    console.log('\n' + generateWebVitalsReport());
  });
  
  // Periodic cleanup
  setInterval(() => {
    storage.cleanup();
  }, 60000); // Cleanup every minute
}

/**
 * Get Web Vitals data for a specific metric
 * 
 * @param {string} metric - The metric name
 * @returns {Object|null} Metric data or null if not found
 */
export function getWebVitalsMetric(metric) {
  const data = storage.get(WEB_VITALS_STORAGE_KEY) || new Map();
  
  for (const [key, value] of data.entries()) {
    if (key.includes(metric)) {
      return JSON.parse(value);
    }
  }
  
  return null;
}

/**
 * Get all Web Vitals data
 * 
 * @returns {Map} Map of all Web Vitals data
 */
export function getAllWebVitalsData() {
  return storage.get(WEB_VITALS_STORAGE_KEY) || new Map();
}

/**
 * Clear all Web Vitals data
 */
export function clearWebVitalsData() {
  storage.set(WEB_VITALS_STORAGE_KEY, new Map());
  storage.cleanup();
}

// Initialize on module load
initializeWebVitals();
