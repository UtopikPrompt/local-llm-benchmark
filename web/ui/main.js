var __defProp = Object.defineProperty;
var __markAsModule = (target) => __defProp(target, "__esModule", { value: true });
var __require = typeof require !== "undefined" ? require : (x) => {
  throw new Error('Dynamic require of "' + x + '" is not supported');
};
var __esm = (fn, res) => function __init() {
  return fn && (res = (0, fn[Object.keys(fn)[0]])(fn = 0)), res;
};
var __export = (target, all) => {
  __markAsModule(target);
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};

// web/ui/dom.js
var dom_exports = {};
__export(dom_exports, {
  default: () => dom_default
});
var dom, dom_default;
var init_dom = __esm({
  "web/ui/dom.js"() {
    dom = {
      getEl(root, id) {
        return root ? root.querySelector(id) : document.getElementById(id);
      },
      setText(el, text) {
        if (!el)
          return;
        el.textContent = text;
      },
      create(tag, props, children) {
        const el = document.createElement(tag);
        if (props) {
          for (const [key, value] of Object.entries(props)) {
            if (value === void 0)
              continue;
            if (key === "class") {
              el.className = value;
            } else if (key === "html") {
              el.innerHTML = value;
            } else if (key.startsWith("on") && typeof value === "function") {
              el.addEventListener(key.slice(2).toLowerCase(), value);
            } else if (key === "dataset" && typeof value === "object") {
              for (const [k, v] of Object.entries(value))
                el.dataset[k] = v;
            } else if (key === "style" && typeof value === "object") {
              for (const [k, v] of Object.entries(value))
                el.style[k] = v;
            } else if (key === "type" && typeof value === "string") {
              el.setAttribute("type", value);
            } else {
              el.setAttribute(key, value);
            }
          }
        }
        if (children) {
          if (typeof children === "string")
            el.textContent = children;
          else
            for (const c of children)
              el.append(c);
        }
        return el;
      },
      addClass(el, className) {
        if (el)
          el.classList.add(className);
      },
      removeClass(el, className) {
        if (el)
          el.classList.remove(className);
      },
      toggleClass(el, className, force) {
        if (el)
          el.classList.toggle(className, force);
      },
      isVisible(el) {
        return !!el && el.offsetParent !== null && el.offsetParent !== void 0;
      }
    };
    dom_default = dom;
  }
});

// web/ui/state.js
var state_exports = {};
__export(state_exports, {
  default: () => state_default
});
var state, state_default;
var init_state = __esm({
  "web/ui/state.js"() {
    state = {
      selectedModels: [],
      selectedEngine: "",
      engineModels: {},
      activeModel: "",
      engines: [],
      engineListContainer: null,
      resultsContainer: null,
      tasks: [],
      activeView: "",
      resultsRendered: false,
      activeCategory: null
    };
    state_default = state;
  }
});

