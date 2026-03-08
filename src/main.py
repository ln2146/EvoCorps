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


@control_app.post("/control/attack")
def set_attack_flag(body: ToggleRequest):
    """Enable or disable malicious bot attacks at runtime."""

    control_flags.attack_enabled = bool(body.enabled)
    return {"attack_enabled": control_flags.attack_enabled}


@control_app.post("/control/attack-mode")
def set_attack_mode(body: AttackModeRequest):
    """Set malicious attack coordination mode at runtime."""

    mode = str(body.mode).strip().lower()

    # Single source of truth for runtime status
    control_flags.attack_mode = mode

    # Sync strategy router config used by malicious bot manager
    from malicious_bots.config import DEFAULT_CONFIG
    DEFAULT_CONFIG.attack_mode.mode = mode

    return {"attack_mode": control_flags.attack_mode}


@control_app.post("/control/aftercare")
def set_aftercare_flag(body: ToggleRequest):
    """Enable or disable third-party fact checking at runtime.
    
    This controls the third-party fact checking system (_run_fact_checking_async).
    Truth appending is NOT affected by this flag and runs unconditionally.
    """

    control_flags.aftercare_enabled = bool(body.enabled)
    return {"aftercare_enabled": control_flags.aftercare_enabled}


@control_app.post("/control/auto-status")
def set_auto_status_flag(body: ToggleRequest):
    """Enable or disable opinion-balance auto monitoring/intervention via port 8000.

    语义：WSL 侧只需要调用 8000 端口，实际由 main.py 在

        http://localhost:8100/launcher/auto-status

    上转发同样的 enabled=true/false 给启动器，实现跨环境控制。
    """

    enabled = bool(body.enabled)

    # 1) 更新当前进程的全局控制变量
    control_flags.auto_status = enabled

    # 2) 将 enabled 原样转发给启动器端口
    #    等价于：
    #    curl -X POST http://localhost:8100/launcher/auto-status \
    #         -H "Content-Type: application/json" \
    #         -d '{"enabled": true/false}'
    resp_data = {}
    try:
        resp = requests.post(
            "http://localhost:8100/launcher/auto-status",
            json={"enabled": enabled},
            timeout=5,
        )
        resp_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    except Exception as e:
        # 启动器端口可能未开启，主流程仍然保持可用
        resp_data = {"error": str(e)}

    return {
        "auto_status": control_flags.auto_status,
        "launcher_call": resp_data,
    }


@control_app.get("/control/auto-status")
def get_auto_status_flag():
    """Get current opinion-balance auto monitoring/intervention status."""

    return {"auto_status": control_flags.auto_status}


@control_app.post("/control/moderation")
def set_moderation_flag(body: ToggleRequest):
    """Enable or disable moderation system at runtime.

    The moderation system maintains ecological boundaries through:
    - Visibility degradation: reducing content weight in recommendations
    - Warning labels: marking content with official warnings
    - Hard takedowns: removing posts and banning users
    """

    control_flags.moderation_enabled = bool(body.enabled)
    return {"moderation_enabled": control_flags.moderation_enabled}


@control_app.get("/control/moderation")
def get_moderation_status():
    """Get current moderation system status and statistics."""

    stats = {}
    if moderation_service:
        stats = moderation_service.get_stats().model_dump()

    return {
        "moderation_enabled": control_flags.moderation_enabled,
        "stats": stats,
    }


