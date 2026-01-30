# Intervention Flow Summary Lines Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** In the right-side intervention flow panel, each role card shows 4 fixed “summary lines” (B) that update from real workflow logs, while the streaming “event” area remains concise (max 10 lines, aggregated).

**Architecture:** Keep the existing SSE log stream + `routeLogLine()` state machine. Extend the role card state with `summary: string[]` (fixed 4 rows). Update summaries by parsing a small set of log patterns per role; show placeholders when unknown.

**Tech Stack:** React + TypeScript + Tailwind (frontend), Vitest for unit tests.

---

### Task 1: Extend Flow State With 4-Line Summary Per Role (TDD)

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRouter.ts`
- Test: `frontend/src/lib/interventionFlow/logRouter.test.ts`

**Step 1: Write failing tests**
- Add a test that verifies `createInitialFlowState()` initializes `roles[role].summary` with exactly 4 lines and sensible placeholders.
- Add tests that when routing specific log lines, the corresponding summary lines update (Analyst/Strategist/Leader/Amplifier).

**Step 2: Run tests to confirm failure**
Run: `cd frontend && npm test`
Expected: FAIL due to missing `summary` field / missing parsing.

**Step 3: Minimal implementation**
- Update `RoleCardState` to include `summary: string[]` (length 4).
- Update `createInitialFlowState()` to populate per-role default summaries.
- Add parsing helpers inside `logRouter.ts` to extract key fields and rewrite only the specific summary slot(s) touched by the log line.
- Keep existing anchor-based role switching behavior unchanged.

**Step 4: Re-run tests**
Run: `cd frontend && npm test`
Expected: PASS.

---

### Task 2: Render 4-Line Summary In UI (TDD)

**Files:**
- Modify: `frontend/src/pages/DynamicDemo.tsx`
- (Optional) Modify: `frontend/src/lib/interventionFlow/logRouter.ts` (types/exports only if needed)
- Test: (Optional) `frontend/src/pages/DynamicDemo.test.tsx` if tests exist; otherwise rely on unit tests + manual check.

**Step 1: Write failing test (optional)**
- If there is a React testing setup, add a test that `RoleStepCard` renders exactly 4 summary rows and that content updates when state changes.

**Step 2: Minimal implementation**
- Replace the single `before` line rendering with a 4-row summary block.
- Keep “during” and “after” sections unchanged.
- Ensure compressed cards still look readable (small font, line clamp).

**Step 3: Verify build**
Run: `cd frontend && npm run build`
Expected: build succeeds.

---

### Task 3: Manual Verification With Real Logs

**Files:**
- None (manual)

**Step 1: Start backend + frontend**
- Start the backend that exposes `/api/opinion-balance/logs/stream`.
- Start the frontend dev server.

**Step 2: Validate behavior**
- Toggle “开启舆论平衡” on: right panel immediately streams and renders.
- Active role card expands; others shrink; total height constant.
- No timestamps shown.
- After `⚖️ Activating Echo Agent cluster...`, subsequent logs stick to Amplifier until monitoring anchors appear.
- Each role card shows 4 summary lines that update as logs arrive.

