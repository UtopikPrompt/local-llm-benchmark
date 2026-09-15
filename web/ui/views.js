import dom from './dom.js'
import state from './state.js'
import { loadModels } from './models.js'

export const VIEWS = ['dashboard', 'benchmark', 'challenges']

export function switchView(viewName) {
  state.activeView = viewName

  VIEWS.forEach((v) => {
    // 1. Toggle Tab Styling
    const tab = dom.getEl(document, `#header-nav [data-view="${v}"]`)
    tab?.classList.toggle('active', v === viewName)

    // 2. Toggle Panel Visibility
    const panel = dom.getEl(document, `#content-area .view-panel[data-view="${v}"]`)
    if (panel) {
      panel.style.display = v === viewName ? '' : 'none'
    }
  })

  // 3. Bind elements strictly from the benchmark panel
  const benchmarkPanel = dom.getEl(document, `#content-area .view-panel[data-view="benchmark"]`)
  if (benchmarkPanel) {
    state.engineListContainer = benchmarkPanel.querySelector('#engine-list')
    state.resultsContainer = benchmarkPanel.querySelector('#results-container')
  }
}

export function reloadModels() {
  if (state.engineListContainer) {
    loadModels()
  } else {
    console.warn("Cannot reload models: Engine list container is missing from the benchmark panel.")
  }
}

// Named function for explicit initialization control
export function initializeViewSwitcher() {
  // Event delegation setup
  document.querySelector("#header-nav")?.addEventListener("click", (e) => {
    const tab = e.target.closest(".nav-tab")
    if (tab) {
      switchView(tab.getAttribute("data-view"))
    }
  })

  // Establish initial view state
  switchView(state.activeView || "dashboard")
}
