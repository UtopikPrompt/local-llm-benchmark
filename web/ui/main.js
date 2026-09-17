import { loadChallenges } from './challenges.js'
import { loadModels } from './models.js'
import state from './state.js'
import { initializeViewSwitcher } from './views.js'

// 1. Hydrate state
// Hydration: no persisted globals exist, so the imported `state` holds defaults.

// 2. Direct initialization using top-level await
initializeViewSwitcher()

await Promise.all([
  loadModels(),
  loadChallenges()
])
