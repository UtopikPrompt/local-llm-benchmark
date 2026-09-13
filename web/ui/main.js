// main.js — renders benchmark results using the Row data schema
// (engine, model, category, ttft_s, tok_per_s, iters_per_s, quality_*).

document.addEventListener('DOMContentLoaded', async () => {
    const modelList = document.getElementById('engine-list');
    const resultsContainer = document.getElementById('results-container');
    const typeFilter = document.getElementById('benchmarkType') || null;

    // Track the set of selected models and the selected engine so the
    // "Run benchmark" button triggers a run for the active model and the
    // results table lists every selected model's rows.
    window.__selectedModels = [];
    window.__selectedEngine = '';
    // Models selected per engine section.
    window.__engineModels = {};
    // The model whose rows are currently highlighted in the side menu.
    window.__activeModel = '';

    async function loadEngines() {
        try {
            const response = await fetch('/api/config/engines');
            if (!response.ok) throw new Error('Failed to fetch engine list.');
            const data = await response.json();
            if (data.engines && Array.isArray(data.engines)) {
                window.__engines = data.engines;
            }
        } catch (error) {
            console.error('Error loading engines:', error);
        }
    }

    // Resolve the base_url for the selected engine so we can query the
    // remote engine's model list via the remote API.
    function engineBaseURL(engineName) {
        if (!engineName) return '';
        const engines = window.__engines || [];
        const engine = engines.find((e) => e.name === engineName);
        return engine ? engine.base_url : engineName;
    }

    // Fetch and render the model checkboxes for each engine section.
    async function loadModels() {
        try {
            const modelList = document.getElementById('engine-list');
            if (!modelList) return;
            modelList.classList.add('loading');
            for (const engine of window.__engines || []) {
                const engineContent = document.createElement('div');
                engineContent.className = 'engine-content';
                engineContent.dataset.engine = engine.name;
                const engineTitle = document.createElement('div');
                engineTitle.className = 'engine-title';
                engineTitle.textContent = engine.name;
                engineContent.appendChild(engineTitle);

                const heading = document.createElement('button');
                heading.className = 'engine-heading';

                const name = document.createElement('span');
                name.className = 'engine-heading-text';
                name.textContent = engine.name;
                heading.appendChild(name);

                const toggle = document.createElement('span');
                toggle.className = 'engine-chevron';
                toggle.textContent = '▾';
                heading.appendChild(toggle);

                heading.addEventListener('click', () => engineContent.classList.toggle('expanded'));

                const engineModels = [];
                (async () => {
                    try {
                        const resp = await fetch('/models?base_url=' + encodeURIComponent(engine.base_url), { method: 'POST' });
                        const data = await resp.json();
                        if (data.models) {
                            for (const model of data.models) engineModels.push(model);
                            renderModelCheckboxes(engineContent, engine.name, engineModels);
                        } else {
                            const note = document.createElement('p');
                            note.className = 'model-empty';
                            note.textContent = 'No models available.';
                            engineContent.appendChild(note);
                        }
                    } catch (e) {
                        console.error('Failed to load models for', engine.name, e);
                    }
                })();

                modelList.appendChild(engineContent);
            }
            attachModelListeners();
        } catch (e) {
            console.error('Error loading models:', e);
        } finally {
            const modelList = document.getElementById('engine-list');
            if (modelList) modelList.classList.remove('loading');
        }
    }

    function formatModelName(model) {
        return model.charAt(0).toUpperCase() + model.slice(1).replace(/_/g, ' ');
    }

    function renderModelCheckboxes(engineContent, engineName, models) {
        const list = document.createElement('div');
        list.className = 'engine-items';
        if (!models || models.length === 0) {
            const note = document.createElement('p');
            note.className = 'model-empty';
            note.textContent = 'No models available.';
            list.appendChild(note);
        } else {
            models.forEach(model => {
                const label = document.createElement('label');
                label.className = 'model-row';
                const input = document.createElement('input');
                input.type = 'checkbox';
                input.className = 'model-checkbox';
                input.value = model;
                input.setAttribute('data-engine', engineName);
                const text = document.createElement('span');
                text.className = 'model-label';
                text.textContent = formatModelName(model);
                label.appendChild(input);
                label.appendChild(text);
                list.appendChild(label);
            });
        }
        engineContent.appendChild(list);
    }

    // Refresh the side menu by reloading the engines from the config API
    // and re-fetching every engine's model list from the remote engines.
    async function refreshAll() {
        const button = document.getElementById('refresh-models');
        if (button) button.disabled = true;
        try {
            await loadEngines();
            await loadModels();
        } catch (error) {
            console.error('Error refreshing engines:', error);
        } finally {
            if (button) button.disabled = false;
        }
    }

    // Attach change listeners to the model checkboxes, then keep the
    // in-memory selection in sync.
    function attachModelListeners() {
        const checkboxes = modelList.querySelectorAll('.model-checkbox');
        checkboxes.forEach((checkbox) => {
            checkbox.addEventListener('change', () => {
                setSelectedModels();
                const section = checkbox.closest('.engine-section');
                if (section) {
                    const anyChecked = Array.from(section.querySelectorAll('.model-checkbox')).some(
                        (c) => c.checked
                    );
                    section.classList.toggle('has-selection', anyChecked);
                }
            });
        });
    }

    // Read every checked model checkbox and update the shared selection
    // state. ``__selectedModels`` holds all selected models (used to filter
    // the results table), ``__selectedEngine`` marks the active section,
    // ``__engineModels`` tracks the selection per engine, and ``__activeModel``
    // is the single model used to trigger a run.
    function setSelectedModels() {
        const checkboxes = modelList.querySelectorAll('.model-checkbox');
        const selected = [];
        const perEngine = {};
        checkboxes.forEach((checkbox) => {
            if (checkbox.checked) {
                selected.push(checkbox.value);
                const engine = checkbox.getAttribute('data-engine');
                (perEngine[engine] || (perEngine[engine] = [])).push(checkbox.value);
            }
        });
        window.__selectedModels = selected;
        window.__engineModels = perEngine;
        if (selected.length === 1) {
            window.__activeModel = selected[0];
        }
    }

    // Trigger a benchmark run for the active model and refresh the
    // results table once the saved report is available.
    async function runBenchmark() {
        const button = resultsContainer.querySelector('.run-button');
        if (button) button.disabled = true;
        const note = resultsContainer.querySelector('.run-note');
        if (note) note.textContent = 'Running benchmark…';
        const activeModel = window.__activeModel || window.__selectedModels[0];
        try {
            const response = await fetch('/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildRunRequest(activeModel)),
            });
            if (!response.ok) throw new Error('Failed to run benchmark.');
            if (note) note.textContent = '';
            await loadBenchmarkResults(serializeSelectedModels());
        } catch (error) {
            console.error('Error running benchmark:', error);
            if (note) note.textContent = 'Error: ' + error.message;
            await loadBenchmarkResults(serializeSelectedModels());
        } finally {
            if (button) button.disabled = false;
        }
    }

    function buildRunRequest(model) {
        const request = {};
        const models = window.__selectedModels;
        if (models && models.length) {
            const engine = window.__engines.find((e) => e.models && e.models.includes(model)) ||
                window.__engines.find((e) => e.model === model) ||
                window.__engines[0];
            if (engine) request.base_url = engine.base_url;
        }
        request.model = model;
        return request;
    }

    function fmt(n) {
        if (n === null || n === undefined || n === '' || Number.isNaN(n)) return '—';
        return Number(n).toLocaleString(undefined, { maximumFractionDigits: 3 });
    }

    function cls(value, passClass, failClass, warnClass) {
        if (value === null || value === undefined || value === '') return '';
        const v = value;
        if (typeof v === 'boolean') {
            return v ? '<span class="pill ' + passClass + '">' + (v ? 'PASS' : 'FAIL') + '</span>'
                : '<span class="pill ' + failClass + '">' + (v ? 'PASS' : 'FAIL') + '</span>';
        }
        return '';
    }

    function renderResult(r) {
        const qualityPill = cls(r.quality_passed, 'pass', 'fail', 'warn');
        const qualityJudgePill = cls(r.quality_judge, 'pass', 'fail', 'warn');
        return '<tr>' +
            '<td class="mono" style="color:var(--text-secondary);">' + fmt(r.engine) + '</td>' +
            '<td class="mono" style="color:var(--text-secondary);">' + fmt(r.model) + '</td>' +
            '<td><span class="category-pill">' + fmt(r.category) + '</span></td>' +
            '<td class="num">' + fmt(r.ttft_s) + '</td>' +
            '<td class="num">' + fmt(r.tok_per_s) + '</td>' +
            '<td class="num">' + fmt(r.iters_per_s) + '</td>' +
            '<td>' + qualityPill + '</td>' +
            '<td>' + qualityJudgePill + '</td>' +
        '</tr>';
    }

    function displayResults(results, modelNames, benchmarkType) {
        // ``modelNames`` may arrive either as an array or a comma-separated
        // string (serialized from the checkbox selection); normalize it.
        const array = Array.isArray(modelNames)
            ? modelNames
            : (modelNames || '').split(',').filter((n) => n !== '');
        resultsContainer.innerHTML = '';
        // Only block re-renders AFTER the first table has been rendered. The
        // default container (from dashboard.html) contains a .run-button, so on
        // the initial load this guard must NOT return early.
        if (__resultsRendered && !resultsContainer.querySelector('.results-table')) return;

        if (!results || results.length === 0) {
            const label = array.length === 1
                ? array[0]
                : array.join(', ');
            resultsContainer.innerHTML =
                '<div class="run-state">' +
                    '<div class="run-subtitle">No results yet for ' +
                        escapeHtml(label) + '.</div>' +
                    '<button class="run-button" id="run-button">Run benchmark</button>' +
                    '<div class="run-note" id="run-note"></div>' +
                '</div>';
            resultsContainer.querySelector('#run-button').addEventListener('click',  () => switchView(tab.getAttribute('benchmark')));
            return;
        }
        __resultsRendered = true;
            '<span class="results-header-title">Benchmark Results</span>' +
            '<span class="results-header-models">';
        array.forEach((name, index) => {
            header += '<span class="results-header-chip">' + escapeHtml(name) + '</span>';
            if (index < modelNames.length - 1) header += ', ';
        });
        header += '</span></div>';

        const rows = results.map(renderResult).join('');
        resultsContainer.innerHTML =
            '<div class="results-header">' + header + '</div>' +
            '<div class="results-filter">' +
                '<div class="results-filter-search"><input id="results-search" type="search" placeholder="Search engine, model or category…" /></div>' +
                '<div class="results-filter-categories" id="results-categories">' +
                    categories.map((c) => '<span class="category-pill">' + escapeHtml(c) + '</span>').join('') +
                '</div>' +
                '<div class="results-filter-clear"><button id="results-clear" class="run-button">Clear</button></div>' +
            '</div>' +
            '<table class="results-table">' +
                '<thead><tr>' +
                    '<th class="mono">Engine</th>' +
                    '<th class="mono">Model</th>' +
                    '<th>Category</th>' +
                    '<th class="num">TTFT (s)</th>' +
                    '<th class="num">Tokens/s</th>' +
                    '<th class="num">Iters/s</th>' +
                    '<th style="text-align:right;">Quality</th>' +
                    '<th style="text-align:right;">Judge</th>' +
                '</tr></thead>' +
                '<tbody>' + rows + '</tbody>' +
            '</table>';
        attachResultsFilterListeners();
    }

    // ---------------------------------------------------------------------
    // Results table filtering
    // ---------------------------------------------------------------------
    function attachResultsFilterListeners() {
        const searchInput = document.getElementById('results-search');
        const clearButton = document.getElementById('results-clear');
        if (searchInput) {
            searchInput.value = '';
            searchInput.addEventListener('input', (e) => {
                const value = e.target.value.trim().toLowerCase();
                const rows = document.querySelectorAll('.results-table tbody tr');
                let visible = 0;
                rows.forEach((row) => {
                    const text = row.textContent.toLowerCase();
                    const match = value === '' || text.includes(value);
                    row.style.display = match ? '' : 'none';
                    if (match) visible++;
                });
                updateResultsCount(visible);
            });
        }
        if (clearButton) {
            clearButton.addEventListener('click', () => {
                document.getElementById('results-search').value = '';
                document.querySelectorAll('.results-table tbody tr')
                    .forEach((row) => (row.style.display = ''));
                document.getElementById('results-categories').innerHTML = '';
                updateResultsCount(document.querySelectorAll('.results-table tbody tr').length);
            });
        }
    }

    function updateResultsCount(visible) {
        const note = document.querySelector('.results-count');
        if (note) {
            note.textContent = (visible === document.querySelectorAll('.results-table tbody tr').length)
                ? ''
                : (visible + ' of ' + document.querySelectorAll('.results-table tbody tr').length + ' shown');
        }
    }

    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    async function loadBenchmarkResults(modelNames) {
        const names = modelNames || window.__selectedModels;
        const typeGroup = document.getElementById('benchmarkType') || null;
        const radio = typeGroup ? typeGroup.querySelector('input[name="benchmark_type"]:checked') : null;
        const benchmarkType = radio ? radio.value : '';
        const params = new URLSearchParams();
        params.append('models', serializeSelectedModels(names));
        if (benchmarkType) params.append('benchmark_type', benchmarkType);
        const response = await fetch('/api/results?' + params.toString());
        if (!response.ok) throw new Error('Failed to fetch results.');
        const data = await response.json();
        displayResults(data.results, serializeSelectedModels(names), benchmarkType);
    }

    function serializeSelectedModels() {
        const names = window.__selectedModels;
        if (!names || names.length === 0) return '';
        return names.join(',');
    }

    // -------------------------------------------------------------------------
    // Challenges / task corpus panel
    // -------------------------------------------------------------------------

    // Fetch the default task corpus and render it as category filter chips on
    // top and task cards below, with an "active filter" pill on the card.
    async function loadChallenges() {
        const categoriesEl = document.getElementById('challenge-categories');
        const listEl = document.getElementById('challenges-list');
        categoriesEl.innerHTML = '';
        listEl.innerHTML = '';
        if (!categoriesEl || !listEl) return;
        try {
            const response = await fetch('/api/tasks');
            if (!response.ok) throw new Error('Failed to fetch tasks.');
            const data = await response.json();
            const tasks = data.tasks || [];
            window.__tasks = tasks;
            if (tasks.length === 0) {
                listEl.innerHTML = '<p class="empty">No tasks found.</p>';
                return;
            }
            // Build category chips (one per distinct category, in first-seen order).
            const order = [];
            const counts = {};
            for (const task of tasks) {
                counts[task.category] = (counts[task.category] || 0) + 1;
                if (!order.includes(task.category)) order.push(task.category);
            }
            for (const category of order) {
                const chip = document.createElement('button');
                chip.className = 'chip';
                chip.setAttribute('type', 'button');
                chip.setAttribute('data-category', category);
                chip.innerHTML =
                    '<span class="chip-label">' + escapeHtml(category) + '</span>' +
                    '<span class="chip-count">' + counts[category] + '</span>';
                chip.addEventListener('click', () => toggleCategoryFilter(category));
                categoriesEl.appendChild(chip);
            }
            // Render every task as a card.
            for (const task of tasks) {
                listEl.appendChild(renderChallengeCard(task));
            }
        } catch (error) {
            listEl.innerHTML =
                '<p style="color:var(--text-secondary);">Error loading challenges: ' + error.message + '</p>';
        }
    }

    // Track the active category filter chip (if any).
    let __activeCategory = null;
    let __resultsRendered = false;

    function toggleCategoryFilter(category) {
        if (__activeCategory === category) {
            __activeCategory = null;
        } else {
            __activeCategory = category;
        }
        // Reflect the toggle on the chips.
        const chips = document.querySelectorAll('#challenge-categories .chip');
        for (const chip of chips) {
            const chipCategory = chip.getAttribute('data-category');
            if (chipCategory === __activeCategory) {
                chip.classList.add('active');
                chip.setAttribute('aria-pressed', 'true');
            } else {
                chip.classList.remove('active');
                chip.setAttribute('aria-pressed', 'false');
            }
        }
        applyChallengeFilter();
    }

    // Re-render the challenge cards applying the active category filter.
    function applyChallengeFilter() {
        if (!__activeCategory) {
            // No active filter: show every task.
            const listEl = document.getElementById('challenges-list');
            const tasks = window.__tasks || [];
            listEl.innerHTML = '';
            if (tasks.length === 0) {
                listEl.innerHTML = '<p class="empty">No tasks found.</p>';
                return;
            }
            for (const task of tasks) listEl.appendChild(renderChallengeCard(task));
            __resultsRendered = true;
            return;
        }
        const listEl = document.getElementById('challenges-list');
        const tasks = (window.__tasks || []).filter((t) => t.category === __activeCategory);
        listEl.innerHTML = '';
        if (tasks.length === 0) {
            listEl.innerHTML =
                '<p class="empty">No tasks found in category "' + escapeHtml(__activeCategory) + '".</p>';
            return;
        }
        for (const task of tasks) listEl.appendChild(renderChallengeCard(task));
    }

    function renderChallengeCard(task) {
        const card = document.createElement('div');
        card.className = 'challenge-card';
        card.setAttribute('data-category', task.category || '');
        const tags = [];
        if (task.system) tags.push('<span class="tag">system</span>');
        if (task.expected) tags.push('<span class="tag">expected</span>');
        const tagsHtml = tags.join('') || '<span class="tag">prompt</span>';
        card.innerHTML =
            '<div class="challenge-card-header">' +
                '<span class="challenge-card-title">' + escapeHtml(task.id) + '</span>' +
                '<span class="chip small">' + escapeHtml(task.category) + '</span>' +
            '</div>' +
            '<div class="challenge-card-body">' +
                '<p class="challenge-card-prompt">' + escapeHtml(task.prompt) + '</p>' +
            '</div>' +
            '<div class="challenge-card-tags">' + tagsHtml + '</div>';
        return card;
    }

    // -------------------------------------------------------------------------
    // View switching between the three nav tabs
    // -------------------------------------------------------------------------

    // Challenge corpus loaded once for filtering.
    window.__tasks = [];

    function switchView(viewName) {
        const tabs = document.querySelectorAll('#header-nav .nav-tab');
        const panels = document.querySelectorAll('#content-area .view-panel');
        let current = 'dashboard';
        for (const tab of tabs) {
            if (tab.getAttribute('data-view') === viewName) {
                tab.classList.add('active');
                tab.setAttribute('aria-current', 'page');
            } else {
                tab.classList.remove('active');
                tab.removeAttribute('aria-current');
            }
            current = viewName;
        }
        for (const panel of panels) {
            const shouldShow = panel.getAttribute('data-view') === viewName;
            panel.classList.toggle('hidden', !shouldShow);
            if (!shouldShow) panel.style.display = 'none';
            else panel.style.display = '';
        }
        window.__activeView = current;

        // Refresh the new Benchmark panel widgets (#engine-select,
        // #model-select, #challenge-checks) whenever their view is shown.
        // __engines and __challengeTasks are already populated by
        // initializeListeners()'s loadEngines()/loadChallenges() calls.
        if (viewName === "benchmark" || viewName === "challenges") {
          renderEngineOptions();
          renderChallengeChecks();
          loadChallengeSelection();
        }

        return current;
    }

    async function initializeListeners() {
        const benchmarkType = document.getElementById('benchmarkType') || null;
        const challengesList = document.getElementById('challenges-list');
        const categoriesEl = document.getElementById('challenge-categories');
        // Delegated toggle: the module-level toggleCategoryFilter handles the
        // filter state, chip visuals, and applyChallengeFilter() call.
        if (benchmarkType) benchmarkType.addEventListener('change', () => {
            window.__selectedModels = [];
            window.__selectedEngine = '';
            window.__engineModels = {};
            loadModels();
        });
        if (categoriesEl) {
            const chips = categoriesEl.querySelectorAll('.chip');
            for (const chip of chips) {
                chip.addEventListener('click', () => toggleCategoryFilter(chip.getAttribute('data-category')));
            }
        }
        for (const tab of document.querySelectorAll('#header-nav .nav-tab')) {
            tab.addEventListener('click', () => switchView(tab.getAttribute('data-view')));
        }
        await loadEngines();
        await loadModels();
        await loadChallenges();
        switchView(window.__activeView || 'dashboard');
    }
    initializeListeners();

    // Render the saved results table on page load so the dashboard shows
    // results immediately (with the filter UI), no manual run required.
    await loadBenchmarkResults();
});

