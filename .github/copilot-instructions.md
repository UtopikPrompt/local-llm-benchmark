# Operating Manual for Ornith-1.5 — repo-template

Apply these rules to all changes in this repository. Treat this as the always-loaded core of the
operating manual; the generic engineering standards live in the on-demand `/engineering-standards`
skill, loaded only when a task needs them.

## Always-loaded core — keep this section small

- **Scope** — the one rule that makes this repo behave differently from any other.
- **Just-in-time load/compact** — the context-window discipline that keeps this window small.
- **PR/review** — make the smallest change and summarize with reason, testing, and key risks.

## Everything else — load on demand

Generic engineering standards (implementation, testing, documentation, security, dependencies,
debugging) are shared best practices identical for every Ornith-1.5 code agent, so they live in the
on-demand `/engineering-standards` skill. Load it when a task needs them instead of keeping them in
the always-loaded window.

## Scope

- This is a **code-delivery** repository. Write and edit code as needed to implement the task.
- Keep the token window low by preferring concise prompts, targeted searches, and minimal required
  context — load only what the immediate step needs.

## Just-in-time load/compact

- Keep the context window as small as possible, loading **just in time** and unloading **just in
  time**.
- Load only what the immediate task needs; defer or drop the rest.
- Once a step is complete, stop carrying its context — do not re-read files already read,
  re-derive what is already resolved, or hold spent tool outputs and stale reasoning.
- Prefer careful reading over fast guessing. Make one clear change at a time.
- Be explicit about uncertainty instead of pretending certainty. Do not fabricate logs, outputs, or
  results. When in doubt, choose the most conservative, verifiable solution.

## PR and review expectations

Provide a brief summary, reason, testing performed, and key risks for significant changes.

For significant changes provide:

### Summary

What changed.

### Reason

Why the change was necessary.

### Testing

How it was validated.

### Risks

Potential impacts and mitigations.

- When in doubt, choose the most conservative, verifiable solution.