"""
Comparison Simulator - 从指定时间步恢复并继续模拟

与main.py功能相同，但支持从任意时间步恢复状态
"""

import json
import sys
import os
import sqlite3
from simulation import Simulation
from utils import Utils
from engine_selector import apply_selector_engine
import logging
import time
from datetime import datetime

# Runtime control API
import threading
from typing import Optional, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests

from openai import OpenAI
from keys import OPENAI_API_KEY, OPENAI_BASE_URL

import control_flags

# Moderation service (initialized when needed)
moderation_service = None

# =============================
# FastAPI control server setup
# =============================

control_app = FastAPI(title="Simulation Control API", version="1.0.0")

control_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ToggleRequest(BaseModel):
    """Simple request body for enabling / disabling a flag."""

    enabled: bool


class AttackModeRequest(BaseModel):
    """Request body for setting malicious attack coordination mode."""

    mode: Literal["swarm", "dispersed", "chain"]


class PostCommentsAnalysisRequest(BaseModel):
    """Request body for analyzing a single post and its comments."""

    post_id: str


@control_app.get("/control/status")
def get_control_status():
    """Return current values of all runtime control flags."""

    return control_flags.as_dict()


@control_app.post("/control/toggle-attack")
def toggle_attack(request: ToggleRequest):
    """
    Toggle malicious attacks on/off.
    """
    control_flags.attack_enabled = request.enabled
    return {
        "success": True,
        "attack_enabled": control_flags.attack_enabled,
        "message": f"Malicious attacks {'enabled' if request.enabled else 'disabled'}"
    }


@control_app.post("/control/set-attack-mode")
def set_attack_mode(request: AttackModeRequest):
    """
    Set malicious attack coordination mode (swarm/dispersed/chain).
    """
    # Import here to avoid circular dependency
    from malicious_bots.malicious_bot_manager import MaliciousBotManager

    # Validate mode
    valid_modes = ["swarm", "dispersed", "chain"]
    if request.mode not in valid_modes:
        return {
            "success": False,
            "error": f"Invalid mode: {request.mode}. Must be one of {valid_modes}"
        }

    # This will be read by MaliciousBotManager on next attack
    control_flags.attack_mode = request.mode

    return {
        "success": True,
        "attack_mode": control_flags.attack_mode,
        "message": f"Attack coordination mode set to {request.mode}"
    }


@control_app.post("/control/toggle-opinion-balance")
def toggle_opinion_balance(request: ToggleRequest):
    """
    Toggle opinion balance system on/off (standalone mode is always on if enabled).
    """
    control_flags.opinion_balance_enabled = request.enabled
    return {
        "success": True,
        "opinion_balance_enabled": control_flags.opinion_balance_enabled,
        "message": f"Opinion balance system {'enabled' if request.enabled else 'disabled'}"
    }


@control_app.post("/control/toggle-moderation")
def toggle_moderation(request: ToggleRequest):
    """
    Toggle content moderation system on/off.
    """
    control_flags.moderation_enabled = request.enabled
    return {
        "success": True,
        "moderation_enabled": control_flags.moderation_enabled,
        "message": f"Content moderation system {'enabled' if request.enabled else 'disabled'}"
    }


@control_app.post("/control/toggle-aftercare")
def toggle_aftercare(request: ToggleRequest):
    """
    Toggle third-party fact-checking (aftercare) on/off.
    """
    control_flags.aftercare_enabled = request.enabled
    return {
        "success": True,
        "aftercare_enabled": control_flags.aftercare_enabled,
        "message": f"Third-party fact-checking {'enabled' if request.enabled else 'disabled'}"
    }


def start_control_api_server():
    """
    Start the FastAPI control server in a background thread.
    """

    def run_server():
        uvicorn.run(control_app, host="127.0.0.1", port=8001, log_level="warning")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1)  # Give server time to start
    print("🚀 Control API server started on http://127.0.0.1:8001")


