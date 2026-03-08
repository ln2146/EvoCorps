#!/usr/bin/env python3
"""
运行EvoCorps系统测试 - 启用X算法推荐和审核系统
运行约10分钟，验证系统正确性
"""
import sys
import os
import time
import logging

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_run.log'),
        logging.StreamHandler()
    ]
)

print("=" * 70)
print("EvoCorps 系统测试")
print("=" * 70)
print("\n测试配置:")
print("  - X算法推荐系统: 启用")
print("  - 审核系统: 启用")
print("  - 运行时间: ~10分钟")
print("  - 配置文件: test_run_config.json")
print("=" * 70)

# 启用审核系统
import control_flags
control_flags.moderation_enabled = True
print(f"\n[控制标志] moderation_enabled = {control_flags.moderation_enabled}")

# 导入并运行模拟
from simulation import Simulation

try:
    # 读取配置
    import json
    config_path = os.path.join(os.path.dirname(__file__), 'test_run_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    print(f"\n[配置] num_users: {config.get('num_users')}")
    print(f"[配置] num_time_steps: {config.get('num_time_steps')}")
    print(f"[配置] moderation.content_moderation: {config.get('moderation', {}).get('content_moderation')}")
    print(f"[配置] recommender.enabled: {config.get('recommender', {}).get('enabled')}")

    print("\n" + "=" * 70)
    print("开始运行模拟...")
    print("=" * 70 + "\n")

    start_time = time.time()

    # 运行模拟
    sim = Simulation(config_path=config_path)
    sim.run()

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("模拟完成!")
    print(f"运行时间: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print("=" * 70)

    # 输出统计信息
    print("\n系统统计:")
    print(f"  - 总用户数: {len(sim.users)}")
    print(f"  - 总帖子数: {len(sim.posts)}")

    # 检查审核系统
    if hasattr(sim, 'moderation_service'):
        print("\n审核系统状态:")
        print(f"  - 服务已初始化: {sim.moderation_service is not None}")

    # 检查推荐系统
    if hasattr(sim, 'recommender_enabled'):
        print(f"\n推荐系统状态:")
        print(f"  - 已启用: {sim.recommender_enabled}")

    print("\n日志已保存到: test_run.log")

except Exception as e:
    print(f"\n[错误] 模拟运行失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
