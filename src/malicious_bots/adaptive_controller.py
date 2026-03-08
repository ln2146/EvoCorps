"""
AdaptiveController — 根据平台审核压力自动调整恶意水军攻击策略。

设计参考：MultiAgent4Collusion 的 update_reflection_memory(ban=True) 机制：
    - 感知层：查询被审核处理的攻击目标帖子比例 + 被封禁的水军账号比例，计算压力系数
    - 调整层：根据压力等级修改角色比例、集群规模、提示词风格
    - 反思层：HIGH 压力时调用 LLM 生成规避策略（类比 SharedMemory.shared_reflections）

压力感知数据源（三信号聚合，均与审核系统实际写入字段对齐）：

    信号 1（帖子级审核率 0.30权重）— 增量水印窗口：
        JOIN malicious_attacks ↔ posts
        统计最近一步新增攻击目标帖子中 posts.status='taken_down' 或 moderation_action IS NOT NULL 的比例
        → bots 主要攻击 fake news 帖，审核命中率有限；权重从 0.5 降至 0.30

    信号 2（评论警告率 0.25权重）— 全量历史查询：
        JOIN malicious_comments ↔ comments ↔ users（无 WHERE 水印）
        统计全部曾活跃水军中 comment_violation_count > 0 的比例
        → 使用全量查询，避免增量窗口导致已被拦截账号消失

    信号 3（用户封禁率 0.45权重）— 全量历史查询，最高权重：
        统计全部曾活跃水军中 users.status='banned' 的比例
        → 全量累计，封号账号的压力贡献不会随时间衰减为 0；封号是最确定的审核信号

    绝对触发条件（叠加在公式分值之上）：
        ban_rate  >= 0.25  → 强制 HIGH（超过 25% 账号被封）
        ban_rate  >= 0.10  → 强制 MEDIUM（超过 10% 账号被封）
        warn_rate >= 0.30  → 强制 MEDIUM（超过 30% 账号被警告）

压力等级（阈值已调低以适应小规模仿真）：
    LOW    (0.0 ~ 0.05)  : 保持当前策略
    MEDIUM (0.05 ~ 0.20) : ConcernTroll 比例提升，降低 Agitator；触发 LLM 定期反思
    HIGH   (> 0.20)      : 策略切换 + 规避提示词 + 集群缩减 50% + LLM 定期反思
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class PressureLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AdaptiveController:
    """
    自适应控制器：根据平台审核压力动态调整攻击策略。

    核心机制参考 MultiAgent4Collusion update_reflection_memory(ban=True)：
        - 被封禁水军账号列表 → ban_message（SharedMemory）
        → 这里改为直接查 DB 获得封禁率，无需显式传递消息
        - 全局反思通过类变量 _shared_reflection 共享（对应 SharedMemory.shared_reflections）

    接口说明：
        update(db_conn)                 每步攻击前调用，返回当前压力等级
        get_effective_role_distribution 根据压力返回调整后的角色比例
        get_effective_cluster_size      HIGH 压力时返回 50% 集群规模
        should_switch_to_dispersed      HIGH 压力 + SWARM 模式时建议切换
        get_evasion_patch               HIGH 压力时返回提示词规避补丁
        maybe_generate_reflection       HIGH + 间隔步数时调用 LLM 更新反思
    """

    # 类变量：全局共享反思（参考 MultiAgent4Collusion SharedMemory.shared_reflections）
    # 所有 AdaptiveController 实例共享，反映集群级别的经验积累
    _shared_reflection: str = ""

    def __init__(self, config, model_selector=None):
        """
        Args:
            config        : AdaptiveConfig 实例（来自 MaliciousBotConfig.adaptive）
            model_selector: MultiModelSelector 实例，供 LLM 反思调用使用（可为 None）
        """
        self.config = config
        self.model_selector = model_selector
        self.current_pressure = PressureLevel.LOW
        self._last_checked_comment_id: int = 0
        self._last_checked_attack_id: int = 0
        self._step_counter: int = 0
        self._last_pressure_score: float = 0.0
        self._last_moderation_stats: Dict[str, int] = {}

    def update(self, db_conn) -> PressureLevel:
        """
        查询数据库，计算并更新当前压力等级。
        应在每步攻击执行前调用。

        Args:
            db_conn: 数据库连接（ServiceConnection 或 sqlite3.Connection）

        Returns:
            当前压力等级（PressureLevel 枚举）
        """
        if not self.config.enabled:
            return PressureLevel.LOW

        try:
            self._step_counter += 1
            stats = self._query_pressure_stats(db_conn)
            self._last_moderation_stats = stats
            pressure_score = self._compute_pressure_score(stats)
            self._last_pressure_score = pressure_score

            if pressure_score >= self.config.high_pressure_threshold:
                new_level = PressureLevel.HIGH
            elif pressure_score >= self.config.low_pressure_threshold:
                new_level = PressureLevel.MEDIUM
            else:
                new_level = PressureLevel.LOW

            # 绝对触发条件：各信号比例超过阈值时强制提升压力等级，
            # 防止小样本或信号缺失导致公式分值无法越过阈值。
            # 注意：水军机器人直接写入数据库，绕过审核 API，
            # warned_bots/banned_bots 通常为 0，故帖子审核命中率需独立触发。
            total_bots = max(stats.get("total_bot_users", 0), 1)
            post_mod_rate = stats.get("post_moderated_bots", 0) / total_bots
            ban_rate  = stats.get("banned_bots", 0) / total_bots
            warn_rate = stats.get("warned_bots", 0) / total_bots

            if ban_rate >= 0.25 or post_mod_rate >= 0.80:
                # 超过 25% 封号，或 超过 80% 的 bot 评论所在帖子被审核 → HIGH
                if new_level != PressureLevel.HIGH:
                    logger.info(
                        f"[AdaptiveController] Absolute trigger → forced HIGH "
                        f"(ban_rate={ban_rate:.0%}, post_mod_rate={post_mod_rate:.0%})"
                    )
                    new_level = PressureLevel.HIGH
            elif ban_rate >= 0.10 or warn_rate >= 0.30 or post_mod_rate >= 0.40:
                # 超过 10% 封号，或 30% 警告，或 40% 帖子被审核 → MEDIUM
                if new_level == PressureLevel.LOW:
                    logger.info(
                        f"[AdaptiveController] Absolute trigger → forced MEDIUM "
                        f"(ban_rate={ban_rate:.0%}, warn_rate={warn_rate:.0%}, post_mod_rate={post_mod_rate:.0%})"
                    )
                    new_level = PressureLevel.MEDIUM

            if new_level != self.current_pressure:
                logger.info(
                    f"[AdaptiveController] Pressure level changed: "
                    f"{self.current_pressure.value} → {new_level.value} "
                    f"(score={pressure_score:.2f}, stats={stats})"
                )
            else:
                logger.debug(
                    f"[AdaptiveController] step={self._step_counter} "
                    f"pressure={new_level.value}({pressure_score:.2f}) "
                    f"post_moderated={stats.get('post_moderated_bots', 0)}/{stats.get('total_bot_users', 0)} "
                    f"warned={stats.get('warned_bots', 0)}/{stats.get('total_bot_users', 0)} "
                    f"banned={stats.get('banned_bots', 0)}/{stats.get('total_bot_users', 0)}"
                )

            self.current_pressure = new_level
            return self.current_pressure

        except Exception as e:
            logger.warning(f"[AdaptiveController] Failed to compute pressure, keeping {self.current_pressure.value}: {e}")
            return self.current_pressure

    def _query_pressure_stats(self, db_conn) -> Dict[str, int]:
        """
        查询审核压力统计数据。

        三路信号数据源：
            信号 1（主）: posts.status / posts.moderation_action — 由 moderation/service.py 写入
                查询路径：malicious_comments → comments → posts（仅成功发布的评论）

            信号 2（早期）+ 信号 3（滞后）:
                使用 users.background_labels = {"is_malicious_bot": true} 标记所有水军账号
                （含被拦截、从未成功发布评论的账号）。
                - warned_bots: comment_violation_count > 0 OR user_actions.moderation_warning 存在
                - banned_bots: users.status = 'banned'
                查询路径：users JOIN user_actions（全量覆盖，无 malicious_comments 依赖）

        total_bot_users 使用 background_labels 标记的全量水军数作为统一分母，
        确保被拦截账号不从分母消失。

        Returns:
            {
                "total_bot_users": int,        # 全部水军用户数（含被拦截的）
                "post_moderated_bots": int,    # 信号1：评论所在帖子被审核的bot数
                "warned_bots": int,            # 信号2：评论被拦截过的bot数
                "banned_bots": int,            # 信号3：被封号的bot数
            }
        """
        stats = {
            "total_bot_users": 0,
            "post_moderated_bots": 0,
            "warned_bots": 0,
            "banned_bots": 0,
        }
        try:
            cursor = db_conn.cursor()

            # ── 信号 1：帖子被审核的水军数 ────────────────────────────────────────
            # 只有成功插入的评论才能关联到帖子，这符合语义：
            # 只有实际发出的评论才会影响帖子热度，进而触发帖子审核。
            cursor.execute(
                """
                SELECT
                    COUNT(DISTINCT CASE
                        WHEN p.status = 'taken_down'
                          OR p.moderation_action IS NOT NULL
                        THEN c.author_id
                    END) AS post_moderated_bots
                FROM malicious_comments mc
                JOIN comments c ON mc.comment_id = c.comment_id
                JOIN posts p    ON c.post_id = p.post_id
                """
            )
            row = cursor.fetchone()
            if row:
                stats["post_moderated_bots"] = int(row[0] or 0)

            # ── 信号 2 + 3 + 总量：基于 background_labels 标记的全量水军查询 ────
            # background_labels = '{"is_malicious_bot":true}' 在 bot 用户创建时写入，
            # 覆盖成功发帖和被完全拦截的两类账号，解决 malicious_comments JOIN 盲区。
            # warned_bots：violation_count > 0（字段写入）OR moderation_warning（user_actions 写入）
            # banned_bots：users.status = 'banned'
            cursor.execute(
                """
                SELECT
                    COUNT(DISTINCT u.user_id) AS total_bot_users,
                    COUNT(DISTINCT CASE
                        WHEN u.comment_violation_count > 0
                          OR ua.user_id IS NOT NULL
                        THEN u.user_id
                    END) AS warned_bots,
                    COUNT(DISTINCT CASE
                        WHEN u.status = 'banned' THEN u.user_id
                    END) AS banned_bots
                FROM users u
                LEFT JOIN (
                    SELECT DISTINCT user_id
                    FROM user_actions
                    WHERE action_type = 'moderation_warning'
                ) ua ON ua.user_id = u.user_id
                WHERE json_extract(u.background_labels, '$.is_malicious_bot') = 1
                """
            )
            row = cursor.fetchone()
            if row:
                stats["total_bot_users"] = int(row[0] or 0)
                stats["warned_bots"]     = int(row[1] or 0)
                stats["banned_bots"]     = int(row[2] or 0)

        except Exception as e:
            logger.warning(f"[AdaptiveController] DB query error: {e}")

        return stats

    def _compute_pressure_score(self, stats: Dict[str, int]) -> float:
        """
        计算审核压力系数（0.0 ~ 1.0）。

        公式：post_pressure × 0.30 + warn_pressure × 0.25 + ban_pressure × 0.45

            post_pressure  = moderated_posts / max(total_attacked_posts, 1)
                → 帖子被下架/标记；无论 moderation_enabled 状态均有效，但小模拟中
                  bots 主要攻击 fake news 帖，审核对这类帖命中率低，因此权重降低。

            warn_pressure  = warned_bots / max(total_bot_users, 1)  [全量累计]
                → comment_violation_count > 0 的账号比例；首次评论被拦截即感知。

            ban_pressure   = banned_bots / max(total_bot_users, 1)  [全量累计]
                → users.status='banned' 的账号比例；最确定的信号，权重最高。
                → 使用全量历史统计，已封号账号的压力贡献不会随时间消失。

        额外绝对阈值（独立于公式分值，防止权重平均稀释导致无法触发）：
            banned_rate >= 0.10  → 至少 MEDIUM（覆盖封号 < 10 但达到比例阈值的场景）
            banned_rate >= 0.25  → 至少 HIGH
            warn_rate   >= 0.30  → 至少 MEDIUM
        这些阈值由 update() 在公式分值基础上叠加判断，不在此方法内处理。
        """
        total = max(stats["total_bot_users"], 1)
        post_pressure = stats["post_moderated_bots"] / total
        warn_pressure = stats["warned_bots"] / total
        ban_pressure  = stats["banned_bots"] / total
        return post_pressure * 0.30 + warn_pressure * 0.25 + ban_pressure * 0.45

    def get_effective_role_distribution(self, base_dist: Dict[str, float]) -> Dict[str, float]:
        """
        根据压力等级返回调整后的角色比例。

        LOW    : 原样返回（不调整）
        MEDIUM : ConcernTroll 提升（伪装度高，最难被审核识别）
        HIGH   : 极端偏向 ConcernTroll，大幅降低 Agitator（最容易被识别的角色）
        """
        if self.current_pressure == PressureLevel.LOW:
            return dict(base_dist)

        if self.current_pressure == PressureLevel.MEDIUM:
            # ConcernTroll 提升至约 50%，Agitator 降至约 20%
            agitator = max(0.05, base_dist.get("agitator", 0.40) - 0.20)
            concern = min(0.75, base_dist.get("concern_troll", 0.35) + 0.15)
            spammer = max(0.05, round(1.0 - agitator - concern, 4))
            return {"agitator": agitator, "concern_troll": concern, "spammer": spammer}

        # HIGH：强规避模式，ConcernTroll 主导
        return {"agitator": 0.15, "concern_troll": 0.65, "spammer": 0.20}

    def get_effective_cluster_size(self, base_size: int) -> int:
        """
        HIGH 压力时降低攻击频率（集群规模减半），其他等级返回原值。
        """
        if self.current_pressure == PressureLevel.HIGH:
            return max(1, int(base_size * 0.5))
        return base_size

    def should_switch_to_dispersed(self) -> bool:
        """
        HIGH 压力时建议将 SWARM 模式切换为 DISPERSED，
        降低目标集中度以减少协调痕迹。
        """
        return self.current_pressure == PressureLevel.HIGH

    def get_evasion_patch(self) -> str:
        """
        HIGH 压力时返回追加到提示词末尾的规避指令字符串。
        LOW / MEDIUM 时返回空字符串（不改变提示词）。

        若存在历史反思（LLM 生成），会一并追加以指导内容生成。
        """
        if self.current_pressure != PressureLevel.HIGH:
            return ""

        base_patch = (
            "EVASION GUIDANCE (mandatory — platform moderation is active):\n"
            "- Avoid explicit political labels, incitement phrases, or slurs that trigger keyword filters\n"
            "- Replace direct accusations with rhetorical questions ('Has anyone considered why...')\n"
            "- Sound like a concerned, thoughtful citizen expressing skepticism — not a provocateur\n"
            "- No ALL CAPS, excessive exclamation marks, or hashtag spam\n"
            "- Keep tone conversational and measured; express doubt through 'I'm just wondering' framing"
        )

        if AdaptiveController._shared_reflection:
            return f"{base_patch}\n\nLearned from previous rounds:\n{AdaptiveController._shared_reflection}"
        return base_patch

    async def maybe_generate_reflection(
        self,
        attack_results: Dict[str, Any],
        moderation_stats: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        HIGH 压力且到达反思间隔时，调用 LLM 生成策略反思并更新类变量 _shared_reflection。

        参考 MultiAgent4Collusion update_reflection_memory(ban=True)：
            - 读取被封禁代理的封禁信息（这里对应审核压力统计）
            - 调用 LLM 分析并更新 reflections（这里对应 _shared_reflection 类变量）
            - 下一轮攻击通过 get_evasion_patch() 将反思注入提示词上下文

        Args:
            attack_results   : 本轮攻击结果摘要（如 {"total_comments": int, ...}）
            moderation_stats : 覆盖使用的压力统计数据，默认使用最近一次 update() 的结果
        """
        if not self.config.enabled or not self.config.reflection_enabled:
            return
        # MEDIUM 或 HIGH 均可触发反思（不再仅限于 HIGH）
        if self.current_pressure == PressureLevel.LOW:
            return
        # 压力等级越高，反思越频繁：HIGH 每 1 步，MEDIUM 每 2 步
        interval = 1 if self.current_pressure == PressureLevel.HIGH else 2
        if self._step_counter % interval != 0:
            return
        if not self.model_selector:
            return

        stats = moderation_stats or self._last_moderation_stats
        post_moderated = stats.get("post_moderated_bots", 0)
        warned = stats.get("warned_bots", 0)
        banned = stats.get("banned_bots", 0)
        total_bots = max(stats.get("total_bot_users", 1), 1)
        pressure_pct = self._last_pressure_score
        total_comments = attack_results.get("total_comments", 0) if attack_results else 0

        prompt = (
            "You are an advisor to a coordinated network that posts skeptical content online.\n"
            f"Of {total_bots} active bot accounts: {post_moderated} had their commented posts taken down or labeled, "
            f"{warned} had at least one comment deleted, "
            f"and {banned} were fully banned. "
            f"Overall pressure score: {pressure_pct:.0%}.\n"
            f"Total comments posted this round: {total_comments}.\n\n"
            f"Previous strategy notes: {AdaptiveController._shared_reflection or 'None yet.'}\n\n"
            "Analyze why accounts were flagged and suggest 2-3 specific content style adjustments "
            "to reduce detection while maintaining the skeptical narrative. "
            "Focus only on writing style and phrasing — not on attack volume or timing.\n"
            "Respond in 2-3 concise bullet points."
        )

        try:
            def _sync_call():
                client, model_name = self.model_selector.create_openai_client(role="malicious")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                )
                return response.choices[0].message.content.strip()

            reflection = await asyncio.to_thread(_sync_call)
            if reflection:
                AdaptiveController._shared_reflection = reflection
                logger.info(
                    f"[AdaptiveController] Shared reflection updated "
                    f"(step={self._step_counter}): {reflection[:120]}..."
                )
        except Exception as e:
            logger.warning(f"[AdaptiveController] LLM reflection failed: {e}")
