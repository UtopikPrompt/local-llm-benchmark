// Global UI state.
//
// Previously this was spread across several ``window.__*`` globals and module
// ``let`` declarations in ``main.js``. It now lives in a single object owned
// by this module, which every feature module imports via ``import { state }``.
// This keeps the shared mutable state in one place instead of polluting the
// global scope.

const state = {
  // Models selected by the user (array of model names).
  selectedModels: [],
  // Challenges (tasks) selected by the user (array of task ids).
  selectedChallenges: [],
  // Name of the currently selected engine ('' when none).
  selectedEngine: '',
  // Models selected per engine section: { 'ollama': ['llama3', ...] }.
  engineModels: {},
  // Model whose rows are highlighted in the side menu ('' when none).
  activeModel: '',
  // Engine definitions fetched from ``/api/config/engines``.
  engines: [],
  // The active panel's engine-list container, rebound inside ``switchView``.
  // Read/written by ``loadModels`` (``models.js``).
  engineListContainer: null,
  // The active panel's results container, rebound inside ``switchView``.
  // Read/written by ``displayResults`` (``results.js``).
  resultsContainer: null,
  // Tasks fetched from ``/api/tasks``.
  tasks: [],
  // Active view: 'dashboard' | 'benchmark' | 'challenges'.
  activeView: '',
  // Module-level: whether results have been rendered at least once.
  // Guards ``displayResults`` against an early return on first load, where
  // the dashboard's default ``.results-table`` (from dashboard.html) would
  // otherwise cause the freshly built table to be discarded.
  resultsRendered: false,
  // Module-level: active challenge category filter (null = all).
  activeCategory: null,
}

export default state
