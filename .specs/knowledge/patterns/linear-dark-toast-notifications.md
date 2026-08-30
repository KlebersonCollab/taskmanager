# Pattern: Non-Blocking Linear Dark Toast Notifications

## Context
Standard browser `alert()` and `confirm()` dialogs freeze the JavaScript event loop, block DOM updates, and interrupt the user experience. They also break visual immersion in dark-themed enterprise dashboards.

## Solution Pattern
Implement a decoupled Toast Controller in the frontend with CSS transitions and auto-dismiss timers:

```javascript
const toast = {
  show(title, msg = "", type = "info", duration = 4000) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
    const elem = document.createElement("div");
    elem.className = `toast toast-${type}`;
    elem.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <div class="toast-body">
        <div class="toast-title">${escapeHtml(title)}</div>
        ${msg ? `<div class="toast-msg">${escapeHtml(msg)}</div>` : ""}
      </div>
      <button class="toast-close" onclick="this.closest('.toast').remove()">&times;</button>
    `;
    container.appendChild(elem);
    requestAnimationFrame(() => elem.classList.add("show"));

    if (duration > 0) {
      setTimeout(() => {
        elem.classList.remove("show");
        setTimeout(() => elem.remove(), 350);
      }, duration);
    }
  },
  success(title, msg) { this.show(title, msg, "success", 4000); },
  error(title, msg) { this.show(title, msg, "error", 5500); },
  warning(title, msg) { this.show(title, msg, "warning", 4500); },
  info(title, msg) { this.show(title, msg, "info", 4000); },
};
```

## Benefits
- 100% non-blocking; UI continues streaming WebSocket events in the background.
- Semantic color coding matching `DESIGN.md` tokens (Emerald green, Amber warning, Crimson error, Slate info).
