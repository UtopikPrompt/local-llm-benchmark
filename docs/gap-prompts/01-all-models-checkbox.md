# Gap #1 — Missing "Select All Models" (Benchmark Panel left menu)

**ADR obligation:** ADR 0003, §2.1 — "A global checkbox to select all models across all engines must be provided in the Benchmark Panel's left menu."

**Prompt:**

> In the dashboard's Benchmark Panel left menu, there is no global checkbox to select all models.
> Add one in `web/ui/models.js`.

**Requirements:**
1. Locate the model-rendering function that builds the per-model `<label>` / checkbox markup.
2. Add a **global "Select all models" checkbox** rendered above the engine/model list.
3. Toggle logic:
   - Checked → select every currently-unselected model, mirroring `setSelectedModels`.
   - Unchecked → clear `state.selectedModels`.
4. Set the checkbox `indeterminate` when some — but not all — models are selected.
5. Re-render the model list when the global checkbox state changes so individual checkboxes and
   indeterminate state update correctly.
6. Keep the run button disabled while `state.selectedModels.length === 0`.

**Acceptance test:** With no models selected, check "Select all models" → all boxes ticked.
Uncheck one individually → global box becomes indeterminate. Select all again → all ticked.
Uncheck the global box → all deselected, run button disabled.
