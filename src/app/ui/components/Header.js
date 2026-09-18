/**
 * Lazy-loaded Header Component
 * 
 * Renders the navigation header with view tabs.
 * Dynamically imported to enable code splitting.
 * 
 * @module components/Header
 */

import dom from '../dom.js'
import state from '../state.js'
import { VIEWS } from './views.js'

/**
 * Header component - renders navigation tabs
 */
export function Header() {
  const header = dom.create('header', { class: 'app-header' }, [
    dom.create('h1', { class: 'app-title' }, 'LLM Benchmark'),
    dom.create('nav', { class: 'nav-tabs' }, ...VIEWS.map(view => [
      dom.create('button', {
        class: `nav-tab ${state.activeView === view ? 'active' : ''}`,
        onclick: `switchView('${view}')`,
        dataView: view,
        'aria-label': `Switch to ${view} view`
      }, view.charAt(0).toUpperCase() + view.slice(1))
    ]))
  ])
  
  return header
}

/**
 * Lazy Header component for code splitting
 */
export const LazyHeader = () => {
  return import('./components/Header.js').then(module => module.Header)()
}

// Export both sync and lazy versions
export { LazyHeader }
