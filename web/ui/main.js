import { loadChallenges } from './challenges.js'
import { loadModels } from './models.js'
import state from './state.js'
import { initializeViewSwitcher } from './views.js'

// 1. Hydrate state
state.selectedModels = window.__selectedModels || []
state.selectedEngine = window.__selectedEngine || ''
state.engineModels = window.__engineModels || {}
state.activeModel = window.__activeModel || ''
state.engines = window.__engines || []
state.tasks = window.__tasks || []
window.__tasks = [] 

// 2. Direct initialization using top-level await
initializeViewSwitcher()

await Promise.all([
  loadModels(),
  loadChallenges()
])
