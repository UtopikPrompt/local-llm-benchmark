// Benchmark results view (Dashboard / Benchmark tabs).
//
// Renders the results table, the row filter controls, and drives the
// benchmark run. Shares formatting helpers with the challenges view and the
// model-selection helpers with ``models.js``.
import state from './state.js'
import dom from './dom.js'
import { serializeSelectedModels, buildRunRequest } from './models.js'
import { loadChallenges, toggleCategoryFilter, perCardStatus } from './challenges.js'
import { ensureRunState } from './main.js'

// Return the currently active view panel. ALL results-panel lookups must go
// through this panel because ``dom.getEl`` falls back to
// ``document.getElementById`` (see dom.js), which only finds the FIRST match —
// the hidden Dashboard panel — instead of the one currently shown. Every
// ``dom.getEl(document, ...)`` call in this module is a latent bug waiting for
// the wrong panel; this helper resolves the active panel from ``state``.
function activePanel() {
  return document.querySelector(
    '#content-area .view-panel[data-view="' + (state.activeView || 'benchmark') + '"]'
  )
}

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
  if (state.selectedModels.length === 0) {
    // No model selected: render the empty-state instead of a results table.
    const resultsContainer = state.resultsContainer
    resultsContainer.innerHTML = ''
    resultsContainer.appendChild(createRunState())
    return
  }
  if (!state.resultsRendered) {
    // First load: the dashboard ships with a default results table, so we
    // must guard against replacing it before a real run has occurred.
    return
  }
  const resultsContainer = state.resultsContainer
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
  wirePerCardStatus(results, modelNames, benchmarkType)
}

// Wire per-challenge status into each challenge card in the Dashboard's
// challenges panel. Each result Row corresponds to a single (engine, task) pair
// for one model, so group rows by model and map each row's ``task_id`` onto the
// matching challenge card. Cards are injected into the DOM by ``loadChallenges``
// at initialization, so the global lookup in ``perCardStatus`` finds them even
// when the challenges panel isn't the active view. Tasks with no row (e.g. the
// select-all checkbox or tasks excluded by a filter) are left untouched.
function wirePerCardStatus(results, modelNames, benchmarkType) {
  if (!results || modelNames === undefined) return
  const cards = document.querySelectorAll('.challenge-card[data-id]')
  for (const card of cards) {
    const taskId = card.getAttribute('data-id')
    const name = modelNames && modelNames[taskId]
    if (!name) continue
    let anyRow = null
    for (const r of results) {
      if (r.taskId === taskId) {
        anyRow = r
        break
      }
    }
    if (!anyRow) continue
    let status
    if (anyRow.quality_passed === true) status = 'pass'
    else if (anyRow.quality_passed === false) status = 'fail'
    else if (anyRow.quality_passed === null || anyRow.quality_passed === undefined || anyRow.quality_passed === '') {
      if (anyRow.error) status = 'error'
      else if (anyRow.qualityJudge) status = 'judge'
      else status = 'not-run'
    } else if (anyRow.error) {
      status = 'error'
    } else if (anyRow.qualityJudge) {
      status = 'judge'
    } else {
      status = 'not-run'
    }
    try {
      perCardStatus(taskId, status)
    } catch (e) {
      console.error('perCardStatus failed for task ' + taskId, e)
    }
  }
}

// Run-state toolbar: a single cached ``#run-note`` + ``#run-button`` pair.
// The dashboard ships a static ``.run-state-toolbar`` inside each panel's
// ``#results-container``, so it is looked up here (not created). The click
// handler is delegated to the panel so it survives the container's innerHTML
// being cleared on every render.
let runStatePanel = null
let runStateToolbar = null

function onRunStateClick(event) {
  const target = event.target
  if (target && target.id === 'run-button') {
    runBenchmark()
  }
}

