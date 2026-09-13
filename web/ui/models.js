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

// Fetch and render the model checkboxes for each engine section.
// Idempotent: the target container is cleared first so the function is safe to
// call on every view switch (which rebinds ``modelList`` to the active panel).
// Returns early when there is no container to populate.
async function loadModels() {
  try {
    if (!modelList) return
    modelList.innerHTML = ''
    modelList.classList.add('loading')
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

      const engineModels = []
      (async () => {
        try {
          const resp = await fetch('/api/models?base_url=' + encodeURIComponent(engine.base_url), {
            method: 'POST',
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

      modelList.appendChild(engineContent)
    }
    attachModelListeners()
  } catch (e) {
    console.error('Error loading models:', e)
  } finally {
    if (modelList) modelList.classList.remove('loading')
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

// Refresh the side menu by reloading the engines from the config API and
// re-fetching every engine's model list from the remote engines.
async function refreshAll() {
  const button = document.getElementById('refresh-models')
  if (button) button.disabled = true
  try {
    await loadEngines()
    await loadModels()
  } catch (error) {
    console.error('Error refreshing engines:', error)
  } finally {
    if (button) button.disabled = false
  }
}

let modelList // rebound to the active engine-list panel inside switchView()

export {
  engineBaseURL,
  loadModels,
  formatModelName,
  renderModelCheckboxes,
  attachModelListeners,
  setSelectedModels,
  buildRunRequest,
  serializeSelectedModels,
  loadEngines,
  refreshAll,
}
