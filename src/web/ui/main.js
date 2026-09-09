// main.js — renders benchmark results using the Row data schema
// (engine, model, category, ttft_s, tok_per_s, iters_per_s, quality_*).

document.addEventListener('DOMContentLoaded', () => {
    const engineSelect = document.getElementById('engine-select');
    const modelList = document.getElementById('model-list');
    const resultsContainer = document.getElementById('results-container');
    const typeFilter = document.getElementById('benchmark-type-filter');

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
        loadBenchmarkResults(modelName);
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

        if (!results || results.length === 0) {
            resultsContainer.innerHTML =
                '<div class="empty-state">' +
                    '<div class="empty-icon">📊</div>' +
                    '<div class="empty-title">No results yet</div>' +
                    '<div style="color:var(--text-secondary);font-size:0.85em;">Run a benchmark to populate results.</div>' +
                '</div>';
            return;
        }

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
