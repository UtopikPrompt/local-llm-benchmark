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
//
// NOTE: the model/results containers live ONLY in the benchmark panel, so they
// must be rebound to the active panel on EVERY switch — including the very first
// one performed by ``initializeViewSwitcher``. If this is skipped, ``state.engineListContainer``
// / ``state.resultsContainer`` stay bound to the (wrong) initial panel and
// ``loadModels``/``displayResults`` silently fail.
function switchView(viewName) {
  state.activeView = viewName
  VIEWS.forEach((v) => {
    const tab = dom.getEl(document, `#header-nav [data-view="${v}"]`)
    if (tab) {
      if (v === viewName) {
        tab.classList.add('active')
      } else {
        tab.classList.remove('active')
      }
    }
    const panel = dom.getEl(document, `#content-area .view-panel[data-view="${v}"]`)
    if (panel) panel.style.display = v === viewName ? '' : 'none'
  })

  // Bind the containers to every panel. The engine-list and results containers
  // live in the "benchmark" panel, so this keeps state.engineListContainer /
  // state.resultsContainer pointing at them regardless of which view is active
  // (e.g. the dashboard, which has neither). Binding only the active panel
  // skips loadModels() / displayResults() on initial load when the dashboard
  // is the default view.
  VIEWS.forEach((v) => {
    const panel = dom.getEl(document, `#content-area .view-panel[data-view="${v}"]`)
    if (panel) {
      state.engineListContainer = panel.querySelector('#engine-list')
      state.resultsContainer = panel.querySelector('#results-container')
    }
  })
}

// Re-run loadModels against the freshly rebound ``modelList``.
function reloadModels() {
  // Only attempt to reload if the container is actually present.
  if (state.engineListContainer) {
    loadModels()
  } else {
    console.warn("Cannot reload models: Engine list container is null.")
  }
}
// ...existing code...

/**
 * Manages the visibility and state of the main views (dashboard, benchmark, challenges).
 * Attaches view change listeners once and ensures the view state is correct.
 */
function initializeViewSwitcher() {
  // Use a global check on the document body's data attribute to ensure setup runs only once.
  if (document.body.dataset.viewSwitcherInitialized === 'true') {
    console.warn("View switcher initialization already completed. Skipping setup.");
    return;
  }

  // 1. Attach Listeners to all navigation tabs
  const navTabs = document.querySelectorAll("#header-nav .nav-tab");
  for (const tab of navTabs) {
    tab.addEventListener("click", () => switchView(tab.getAttribute("data-view")));
  }
  
  // 2. Set the flag indicating setup is complete
  document.body.dataset.viewSwitcherInitialized = 'true';
  
  // 3. Run initial view state
  switchView(state.activeView || "dashboard");
}

// The container targets are rebound to the active panel inside ``switchView``
// and shared via the ``state`` object (see ``models.js`` / ``results.js``).

export { VIEWS, switchView, reloadModels, initializeViewSwitcher }
