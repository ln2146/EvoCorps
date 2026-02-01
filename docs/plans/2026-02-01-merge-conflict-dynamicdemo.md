# DynamicDemo.tsx Merge Conflict Resolution Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan.

**Goal:** Resolve the `frontend/src/pages/DynamicDemo.tsx` merge conflict by keeping upstream UI improvements while preserving local “frontend-only replay” support.

**Architecture:** Use `theirs` (`origin/main`) as the base, then re-apply the local replay changes (fetch-based replay from `frontend/public/workflow/`). Verify by building the frontend and ensuring no conflict markers remain.

**Tech Stack:** React + TypeScript, Vite (frontend), Git merge conflict resolution.

### Task 1: Inspect conflict and versions

**Files:**
- Inspect: `frontend/src/pages/DynamicDemo.tsx`

**Step 1:** Identify conflict markers and the 2 index versions (`:2:` ours, `:3:` theirs).  
Run: `rg -n "^(<{7}|={7}|>{7})" frontend/src/pages/DynamicDemo.tsx`

### Task 2: Apply resolution (theirs + local replay additions)

**Files:**
- Modify: `frontend/src/pages/DynamicDemo.tsx`

**Step 1:** Replace conflicted file with `theirs` as the base.  
Run: `git checkout --theirs frontend/src/pages/DynamicDemo.tsx`

**Step 2:** Re-apply local “fetch replay” support:
- Import `createFetchReplayLogStream`
- Add `WORKFLOW_REPLAY_PUBLIC_FILE`
- Select stream with `createFetchReplayLogStream` when in replay mode

### Task 3: Verify

**Step 1:** Ensure no conflict markers remain.  
Run: `rg -n "^(<{7}|={7}|>{7})" frontend/src/pages/DynamicDemo.tsx`

**Step 2:** Build the frontend.  
Run: `npm -C frontend ci` then `npm -C frontend run build`

### Task 4: Finish merge

**Step 1:** Stage merge resolution.  
Run: `git add frontend/src/pages/DynamicDemo.tsx`

**Step 2:** Commit the merge.  
Run: `git commit`

