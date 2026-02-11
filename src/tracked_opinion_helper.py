import os
import json
import csv
import asyncio
import logging
from typing import Optional


def ensure_opinion_tracking_initialized(sim):
    """Ensure opinion-tracking attributes exist and initialize tracked users."""
    if not hasattr(sim, '_tracked_users'):
        sim._tracked_users = []
    if not hasattr(sim, '_first_malicious_post_id'):
        sim._first_malicious_post_id = None
    if not hasattr(sim, '_first_malicious_news_content'):
        sim._first_malicious_news_content = None
    if not hasattr(sim, '_opinions_log_path'):
        # Save under logs/tracked_opinions
        out_dir = os.path.join('logs', 'tracked_opinions')
        os.makedirs(out_dir, exist_ok=True)
        sim._opinions_log_path = os.path.join(
            out_dir, f"tracked_user_opinions_{sim.timestamp}.csv"
        )
    if not hasattr(sim, '_asked_timesteps'):
        sim._asked_timesteps = set()

    if not sim._tracked_users:
        _init_tracked_users(sim)


def _init_tracked_users(sim):
    try:
        normal_users = []
        for u in sim.users:
            if getattr(u, 'is_news_agent', False):
                continue
            if getattr(u, 'agent_type', '') == 'malicious_agent':
                continue
            normal_users.append(u)
        sim._tracked_users = normal_users[:3]
        ids = [getattr(u, 'user_id', '?') for u in sim._tracked_users]
        logging.info(f"Selected {len(sim._tracked_users)} tracked users: {ids}")
    except Exception as e:
        logging.error(f"Failed to initialize tracked users: {e}")
        sim._tracked_users = []