// web/ui/models.js
var models_exports = {};
__export(models_exports, {
  attachModelListeners: () => attachModelListeners,
  buildRunRequest: () => buildRunRequest,
  engineBaseURL: () => engineBaseURL,
  formatModelName: () => formatModelName,
  loadEngines: () => loadEngines,
  loadModels: () => loadModels,
  refreshAll: () => refreshAll,
  renderModelCheckboxes: () => renderModelCheckboxes,
  serializeSelectedModels: () => serializeSelectedModels,
  setSelectedModels: () => setSelectedModels
});
function engineBaseURL(engineName) {
  const engines = state_default.engines || [];
  const engine = engines.find((e) => e.name === engineName);
  return engine ? engine.base_url : engineName;
}
async function ensureEngines() {
  if (state_default.engines && state_default.engines.length)
    return state_default.engines;
  try {
    const engines = await loadEngines();
    state_default.engines = engines || [];
  } catch (e) {
    console.error("Failed to load engines:", e);
  }
  return state_default.engines || [];
}
async function loadModels() {
  const container = state_default.engineListContainer;
  if (!container) {
    console.warn("loadModels() skipped: Engine list container not found in the current active view.");
    return;
  }
  try {
    await ensureEngines();
    container.innerHTML = "";
    container.classList.add("loading");
    for (const engine of state_default.engines || []) {
      const engineContent = document.createElement("div");
      engineContent.className = "engine-content";
      engineContent.dataset.engine = engine.name;
      const engineTitle = document.createElement("div");
      engineTitle.className = "engine-title";
      engineTitle.textContent = engine.name;
      engineContent.appendChild(engineTitle);
      const heading = document.createElement("button");
      heading.className = "engine-heading";
      const name = document.createElement("span");
      name.className = "engine-heading-text";
      name.textContent = engine.name;
      heading.appendChild(name);
      const toggle = document.createElement("span");
      toggle.className = "engine-chevron";
      toggle.textContent = "\u25BE";
      heading.appendChild(toggle);
      heading.addEventListener("click", () => engineContent.classList.toggle("expanded"));
      const engineModels = [](async () => {
        try {
          const resp = await fetch("/api/models?base_url=" + encodeURIComponent(engine.base_url), {
            method: "POST"
          });
          const data = await resp.json();
          if (data.models) {
            for (const model of data.models)
              engineModels.push(model);
            renderModelCheckboxes(engineContent, engine.name, engineModels);
          } else {
            const note = document.createElement("p");
            note.className = "model-empty";
            note.textContent = "No models available.";
            engineContent.appendChild(note);
          }
        } catch (e) {
          console.error("Failed to load models for", engine.name, e);
        }
      })();
      container.appendChild(engineContent);
    }
    attachModelListeners();
  } catch (e) {
    console.error("Error loading models:", e);
  } finally {
    container.classList.remove("loading");
  }
}
function formatModelName(model) {
  return model.charAt(0).toUpperCase() + model.slice(1).replace(/_/g, " ");
}
function renderModelCheckboxes(engineContent, engineName, models) {
  const list = document.createElement("div");
  list.className = "engine-items";
  if (!models || models.length === 0) {
    const note = document.createElement("p");
    note.className = "model-empty";
    note.textContent = "No models available.";
    list.appendChild(note);
  } else {
    models.forEach((model) => {
      const label = document.createElement("label");
      label.className = "model-row";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.className = "model-checkbox";
      input.value = model;
      input.setAttribute("data-engine", engineName);
      const text = document.createElement("span");
      text.className = "model-label";
      text.textContent = formatModelName(model);
      label.appendChild(input);
      label.appendChild(text);
      list.appendChild(label);
    });
  }
  engineContent.appendChild(list);
}
function attachModelListeners() {
  const checkboxes = document.querySelectorAll(".model-checkbox");
  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", () => setSelectedModels());
  });
}
function setSelectedModels() {
  const models = [];
  const engineModels = {};
  for (const checkbox of document.querySelectorAll(".model-checkbox")) {
    const model = checkbox.value;
    const engine = checkbox.getAttribute("data-engine");
    if (!engineModels[engine])
      engineModels[engine] = [];
    engineModels[engine].push(model);
    models.push(model);
  }
  window.__selectedModels = models;
  window.__engineModels = engineModels;
  const active = models.length ? models[0] : "";
  window.__activeModel = active;
  state_default.activeModel = active;
}
function buildRunRequest(model) {
  const request = { model };
  if (window.__selectedModels && window.__selectedModels.length > 0) {
    request.model_names = window.__selectedModels;
  }
  return request;
}
function serializeSelectedModels() {
  const names = window.__selectedModels || [];
  return names.length ? names.join(",") : "";
}
async function loadEngines() {
  if (!("fetch" in window))
    return state_default.engines || [];
  try {
    const res = await fetch("/api/config/engines");
    const data = await res.json();
    state_default.engines = data.engines || [];
  } catch (e) {
    state_default.engines = state_default.engines || [];
  }
  return state_default.engines || [];
}
async function refreshAll() {
  const button = document.getElementById("refresh-models");
  if (button)
    button.disabled = true;
  try {
    await loadEngines();
    await loadModels();
  } catch (error) {
    console.error("Error refreshing engines:", error);
  } finally {
    if (button)
      button.disabled = false;
  }
}
var init_models = __esm({
  "web/ui/models.js"() {
    init_dom();
    init_state();
  }
});

