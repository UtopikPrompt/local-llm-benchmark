import dom from './dom.js'
import state from './state.js'
import { loadModels } from './models.js'
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
 * Loads and renders the available engine list in the UI.
 */
async function loadEngines() {
    // Placeholder for actual engine fetching logic (e.g., API call)
    // Simulate loading data.
    await new Promise(resolve => setTimeout(resolve, 50)); 
    
    const container = state.engineListContainer
    if (!container) {
        console.warn("Engine list container (#engine-list) not found in benchmark panel.");
        return;
    }
    
    // Clearing and re-populating dummy content for demonstration.
    container.innerHTML = ''; 
    
    // In a real application, this would fetch from a service.
    const dummyEngines = [
        { id: 'openai_compat', name: 'OpenAI Compatible Engine', selected: true },
        { id: 'local_llm', name: 'Local LLM Benchmark Engine', selected: false }
    ]
    
    state.allEngines = dummyEngines
    state.selectedEngines = dummyEngines.filter(e => e.selected).map(e => e.id)

    // Simple rendering logic for demonstration
    const engineOptionsHtml = `
        <div class="form-check form-engine-selection mb-3">
            <input class="form-check-input" type="checkbox" id="engine-openai_compat" checked data-engine-id="openai_compat">
            <label class="form-check-label" for="engine-openai_compat">
                OpenAI Compatible Engine
            </label>
        </div>
        <div class="form-check form-engine-selection mb-3">
            <input class="form-check-input" type="checkbox" id="engine-local_llm" data-engine-id="local_llm">
            <label class="form-check-label" for="engine-local_llm">
                Local LLM Benchmark Engine
            </label>
        </div>
        <button class="btn btn-secondary mt-3" id="add-engine-btn">
            + Add Custom Engine
        </button>
    `.trim();

    container.innerHTML = engineOptionsHtml;

    // Attach event listeners to the new elements
    container.querySelectorAll('.form-check-input').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const engineId = e.target.getAttribute('data-engine-id');
            const isChecked = e.target.checked;

            if (isChecked) {
                if (!state.selectedEngines.includes(engineId)) {
                    state.selectedEngines.push(engineId);
                }
            } else {
                state.selectedEngines = state.selectedEngines.filter(id => id !== engineId);
            }
            updateRunButtonState();
        });
    });
    
    // Attach listener for Add Engine button
    document.getElementById('add-engine-btn')?.addEventListener('click', handleAddEngineClick);
}

/**
 * Placeholder handler for adding a new engine.
 * This function now simulates triggering a dedicated modal/view for engine CRUD operations.
 */
function handleAddEngineClick() {
    console.log("--- ENGINE CRUD Workflow Triggered ---");
    
    // 1. Simulate opening a Modal/Dedicated View
    const modalId = 'engine-crud-modal';
    let modal = document.getElementById(modalId);
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000;';
        modal.innerHTML = `
            <div class="card p-4" style="width: 400px; background: white;">
                <h4 class="card-title">Manage Engine Definition</h4>
                <p class="card-text">This view handles Create, Read, Update, and Delete operations for custom engines.</p>
                
                <div class="form-group mb-3">
                    <label for="engine-name">Engine Name (Read)</label>
                    <input type="text" class="form-control engine-name-input" id="engine-name" value="New Custom Engine">
                </div>
                <div class="form-group mb-3">
                    <label for="engine-id">Unique ID (Read)</label>
                    <input type="text" class="form-control engine-id-input" id="engine-id" value="custom_engine_abc" readonly>
                </div>
                <div class="form-group mb-3">
                    <label for="engine-type">Engine Type (Read)</label>
                    <select class="form-control" id="engine-type">
                        <option>LLM Provider</option>
                        <option>Local Benchmarker</option>
                        <option>External API</option>
                    </select>
                </div>
                
                <button class="btn btn-success me-2" id="save-engine-btn-widget">Save/Update</button>
                <button class="btn btn-danger" id="delete-engine-btn-widget">Delete</button>
            </div>
        `;
        document.body.appendChild(modal);
    } else {
        modal.style.display = 'flex';
    }

    // Attach save listener
    document.getElementById('save-engine-btn-widget')?.addEventListener('click', handleSaveEngine);
    // Attach delete listener
    document.getElementById('delete-engine-btn-widget')?.addEventListener('click', handleDeleteEngine);
}

/**
 * Handles saving or updating an engine definition (Create/Update).
 */
function handleSaveEngine() {
    const id = document.getElementById('engine-id');
    const name = document.getElementById('engine-name');
    
    if (!id || !name) {
        alert("Engine ID and Name are required.");
        return;
    }
    
    console.log(`[API CALL] Attempting to CREATE or UPDATE engine: ID=${id.value}, Name=${name.value}`);
    
    // Simulate API call and success
    alert(`[SUCCESS] Engine Definition saved/updated: ${name.value} (ID: ${id.value}). The system will now re-read engine configurations.`);
    
    // Trigger a state refresh to reflect the new engine
    refreshBenchmarkState(); 
}

/**
 * Handles deleting an engine definition (Delete).
 */
function handleDeleteEngine() {
    const id = document.getElementById('engine-id').value;
    if (confirm(`WARNING: Are you sure you want to DELETE the engine with ID: ${id}? This action cannot be undone.`)) {
        console.log(`[API CALL] Attempting to DELETE engine: ID=${id}`);
        
        // Simulate API call and success
        alert(`[SUCCESS] Engine Definition deleted for ID: ${id}. The system will now re-read engine configurations.`);
        
        // Trigger a state refresh to reflect the deletion
        refreshBenchmarkState();
    }
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
  // Re-calling this at the end of the file to ensure the initial state is checked
  updateRunButtonState()
}
