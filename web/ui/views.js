// views.js — tab switching & listener wiring.
// Mirrors the original main.js switchView / initializeListeners.
//
// NOTE: ``modelList``/``resultsContainer`` are NOT document.getElementById()
// targets — getElementById returns the FIRST match (the hidden Dashboard
// panel), so switchView() rebinds them to the active panel's container.

import dom from './dom.js'
import state from './state.js'
import { loadModels, loadEngines } from './models.js'
import { toggleCategoryFilter, loadChallenges } from './challenges.js'

// Ordered list of views. Mirrors the ``data-view`` attributes on the nav
// tabs (``dashboard`` / ``benchmark`` / ``challenges``) in dashboard.html.
const VIEWS = ['dashboard', 'benchmark', 'challenges']

// Switch to the given view: update active-tab styling, toggle panel visibility
// and rebind the model/results containers to the active panel.
function switchView(viewName) {
  state.activeView = viewName
  VIEWS.forEach((v) => {
    const tab = dom.getEl(document, `[data-view="${v}"]`)
    if (tab) {
      if (v === viewName) {
        tab.classList.add('active')
      } else {
        tab.classList.remove('active')
      }
    }
    const panel = dom.getEl(document, `[data-view="${v}"]`)
    if (panel) panel.style.display = v === viewName ? '' : 'none'
  })

  const panel = document.querySelector(`#content-area .view-panel[data-view="${viewName}"]`)
  if (panel) {
    modelList = panel.querySelector('#engine-list')
    resultsContainer = panel.querySelector('#results-container')
  }
}

// Re-run loadModels against the freshly rebound ``modelList``.
function reloadModels() {
  if (modelList) loadModels()
}

// Attach tab-click listeners (click -> switchView).
function initializeListeners() {
  switchView(state.activeView || 'dashboard')
  const benchmarkType = dom.getEl(document, '#benchmarkType') || null
  const categoriesEl = dom.getEl(document, '#challenge-categories')
  // Delegated toggle: the module-level toggleCategoryFilter handles the
  // filter state, chip visuals, and applyChallengeFilter() call.
  if (benchmarkType) benchmarkType.addEventListener('change', () => {
    window.__selectedModels = []
    window.__selectedEngine = ''
    window.__engineModels = {}
    loadModels()
  })
  if (categoriesEl) {
    const chips = categoriesEl.querySelectorAll('.chip')
    for (const chip of chips) {
      chip.addEventListener('click', () => toggleCategoryFilter(chip.getAttribute('data-category')))
    }
  }
  for (const tab of document.querySelectorAll('#header-nav .nav-tab')) {
    tab.addEventListener('click', () => switchView(tab.getAttribute('data-view')))
  }
  loadEngines()
  loadModels()
  loadChallenges()
  switchView(window.__activeView || 'dashboard')
}

// Rebound container targets to the active panel (see ``switchView``).
let modelList
let resultsContainer

export { VIEWS, switchView, reloadModels, initializeListeners }
