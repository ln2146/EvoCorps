"""
CoordinationStrategy - 恶意水军协同策略系统

定义三种可选的攻击协同模式：
    SWARM     (蜂群式) : 全部 bot 集中攻击同一目标 + cross-like（默认，与现有行为等价）
    DISPERSED (游离式) : bot 随机分散到多条帖子，低组织度攻击
    CHAIN     (链式)   : 三层结构（LeaderBot → AmplifierBot → CommentFloodBot）

已实现：
    - CoordinationMode 枚举
    - SwarmStrategy（复用现有 coordinate_attack 逻辑，叠加角色分配）
    - DispersedStrategy
    - AttackBlackboard + ChainStrategy（链式传播，参考 MultiAgent4Collusion）
"""

import asyncio
import hashlib
import json
import logging
import random
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional

from .bot_role_overlay import assign_bot_roles, get_role_overlay, BotRole

logger = logging.getLogger(__name__)


# ─── 策略枚举 ──────────────────────────────────────────────────────────────────

class CoordinationMode(Enum):
    """
    攻击协同模式。

    在 MaliciousBotConfig.coordination_mode 中设置：
        CoordinationMode.SWARM     - 蜂群式（默认）
        CoordinationMode.DISPERSED - 游离式
        CoordinationMode.CHAIN     - 链式传播
    """
    DISPERSED = "dispersed"  # 游离式：低组织度，随机分散到多条帖子
    SWARM     = "swarm"      # 蜂群式：集中火力攻击单一目标（当前默认行为）
    CHAIN     = "chain"      # 链式传播：三层结构，参考 MultiAgent4Collusion


# ─── 蜂群式策略 ────────────────────────────────────────────────────────────────