// ===== Benchmark panel: engine/model comboboxes, challenge checks, run & progression =====
// These populate the NEW Benchmark panel (#engine-select, #model-select, #challenge-checks,
// #bench-status, #bench-progress) directly — they do NOT use the old side-menu #engine-list.

var __engines = [];
var __challengeTasks = [];

function renderEngineOptions() {
  var sel = document.getElementById("engine-select");
  if (!sel) return;
  var html = "";
  $.each(__engines, function (i, e) {
    html += "<option value=\"" + escapeHtml(e.name) + "\">" + escapeHtml(e.name) +
      " — " + escapeHtml(e.model) + "</option>";
  });
  sel.innerHTML = html;
}

function engineBaseURL(name) {
  for (var i = 0; i < __engines.length; i++) {
    if (__engines[i].name === name) return __engines[i].base_url;
  }
  return null;
}

function loadModelsForEngine(name) {
  var sel = document.getElementById("model-select");
  if (!sel) return;
  var base = engineBaseURL(name);
  if (!base) return;
  $.post("/models", { base_url: base }).done(function (data) {
    var models = (data.models || []).map(m => String(m));
    sel.innerHTML = "<option value=\"\">Select model…</option>";
    $.each(models, function (i, m) {
      sel.innerHTML += "<option value=\"" + escapeHtml(m) + "\">" + escapeHtml(m) + "</option>";
    });
  }).fail(function () {
    sel.innerHTML = "<option value=\"\">(no models)</option>";
  });
}

