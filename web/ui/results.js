// Benchmark results view (Dashboard / Benchmark tabs).
//
// Renders the results table, the row filter controls, and drives the
// benchmark run. Shares formatting helpers with the challenges view and the
// model-selection helpers with ``models.js``.
import state from './state.js'
import dom from './dom.js'
import { serializeSelectedModels, buildRunRequest } from './models.js'
import { loadChallenges, toggleCategoryFilter } from './challenges.js'

// Format a numeric / string cell value, returning an em dash for empty input.
function fmt(n) {
  if (n === null || n === undefined || n === '') return '—'
  if (Number.isNaN(Number(n))) return n
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 3 })
}

// Class pill for a boolean quality metric.
function cls(value, passClass, failClass, warnClass) {
  if (value === true) return '<span class="pill ' + passClass + '">' + value + '</span>'
  if (value === false) return '<span class="pill ' + failClass + '">' + value + '</span>'
  if (value === null || value === undefined || value === '') return ''
  return '<span class="pill warn">' + value + '</span>'
}

function renderResult(r) {
  return (
    '<tr>' +
      '<td class="mono" style="color:var(--text-secondary);">' + escapeHtml(r.engine) + '</td>' +
      '<td class="mono" style="color:var(--text-secondary);">' + escapeHtml(r.model) + '</td>' +
      '<td class="pill">' + escapeHtml(r.category) + '</td>' +
      '<td class="mono">' + fmt(r.ttft_s) + '</td>' +
      '<td class="mono">' + fmt(r.tok_per_s) + '</td>' +
      '<td class="mono">' + fmt(r.iters_per_s) + '</td>' +
      '<td class="pill">' + cls(r.quality, 'pass', 'fail', 'warn') + '</td>' +
      '<td class="pill">' + cls(r.qualityJudge, 'pass', 'fail', 'warn') + '</td>' +
    '</tr>'
  )
}

// Render the results table from a set of benchmark results.
function displayResults(results, modelNames, benchmarkType) {
  if (!state.resultsRendered) {
    // First load: the dashboard ships with a default results table, so we
    // must guard against replacing it before a real run has occurred.
    return
  }
  const resultsContainer = dom.getEl(document, '#results-container')
  resultsContainer.innerHTML = ''
  const modelList = dom.getEl(resultsContainer, '#engine-list')
  resultsContainer.classList.add('rendered')
  modelList.classList.remove('expanded')

  if (modelNames && modelNames.length === 0) {
    resultsContainer.innerHTML = ''
    resultsContainer.appendChild(createRunState())
    return
  }

  resultsContainer.classList.remove('empty')
  resultsContainer.classList.add('results-rendered')
  const resultsTable = buildResultsTable(results, modelNames, benchmarkType)
  resultsContainer.appendChild(resultsTable)
}

function createRunState() {
  const resultsContainer = dom.getEl(document, '#results-container')
  resultsContainer.classList.add('run-state')
  const runNote = dom.getEl(resultsContainer, '#run-note')
  runNote.textContent = 'Select at least one model to run a benchmark.'
  const runButton = dom.getEl(resultsContainer, '#run-button')
  const benchmarkType = document.getElementById('benchmarkType')
  runButton.setAttribute('data-benchmark-type', benchmarkType ? benchmarkType.value : 'quality')
  runButton.addEventListener('click', runBenchmark)
  return runButton
}

function buildResultsTable(results, modelNames, benchmarkType) {
  const resultsContainer = dom.getEl(document, '#results-container')
  const resultsHeader = dom.getEl(resultsContainer, '#results-header')
  resultsHeader.textContent = benchmarkType === 'latency' ? 'Latency results' : 'Quality results'
  const resultsFilter = dom.getEl(resultsContainer, '#results-filter')
  const resultsFilterEl = dom.getEl(resultsContainer, '#results-filter')
  resultsFilterEl.innerHTML = ''
  resultsFilterEl.appendChild(createSearchFilter())
  resultsFilterEl.appendChild(createCategoryFilter())
  const resultsTable = dom.create('table', { className: 'results-table' }, [])
  resultsContainer.appendChild(resultsTable)
  return resultsTable
}

function createSearchFilter() {
  const resultsContainer = dom.getEl(document, '#results-container')
  const resultsFilter = dom.getEl(resultsContainer, '#results-filter')
  const search = dom.create('input', { className: 'search', placeholder: 'Filter results', type: 'text', onInput: filterResults })
  resultsFilter.appendChild(search)
  return search
}

