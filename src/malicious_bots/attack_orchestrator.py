"""
AttackOrchestrator - 攻击策略统一入口

根据 MaliciousBotConfig.coordination_mode 路由到对应的策略实现：
    SWARM     -> SwarmStrategy（当前已实现）
    DISPERSED -> DispersedStrategy（Step 3 实现）
    CHAIN     -> ChainStrategy（Step 4 实现）

MaliciousBotManager 只需调用 orchestrator.execute()，无需感知底层策略细节。
"""

import logging
from typing import List, Dict, Any, Optional

from .coordination_strategies import CoordinationMode, SwarmStrategy, DispersedStrategy, ChainStrategy

logger = logging.getLogger(__name__)


class AttackOrchestrator:
    """
    攻击策略路由器。

    职责：
    - 持有 bot_cluster 和 config 引用
    - 根据配置中的 coordination_mode 选择对应的策略实例
    - 向上层（MaliciousBotManager）提供统一的 execute() 接口
    - 记录策略切换日志，便于审计

    示例：
        orchestrator = AttackOrchestrator(bot_cluster, bot_config)

        # 蜂群式（默认）
        results = await orchestrator.execute(post_id, content, cluster_size)

        # 动态切换策略（如 AdaptiveController 触发高压调整）
        bot_config.attack_mode.mode = "dispersed"
        results = await orchestrator.execute(post_id, content, cluster_size)
    """

    def __init__(self, bot_cluster, config, conn=None):
        """
        Args:
            bot_cluster: SimpleMaliciousCluster 实例
            config     : MaliciousBotConfig 实例
            conn       : SQLite 连接（ChainStrategy 需要用于写入 leader post/user）
        """
        self.bot_cluster = bot_cluster
        self.config = config
        self.conn = conn  # 传递给 ChainStrategy，其他策略不使用

        # 预实例化策略对象（无状态，可复用）
        self._swarm_strategy = SwarmStrategy()
        self._dispersed_strategy = DispersedStrategy()
        self._chain_strategy = ChainStrategy()

        logger.info(
            f"[AttackOrchestrator] Initialized | "
            f"default_mode={config.coordination_mode.value}"
        )

    async def execute(
        self,
        target_post_id: str,
        target_content: str,
        cluster_size: int,
        post_pool: Optional[List[Dict[str, Any]]] = None,
        time_step: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据当前配置的协同模式执行攻击，返回评论结果列表。

        Args:
            target_post_id: 目标帖子 ID（SWARM / CHAIN 模式使用）
            target_content: 目标帖子内容
            cluster_size  : 本轮参与攻击的 bot 总数
            post_pool     : 帖子候选池（DISPERSED 模式使用），可为 None
            time_step     : 当前仿真时间步（CHAIN 模式用于写入 post_timesteps）

        Returns:
            List[Dict]: 各 bot 生成的评论结果。
            SwarmStrategy 下每条记录包含：
                content, persona_info, model_used, bot_role, disguise_level, ...
        """
        mode = self.config.coordination_mode

        if mode == CoordinationMode.SWARM:
            return await self._swarm_strategy.execute(
                target_post_id=target_post_id,
                target_content=target_content,
                cluster_size=cluster_size,
                bot_cluster=self.bot_cluster,
                role_distribution=self.config.role_distribution,
            )

        elif mode == CoordinationMode.DISPERSED:
            if not post_pool:
                logger.warning(
                    "[AttackOrchestrator] DISPERSED mode requires post_pool; "
                    "falling back to SWARM"
                )
                return await self._swarm_strategy.execute(
                    target_post_id=target_post_id,
                    target_content=target_content,
                    cluster_size=cluster_size,
                    bot_cluster=self.bot_cluster,
                    role_distribution=self.config.role_distribution,
                )
            return await self._dispersed_strategy.execute(
                post_pool=post_pool,
                cluster_size=cluster_size,
                bot_cluster=self.bot_cluster,
                role_distribution=self.config.role_distribution,
            )

        elif mode == CoordinationMode.CHAIN:
            return await self._chain_strategy.execute(
                target_post_id=target_post_id,
                target_content=target_content,
                cluster_size=cluster_size,
                bot_cluster=self.bot_cluster,
                chain_config=self.config.chain_config,
                conn=self.conn,
                time_step=time_step,
            )

        else:
            logger.error(f"[AttackOrchestrator] Unknown mode: {mode}; falling back to SWARM")
            return await self._swarm_strategy.execute(
                target_post_id=target_post_id,
                target_content=target_content,
                cluster_size=cluster_size,
                bot_cluster=self.bot_cluster,
                role_distribution=self.config.role_distribution,
            )