def get_required_feedback_monitoring_interval(config):
    """获取反馈监控间隔（分钟）"""
    opinion_balance_config = config.get('opinion_balance_system')
    if not isinstance(opinion_balance_config, dict):
        raise ValueError("Missing 'opinion_balance_system' section in configs/experiment_config.json")

    value = opinion_balance_config.get('feedback_monitoring_interval')
    if isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            value = int(value)

    if isinstance(value, (int, float)) and int(value) > 0:
        return int(value)

    raise ValueError(
        "opinion_balance_system.feedback_monitoring_interval must be a positive integer "
        f"in configs/experiment_config.json, got: {opinion_balance_config.get('feedback_monitoring_interval')!r}"
    )


def setup_comprehensive_logging():
    """设置综合日志配置，影响所有日志调用"""
    # 确定脚本目录和项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Public-opinion-balance directory
    log_dir = os.path.join(project_root, "logs", "output")
    os.makedirs(log_dir, exist_ok=True)

    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"simulation_comparison_{timestamp}.log")

    # 清除现有日志处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ],
        force=True  # 强制重新配置
    )

    print(f"📁 日志文件: {log_file}")
    return log_file


def select_snapshot_to_restore():
    """
    显示可用的快照并让用户选择要恢复的tick

    Returns:
        (session_id, tick) 或 (None, None) 如果用户取消
    """
    try:
        from snapshot_manager import create_snapshot_manager

        project_root = os.path.dirname(os.path.dirname(__file__))
        db_path = os.path.join(project_root, 'database', 'simulation.db')
        snapshot_manager = create_snapshot_manager(project_root, db_path)

        # 列出所有会话
        sessions = snapshot_manager.list_sessions()

        if not sessions:
            print("❌ 没有找到任何快照会话")
            print("   请先运行 main.py 生成快照数据")
            return None, None

        print("\n" + "=" * 60)
        print("📦 可用的快照会话")
        print("=" * 60)

        for i, session in enumerate(sessions, 1):
            session_id = session.get('session_id', 'Unknown')
            created_at = session.get('created_at', 'Unknown')
            ticks = session.get('ticks', {})
            tick_count = len(ticks)

            print(f"\n[{i}] 会话ID: {session_id}")
            print(f"    创建时间: {created_at}")
            print(f"    快照数量: {tick_count} 个tick")

            # 显示可用的tick
            if ticks:
                available_ticks = sorted([int(t) for t in ticks.keys()])
                print(f"    可用tick: {available_ticks}")

        print("=" * 60)

        # 选择会话
        while True:
            choice = input("\n请选择会话编号 (1-{}, 或输入 'q' 退出): ".format(len(sessions)))
            if choice.lower() == 'q':
                return None, None

            try:
                session_idx = int(choice) - 1
                if 0 <= session_idx < len(sessions):
                    selected_session = sessions[session_idx]
                    session_id = selected_session.get('session_id')
                    break
                else:
                    print("❌ 无效的会话编号，请重新输入")
            except ValueError:
                print("❌ 请输入有效的数字")

        # 获取该会话的详细信息
        session_info = snapshot_manager.get_session_info(session_id)
        if not session_info:
            print("❌ 无法获取会话信息")
            return None, None

        ticks = session_info.get('ticks', {})
        available_ticks = sorted([int(t) for t in ticks.keys()])

        print(f"\n会话 {session_id} 中可用的tick:")
        print(f"可用tick: {available_ticks}")

        # 选择tick
        while True:
            tick_choice = input(f"\n请选择要恢复的tick (或输入 'q' 退出): ")
            if tick_choice.lower() == 'q':
                return None, None

            try:
                tick = int(tick_choice)
                if tick in available_ticks:
                    # 显示该tick的信息
                    tick_info = ticks.get(str(tick), {})
                    print(f"\n✅ 已选择 tick {tick}")
                    if tick_info:
                        info_file = tick_info.get('info_file')
                        if info_file and os.path.exists(info_file):
                            with open(info_file, 'r', encoding='utf-8') as f:
                                info_data = json.load(f)
                                print(f"   时间戳: {tick_info.get('timestamp', 'Unknown')}")
                                print(f"   用户数: {info_data.get('user_count', 'Unknown')}")
                                print(f"   帖子数: {info_data.get('post_count', 'Unknown')}")
                    return session_id, tick
                else:
                    print(f"❌ tick {tick} 不存在，请从以下tick中选择: {available_ticks}")
            except ValueError:
                print("❌ 请输入有效的数字")

    except Exception as e:
        print(f"❌ 选择快照时出错: {e}")
        return None, None


