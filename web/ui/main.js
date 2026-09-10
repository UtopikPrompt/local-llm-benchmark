// main.js — renders benchmark results using the Row data schema
// (engine, model, category, ttft_s, tok_per_s, iters_per_s, quality_*).

document.addEventListener('DOMContentLoaded', () => {
    const engineSelect = document.getElementById('engine-select');
    const modelList = document.getElementById('model-list');
    const resultsContainer = document.getElementById('results-container');
    const typeFilter = document.getElementById('benchmark-type-filter');

    // Track the set of selected models and the selected engine so the
    // "Run benchmark" button triggers a run for the active model and the
    // results table lists every selected model's rows.
    window.__selectedModels = [];
    window.__selectedEngine = '';
    // The model whose rows are currently highlighted in the side menu.
    window.__activeModel = '';

    async function loadEngines() {
        try {
            const response = await fetch('/api/config/engines');
            if (!response.ok) throw new Error('Failed to fetch engine list.');
            const data = await response.json();
            if (data.engines && Array.isArray(data.engines)) {
                window.__engines = data.engines;
                data.engines.forEach((engine) => {
                    const option = document.createElement('option');
                    option.value = engine.name;
                    option.textContent = engine.name;
                    option.setAttribute('data-engine', engine.name);
                    engineSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading engines:', error);
            engineSelect.innerHTML =
                '<option value="">Error loading engines: ' + error.message + '</option>';
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

    async function loadModels(engineName) {
        // Reset any previous selection.
        modelList.innerHTML = '<p class="loading">Loading models…</p>';
        try {
            const base_url = engineBaseURL(engineName);
            const response = await fetch('/models?base_url=' + encodeURIComponent(base_url), {
                method: 'POST',
            });
            if (!response.ok) throw new Error('Failed to fetch models.');
            const data = await response.json();
            if (data.models && Array.isArray(data.models)) {
                populateModelList(data.models, engineName);
            } else {
                modelList.innerHTML = '<p style="color:var(--text-secondary);">No models available.</p>';
            }
        } catch (error) {
            console.error('Error loading models:', error);
            modelList.innerHTML =
                '<p style="color:var(--text-secondary);">Error loading models: ' + error.message + '</p>';
        }
    }

    function populateModelList(models, engineName) {
        modelList.innerHTML = '';
        if (!models || models.length === 0) {
            modelList.innerHTML = '<p style="color:var(--text-secondary);">No models available.</p>';
            return;
        }
        const select = document.createElement('select');
        select.setAttribute('multiple', 'multiple');
        select.setAttribute('id', 'model-select');
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = '— Select Model(s) —';
        placeholder.disabled = true;
        select.appendChild(placeholder);
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model.charAt(0).toUpperCase() + model.slice(1).replace(/_/g, ' ');
            select.appendChild(option);
        });
        modelList.appendChild(select);
        select.addEventListener('change', () => {
            setSelectedModels();
            loadBenchmarkResults(serializeSelectedModels());
        });
    }

    // Read the current selection from the multi-select dropdown. When no
    // option is selected, keep the last active model so a run can still
    // target a single model.
    function readModelSelection(select) {
        if (!select || select.selectedIndex === -1) {
            const value = select.value;
            if (value !== '') {
                setSelectedModels();
            }
            return window.__activeModel || (window.__selectedModels[0] || '');
        }
        const selected = [];
        for (let i = 0; i < select.options.length; i++) {
            if (select.options[i].selected) selected.push(select.options[i].value);
        }
        setSelectedModels();
        return selected;
    }

    function setSelectedModels() {
        const select = document.getElementById('model-select');
        const models = readModelSelection(select);
        window.__selectedModels = models;
        window.__selectedEngine = engineSelect.value;
        if (models.length === 1) {
            window.__activeModel = models[0];
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
        request.base_url = engineBaseURL(window.__selectedEngine);
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
        resultsContainer.innerHTML = '';
        if (resultsContainer.querySelector('.run-button')) return;

        if (!results || results.length === 0) {
            const label = modelNames.length === 1
                ? modelNames[0]
                : modelNames.join(', ');
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

        window.__selectedModels = modelNames;
        const header = '<div class="results-header">' +
            '<span class="results-header-title">Benchmark Results</span>' +
            '<span class="results-header-models">';
        modelNames.forEach((name, index) => {
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
        const benchmarkType = typeFilter.value;
        const params = new URLSearchParams();
        params.append('models', serializeSelectedModels(modelNames));
        if (benchmarkType) params.append('type', benchmarkType);
        const response = await fetch('/api/results?' + params.toString());
        if (!response.ok) throw new Error('Failed to fetch results.');
        const data = await response.json();
        displayResults(data.results, serializeSelectedModels(modelNames), benchmarkType);
    }

    function serializeSelectedModels(modelNames) {
        const names = modelNames && modelNames.length ? modelNames : window.__selectedModels;
        if (!names || names.length === 0) return '';
        return names.join(',');
    }

    function initializeListeners() {
        typeFilter.addEventListener('change', (e) => {
            loadBenchmarkResults(serializeSelectedModels());
        });
        engineSelect.addEventListener('change', (e) => {
            loadModels(e.target.value);
        });
        loadEngines();
    }

    initializeListeners();
});