def discover_first_malicious_news_if_needed(sim):
    if getattr(sim, '_first_malicious_news_content', None):
        return
    try:
        cursor = sim.conn.cursor()
        try:
            cursor.execute(
                """
                SELECT post_id, content
                FROM posts
                WHERE is_news = 1 AND news_type = 'fake'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    """
                    SELECT post_id, content
                    FROM posts
                    WHERE is_news = 1 AND news_type = 'fake'
                    ORDER BY rowid ASC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
        except Exception:
            cursor.execute(
                """
                SELECT post_id, content
                FROM posts
                WHERE is_news = 1 AND news_type = 'fake'
                ORDER BY rowid ASC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

        if row:
            sim._first_malicious_post_id = row[0]
            sim._first_malicious_news_content = row[1]
            logging.info(f"Captured first malicious news post: {sim._first_malicious_post_id}")
    except Exception as e:
        logging.error(f"Failed to discover first malicious news: {e}")


def preload_first_fake_news_from_dataset(sim) -> Optional[str]:
    """Get the first fake news content directly from datasets (without DB).

    Priority:
    1) data/COVID2019-news.json -> first item's "Fake Narrative"
    Returns the content string or None.
    """
    try:
        covid_path = 'data/COVID2019-news.json'
        if os.path.exists(covid_path):
            with open(covid_path, 'r', encoding='utf-8') as f:
                arr = json.load(f)
                if isinstance(arr, list) and arr:
                    item = arr[0]
                    fake = item.get('Fake Narrative') or item.get('fake') or item.get('fake_narrative')
                    if fake:
                        sim._first_malicious_news_content = str(fake)
                        logging.info("Preloaded first fake news from COVID2019-news.json")
                        return sim._first_malicious_news_content
    except Exception as e:
        logging.warning(f"Failed COVID dataset preload: {e}")

    return None


def init_opinions_log(sim):
    if not getattr(sim, '_first_malicious_news_content', None) or not getattr(sim, '_opinions_log_path', None):
        return
    try:
        file_exists = os.path.exists(sim._opinions_log_path)
        if not file_exists:
            with open(sim._opinions_log_path, 'w', encoding='utf-8', newline='') as f:
                # 1) 写入固定新闻
                f.write(f"# news_content: {sim._first_malicious_news_content}\n")
                # 2) 写入被追踪角色的身份信息（集中在文件开头，不占用列）
                try:
                    if getattr(sim, '_tracked_users', None):
                        for u in sim._tracked_users:
                            persona = getattr(u, 'persona', {}) or {}
                            name = persona.get('name') if isinstance(persona, dict) else getattr(u, 'user_id', 'unknown-user')
                            try:
                                persona_compact = json.dumps(persona, ensure_ascii=False)
                            except Exception:
                                persona_compact = str(persona)
                            f.write(f"# user_identity: {name} | {persona_compact}\n")
                except Exception as e:
                    logging.warning(f"Failed to write tracked user identities: {e}")
                # 3) 写入表头（去掉 user_information 列）
                writer = csv.writer(f)
                writer.writerow(["timestep", "user_name", "user_memory", "content", "reason"])  # header
                logging.info(f"Initialized opinions log at {sim._opinions_log_path}")
    except Exception as e:
        logging.error(f"Failed to initialize opinions log file: {e}")


async def _get_user_current_memory_text(user) -> str:
    """Return reflection memory from cache (preferred), avoiding DB reads.

    Order:
    1) AgentUser instance cache: user._reflection_cache
    2) AgentMemory class cache: user.memory.get_cached_reflection()
    3) Trigger background cache update tasks and return empty string
    """
    try:
        # 1) Instance-level reflection cache on AgentUser
        cached = getattr(user, '_reflection_cache', None)
        if cached:
            return cached

        # 2) Class-level reflection cache on AgentMemory
        try:
            cached2 = user.memory.get_cached_reflection()
            if cached2:
                return cached2
        except Exception:
            pass

        # 3) Trigger background updates to refresh cache; do not block
        try:
            import asyncio as _asyncio
            _asyncio.create_task(user._update_reflection_cache_background())
            _asyncio.create_task(user.memory.update_reflection_cache())
        except Exception:
            pass

    except Exception as e:
        logging.warning(f"Failed to get cached reflection for {getattr(user,'user_id','?')}: {e}")
    # When no cached memory is available, explicitly return 'NONE'
    return "NONE"


async def ask_tracked_users_about_first_malicious_news(sim, timestep: int):
    if not getattr(sim, '_tracked_users', None) or not getattr(sim, '_first_malicious_news_content', None):
        return

    # Avoid duplicate asks for the same timestep
    try:
        if hasattr(sim, '_asked_timesteps'):
            if timestep in sim._asked_timesteps:
                return
            sim._asked_timesteps.add(timestep)
    except Exception:
        pass

    base_prompt = (
        "You are an ordinary social media user.\n"
        "Your identity:\n"
        "{persona_description}\n\n"
        "Your memory:\n"
        "{persona_memory}\n\n"
        "Here is a piece of news:\n"
        "{news_content}\n\n"
        "Based on your identity and memory, what is your opinion about this news? "
        "Explain why you have this opinion — describe the thinking or feeling process that led you to it.\n\n"
        "Respond in JSON format:\n"
        "{{\n"
        "  \"user_id\": \"{persona_id}\",\n"
        "  \"content\": \"<your natural opinion or reaction>\",\n"
        "  \"reason\": \"<analysis of why you personally have this opinion>\"\n"
        "}}"
    )

    for user in sim._tracked_users:
        try:
            persona = getattr(user, 'persona', {}) or {}
            persona_name = persona.get('name') if isinstance(persona, dict) else None
            if not persona_name:
                persona_name = getattr(user, 'user_id', 'unknown-user')

            # 为提示词生成准备 persona 描述（仅用于 prompt，不写入列）
            try:
                persona_desc = json.dumps(persona, ensure_ascii=False, indent=2) if isinstance(persona, dict) else str(persona)
            except Exception:
                persona_desc = str(persona)

            memory_text = await _get_user_current_memory_text(user)

            prompt_text = base_prompt.format(
                persona_description=persona_desc,
                persona_memory=memory_text,
                news_content=sim._first_malicious_news_content,
                persona_id=persona_name,
            )

            try:
                from multi_model_selector import MultiModelSelector
                if getattr(sim, "multi_model_selector", None):
                    model_name = sim.multi_model_selector.select_random_model(role="regular")
                else:
                    model_name = MultiModelSelector.DEFAULT_POOL[0]
            except Exception:
                model_name = getattr(sim, "engine", None) or "unknown"

            response = await asyncio.to_thread(
                sim.openai_client.chat.completions.create,
                model=model_name,
                messages=[
                    {"role": "system", "content": "You answer as the user described."},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.4
            )

            raw_content = response.choices[0].message.content if response and response.choices else ""

            parsed = None
            if raw_content:
                txt = raw_content.strip()
                if txt.startswith("```"):
                    txt = "\n".join([line for line in txt.splitlines() if not line.strip().startswith("```")])
                first = txt.find('{')
                last = txt.rfind('}')
                if first != -1 and last != -1 and last > first:
                    try:
                        parsed = json.loads(txt[first:last+1])
                    except Exception:
                        parsed = None

            content_out = parsed.get('content') if isinstance(parsed, dict) else None
            reason_out = parsed.get('reason') if isinstance(parsed, dict) else None
            if not content_out or not reason_out:
                content_out = raw_content or ""
                reason_out = ""

            # Always write a row（去掉 user_information 列）
            try:
                with open(sim._opinions_log_path, 'a', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        timestep,
                        persona_name,
                        memory_text,
                        content_out,
                        reason_out
                    ])
            except Exception as e:
                logging.error(f"Failed writing to opinions log: {e}")

        except Exception as e:
            logging.error(f"Failed to query opinion for user {getattr(user,'user_id','?')}: {e}")
