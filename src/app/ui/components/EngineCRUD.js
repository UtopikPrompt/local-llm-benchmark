/**
 * Lazy-loaded EngineCRUD Component
 * 
 * Renders the engine CRUD operations panel.
 * Dynamically imported to enable code splitting.
 * 
 * @module components/EngineCRUD
 */

import dom from '../dom.js'
import state from '../state.js'
import { engines } from '../models.js'

/**
 * EngineCRUD component - renders engine management UI
 */
export function EngineCRUD() {
  const engineList = engines.list()
  
  const panel = dom.create('section', { class: 'engine-panel' }, [
    dom.create('h2', { class: 'panel-title' }, 'Engines'),
    dom.create('div', { class: 'engine-actions' }, [
      dom.create('button', {
        class: 'btn btn-primary',
        onclick: `createEngine()`
      }, '+ Add Engine'),
      dom.create('button', {
        class: 'btn btn-secondary',
        onclick: `resetEngineSelection()`
      }, 'Reset Selection')
    ]),
    dom.create('table', { class: 'engine-table' }, [
      dom.create('thead', [
        dom.create('tr', [
          dom.create('th', 'Name'),
          dom.create('th', 'Provider'),
          dom.create('th', 'Models'),
          dom.create('th', 'Actions')
        ])
      ]),
      dom.create('tbody', engineList.map(engine => [
        dom.create('tr', [
          dom.create('td', dom.escape(engine.name)),
          dom.create('td', dom.escape(engine.provider)),
          dom.create('td', engine.models?.length || 0),
          dom.create('td', [
            dom.create('button', {
              class: 'btn btn-sm btn-edit',
              onclick: `editEngine('${engine.id}')`
            }, 'Edit'),
            dom.create('button', {
              class: 'btn btn-sm btn-delete',
              onclick: `deleteEngine('${engine.id}')`
            }, 'Delete')
          ])
        ])
      ]))
    ])
  ])
  
  return panel
}

/**
 * EngineCRUD component - renders engine management UI (sync version)
 */
export function LazyEngineCRUD() => {
  return import('./components/EngineCRUD.js').then(module => module.EngineCRUD)()
}

// Export both sync and lazy versions
export { LazyEngineCRUD }

/**
 * Engine creation handler
 */
export async function createEngine() {
  const name = prompt('Enter engine name:')
  if (!name) return
  
  await state.dispatch({
    type: 'ADD_ENGINE',
    payload: { name }
  })
}

/**
 * Engine edit handler
 */
export async function editEngine(engineId) {
  const engine = engines.find(e => e.id === engineId)
  if (!engine) return
  
  const name = prompt('Enter engine name:')
  if (!name) return
  
  await state.dispatch({
    type: 'UPDATE_ENGINE',
    payload: { id: engine.id, name }
  })
}

/**
 * Engine deletion handler
 */
export async function deleteEngine(engineId) {
  if (!confirm(`Delete engine ${engineId}?`)) return
  
  await state.dispatch({
    type: 'DELETE_ENGINE',
    payload: { id: engineId }
  })
}

/**
 * Reset engine selection handler
 */
export async function resetEngineSelection() {
  await state.dispatch({
    type: 'RESET_ENGINE_SELECTION'
  })
}

/**
 * Escape HTML for safe rendering
 */
export function escape(text) {
  const div = dom.create('div')
  div.textContent = text
  return div.innerHTML
}
