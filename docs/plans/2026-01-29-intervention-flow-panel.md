# Intervention Flow Panel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the Dynamic Demo right-side panel with a 4-role intervention flow stepper that highlights the active role, streams backend log lines during execution, and freezes each role's start/end copy.

**Architecture:** Introduce a small, testable log-router/state-machine (pure functions) that maps log lines to an `ActiveRole` and per-role `before/during/after` content. The UI consumes this state and renders a stepper; log ingestion can be simulated first and later swapped to real SSE/WS without changing the router.

**Tech Stack:** React + TypeScript (Vite), Vitest for unit tests, Tailwind CSS (existing).

---

### Task 1: Add a log router/state machine module (pure functions)

**Files:**
- Create: `frontend/src/lib/interventionFlow/logRouter.ts`

**Step 1: Write the failing tests**

Create: `frontend/src/lib/interventionFlow/logRouter.test.ts`

Test cases to cover:
- Strips timestamp prefix like `2026-01-28 21:13:09,264 - INFO - `.
- Detects role switches only on strong anchors:
  - Analyst: `Analyst is analyzing`, `Analyst monitoring`, `generate baseline effectiveness report`, `Analyzing viewpoint extremism`
  - Strategist: `Strategist is creating strategy`, `start intelligent strategy creation workflow`, `Use Tree-of-Thought`
  - Leader: `Leader Agent starting USC`, `USC-Generate`, `USC-Vote`, `Output final copy`
  - Amplifier: `Activating Echo Agent cluster`, `Start parallel execution`, `Bulk like`
- Amplifier sticky window:
  - After seeing `Activating Echo Agent cluster`, lines like `Leader comment ...` are attributed to Amplifier (no role switch).
  - Sticky is released when monitoring anchors appear (e.g. `🔄 [Monitoring round`, `Analyst monitoring`, `generate baseline effectiveness report`).
- Per-role freezing:
  - While a role is active, its `during` list appends new cleaned lines (bounded to last N).
  - When role switches away, snapshot gets written to `after` and `during` is reset for the next run.

**Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- --runInBand frontend/src/lib/interventionFlow/logRouter.test.ts`
Expected: FAIL because the module does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- `stripLogPrefix(line: string): string`
- `routeLogLine(prevState, rawLine): nextState`
- Constants for role anchors + monitoring anchors
- Keep `during` as `string[]` without timestamps, bounded to `MAX_DURING_LINES`

**Step 4: Run test to verify it passes**

Same command; Expected: PASS.

---

### Task 2: Add a simulated streaming log source for the demo

**Files:**
- Modify: `frontend/src/pages/DynamicDemo.tsx`

**Step 1: Write the failing test (optional)**

If no frontend test harness exists, skip automated UI tests and rely on manual verification in Task 5.

**Step 2: Implement minimal streaming**

Add:
- A sample `rawLogLines: string[]` (the backend output excerpt, or a trimmed version)
- A timer that pushes one line every `200-400ms` when the demo is running and "舆论平衡" is enabled
- Use the router to compute the stepper state incrementally

---

### Task 3: Replace AgentLogsPanel UI with a role stepper UI (B方案)

**Files:**
- Modify: `frontend/src/pages/DynamicDemo.tsx`

**Step 1: Implement UI**

Render 4 role cards in order: Analyst -> Strategist -> Leader -> Amplifier:
- Current role: larger height, stronger gradient border, show `during` (scroll area, no timestamps).
- Non-current roles: compact (title + status badge), hide `during`.
- Each role shows:
  - `before`: fixed copy (one line)
  - If has `after` for latest run: show a 1-2 line summary section

---

### Task 4: Prepare real log stream integration seam (SSE/WS)

**Files:**
- Modify: `frontend/src/pages/DynamicDemo.tsx` (or create `frontend/src/lib/interventionFlow/logStream.ts`)

**Step 1: Add adapter interface**

Define a minimal callback shape:
- `onLogLine((line: string) => void)`
So swapping from simulator to SSE/WS is a single place change.

---

### Task 5: Verification

**Step 1: Run unit tests**

Run: `cd frontend; npm test`
Expected: PASS.

**Step 2: Build**

Run: `cd frontend; npm run build`
Expected: build success.

**Step 3: Manual acceptance**

Run: `cd frontend; npm run dev`
Checklist:
- Toggle "开启舆论平衡" on/off hides/shows the flow panel.
- Click "开启演示": right panel starts streaming lines, active role highlights and expands.
- No timestamps are visible in the streamed lines.
- When switching roles, the previous role's `after` stays fixed.
- After `Activating Echo Agent cluster...`, subsequent `Leader comment ...` lines remain under Amplifier.
- During monitoring, active role can return to Analyst/Strategist and highlight switches accordingly.

