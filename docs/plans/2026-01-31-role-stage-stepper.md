# Role Stage Stepper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** In the Dynamic Demo right panel, show a compact “stage stepper” on the right side of the role detail header, driven by workflow logs (per-role, variable step counts, reset each round).

**Architecture:** Extend `FlowState` with per-role stage progress (`stageIndex`) updated by `logRouter` as log anchors arrive. Render a fixed-width stepper in `RoleDetailSection` header that shows current stage text + progress segments without changing layout size.

**Tech Stack:** React + TypeScript + Tailwind + Vitest

---

### Task 1: Define per-role stage definitions

**Files:**
- Create: `frontend/src/lib/interventionFlow/roleStages.ts`
- Test: `frontend/src/lib/interventionFlow/roleStages.test.ts`

**Step 1: Write the failing test**

- Add tests asserting stage arrays per role:
  - Analyst: `['内容识别','评论抽样','情绪度','极端度','干预判定','监测评估']`
  - Strategist: `['确认告警','检索历史','生成方案','选择策略','输出指令']`
  - Leader: `['解析指令','检索论据','生成候选','投票选优','发布评论']`
  - Amplifier: `['启动集群','生成回应','点赞放大','扩散完成']`

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL (module missing).

**Step 3: Write minimal implementation**

- Implement `getRoleStages(role)` returning the arrays above.
- Implement `formatRoleStagesTooltip(role)` joining with ` -> `.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS.

---

### Task 2: Track stage progress in FlowState and update via logs

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRouter.ts`
- Test: `frontend/src/lib/interventionFlow/logRouter.test.ts`

**Step 1: Write failing test**

- Add a test that feeds Analyst-related log lines and expects stageIndex to advance:
  - `Analyst is analyzing` => stage 0
  - `Total weight calculated` => stage 1
  - `Overall sentiment` => stage 2
  - `Viewpoint extremism` => stage 3
  - `Needs intervention` => stage 4
  - `[Monitoring round` => stage 5
- Add a test that on a new-round anchor (e.g. `Start workflow execution - Action ID:`) stageIndex resets to 0 and role statuses clear to initial.

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL (no stage tracking).

**Step 3: Implement minimal code**

- Extend `RoleCardState` to include `stageIndex: number` (default `-1`).
- Add `applyStageUpdates(prev, cleanLine)` that:
  - maps anchors to stage indexes per role
  - clamps to max stage count - 1
- Add `isNewRoundAnchor(cleanLine)` and reset the whole `FlowState` on it (Option A).

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS.

---

### Task 3: Render stage stepper in RoleDetailSection header

**Files:**
- Create: `frontend/src/lib/interventionFlow/stageStepper.tsx`
- Create: `frontend/src/lib/interventionFlow/stageStepper.test.tsx` (or keep as logic-only tests if JSX test infra is heavy)
- Modify: `frontend/src/pages/DynamicDemo.tsx`

**Step 1: Write failing test**

- Prefer a logic-only test:
  - `buildStageStepperModel(role, stageIndex)` returns `currentLabel`, `total`, `doneCount`, `tooltip`.

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL.

**Step 3: Implement minimal code**

- Add `buildStageStepperModel` in `stageStepper.ts` (no JSX).
- In `DynamicDemo.tsx`, render a fixed-width right-side container in the role header:
  - show `当前：{label}（{idx+1}/{total}）` when stageIndex >= 0 and not idle
  - show a small segment bar (N segments) with done/current/pending color
  - set `title` to tooltip string
- Ensure fixed width and `min-w-0` to prevent layout shifts.

**Step 4: Run tests + build**

Run:
- `cd frontend && npm test`
- `cd frontend && npm run build`
Expected: PASS.

---

### Task 4: Quick manual verification

**Steps:**
- Start dev server: `cd frontend && npm run dev`
- Click “开启舆论平衡” (replay mode)
- Observe each role’s header shows stage progress and advances
- Ensure no width/height jumping during streaming