def get_user_choice_malicious_bots():
    """Get user selection for the malicious bot system."""
    print("\n" + "="*60)
    print("🔥 Malicious bot system selection")
    print("="*60)
    print("The malicious bot system can:")
    print("  • Simulate real malicious attacks and extreme rhetoric")
    print("  • Automatically generate diverse opposing viewpoints and criticism")
    print("  • Test the opinion balance system's defense capability")
    print("  • Provide a complete attack-defense demonstration")
    print("  • All malicious comments carry the 🔥[Malicious Bots] tag")
    print()
    print("Note: Enabling generates simulated malicious content, for research and testing only")
    print("="*60)

    while True:
        choice = input("Enable malicious bot system? (y/n): ").strip().lower()

        if choice in ['y', 'yes', 'enable']:
            print("✅ Selected to enable the malicious bot system")
            return True
        elif choice in ['n', 'no', 'disable']:
            print("❌ Selected to disable the malicious bot system")
            return False
        else:
            print("❌ Invalid input, please enter y (enable) or n (disable)")


def get_user_choice_opinion_balance():
    """Get user selection for the opinion balance system."""
    print("\n" + "="*60)
    print("⚖️  Opinion balance system selection")
    print("="*60)
    print("The opinion balance system can:")
    print("  • Monitor extreme content in real time (conspiracy theories, hate speech, radical incitement, etc.)")
    print("  • Automatically generate balanced responses to reduce polarization")
    print("  • Provide detailed intervention effect analysis and stats")
    print("  • Simulate real social media content governance scenarios")
    print("  • Support feedback and iteration, dynamically adjusting strategies")
    print()
    print("Note: Enabling increases runtime but shows full intervention effects")
    print("="*60)

    while True:
        choice = input("Enable opinion balance system? (y=standalone/n=disable) [default: y]: ").strip().lower()

        # If the user presses Enter, default to y
        if choice == "":
            choice = "y"

        if choice in ['y', 'yes', 'enable']:
            print("🚀 Selected to start the opinion balance system in standalone mode")
            return "standalone"
        elif choice in ['n', 'no', 'disable']:
            print("❌ Selected to disable the opinion balance system")
            return False
        elif choice in ['standalone', 's']:
            print("🚀 Selected to start the opinion balance system in standalone mode")
            return "standalone"
        else:
            print("❌ Invalid input, please enter y (standalone) / n (disable)")


def get_user_choice_prebunking():
    """Get user choice for the prebunking system."""
    print("\n" + "="*60)
    print("🛡️  Prebunking system (Pre-bunking)")
    print("="*60)
    print("Prebunking system features:")
    print("  • Directly insert safety prompts into regular users' feeds")
    print("  • Provide background knowledge before users encounter potentially misleading information")
    print("  • Improve users' immunity to fake news and critical thinking")
    print("  • Show warning messages for specific topics")
    print("  • For example: before viewing posts about 'miracle cures', users see prompts to spot health pseudoscience")
    print("\nImplementation:")
    print("  - The system inserts safety prompts into regular users' feeds")
    print("  - These prompts appear before users view related content")
    print("\nNote: enabling this feature adds warning prompts to user feeds")
    print("="*60)

    while True:
        choice = input("Enable prebunking system? (y/n): ").strip().lower()
        if choice in ['y', 'yes', 'enable']:
            print("✅ Selected to enable the prebunking system")
            print("   - Will insert safety prompts into regular users' feeds")
            return True
        elif choice in ['n', 'no', 'disable']:
            print("❌ Selected to disable the prebunking system")
            return False
        else:
            print("❌ Invalid input, please enter y (enable) or n (disable)")


