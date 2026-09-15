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
  card.setAttribute('data-id', task.id)
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
    '<div class="challenge-card-tags">' + tagsHtml + '</div>' +
    '<div class="challenge-checkboxes">' +
      '<button class="challenge-checkbox select-all" type="button" aria-pressed="false">' +
        '<input type="checkbox" class="challenge-checkbox" aria-hidden="true" />' +
        'select all' +
      '</button>' +
    '</div>' +
    '<span class="check-count">0/0</span>' +
    '<div class="bench-status">' +
      '<span class="bench-status-text">Not run</span>' +
      '<div class="bench-progress-bar"><div class="bench-status-bar"></div></div>' +
    '</div>'
  wireChallengeCard(card)
  return card
}

// Wire up the per-card checkboxes: the select-all button toggles every
// per-card checkbox on the same card, and each per-card checkbox updates the
// select-all state, the check-count span, and (via perCardStatus) the
// per-card status bar when results come back.
//
// Note: the select-all button's visible checkbox is NOT a per-card checkbox,
// so it must be excluded from the per-card selection queries.
function wireChallengeCard(card) {
  const selectAll = card.querySelector('.challenge-checkbox select-all .challenge-checkbox')
  const perCard = card.querySelectorAll('.challenge-checkboxes .challenge-checkbox')
  if (selectAll) {
    selectAll.addEventListener('change', () => {
      const checked = selectAll.checked
      for (const cb of perCard) cb.checked = checked
      syncSelectAll(selectAll, perCard)
      updateCheckCount(card, perCard)
    })
  }
  for (const cb of perCard) {
    cb.addEventListener('change', () => {
      const selectAll = card.querySelector('.challenge-checkbox select-all .challenge-checkbox')
      const remaining = card.querySelectorAll('.challenge-checkboxes .challenge-checkbox:not(:checked)').length
      if (remaining === 0) {
        selectAll.checked = true
        selectAll.setAttribute('aria-pressed', 'true')
      } else if (perCard.length === remaining) {
        selectAll.checked = false
        selectAll.setAttribute('aria-pressed', 'false')
      }
      syncSelectAll(selectAll, perCard)
      updateCheckCount(card, perCard)
    })
  }
}

// Sync the select-all checkbox's visible state to the actual per-card
// selection: all -> pressed, some -> unpressed, none -> unpressed.
function syncSelectAll(selectAll, perCard) {
  if (!selectAll || perCard.length === 0) return
  const all = perCard.every((cb) => cb.checked)
  const some = perCard.some((cb) => cb.checked)
  if (all) {
    selectAll.checked = true
    selectAll.setAttribute('aria-pressed', 'true')
  } else {
    selectAll.checked = false
    selectAll.setAttribute('aria-pressed', 'false')
  }
}

// Update the "x/total" check-count span on a challenge card.
function updateCheckCount(card, perCard) {
  const countEl = card.querySelector('.check-count')
  if (countEl) countEl.textContent = `${perCard.filter((cb) => cb.checked).length}/${perCard.length}`
}

// Reflect a per-challenge result into the card's status bar.
// status: 'not-run' | 'pass' | 'fail' | 'error'
function perCardStatus(taskId, status) {
  const bar = document.querySelector(`.challenge-card[data-id="${taskId}"] .bench-status-bar`)
  const text = document.querySelector(`.challenge-card[data-id="${taskId}"] .bench-status-text`)
  if (!bar || !text) return
  const labels = { pass: 'Pass', fail: 'Fail', error: 'Error', 'not-run': 'Not run' }
  const pct = { 'not-run': 0, pass: 100, fail: 0, error: 0 }
  text.textContent = labels[status] || 'Not run'
  bar.style.width = `${pct[status] || 0}%`
  bar.classList.remove('complete', 'partial')
  if (status === 'pass') bar.classList.add('complete')
  else if (status === 'fail' || status === 'error') bar.classList.add('partial')
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
  const data = await response.json()
  // ``/api/tasks`` returns ``{"tasks": [...]}`` (a wrapper object), never a
  // bare array; normalize defensively so downstream ``Array`` methods work.
  state.tasks = Array.isArray(data) ? data : data.tasks || []
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

export { loadChallenges, toggleCategoryFilter, applyChallengeFilter, renderChallengeCard, perCardStatus }
