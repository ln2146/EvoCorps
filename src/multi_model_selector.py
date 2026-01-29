#!/usr/bin/env python3
"""
Multi-model selection system - centrally manages model selection for all agents.
Supports random selection across multiple models with fallback mechanisms.
"""

from __future__ import annotations

import random
import logging
import time
import asyncio
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING
from openai import OpenAI
import httpx
from keys import OPENAI_API_KEY, OPENAI_BASE_URL, EMBEDDING_API_KEY, EMBEDDING_BASE_URL

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI


class MultiModelSelector:
    """Multi-model selection system."""
    
    # Full list of supported models.
    ALL_MODELS = [
        "gpt-4.1-nano",      # OpenAI-compatible model
        "gemini-2.0-flash",  # Google Gemini model
        "deepseek-chat",
    ]

    # Centralized per-role model pools.
    #
    # Keep all role defaults here. If you want every role to use DeepSeek, keep the
    # pools as ["deepseek-chat"]. If you want multi-provider fallback, add models
    # to the lists below (they must be OpenAI-compatible on your OPENAI_BASE_URL).
    EMBEDDING_MODEL = "embedding-3"
    DEFAULT_POOL = ["deepseek-chat"]
    ROLE_MODEL_POOLS: dict[str, list[str]] = {
        # Core agent roles
        "regular": DEFAULT_POOL,
        "malicious": DEFAULT_POOL,
        "analyst": DEFAULT_POOL,
        "strategist": DEFAULT_POOL,
        "leader": DEFAULT_POOL,
        "echo": DEFAULT_POOL,
        # System roles
        "memory": DEFAULT_POOL,
        "fact_checker": DEFAULT_POOL,
        "summary": DEFAULT_POOL,
        "experiment": DEFAULT_POOL,
        "interview": DEFAULT_POOL,
        "comment_diversity": DEFAULT_POOL,
        # Embedding role (client only; embedding model is supplied by caller)
        "embedding": [EMBEDDING_MODEL],
    }

    # Backwards-compatible aliases used elsewhere in this repo.
    AVAILABLE_MODELS = ROLE_MODEL_POOLS["regular"]
    MALICIOUS_ECHO_MODELS = ROLE_MODEL_POOLS["malicious"]
    FALLBACK_PRIORITY = ROLE_MODEL_POOLS["regular"]
    MALICIOUS_ECHO_FALLBACK = ROLE_MODEL_POOLS["malicious"]
    
    def __init__(self):
        self.usage_stats = {model: 0 for model in self.ALL_MODELS}
        self.failure_stats = {model: 0 for model in self.ALL_MODELS}
        self.api_health_status = {}
        self.failed_api_cooldown = 300  # 5-minute cooldown
        self.last_failure_time = {}

        # New: request configuration optimized to align with utils.py
        self.request_config = {
            "timeout": 120,  # Increased timeout to match utils.py
            "max_retries": 1,  # Fewer retries to fail fast into fallback
            "retry_delay": 2,  # Retry delay
            "connection_pool_size": 5,  # Smaller connection pool to avoid conflicts
            "max_keepalive_connections": 2  # Lower keep-alive count
        }

        # New: request pacing control matching utils.py
        self.last_request_time = {model: 0 for model in self.ALL_MODELS}
        # Extended intervals to address persistent API errors
        self.min_request_interval = {
            "deepseek-chat": 10.0,    # DeepSeek can be rate-limited on some gateways
            "gemini-2.0-flash": 8.0,  # Gemini interval 8 seconds (increased)
            "gpt-4.1-nano": 6.0,      # GPT interval 6 seconds
            "default": 8.0            # Others 8 seconds (increased)
        }
        self.request_lock = {model: False for model in self.ALL_MODELS}  # Add per-model lock

        # New: connection pool management
        self._http_client = None
        
    def _wait_for_request_interval(self, model: str):
        """等待请求间隔，避免过于频繁的请求"""
        # check模型是否被锁定
        max_wait_attempts = 10
        wait_attempts = 0

        while self.request_lock.get(model, False) and wait_attempts < max_wait_attempts:
            time.sleep(0.1)
            wait_attempts += 1

        # 锁定模型
        self.request_lock[model] = True

        try:
            current_time = time.time()
            last_request = self.last_request_time.get(model, 0)
            time_since_last = current_time - last_request

            # 根据failed次数dynamicadjust间隔
            failure_count = self.failure_stats.get(model, 0)
            # get模型特定的间隔时间
            base_interval = self.min_request_interval.get(model, self.min_request_interval["default"])
            dynamic_interval = base_interval

            if failure_count >= 3:
                dynamic_interval = base_interval * (1 + failure_count * 0.5)

            if time_since_last < dynamic_interval:
                wait_time = dynamic_interval - time_since_last
                if wait_time > 0.1:  # 只有等待时间超过0.1秒才等待
                    time.sleep(wait_time)

            self.last_request_time[model] = time.time()
        finally:
            # 释放锁
            self.request_lock[model] = False

    @staticmethod
    def _normalize_role(role: Optional[str]) -> str:
        if not role:
            return "regular"
        role_norm = str(role).strip().lower()
        return role_norm or "regular"

    def get_model_pool(self, role: Optional[str] = None) -> list[str]:
        """Get model pool for a role; falls back to regular."""
        role_norm = self._normalize_role(role)
        pool = self.ROLE_MODEL_POOLS.get(role_norm)
        return pool if pool else self.ROLE_MODEL_POOLS["regular"]

    def select_random_model(self, role: Optional[str] = None) -> str:
        """randomselect一个模型（按角色）"""
        pool = self.get_model_pool(role)
        # 优先select健康的模型
        healthy_models = [model for model in pool if self.is_model_healthy(model)]

        if healthy_models:
            selected = random.choice(healthy_models)
        else:
            # 如果没有健康的模型，select冷却时间最短的
            selected = min(pool, key=lambda m: self.last_failure_time.get(m, 0))
            print(f"⚠️ 所有模型都在冷却期，选择冷却时间最短的: {selected}")

        self.usage_stats[selected] += 1
        return selected
    
    def select_model_for_agent_type(self, agent_type: str) -> str:
        """根据Agentclass型select模型（兼容旧调用）"""
        return self.select_random_model(role=agent_type)

    def is_model_healthy(self, model: str) -> bool:
        """check模型是否健康（未在冷却期）"""
        import time
        if model not in self.last_failure_time:
            return True

        time_since_failure = time.time() - self.last_failure_time[model]
        return time_since_failure > self.failed_api_cooldown

    def mark_model_failed(self, model: str, error_type: str = "unknown"):
        """标记模型failed"""
        import time
        if model not in self.failure_stats:
            self.failure_stats[model] = 0
            self.usage_stats[model] = 0
        self.failure_stats[model] += 1
        self.last_failure_time[model] = time.time()
        print(f"🚫 模型 {model} 标记为失败，进入冷却期")
        print(f"⚠️ 模型 {model} 失败次数: {self.failure_stats[model]}")

        # 根据errorclass型提供详细information
        if "502" in error_type or "Bad Gateway" in error_type:
            print(f"⚠️ 模型 {model} 遇到502错误，标记为失败并尝试下一个模型...")
        elif "405" in error_type or "bad_response_status_code" in error_type:
            print(f"⚠️ 模型 {model} 遇到405错误，方法不支持，标记为失败...")
        elif "content_filter" in error_type:
            print(f"⚠️ 模型 {model} 遇到内容过滤错误，内容被Microsoft策略过滤，标记为失败...")
        elif "400" in error_type:
            print(f"⚠️ 模型 {model} 遇到400错误，请求格式问题，标记为失败...")
        elif "timeout" in error_type.lower():
            print(f"⚠️ 模型 {model} 遇到超时错误，标记为失败...")
        elif "rate_limit" in error_type.lower():
            print(f"⚠️ 模型 {model} 遇到速率限制，标记为失败...")
        elif "upstream_error" in error_type:
            print(f"⚠️ 模型 {model} 遇到上游错误，标记为失败...")
        elif "json_parse_error" in error_type:
            print(f"⚠️ 模型 {model} 返回空响应或格式错误，标记为失败...")

        return None

    def handle_api_error(self, model: str, error: Exception) -> str:
        """processAPIerror并返回回退模型"""
        error_str = str(error)

        # identifyerrorclass型
        if "502" in error_str or "Bad Gateway" in error_str:
            error_type = "502_bad_gateway"
        elif "405" in error_str or "bad_response_status_code" in error_str:
            error_type = "405_error"
        elif "400" in error_str and "content_filter" in error_str.lower():
            error_type = "content_filter"
        elif "400" in error_str:
            error_type = "400_error"
        elif "upstream_error" in error_str:
            error_type = "upstream_error"
        elif "timeout" in error_str.lower():
            error_type = "timeout"
        elif "rate_limit" in error_str.lower():
            error_type = "rate_limit"
        elif "Expecting value" in error_str and "char 0" in error_str:
            error_type = "json_parse_error"
        else:
            error_type = "unknown"

        # 标记模型failed
        self.mark_model_failed(model, error_type)

        # get下一个可用模型
        next_model = self.get_next_fallback_model(model)
        if next_model:
            print(f"✅ 模型回退成功: {model} -> {next_model}")
            return next_model
        else:
            print(f"❌ 没有可用的回退模型")
            return None

    def get_healthy_models(self) -> list[str]:
        """get健康的模型列表（regular 池）"""
        pool = self.get_model_pool("regular")
        return [model for model in pool if self.is_model_healthy(model)]

    def get_next_fallback_model(self, failed_model: str) -> str:
        """get下一个回退模型"""
        try:
            current_index = self.FALLBACK_PRIORITY.index(failed_model)
            # 返回下一个优先级的模型
            if current_index + 1 < len(self.FALLBACK_PRIORITY):
                return self.FALLBACK_PRIORITY[current_index + 1]
            else:
                # 如果已经是最后一个，返回第一个
                return self.FALLBACK_PRIORITY[0]
        except ValueError:
            # 如果模型不在优先级列表中，返回default模型
            return self.FALLBACK_PRIORITY[0]

    def select_smart_model(self) -> str:
        """智能select模型 - 优先select健康的模型"""
        healthy_models = self.get_healthy_models()

        if not healthy_models:
            print("⚠️ 所有模型都在冷却期，使用最早失败的模型")
            # select最早failed的模型（冷却时间最长）
            if self.last_failure_time:
                return min(self.last_failure_time.keys(), key=lambda x: self.last_failure_time[x])
            else:
                return random.choice(self.get_model_pool("regular"))

        # 从健康模型中randomselect
        selected = random.choice(healthy_models)
        self.usage_stats[selected] += 1
        return selected

    def select_malicious_echo_model(self) -> str:
        """为恶意水军和echo_groupselect模型"""
        # get健康的恶意水军专用模型
        pool = self.get_model_pool("echo")
        healthy_malicious_models = [model for model in pool if self.is_model_healthy(model)]

        if not healthy_malicious_models:
            print("⚠️ 所有恶意水军专用模型都在冷却期，使用最早失败的模型")
            # 从恶意水军专用模型中select最早failed的
            malicious_failure_times = {k: v for k, v in self.last_failure_time.items() if k in pool}
            if malicious_failure_times:
                return min(malicious_failure_times.keys(), key=lambda x: malicious_failure_times[x])
            else:
                return random.choice(pool)

        # 从健康的恶意水军专用模型中randomselect
        selected = random.choice(healthy_malicious_models)
        self.usage_stats[selected] += 1
        return selected

    def create_openai_client(self, model_name: str = None, role: str = "regular") -> Tuple[OpenAI, str]:
        """createoptimize的OpenAIclient"""
        if model_name is None:
            model_name = self.select_random_model(role=role)

        # 请求间隔控制
        self._wait_for_request_interval(model_name)

        # createoptimize的HTTPclient
        http_client = httpx.Client(
            timeout=self.request_config["timeout"],
            limits=httpx.Limits(
                max_connections=self.request_config["connection_pool_size"],
                max_keepalive_connections=self.request_config["max_keepalive_connections"]
            )
        )

        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            timeout=self.request_config["timeout"],
            http_client=http_client
        )

        return client, model_name

    def create_openai_client_with_base_url(
        self,
        base_url: str,
        api_key: str,
        model_name: str = None,
        role: str = "regular",
    ) -> Tuple[OpenAI, str]:
        """Create OpenAI client with a custom base_url (e.g., local/ollama)."""
        if model_name is None:
            model_name = self.select_random_model(role=role)

        # 请求间隔控制
        self._wait_for_request_interval(model_name)

        http_client = httpx.Client(
            timeout=self.request_config["timeout"],
            limits=httpx.Limits(
                max_connections=self.request_config["connection_pool_size"],
                max_keepalive_connections=self.request_config["max_keepalive_connections"]
            )
        )

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=self.request_config["timeout"],
            http_client=http_client
        )

        return client, model_name

    def create_embedding_client(self, model_name: str = None) -> Tuple[OpenAI, str]:
        """Create OpenAI client for embeddings."""
        if model_name is None:
            model_name = self.EMBEDDING_MODEL
        return self.create_openai_client_with_base_url(
            base_url=EMBEDDING_BASE_URL,
            api_key=EMBEDDING_API_KEY,
            model_name=model_name,
            role="embedding",
        )
    
    def create_langchain_client(self, model_name: str = None, role: str = "regular", **kwargs) -> Tuple[ChatOpenAI, str]:
        """createoptimize的LangChain ChatOpenAIclient"""
        try:
            from langchain_openai import ChatOpenAI
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "Missing dependency 'langchain-openai'. Install it or avoid calling create_langchain_client()."
            ) from e

        if model_name is None:
            model_name = self.select_random_model(role=role)

        # 请求间隔控制
        self._wait_for_request_interval(model_name)

        # getsecure的模型configure（避免不支持的parameter）
        model_config = self.get_safe_model_config(model_name)

        # mergeuser提供的parameter
        final_config = model_config.copy()
        final_config.update(kwargs)

        # createoptimize的HTTPclient
        http_client = httpx.Client(
            timeout=self.request_config["timeout"],
            limits=httpx.Limits(
                max_connections=self.request_config["connection_pool_size"],
                max_keepalive_connections=self.request_config["max_keepalive_connections"]
            )
        )

        client = ChatOpenAI(
            model=model_name,
            openai_api_key=OPENAI_API_KEY,
            openai_api_base=OPENAI_BASE_URL,
            timeout=self.request_config["timeout"],
            max_retries=self.request_config["max_retries"],
            http_client=http_client,
            **final_config
        )

        return client, model_name
    
    def create_client_with_fallback(
        self,
        preferred_model: str = None,
        client_type: str = "openai",
        role: str = "regular",
    ) -> Tuple[Any, str]:
        """createclient，支持回退机制（按角色）"""
        fallback_pool = self.get_model_pool(role)
        models_to_try = fallback_pool.copy() if preferred_model is None else [preferred_model] + [m for m in fallback_pool if m != preferred_model]
        
        last_error = None
        for model in models_to_try:
            try:
                if client_type == "langchain":
                    client, selected_model = self.create_langchain_client(model, role=role)
                else:
                    client, selected_model = self.create_openai_client(model, role=role)
                
                # simpletestingconnect（可选）
                return client, selected_model
                
            except Exception as e:
                last_error = e
                self.failure_stats[model] += 1
                logging.warning(f"模型 {model} connectfailed: {e}")
                continue
        
        # 如果所有模型都failed，抛出exception
        raise Exception(f"所有模型都connectfailed，最后error: {last_error}")
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """get特定模型的configureparameter"""
        # basicconfigure（所有模型都支持）
        base_configs = {
            "gpt-4.1-nano": {
                "temperature": 0.8,
                "max_tokens": 150
            },
            "deepseek-chat": {
                "temperature": 0.7,
                "max_tokens": 200
            },
            "gemini-2.0-flash": {
                "temperature": 0.75,
                "max_tokens": 180
            },

        }

        # 模型特定的支持parameter
        model_specific_params = {
            "gpt-4.1-nano": {
                "frequency_penalty": 0.3,
                "presence_penalty": 0.3
            },
            "deepseek-chat": {},
            "gemini-2.0-flash": {},
        }

        # getbasicconfigure，如果模型不存在则抛出exception
        if model_name not in base_configs:
            raise ValueError(f"模型 {model_name} 不支持")
        config = base_configs[model_name].copy()

        # 添加模型特定parameter
        if model_name in model_specific_params:
            config.update(model_specific_params[model_name])

        return config

    def get_safe_model_config(self, model_name: str) -> Dict[str, Any]:
        """getsecure的模型configureparameter（移除可能不支持的parameter）"""
        config = self.get_model_config(model_name)

        # 定义secure的通用parameter（大多数模型都支持）
        safe_params = ["temperature", "max_tokens", "top_p", "top_k"]

        # createsecureconfigure
        safe_config = {}
        for param in safe_params:
            if param in config:
                safe_config[param] = config[param]

        # 对于特定模型，谨慎添加advancedparameter
        if model_name == "gpt-4.1-nano":
            # GPT模型通常支持penaltyparameter
            if "frequency_penalty" in config:
                safe_config["frequency_penalty"] = config["frequency_penalty"]
            if "presence_penalty" in config:
                safe_config["presence_penalty"] = config["presence_penalty"]

        return safe_config
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """getusingstatistics"""
        total_usage = sum(self.usage_stats.values())
        total_failures = sum(self.failure_stats.values())
        
        return {
            "total_requests": total_usage,
            "total_failures": total_failures,
            "success_rate": (total_usage - total_failures) / max(total_usage, 1),
            "model_usage": self.usage_stats.copy(),
            "model_failures": self.failure_stats.copy(),
            "model_success_rates": {
                model: (self.usage_stats[model] - self.failure_stats[model]) / max(self.usage_stats[model], 1)
                for model in self.AVAILABLE_MODELS
            }
        }
    
    def print_stats(self):
        """打印usingstatistics"""
        stats = self.get_usage_stats()
        print("\n🤖 多模型选择系统统计:")
        print(f"   总请求数: {stats['total_requests']}")
        print(f"   总失败数: {stats['total_failures']}")
        print(f"   总成功率: {stats['success_rate']:.1%}")
        print("\n📊 各模型使用情况:")
        for model in self.AVAILABLE_MODELS:
            usage = stats['model_usage'][model]
            failures = stats['model_failures'][model]
            success_rate = stats['model_success_rates'][model]
            print(f"   {model}: {usage}次使用, {failures}次失败, {success_rate:.1%}成功率")

    def record_usage(self, model_name: str, success: bool = True):
        """record模型using情况"""
        try:
            if model_name in self.ALL_MODELS:
                self.usage_stats[model_name] += 1
                if not success:
                    self.failure_stats[model_name] += 1
                    # Align with is_model_healthy(): failures mark last_failure_time.
                    self.last_failure_time[model_name] = time.time()
            else:
                print(f"⚠️ 未知模型: {model_name}")
        except Exception as e:
            print(f"⚠️ 记录模型使用失败: {e}")


