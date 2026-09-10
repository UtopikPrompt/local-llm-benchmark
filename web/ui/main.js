// main.js — renders benchmark results using the Row data schema
// (engine, model, category, ttft_s, tok_per_s, iters_per_s, quality_*).

document.addEventListener('DOMContentLoaded', () => {
    const modelList = document.getElementById('model-list');
    const resultsContainer = document.getElementById('results-container');
    const typeFilter = document.getElementById('benchmark-type-filter');

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

    async function loadModels() {
        // Clear any previously rendered engine sections.
        modelList.innerHTML = '';
        try {
            const engines = window.__engines || [];
            for (const engine of engines) {
                const container = document.createElement('div');
                container.className = 'engine-section';
                container.setAttribute('data-engine', engine.name);
                const wrapper = document.createElement('div');
                wrapper.className = 'engine-content';
                container.appendChild(wrapper);
                const heading = document.createElement('button');
                heading.className = 'engine-heading';
                heading.setAttribute('type', 'button');
                heading.setAttribute('aria-expanded', 'false');
                heading.innerHTML =
                    '<span class="engine-heading-text">' + escapeHtml(engine.name) + '</span>' +
                    '<span class="engine-chevron">&#9662;</span>';
                heading.addEventListener('click', () => {
                    const section = container.querySelector('.engine-content');
                    if (!section) return;
                    const expanded = !section.classList.contains('collapsed');
                    section.classList.toggle('collapsed', !expanded);
                    heading.setAttribute('aria-expanded', String(expanded));
                });
                wrapper.appendChild(heading);
                try {
                    const base_url = engineBaseURL(engine.name);
                    const response = await fetch('/models?base_url=' + encodeURIComponent(base_url), {
                        method: 'POST',
                    });
                    if (!response.ok) throw new Error('Failed to fetch models.');
                    const data = await response.json();
                    renderModelCheckboxes(wrapper, engine.name, data.models || []);
                } catch (error) {
                    console.error('Error loading models for ' + engine.name + ':', error);
                    const note = document.createElement('p');
                    note.className = 'model-error';
                    note.textContent = 'Error loading models: ' + error.message;
                    wrapper.appendChild(note);
                }
            }
            modelList.scrollTop = 0;
            attachModelListeners();
        } catch (error) {
            console.error('Error loading engines:', error);
            modelList.innerHTML =
                '<p style="color:var(--text-secondary);">Error loading engines: ' + error.message + '</p>';
        }
    }

    function formatModelName(model) {
        return model.charAt(0).toUpperCase() + model.slice(1).replace(/_/g, ' ');
    }

    function renderModelCheckboxes(engineContent, engineName, models) {
        const list = document.createElement('div');
        list.className = 'engine-content';
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
        if (resultsContainer.querySelector('.run-button')) return;

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
            resultsContainer.querySelector('#run-button').addEventListener('click', runBenchmark);
            return;
        }

        window.__selectedModels = array;
        const header = '<div class="results-header">' +
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
        const benchmarkType = typeFilter.value;
        const params = new URLSearchParams();
        params.append('models', serializeSelectedModels(names));
        if (benchmarkType) params.append('type', benchmarkType);
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

    async function initializeListeners() {
        typeFilter.addEventListener('change', (e) => {
            loadBenchmarkResults();
        });
        await loadEngines();
        await loadModels();
    }

    initializeListeners();
    document.getElementById('refresh-models').addEventListener('click', refreshAll);
});
