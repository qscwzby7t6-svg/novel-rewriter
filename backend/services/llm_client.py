"""
LLM调用客户端

支持DeepSeek API和OpenAI兼容接口，包含：
- 单次调用 / 带重试调用 / 批量调用
- 流式和非流式两种模式
- 成本控制：每章预算上限，超出自动切换到低成本模型
- 调用记录与成本估算
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from backend.config import get_config, AppConfig
from backend.models.schemas import LLMCallRecord

logger = logging.getLogger(__name__)


@dataclass
class CostTracker:
    """成本追踪器"""
    total_cost: float = 0.0
    chapter_cost: float = 0.0
    call_count: int = 0
    records: list[LLMCallRecord] = field(default_factory=list)

    def add_record(self, record: LLMCallRecord) -> None:
        """添加调用记录"""
        self.records.append(record)
        self.total_cost += record.cost
        self.call_count += 1

    def add_chapter_cost(self, cost: float) -> None:
        """增加章节成本"""
        self.chapter_cost += cost

    def reset_chapter(self) -> None:
        """重置章节成本"""
        self.chapter_cost = 0.0

    def is_chapter_over_budget(self, budget: float) -> bool:
        """检查章节是否超出预算"""
        return self.chapter_cost >= budget

    def is_total_over_budget(self, budget: float) -> bool:
        """检查总成本是否超出预算"""
        return self.total_cost >= budget


class LLMClient:
    """
    LLM调用客户端

    支持DeepSeek和OpenAI兼容接口，提供成本控制和自动降级功能。
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """
        初始化LLM客户端。

        Args:
            config: 应用配置，为None时自动加载
        """
        self._config = config or get_config()
        self._primary_client: Optional[AsyncOpenAI] = None
        self._fallback_client: Optional[AsyncOpenAI] = None
        self._cost_tracker = CostTracker()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """确保客户端已初始化"""
        if self._initialized:
            return

        llm_cfg = self._config.llm

        # 初始化主客户端
        if llm_cfg.api_key:
            self._primary_client = AsyncOpenAI(
                api_key=llm_cfg.api_key,
                base_url=llm_cfg.base_url,
                timeout=llm_cfg.timeout,
            )

        # 初始化备用客户端
        if llm_cfg.fallback_api_key:
            self._fallback_client = AsyncOpenAI(
                api_key=llm_cfg.fallback_api_key,
                base_url=llm_cfg.fallback_base_url,
                timeout=llm_cfg.timeout,
            )

        self._initialized = True

    @property
    def cost_tracker(self) -> CostTracker:
        """获取成本追踪器"""
        return self._cost_tracker

    def _get_client(self, use_fallback: bool = False) -> AsyncOpenAI:
        """获取OpenAI客户端"""
        self._ensure_initialized()

        if use_fallback:
            if self._fallback_client is None:
                raise RuntimeError("备用LLM客户端未配置，请检查fallback_api_key")
            return self._fallback_client

        if self._primary_client is None:
            raise RuntimeError("主LLM客户端未配置，请检查api_key")
        return self._primary_client

    def _should_use_fallback(self) -> bool:
        """判断是否应该使用备用模型"""
        llm_cfg = self._config.llm
        if self._cost_tracker.is_chapter_over_budget(llm_cfg.cost.chapter_budget):
            logger.warning(
                f"章节成本 {self._cost_tracker.chapter_cost:.4f} 元 "
                f"超过预算 {llm_cfg.cost.chapter_budget:.4f} 元，切换到备用模型"
            )
            return True
        if self._cost_tracker.is_total_over_budget(llm_cfg.cost.total_budget):
            logger.warning(
                f"总成本 {self._cost_tracker.total_cost:.4f} 元 "
                f"超过预算 {llm_cfg.cost.total_budget:.4f} 元，切换到备用模型"
            )
            return True
        return False

    def _get_model_name(self, use_fallback: bool = False) -> str:
        """获取模型名称"""
        if use_fallback:
            return self._config.llm.fallback_model
        return self._config.llm.model

    def _get_provider_name(self, use_fallback: bool = False) -> str:
        """获取提供商名称"""
        if use_fallback:
            return self._config.llm.fallback_provider
        return self._config.llm.provider

    def _get_price_per_1k(self, use_fallback: bool = False) -> float:
        """获取每千token价格"""
        if use_fallback:
            return self._config.llm.cost.fallback_price_per_1k
        return self._config.llm.cost.primary_price_per_1k

    def _calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        use_fallback: bool = False,
    ) -> float:
        """计算调用成本"""
        price = self._get_price_per_1k(use_fallback)
        total_tokens = prompt_tokens + completion_tokens
        return (total_tokens / 1000) * price

    def _create_call_record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        latency_ms: float,
        success: bool,
        error_message: str = "",
        chapter_number: int = 0,
        use_fallback: bool = False,
    ) -> LLMCallRecord:
        """创建调用记录"""
        return LLMCallRecord(
            call_id=str(uuid.uuid4())[:12],
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            provider=self._get_provider_name(use_fallback),
            model=self._get_model_name(use_fallback),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            chapter_number=chapter_number,
            is_fallback=use_fallback,
        )

    async def call(
        self,
        messages: list[dict[str, str]],
        chapter_number: int = 0,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_fallback: Optional[bool] = None,
        **kwargs: Any,
    ) -> str:
        """
        单次LLM调用。

        Args:
            messages: 消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
            chapter_number: 关联章节号
            max_tokens: 最大生成token数，默认使用配置值
            temperature: 生成温度，默认使用配置值
            use_fallback: 是否使用备用模型，None时自动判断
            **kwargs: 其他传递给OpenAI API的参数

        Returns:
            str: LLM生成的文本内容

        Raises:
            RuntimeError: API调用失败且重试耗尽
        """
        # 判断是否使用备用模型
        if use_fallback is None:
            use_fallback = self._should_use_fallback()

        client = self._get_client(use_fallback=use_fallback)
        model = self._get_model_name(use_fallback=use_fallback)
        llm_cfg = self._config.llm

        _max_tokens = max_tokens or llm_cfg.max_tokens_per_call
        _temperature = temperature if temperature is not None else llm_cfg.temperature

        start_time = time.time()
        prompt_tokens = 0
        completion_tokens = 0

        try:
            logger.debug(
                f"LLM调用: model={model}, messages={len(messages)}, "
                f"max_tokens={_max_tokens}, temperature={_temperature}"
            )

            response: ChatCompletion = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                max_tokens=_max_tokens,
                temperature=_temperature,
                top_p=llm_cfg.top_p,
                stream=False,
                **kwargs,
            )

            content = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0

            latency_ms = (time.time() - start_time) * 1000
            cost = self._calculate_cost(prompt_tokens, completion_tokens, use_fallback)

            record = self._create_call_record(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                latency_ms=latency_ms,
                success=True,
                chapter_number=chapter_number,
                use_fallback=use_fallback,
            )
            self._cost_tracker.add_record(record)
            self._cost_tracker.add_chapter_cost(cost)

            logger.info(
                f"LLM调用完成: tokens={prompt_tokens + completion_tokens}, "
                f"cost={cost:.4f}元, latency={latency_ms:.0f}ms"
            )

            return content

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            record = self._create_call_record(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=0.0,
                latency_ms=latency_ms,
                success=False,
                error_message=error_msg,
                chapter_number=chapter_number,
                use_fallback=use_fallback,
            )
            self._cost_tracker.add_record(record)

            logger.error(f"LLM调用失败: {error_msg}")
            raise RuntimeError(f"LLM调用失败: {error_msg}") from e

    async def call_with_retry(
        self,
        messages: list[dict[str, str]],
        chapter_number: int = 0,
        max_retries: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        带重试的LLM调用。

        在主模型失败时自动重试，重试耗尽后切换到备用模型。

        Args:
            messages: 消息列表
            chapter_number: 关联章节号
            max_retries: 最大重试次数，默认使用配置值
            **kwargs: 传递给call()的参数

        Returns:
            str: LLM生成的文本内容
        """
        _max_retries = max_retries or self._config.llm.max_retries
        last_error: Optional[Exception] = None

        # 先尝试主模型
        for attempt in range(_max_retries):
            try:
                return await self.call(
                    messages=messages,
                    chapter_number=chapter_number,
                    use_fallback=False,
                    **kwargs,
                )
            except RuntimeError as e:
                last_error = e
                delay = self._config.llm.retry_delay * (attempt + 1)
                logger.warning(
                    f"主模型调用失败 (尝试 {attempt + 1}/{_max_retries}), "
                    f"{delay}秒后重试: {e}"
                )
                await asyncio.sleep(delay)

        # 主模型重试耗尽，尝试备用模型
        logger.warning("主模型重试耗尽，切换到备用模型")
        try:
            return await self.call(
                messages=messages,
                chapter_number=chapter_number,
                use_fallback=True,
                **kwargs,
            )
        except RuntimeError as e:
            raise RuntimeError(
                f"主模型和备用模型均调用失败。最后错误: {e}"
            ) from e

    async def call_stream(
        self,
        messages: list[dict[str, str]],
        chapter_number: int = 0,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        流式LLM调用。

        Args:
            messages: 消息列表
            chapter_number: 关联章节号
            **kwargs: 传递给OpenAI API的参数

        Yields:
            str: 逐块生成的文本内容
        """
        use_fallback = self._should_use_fallback()
        client = self._get_client(use_fallback=use_fallback)
        model = self._get_model_name(use_fallback=use_fallback)
        llm_cfg = self._config.llm

        start_time = time.time()
        total_content = ""

        try:
            stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                max_tokens=kwargs.get("max_tokens") or llm_cfg.max_tokens_per_call,
                temperature=kwargs.get("temperature") or llm_cfg.temperature,
                top_p=llm_cfg.top_p,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    total_content += delta
                    yield delta

            latency_ms = (time.time() - start_time) * 1000
            # 流式模式无法精确获取token数，使用估算
            prompt_tokens = sum(len(m["content"]) for m in messages) // 2
            completion_tokens = len(total_content) // 2
            cost = self._calculate_cost(prompt_tokens, completion_tokens, use_fallback)

            record = self._create_call_record(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                latency_ms=latency_ms,
                success=True,
                chapter_number=chapter_number,
                use_fallback=use_fallback,
            )
            self._cost_tracker.add_record(record)
            self._cost_tracker.add_chapter_cost(cost)

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            record = self._create_call_record(
                prompt_tokens=0,
                completion_tokens=0,
                cost=0.0,
                latency_ms=latency_ms,
                success=False,
                error_message=str(e),
                chapter_number=chapter_number,
                use_fallback=use_fallback,
            )
            self._cost_tracker.add_record(record)
            raise RuntimeError(f"流式LLM调用失败: {e}") from e

    async def batch_call(
        self,
        messages_list: list[list[dict[str, str]]],
        chapter_number: int = 0,
        concurrency: int = 3,
        **kwargs: Any,
    ) -> list[str]:
        """
        批量LLM调用。

        Args:
            messages_list: 消息列表的列表，每个元素是一次独立的调用
            chapter_number: 关联章节号
            concurrency: 并发数
            **kwargs: 传递给call()的参数

        Returns:
            list[str]: 每次调用生成的文本内容列表
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _call_with_semaphore(messages: list[dict[str, str]]) -> str:
            async with semaphore:
                return await self.call_with_retry(
                    messages=messages,
                    chapter_number=chapter_number,
                    **kwargs,
                )

        tasks = [_call_with_semaphore(msgs) for msgs in messages_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量调用第{i}项失败: {result}")
                output.append("")
            else:
                output.append(result)

        return output

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_chapters: int = 1,
        calls_per_chapter: int = 5,
    ) -> dict[str, float]:
        """
        估算调用成本。

        Args:
            prompt_tokens: 单次调用的提示词token数
            completion_tokens: 单次调用的生成token数
            total_chapters: 总章数
            calls_per_chapter: 每章调用次数

        Returns:
            dict: 包含各项成本估算的字典
        """
        llm_cfg = self._config.llm
        single_cost = self._calculate_cost(
            prompt_tokens, completion_tokens, use_fallback=False
        )
        chapter_cost = single_cost * calls_per_chapter
        total_cost = chapter_cost * total_chapters

        fallback_single_cost = self._calculate_cost(
            prompt_tokens, completion_tokens, use_fallback=True
        )
        fallback_total_cost = fallback_single_cost * calls_per_chapter * total_chapters

        return {
            "single_call_cost": round(single_cost, 6),
            "chapter_cost": round(chapter_cost, 4),
            "total_cost": round(total_cost, 2),
            "fallback_single_call_cost": round(fallback_single_cost, 6),
            "fallback_total_cost": round(fallback_total_cost, 2),
            "total_tokens_estimate": (prompt_tokens + completion_tokens) * calls_per_chapter * total_chapters,
        }

    def reset_chapter_cost(self) -> None:
        """重置章节成本（在新章节开始时调用）"""
        self._cost_tracker.reset_chapter()

    def get_cost_summary(self) -> dict[str, Any]:
        """获取成本摘要"""
        tracker = self._cost_tracker
        return {
            "total_cost": round(tracker.total_cost, 4),
            "chapter_cost": round(tracker.chapter_cost, 4),
            "call_count": tracker.call_count,
            "success_count": sum(1 for r in tracker.records if r.success),
            "failure_count": sum(1 for r in tracker.records if not r.success),
            "fallback_count": sum(1 for r in tracker.records if r.is_fallback),
            "avg_latency_ms": (
                sum(r.latency_ms for r in tracker.records) / max(len(tracker.records), 1)
            ),
        }
