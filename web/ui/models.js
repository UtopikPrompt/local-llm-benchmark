// models.js — engine loading, model-checkbox rendering & selection state.
// Mirrors the original main.js engine/model logic. Shares the single state
// object (default export) and the window.__* globals.

import dom from './dom.js'
import state from './state.js'

// Resolve the base URL for an engine by name.
function engineBaseURL(engineName) {
  const engines = state.engines || []
  const engine = engines.find((e) => e.name === engineName)
  return engine ? engine.base_url : engineName
}

// Ensure the engine list is populated from the config API before reading it.
// Called by ``loadModels()`` so the function is self-sufficient regardless of
// where ``loadEngines()`` was invoked (e.g. from initializeListeners(), where
// it runs asynchronously and may not have completed before loadModels() reads
// ``state.engines``). No-op if engines are already loaded.
async function ensureEngines() {
  if (state.engines && state.engines.length) return state.engines
  try {
    const engines = await loadEngines()
    state.engines = engines || []
  } catch (e) {
    console.error('Failed to load engines:', e)
  }
  return state.engines || []
}

// Fetch and render the model checkboxes for each engine section.
// Idempotent: The target container is cleared first so the function is safe to
// call on every view switch. Must check if state.engineListContainer is available.
async function loadModels() {
  const container = state.engineListContainer
  if (!container) {
    console.warn("loadModels() skipped: Engine list container not found in the current active view.");
    return
  }
  
  try {
    await ensureEngines()
    container.innerHTML = ''
    container.classList.add('loading')
    const selectAll = renderSelectAllCheckbox(container)
    for (const engine of state.engines || []) {
      const engineContent = document.createElement('div')
      engineContent.className = 'engine-content'
      engineContent.dataset.engine = engine.name
      const engineTitle = document.createElement('div')
      engineTitle.className = 'engine-title'
      engineTitle.textContent = engine.name
      engineContent.appendChild(engineTitle)

      const heading = document.createElement('button')
      heading.className = 'engine-heading'

      const name = document.createElement('span')
      name.className = 'engine-heading-text'
      name.textContent = engine.name
      heading.appendChild(name)

      const toggle = document.createElement('span')
      toggle.className = 'engine-chevron'
      toggle.textContent = '▾'
      heading.appendChild(toggle)

      heading.addEventListener('click', () => engineContent.classList.toggle('expanded'))

      const engineModels = state.engineModels || []
      (async () => {
        try {
          const resp = await fetch('/api/models?base_url=' + encodeURIComponent(engine.base_url), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_url: engine.base_url })
          })
          const data = await resp.json()
          if (data.models) {
            for (const model of data.models) engineModels.push(model)
            renderModelCheckboxes(engineContent, engine.name, engineModels)
          } else {
            const note = document.createElement('p')
            note.className = 'model-empty'
            note.textContent = 'No models available.'
            engineContent.appendChild(note)
          }
        } catch (e) {
          console.error('Failed to load models for', engine.name, e)
        }
      })()

      container.appendChild(engineContent)
    }
    updateSelectAllCount()
    attachModelListeners()
  } catch (e) {
    console.error('Error loading models:', e)
  } finally {
    container.classList.remove('loading')
  }
}

// Camel-case and humanize the model name (e.g. "gpt_4o" -> "Gpt 4o").
function formatModelName(model) {
  return model.charAt(0).toUpperCase() + model.slice(1).replace(/_/g, ' ')
}

// Render the model checkboxes for a single engine section.
function renderModelCheckboxes(engineContent, engineName, models) {
  const list = document.createElement('div')
  list.className = 'engine-items'
  if (!models || models.length === 0) {
    const note = document.createElement('p')
    note.className = 'model-empty'
    note.textContent = 'No models available.'
    list.appendChild(note)
  } else {
    models.forEach((model) => {
      const label = document.createElement('label')
      label.className = 'model-row'
      const input = document.createElement('input')
      input.type = 'checkbox'
      input.className = 'model-checkbox'
      input.value = model
      input.setAttribute('data-engine', engineName)
      const text = document.createElement('span')
      text.className = 'model-label'
      text.textContent = formatModelName(model)
      label.appendChild(input)
      label.appendChild(text)
      list.appendChild(label)
    })
  }
  engineContent.appendChild(list)
}

