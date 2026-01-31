# Analyst Panel UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the Analyst (分析师) panel so it feels more "live" and readable during streaming, without dumping full backend logs, while still allowing users to view the full post content.

**Architecture:** Keep the existing SSE + logRouter flow state. Improve presentation in the UI, and enrich `milestones.ts` with a few more Analyst progress milestones so the "during" stream shows meaningful progress.

**Tech Stack:** React + TypeScript + Tailwind + Vitest

---

### Task 1: Add better Analyst progress milestones

**Files:**
- Modify: `frontend/src/lib/interventionFlow/milestones.ts`
- Test: `frontend/src/lib/interventionFlow/milestones.test.ts`

**Step 1: Write the failing test**
- Add test cases mapping common Analyst lines to concise Chinese milestones:
  - `📊 Total weight calculated:` -> `分析师：权重汇总`
  - `📊 Weighted per-comment sentiment:` -> `分析师：情绪汇总`
  - `Viewpoint extremism:` -> `分析师：极端度计算`
  - `Overall sentiment:` -> `分析师：情绪计算`
  - `Trigger reasons:` -> `分析师：触发原因确定`

**Step 2: Run test to verify it fails**
- Run: `cd frontend && npm test -- milestones.test.ts`
- Expected: FAIL because `toUserMilestone()` returns `null` for these lines.

**Step 3: Write minimal implementation**
- Add the regex branches in `toUserMilestone()` to return short Chinese milestones.

**Step 4: Run tests**
- Run: `cd frontend && npm test`
- Expected: PASS.

---

### Task 2: Improve "帖子内容" rendering for Analyst (reduce wall-of-text)

**Files:**
- Create: `frontend/src/lib/interventionFlow/postContent.ts`
- Test: `frontend/src/lib/interventionFlow/postContent.test.ts`
- Modify: `frontend/src/pages/DynamicDemo.tsx`

**Step 1: Write the failing test**
- Add tests for:
  - Extract `[NEWS]` tag (if present) and a title (first sentence / first line).
  - Produce a stable preview (first N chars) without mutating full text.

**Step 2: Run test to verify it fails**
- Run: `cd frontend && npm test -- postContent.test.ts`
- Expected: FAIL because helper does not exist.

**Step 3: Write minimal implementation**
- Implement `parsePostContent(raw)` returning `{ tag?: string; title?: string; preview: string; full: string }`.

**Step 4: Update UI**
- Replace the current always-full "帖子内容" block with:
  - a compact header (tag/title)
  - a preview (collapsed by default)
  - an "展开全文/收起全文" toggle (no "回看" wording)
  - expanded view uses a bounded scroll area (`max-h-*` + `overflow-auto`) so it doesn't push out the rest of the panel.

**Step 5: Run tests**
- Run: `cd frontend && npm test`
- Expected: PASS.

---

### Task 3: Verify end-to-end behavior quickly

**Files:**
- None

**Step 1: Build**
- Run: `cd frontend && npm run build`
- Expected: build succeeds.

**Step 2: Manual check**
- Start the app, enable EvoCorps, confirm:
  - Analyst shows compact post preview by default
  - Full post can be expanded and is complete
  - Analyst "during" stream shows multiple progress milestones (not only start/end)

