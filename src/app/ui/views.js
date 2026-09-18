import dom from './dom.js'
import state from './state.js'
import { loadModels } from './models.js'
import { loadEngines } from './models.js'
import { loadChallenges } from './challenges.js'

export const VIEWS = ['dashboard', 'benchmark', 'challenges']

export async function switchView(viewName) {
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
  
  // NEW: Coordination of state loading based on active view
  if (viewName === 'benchmark') {
    // Load and render both models, engines, and challenges when on the benchmark dashboard
    await loadModels()
    await loadEngines()
    await loadChallenges()
  } else if (viewName === 'challenges') {
    // If the dedicated 'challenges' view is active, load challenges first.
    loadChallenges()
  }
  
  // Update run button state after setting up containers and loading state
  updateRunButtonState()
}

export function reloadModels() {
  // Renamed to refreshBenchmarkState to coordinate both systems
  refreshBenchmarkState()
}

/**
 * Orchestrates the refresh of all benchmark related state: Models, Engines, and Challenges.
 */
async function refreshBenchmarkState() {
    await loadModels()
    await loadEngines()
    await loadChallenges()
    // Update view state buttons after all loads are complete
    updateRunButtonState()
}

/**
 * Adds a new custom engine definition via the API.
 * Fields: name, base_url, model, timeout, max_concurrent.
 * Opens the engine CRUD modal and populates its fields.
 */
async function handleAddEngineClick() {
    const modal = getEngineModal()
    if (!modal) return
    document.getElementById('engine-name').value = 'New Custom Engine'
    document.getElementById('engine-base-url').value = ''
    document.getElementById('engine-model').value = ''
    showEngineModal(modal)
}

/**
 * Handles saving or updating an engine definition (Create/Update).
 */
async function handleSaveEngine() {
    const name = document.getElementById('engine-name')?.value.trim()
    const base_url = document.getElementById('engine-base-url')?.value.trim()
    const model = document.getElementById('engine-model')?.value.trim()

    if (!name) {
        alert("Engine name is required.")
        return
    }

    try {
        const res = await fetch('/api/config/engines', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_url, model })
        })
        const text = await res.text()
        console.log('API response text:', text)
        if (!res.ok) {
            const errorData = JSON.parse(text)
            alert(`Failed to add engine: ${JSON.stringify(errorData) || 'unknown error'}`)
            return
        }
        alert(`Engine "${name}" added successfully.`)
        hideEngineModal()
        await refreshBenchmarkState()
    } catch (e) {
        alert(`Error adding engine: ${e.message}`)
    }
}

/**
 * Handles deleting an engine definition (Delete).
 */
async function handleDeleteEngine() {
    const id = document.getElementById('engine-id')?.value.trim()
    if (confirm(`WARNING: Are you sure you want to DELETE the engine with ID: ${id}? This action cannot be undone.`)) {
        try {
            const res = await fetch(`/api/config/engines/${id}`, { method: 'DELETE' })
            const data = await res.json()
            if (!res.ok) {
                alert(`Failed to delete engine: ${data.detail || 'unknown error'}`)
                return
            }
            alert(`Engine "${id}" deleted successfully.`)
            hideEngineModal()
            await refreshBenchmarkState()
        } catch (e) {
            alert(`Error deleting engine: ${e.message}`)
        }
    }
}

/**
 * Returns the engine CRUD modal, creating it if it doesn't exist.
 */