// Attach change listeners to the model checkboxes, then keep the selection
// in sync with the server (the server stores per-engine selected models and a
// single active model name).
function attachModelListeners() {
  const checkboxes = document.querySelectorAll('.model-checkbox')
  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', () => setSelectedModels())
  })
  const selectAll = document.querySelector('.global-select-all')
  if (selectAll) {
    selectAll.addEventListener('change', () => toggleSelectAllModels(selectAll))
  }
}

// Render the global "Select all models" checkbox (plus its label) above the
// engine/model list. The checkbox lives in ``#engine-list`` (dashboard.html),
// but ``loadModels()`` clears that container's innerHTML on every view switch,
// so it must be re-created here on every render. It uses a distinct class
// (``global-select-all``) so it is never counted as an individual model.
function renderSelectAllCheckbox(container) {
  const checkbox = document.createElement('input')
  checkbox.type = 'checkbox'
  checkbox.className = 'global-select-all'
  checkbox.id = 'all-models-checkbox'
  checkbox.setAttribute('aria-label', 'Select all models')
  const label = document.createElement('label')
  label.className = 'model-checkbox-group'
  label.appendChild(checkbox)
  const count = document.createElement('span')
  count.className = 'model-label'
  label.appendChild(count)
  container.appendChild(label)
  return checkbox
}

// Keep the global checkbox's checked/indeterminate state in sync with the
// individual model checkboxes. ``checkboxes`` must be the individual model
// checkboxes only (i.e. excluding the ``.global-select-all`` global checkbox).
function syncSelectAll(checkbox) {
  const checkboxes = Array.from(document.querySelectorAll('.model-checkbox'))
  const total = checkboxes.length
  const selected = checkboxes.filter((cb) => cb.checked).length
  checkbox.indeterminate = total > 0 && selected > 0 && selected < total
  checkbox.checked = total > 0 && selected === total
}

// Select every currently-unselected model, mirroring setSelectedModels.
function selectAllModels() {
  const checkboxes = document.querySelectorAll('.model-checkbox')
  const models = []
  const engineModels = {}
  for (const cb of checkboxes) {
    cb.checked = true
    models.push(cb.value)
    const engine = cb.getAttribute('data-engine')
    if (!engineModels[engine]) engineModels[engine] = []
    engineModels[engine].push(cb.value)
  }
  window.__selectedModels = models
  window.__engineModels = engineModels
  const active = models.length ? models[0] : ''
  window.__activeModel = active
  state.activeModel = active
  syncSelectAll(document.querySelector('.global-select-all'))
}

// Clear every model selection.
function deselectAllModels() {
  const checkboxes = document.querySelectorAll('.model-checkbox')
  for (const cb of checkboxes) cb.checked = false
  window.__selectedModels = []
  window.__engineModels = {}
  window.__activeModel = ''
  state.activeModel = ''
  syncSelectAll(document.querySelector('.global-select-all'))
}

// Toggle the global checkbox: check selects all unselected models, uncheck
// clears the selection. Re-syncs the global state afterwards.
function toggleSelectAllModels(checkbox) {
  if (checkbox.checked) selectAllModels()
  else deselectAllModels()
  syncSelectAll(checkbox)
}

// Update the "All Models (N)" count label after the model list renders.
function updateSelectAllCount() {
  const total = document.querySelectorAll('.model-checkbox').length
  const label = document.querySelector('.global-select-all')
  if (label) {
    const span = label.querySelector('.model-label')
    if (span) span.textContent = total ? `All Models (${total})` : 'All Models'
  }
}

// Write the current selection into the shared module globals.
function setSelectedModels() {
  const models = []
  const engineModels = {}
  for (const checkbox of document.querySelectorAll('.model-checkbox')) {
    const model = checkbox.value
    const engine = checkbox.getAttribute('data-engine')
    if (!engineModels[engine]) engineModels[engine] = []
    engineModels[engine].push(model)
    models.push(model)
  }
  window.__selectedModels = models
  window.__engineModels = engineModels
  const active = models.length ? models[0] : ''
  window.__activeModel = active
  state.activeModel = active
  syncSelectAll(document.querySelector('.global-select-all'))
}