class SwarmStrategy:
    """
    蜂群式攻击策略（Swarm）。

    行为特征：
    - 全部 cluster_size 个 bot 集中攻击同一目标帖子
    - 通过 assign_bot_roles() 注入三种战术角色（Agitator / ConcernTroll / Spammer）
    - 执行 cross-like，操控推荐算法的热度评分
    - 与现有 SimpleMaliciousCluster.coordinate_attack() 完全等价，是其规范化封装

    这是 Step 2 的实现，已完全覆盖现有功能并新增角色分化能力。
    """

    async def execute(
        self,
        target_post_id: str,
        target_content: str,
        cluster_size: int,
        bot_cluster,
        role_distribution: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        执行蜂群式攻击。

        Args:
            target_post_id   : 目标帖子 ID
            target_content   : 目标帖子内容（用于生成评论提示词）
            cluster_size     : 本轮参与攻击的 bot 数量
            bot_cluster      : SimpleMaliciousCluster 实例
            role_distribution: 角色分布比例字典，如 {"agitator": 0.4, ...}

        Returns:
            List[Dict]: 每个 bot 生成的评论结果，结构同 coordinate_attack() 返回值。
            每条记录新增 "bot_role" 和 "disguise_level" 字段（来自 RoleOverlay）。
        """
        # 生成角色分配列表
        # 用 dummy list 生成 cluster_size 个角色覆盖配置（无需真实 persona）
        dummy_personas = [None] * cluster_size
        paired = assign_bot_roles(dummy_personas, role_distribution)
        role_overlays = [overlay for _, overlay in paired]

        # 统计角色分布，写入日志
        role_counts = {}
        for overlay in role_overlays:
            role_name = overlay.role.value
            role_counts[role_name] = role_counts.get(role_name, 0) + 1
        logger.info(
            f"[SwarmStrategy] Attacking post {target_post_id} | "
            f"cluster_size={cluster_size} | roles={role_counts}"
        )

        # 调用 bot_cluster.coordinate_attack（已支持 role_overlays 参数）
        responses = await bot_cluster.coordinate_attack(
            target_post_id=target_post_id,
            target_content=target_content,
            attack_size=cluster_size,
            role_overlays=role_overlays,
        )

        return responses


# ─── 游离式策略（Step 3） ──────────────────────────────────────────────────────

# 游离式默认角色分布：Agitator 为主，无 ConcernTroll（低组织度场景不需要精密伪装）
_DISPERSED_DEFAULT_ROLE_DIST: Dict[str, float] = {
    "agitator": 0.60,
    "concern_troll": 0.00,
    "spammer": 0.40,
}

# 每条帖子分配的 bot 数量范围
_DISPERSED_MIN_BOTS_PER_POST = 3
_DISPERSED_MAX_BOTS_PER_POST = 5


class DispersedStrategy:
    """
    游离式攻击策略（Dispersed）。

    行为特征：
    - 无中心协调，bot 随机分散到多条帖子（模拟低组织度的自发性舆论攻击）
    - 每条帖子最多分配 3~5 个 bot，避免集中轰炸被审核系统识别
    - 不执行 cross-like（无协调互动）
    - 角色以 Agitator 为主（60%），Spammer 为辅（40%）
    - 若 post_pool 过小（仅 1 条），则等同于 swarm 但不执行 cross-like

    与 MultiAgent4Collusion 对应：类似 bad_type="bad" 的默认行为，
    agents 各自独立行动，没有共享任务黑板。
    """

    async def execute(
        self,
        post_pool: List[Dict[str, Any]],
        cluster_size: int,
        bot_cluster,
        role_distribution: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        执行游离式攻击：将 cluster_size 个 bot 随机分散到 post_pool 中的多条帖子。

        Args:
            post_pool        : 候选帖子列表，每条格式为 {"post_id": str, "content": str, ...}
            cluster_size     : 本轮参与攻击的 bot 总数
            bot_cluster      : SimpleMaliciousCluster 实例
            role_distribution: 角色比例，None 则使用游离式默认值（agitator 60% / spammer 40%）

        Returns:
            所有子组攻击结果的合并列表，格式同 SwarmStrategy 返回值。
            每条记录额外包含 "target_post_id" 字段，标明该评论属于哪条帖子。
        """
        if not post_pool:
            logger.warning("[DispersedStrategy] post_pool is empty, aborting.")
            return []

        dist = role_distribution if role_distribution is not None else _DISPERSED_DEFAULT_ROLE_DIST

        # ── 将 cluster_size 个 bot 分组，随机分配给 post_pool 中的帖子 ──────────
        assignments = self._assign_bots_to_posts(post_pool, cluster_size)

        # 统计日志
        logger.info(
            f"[DispersedStrategy] cluster_size={cluster_size} | "
            f"posts_targeted={len(assignments)} / {len(post_pool)} | "
            f"groups={[(p['post_id'], n) for p, n in assignments]}"
        )

        # ── 并发执行各子组攻击（无协调，真正游离式） ──────────────────────────
        tasks = []
        for target_post, group_size in assignments:
            tasks.append(
                self._attack_single_post(
                    target_post=target_post,
                    group_size=group_size,
                    bot_cluster=bot_cluster,
                    role_distribution=dist,
                )
            )

        group_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果，过滤异常
        all_results: List[Dict[str, Any]] = []
        for i, result in enumerate(group_results):
            if isinstance(result, Exception):
                target_id = assignments[i][0].get("post_id", "?")
                logger.warning(
                    f"[DispersedStrategy] Group targeting post {target_id} failed: {result}"
                )
            else:
                all_results.extend(result)

        logger.info(
            f"[DispersedStrategy] Done | "
            f"total_comments={len(all_results)} across {len(assignments)} posts"
        )
        return all_results

    # ── 私有方法 ────────────────────────────────────────────────────────────────

    def _assign_bots_to_posts(
        self,
        post_pool: List[Dict[str, Any]],
        cluster_size: int,
    ) -> List[tuple]:
        """
        将 cluster_size 个 bot 随机分配到 post_pool 的多条帖子中。

        策略：
        1. 随机打乱 post_pool，逐条帖子随机分配 3~5 个 bot。
        2. 分配至 cluster_size 耗尽为止；若 post_pool 不够分，剩余 bot 追加到随机帖子上
           （但仍限制每条帖子最多 _DISPERSED_MAX_BOTS_PER_POST 个）。
        3. 若 post_pool 只有 1 条帖子，所有 bot 攻击该帖（退化为无 cross-like 的 swarm）。

        Returns:
            [(post_dict, bot_count), ...] 列表，仅包含 bot_count > 0 的帖子。
        """
        if len(post_pool) == 1:
            return [(post_pool[0], cluster_size)]

        shuffled_posts = list(post_pool)
        random.shuffle(shuffled_posts)

        assignments: List[tuple] = []
        remaining = cluster_size

        for post in shuffled_posts:
            if remaining <= 0:
                break
            # 每组随机分配 3~5 个 bot，不超过剩余数量
            group_size = random.randint(
                _DISPERSED_MIN_BOTS_PER_POST,
                _DISPERSED_MAX_BOTS_PER_POST,
            )
            group_size = min(group_size, remaining)
            assignments.append((post, group_size))
            remaining -= group_size

        # 如果还有剩余 bot（post_pool 全部遍历完仍有剩余），随机追加到已有目标
        if remaining > 0 and assignments:
            random.shuffle(assignments)
            for i in range(len(assignments)):
                post, count = assignments[i]
                can_add = _DISPERSED_MAX_BOTS_PER_POST - count
                if can_add <= 0:
                    continue
                add = min(can_add, remaining)
                assignments[i] = (post, count + add)
                remaining -= add
                if remaining <= 0:
                    break

        return assignments

    async def _attack_single_post(
        self,
        target_post: Dict[str, Any],
        group_size: int,
        bot_cluster,
        role_distribution: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        用 group_size 个 bot 攻击单条帖子，返回评论结果列表。
        不执行 cross-like（游离式的核心特征）。
        """
        post_id = target_post.get("post_id", "")
        content = target_post.get("content", "")

        # 分配角色（用 dummy personas 只为生成 role_overlays）
        dummy_personas = [None] * group_size
        paired = assign_bot_roles(dummy_personas, role_distribution)
        role_overlays = [overlay for _, overlay in paired]

        role_counts = {}
        for overlay in role_overlays:
            role_name = overlay.role.value
            role_counts[role_name] = role_counts.get(role_name, 0) + 1
        logger.debug(
            f"[DispersedStrategy] post={post_id} | group_size={group_size} | roles={role_counts}"
        )

        # 调用 coordinate_attack，传入 role_overlays；不调用 cross-like
        responses = await bot_cluster.coordinate_attack(
            target_post_id=post_id,
            target_content=content,
            attack_size=group_size,
            role_overlays=role_overlays,
        )

        # 为每条结果注入 target_post_id，方便上层聚合统计
        for r in responses:
            r["target_post_id"] = post_id

        return responses


# ─── 链式传播协调黑板 ──────────────────────────────────────────────────────────

class AttackBlackboard:
    """
    链式传播协调黑板（参考 MultiAgent4Collusion TaskBlackboard）。

    Leader Bot 创建攻击任务并写入黑板，Amplifier / CommentFlood Bot 从黑板读取
    leader_post_id 后并发执行各自的子任务。

    纯内存结构，asyncio.Lock 保护并发读写，不持久化到 SQLite，
    仅在单次 ChainStrategy.execute() 调用周期内有效。
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self.tasks: Dict[str, Dict] = {}

    async def create_chain_task(
        self,
        task_id: str,
        leader_post_id: str,
        leader_content: str,
        required_amplifiers: int,
        required_commenters: int,
    ) -> None:
        """Leader Bot 完成发帖后写入黑板，通知下层 Bot 可以开始行动。"""
        async with self._lock:
            self.tasks[task_id] = {
                "task_id": task_id,
                "leader_post_id": leader_post_id,
                "leader_content": leader_content,
                "required_amplifiers": required_amplifiers,
                "required_commenters": required_commenters,
                "amplifiers_done": 0,
                "commenters_done": 0,
            }

    async def get_task(self, task_id: str) -> Optional[Dict]:
        """读取任务信息（返回副本，避免外部修改）。"""
        async with self._lock:
            task = self.tasks.get(task_id)
            return dict(task) if task else None

    async def mark_amplifier_done(self, task_id: str) -> None:
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]["amplifiers_done"] += 1

    async def mark_commenter_done(self, task_id: str) -> None:
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]["commenters_done"] += 1


