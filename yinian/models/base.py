"""
Yinian 模型基类
所有模型适配器必须继承此基类
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Callable

import httpx
from loguru import logger


@dataclass
class ModelResponse:
    """模型响应"""
    content: str
    model: str
    finish_reason: str = "stop"
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    raw_response: Optional[Dict] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        return self.content


@dataclass
class StreamChunk:
    """流式输出块"""
    content: str
    delta: str = ""
    is_final: bool = False
    model: str = ""


class BaseModel(ABC):
    """模型适配器基类"""
    
    # 类级别的模型配置
    model_name: str = ""
    display_name: str = ""
    api_key: str = ""
    base_url: str = ""
    model_id: str = ""
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    max_tokens: int = 4096
    timeout: int = 60
    enabled: bool = True
    
    def __init__(self, api_key: str = "", **kwargs):
        """
        初始化模型适配器
        
        Args:
            api_key: API Key
            **kwargs: 其他配置参数
        """
        self.api_key = api_key or self.__class__.api_key
        
        # 更新配置
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端（延迟初始化）"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._client
    
    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> ModelResponse:
        """
        发送对话请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            stream: 是否使用流式输出
            **kwargs: 其他参数
            
        Returns:
            ModelResponse: 模型响应
        """
        pass
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        流式对话
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            StreamChunk: 流式输出块
        """
        yield StreamChunk(content="", is_final=False)
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """计算费用"""
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return round(input_cost + output_cost, 6)
    
    def count_tokens(self, text: str) -> int:
        """
        估算 token 数量（简单估算，中文约 2 字符 = 1 token）
        实际应调用模型的 token 计算 API
        """
        # 简单估算：中文 1字符≈1token，英文 1单词≈1.3token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.0 + other_chars / 1.3)
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 发送一个简单的请求来验证 API Key 和连接
            response = await self.chat(
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5
            )
            return response.error is None
        except Exception as e:
            logger.error(f"{self.model_name} 健康检查失败: {e}")
            return False
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model_id}>"


class RetryHandler:
    """重试处理器"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行带重试的函数"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    logger.warning(
                        f"请求失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"{delay:.1f}秒后重试..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"请求失败，已达到最大重试次数: {e}")
        
        raise last_exception