// Build a run request payload from the active model & selection.
function buildRunRequest(model) {
  const request = { model }
  if (window.__selectedModels && window.__selectedModels.length > 0) {
    request.model_names = window.__selectedModels
  }
  return request
}

// Serialize the selection for the form-data field (comma-joined names).
function serializeSelectedModels() {
  const names = window.__selectedModels || []
  return names.length ? names.join(',') : ''
}

// Fetch engine config from the API. ``engines`` is an array of
// { name, base_url }. Mirrors the original ``loadEngines`` (main.js L24-49).
async function loadEngines() {
  if (!('fetch' in window)) return state.engines || []
  try {
    const res = await fetch('/api/config/engines')
    const data = await res.json()
    state.engines = data.engines || []
  } catch (e) {
    state.engines = state.engines || []
  }
  return state.engines || []
}

// --- Challenge State Management ---

/**
 * Fetches and populates the list of available challenges.
 * Assumes an API endpoint /api/challenges exists.
 * @returns {Promise<Array<string>>} An array of challenge IDs/names.
 */
async function loadChallenges() {
  if (state.challenges && state.challenges.length) return state.challenges
  try {
    // Assuming a simple GET endpoint for all challenge IDs/names
    const resp = await fetch('/api/challenges')
    const data = await resp.json()
    // Assuming data.challenges is an array of strings (IDs or names)
    state.challenges = data.challenges || []
    return state.challenges
  } catch (e) {
    console.error('Failed to load challenges:', e)
    return []
  }
}

/**
 * Renders the checkboxes for all available challenges.
 * @param {HTMLElement} container - The DOM element to append the checkboxes to.
 * @param {Array<string>} challenges - The list of challenge IDs/names.
 */
function renderChallengeCheckboxes(container, challenges) {
  container.innerHTML = ''
  if (!challenges || challenges.length === 0) {
    const note = document.createElement('p')
    note.className = 'challenge-empty'
    note.textContent = 'No challenges available.'
    container.appendChild(note)
    return
  }
  
  // Simplified rendering: assumes challenge names are displayable.
  // In a real scenario, this would use data structures from state.challenges.
  challenges.forEach((challengeId) => {
    const label = document.createElement('label')
    label.className = 'challenge-row'
    const input = document.createElement('input')
    input.type = 'checkbox'
    input.className = 'challenge-checkbox'
    input.value = challengeId
    input.setAttribute('data-key', challengeId) // Use a data attribute for identification
    const text = document.createElement('span')
    text.className = 'challenge-label'
    // For simplicity, using ID as name display
    text.textContent = challengeId.charAt(0).toUpperCase() + challengeId.slice(1).replace(/[-_]/g, ' ')
    label.appendChild(input)
    label.appendChild(text)
    container.appendChild(label)
  })
}

/**
 * Attaches change listeners to the challenge checkboxes and handles state updates.
 * Also handles the global "Select all" checkbox if present.
 */
function attachChallengeListeners() {
  const checkboxes = document.querySelectorAll('.challenge-checkbox')
  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', () => setSelectedChallenges())
  })
  
  // Assuming a global selector for all challenges exists in the HTML structure
  const selectAll = document.querySelector('.global-select-all-challenge')
  if (selectAll) {
    selectAll.addEventListener('change', () => toggleSelectAllChallenges(selectAll))
  }
}

/**
 * Global selection synchronization for challenges.
 * @param {HTMLInputElement} checkbox - The global select all checkbox.
 */
function syncSelectAllChallenges(checkbox) {
  const checkboxes = Array.from(document.querySelectorAll('.challenge-checkbox'))
  const total = checkboxes.length
  const selected = checkboxes.filter((cb) => cb.checked).length
  checkbox.indeterminate = total > 0 && selected > 0 && selected < total
  checkbox.checked = total > 0 && selected === total
}

/**
 * Selects every currently-unselected challenge, mirroring setSelectedChallenges.
 */