// web/ui/results.js
var results_exports = {};
__export(results_exports, {
  cls: () => cls,
  displayResults: () => displayResults,
  escapeHtml: () => escapeHtml,
  fmt: () => fmt,
  loadBenchmarkResults: () => loadBenchmarkResults,
  renderResult: () => renderResult,
  runBenchmark: () => runBenchmark,
  updateResultsCount: () => updateResultsCount
});
function fmt(n) {
  if (n === null || n === void 0 || n === "")
    return "\u2014";
  if (Number.isNaN(Number(n)))
    return n;
  return Number(n).toLocaleString(void 0, { maximumFractionDigits: 3 });
}
function cls(value, passClass, failClass, warnClass) {
  if (value === true)
    return '<span class="pill ' + passClass + '">' + value + "</span>";
  if (value === false)
    return '<span class="pill ' + failClass + '">' + value + "</span>";
  if (value === null || value === void 0 || value === "")
    return "";
  return '<span class="pill warn">' + value + "</span>";
}
function renderResult(r) {
  return '<tr><td class="mono" style="color:var(--text-secondary);">' + escapeHtml(r.engine) + '</td><td class="mono" style="color:var(--text-secondary);">' + escapeHtml(r.model) + '</td><td class="pill">' + escapeHtml(r.category) + '</td><td class="mono">' + fmt(r.ttft_s) + '</td><td class="mono">' + fmt(r.tok_per_s) + '</td><td class="mono">' + fmt(r.iters_per_s) + '</td><td class="pill">' + cls(r.quality, "pass", "fail", "warn") + '</td><td class="pill">' + cls(r.qualityJudge, "pass", "fail", "warn") + "</td></tr>";
}
function displayResults(results, modelNames, benchmarkType) {
  if (state_default.selectedModels.length === 0) {
    const resultsContainer2 = state_default.resultsContainer;
    resultsContainer2.innerHTML = "";
    resultsContainer2.appendChild(createRunState());
    return;
  }
  if (!state_default.resultsRendered) {
    return;
  }
  const resultsContainer = state_default.resultsContainer;
  resultsContainer.innerHTML = "";
  const modelList = dom_default.getEl(resultsContainer, "#engine-list");
  resultsContainer.classList.add("rendered");
  modelList.classList.remove("expanded");
  if (modelNames && modelNames.length === 0) {
    resultsContainer.innerHTML = "";
    resultsContainer.appendChild(createRunState());
    return;
  }
  resultsContainer.classList.remove("empty");
  resultsContainer.classList.add("results-rendered");
  const resultsTable = buildResultsTable(results, modelNames, benchmarkType);
  resultsContainer.appendChild(resultsTable);
  wirePerCardStatus(results, modelNames, benchmarkType);
}
function wirePerCardStatus(results, modelNames, benchmarkType) {
  if (!results || modelNames === void 0)
    return;
  const cards = document.querySelectorAll(".challenge-card[data-id]");
  for (const card of cards) {
    const taskId = card.getAttribute("data-id");
    const name = modelNames && modelNames[taskId];
    if (!name)
      continue;
    let anyRow = null;
    for (const r of results) {
      if (r.taskId === taskId) {
        anyRow = r;
        break;
      }
    }
    if (!anyRow)
      continue;
    let status;
    if (anyRow.quality_passed === true)
      status = "pass";
    else if (anyRow.quality_passed === false)
      status = "fail";
    else if (anyRow.quality_passed === null || anyRow.quality_passed === void 0 || anyRow.quality_passed === "") {
      if (anyRow.error)
        status = "error";
      else if (anyRow.qualityJudge)
        status = "judge";
      else
        status = "not-run";
    } else if (anyRow.error) {
      status = "error";
    } else if (anyRow.qualityJudge) {
      status = "judge";
    } else {
      status = "not-run";
    }
    try {
      perCardStatus(taskId, status);
    } catch (e) {
      console.error("perCardStatus failed for task " + taskId, e);
    }
  }
}
function ensureRunState() {
  const panel = document.querySelector('#content-area .view-panel[data-view="' + (state_default.activeView || "benchmark") + '"]');
  if (!panel)
    return null;
  const resultsContainer = dom_default.getEl(panel, "#results-container");
  if (!resultsContainer)
    return null;
  if (runStatePanel && runStatePanel !== panel) {
    runStatePanel.removeEventListener("click", onRunStateClick);
    panel.addEventListener("click", onRunStateClick);
    runStatePanel = panel;
  }
  return [runStateToolbar.querySelector("#run-button"), runStateToolbar.querySelector("#run-note")];
}
function onRunStateClick(event) {
  const target = event.target;
  if (target && target.id === "run-button") {
    runBenchmark();
  }
}
function createRunState() {
  const found = ensureRunState();
  if (!found)
    return null;
  const [runButton, runNote] = found;
  const resultsContainer = state_default.resultsContainer;
  if (resultsContainer)
    resultsContainer.classList.add("run-state");
  const benchmarkType = document.getElementById("benchmarkType");
  runButton.setAttribute("data-benchmark-type", benchmarkType ? benchmarkType.value : "quality");
  if (state_default.selectedModels.length === 0) {
    runNote.textContent = "Select a model to run the benchmark.";
    runButton.classList.add("btn-primary");
    runButton.setAttribute("disabled", "true");
  } else {
    runNote.textContent = "Select at least one model to run a benchmark.";
    runButton.removeAttribute("disabled");
  }
  return runButton;
}
function buildResultsTable(results, modelNames, benchmarkType) {
  const resultsContainer = state_default.resultsContainer;
  const resultsHeader = dom_default.getEl(resultsContainer, "#results-header");
  resultsHeader.textContent = benchmarkType === "latency" ? "Latency results" : "Quality results";
  ensureResultsFilter();
  const resultsTable = dom_default.create("table", { className: "results-table" }, []);
  resultsContainer.appendChild(resultsTable);
  return resultsTable;
}
function ensureResultsFilter() {
  const resultsContainer = state_default.resultsContainer;
  const search = dom_default.getEl(resultsContainer, "#results-search");
  if (!search)
    return;
  const searchEl = search.querySelector("input");
  if (!searchEl) {
    const input = dom_default.create("input", { className: "search", placeholder: "Filter results", type: "text", onInput: filterResults });
    search.appendChild(input);
  } else if (!searchEl.getAttribute("oninput")) {
    searchEl.addEventListener("input", filterResults);
  }
  const clear = dom_default.getEl(resultsContainer, "#results-clear");
  if (clear && !clear.getAttribute("onclick")) {
    clear.addEventListener("click", clearResults);
  }
}
function filterResults() {
  const resultsContainer = state_default.resultsContainer;
  const search = dom_default.getEl(resultsContainer, "#results-search");
  const resultsTable = dom_default.getEl(resultsContainer, ".results-table");
  const filter = search.value.toLowerCase();
  const rows = resultsTable.querySelectorAll("tbody tr");
  for (const row of rows) {
    row.style.display = row.textContent.toLowerCase().includes(filter) ? "" : "none";
  }
}
function clearResults() {
  const resultsContainer = state_default.resultsContainer;
  const search = dom_default.getEl(resultsContainer, "#results-search");
  if (search)
    search.value = "";
  const resultsTable = dom_default.getEl(resultsContainer, ".results-table");
  if (resultsTable)
    resultsTable.querySelectorAll("tbody tr").forEach((row) => {
      row.style.display = "";
    });
  const categories = dom_default.getEl(resultsContainer, "#results-categories");
  if (categories)
    categories.querySelector(".clear").click();
}
function updateResultsCount(visible) {
  const resultsCount = dom_default.getEl(state_default.resultsContainer, "#results-count");
  resultsCount.textContent = visible + " shown";
}
async function loadBenchmarkResults(modelNames) {
  const benchmarkType = document.getElementById("benchmarkType");
  const type = benchmarkType ? benchmarkType.value : "quality";
  const resultsContainer = state_default.resultsContainer;
  const response = await fetch("/api/results?" + new URLSearchParams({ benchmark_type: type, model_names: modelNames || "" }).toString());
  if (!response.ok) {
    resultsContainer.innerHTML = "";
    resultsContainer.appendChild(createRunState());
    return;
  }
  displayResults(await response.json(), modelNames, type);
}
async function runBenchmark() {
  const resultsContainer = state_default.resultsContainer;
  const runButton = resultsContainer.querySelector(".run-button");
  const runNote = resultsContainer.querySelector(".run-note");
  const runButtonEl = runButton || resultsContainer.querySelector("#run-button");
  runButtonEl.setAttribute("disabled", "true");
  runNote.textContent = "Running benchmark\u2026";
  try {
    const response = await fetch("/api/run", { method: "POST", body: JSON.stringify(buildRunRequest(state_default.activeModel)) });
    if (response.ok) {
      const results = await response.json();
      displayResults(results, serializeSelectedModels(), "quality");
    } else {
      const error = await response.json().catch(() => ({}));
      runNote.textContent = "Error: " + (error.detail || error.message || response.statusText);
    }
  } catch (e) {
    runNote.textContent = "Error: " + e.message;
  } finally {
    const runButtonEl2 = runButton || resultsContainer.querySelector("#run-button");
    runButtonEl2.removeAttribute("disabled");
  }
}
function escapeHtml(value) {
  if (value === null || value === void 0)
    return "";
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
}
var runStatePanel, runStateToolbar;
var init_results = __esm({
  "web/ui/results.js"() {
    init_state();
    init_dom();
    init_models();
    init_challenges();
    runStatePanel = null;
    runStateToolbar = null;
  }
});

