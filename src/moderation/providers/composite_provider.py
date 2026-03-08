"""
组合审核提供者

协调多个审核提供者，综合结果
"""

import logging
from typing import Optional, Dict, Any, List, Tuple

from ..types import ModerationVerdict, ModerationSeverity
from ..config import ModerationConfig
from .keyword_provider import KeywordProvider
from .llm_provider import LLMProvider


logger = logging.getLogger(__name__)


class CompositeProvider:
    """
    组合审核提供者

    协调多个提供者进行审核，综合结果得出最终裁决
    支持的策略:
    1. 优先级策略: 按提供者优先级顺序，返回第一个有结果的
    2. 投票策略: 多个提供者投票决定
    3. 置信度策略: 返回置信度最高的结果
    """

    def __init__(self, config: ModerationConfig):
        """
        初始化组合提供者

        Args:
            config: 审核配置
        """
        self.config = config
        self.providers: List[Tuple[str, float, Any]] = []  # (name, weight, provider)

        # 初始化子提供者
        self._init_providers()

    def _init_providers(self):
        """初始化所有配置的提供者"""
        # LLM Provider（主力：语义级审核，使用与仿真相同的 API 端点）
        if self.config.llm_provider.enabled:
            provider = LLMProvider(self.config.llm_provider)
            weight = self.config.llm_provider.weight
            self.providers.append(("llm", weight, provider))
            logger.info(f"[COMPOSITE_INIT] LLM provider initialized | weight={weight}")

        # Keyword Provider（兜底：无外部依赖，覆盖明显模式）
        if self.config.keyword_provider.enabled:
            provider = KeywordProvider(self.config.keyword_provider)
            weight = self.config.keyword_provider.weight
            self.providers.append(("keyword", weight, provider))
            logger.info(f"[COMPOSITE_INIT] Keyword provider initialized | weight={weight}")

        if not self.providers:
            logger.warning("No moderation providers enabled")

    def check(
        self,
        content: str,
        metadata: Dict[str, Any] = None,
        strategy: str = "confidence",
        keyword_only: bool = False
    ) -> Optional[ModerationVerdict]:
        """
        综合检查内容

        Args:
            content: 待检查的内容
            metadata: 额外元数据
            strategy: 综合策略 ("priority", "vote", "confidence")
            keyword_only: 是否只使用关键词审核（发布前快速检查）

        Returns:
            审核裁决，如果所有提供者都认为内容安全则返回 None

        Raises:
            RuntimeError: If no moderation providers are enabled
        """
        # NO FALLBACK: Require at least one provider to be enabled
        if not self.providers:
            raise RuntimeError(
                "CompositeProvider.check() called but no moderation providers are enabled. "
                "Please enable at least one moderation provider (openai or keyword) in config."
            )

        # 如果只使用关键词审核，直接调用关键词提供者
        if keyword_only:
            for name, weight, provider in self.providers:
                if name == "keyword":
                    try:
                        return provider.check(content, metadata)
                    except Exception as e:
                        logger.error(f"[KEYWORD_ERROR] {type(e).__name__}: {e}")
                        return None
            logger.warning("[COMPOSITE_WARN] keyword_only=True but keyword provider not enabled")
            return None

        if strategy == "priority":
            return self._check_priority(content, metadata)
        elif strategy == "vote":
            return self._check_vote(content, metadata)
        else:  # confidence
            return self._check_confidence(content, metadata)

    def _check_priority(
        self,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[ModerationVerdict]:
        """
        优先级策略: 按顺序返回第一个有结果的裁决
        """
        for name, weight, provider in self.providers:
            try:
                verdict = provider.check(content, metadata)
            except Exception as e:
                logger.error(f"[PROVIDER_ERROR] {name} raised {type(e).__name__}: {e}")
                continue
            if verdict:
                logger.info(f"[PRIORITY_VERDICT] provider={name} | category={verdict.category} | severity={verdict.severity}")
                return verdict

        return None

    def _check_confidence(
        self,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[ModerationVerdict]:
        """
        置信度策略: 返回置信度最高的裁决
        """
        verdicts = []

        for name, weight, provider in self.providers:
            try:
                verdict = provider.check(content, metadata)
            except Exception as e:
                logger.error(f"[PROVIDER_ERROR] {name} raised {type(e).__name__}: {e}")
                continue
            if verdict:
                # 加权置信度
                weighted_confidence = verdict.confidence * weight
                verdicts.append((name, verdict, weighted_confidence))
                logger.info(f"[CONFIDENCE_RESULT] provider={name} | raw_conf={verdict.confidence:.2f} | weight={weight} | weighted={weighted_confidence:.2f}")

        if not verdicts:
            return None

        # 返回置信度最高的
        verdicts.sort(key=lambda x: x[2], reverse=True)
        name, verdict, confidence = verdicts[0]
        logger.info(f"[CONFIDENCE_WINNER] provider={name} | final_confidence={confidence:.2f} | category={verdict.category} | severity={verdict.severity}")

        return verdict

    def _check_vote(
        self,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[ModerationVerdict]:
        """
        投票策略: 多数提供者认为需要审核才返回裁决
        """
        verdicts = []

        for name, weight, provider in self.providers:
            try:
                verdict = provider.check(content, metadata)
            except Exception as e:
                logger.error(f"[PROVIDER_ERROR] {name} raised {type(e).__name__}: {e}")
                continue
            if verdict:
                verdicts.append((name, verdict, weight))
                logger.info(f"[VOTE_RESULT] provider={name} voted FLAG | weight={weight}")

        if not verdicts:
            return None

        # 如果只有一个提供者返回结果，直接返回
        if len(verdicts) == 1:
            logger.info(f"[VOTE_SINGLE] only one provider flagged, returning: {verdicts[0][0]}")
            return verdicts[0][1]

        # 计算投票权重
        total_weight = sum(w for _, _, w in self.providers)
        flagged_weight = sum(w for _, _, w in verdicts)

        # 如果超过半数的权重认为需要审核
        if flagged_weight > total_weight / 2:
            # 选择严重程度最高的裁决
            verdicts.sort(
                key=lambda x: list(ModerationSeverity).index(x[1].severity),
                reverse=True
            )
            logger.info(f"[VOTE_PASSED] flagged_weight={flagged_weight:.1f} > threshold={total_weight/2:.1f} | winner={verdicts[0][0]}")
            return verdicts[0][1]

        logger.info(f"[VOTE_FAILED] flagged_weight={flagged_weight:.1f} <= threshold={total_weight/2:.1f}, no action")
        return None

    def check_batch(
        self,
        contents: List[str],
        metadata: Dict[str, Any] = None,
        strategy: str = "confidence"
    ) -> List[Optional[ModerationVerdict]]:
        """
        批量检查内容

        Args:
            contents: 内容列表
            metadata: 额外元数据
            strategy: 综合策略

        Returns:
            裁决列表
        """
        results = []

        for content in contents:
            verdict = self.check(content, metadata, strategy)
            results.append(verdict)

        return results

    def get_provider_names(self) -> List[str]:
        """获取已初始化的提供者名称列表"""
        return [name for name, _, _ in self.providers]

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """获取各提供者状态"""
        status = {}

        for name, weight, provider in self.providers:
            status[name] = {
                "weight": weight,
                "type": type(provider).__name__,
                "enabled": True,
            }

        return status
