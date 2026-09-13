// Challenge corpus view (Tasks tab).
//
// Renders the task cards fetched from ``/api/tasks`` and handles the category
// filter. The task list is loaded once into ``state.tasks``; the cards are
// (re)rendered on demand by the filter.
import dom from './dom.js'
import state from './state.js'
import { escapeHtml } from './results.js'

// Module-level: active challenge category filter (null = show all).
let activeCategory = null

// Render a single challenge card element for the given task.
function renderChallengeCard(task) {
  const card = document.createElement('div')
  card.className = 'challenge-card'
  card.setAttribute('data-category', task.category || '')
  const tags = []
  if (task.system) tags.push('<span class="tag">system</span>')
  if (task.expected) tags.push('<span class="tag">expected</span>')
  const tagsHtml = tags.join('') || '<span class="tag">prompt</span>'
  card.innerHTML =
    '<div class="challenge-card-header">' +
      '<span class="challenge-card-title">' + escapeHtml(task.id) + '</span>' +
      '<span class="chip small">' + escapeHtml(task.category) + '</span>' +
    '</div>' +
    '<div class="challenge-card-body">' +
      '<p class="challenge-card-prompt">' + escapeHtml(task.prompt) + '</p>' +
    '</div>' +
    '<div class="challenge-card-tags">' + tagsHtml + '</div>'
  return card
}

function applyChallengeFilter() {
  if (!activeCategory) {
    // No active filter: show every task.
    const listEl = dom.getEl(document, '#challenges-list')
    const tasks = state.tasks || []
    listEl.innerHTML = ''
    if (tasks.length === 0) {
      listEl.innerHTML = '<p class="empty">No tasks found.</p>'
      return
    }
    for (const task of tasks) listEl.appendChild(renderChallengeCard(task))
    state.resultsRendered = true
    return
  }
  const listEl = dom.getEl(document, '#challenges-list')
  const tasks = (state.tasks || []).filter((t) => t.category === activeCategory)
  listEl.innerHTML = ''
  if (tasks.length === 0) {
    listEl.innerHTML =
      '<p class="empty">No tasks found in category "' + escapeHtml(activeCategory) + '".</p>'
    return
  }
  for (const task of tasks) listEl.appendChild(renderChallengeCard(task))
}

// Toggle the category filter for the given category.
function toggleCategoryFilter(category) {
  activeCategory = activeCategory === category ? null : category
  const chips = document.querySelectorAll('#challenge-categories .chip')
  for (const chip of chips) {
    const chipCategory = chip.getAttribute('data-category')
    if (chipCategory === activeCategory) {
      chip.classList.add('active')
      chip.setAttribute('aria-pressed', 'true')
    } else {
      chip.classList.remove('active')
      chip.setAttribute('aria-pressed', 'false')
    }
  }
  applyChallengeFilter()
}

// Load the challenge corpus from ``/api/tasks``.
async function loadChallenges() {
  const response = await fetch('/api/tasks')
  if (!response.ok) return
  state.tasks = await response.json()
  const categories = [...new Set((state.tasks || []).map((t) => t.category).filter(Boolean))]
  const categoriesEl = dom.getEl(document, '#challenge-categories')
  if (!categoriesEl) return
  categoriesEl.innerHTML = ''
  for (const category of categories) {
    const chip = document.createElement('button')
    chip.className = 'chip'
    chip.setAttribute('data-category', category)
    chip.setAttribute('aria-pressed', 'false')
    chip.textContent = category
    chip.addEventListener('click', () => toggleCategoryFilter(category))
    categoriesEl.appendChild(chip)
  }
  applyChallengeFilter()
}

export { loadChallenges, toggleCategoryFilter, applyChallengeFilter, renderChallengeCard }
