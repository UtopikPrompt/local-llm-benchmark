// app.js — entry point. Wires up the DOMContentLoaded bootstrap, initializes
// selection state from the window.__* globals and starts the benchmark.
// Mirrors the original main.js entry point.

import { loadModels, refreshAll } from './models.js'
import state from './state.js'
import { loadBenchmarkResults } from './results.js'
import { loadChallenges } from './challenges.js'
import { initializeListeners, switchView } from './views.js'

function init() {
  state.selectedModels = window.__selectedModels || []
  state.selectedEngine = window.__selectedEngine || ''
  state.engineModels = window.__engineModels || {}
  state.activeModel = window.__activeModel || ''
  state.engines = window.__engines || []
  state.tasks = window.__tasks || []
  window.__tasks = []
  switchView()
  initializeListeners()
  loadChallenges()
  loadBenchmarkResults()
}

document.addEventListener('DOMContentLoaded', init)
