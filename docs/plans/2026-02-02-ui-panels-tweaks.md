# UI Panels Tweaks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 调整动态面板与摘要卡片的文案/布局/日志映射：Analyst 文案与结果展示、Strategist 候选策略持久展示与卡片宽度、Leader 噪声过滤与隐藏发布卡片、Amplifier Echo→Amplifier 改名并消除重复执行结果，同时同步后端日志输出。

**Architecture:** 以 `frontend/src/lib/interventionFlow/` 为主入口：`milestones.ts` 负责“日志→面板可读文案”，`logRouter.ts` 负责“角色路由/阶段/流缓冲”，`rolePills.ts` 与 `summaryGridLayout.ts` 负责摘要卡片内容与布局；后端在 `src/agents/simple_coordination_system.py` 等处统一替换 Echo 相关日志短语为 Amplifier，并在前端保持对旧日志的兼容匹配但统一输出为 Amplifier 文案。

**Tech Stack:** React + Tailwind（前端 UI）、Vitest（前端测试）、Python（后端日志）

---

### Task 1: Analyst 动态面板文案调整

**Files:**
- Modify: `frontend/src/lib/interventionFlow/milestones.ts`
- Test: `frontend/src/lib/interventionFlow/milestones.test.ts`

**Step 1: 写失败测试**
- `Feed score: 205.20` 应映射为 `热度值：205.20`（不再是 `信息流得分`）
- `🔍 Comment 1 LLM result: (8.0, 0.1)` 应映射为“情绪度/极端度计算结果”的可读格式

**Step 2: 运行并确认失败**
- Run: `cd frontend && npm test -- milestones.test.ts`

**Step 3: 最小实现通过测试**
- 修改 `toUserMilestone` 对 `Feed score` 与 `Comment ... LLM result` 的映射

---

### Task 2: Strategist 候选策略显示 + 摘要卡片宽度微调

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRouter.ts`
- Modify: `frontend/src/lib/interventionFlow/summaryGridLayout.ts`
- Test: `frontend/src/lib/interventionFlow/logRouter.test.ts`
- Test: `frontend/src/lib/interventionFlow/summaryGridLayout.test.ts`

**Step 1: 写失败测试**
- Strategist 在“选择策略/输出指令”阶段仍能看到候选策略内容（阶段变更不清空已有候选策略行）
- 摘要卡片：策略列略窄、风格列略宽（`grid-cols-[...]` 调整）

**Step 2: 运行并确认失败**
- Run: `cd frontend && npm test -- logRouter.test.ts`
- Run: `cd frontend && npm test -- summaryGridLayout.test.ts`

**Step 3: 最小实现通过测试**
- 调整阶段切换时的 `during` 清空策略（仅对 Strategist 生效）
- 调整 `getSummaryGridClassName('Strategist')` 列宽比例

---

### Task 3: Leader 完整展示 + 噪声过滤 + 隐藏“发布”卡片

**Files:**
- Modify: `frontend/src/lib/interventionFlow/logRouter.ts`
- Modify: `frontend/src/lib/interventionFlow/rolePills.ts`
- Test: `frontend/src/lib/interventionFlow/logRouter.test.ts`
- Test: `frontend/src/lib/interventionFlow/rolePills.test.ts`

**Step 1: 写失败测试**
- 动态面板不显示全是 `=` 的分隔线
- 动态面板不显示包含 `model(unknown)` 的行
- Leader 摘要卡片不显示 `发布：N`
- Leader 论据/候选评论在阶段变化后仍可见（阶段变更不清空已有内容）

**Step 2: 运行并确认失败**
- Run: `cd frontend && npm test -- logRouter.test.ts`
- Run: `cd frontend && npm test -- rolePills.test.ts`

**Step 3: 最小实现通过测试**
- `compressDisplayLine` 增加噪声过滤规则
- `applyStageUpdateForRole` 对 Leader 不清空 `during`
- `buildRolePills('Leader', ...)` 过滤 `发布：` 行

---

### Task 4: Amplifier Echo→Amplifier + 去重执行结果

**Files:**
- Modify: `frontend/src/lib/interventionFlow/milestones.ts`
- Modify: `frontend/src/lib/interventionFlow/logRouter.ts`
- Modify: `frontend/src/lib/interventionFlow/rolePills.ts`
- Modify: `frontend/src/lib/interventionFlow/logCompression.ts`
- Test: `frontend/src/lib/interventionFlow/milestones.test.ts`
- Test: `frontend/src/lib/interventionFlow/logRouter.test.ts`
- Test: `frontend/src/lib/interventionFlow/rolePills.test.ts`
- Test: `frontend/src/lib/interventionFlow/logCompression.test.ts`

**Step 1: 写失败测试**
- `Echo plan / Echo Agent results / echo responses generated` 的 UI 映射统一输出为 Amplifier 文案
- `扩音器：执行结果（成功 X / 失败 Y）` 连续重复时只显示一次（不重复）

**Step 2: 运行并确认失败**
- Run: `cd frontend && npm test -- milestones.test.ts`
- Run: `cd frontend && npm test -- logRouter.test.ts`

**Step 3: 最小实现通过测试**
- `milestones.ts` 同时匹配旧/新日志短语，但输出统一为 Amplifier
- `logRouter.ts` 中 summary/stage/anchor 匹配同步支持新短语
- `appendDuringWithCap` 对连续重复行去重

---

### Task 5: 后端日志同步（Echo→Amplifier）

**Files:**
- Modify: `src/agents/simple_coordination_system.py`
- Modify: `src/advanced_rag_system.py`（若其输出 Echo plan 影响前端）

**Step 1: 最小实现**
- 将相关 `workflow_logger.info(...)` 文案从 Echo 改为 Amplifier（保持语义不变）

**Step 2: 手动验证路径**
- 跑一次后端工作流/回放日志，确认前端动态面板不再出现 `Echo` 字样

---

### Task 6: 全量验证

**Step 1: 运行前端全量测试**
- Run: `cd frontend && npm test`
- Expected: `0 failed`

