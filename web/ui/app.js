// app.js — entry point. Wires up the application initialization.
// Mirrors the original app.js entry point.

import { loadModels } from './models.js'
import state from './state.js'
import { loadBenchmarkResults } from './results.js'
import { loadChallenges } from './challenges.js'
import { initializeViewSwitcher, switchView } from './views.js'

(async () => {
  state.selectedModels = window.__selectedModels || []
  state.selectedEngine = window.__selectedEngine || ''
  state.engineModels = window.__engineModels || {}
  state.activeModel = window.__activeModel || ''
  state.engines = window.__engines || []
  state.tasks = window.__tasks || []
  window.__tasks = []

  await initializeViewSwitcher()
  await loadModels()
  await loadChallenges()
  await loadBenchmarkResults()
})()