// web/ui/challenges.js
var challenges_exports = {};
__export(challenges_exports, {
  applyChallengeFilter: () => applyChallengeFilter,
  loadChallenges: () => loadChallenges,
  perCardStatus: () => perCardStatus,
  renderChallengeCard: () => renderChallengeCard,
  toggleCategoryFilter: () => toggleCategoryFilter
});
function renderChallengeCard(task) {
  const card = document.createElement("div");
  card.className = "challenge-card";
  card.setAttribute("data-category", task.category || "");
  card.setAttribute("data-id", task.id);
  const tags = [];
  if (task.system)
    tags.push('<span class="tag">system</span>');
  if (task.expected)
    tags.push('<span class="tag">expected</span>');
  const tagsHtml = tags.join("") || '<span class="tag">prompt</span>';
  card.innerHTML = '<div class="challenge-card-header"><span class="challenge-card-title">' + escapeHtml(task.id) + '</span><span class="chip small">' + escapeHtml(task.category) + '</span></div><div class="challenge-card-body"><p class="challenge-card-prompt">' + escapeHtml(task.prompt) + '</p></div><div class="challenge-card-tags">' + tagsHtml + '</div><div class="challenge-checkboxes"><button class="challenge-checkbox select-all" type="button" aria-pressed="false"><input type="checkbox" class="challenge-checkbox" aria-hidden="true" />select all</button></div><span class="check-count">0/0</span><div class="bench-status"><span class="bench-status-text">Not run</span><div class="bench-progress-bar"><div class="bench-status-bar"></div></div></div>';
  wireChallengeCard(card);
  return card;
}
function wireChallengeCard(card) {
  const selectAll = card.querySelector(".challenge-checkbox select-all .challenge-checkbox");
  const perCard = card.querySelectorAll(".challenge-checkboxes .challenge-checkbox");
  if (selectAll) {
    selectAll.addEventListener("change", () => {
      const checked = selectAll.checked;
      for (const cb of perCard)
        cb.checked = checked;
      syncSelectAll(selectAll, perCard);
      updateCheckCount(card, perCard);
    });
  }
  for (const cb of perCard) {
    cb.addEventListener("change", () => {
      const selectAll2 = card.querySelector(".challenge-checkbox select-all .challenge-checkbox");
      const remaining = card.querySelectorAll(".challenge-checkboxes .challenge-checkbox:not(:checked)").length;
      if (remaining === 0) {
        selectAll2.checked = true;
        selectAll2.setAttribute("aria-pressed", "true");
      } else if (perCard.length === remaining) {
        selectAll2.checked = false;
        selectAll2.setAttribute("aria-pressed", "false");
      }
      syncSelectAll(selectAll2, perCard);
      updateCheckCount(card, perCard);
    });
  }
}
function syncSelectAll(selectAll, perCard) {
  if (!selectAll || perCard.length === 0)
    return;
  const all = perCard.every((cb) => cb.checked);
  const some = perCard.some((cb) => cb.checked);
  if (all) {
    selectAll.checked = true;
    selectAll.setAttribute("aria-pressed", "true");
  } else {
    selectAll.checked = false;
    selectAll.setAttribute("aria-pressed", "false");
  }
}
function updateCheckCount(card, perCard) {
  const countEl = card.querySelector(".check-count");
  if (countEl)
    countEl.textContent = `${perCard.filter((cb) => cb.checked).length}/${perCard.length}`;
}
function perCardStatus(taskId, status) {
  const bar = document.querySelector(`.challenge-card[data-id="${taskId}"] .bench-status-bar`);
  const text = document.querySelector(`.challenge-card[data-id="${taskId}"] .bench-status-text`);
  if (!bar || !text)
    return;
  const labels = { pass: "Pass", fail: "Fail", error: "Error", "not-run": "Not run" };
  const pct = { "not-run": 0, pass: 100, fail: 0, error: 0 };
  text.textContent = labels[status] || "Not run";
  bar.style.width = `${pct[status] || 0}%`;
  bar.classList.remove("complete", "partial");
  if (status === "pass")
    bar.classList.add("complete");
  else if (status === "fail" || status === "error")
    bar.classList.add("partial");
}
function applyChallengeFilter() {
  if (!activeCategory) {
    const listEl2 = dom_default.getEl(document, "#challenges-list");
    const tasks2 = state_default.tasks || [];
    listEl2.innerHTML = "";
    if (tasks2.length === 0) {
      listEl2.innerHTML = '<p class="empty">No tasks found.</p>';
      return;
    }
    for (const task of tasks2)
      listEl2.appendChild(renderChallengeCard(task));
    state_default.resultsRendered = true;
    return;
  }
  const listEl = dom_default.getEl(document, "#challenges-list");
  const tasks = (state_default.tasks || []).filter((t) => t.category === activeCategory);
  listEl.innerHTML = "";
  if (tasks.length === 0) {
    listEl.innerHTML = '<p class="empty">No tasks found in category "' + escapeHtml(activeCategory) + '".</p>';
    return;
  }
  for (const task of tasks)
    listEl.appendChild(renderChallengeCard(task));
}
function toggleCategoryFilter(category) {
  activeCategory = activeCategory === category ? null : category;
  const chips = document.querySelectorAll("#challenge-categories .chip");
  for (const chip of chips) {
    const chipCategory = chip.getAttribute("data-category");
    if (chipCategory === activeCategory) {
      chip.classList.add("active");
      chip.setAttribute("aria-pressed", "true");
    } else {
      chip.classList.remove("active");
      chip.setAttribute("aria-pressed", "false");
    }
  }
  applyChallengeFilter();
}
async function loadChallenges() {
  const response = await fetch("/api/tasks");
  if (!response.ok)
    return;
  const data = await response.json();
  state_default.tasks = Array.isArray(data) ? data : data.tasks || [];
  const categories = [...new Set((state_default.tasks || []).map((t) => t.category).filter(Boolean))];
  const categoriesEl = dom_default.getEl(document, "#challenge-categories");
  if (!categoriesEl)
    return;
  categoriesEl.innerHTML = "";
  for (const category of categories) {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.setAttribute("data-category", category);
    chip.setAttribute("aria-pressed", "false");
    chip.textContent = category;
    chip.addEventListener("click", () => toggleCategoryFilter(category));
    categoriesEl.appendChild(chip);
  }
  applyChallengeFilter();
}
var activeCategory;
var init_challenges = __esm({
  "web/ui/challenges.js"() {
    init_dom();
    init_state();
    init_results();
    activeCategory = null;
  }
});

