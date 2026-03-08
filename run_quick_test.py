#!/usr/bin/env python3
"""快速测试 - 验证X算法和审核系统"""
import sys
import os
import time
import json
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 70)
print("EvoCorps 快速系统测试")
print("=" * 70)

# 启用系统
import control_flags
control_flags.moderation_enabled = True
print(f"\n[SETUP] moderation_enabled = {control_flags.moderation_enabled}")
print("[SETUP] recommender.enabled = True (from config)")
print("[SETUP] author_credibility.enabled = True")

from simulation import Simulation

config_path = os.path.join(os.path.dirname(__file__), 'quick_test_config.json')

print(f"\n[CONFIG] Using: {config_path}")
with open(config_path, 'r') as f:
    cfg = json.load(f)
    print(f"[CONFIG] num_users={cfg.get('num_users')}, steps={cfg.get('num_time_steps')}")
    print(f"[CONFIG] moderation={cfg.get('moderation', {}).get('content_moderation')}")
    print(f"[CONFIG] recommender={cfg.get('recommender', {}).get('enabled')}")

print("\n" + "=" * 70)
print("Starting simulation...")
print("=" * 70 + "\n")

start = time.time()
try:
    sim = Simulation(config=cfg)
    # Run the async simulation properly
    asyncio.run(sim.run(num_time_steps=cfg.get('num_time_steps', 5)))
    elapsed = time.time() - start

    print("\n" + "=" * 70)
    print(f"Simulation completed in {elapsed:.1f}s")
    print(f"Users: {len(sim.users)}, Posts: {len(sim.posts)}")
    print("=" * 70)
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
