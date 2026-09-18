/**
 * Lazy-loaded BenchmarkRunner Component
 * 
 * Renders the benchmark runner panel.
 * Dynamically imported to enable code splitting.
 * 
 * @module components/BenchmarkRunner
 */

import dom from '../dom.js'
import state from '../state.js'
import { engines } from '../models.js'
import { challenges } from '../challenges.js'

/**
 * BenchmarkRunner component - renders benchmark execution UI
 */
export function BenchmarkRunner() {
  const engineList = engines.list()
  const availableChallenges = challenges.list()
  
  const panel = dom.create('section', { class: 'benchmark-panel' }, [
    dom.create('h2', { class: 'panel-title' }, 'Benchmark Runner'),
    dom.create('div', { class: 'benchmark-controls' }, [
      dom.create('div', { class: 'engine-select' }, [
        dom.create('label', 'Engine: '),
        dom.create('select', { id: 'benchmark-engine' }, 
          engineList.map(engine => [
            dom.create('option', { value: engine.id }, engine.name)
          ])
        )
      ]),
      dom.create('div', { class: 'challenge-select' }, [
        dom.create('label', 'Challenge: '),
        dom.create('select', { id: 'benchmark-challenge' }, 
          availableChallenges.map(challenge => [
            dom.create('option', { value: challenge.id }, challenge.name)
          ])
        )
      ]),
      dom.create('button', {
        class: 'btn btn-success',
        onclick: `runBenchmark()`
      }, 'Run Benchmark'),
      dom.create('button', {
        class: 'btn btn-secondary',
        onclick: `cancelBenchmark()`
      }, 'Cancel')
    ]),
    dom.create('div', { class: 'benchmark-progress' }, [
      dom.create('div', { class: 'progress-bar' }, [
        dom.create('div', { class: 'progress-fill' }, [
          dom.create('span', 'Running...')
        ])
      ])
    ])
  ])
  
  return panel
}

/**
 * BenchmarkRunner component - renders benchmark execution UI (sync version)
 */
export function LazyBenchmarkRunner() => {
  return import('./components/BenchmarkRunner.js').then(module => module.BenchmarkRunner)()
}

// Export both sync and lazy versions
export { LazyBenchmarkRunner }

/**
 * Benchmark execution handler
 */
export async function runBenchmark() {
  const engineId = document.getElementById('benchmark-engine').value
  const challengeId = document.getElementById('benchmark-challenge').value
  
  if (!engineId || !challengeId) {
    alert('Please select an engine and challenge')
    return
  }
  
  const engine = engines.find(e => e.id === engineId)
  const challenge = challenges.find(c => c.id === challengeId)
  
  if (!engine || !challenge) {
    alert('Engine or challenge not found')
    return
  }
  
  const result = await engine.runChallenge(challenge)
  
  // Store benchmark result
  const benchmarkResult = {
    id: Date.now().toString(),
    engineId,
    challengeId,
    timestamp: Date.now(),
    ...result
  }
  
  // Dispatch custom event for result
  window.dispatchEvent(new CustomEvent('benchmark-complete', {
    detail: benchmarkResult
  }))
  
  console.log('Benchmark complete:', benchmarkResult)
}

/**
 * Benchmark cancellation handler
 */
export async function cancelBenchmark() {
  // Cancel any ongoing benchmark
  window.dispatchEvent(new CustomEvent('benchmark-cancel'))
  console.log('Benchmark cancelled')
}
