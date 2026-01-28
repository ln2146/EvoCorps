# Centralize Memory & Fact-Check Models Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将记忆机制与第三方事实核查使用的模型统一到 `src/multi_model_selector.py` 的集中配置中，并默认使用 `DEFAULT_POOL = ["deepseek-chat"]`。

**Architecture:** 在 `MultiModelSelector` 中新增角色池（`memory`、`fact_checker`），并将相关调用从硬编码或配置文件读取替换为按角色获取模型。所有模型最终统一来自 `DEFAULT_POOL`，只需改一处即可全局生效。

**Tech Stack:** Python, OpenAI-compatible client (`openai`), pytest

---

### Task 1: 扩展 MultiModelSelector 角色池

**Files:**
- Modify: `src/multi_model_selector.py`
- Test: `tests/test_multi_model_selector.py`

**Step 1: Write the failing test**

```python
def test_role_pools_include_memory_and_fact_checker():
    from multi_model_selector import MultiModelSelector
    assert "memory" in MultiModelSelector.ROLE_MODEL_POOLS
    assert "fact_checker" in MultiModelSelector.ROLE_MODEL_POOLS
    assert MultiModelSelector.ROLE_MODEL_POOLS["memory"] == MultiModelSelector.DEFAULT_POOL
    assert MultiModelSelector.ROLE_MODEL_POOLS["fact_checker"] == MultiModelSelector.DEFAULT_POOL
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_multi_model_selector.py::test_role_pools_include_memory_and_fact_checker -v`  
Expected: FAIL (role keys missing).

**Step 3: Write minimal implementation**

- 在 `ROLE_MODEL_POOLS` 中加入 `memory` 与 `fact_checker`，都指向 `DEFAULT_POOL`。

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_multi_model_selector.py::test_role_pools_include_memory_and_fact_checker -v`  
Expected: PASS

---

### Task 2: 记忆机制改为集中模型配置

**Files:**
- Modify: `src/agent_user.py`

**Step 1: Write the failing test**

Add a small unit test to ensure memory integration pulls model via selector (if feasible), or a smoke test that imports the module without hardcoded model strings. If no existing testing pattern for this module, skip test and document.

**Step 2: Write minimal implementation**

Replace hardcoded memory LLM calls with centralized selection:
- In `_integrate_memory_after_content_creation`
- In `_integrate_memories_with_llm`
- In `_update_memory_after_action`

Each uses `multi_model_selector.create_openai_client(role="memory")` and passes its model.

---

### Task 3: 第三方事实核查改为集中模型配置

**Files:**
- Modify: `src/simulation.py`

**Step 1: Write minimal implementation**

Replace:
```python
fact_checker_engine = self.experiment_settings.get('fact_checker_engine', self.engine)
```
with:
```python
from multi_model_selector import multi_model_selector
fact_checker_engine = multi_model_selector.select_random_model(role="fact_checker")
```

---

### Task 4: 统一回归与记录基线问题

**Step 1: Run full test suite**

Run: `pytest -q`  
Expected: PASS  
If it fails due to baseline issues (e.g., missing `src/keys.py`), document the failure explicitly.