# global多模型select器instance
multi_model_selector = MultiModelSelector()


def get_random_model(role: str = "regular") -> str:
    """getrandom模型的便捷函数（按角色）"""
    return multi_model_selector.select_random_model(role=role)


def create_model_client(agent_type: str = "normal", client_type: str = "openai", **kwargs) -> Tuple[Any, str]:
    """为Agentcreate模型client的便捷函数"""
    try:
        return multi_model_selector.create_client_with_fallback(client_type=client_type, role=agent_type, **kwargs)
    except Exception as e:
        logging.error(f"create{agent_type} Agent的模型clientfailed: {e}")
        raise


def log_model_usage(agent_type: str, model_name: str, success: bool = True):
    """record模型using情况"""
    if not success:
        multi_model_selector.failure_stats[model_name] += 1
    
    logging.info(f"{agent_type} Agentusing模型: {model_name}, successful: {success}")


if __name__ == "__main__":
    # testing多模型selectsystem
    print("🧪 测试多模型选择系统...")
    
    selector = MultiModelSelector()
    
    # testingrandomselect
    print("\n🎲 随机模型选择测试:")
    for i in range(10):
        model = selector.select_random_model()
        print(f"   选择 {i+1}: {model}")
    
    # 打印statistics
    selector.print_stats()
    
    # testingclientcreate
    print("\n🔧 客户端创建测试:")
    try:
        client, model = selector.create_openai_client()
        print(f"   ✅ OpenAI客户端创建成功，模型: {model}")
    except Exception as e:
        print(f"   ❌ OpenAI客户端创建失败: {e}")
    
    try:
        client, model = selector.create_langchain_client()
        print(f"   ✅ LangChain客户端创建成功，模型: {model}")
    except Exception as e:
        print(f"   ❌ LangChain客户端创建失败: {e}")