function getEngineModal() {
    const modalId = 'engine-crud-modal'
    let modal = document.getElementById(modalId)
    if (!modal) {
        modal = document.createElement('div')
        modal.id = modalId
        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 2000; backdrop-filter: blur(4px);'
        modal.innerHTML = `
            <div class="engine-modal-card">
                <h4 class="engine-modal-title">Manage Engine Definition</h4>
                <p class="engine-modal-description">This view handles Create, Read, Update, and Delete operations for custom engines.</p>
                
                <div class="engine-form-group">
                    <label class="engine-form-label" for="engine-name">Engine Name</label>
                    <input type="text" class="engine-form-control engine-name-input" id="engine-name" value="New Custom Engine">
                </div>
                <div class="engine-form-group">
                    <label class="engine-form-label" for="engine-base-url">Base URL</label>
                    <input type="text" class="engine-form-control engine-base-url-input" id="engine-base-url" value="">
                </div>
                <div class="engine-form-group">
                    <label class="engine-form-label" for="engine-model">Model</label>
                    <input type="text" class="engine-form-control engine-model-input" id="engine-model" value="">
                </div>
                
                <div class="engine-buttons">
                    <button class="engine-btn engine-btn-save" id="save-engine-btn-widget">Save/Update</button>
                    <button class="engine-btn engine-btn-delete" id="delete-engine-btn-widget">Delete</button>
                    <button class="engine-btn engine-btn-cancel" id="cancel-engine-btn-widget">Cancel</button>
                </div>
            </div>
        `
        document.body.appendChild(modal)
    }
    return modal
}

/**
 * Shows the engine CRUD modal.
 */
function showEngineModal(modal) {
    modal.style.display = 'flex'
    document.getElementById('save-engine-btn-widget')?.addEventListener('click', handleSaveEngine)
    document.getElementById('delete-engine-btn-widget')?.addEventListener('click', handleDeleteEngine)
    document.getElementById('cancel-engine-btn-widget')?.addEventListener('click', hideEngineModal)
}

/**
 * Hides the engine CRUD modal.
 */
function hideEngineModal() {
    const modal = document.getElementById('engine-crud-modal')
    if (modal) modal.style.display = 'none'
}

/**
 * Checks the current model and challenge selection state and updates the disabled status
 * and message of the primary run button.
 * @param {HTMLElement} button The run button element to check.
 */
function updateRunButtonState(button) {
  const hasModels = state.selectedModels && state.selectedModels.length > 0
  const hasChallenges = state.selectedChallenges && state.selectedChallenges.length > 0
  
  // Button is disabled if we are missing models OR missing challenges.
  const disabled = !hasModels || !hasChallenges
  const buttons = button
    ? [button]
    : Array.from(document.querySelectorAll('#run-challenge-batch-button'))

  buttons.forEach((btn) => {
    if (btn) btn.disabled = disabled
  })
  
  const messageEl = document.getElementById('model-status-message');
  if (messageEl) {
    if (disabled) {
      let message = "Please select models and challenges to run the benchmark.";
      if (!hasModels && !hasChallenges) {
        message = "Select a model to run the benchmark.";
      } else if (!hasChallenges && hasModels) {
        message = `Selected ${state.selectedModels.length} model(s). Please select at least one challenge to run.`;
      } else if (hasModels && !hasChallenges) {
        message = `Selected ${state.selectedModels.length} model(s). Please select at least one challenge to run.`;
      }
      messageEl.textContent = message;
      messageEl.style.display = 'block';
    } else {
      messageEl.textContent = `Ready to run ${state.selectedModels.length} model(s) across ${state.selectedChallenges.length} challenge(s).`;
      messageEl.style.display = 'block';
    }
  }
}

// Named function for explicit initialization control
function initializeViewSwitcher() {
  // Event delegation setup
  document.querySelector("#header-nav")?.addEventListener("click", (e) => {
    const tab = e.target.closest(".nav-tab")
    if (tab) {
      switchView(tab.getAttribute("data-view"))
    }
  })

  // Wire the "Add Engine" button (defined in dashboard.html) to the engine
  // CRUD modal. Only active while the benchmark panel is shown.
  const addEngineBtn = document.getElementById("add-engine")
  if (addEngineBtn) {
    addEngineBtn.addEventListener("click", handleAddEngineClick)
  }

  // Establish initial view state
  switchView(state.activeView || "dashboard")
  // Re-calling this at the end of the file to ensure the initial state is checked
  updateRunButtonState()
}

export {
  initializeViewSwitcher,
}