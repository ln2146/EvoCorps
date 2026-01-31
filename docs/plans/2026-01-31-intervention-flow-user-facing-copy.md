# User-Facing Agent Copy (B) Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Improve how each Agent stage is presented to users: keep English keywords, but show structured, short “milestones” and “key facts” instead of raw log lines.

**Architecture:** Keep the SSE log stream + state machine. Add a new mapping layer:
- `extractFactsFromLogLine(cleanLine)` updates per-role `facts` (4 pills already exist as `summary`).
- `toUserMilestone(cleanLine)` maps verbose logs to short, consistent milestone text (English keywords + compact structure).
Replace existing `compressDisplayLine()` with `toUserMilestone()` and ensure repeated milestones aggregate `× N`.

**Tech Stack:** React + TypeScript + Vitest.

---

### Task 1: Add Milestone Mapper With Tests (TDD)

**Files:**
- Create: `frontend/src/lib/interventionFlow/milestones.ts`
- Test: `frontend/src/lib/interventionFlow/milestones.test.ts`

**Step 1: Write failing tests**
Cover these mappings:
- Analyst:
  - `Analyst is analyzing` -> `Analyst: Analysis started`
  - `Analyst analysis completed` -> `Analyst: Analysis completed`
  - `Needs intervention: yes` -> `Analyst: Intervention required`
- Strategist:
  - `Strategist is creating strategy` -> `Strategist: Strategy drafting`
  - `Selected optimal strategy: balanced_response` -> `Strategist: Strategy selected (balanced_response)`
- Leader:
  - `USC-Generate - generate 6 candidate comments` -> `Leader: Candidates generated (6)`
  - `Best selection: candidate_4` -> `Leader: Best selection (candidate_4)`
  - `Leader comment 1 on post ...` -> `Leader: Comment posted (1)`
- Amplifier:
  - `Activating Echo Agent cluster` -> `Amplifier: Echo cluster activated`
  - `Echo plan: total=12` -> `Amplifier: Echo plan (12)`
  - `12 echo responses generated` -> `Amplifier: Responses generated (12)`
  - `total: 480 likes` -> `Amplifier: Likes boosted (+480)`
  - `effectiveness score: 10.0/10` -> `Amplifier: Effectiveness (10.0/10)`

**Step 2: Run tests to confirm failure**
Run: `cd frontend && npm test`
Expected: FAIL (missing module).

**Step 3: Minimal implementation**
Implement `toUserMilestone(cleanLine): string | null`.
- Return `null` for noise/infra lines.
- Keep message length <= 72 chars (truncate tail if needed).

**Step 4: Re-run tests**
Run: `cd frontend && npm test`
Expected: PASS.

---

### Task 2: Integrate Milestones Into Router (TDD)

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRouter.ts`
- Modify: `frontend/src/lib/interventionFlow/logRouter.test.ts`

**Step 1: Write failing test**
- Ensure `routeLogLine()` uses milestone strings for `during` instead of raw/compressed lines for at least one representative line per role.

**Step 2: Run tests to confirm failure**
Run: `cd frontend && npm test`
Expected: FAIL.

**Step 3: Minimal implementation**
- Replace `compressDisplayLine()` with `toUserMilestone()` (fallback to a short truncated string only if needed).
- Keep existing sticky logic unchanged.

**Step 4: Re-run tests**
Run: `cd frontend && npm test`
Expected: PASS.

---

### Task 3: Improve Summary (“facts”) Labels (TDD-light)

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRouter.ts`
- Test: `frontend/src/lib/interventionFlow/logRouter.test.ts`

**Changes:**
- Analyst summary line 0 becomes: `Decision: required (U3)` / `Decision: not required`
- Strategist summary line 0 becomes: `Strategy: balanced_response`
- Leader summary line 3 becomes: `Posted: 2`
- Amplifier summary line 3 becomes: `Effectiveness: 10.0/10`

**Verify**
Run: `cd frontend && npm test`
Expected: PASS.

---

### Task 4: Manual Visual Check

**Run:**
- Start backend + frontend and toggle enable.

**Expect:**
- Event stream reads like consistent milestones (English keywords), not raw logs.
- Repeats aggregate as `× N`.
- Summary pills remain stable and readable.