def get_required_feedback_monitoring_interval(config: dict) -> int:
    """Read feedback monitoring interval from config without fallback."""
    obs_config = config.get('opinion_balance_system')
    if not isinstance(obs_config, dict):
        raise ValueError("Missing 'opinion_balance_system' section in configs/experiment_config.json")

    value = obs_config.get('feedback_monitoring_interval')
    if isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            value = int(value)

    if isinstance(value, (int, float)) and int(value) > 0:
        return int(value)

    raise ValueError(
        "opinion_balance_system.feedback_monitoring_interval must be a positive integer "
        f"in configs/experiment_config.json, got: {obs_config.get('feedback_monitoring_interval')!r}"
    )


def get_user_choice_fact_checking():
    """Get user choice for the fact-checking system."""
    print("\n" + "=" * 60)
    print("🔍 Third-party fact-checking system")
    print("=" * 60)
    print("Fact-checking system can:")
    print("  • Automatically identify news requiring fact-checking")
    print("  • Generate detailed fact-check reports")
    print("  • Provide follow-up interventions")
    print("  • Simulate real social media fact-checking scenarios")
    print()
    print("Note: Enabling will add runtime overhead")
    print("=" * 60)

    while True:
        choice = input("Enable third-party fact-checking? (y/n): ").strip().lower()

        if choice in ['y', 'yes', 'enable']:
            print("✅ Selected to enable third-party fact-checking")
            return "third_party_fact_checking"
        elif choice in ['n', 'no', 'disable']:
            print("❌ Selected to disable third-party fact-checking")
            return "no_fact_checking"
        else:
            print("❌ Invalid input, please enter y (enable) or n (disable)")


def get_fact_checking_settings(fact_check_type):
    """Get default fact-checking settings."""
    if fact_check_type == "no_fact_checking":
        return {}

    # Use optimized parameters targeting news content per time step
    settings = {
        'posts_per_step': 10,  # Check 10 posts per step
        'fact_checker_temperature': 0.3,  # Default temperature 0.3
        'include_reasoning': False,  # Default does not include reasoning
        'start_delay_minutes': 0,  # Start fact checking immediately (no delay)
        'fact_checking_enabled': True  # Explicitly enable fact checking
    }

    print(
        f"✅ Using default settings: check {settings['posts_per_step']} news items per step, "
        f"temperature {settings['fact_checker_temperature']}, start async checks immediately"
    )

    return settings


def check_database_service():
    """Check whether the database service is running."""
    import requests

    try:
        response = requests.get("http://127.0.0.1:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Database service is running")
            return True
        else:
            print(f"❌ Database service status abnormal: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Unable to connect to the database service: {e}")
        return False


