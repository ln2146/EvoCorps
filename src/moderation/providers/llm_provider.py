"""
LLM 审核提供者

使用与仿真主体相同的 LLM 端点（Gemini via OpenAI-compatible proxy）
进行语义级内容审核，能够识别仇恨言论、暴力内容等关键词无法覆盖的内容。

通过 multi_model_selector 统一管理 LLM 客户端（与其他 Agent 共享 API 配置和限速）。
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from ..types import ModerationVerdict, ModerationSeverity, ModerationCategory
from ..config import ModerationProviderConfig


logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """You are a content moderation assistant for a social media platform.
Analyze the given content and determine if it violates platform community guidelines.

Categories to flag:
- hate_speech: slurs, dehumanization, calls for discrimination against protected groups, targeted harassment
- violence: explicit threats of harm, graphic depictions of violence, incitement to violence
- sexual: explicit sexual content, unsolicited sexual material
- spam: commercial spam, scam links, phishing, deceptive advertising

Severity:
- low: borderline content, mildly problematic
- medium: clear violation, warrants a warning
- high: serious violation
- critical: severe violation requiring immediate action

Respond with valid JSON only — no markdown, no extra text.
If content violates policies:
{"flagged": true, "category": "hate_speech", "severity": "high", "confidence": 0.85, "reason": "brief reason"}
If content is acceptable:
{"flagged": false}"""


class LLMProvider:
    """
    LLM 审核提供者

    通过 LLM 对内容进行语义级审核，准确率远高于关键词匹配。
    使用 multi_model_selector 统一管理 API 客户端，与仿真主体共享 API 基础设施。
    """

    def __init__(self, config: ModerationProviderConfig):
        self.config = config

    def check(self, content: str, metadata: Dict[str, Any] = None) -> Optional[ModerationVerdict]:
        """
        使用 LLM 检查内容

        Args:
            content: 待检查的内容
            metadata: 额外元数据

        Returns:
            审核裁决，内容安全则返回 None
        """
        if not self.config.enabled:
            return None

        raw_text = self._call_llm(content)
        return self._parse_response(raw_text, content, metadata)

    def _call_llm(self, content: str) -> str:
        """调用 LLM 获取审核结果（通过 multi_model_selector 统一管理客户端）"""
        try:
            from multi_model_selector import multi_model_selector
            client, model_name = multi_model_selector.create_openai_client(role="moderation")
            logger.info(f"[LLM_CALL] Calling model={model_name} for content length={len(content)}")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"Moderate this content:\n\n{content[:2000]}"},
                ],
                max_tokens=150,
                temperature=0.1,
            )
            raw_response = response.choices[0].message.content.strip()
            logger.debug(f"[LLM_RESPONSE] raw={raw_response[:200]}")
            return raw_response
        except Exception as e:
            logger.error(f"[LLM_ERROR] API call failed: {e}")
            raise RuntimeError(f"LLM moderation API call failed: {e}") from e

    def _parse_response(
        self,
        raw_text: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[ModerationVerdict]:
        """解析 LLM 返回的 JSON 裁决"""
        # 剥离可能的 markdown 代码块
        text = raw_text
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else parts[0]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"LLM moderation returned invalid JSON: '{raw_text[:120]}': {e}"
            ) from e

        if not result.get("flagged"):
            logger.info(f"[LLM_PASS] content not flagged")
            return None

        # 解析分类
        category_str = result.get("category", "other")
        try:
            category = ModerationCategory(category_str)
        except ValueError:
            logger.warning(f"LLM returned unknown category '{category_str}', using OTHER")
            category = ModerationCategory.OTHER

        # 解析严重程度
        severity_str = result.get("severity", "medium")
        try:
            severity = ModerationSeverity(severity_str)
        except ValueError:
            logger.warning(f"LLM returned unknown severity '{severity_str}', using MEDIUM")
            severity = ModerationSeverity.MEDIUM

        confidence = max(0.0, min(1.0, float(result.get("confidence", 0.7))))
        reason = result.get("reason", "LLM moderation flagged content")

        verdict = ModerationVerdict(
            post_id="",
            user_id="",
            content=content,
            category=category,
            severity=severity,
            confidence=confidence,
            reason=reason,
            provider="llm",
            checked_at=datetime.now(),
            metadata=metadata or {},
        )

        logger.info(f"[LLM_FLAGGED] {reason} | category={category_str} | severity={severity_str} | confidence={confidence:.2f}")
        return verdict
