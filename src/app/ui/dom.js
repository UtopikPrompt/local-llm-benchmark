// DOM helpers.
//
// Centralizes the handful of DOM operations the dashboard needs so the
// feature modules (``models.js``, ``results.js``, ``views.js``) do not reach
// for ``document.getElementById`` / ``innerHTML`` / ``classList`` directly.
//
// The helpers are intentionally small and synchronous: every caller already
// runs inside a macro-task or an ``async`` function, so there is no need to
// wrap them in ``queueMicrotask`` / promises.
const dom = {
  // ``document.getElementById`` returns only the FIRST matching element, which
  // is the hidden Dashboard panel while the Benchmark view is active. By
  // always passing an explicit root element we avoid silently populating the
  // wrong (hidden) container.
  getEl(root, id) {
    return root ? root.querySelector(id) : document.getElementById(id)
  },

  setText(el, text) {
    if (!el) return
    el.textContent = text
  },

  create(tag, props, children) {
    const el = document.createElement(tag)
    if (props) {
      for (const [key, value] of Object.entries(props)) {
        if (value === undefined) continue
        if (key === "class") {
          el.className = value
        } else if (key === "html") {
          el.innerHTML = value
        } else if (key.startsWith("on") && typeof value === "function") {
          el.addEventListener(key.slice(2).toLowerCase(), value)
        } else if (key === "dataset" && typeof value === "object") {
          for (const [k, v] of Object.entries(value)) el.dataset[k] = v
        } else if (key === "style" && typeof value === "object") {
          for (const [k, v] of Object.entries(value)) el.style[k] = v
        } else if (key === "type" && typeof value === "string") {
          el.setAttribute("type", value)
        } else {
          el.setAttribute(key, value)
        }
      }
    }
    if (children) {
      if (typeof children === "string") el.textContent = children
      else for (const c of children) el.append(c)
    }
    return el
  },

  addClass(el, className) {
    if (el) el.classList.add(className)
  },

  removeClass(el, className) {
    if (el) el.classList.remove(className)
  },

  toggleClass(el, className, force) {
    if (el) el.classList.toggle(className, force)
  },

  isVisible(el) {
    return !!el && el.offsetParent !== null && el.offsetParent !== undefined
  },
}

export default dom
