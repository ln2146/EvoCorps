# Intervention Flow 2x2 Tabs Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Make the role selector a compact 2×2 grid (instead of 1×4 row) and show only 1 key subtitle line per role (A). Improve the “static/empty” copy in the single role detail panel.

**Architecture:** Keep the “single role detail panel + review mode A” structure. In UI, change the role selector to a 2-column grid and compute a per-role subtitle from the role’s 4-line summary. In router, add one extra summary field update for Leader “发布” so the tab subtitle can be meaningful.

**Tech Stack:** React + TypeScript + Tailwind + Vitest.

---

### Task 1: Add Leader publish summary update (TDD)

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRouter.ts`
- Test: `frontend/src/lib/interventionFlow/logRouter.test.ts`

**Step 1: Write failing test**
- Given a line `💬 👑 Leader comment 1 on post ...`, Leader summary line 4 becomes `发布: 1` (or equivalent).

**Step 2: Run tests to verify it fails**
Run: `cd frontend && npm test`
Expected: FAIL (publish summary not updated).

**Step 3: Minimal implementation**
- In `applySummaryUpdates()`, parse leader comment IDs/count and update `roles.Leader.summary[3]`.

**Step 4: Re-run tests**
Run: `cd frontend && npm test`
Expected: PASS.

---

### Task 2: Refactor selector to 2×2 + 1-line subtitle per role

**Files:**
- Modify: `frontend/src/pages/DynamicDemo.tsx`

**Step 1: Implement 2×2 grid**
- Change `RoleTabsRow` layout to `grid grid-cols-2 gap-2`.
- Reduce padding and badge size for denser footprint.

**Step 2: Implement 1-line subtitle**
- Subtitle mapping:
  - Analyst: `summary[0]`
  - Strategist: `summary[0]`
  - Leader: `summary[3]`
  - Amplifier: `summary[3]`

**Step 3: Improve empty/static copy**
- In the detail panel, when no live lines and no `after`, show:
  - `等待系统输出…`
  - `开启舆论平衡后自动接入实时日志流`

**Step 4: Verify**
Run: `cd frontend && npm test`
Expected: PASS.

Run: `cd frontend && npm run build`
Expected: exit 0.