function selectAllChallenges() {
  const checkboxes = document.querySelectorAll('.challenge-checkbox')
  const challenges = []
  const challengeMap = {}
  for (const cb of checkboxes) {
    cb.checked = true
    challenges.push(cb.value)
    const key = cb.getAttribute('data-key')
    if (!challengeMap[key]) challengeMap[key] = []
    challengeMap[key].push(cb.value)
  }
  window.__selectedChallenges = challenges
  window.__challengeMap = challengeMap
  const active = challenges.length ? challenges[0] : ''
  window.__activeChallenge = active
  state.activeChallenge = active
  syncSelectAllChallenges(document.querySelector('.global-select-all-challenge'))
}

/**
 * Clears every challenge selection.
 */
function deselectAllChallenges() {
  const checkboxes = document.querySelectorAll('.challenge-checkbox')
  for (const cb of checkboxes) cb.checked = false
  window.__selectedChallenges = []
  window.__challengeMap = {}
  window.__activeChallenge = ''
  state.activeChallenge = ''
  syncSelectAllChallenges(document.querySelector('.global-select-all-challenge'))
}

/**
 * Toggles the global challenge checkbox and re-syncs the global state.
 */
function toggleSelectAllChallenges(checkbox) {
  if (checkbox.checked) selectAllChallenges()
  else deselectAllChallenges()
  syncSelectAllChallenges(checkbox)
}

/**
 * Writes the current challenge selection into the shared module globals.
 */
function setSelectedChallenges() {
  const challenges = []
  const challengeMap = {}
  for (const checkbox of document.querySelectorAll('.challenge-checkbox')) {
    const challenge = checkbox.value
    const key = checkbox.getAttribute('data-key')
    if (!challengeMap[key]) challengeMap[key] = []
    challengeMap[key].push(challenge)
    challenges.push(challenge)
  }
  window.__selectedChallenges = challenges
  window.__challengeMap = challengeMap
  const active = challenges.length ? challenges[0] : ''
  window.__activeChallenge = active
  state.activeChallenge = active
  syncSelectAllChallenges(document.querySelector('.global-select-all-challenge'))
}

/**
 * Builds a run request payload from the active challenge & selection.
 * @param {string} challengeId - The ID of the active challenge.
 * @returns {object} The request payload.
 */
function buildChallengeRunRequest(challengeId) {
  const request = { challengeId }
  if (window.__selectedChallenges && window.__selectedChallenges.length > 0) {
    request.challenge_ids = window.__selectedChallenges
  }
  return request
}

/**
 * Serializes the selection for the form-data field (comma-joined IDs).
 */
function serializeSelectedChallenges() {
  const ids = window.__selectedChallenges || []
  return ids.length ? ids.join(',') : ''
}

// --- Initialization and Refresh ---

// Runs both model and challenge loading.
async function refreshAll() {
  const button = document.getElementById('refresh-models')
  if (button) button.disabled = true
  try {
    // 1. Load Models
    await loadEngines()
    await loadModels()
    
    // 2. Load Challenges
    const challenges = await loadChallenges()
    const challengeContainer = document.getElementById('challenge-list-container') // Assuming an ID for the container
    if (challengeContainer) {
        renderChallengeCheckboxes(challengeContainer, challenges)
        attachChallengeListeners()
    }
  } catch (error) {
    console.error('Error refreshing entire benchmark state:', error)
  } finally {
    if (button) button.disabled = false
  }
}

export {
  engineBaseURL,
  loadModels,
  formatModelName,
  renderModelCheckboxes,
  attachModelListeners,
  setSelectedModels,
  toggleSelectAllModels,
  selectAllModels,
  deselectAllModels,
  renderSelectAllCheckbox,
  syncSelectAll,
  buildRunRequest,
  serializeSelectedModels,
  loadEngines,
  loadChallenges,
  renderChallengeCheckboxes,
  attachChallengeListeners,
  setSelectedChallenges,
  toggleSelectAllChallenges,
  selectAllChallenges,
  buildChallengeRunRequest,
  serializeSelectedChallenges,
  refreshAll,
}
