# Intervention Flow Tabs + Single Role Panel Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Change the right-side intervention flow display to a top horizontal row of 4 role tabs and a single detail panel that shows only the currently selected role. Clicking a tab enters “review mode” (A): the UI does not auto-jump back when `activeRole` changes, until the user chooses to follow again.

**Architecture:** Keep SSE log stream + `routeLogLine()` state machine unchanged. Add a small pure helper to compute the effective role to display (`selectedRole ?? activeRole ?? 'Analyst'`). In UI, render a tabs row from the existing roles list; detail panel reads from `state.roles[effectiveRole]`. Add a “跟随当前” control to clear `selectedRole` back to `null`.

**Tech Stack:** React + TypeScript + Tailwind + Vitest.

---

### Task 1: Add Pure Selection Helper + Unit Tests (TDD)

**Files:**
- Create: `frontend/src/lib/interventionFlow/selection.ts`
- Test: `frontend/src/lib/interventionFlow/selection.test.ts`

**Step 1: Write the failing test**
- Test cases:
  - `selectedRole` wins over `activeRole`.
  - When `selectedRole` is `null`, follow `activeRole`.
  - When both are `null`, default to `'Analyst'` (stable empty state).

**Step 2: Run tests to verify it fails**
Run: `cd frontend && npm test`
Expected: FAIL because helper doesn’t exist.

**Step 3: Write minimal implementation**
- Export `computeEffectiveRole(selectedRole, activeRole): Role`.

**Step 4: Re-run tests**
Run: `cd frontend && npm test`
Expected: PASS.

---

### Task 2: Refactor Right Panel UI To Tabs + Single Detail Card (TDD-light)

**Files:**
- Modify: `frontend/src/pages/DynamicDemo.tsx`
- (Optional) Create: `frontend/src/pages/DynamicDemo.interventionFlow.test.tsx` (only if React test infra already exists)

**Step 1: Implement tabs row**
- Replace the current 4 stacked cards with:
  - A top row `Tabs` (4 items) showing: label + status badge.
  - Clicking any tab sets `selectedRole` and enters review mode.
  - Add “跟随当前” button that resets `selectedRole` to `null`.

**Step 2: Implement single detail panel**
- Render one card using the *selected/effective* role:
  - Header shows role label + status + (if review mode) “回看中”.
  - Show the 4-line summary (already in state) + event stream (during) if `effectiveRole === state.activeRole`, else show `after` snapshot if present.
  - Keep noise filtering + compression in `routeLogLine()` (no timestamps).

**Step 3: Ensure reset behavior**
- When `enableEvoCorps` becomes false (流断开/状态清空) also reset `selectedRole` to `null` so UI returns to follow mode.

**Step 4: Verify**
Run: `cd frontend && npm test`
Expected: PASS.

Run: `cd frontend && npm run build`
Expected: exit 0.

---

### Task 3: Manual Verification With Real Logs

**Files:**
- None

**Checks:**
- Top row shows 4 roles; only one detail panel visible.
- When active role changes due to logs, detail panel follows *unless* user clicked a tab (review mode A).
- Click “跟随当前” restores auto-follow of `activeRole`.
- After `⚖️ Activating Echo Agent cluster...` amplifier sticky attribution still works (because router logic unchanged).