$(document).on("change", "#engine-select", function () {
  var name = $(this).val();
  if (name) loadModelsForEngine(name);
});

function renderChallengeChecks() {
  var container = document.getElementById("challenge-checks");
  var list = document.getElementById("challenges-list");
  if (!container || !list) return;
  var categories = {};
  $.each(__challengeTasks, function (i, t) {
    var c = (t.category || "Other").trim() || "Other";
    categories[c] = true;
  });
  var vars = ["", "All challenges"];
  var catNames = Object.keys(categories);
  var selectAll = document.createElement("label");
  selectAll.className = "challenge-checkbox";
  selectAll.innerHTML = '<input type="checkbox" class="check-all" checked> ' +
    '<span class="challenge-checks-title">All challenges</span>';
  selectAll.addEventListener("change", function () {
    var checked = this.checked;
    $(".challenge-checks .category-checkbox").each(function () {
      this.checked = checked;
    });
  });
  container.appendChild(selectAll);
  catNames.forEach(function (c) {
    var label = document.createElement("label");
    label.className = "challenge-checkbox";
    var count = 0;
    __challengeTasks.forEach(function (t) {
      if ((t.category || "Other").trim() === c) count++;
    });
    label.innerHTML =
      '<input type="checkbox" class="category-checkbox" data-category="' +
      escapeHtml(c) + '">' +
      '<span>' + escapeHtml(c) + '</span>' +
      '<span class="check-count">(' + count + ')</span>';
    container.appendChild(label);
  });
}