function createRunState() {
  const found = ensureRunState()
  if (!found) return null
  const [runButton, runNote] = found
  const resultsContainer = state.resultsContainer
  if (resultsContainer) resultsContainer.classList.add('run-state')
  const benchmarkType = document.getElementById('benchmarkType')
  runButton.setAttribute('data-benchmark-type', benchmarkType ? benchmarkType.value : 'quality')
  if (state.selectedModels.length === 0) {
    // No model selected: dim the run button and show the empty-state note.
    runNote.textContent = 'Select a model to run the benchmark.'
    runButton.classList.add('btn-primary')
    runButton.setAttribute('disabled', 'true')
  } else {
    runNote.textContent = 'Select at least one model to run a benchmark.'
    runButton.removeAttribute('disabled')
  }
  return runButton
}

function buildResultsTable(results, modelNames, benchmarkType) {
  const resultsContainer = state.resultsContainer
  const resultsHeader = dom.getEl(resultsContainer, '#results-header')
  resultsHeader.textContent = benchmarkType === 'latency' ? 'Latency results' : 'Quality results'
  ensureResultsFilter()
  const resultsTable = dom.create('table', { className: 'results-table' }, [])
  resultsContainer.appendChild(resultsTable)
  return resultsTable
}

// The search input and "Clear" button are static markup in ``dashboard.html``
// (``#results-search`` / ``#results-clear``). Find them and attach listeners
// only if they are missing — never recreate or re-append nodes.
function ensureResultsFilter() {
  const resultsContainer = state.resultsContainer
  const search = dom.getEl(resultsContainer, '#results-search')
  if (!search) return
  const searchEl = search.querySelector('input')
  if (!searchEl) {
    const input = dom.create('input', { className: 'search', placeholder: 'Filter results', type: 'text', onInput: filterResults })
    search.appendChild(input)
  } else if (!searchEl.getAttribute('oninput')) {
    searchEl.addEventListener('input', filterResults)
  }
  const clear = dom.getEl(resultsContainer, '#results-clear')
  if (clear && !clear.getAttribute('onclick')) {
    clear.addEventListener('click', clearResults)
  }
}

function filterResults() {
  const resultsContainer = state.resultsContainer
  const search = dom.getEl(resultsContainer, '#results-search')
  const resultsTable = dom.getEl(resultsContainer, '.results-table')
  const filter = search.value.toLowerCase()
  const rows = resultsTable.querySelectorAll('tbody tr')
  for (const row of rows) {
    row.style.display = row.textContent.toLowerCase().includes(filter) ? '' : 'none'
  }
}

function clearResults() {
  const resultsContainer = state.resultsContainer
  const search = dom.getEl(resultsContainer, '#results-search')
  if (search) search.value = ''
  const resultsTable = dom.getEl(resultsContainer, '.results-table')
  if (resultsTable) resultsTable.querySelectorAll('tbody tr').forEach((row) => { row.style.display = '' })
  const categories = dom.getEl(resultsContainer, '#results-categories')
  if (categories) categories.querySelector('.clear').click()
}

function updateResultsCount(visible) {
  const resultsCount = dom.getEl(state.resultsContainer, '#results-count')
  resultsCount.textContent = visible + ' shown'
}

// Run a benchmark for the currently active model.
async function runBenchmark() {
  const resultsContainer = state.resultsContainer
  const runButton = resultsContainer.querySelector('.run-button')
  const runNote = resultsContainer.querySelector('.run-note')
  const runButtonEl = runButton || resultsContainer.querySelector('#run-button')
  runButtonEl.setAttribute('disabled', 'true')
  runNote.textContent = 'Running benchmark…'
  try {
    const response = await fetch('/api/run', { method: 'POST', body: JSON.stringify(buildRunRequest(state.activeModel)) })
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

const RESULTS_CATEGORIES = '#results-categories';

export {
  fmt,
  cls,
  renderResult,
  displayResults,
  updateResultsCount,
  escapeHtml,
  runBenchmark,
}