function createCategoryFilter() {
  const resultsContainer = dom.getEl(document, '#results-container')
  const resultsFilter = dom.getEl(resultsContainer, '#results-filter')
  const categories = dom.getEl(resultsContainer, '#results-categories')
  const clear = dom.create('button', { className: 'clear', onclick: clearResults, type: 'button' }, ['Clear'])
  categories.appendChild(clear)
  return categories
}

function filterResults() {
  const search = dom.getEl(document, '#results-search')
  const resultsTable = dom.getEl(document, '.results-table')
  const filter = search.value.toLowerCase()
  const rows = resultsTable.querySelectorAll('tbody tr')
  for (const row of rows) {
    row.style.display = row.textContent.toLowerCase().includes(filter) ? '' : 'none'
  }
}

function clearResults() {
  const search = dom.getEl(document, '#results-search')
  if (search) search.value = ''
  const resultsTable = dom.getEl(document, '.results-table')
  if (resultsTable) resultsTable.querySelectorAll('tbody tr').forEach((row) => { row.style.display = '' })
  const categories = dom.getEl(document, '#results-categories')
  if (categories) categories.querySelector('.clear').click()
}

function updateResultsCount(visible) {
  const resultsCount = dom.getEl(document, '#results-count')
  resultsCount.textContent = visible + ' shown'
}

// Load benchmark results for the currently selected models.
async function loadBenchmarkResults(modelNames) {
  const benchmarkType = document.getElementById('benchmarkType')
  const type = benchmarkType ? benchmarkType.value : 'quality'
  const resultsContainer = dom.getEl(document, '#results-container')
  const response = await fetch('/api/results?' + new URLSearchParams({ benchmark_type: type, model_names: modelNames || '' }).toString())
  if (!response.ok) {
    resultsContainer.innerHTML = ''
    resultsContainer.appendChild(createRunState())
    return
  }
  displayResults(await response.json(), modelNames, type)
}

// Run a benchmark for the currently active model.
async function runBenchmark() {
  const resultsContainer = dom.getEl(document, '#results-container')
  const runButton = resultsContainer.querySelector('.run-button')
  const runNote = resultsContainer.querySelector('.run-note')
  const runButtonEl = runButton || resultsContainer.querySelector('#run-button')
  runButtonEl.setAttribute('disabled', 'true')
  runNote.textContent = 'Running benchmark…'
  try {
    const response = await fetch('/run', { method: 'POST', body: JSON.stringify(buildRunRequest(state.activeModel)) })
    if (response.ok) {
      const results = await response.json()
      displayResults(results, serializeSelectedModels(), 'quality')
    } else {
      const error = await response.json().catch(() => ({}))
      runNote.textContent = 'Error: ' + (error.detail || error.message || response.statusText)
    }
  } catch (e) {
    runNote.textContent = 'Error: ' + e.message
  } finally {
    const runButtonEl2 = runButton || resultsContainer.querySelector('#run-button')
    runButtonEl2.removeAttribute('disabled')
  }
}

function escapeHtml(value) {
  if (value === null || value === undefined) return ''
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

const RESULTS_ROWS = '.results-table tbody tr';
const RESULTS_SEARCH = '#results-search';
const RESULTS_CLEAR = '#results-clear';
const RESULTS_CATEGORIES = '#results-categories';

function rowText(rows) {
  return Array.from(rows).map((r) => r.textContent.toLowerCase());
}

function attachResultsFilterListeners() {
  const searchInput = dom.getEl(document, RESULTS_SEARCH);
  const clearButton = dom.getEl(document, RESULTS_CLEAR);
  if (searchInput) {
    searchInput.value = '';
    searchInput.addEventListener('input', (e) => {
      const value = e.target.value.trim().toLowerCase();
      const rows = document.querySelectorAll(RESULTS_ROWS);
      const texts = rowText(rows);
      let visible = 0;
      for (let i = 0; i < texts.length; i++) {
        const match = value === '' || texts[i].includes(value);
        rows[i].style.display = match ? '' : 'none';
        if (match) visible++;
      }
      updateResultsCount(visible);
    });
  }
  if (clearButton) {
    clearButton.addEventListener('click', () => {
      const search = dom.getEl(document, RESULTS_SEARCH);
      if (search) search.value = '';
      document.querySelectorAll(RESULTS_ROWS).forEach((row) => (row.style.display = ''));
      dom.getEl(document, RESULTS_CATEGORIES).innerHTML = '';
      updateResultsCount(document.querySelectorAll(RESULTS_ROWS).length);
    });
  }
}

export {
  fmt,
  cls,
  renderResult,
  displayResults,
  attachResultsFilterListeners,
  updateResultsCount,
  escapeHtml,
  loadBenchmarkResults,
  runBenchmark,
}
