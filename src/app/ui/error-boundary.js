/**
 * Error Boundary Component
 * 
 * A React-style error boundary for vanilla JavaScript.
 * Catches rendering errors and displays user-friendly fallbacks.
 */

/**
 * ErrorBoundary - A class-based error boundary component
 * 
 * Usage:
 * ```js
 * const ErrorBoundary = createErrorBoundary({
 *   fallback: <div>Error occurred</div>
 * });
 * 
 * <ErrorBoundary>
 *   <CriticalComponent />
 * </ErrorBoundary>
 * ```
 */
export function createErrorBoundary(options = {}) {
  const {
    fallback = '<div class="error-boundary">An unexpected error occurred. Please try again.</div>',
    logLevel = 'error',
    onCapture = null,
    onRender = null
  } = options;
  
  let hasError = false;
  let error = null;
  let errorInfo = null;
  
  const ErrorBoundary = class extends React.Component {
    constructor(props) {
      super(props);
      this.state = { hasError: false, error: null };
    }
    
    static getDerivedStateFromError(error) {
      hasError = true;
      error = error;
      return { hasError: true, error };
    }
    
    componentDidCatch(error, errorInfo) {
      errorInfo = errorInfo;
      console[logLevel](error, errorInfo);
      if (onCapture) onCapture(error, errorInfo);
    }
    
    render() {
      if (this.state.hasError) {
        return fallback;
      }
      return this.props.children;
    }
  };
  
  return ErrorBoundary;
}

/**
 * Simple ErrorBoundary for immediate use
 * 
 * Usage:
 * ```js
 * const ErrorBoundary = createErrorBoundary({
 *   fallback: <div>Error occurred</div>
 * });
 * ```
 */
export const ErrorBoundary = createErrorBoundary();

/**
 * ErrorBoundary with default options
 */
export const DefaultErrorBoundary = createErrorBoundary({
  fallback: '<div class="error-boundary">An unexpected error occurred. Please try again.</div>',
  logLevel: 'error'
});

/**
 * ErrorBoundary with detailed logging
 */
export const DebugErrorBoundary = createErrorBoundary({
  fallback: '<div class="error-boundary debug">
    <h2>Something went wrong!</h2>
    <pre class="error-details">' +
    '<span class="error-type">Type:</span> ' +
    '<span class="error-message">' +
    (typeof error !== 'undefined' ? error.constructor.name + ': ' +
    (error.message || 'Unknown error') +
    '</span>' +
    '</pre>
    <button onclick="window.location.reload()">Reload Page</button>
  </div>',
  logLevel: 'debug'
});

/**
 * Component wrapper for error handling
 * 
 * @param {Object} props - Component props
 * @param {Function} props.children - Child components
 */
export function withErrorBoundary(Component) {
  return function WrappedComponent(props) {
    return (
      <ErrorBoundary>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}

/**
 * Error display component
 * 
 * Renders a styled error message with recovery options
 */
export function ErrorDisplay({ error, onRetry }) {
  return `
    <div class="error-boundary">
      <h2>⚠️ Error occurred</h2>
      <p class="error-message">${escapeHtml(error?.message || 'An unexpected error occurred')}</p>
      <p class="error-stack">${escapeHtml(formatError(error))}</p>
      ${onRetry ? `<button class="error-retry" onclick="${onRetry}">Retry</button>` : ''}
      <button class="error-help" onclick="window.location.reload()">Reload Page</button>
    </div>
  `;
}

/**
 * Format error for display
 */
function formatError(error) {
  if (!error) return 'Unknown error';
  
  let message = error.message || String(error);
  
  // Stack trace if available
  if (error.stack) {
    message += '\n\n' + error.stack.split('\n').slice(0, 10).join('\n');
  }
  
  return message;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Error boundary for entire application
 * 
 * Wraps the main application to catch any rendering errors
 */
export function AppErrorBoundary({ children }) {
  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  );
}

/**
 * Error boundary for benchmark runner
 */
export function BenchmarkErrorBoundary({ children }) {
  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  );
}