function loadChallengeSelection() {
  var checks = document.querySelectorAll("#challenge-checks .category-checkbox");
  var selected = [];
  $.each(__challengeTasks, function (i, t) { selected.push(t.id); });
  __challengeSelection = selected.slice();
  $(".category-checkbox").each(function () {
    var cat = $(this).attr("data-category");
    var inSel = __challengeSelection.filter(function (t) {
      return __challengeTasks.filter(function (x) {
        return (x.category || "Other").trim() === cat;
      }).length > 0;
    });
    this.checked = inSel.length > 0;
  });
  syncChallengeCounts();
}

function syncChallengeCounts() {
  var all = $(".check-all")[0];
  var total = __challengeTasks.length;
  if (all) all.checked = total > 0;
  $(".challenge-checkbox").each(function () {
    var input = $(this).find("input")[0];
    if (!input) return;
    $(this).find(".check-count").text("(" + __challengeTasks.length + ")");
  });
}

function selectedChallenges() {
  var result = [];
  $(".category-checkbox").each(function () {
    if (this.checked) {
      var cat = $(this).attr("data-category");
      __challengeTasks.filter(function (t) {
        return (t.category || "Other").trim() === cat;
      }).forEach(function (t) { result.push(t.id); });
    }
  });
  return result;
}