@control_app.post("/analysis/post-comments")
def analyze_post_comments(body: PostCommentsAnalysisRequest):
    import os
    import json
    import logging
    import sqlite3
    import requests
    from database_manager import DatabaseManager

    post_id = body.post_id

    # 1) 打开数据库并读取帖子与评论
    project_root = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(project_root, "database", "simulation.db")

    db_manager = DatabaseManager(db_path, reset_db=False)
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT post_id, content, author_id, created_at, num_comments
        FROM posts
        WHERE post_id = ?
        """,
        (post_id,),
    )
    post_row = cursor.fetchone()

    if not post_row:
        return {"error": f"Post {post_id} not found"}

    cursor.execute(
        """
        SELECT comment_id, content, author_id, created_at, num_likes
        FROM comments
        WHERE post_id = ?
        ORDER BY num_likes DESC, created_at ASC
        LIMIT 30
        """,
        (post_id,),
    )
    comment_rows = cursor.fetchall()

    # 2) 构造提示词
    post_content = post_row["content"] or ""
    post_author = post_row["author_id"]

    comments_block_lines = []
    for idx, c in enumerate(comment_rows, start=1):
        comments_block_lines.append(
            f"[{idx}] author={c['author_id']} likes={c['num_likes']}: {c['content']}"
        )
    comments_block = "\n".join(comments_block_lines) if comments_block_lines else "(暂无评论)"

    system_prompt = (
        "你是一名严谨的舆论分析助手，专门分析某个帖子评论区的整体情绪氛围、观点极端程度，"
        "并用自然语言总结多数观点与少数观点。你需要返回结构化 JSON，便于前端程序直接读取。"
    )

    user_prompt = f"""请基于下面的内容进行分析：

    [主帖]
    作者: {post_author}
    内容: {post_content}

    [评论区]
    {comments_block}

    你的任务是：
    1. **内部评估每条评论**（不在最终输出中显示）：
    * 对每条评论的情感分数（sentiment_score）进行评估，使用以下五个离散值之一：0, 0.25, 0.5, 0.75, 1。
    * 对每条评论的极端程度分数（extremeness_score）进行评估，使用以下五个离散值之一：0, 0.25, 0.5, 0.75, 1。

    2. **计算整体分数**：
    * 基于所有评论的情感分数，计算平均值，得到最终的 `sentiment_score_overall`。
    * 基于所有评论的极端程度分数，计算平均值，得到最终的 `extremeness_score_overall`。
    * **重要**：这两个整体分数应为 0 到 1 之间的任意数值（不限于那五个离散值），例如 0.33、0.67 等，以更精确地反映整体水平。

    3. 用一段中文总结评论区的主要观点结构。

    请严格按照下面的 JSON 格式直接作答，只返回整体分析结果：

    {{
    "sentiment_score_overall": 0.42, // 计算出的0-1之间的任意值
    "extremeness_score_overall": 0.38, // 计算出的0-1之间的任意值
    "summary": "一段中文总结，概括评论区的主要观点结构。"
    }}"""

    # 3) 直接用 requests 调用 AIHUBMIX（与 curl 完全一致）
    try:
        base_url = OPENAI_BASE_URL.rstrip("/") if OPENAI_BASE_URL else "https://api.openai.com/v1"
        response = requests.post(
            url=f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 600,
                "temperature": 0.5,
                "response_format": {"type": "json_object"},
            }),
            timeout=120,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"LLM HTTP {response.status_code}: {response.text}"
            )

        resp_json = response.json()

        raw_content = (
            resp_json.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not raw_content:
            analysis_data = {
                "sentiment_score_overall": None,
                "extremeness_score_overall": None,
                "summary": None,
                "error": "LLM returned empty content",
                "raw_text": resp_json,
            }
        else:
            try:
                analysis_data = json.loads(raw_content)
            except Exception:
                # 兜底：从 markdown 代码块或裸文本中提取 JSON
                import re
                m = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if m:
                    try:
                        analysis_data = json.loads(m.group())
                    except Exception as e2:
                        analysis_data = {
                            "sentiment_score_overall": None,
                            "extremeness_score_overall": None,
                            "summary": None,
                            "error": f"json_parse_failed: {e2}",
                            "raw_text": raw_content,
                        }
                else:
                    analysis_data = {
                        "sentiment_score_overall": None,
                        "extremeness_score_overall": None,
                        "summary": None,
                        "error": "no_json_in_response",
                        "raw_text": raw_content,
                    }

    except Exception as e:
        logging.error(f"Post comments analysis failed for {post_id}: {e}")
        analysis_data = {
            "sentiment_score_overall": None,
            "extremeness_score_overall": None,
            "summary": None,
            "error": str(e),
        }

    # 4) 关闭数据库连接
    try:
        db_manager.close()
    except Exception:
        pass

    return {
        "post_id": post_id,
        "post_content": post_content,
        "num_comments": len(comment_rows),
        "sentiment_score_overall": analysis_data.get("sentiment_score_overall"),
        "extremeness_score_overall": analysis_data.get("extremeness_score_overall"),
        "summary": analysis_data.get("summary"),
        "analysis_raw": analysis_data.get("raw_text"),
        "error": analysis_data.get("error"),
    }


def start_control_api_server(host: str = "0.0.0.0", port: int = 8000) -> Optional[threading.Thread]:
    """Start the FastAPI control server in a background thread.

    The server shares the same process and memory space as the
    simulation, so updates to control_flags are visible immediately
    inside simulation.py.
    """

    def _run() -> None:
        config = uvicorn.Config(
            control_app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        server.run()

    try:
        thread = threading.Thread(target=_run, daemon=True, name="control-api-server")
        thread.start()
        print(f"📡 Control API server started at http://{host}:{port}")
        return thread
    except Exception as e:
        print(f"⚠️  Failed to start control API server: {e}")
        return None

def setup_comprehensive_logging():
    """Set comprehensive logging configuration affecting all logging calls."""
    # Create logs/output directory - use a path relative to the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Public-opinion-balance directory
    log_dir = os.path.join(project_root, "logs", "output")
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"simulation_{timestamp}.log")
    
    # Clear existing log handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # Also output to console
        ],
        force=True  # Force reconfiguration
    )
    
    print(f"📁 Log file: {log_file}")
    return log_file

def print_opinion_balance_status(sim):
    """Print opinion balance system status."""
    if hasattr(sim, 'opinion_balance_manager') and sim.opinion_balance_manager:
        stats = sim.opinion_balance_manager.get_system_stats()
        if stats.get("enabled"):
            print("\n" + "="*60)
            print("⚖️  Opinion balance system real-time status")
            print("="*60)

            monitoring = stats.get("monitoring", {})
            interventions = stats.get("interventions", {})

            print("📊 Monitoring stats:")
            print(f"   Total monitored posts: {monitoring.get('total_posts_monitored', 0)}")
            print(f"   Intervention needed: {monitoring.get('intervention_needed', 0)}")
            print(f"   Intervention trigger rate: {monitoring.get('intervention_rate', 0):.1%}")

            print("\n🚨 Intervention stats:")
            print(f"   Total interventions: {interventions.get('total_interventions', 0)}")
            print(f"   Agent responses: {interventions.get('total_agent_responses', 0)}")
            print(f"   Average effectiveness score: {interventions.get('average_effectiveness', 0):.1f}/10")

            if interventions.get('total_interventions', 0) > 0:
                print("\n✅ System successfully detected and intervened with extreme content!")

                # Show recent intervention history
                if hasattr(sim.opinion_balance_manager, 'intervention_history'):
                    recent = sim.opinion_balance_manager.intervention_history[-3:]
                    if recent:
                        print("\n📋 Recent intervention records:")
                        for i, record in enumerate(recent, 1):
                            print(f"   {i}. Intervention ID: {record.get('intervention_id')}")
                            print(f"      Original post ID: {record.get('original_post_id')}")
                            print(f"      Agent responses: {len(record.get('agent_post_ids', []))}")
                            print(f"      Effectiveness score: {record.get('effectiveness_score', 0):.1f}/10")
            else:
                print("\n⏳ No intervention triggered yet, continuing monitoring...")

            print("="*60)
        # When the system is disabled, do not show any statistics information
    else:
        print("\n❌ Opinion balance system not initialized")

def print_persona_config_info(config):
    """Show detailed persona configuration information."""
    agent_config_path = config.get('agent_config_path', 'N/A')

    print("\n" + "="*60)
    print("🎭 Persona identity configuration info")
    print("="*60)

    if agent_config_path == "separate":
        separate_config = config.get('separate_personas', {})
        positive_ratio = separate_config.get('positive_ratio', 0.33)
        neutral_ratio = separate_config.get('neutral_ratio', 0.33)
        negative_ratio = separate_config.get('negative_ratio', 0.34)

        print("📊 Current config: all regular users use neutral personas")
        print(f"   • Neutral persona ratio: {neutral_ratio:.1%} (regular users)")
        print(f"   • Positive persona ratio: {positive_ratio:.1%} (system counteraction only)")
        print(f"   • Negative persona ratio: {negative_ratio:.1%} (malicious bots only)")
        print(f"   • Neutral persona file: {separate_config.get('neutral_file', 'personas/neutral_personas_database.json')}")
        print(f"   • Positive persona file: {separate_config.get('positive_file', 'personas/positive_personas_database.json')} (system only)")
        print(f"   • Negative persona file: {separate_config.get('negative_file', 'personas/negative_personas_database.json')} (bot only)")

        print("\n📋 Persona type descriptions:")
        print("   🟡 Neutral personas: base role for regular social media users")
        print("      - Strong emotional reactions and easily influenced")
        print("      - Tend to spread controversial and inflammatory content")
        print("      - Lack fact-checking awareness")
        print("      - All regular users use this role")
        print()
        print("   🟢 Positive personas: counter roles used only by the opinion balance system")
        print("      - Rational, constructive, gentle responses")
        print("      - Support rational discussion and fact-checking")
        print("      - Called only when extreme content is detected")
        print()
        print("   🔴 Negative personas: attack roles used only by the malicious bot system")
        print("      - Extreme, radical, inflammatory content")
        print("      - Spread conspiracy theories or hate speech")
        print("      - Used only during malicious bot attacks")

        # Calculate actual allocated user counts - now all regular users are neutral
        total_users = config.get('num_users', 4)

        # All regular users use neutral roles
        num_positive = 0  # Regular users do not use positive roles
        num_neutral = total_users  # All regular users are neutral
        num_negative = 0  # Regular users do not use negative roles

        print(f"\n📊 Actual user allocation (total: {total_users}):")
        print(f"   • Regular users (neutral): {num_neutral} ({num_neutral/total_users:.1%})")
        print("   • Positive roles: 0 (only used during system counteraction)")
        print("   • Negative roles: 0 (only used by malicious bots)")

        print("\n⚙️  Configuration notes:")
        print("   • All regular users use neutral roles and show strong emotional reactions")
        print("   • Positive and negative roles are used only in specific system functions")
        print("   • This configuration makes regular users more vulnerable to malicious attacks")
        print("   • It helps test the opinion balance system's intervention effectiveness")

    else:
        print("📁 Current config: single-file mode")
        print(f"   • Config file: {agent_config_path}")
        print("   • All personas come from the same file")
        print("   • To mix positive and negative personas, set agent_config_path to 'separate'")

    print("="*60)

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

def get_user_choice_feedback_system():
    """Get user choice for the feedback and iteration system."""
    print("\n" + "="*60)
    print("🔄 Feedback and iteration system selection")
    print("="*60)
    print("The feedback and iteration system includes:")
    print("  📊 [Evaluation] Analyst Agent:")
    print("      • Continuously monitor engagement data on leader posts and sentiment changes in comments")
    print("      • Periodically generate effect briefs")
    print("      • Compare with baseline data before actions")
    print("  🎯 [Iteration] Strategist Agent:")
    print("      • Receive effect reports from the Analyst Agent")
    print("      • Evaluate whether current strategies are effective")
    print("      • If negative rhetoric appears, immediately devise supplementary action plans")
    print()
    print("Note: Enabling increases system complexity and runtime")
    print("="*60)

    while True:
        choice = input("Enable feedback and iteration system? (y/n): ").strip().lower()

        if choice in ['y', 'yes', 'enable']:
            print("✅ Selected to enable the feedback and iteration system")
            return True
        elif choice in ['n', 'no', 'disable']:
            print("❌ Selected to disable the feedback and iteration system")
            return False
        else:
            print("❌ Invalid input, please enter y (enable) or n (disable)")

def get_monitoring_interval():
    """Get user selection for monitoring interval."""
    print("\n⏰ Select monitoring interval:")
    print("Select monitoring duration: 1/3/5/10/30/60 (minutes)")

    while True:
        try:
            choice = input("Please select (1/3/5/10/30/60): ").strip()

            # Parse user input as a number directly
            interval = int(choice)
            supported_intervals = [1, 3, 5, 10, 30, 60]

            if interval not in supported_intervals:
                print(f"❌ Unsupported {interval} minutes, supported: {supported_intervals}")
                # Select the nearest supported value
                interval = min(supported_intervals, key=lambda x: abs(x - interval))
                print(f"🔄 Auto-adjusted to: {interval} minutes")

            print(f"✅ Monitoring interval: {interval} minutes")

            return interval

        except ValueError:
            print("❌ Please enter a valid number")

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
    """Get user choice for the fact-checking feature."""
    print("\n" + "="*60)
    print("🔍 Third-party fact-checking system configuration")
    print("="*60)
    print("Third-party fact-checking system features:")
    print("  • Check 10 news items published in the current step after each time step")
    print("  • Run asynchronously with the main flow, without blocking user interaction")
    print("  • Automatically detect and label misinformation to improve platform quality")
    print("  • High accuracy, suitable for accuracy-sensitive scenarios")
    print("  • Use default parameter settings")
    print("\nNote: enabling runs fact checking asynchronously after each time step")

    while True:
        try:
            choice = input("\nEnable third-party fact checking? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                print("✅ Third-party fact checking enabled")
                print("   - Will asynchronously check news content after each time step")
                print("   - Check 10 items per step")
                return "third_party_fact_checking"
            elif choice in ['n', 'no']:
                print("✅ Third-party fact checking disabled")
                return "no_fact_checking"
            else:
                print("❌ Please enter y (enable) or n (disable)")
        except KeyboardInterrupt:
            print("\n👋 Program exited")
            exit(0)

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
    # Set comprehensive logging configuration affecting all logging calls
    log_file = setup_comprehensive_logging()

    # 读取环境变量（用于从快照恢复）
    start_tick_env = os.environ.get('START_TICK', '')
    reset_db_env = os.environ.get('RESET_DB', 'true')
    parent_session_id = os.environ.get('PARENT_SESSION_ID', '')

    start_tick = int(start_tick_env) if start_tick_env.isdigit() else 1
    reset_db = reset_db_env.lower() != 'false'

    # 如果从快照恢复但没有通过环境变量传递 parent session，自动查找
    if start_tick > 1 and not parent_session_id:
        try:
            project_root = os.path.dirname(os.path.dirname(__file__))
            snapshots_dir = os.path.join(project_root, "snapshots")
            if os.path.exists(snapshots_dir):
                best_session = None
                best_time = ""
                for sid in os.listdir(snapshots_dir):
                    session_dir = os.path.join(snapshots_dir, sid)
                    if not os.path.isdir(session_dir):
                        continue
                    tick_dir = os.path.join(session_dir, f"tick_{start_tick}")
                    if os.path.isdir(tick_dir):
                        if sid > best_time:
                            best_time = sid
                            best_session = sid
                if best_session:
                    parent_session_id = best_session
                    print(f"📌 自动检测到父快照会话: {parent_session_id}")
        except Exception as e:
            print(f"⚠️ 自动检测父快照失败: {e}")

    if start_tick > 1:
        print(f"📌 从快照恢复: 起始 tick = {start_tick}")
        print(f"📌 数据库重置: {'是' if reset_db else '否'}")
        if parent_session_id:
            print(f"📌 父快照会话: {parent_session_id}")

    # Start the FastAPI control server in the background so that
    # external tools / frontend can toggle runtime flags while the
    # simulation is running.
    start_control_api_server()

    # Check database service
    print("🔍 Checking database service status...")
    if not check_database_service():
        print("\n" + "="*60)
        print("⚠️  Database service is not running!")
        print("📋 Please follow these steps:")
        print("1. Open a new terminal window")
        print("2. Run: python src/start_database_service.py")
        print("3. Wait for the service to start")
        print("4. Then return to this window to continue the simulation")
        print("="*60)
        
        input("Press Enter to continue (ensure the database service is running)...")
        
        # Check again
        print("\n🔍 Checking database service status again...")
        if not check_database_service():
            print("❌ Database service is still not running, exiting")
            sys.exit(1)
    
    # Fix config file path
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configs', 'experiment_config.json')
    with open(config_path, 'r') as file:
        config = json.load(file)

    apply_selector_engine(config)
    config['reset_db'] = reset_db
    config['restore_from_snapshot'] = bool(parent_session_id)

    # Reset simulation database before each run (unless restoring from snapshot)
    from database_manager import DatabaseManager
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'simulation.db')
    if reset_db:
        reset_manager = DatabaseManager(db_path, reset_db=True)
        reset_manager.close()
    else:
        print("📌 跳过数据库重置（从快照恢复）")

    # 清理所有旧快照（仅在非快照恢复模式下清理）
    if reset_db:
        try:
            from snapshot_manager import create_snapshot_manager
            project_root = os.path.dirname(os.path.dirname(__file__))
            snapshot_mgr = create_snapshot_manager(project_root, db_path)
            snapshot_mgr.cleanup_all_snapshots()
            print("🗑️  已清理所有旧快照数据")
        except Exception as e:
            print(f"⚠️  清理快照失败: {e}")

    # Show persona configuration info
    print_persona_config_info(config)

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

    # Update fact-checking config
    # 保留 experiment type 和 settings 供日志/其他组件参考，
    # 但实际是否执行事实核查已完全由 control_flags.aftercare_enabled 控制
    if 'experiment' not in config:
        config['experiment'] = {}

    config['experiment']['type'] = fact_check_type
    # Replace settings entirely (avoid stale keys from a previous run)
    config['experiment']['settings'] = fact_check_settings

    # Update prebunking config
    if 'prebunking_system' not in config:
        config['prebunking_system'] = {}
    config['prebunking_system']['enabled'] = enable_prebunking

    # Persist moderation flag so it survives restarts
    if 'moderation' not in config:
        config['moderation'] = {}
    config['moderation']['content_moderation'] = control_flags.moderation_enabled

    # Persist user selections to the config file (engine is resolved dynamically via selector; do not persist it)
    config_to_save = dict(config)
    config_to_save.pop('engine', None)
    with open(config_path, 'w') as f:
        json.dump(config_to_save, f, indent=4)

    Utils.configure_logging(engine=config['engine'])

    # Show startup information
    print("\n🚀 Starting social media simulation system")
    print("="*50)
    print(f"👥 Users: {config['num_users']}")
    print(f"⏰ Time steps: {config['num_time_steps']}")
    print(f"🤖 AI engine: {config['engine']}")
    print(f"🌡️  Temperature: {config['temperature']}")
    print(f"🔥 Malicious bot system: {'enabled' if enable_malicious_bots else 'disabled'}")
    print(f"⚖️  Opinion balance system: {'enabled' if enable_opinion_balance else 'disabled'}")
    if enable_opinion_balance:
        print(f"   📊 Feedback system: {'enabled' if enable_feedback_system else 'disabled'}")
        if enable_feedback_system:
            print(f"   ⏰ Monitoring interval: {monitoring_interval} minutes")

    print(f"🛡️  Prebunking system: {'enabled' if enable_prebunking else 'disabled'}")
    if enable_prebunking:
        print("   • Will insert safety prompts into regular users' feeds")

    # 显示内容审核状态（由全局开关控制）
    if control_flags.moderation_enabled:
        print("🛡️  Content moderation: ✅ enabled")
        print("   • Visibility degradation, warning labels, hard takedowns")
        print("   • Can be toggled via API at runtime")
    else:
        print("🛡️  Content moderation: ❌ disabled")
        print("   • Can be enabled via API at runtime")

    # 显示第三方事实核查状态（由全局开关控制）
    if control_flags.aftercare_enabled:
        print("🔍 Third-party fact checking: ✅ enabled")
        print("   • Asynchronously check news content after each time step")
        print("   • Run in parallel with the main flow, without affecting user interaction")
        print("   • Can be toggled via API at runtime")
    else:
        print("🔍 Third-party fact checking: ❌ disabled")
        print("   • Can be enabled via API at runtime")

    # Show news configuration info
    news_config = config.get('news_injection', {})
    selection_mode = news_config.get('selection_mode', 'sequential')
    articles_per_injection = news_config.get('articles_per_injection', 5)

    print(f"📰 News injection: {articles_per_injection} articles/step")
    if selection_mode == 'random':
        print("📰 News selection: 🎲 random (content differs each run)")
    else:
        print("📰 News selection: 📋 sequential (starts from the first item)")

    # Show new user configuration info
    new_user_config = config.get('new_users', {})
    add_probability = new_user_config.get('add_probability', 0.0)
    users_per_step = new_user_config.get('users_per_step', 'same_as_initial')
    start_step = new_user_config.get('start_step', 1)
    initial_users = config.get('num_users', 4)

    if add_probability > 0:
        print(f"👥 New user generation: ✅ enabled (probability: {add_probability:.1%})")
        if users_per_step == 'same_as_initial':
            print(f"   Added per step: {initial_users} users (same as initial count)")
        else:
            print(f"   Added per step: {users_per_step} users")
        print(f"   Start step: step {start_step}")
        print("   User types: allocate positive/neutral/negative roles at a 1:1:1 ratio")
    else:
        print("👥 New user generation: ❌ disabled")

    # Show persona configuration info
    agent_config_path = config.get('agent_config_path', 'N/A')
    print(f"🎭 Persona config: {agent_config_path}")

    # Check whether this is separate mode
    if agent_config_path == "separate":
        separate_config = config.get('separate_personas', {})
        positive_ratio = separate_config.get('positive_ratio', 0.33)
        neutral_ratio = separate_config.get('neutral_ratio', 0.33)
        negative_ratio = separate_config.get('negative_ratio', 0.34)
        positive_file = separate_config.get('positive_file', 'personas/positive_personas_database.json')
        neutral_file = separate_config.get('neutral_file', 'personas/neutral_personas_database.json')
        negative_file = separate_config.get('negative_file', 'personas/negative_personas_database.json')

        print("   Mixed mode: ✅ regular users use neutral personas, system uses positive/negative roles")
        print("   Regular users: 100% neutral roles (emotional, easily influenced)")
        print("   Positive roles: used only by the opinion balance system")
        print("   Negative roles: used only by the malicious bot system")
        print(f"   Neutral persona file: {neutral_file}")
        print(f"   Positive persona file: {positive_file} (system only)")
        print(f"   Negative persona file: {negative_file} (bot only)")

        if separate_config.get('shuffle_order', True):
            print("   Persona order: 🔀 shuffled")
        else:
            print("   Persona order: 📋 keep original order")
    else:
        print("   Persona config: 📁 single-file mode")
        print(f"   Config file: {agent_config_path}")

    # Show malicious bot system status
    mbs_config = config.get('malicious_bot_system', {})
    if mbs_config.get('enabled'):
        print("🔥 Malicious bot system: ✅ enabled")
        cluster_size = mbs_config.get('cluster_size', 10)
        print(f"   Cluster size: {cluster_size} (select {cluster_size} malicious roles per attack)")
        print(f"   Attack probability: {mbs_config.get('attack_probability', 0.3):.1%}")
        print(f"   Initial attack threshold: {mbs_config.get('initial_attack_threshold', 15)} (comments+likes+shares)")
        print(f"   Subsequent attack interval: {mbs_config.get('subsequent_attack_interval', 30)}")
        print("   Expected effect: escalating malicious attacks when post heat reaches the threshold")
    else:
        print("🔥 Malicious bot system: ❌ disabled")
        print("   Run mode: no malicious attack simulation")

    # Show opinion balance system status
    obs_config = config.get('opinion_balance_system', {})
    if obs_config.get('enabled'):
        print("⚖️  Opinion balance system: ✅ enabled")
        print(f"   Intervention threshold: {obs_config.get('intervention_threshold', 'N/A')}")
        print(f"   Response delay: {obs_config.get('response_delay_minutes', 'N/A')} minutes")

        # Show monitoring interval configuration
        monitoring_interval = get_required_feedback_monitoring_interval(config)
        interval_descriptions = {
            1: "🔥 Ultra-high-frequency monitoring",
            3: "🚀 High-frequency monitoring",
            5: "🚀 High-frequency monitoring",
            10: "⚡ Mid-high-frequency monitoring",
            30: "📊 Standard monitoring",
            60: "🕐 Low-frequency monitoring"
        }
        interval_desc = interval_descriptions.get(monitoring_interval, "📊 Custom monitoring")
        print(f"   Monitoring interval: {monitoring_interval} minutes ({interval_desc})")
        print("   Expected effect: detect and intervene with extreme content")
        if enable_feedback_system:
            print("   Phase 3 feature: feedback and iteration system enabled")
        else:
            print("   Phase 3 feature: feedback and iteration system disabled")
    else:
        print("⚖️  Opinion balance system: ❌ disabled")
        print("   Run mode: pure social media simulation (no content intervention)")

    # Show combined mode description
    print("\n📋 Simulation mode:")
    if enable_malicious_bots and enable_opinion_balance:
        print("   🎭 Full adversarial mode: malicious attacks + opinion balance")
        print("      Flow: users post → malicious bots attack → opinion balance intervention")
    elif enable_malicious_bots and not enable_opinion_balance:
        print("   🔥 Malicious attack mode: malicious attacks only")
        print("      Flow: users post → malicious bots attack")
    elif not enable_malicious_bots and enable_opinion_balance:
        print("   ⚖️  Balance monitoring mode: opinion balance only")
        print("      Flow: monitor content → detect extreme rhetoric → intervene")
    else:
        print("   📱 Basic simulation mode: clean simulation")
        print("      Flow: users interact normally, no special systems")

    print("="*50)

    # If opinion balance and feedback/iteration are enabled, show related info
    if enable_opinion_balance and enable_feedback_system:
        interval_descriptions = {
            1: "🔥 Ultra-high-frequency monitoring (1 minute)",
            3: "🚀 High-frequency monitoring (3 minutes)",
            5: "🚀 High-frequency monitoring (5 minutes)",
            10: "⚡ Mid-high-frequency monitoring (10 minutes)",
            30: "📊 Standard monitoring (30 minutes)",
            60: "🕐 Low-frequency monitoring (60 minutes)"
        }
        interval_desc = interval_descriptions.get(
            monitoring_interval,
            f"📊 Custom monitoring ({monitoring_interval} minutes)"
        )

        print("\n🔄 Phase 3: feedback and iteration system:")
        print("   📊 [Evaluation] Analyst Agent:")
        print("      • Continuously monitor engagement data on leader posts and sentiment changes in comments")
        print(f"      • Generate effect briefs every {monitoring_interval} minutes")
        print("      • Compare with baseline data before actions")
        print("   🎯 [Iteration] Strategist Agent:")
        print("      • Receive effect reports from the Analyst Agent")
        print("      • Evaluate whether current strategies are effective")
        print("      • If negative rhetoric appears, immediately devise supplementary action plans")
        print(f"   ⏰ Monitoring config: {interval_desc}")
        print("   💾 Effectiveness reports saved: logs/effectiveness_reports/effectiveness_report_[ID]_[timestamp].json")
        print("   🔄 Dynamic adjustments: activate extra agents, leader clarifications, increase activities")
        print("="*50)
    elif enable_opinion_balance and not enable_feedback_system:
        print("\n⚖️  Basic opinion balance system:")
        print("   🎯 Only core intervention features enabled")
        print("   📊 Real-time monitoring and response to extreme content")
        print("   ❌ Feedback and iteration system disabled")
        print("   💡 For full features, rerun and enable the feedback system")
        print("="*50)

    # Prompt the user to start the opinion balance system manually (standalone mode)
    if opinion_balance_choice == "standalone":
        print("\n" + "="*60)
        print("🚀 Opinion balance system configuration complete")
        print("="*60)
        
        print("📋 Opinion balance system configuration:")
        print("   🎯 System enabled: ✅")
        print("   📊 Monitoring enabled: ✅")
        print(f"   🔄 Feedback system: {'✅' if enable_feedback_system else '❌'}")
        print(f"   ⏰ Monitoring interval: {monitoring_interval} minutes")
        
        print("\n📋 Please follow these steps to start the opinion balance system manually:")
        print("1. Open a new terminal window")
        print("2. Run: python src/opinion_balance_launcher.py")
        print("3. In the standalone launcher, enter 'start' to begin monitoring")
        print("4. The opinion balance system will use the following configuration:")
        print(f"   • Monitoring interval: {monitoring_interval} minutes")
        print(f"   • Feedback system: {'enabled' if enable_feedback_system else 'disabled'}")
        print("5. Then return to this window to continue the simulation")
        print("="*60)
        
        input("Press Enter to continue the simulation (ensure the opinion balance system is started manually)...")
        
        print("✅ Continuing simulation; opinion balance system will run in a separate terminal")
        print("="*60)

    logging.info(f"Starting simulation with {config['num_users']} users for {config['num_time_steps']} time steps using {config['engine']}...")

    # Create and run the simulation
    sim = Simulation(config)

    # Run the simulation (从 start_tick 开始)
    if start_tick > 1:
        print(f"\n🎬 Starting simulation from tick {start_tick}...")
    else:
        print("\n🎬 Starting simulation...")
    import asyncio
    asyncio.run(sim.run(
        config['num_time_steps'],
        start_tick=start_tick,
        parent_session_id=parent_session_id or None,
        parent_tick=start_tick if parent_session_id else None
    ))

    # Show final results
    print("\n✅ Simulation completed!")
    print("\n🎉 Thanks for using the social media simulation system!")
    try:
        input("\nPress Enter to exit...")
    except EOFError:
        # 管道输入耗尽时（自动输入脚本执行完毕），保持终端打开不关闭
        print("\n📋 Simulation finished. Terminal will remain open.")
        print("📋 Press Ctrl+C to close this terminal.")
        import time
        while True:
            time.sleep(1)  # 无限等待，保持终端打开
