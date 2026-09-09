// main.js — renders benchmark results using the Row data schema
// (engine, model, category, ttft_s, tok_per_s, iters_per_s, quality_*).

document.addEventListener('DOMContentLoaded', () => {
    const engineSelect = document.getElementById('engine-select');
    const modelList = document.getElementById('model-list');
    const resultsContainer = document.getElementById('results-container');
    const typeFilter = document.getElementById('benchmark-type-filter');

    // Track the currently selected model and engine so the "Run benchmark"
    // button triggers a run for exactly the model being viewed.
    window.__selectedModel = '';
    window.__selectedEngine = '';

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
        document.querySelectorAll('#model-list a').forEach(a => a.classList.remove('active'));
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
        models.forEach(model => {
            const link = document.createElement('a');
            link.href = '#';
            link.textContent = model.charAt(0).toUpperCase() + model.slice(1).replace(/_/g, ' ');
            link.setAttribute('data-model', model);
            link.addEventListener('click', (e) => {
                e.preventDefault();
                setActiveModel(link, model);
            });
            modelList.appendChild(link);
        });
    }

    function setActiveModel(element, modelName) {
        document.querySelectorAll('#model-list a').forEach(a => a.classList.remove('active'));
        element.classList.add('active');
        window.__selectedModel = modelName;
        window.__selectedEngine = engineSelect.value;
        loadBenchmarkResults(modelName);
    }

    // Build the request body for POST /run using the currently selected
    // engine (its base_url) and model.
    function buildRunRequest() {
        const request = {};
        const base_url = engineBaseURL(window.__selectedEngine);
        if (base_url) request.base_url = base_url;
        if (window.__selectedModel) request.model = window.__selectedModel;
        return request;
    }

    // Trigger a benchmark run for the selected model and refresh the
    // results table once the saved report is available.
    async function runBenchmark() {
        const button = resultsContainer.querySelector('.run-button');
        if (button) button.disabled = true;
        const note = resultsContainer.querySelector('.run-note');
        if (note) note.textContent = 'Running benchmark…';
        try {
            const response = await fetch('/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildRunRequest()),
            });
            if (!response.ok) throw new Error('Failed to run benchmark.');
            if (note) note.textContent = '';
            await loadBenchmarkResults(window.__selectedModel);
        } catch (error) {
            console.error('Error running benchmark:', error);
            if (note) note.textContent = 'Error: ' + error.message;
            await loadBenchmarkResults(window.__selectedModel);
        } finally {
            if (button) button.disabled = false;
        }
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

    function displayResults(results, modelName, benchmarkType) {
        resultsContainer.innerHTML = '';
        if (resultsContainer.querySelector('.run-button')) return;

        if (!results || results.length === 0) {
            const engineLabel = window.__selectedEngine
                ? window.__selectedEngine
                : 'the selected model';
            resultsContainer.innerHTML =
                '<div class="run-state">' +
                    '<div class="run-subtitle">No results yet for ' +
                        escapeHtml(engineLabel) + '.</div>' +
                    '<button class="run-button" id="run-button">Run benchmark</button>' +
                    '<div class="run-note" id="run-note"></div>' +
                '</div>';
            resultsContainer.querySelector('#run-button').addEventListener('click', runBenchmark);
            return;
        }

        window.__selectedModel = modelName;
        const rows = results.map(renderResult).join('');
        resultsContainer.innerHTML =
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

    async function loadBenchmarkResults(modelName) {
        const benchmarkType = typeFilter.value;
        const params = new URLSearchParams();
        if (modelName) params.append('model', modelName);
        if (benchmarkType) params.append('type', benchmarkType);
        const response = await fetch('/api/results?' + params.toString());
        if (!response.ok) throw new Error('Failed to fetch results.');
        const data = await response.json();
        displayResults(data.results, modelName, benchmarkType);
    }

    function initializeListeners() {
        typeFilter.addEventListener('change', (e) => {
            loadBenchmarkResults('');
        });
        engineSelect.addEventListener('change', (e) => {
            loadModels(e.target.value);
        });
        modelList.addEventListener('click', (e) => {
            const target = e.target.closest('#model-list a');
            if (target) {
                e.preventDefault();
                setActiveModel(target, target.getAttribute('data-model'));
            }
        });
        loadEngines();
    }

    initializeListeners();
});
