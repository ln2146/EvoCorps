"""
关键词审核提供者

基于预定义关键词列表进行内容审核
"""

import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from ..types import ModerationVerdict, ModerationSeverity, ModerationCategory
from ..config import ModerationProviderConfig


logger = logging.getLogger(__name__)


class KeywordProvider:
    """
    关键词审核提供者

    基于预定义的关键词列表进行简单快速的审核
    适合作为 LLM 审核的前置过滤器

    特性:
    - 支持白名单上下文（避免误杀正面表达）
    - 支持正则表达式精确匹配
    - 默认只降级不删除（保守策略）
    """

    # 默认严重程度映射（关键词审核统一使用 LOW，只降级）
    DEFAULT_SEVERITY_MAP = {
        "hate_speech": ModerationSeverity.LOW,      # 降级 20%
        "spam": ModerationSeverity.LOW,
        "violence": ModerationSeverity.LOW,
        "sexual": ModerationSeverity.MEDIUM,        # 色情稍严格，降级 50%
        "controversial": ModerationSeverity.LOW,
    }

    # 默认关键词列表
    DEFAULT_KEYWORDS = {
        "hate_speech": [
            "仇恨", "歧视", "种族主义", "纳粹", "恐怖分子",
            "should die", "kill yourself", "hate speech"
        ],
        "spam": [
            "加微信", "扫码", "代购", "兼职", "赚钱",
            "buy now", "click here", "free money"
        ],
        "violence": [
            "暴力", "杀人", "砍人", "袭击", "爆炸",
            "violence", "murder", "attack", "bomb"
        ],
        "sexual": [
            "色情", "淫秽", "裸聊",
            "porn", "nude", "sex video"
        ],
        "controversial": [
            "争议", "质疑", "不明确",
        ],
    }

    # 白名单上下文（包含这些词组时不触发）
    WHITELIST_CONTEXTS = [
        # 反对/谴责类
        r"反对\s*仇恨", r"谴责\s*仇恨", r"抵制\s*仇恨",
        r"反对\s*歧视", r"谴责\s*歧视", r"抵制\s*歧视",
        r"反对\s*暴力", r"谴责\s*暴力", r"抵制\s*暴力",
        r"反对\s*恐怖", r"打击\s*恐怖",

        # 讨论/分析类
        r"讨论\s*仇恨", r"分析\s*歧视", r"研究\s*暴力",
        r"探讨.*?暴力", r"分析.*?恐怖",

        # 引用/报道类
        r"报道.*?暴力", r"新闻.*?暴力", r"事件.*?暴力",
        r"暴力.*?事件", r"暴力.*?报道",
        r"恐怖.*?袭击", r"袭击.*?事件",
        r"爆炸.*?事件", r"枪击.*?案",

        # 法律/执法类
        r"打击.*?暴力", r"制裁.*?恐怖", r"逮捕.*?杀人",
        r"判决.*?杀人", r"审判.*?暴力",

        # 历史/教育类
        r"历史.*?屠杀", r"纪念.*?屠杀", r"二战.*?纳粹",
        r"教训.*?暴力", r"警示.*?恐怖",

        # 英文
        r"against\s+hate", r"condemn\s+hate", r"oppose\s+discrimination",
        r"anti-violence", r"stop\s+violence", r"fight\s+terrorism",
        r"news.*?attack", r"report.*?violence",
    ]

    def __init__(self, config: ModerationProviderConfig):
        """
        初始化关键词提供者

        Args:
            config: 提供者配置
        """
        self.config = config
        self.enabled = config.enabled

        # 构建关键词索引
        self.keyword_map: Dict[str, Tuple[str, ModerationSeverity]] = {}
        self._build_keyword_index()

    def _build_keyword_index(self):
        """构建关键词索引 (keyword -> (category, severity))"""
        # 使用配置的关键词，如果为空则使用默认值
        keywords = self.config.keywords if self.config.keywords else self.DEFAULT_KEYWORDS

        for category, keyword_list in keywords.items():
            # 字符串分类转换为枚举
            try:
                category_enum = ModerationCategory(category)
            except ValueError:
                # 如果不是有效的枚举值，保持原样作为 metadata
                category_enum = category

            severity = self.DEFAULT_SEVERITY_MAP.get(
                category if isinstance(category, str) else category.value,
                ModerationSeverity.MEDIUM
            )

            for keyword in keyword_list:
                self.keyword_map[keyword.lower()] = (category_enum, severity)

        logger.info(f"[KEYWORD_INIT] Built keyword index with {len(self.keyword_map)} keywords across {len(keywords)} categories")

    def check(self, content: str, metadata: Dict[str, Any] = None) -> Optional[ModerationVerdict]:
        """
        检查内容

        Args:
            content: 待检查的内容
            metadata: 额外元数据

        Returns:
            审核裁决，如果未检测到关键词则返回 None
        """
        if not self.enabled:
            return None

        # 白名单检查：如果匹配白名单上下文，直接放行
        if self._is_whitelisted(content):
            logger.info(f"[KEYWORD_WHITELIST] content matched positive context pattern, passed")
            return None

        content_lower = content.lower()
        detected = []

        # 检测所有匹配的关键词
        for keyword, (category, severity) in self.keyword_map.items():
            if keyword in content_lower:
                detected.append((keyword, category, severity))

        if not detected:
            return None

        # 选择严重程度最高的检测结果
        top_result = max(detected, key=lambda x: list(ModerationSeverity).index(x[2]))
        keyword, category, severity = top_result

        # 收集所有检测到的关键词
        detected_keywords = [d[0] for d in detected]

        # 确定分类
        if isinstance(category, str):
            try:
                category_enum = ModerationCategory(category)
            except ValueError:
                category_enum = ModerationCategory.OTHER
        else:
            category_enum = category

        # 计算置信度 (基于命中关键词数量)
        confidence = min(0.9, 0.6 + len(detected) * 0.1)

        verdict = ModerationVerdict(
            post_id="",
            user_id="",
            content=content,
            category=category_enum,
            severity=severity,
            confidence=confidence,
            reason=f"检测到敏感关键词: {', '.join(set(detected_keywords))}",
            detected_keywords=list(set(detected_keywords)),
            provider="keyword",
            checked_at=datetime.now(),
            metadata=metadata or {},
        )

        logger.info(f"[KEYWORD_FLAGGED] {verdict.reason} | category={category_enum.value} | severity={severity.value} | confidence={confidence:.2f}")
        return verdict

    def _is_whitelisted(self, content: str) -> bool:
        """
        检查内容是否匹配白名单上下文

        Args:
            content: 待检查的内容

        Returns:
            是否匹配白名单
        """
        for pattern in self.WHITELIST_CONTEXTS:
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
            except re.error as e:
                logger.warning(f"Invalid whitelist pattern '{pattern}': {e}")
        return False

    def add_keywords(self, category: str, keywords: List[str], severity: ModerationSeverity = None):
        """
        动态添加关键词

        Args:
            category: 分类
            keywords: 关键词列表
            severity: 严重程度 (可选)
        """
        if severity is None:
            severity = self.DEFAULT_SEVERITY_MAP.get(category, ModerationSeverity.MEDIUM)

        try:
            category_enum = ModerationCategory(category)
        except ValueError:
            category_enum = category

        for keyword in keywords:
            self.keyword_map[keyword.lower()] = (category_enum, severity)

        logger.info(f"Added {len(keywords)} keywords to category '{category}'")

    def remove_keywords(self, keywords: List[str]):
        """
        移除关键词

        Args:
            keywords: 要移除的关键词列表
        """
        count = 0
        for keyword in keywords:
            if keyword.lower() in self.keyword_map:
                del self.keyword_map[keyword.lower()]
                count += 1

        logger.info(f"Removed {count} keywords")

    def check_regex(self, content: str, patterns: Dict[str, str]) -> Optional[ModerationVerdict]:
        """
        使用正则表达式检查内容

        Args:
            content: 待检查的内容
            patterns: 正则表达式模式字典 {category: pattern}

        Returns:
            审核裁决
        """
        if not self.enabled:
            return None

        detected = []

        for category, pattern in patterns.items():
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    detected.append((pattern, category))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        if not detected:
            return None

        # 使用第一个匹配的分类
        _, category = detected[0]
        severity = self.DEFAULT_SEVERITY_MAP.get(category, ModerationSeverity.MEDIUM)

        try:
            category_enum = ModerationCategory(category)
        except ValueError:
            category_enum = ModerationCategory.OTHER

        verdict = ModerationVerdict(
            post_id="",
            user_id="",
            content=content,
            category=category_enum,
            severity=severity,
            confidence=0.75,
            reason=f"检测到违规模式: {category}",
            provider="keyword_regex",
            checked_at=datetime.now(),
        )

        return verdict
