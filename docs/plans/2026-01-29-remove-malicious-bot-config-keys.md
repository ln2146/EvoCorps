# Remove Deprecated Malicious Bot Config Keys Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the unused `attack_probability` and `target_post_types` keys from `configs/experiment_config.json`.

**Architecture:** Single-file config cleanup; no runtime code changes.

**Tech Stack:** JSON config

### Task 1: Remove deprecated keys from experiment_config.json

**Files:**
- Modify: `configs/experiment_config.json`

**Step 1: Write the failing test**

Not applicable for config-only cleanup.

**Step 2: Run test to verify it fails**

Not applicable for config-only cleanup.

**Step 3: Write minimal implementation**

Delete the `attack_probability` and `target_post_types` entries under `malicious_bot_system` (or wherever present in the file).

**Step 4: Run test to verify it passes**

Not applicable for config-only cleanup.

**Step 5: Commit**

```bash
git add configs/experiment_config.json
git commit -m "chore: remove deprecated malicious bot config keys"
```