# ─── 链式传播策略 ──────────────────────────────────────────────────────────────

# Leader Bot 发帖时的提示词：伪装成权威意见领袖，散布对目标话题的质疑
_LEADER_POST_PROMPT = """ROLE: You are a highly-followed opinion influencer posting about a trending topic.
TACTICS:
- Write as if you have inside knowledge ("I've been following this for months...")
- Sound authoritative but plant subtle doubts about mainstream narratives
- Use first-person perspective; sound personal and genuine
- End with a question that invites followers to distrust official sources
CONSTRAINT: Under 50 words. Sound like a respected community voice, not a bot.

Topic context: "{target_content}"

Write your influencer post:"""

# Amplifier Bot 转发评论的提示词：为 Leader 的帖子添加情绪化转发注释
_AMPLIFIER_REPOST_PROMPT = """ROLE: You are reposting and amplifying an influencer's message you strongly agree with.
TACTICS:
- Express strong agreement and urgency ("This is EXACTLY what I've been saying!")
- Add one emotional sentence that reinforces the message
- Use CAPS for emphasis on key words
- Encourage others to share
CONSTRAINT: Under 25 words. High emotion, strong endorsement.

Original post context: "{leader_content}"

Write your repost comment:"""


class ChainStrategy:
    """
    链式传播攻击策略（Chain）。

    三层水军结构（参考 MultiAgent4Collusion TaskBlackboard + SharedMemory 机制）：

    Layer 1 — LeaderBot (ConcernTroll)
        - 从 cluster 中选出 chain_config.leader_bot_count 个 bot 作为大V水军
        - 在 users 表注入高 follower_count，伪造权威账号身份
        - 调用 LLM 生成「影响力帖子」内容并写入 posts 表
        - 将 leader_post_id 写入 AttackBlackboard，通知下层开始行动

    Layer 2 — AmplifierBot (Agitator)
        - 读取黑板获取 leader_post_id
        - 并发生成情绪化「转发评论」，在 leader_post 下评论
        - 同时 UPDATE posts SET num_shares += 1，模拟转发行为
        - 结果的 target_post_id = leader_post_id（由 _create_malicious_comments 路由）

    Layer 3 — CommentFloodBot (Spammer)
        - 读取黑板获取 leader_post_id
        - 并发生成大量短评论刷热度，污染 leader_post 的评论区
        - 结果同样携带 target_post_id = leader_post_id
        - cross-like 由 _create_malicious_comments 统一处理

    注意：ChainStrategy 需要 conn（SQLite 连接）用于写入 leader user 和 leader post。
    若 conn 为 None，将退化为 SwarmStrategy 行为并记录警告。
    """

    async def execute(
        self,
        target_post_id: str,
        target_content: str,
        cluster_size: int,
        bot_cluster,
        chain_config,
        conn=None,
        time_step: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        执行链式传播攻击。

        Args:
            target_post_id : 虚假新闻帖子 ID（Leader 据此生成相关内容）
            target_content : 虚假新闻帖子内容
            cluster_size   : 本轮总 bot 数量
            bot_cluster    : SimpleMaliciousCluster 实例
            chain_config   : ChainConfig 实例（含各层比例配置）
            conn           : SQLite 连接（用于写入 leader post / user）

        Returns:
            Amplifier + CommentFlood 两层 bot 的评论结果列表。
            每条结果携带 "target_post_id" = leader_post_id，
            由 _create_malicious_comments 负责写入数据库。
        """
        if conn is None:
            logger.warning(
                "[ChainStrategy] No DB connection provided; falling back to SwarmStrategy."
            )
            return await SwarmStrategy().execute(
                target_post_id=target_post_id,
                target_content=target_content,
                cluster_size=cluster_size,
                bot_cluster=bot_cluster,
                role_distribution={"agitator": 0.40, "concern_troll": 0.35, "spammer": 0.25},
            )

        # ── 计算各层 bot 数量 ───────────────────────────────────────────────────
        n_leaders = min(chain_config.leader_bot_count, cluster_size)
        remaining = cluster_size - n_leaders
        n_amplifiers = max(1, round(remaining * chain_config.amplifier_ratio))
        n_flood = max(1, remaining - n_amplifiers)

        logger.info(
            f"[ChainStrategy] cluster_size={cluster_size} | "
            f"leaders={n_leaders} | amplifiers={n_amplifiers} | flood={n_flood}"
        )

        # ── Step 1: LeaderBot 行动 ─────────────────────────────────────────────
        blackboard = AttackBlackboard()
        task_id = f"chain-{uuid.uuid4().hex[:8]}"

        leader_post_id, leader_content = await self._leader_action(
            target_content=target_content,
            n_leaders=n_leaders,
            chain_config=chain_config,
            bot_cluster=bot_cluster,
            conn=conn,
            task_id=task_id,
            blackboard=blackboard,
            n_amplifiers=n_amplifiers,
            n_flood=n_flood,
            time_step=time_step,
        )

        if not leader_post_id:
            # Leader 行动失败，退化为蜂群式
            logger.warning("[ChainStrategy] Leader action failed; falling back to SwarmStrategy.")
            return await SwarmStrategy().execute(
                target_post_id=target_post_id,
                target_content=target_content,
                cluster_size=cluster_size,
                bot_cluster=bot_cluster,
                role_distribution={"agitator": 0.40, "concern_troll": 0.35, "spammer": 0.25},
            )

        # ── Step 2 & 3: AmplifierBot + CommentFloodBot 并发行动 ────────────────
        amplifier_task = asyncio.create_task(
            self._amplifier_action(
                leader_post_id=leader_post_id,
                leader_content=leader_content,
                n_amplifiers=n_amplifiers,
                bot_cluster=bot_cluster,
                conn=conn,
                task_id=task_id,
                blackboard=blackboard,
            )
        )
        flood_task = asyncio.create_task(
            self._flood_action(
                leader_post_id=leader_post_id,
                leader_content=leader_content,
                n_flood=n_flood,
                bot_cluster=bot_cluster,
                task_id=task_id,
                blackboard=blackboard,
            )
        )

        amplifier_results, flood_results = await asyncio.gather(
            amplifier_task, flood_task, return_exceptions=True
        )

        # 合并结果，过滤异常
        combined: List[Dict[str, Any]] = []
        for layer_name, results in [("amplifier", amplifier_results), ("flood", flood_results)]:
            if isinstance(results, Exception):
                logger.warning(f"[ChainStrategy] {layer_name} layer failed: {results}")
            elif isinstance(results, list):
                combined.extend(results)

        logger.info(
            f"[ChainStrategy] Done | leader_post={leader_post_id} | "
            f"total_comments={len(combined)}"
        )
        return combined

    # ── 私有方法：Leader 行动 ─────────────────────────────────────────────────

    async def _leader_action(
        self,
        target_content: str,
        n_leaders: int,
        chain_config,
        bot_cluster,
        conn,
        task_id: str,
        blackboard: AttackBlackboard,
        n_amplifiers: int,
        n_flood: int,
        time_step: Optional[int] = None,
    ):
        """
        Leader Bot 行动：
        1. 选取 n_leaders 个 persona，赋予 ConcernTroll 角色
        2. 生成「影响力帖子」内容（特定提示词，不同于普通评论）
        3. 在 users 表注入大V账号（高 follower_count）
        4. 将帖子写入 posts 表，获得 leader_post_id
        5. 写入 AttackBlackboard，通知下层开始行动

        Returns:
            (leader_post_id, leader_content) 元组，失败时返回 (None, "")
        """
        try:
            # 生成 Leader 帖子内容（使用专属提示词，不调用 coordinate_attack）
            leader_content = await asyncio.to_thread(
                self._generate_leader_post_content, bot_cluster, target_content
            )
            if not leader_content:
                logger.warning(
                    "⚠️ [ChainStrategy] Leader content generation returned empty; "
                    "entire _leader_action aborted, caller will fall back to SwarmStrategy."
                )
                return None, ""

            # 创建大V账号并写入帖子
            leader_post_id = await asyncio.to_thread(
                self._insert_leader_post_to_db,
                leader_content,
                chain_config,
                conn,
                time_step,
            )
            if not leader_post_id:
                logger.warning(
                    "⚠️ [ChainStrategy] Leader post DB insertion failed (returned None); "
                    "entire _leader_action aborted, caller will fall back to SwarmStrategy."
                )
                return None, ""

            # 写入黑板
            await blackboard.create_chain_task(
                task_id=task_id,
                leader_post_id=leader_post_id,
                leader_content=leader_content,
                required_amplifiers=n_amplifiers,
                required_commenters=n_flood,
            )

            logger.info(
                f"[ChainStrategy] Leader posted: post_id={leader_post_id} | "
                f"content={leader_content[:60]}..."
            )
            print(
                f"[Chain-Leader] Created influencer post {leader_post_id}: "
                f"{leader_content[:80]}"
            )
            return leader_post_id, leader_content

        except Exception as e:
            logger.error(f"[ChainStrategy] _leader_action failed: {e}")
            return None, ""

    def _generate_leader_post_content(self, bot_cluster, target_content: str) -> str:
        """
        同步 LLM 调用，生成 Leader Bot 的「影响力帖子」内容。
        使用专为 Leader 设计的提示词（ConcernTroll 风格，伪装成意见领袖）。
        运行在 asyncio.to_thread 中，不阻塞事件循环。
        """
        import threading

        prompt = _LEADER_POST_PROMPT.format(target_content=target_content[:200])
        result = [None]
        error = [None]

        def call_llm():
            try:
                client, model_name = bot_cluster.model_selector.create_langchain_client()
                response = client.invoke(prompt)
                content = response.content.strip() if response and hasattr(response, "content") else ""
                # 截断到合理长度
                words = content.split()[:50]
                content = " ".join(words).replace('"', "").replace("*", "")
                result[0] = content
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=call_llm)
        thread.daemon = True
        thread.start()
        thread.join(timeout=15.0)

        if thread.is_alive():
            logger.warning(
                "⚠️ [ChainStrategy] Leader LLM call timed out (15s); "
                "falling back to hardcoded template post."
            )
            return (
                "I've been researching this topic for weeks and what I'm finding is deeply "
                "concerning. Has anyone else noticed how one-sided the coverage has been? "
                "Something doesn't add up here."
            )

        if error[0]:
            logger.warning(
                f"⚠️ [ChainStrategy] Leader LLM call raised exception: {error[0]}; "
                f"falling back to hardcoded template post."
            )
            return (
                "I've been researching this topic for weeks and what I'm finding is deeply "
                "concerning. Has anyone else noticed how one-sided the coverage has been? "
                "Something doesn't add up here."
            )

        content = result[0] or ""
        if not content or len(content.strip()) < 10:
            logger.warning(
                "⚠️ [ChainStrategy] Leader LLM returned empty/too-short content; "
                "falling back to hardcoded template post."
            )
            return (
                "I'm genuinely worried about what I'm seeing here. "
                "The mainstream story doesn't match what independent researchers are saying. "
                "Why isn't anyone asking the hard questions?"
            )
        return content

    def _insert_leader_post_to_db(self, leader_content: str, chain_config, conn, time_step: Optional[int] = None) -> Optional[str]:
        """
        同步数据库写入：创建大V账号 + 写入 leader 帖子。
        运行在 asyncio.to_thread 中。

        Returns:
            leader_post_id（成功）或 None（失败）
        """
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # 生成大V账号 ID（与 _create_malicious_comments 中的用户 ID 格式一致）
            seed = f"leader_{uuid.uuid4().hex[:8]}"
            hash_obj = hashlib.md5(seed.encode())
            user_suffix = hash_obj.hexdigest()[:6]
            leader_user_id = f"user-leader-{user_suffix}"

            # 伪造大V粉丝数
            followers_count = random.randint(
                chain_config.leader_followers_count_min,
                chain_config.leader_followers_count_max,
            )

            # 创建大V账号（若不存在）
            cursor.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (leader_user_id,)
            )
            if not cursor.fetchone():
                leader_persona = {
                    "name": f"Influencer{user_suffix}",
                    "type": "negative",
                    "profession": "Social Media Influencer",
                    "age_range": "28-45",
                    "personality_traits": ["Authoritative", "Persuasive", "Influential"],
                    "interests": ["Politics", "Social Issues", "Truth-Seeking"],
                    "is_leader_bot": True,
                }
                cursor.execute(
                    """
                    INSERT INTO users (user_id, persona, creation_time, follower_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (leader_user_id, json.dumps(leader_persona), now, followers_count),
                )
            else:
                # 更新已有账号的粉丝数
                cursor.execute(
                    "UPDATE users SET follower_count = ? WHERE user_id = ?",
                    (followers_count, leader_user_id),
                )

            # 生成 leader_post_id
            leader_post_id = f"chain-post-{uuid.uuid4().hex[:8]}"

            # 写入 posts 表（使用 INSERT OR IGNORE 避免主键冲突）
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO posts
                        (post_id, content, author_id, created_at,
                         num_likes, num_shares, num_comments, is_news, status,
                         agent_type, is_agent_response)
                    VALUES (?, ?, ?, ?, 0, 0, 0, 0, 'active', 'malicious', 1)
                    """,
                    (leader_post_id, leader_content, leader_user_id, now),
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ [ChainStrategy] Full-schema posts INSERT failed ({e}); "
                    f"falling back to minimal schema (post_id, content, author_id, created_at only)."
                )
                cursor.execute(
                    "INSERT OR IGNORE INTO posts (post_id, content, author_id, created_at) VALUES (?, ?, ?, ?)",
                    (leader_post_id, leader_content, leader_user_id, now),
                )

            # 写入 post_timesteps 表，与主流程 agent_user.py 保持一致（INSERT OR REPLACE + int）
            if time_step is not None:
                try:
                    cursor.execute(
                        "INSERT OR REPLACE INTO post_timesteps (post_id, time_step) VALUES (?, ?)",
                        (leader_post_id, int(time_step)),
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [ChainStrategy] post_timesteps INSERT failed: {e}")

            conn.commit()

            logger.debug(
                f"[ChainStrategy] Leader user={leader_user_id} "
                f"(followers={followers_count}), post={leader_post_id}"
            )
            return leader_post_id

        except Exception as e:
            logger.error(f"[ChainStrategy] _insert_leader_post_to_db failed: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return None

    # ── 私有方法：Amplifier 行动 ──────────────────────────────────────────────

    async def _amplifier_action(
        self,
        leader_post_id: str,
        leader_content: str,
        n_amplifiers: int,
        bot_cluster,
        conn,
        task_id: str,
        blackboard: AttackBlackboard,
    ) -> List[Dict[str, Any]]:
        """
        AmplifierBot 行动：
        1. 并发生成 n_amplifiers 个 Agitator 风格的转发评论（目标为 leader_post）
        2. 每个 amplifier 在数据库中执行 num_shares +1（模拟转发）
        3. 返回结果携带 target_post_id = leader_post_id

        使用专属「转发评论」提示词（_AMPLIFIER_REPOST_PROMPT），让内容更像真实转发。
        """
        # 为 Amplifier 分配 Agitator 角色（转发者用激进风格强化 Leader 的消息）
        agitator_overlay = get_role_overlay(BotRole.AGITATOR)

        # 使用转发专属提示词覆盖 Agitator 的默认提示词
        amplifier_prompt = _AMPLIFIER_REPOST_PROMPT.format(
            leader_content=leader_content[:150]
        )
        from dataclasses import replace as dc_replace
        amplifier_overlay = dc_replace(agitator_overlay, prompt_override=amplifier_prompt)

        overlays = [amplifier_overlay] * n_amplifiers

        # 并发调用 coordinate_attack（传入 role_overlays）
        responses = await bot_cluster.coordinate_attack(
            target_post_id=leader_post_id,
            target_content=leader_content,
            attack_size=n_amplifiers,
            role_overlays=overlays,
        )

        # 更新 leader post 的转发数（模拟 AmplifierBot 转发行为）
        await asyncio.to_thread(
            self._increment_shares, conn, leader_post_id, len(responses)
        )

        # 为每条结果注入 target_post_id 和 layer 标记
        for r in responses:
            r["target_post_id"] = leader_post_id
            r["chain_layer"] = "amplifier"

        # 更新黑板进度
        for _ in responses:
            await blackboard.mark_amplifier_done(task_id)

        logger.info(
            f"[ChainStrategy] AmplifierBot: {len(responses)} repost-comments on {leader_post_id}"
        )
        return responses

    def _increment_shares(self, conn, post_id: str, count: int) -> None:
        """同步：将 leader post 的 num_shares 增加 count（模拟转发）。"""
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE posts SET num_shares = COALESCE(num_shares, 0) + ? WHERE post_id = ?",
                (count, post_id),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"[ChainStrategy] _increment_shares failed: {e}")

    # ── 私有方法：CommentFlood 行动 ──────────────────────────────────────────

    async def _flood_action(
        self,
        leader_post_id: str,
        leader_content: str,
        n_flood: int,
        bot_cluster,
        task_id: str,
        blackboard: AttackBlackboard,
    ) -> List[Dict[str, Any]]:
        """
        CommentFloodBot 行动：
        1. 并发生成 n_flood 个 Spammer 风格的短评论（目标为 leader_post）
        2. 返回结果携带 target_post_id = leader_post_id
        3. cross-like 由上层 _create_malicious_comments 统一处理
        """
        # 为所有 flood bots 分配 Spammer 角色
        spammer_overlay = get_role_overlay(BotRole.SPAMMER)
        overlays = [spammer_overlay] * n_flood

        responses = await bot_cluster.coordinate_attack(
            target_post_id=leader_post_id,
            target_content=leader_content,
            attack_size=n_flood,
            role_overlays=overlays,
        )

        # 注入 target_post_id 和 layer 标记
        for r in responses:
            r["target_post_id"] = leader_post_id
            r["chain_layer"] = "flood"

        # 更新黑板进度
        for _ in responses:
            await blackboard.mark_commenter_done(task_id)

        logger.info(
            f"[ChainStrategy] CommentFloodBot: {len(responses)} flood-comments on {leader_post_id}"
        )
        return responses
