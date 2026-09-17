// app.js — entry point. Wires up the application initialization.
// Mirrors the original app.js entry point.

import { loadModels, loadEngines } from './models.js'
import { loadBenchmarkResults } from './results.js'
import { loadChallenges } from './challenges.js'
import { initializeViewSwitcher } from './views.js'

initializeViewSwitcher()

await Promise.all([
  // Hydration: no persisted globals exist, so `state` holds defaults.
  loadModels(),
  loadEngines(),
  loadChallenges(),
  loadBenchmarkResults()
])
