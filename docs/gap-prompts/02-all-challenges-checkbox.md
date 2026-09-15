# Gap #2 — Missing "Select All Challenges" (Benchmark Panel main container)

**ADR obligation:** ADR 0003, §2.1 — "A global checkbox to select all challenges must be provided in the Benchmark Panel."
ADR 0003, §2.3 — "The challenge list must support per-challenge selection with a global select-all control."

**Prompt:**

> In the Benchmark Panel's main container, there is no global "select all challenges" checkbox,
> even though per-challenge cards already exist. Add one in `web/ui/challenges.js`.

**Requirements:**
1. Locate the per-card rendering function in `web/ui/challenges.js` (the function that builds
   each challenge card and its checkbox).
2. Add a **global "Select all challenges" checkbox** rendered above the challenge list, mirroring
   the existing per-card selection behavior.
3. Toggle logic:
   - Checked → select every currently-unselected challenge (update `state.selectedChallenges`).
   - Unchecked → clear `state.selectedChallenges`.
4. Set the global checkbox `indeterminate` when some — but not all — challenges are selected, using
   the same sync pattern the per-card checkboxes use.
5. When the challenge list is re-rendered (e.g. `loadChallenges`, `applyChallengeFilter`),
   re-sync the global checkbox's checked/indeterminate state from `state.selectedChallenges`
   so filtering does not desync it.

**Acceptance test:** With an empty selection, check "Select all challenges" → all cards ticked.
Uncheck one card individually → global box becomes indeterminate. Select all again → all ticked.