function showProgress(status, percent) {
  var box = document.getElementById("bench-status");
  var text = document.getElementById("bench-status-text");
  var bar = document.getElementById("bench-progress-bar");
  if (!box) return;
  box.classList.remove("is-hidden");
  box.classList.add("is-loading");
  if (text) text.innerHTML = "Running benchmark — " + escapeHtml(status);
  if (bar) bar.style.width = percent + "%";
}

function updateProgress(done, total, log) {
  var box = document.getElementById("bench-status");
  if (!box) return;
  box.classList.remove("is-loading");
  var bar = document.getElementById("bench-progress-bar");
  var text = document.getElementById("bench-status-text");
  var pct = total > 0 ? Math.round((done / total) * 100) : 0;
  if (bar) bar.style.width = pct + "%";
  if (text) {
    var rows = "";
    $.each(log, function (i, line) { rows += "<div>" + escapeHtml(line) + "</div>"; });
    text.innerHTML = "Progress: " + done + "/" + total +
      " (" + pct + "%)<br><span class='highlight'>" + rows + "</span>";
  }
}

function runBenchmark() {
  var name = $("#engine-select").val();
  if (!name) { $("#engine-select").focus(); return; }
  var model = $("#model-select").val();
  if (!model) { $("#model-select").focus(); return; }
  var prompt = $("#bench-prompt").val().trim();
  if (!prompt) { $("#bench-prompt").focus(); return; }
  var tasks = selectedChallenges();
  var task = tasks.length ? tasks[0] : null;
  var max_concurrent = 1;
  $.post("/run", {
    engine: name,
    model,
    task,
    max_concurrent,
    timeout: 300,
  })
  .done(function (resp) {
    if (resp && resp.rows) {
      var log = [];
      $.each(resp.rows, function (i, row) {
        log.push(row.task_id + " — " + row.category + ": " + row.quality_passed ? "pass" : "fail");
      });
      updateProgress(resp.rows.length, resp.rows.length, log);
    }
  })
  .fail(function () {
    var box = document.getElementById("bench-status");
    var text = document.getElementById("bench-status-text");
    if (box) box.classList.remove("is-loading");
    if (text) text.innerHTML = "Error running benchmark — check the engine and model.";
  });
}

$(document).on("click", "#btn-run-benchmark", function () {
  $("#bench-status").addClass("is-hidden");
  runBenchmark();
});

// ===== end of runBenchmark and button wiring =====
