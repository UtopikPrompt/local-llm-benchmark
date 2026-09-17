// Challenge corpus view (Tasks tab).
//
// Renders the task cards fetched from ``/api/tasks`` and handles the category
// filter. The task list is loaded once into ``state.tasks``; the cards are
// (re)rendered on demand by the filter.
import dom from './dom.js'
import state from './state.js'
import { escapeHtml } from './utils.js'

// Module-level: active challenge category filter (null = show all).
let activeCategory = null

// Reference to the panel-level "Select all challenges" global checkbox
// (class ``global-select-all``, id ``all-challenges-checkbox``). Mirrors
// ``models.js`` which renders an equivalent ``#all-models-checkbox``. The
// global checkbox mirrors the per-card selection: checked => every
// challenge selected, unchecked => none selected, indeterminate => partial.
let globalSelectAllCheckbox = null

// --- Per-card checkbox <-> global checkbox sync (mirrors models.js). ------
// Count a challenge as "selected" when its per-card checkbox is checked.
function countSelectedChallenges() {
  const checkboxes = document.querySelectorAll('.challenge-checkboxes .challenge-checkbox')
  return {
    total: checkboxes.length,
    selected: Array.from(checkboxes).filter((cb) => cb.checked).length
  }
}

// Reconcile the global "Select all challenges" checkbox with the current
// per-card selection. Uses the indeterminate pattern (mirrors
// ``syncSelectAll`` in models.js): indeterminate when some but not all
// challenges are selected.
function syncGlobalSelectAll() {
  if (!globalSelectAllCheckbox) return
  const { total, selected } = countSelectedChallenges()
  globalSelectAllCheckbox.indeterminate = total > 0 && selected > 0 && selected < total
  globalSelectAllCheckbox.checked = total > 0 && selected === total
}

// Select every currently-unselected challenge. Updates
// ``state.selectedChallenges`` (an array of task ids).
function selectAllChallenges() {
  if (!globalSelectAllCheckbox) return
  const checkboxes = document.querySelectorAll('.challenge-checkboxes .challenge-checkbox')
  const ids = Array.from(checkboxes)
    .filter((cb) => !cb.checked)
    .map((cb) => cb.getAttribute('data-task'))
  for (const cb of checkboxes) cb.checked = true
  updateCheckCounts()
  state.selectedChallenges = ids
  syncGlobalSelectAll()
  updateGlobalLabel()
}

// Clear every per-card challenge selection. Resets
// ``state.selectedChallenges`` to an empty array.
function deselectAllChallenges() {
  if (!globalSelectAllCheckbox) return
  const checkboxes = document.querySelectorAll('.challenge-checkboxes .challenge-checkbox')
  for (const cb of checkboxes) cb.checked = false
  state.selectedChallenges = []
  syncGlobalSelectAll()
  updateGlobalLabel()
}

// Re-sync the global checkbox purely from ``state.selectedChallenges``.
// Used when the backend resets the selection (e.g. after a batch run).
function applySelectedChallengesFromState() {
  const checkboxes = document.querySelectorAll('.challenge-checkboxes .challenge-checkbox')
  const selectedIds = new Set(state.selectedChallenges || [])
  for (const cb of checkboxes) cb.checked = selectedIds.has(cb.getAttribute('data-task'))
  syncGlobalSelectAll()
  updateCheckCounts()
  updateGlobalLabel()
}

// Toggle the global checkbox: checked => select all, unchecked => clear all.
function toggleGlobalSelectAll(checkbox) {
  if (checkbox.checked) selectAllChallenges()
  else deselectAllChallenges()
}

// Render the panel-level "Select all challenges" global checkbox above the
// challenge list. Mirrors ``renderSelectAllCheckbox`` in models.js.
function renderGlobalSelectAllCheckbox(container) {
  const checkbox = document.createElement('input')
  checkbox.type = 'checkbox'
  checkbox.className = 'global-select-all'
  checkbox.id = 'all-challenges-checkbox'
  checkbox.setAttribute('aria-label', 'Select all challenges')
  checkbox.indeterminate = false
  checkbox.checked = false

  const label = document.createElement('label')
  label.className = 'challenge-checkbox-group'
  label.appendChild(checkbox)
  const count = document.createElement('span')
  count.className = 'model-label'
  label.appendChild(count)
  container.appendChild(label)
  globalSelectAllCheckbox = checkbox
  return label
}

// Find (or create) the panel container for the panel-level global checkbox.
// The challenges panel ships an HTML slot ``#all-challenges-checkbox`` in its
// toolbar; reuse it when present so there is a single source of truth for the
// global checkbox's id/class, otherwise fall back to a new container above the
// challenge list.
function globalSelectAllContainer() {
  const slot = dom.getEl(document, '#all-challenges-checkbox')
  if (slot) return slot
  const listEl = dom.getEl(document, '#challenge-items-list')
  if (listEl) {
    const wrapper = document.createElement('div')
    wrapper.className = 'challenge-global-select-all'
    wrapper.style.display = 'flex'
    wrapper.style.justifyContent = 'flex-end'
    listEl.parentNode.insertBefore(wrapper, listEl)
    return wrapper
  }
  return null
}

// Recompute the global checkbox label from the current selection count.
function updateGlobalLabel() {
  const { total, selected } = countSelectedChallenges()
  const countEl = globalSelectAllCheckbox ? globalSelectAllCheckbox.closest('.challenge-checkbox-group').querySelector('.model-label') : null
  if (countEl) countEl.setAttribute('data-count', String(selected))
}

// Re-render the global checkbox count span after a per-card change.
function updateGlobalLabelFromState() {
  const { selected } = countSelectedChallenges()
  const countEl = globalSelectAllCheckbox ? globalSelectAllCheckbox.closest('.challenge-checkbox-group').querySelector('.model-label') : null
  if (countEl) countEl.setAttribute('data-count', String(selected))
}

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
    syncGlobalSelectAll(globalSelectAllCheckbox)
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
  syncGlobalSelectAll(globalSelectAllCheckbox)
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
  const container = globalSelectAllContainer()
  if (container) renderGlobalSelectAllCheckbox(container)
  applyChallengeFilter()
}

export {
  loadChallenges,
  toggleCategoryFilter,
  applyChallengeFilter,
  renderChallengeCard,
  perCardStatus,
  renderGlobalSelectAllCheckbox,
  syncGlobalSelectAll,
  toggleGlobalSelectAll,
  selectAllChallenges,
  deselectAllChallenges,
  applySelectedChallengesFromState,
  countSelectedChallenges,
}
