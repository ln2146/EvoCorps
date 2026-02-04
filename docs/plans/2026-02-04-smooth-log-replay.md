# Smooth Log Replay Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按日志时间戳平滑回放动态面板日志，设置最小/最大间隔，避免忽快忽慢且更贴近真实耗时。

**Architecture:** 前端渲染不再固定 `setInterval` 取队列，而是将每条日志解析出时间戳，计算与上一条“可解析时间戳”的差值，应用 `timeScale` 缩放并用 `min/max` 夹紧，再用轻量平滑（EMA）消除抖动。SSE 仍可快速接收，渲染按队列节奏输出，避免 burst 一次性刷屏。

**Tech Stack:** React + TypeScript + Vitest（前端）；现有 `LogStream` + `routeLogLine` 渲染管线复用。

---

### Task 1: 为时间戳解析与夹紧策略写 failing tests

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRenderQueue.test.ts`

**Step 1: Write the failing test**

- 新增 `createTimestampSmoothLineQueue` 的测试：
  - 解析 `YYYY-MM-DD HH:MM:SS,mmm - INFO - ...` 并计算 delta
  - `delta * timeScale` 后再 `clamp(min,max)`
  - 无法解析时间戳的行使用 `minDelayMs`
  - 通过 `vi.useFakeTimers()` 验证触发顺序与触发时间

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- logRenderQueue.test.ts`
Expected: FAIL（函数/行为不存在或不符合）

---

### Task 2: 实现 timestamp-smooth 队列（GREEN）

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRenderQueue.ts`

**Step 1: Write minimal implementation**

- 新增：
  - `parseLogPrefixTimestampMs(line: string): number | null`
  - `createTimestampSmoothLineQueue({ minDelayMs, maxDelayMs, timeScale, smoothingAlpha, onDrain })`
- 核心逻辑：
  - `delay = clamp(deltaMs * timeScale, minDelayMs, maxDelayMs)`
  - `smoothedDelay = alpha * delay + (1 - alpha) * prevDelay`
  - `setTimeout` 串行 drain（默认每次 1 行）

**Step 2: Run test to verify it passes**

Run: `cd frontend && npm test -- logRenderQueue.test.ts`
Expected: PASS

---

### Task 3: DynamicDemo 接入平滑队列（GREEN）

**Files:**
- Modify: `frontend/src/pages/DynamicDemo.tsx`

**Step 1: Update wiring**

- 用 `createTimestampSmoothLineQueue` 替代 `createFixedRateLineQueue`
- 设置推荐默认值（可后续抽到配置文件）：
  - `minDelayMs`：例如 80
  - `maxDelayMs`：例如 1200
  - `timeScale`：例如 0.12~0.2（让 10s 级别等待映射到 ~1-2s）
  - `smoothingAlpha`：例如 0.25
- Replay 模式下建议将后端 `delay_ms` 设为 0（避免前后双重节流），渲染节奏由前端控制

**Step 2: Run tests**

Run: `cd frontend && npm test`
Expected: PASS

---

### Task 4: 端到端校验与参数微调

**Files:**
- Modify (optional): `frontend/src/lib/interventionFlow/replayConfig.ts`

**Step 1: Verify**

- 打开动态面板观察：
  - 长耗时步骤（LLM）不再瞬间刷过，但也不会卡住太久（由 max 控制）
  - burst 日志不再“跳跃式”刷新

**Step 2: Full test**

Run: `pytest -q`
Expected: PASS