if __name__ == "__main__":
    # 设置综合日志配置，影响所有日志调用
    log_file = setup_comprehensive_logging()

    # 启动后台FastAPI控制服务器
    start_control_api_server()

    # 检查数据库服务
    print("🔍 检查数据库服务状态...")
    if not check_database_service():
        print("\n" + "=" * 60)
        print("⚠️  数据库服务未运行!")
        print("📋 请按以下步骤操作:")
        print("1. 打开新的终端窗口")
        print("2. 运行: python src/start_database_service.py")
        print("3. 等待服务启动")
        print("4. 然后返回此窗口继续模拟")
        print("=" * 60)

        input("按 Enter 继续 (确保数据库服务正在运行)...")

        # 再次检查
        print("\n🔍 再次检查数据库服务状态...")
        if not check_database_service():
            print("❌ 数据库服务仍未运行，退出")
            sys.exit(1)

    # 选择快照恢复
    print("\n" + "=" * 60)
    print("🔄 从快照恢复模拟状态")
    print("=" * 60)
    print("本程序允许从任意时间步恢复模拟状态并继续运行")
    print("=" * 60)

    session_id, tick_to_restore = select_snapshot_to_restore()

    if not session_id or not tick_to_restore:
        print("\n❌ 未选择有效的快照，退出程序")
        sys.exit(0)

    # 恢复快照
    try:
        from snapshot_manager import create_snapshot_manager

        project_root = os.path.dirname(os.path.dirname(__file__))

        # ⚠️ 重要：comparison.py 使用独立的数据库文件，避免与 main.py 冲突
        # main.py 使用: database/simulation.db
        # comparison.py 使用: database/simulation_comparison.db
        main_db_path = os.path.join(project_root, 'database', 'simulation.db')
        comparison_db_path = os.path.join(project_root, 'database', 'simulation_comparison.db')

        snapshot_manager = create_snapshot_manager(project_root, main_db_path)

        print(f"\n🔄 正在从 tick {tick_to_restore} 恢复数据库...")
        # 先恢复到主数据库路径
        restored_db = snapshot_manager.restore_from_tick(tick_to_restore, session_id)

        if not restored_db:
            print("❌ 恢复失败，退出程序")
            sys.exit(1)

        # 将恢复的数据库复制到 comparison.py 专用数据库
        print(f"📋 复制恢复的数据库到 comparison.py 专用数据库...")
        import shutil
        shutil.copy2(main_db_path, comparison_db_path)

        print(f"✅ 成功从 tick {tick_to_restore} 恢复数据库状态")
        print(f"📁 Comparison 数据库: {comparison_db_path}")
        print(f"💡 这样可以与 main.py 同时运行而不冲突！")

    except Exception as e:
        print(f"❌ 恢复快照时出错: {e}")
        sys.exit(1)

    # 加载配置文件
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configs', 'experiment_config.json')
    with open(config_path, 'r') as file:
        config = json.load(file)

    # ⚠️ 重要：设置 comparison.py 专用数据库路径
    # 这样 comparison.py 和 main.py 可以同时运行而不冲突
    project_root = os.path.dirname(os.path.dirname(__file__))
    config['db_path'] = os.path.join(project_root, 'database', 'simulation_comparison.db')

    apply_selector_engine(config)

    # 显示恢复的tick信息
    print("\n" + "=" * 60)
    print(f"📊 从 tick {tick_to_restore} 继续模拟")
    print("=" * 60)

    # Get user selection - choose malicious bot system first
    enable_malicious_bots = get_user_choice_malicious_bots()

    # CLI 选择直接写入全局恶意攻击开关，成为单一真值来源
    control_flags.attack_enabled = enable_malicious_bots

    # Then choose the opinion balance system
    opinion_balance_choice = get_user_choice_opinion_balance()

    # Handle opinion balance system selection
    if opinion_balance_choice == "standalone":
        # Disable the opinion balance system so simulation.py knows this is standalone mode
        enable_opinion_balance = False
        enable_feedback_system = True  # Enable feedback iteration by default in standalone mode
        # Read monitoring interval from config
        monitoring_interval = get_required_feedback_monitoring_interval(config)

        # Set standalone mode flag
        if 'opinion_balance_system' not in config:
            config['opinion_balance_system'] = {}
        config['opinion_balance_system']['standalone_mode'] = True

        print("✅ Using the standalone opinion balance system; main program feature is disabled")
    else:
        # Disable the opinion balance system
        enable_opinion_balance = False
        enable_feedback_system = True  # Enable feedback iteration by default
        # Read monitoring interval from config
        monitoring_interval = get_required_feedback_monitoring_interval(config)
        print("❌ Opinion balance system disabled")

    # Select fact-checking system
    fact_check_type = get_user_choice_fact_checking()
    fact_check_settings = get_fact_checking_settings(fact_check_type)

    # CLI 选择直接写入全局事实核查开关，成为单一真值来源
    # 与恶意攻击开关类似的控制逻辑
    if fact_check_type == "third_party_fact_checking":
        control_flags.aftercare_enabled = True
    else:
        control_flags.aftercare_enabled = False

    # Content moderation: no CLI prompt — read from config file.
    # Can be toggled at runtime via /control/moderation API.
    control_flags.moderation_enabled = config.get('moderation', {}).get('content_moderation', False)

    # Get user choice for the prebunking system
    enable_prebunking = get_user_choice_prebunking()

    # Update config based on CLI selections - CLI takes precedence
    if 'malicious_bot_system' not in config:
        config['malicious_bot_system'] = {}

    # 保留 enabled 字段供日志/其他组件参考，但实际是否攻击
    # 已完全由 control_flags.attack_enabled 控制。
    config['malicious_bot_system']['enabled'] = enable_malicious_bots
    # Keep cluster_size from the config without forcing an override
    if enable_malicious_bots:
        # Only use defaults if the config does not specify them
        if 'attack_probability' not in config['malicious_bot_system']:
            config['malicious_bot_system']['attack_probability'] = 1.0
        if 'target_post_types' not in config['malicious_bot_system']:
            config['malicious_bot_system']['target_post_types'] = ['user_post']

    if 'opinion_balance_system' not in config:
        config['opinion_balance_system'] = {}

    config['opinion_balance_system']['enabled'] = enable_opinion_balance
    config['opinion_balance_system']['monitoring_enabled'] = enable_opinion_balance  # Monitoring is tied to opinion balance, not feedback
    config['opinion_balance_system']['feedback_system_enabled'] = enable_feedback_system
    config['opinion_balance_system']['feedback_monitoring_interval'] = monitoring_interval

    # 更新事实核查配置
    # 保留 experiment type 和 settings 供日志/其他组件参考，
    # 但实际是否执行事实核查已完全由 control_flags.aftercare_enabled 控制
    if 'experiment' not in config:
        config['experiment'] = {}

    config['experiment']['type'] = fact_check_type
    # 完全替换设置（避免上次运行的陈旧键）
    config['experiment']['settings'] = fact_check_settings

    # 更新prebunking配置
    if 'prebunking_system' not in config:
        config['prebunking_system'] = {}
    config['prebunking_system']['enabled'] = enable_prebunking

    # 禁用快照功能（comparison模式不需要再保存快照）
    config['snapshot_enabled'] = False

    print("\n" + "=" * 60)
    print("⚙️  配置已更新")
    print("=" * 60)
    print(f"• 恶意攻击: {'启用' if control_flags.attack_enabled else '禁用'}")
    print(f"• 事实核查: {'启用' if control_flags.aftercare_enabled else '禁用'}")
    print(f"• 内容审核: {'启用' if control_flags.moderation_enabled else '禁用'}")
    print(f"• 预先免疫: {'启用' if enable_prebunking else '禁用'}")
    print(f"• 起始tick: {tick_to_restore}")
    print(f"• 数据库: simulation_comparison.db (独立数据库，可与main.py同时运行)")
    print("=" * 60)

    # 创建模拟实例（注意：这里reset_db=False，因为我们已经恢复了快照）
    print("\n🚀 初始化模拟系统...")
    sim = Simulation(config)
    sim.reset_db = False  # 不要重置数据库，因为我们已经恢复了快照

    # 设置起始时间步
    start_tick = tick_to_restore

    # 询问用户要运行多少个时间步
    while True:
        try:
            num_steps_input = input(f"\n从 tick {start_tick} 开始，要运行多少个时间步? (默认: 10): ").strip()
            if not num_steps_input:
                num_steps = 10
            else:
                num_steps = int(num_steps_input)

            if num_steps > 0:
                break
            else:
                print("❌ 请输入大于0的数字")
        except ValueError:
            print("❌ 请输入有效的数字")

    print(f"\n🎯 将从 tick {start_tick} 运行到 tick {start_tick + num_steps - 1}")

    # 运行模拟
    try:
        print("\n" + "=" * 60)
        print("🎬 开始模拟")
        print("=" * 60)

        import asyncio
        asyncio.run(sim.run(num_steps))

    except KeyboardInterrupt:
        print("\n\n⚠️  模拟被用户中断")
    except Exception as e:
        print(f"\n\n❌ 模拟运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n👋 程序退出")
        exit(0)