// web/ui/views.js
var views_exports = {};
__export(views_exports, {
  VIEWS: () => VIEWS,
  initializeViewSwitcher: () => initializeViewSwitcher,
  reloadModels: () => reloadModels,
  switchView: () => switchView
});
function switchView(viewName) {
  state_default.activeView = viewName;
  VIEWS.forEach((v) => {
    const tab = dom_default.getEl(document, `#header-nav [data-view="${v}"]`);
    if (tab) {
      if (v === viewName) {
        tab.classList.add("active");
      } else {
        tab.classList.remove("active");
      }
    }
    const panel2 = dom_default.getEl(document, `#content-area .view-panel[data-view="${v}"]`);
    if (panel2)
      panel2.style.display = v === viewName ? "" : "none";
  });
  const panel = document.querySelector(`#content-area .view-panel[data-view="${viewName}"]`);
  if (panel) {
    state_default.engineListContainer = panel.querySelector("#engine-list");
    if (!state_default.engineListContainer) {
      console.warn("View setup warning: #engine-list container not found in the active view panel.");
    }
    state_default.resultsContainer = panel.querySelector("#results-container");
    if (!state_default.resultsContainer) {
      console.warn("View setup warning: #results-container not found in the active view panel.");
    }
  } else {
    state_default.engineListContainer = null;
    state_default.resultsContainer = null;
  }
}
function reloadModels() {
  if (state_default.engineListContainer) {
    loadModels();
  } else {
    console.warn("Cannot reload models: Engine list container is null.");
  }
}
function initializeViewSwitcher() {
  if (document.body.dataset.viewSwitcherInitialized === "true") {
    console.warn("View switcher initialization already completed. Skipping setup.");
    return;
  }
  const navTabs = document.querySelectorAll("#header-nav .nav-tab");
  for (const tab of navTabs) {
    tab.addEventListener("click", () => switchView(tab.getAttribute("data-view")));
  }
  document.body.dataset.viewSwitcherInitialized = "true";
  switchView(state_default.activeView || "dashboard");
}
var VIEWS;
var init_views = __esm({
  "web/ui/views.js"() {
    init_dom();
    init_state();
    init_models();
    init_challenges();
    VIEWS = ["dashboard", "benchmark", "challenges"];
  }
});

// web/ui/main.js
(function() {
  const dom2 = (init_dom(), dom_exports);
  const state2 = (init_state(), state_exports);
  const models = (init_models(), models_exports);
  const challenges = (init_challenges(), challenges_exports);
  const results = (init_results(), results_exports);
  const views = (init_views(), views_exports);
  state2.selectedModels = window.__selectedModels || [];
  state2.selectedEngine = window.__selectedEngine || "";
  state2.engineModels = window.__engineModels || {};
  state2.activeModel = window.__activeModel || "";
  state2.engines = window.__engines || [];
  state2.tasks = window.__tasks || [];
  window.__tasks = [];
  views.initializeViewSwitcher();
  models.loadModels();
  challenges.loadChallenges();
  results.loadBenchmarkResults();
  views.switchView(state2.activeView || "dashboard");
})();
