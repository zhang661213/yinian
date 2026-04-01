"""
Kimi (Moonshot) 模型适配器
"""
import json
import time
from typing import Any, Dict, List, Optional

from yinian.models.base import BaseModel, ModelResponse, StreamChunk

from loguru import logger


class KimiModel(BaseModel):
    """Kimi (Moonshot) 模型适配器"""
    
    model_name = "kimi"
    display_name = "Kimi (Moonshot)"
    base_url = "https://api.moonshot.cn/v1"
    model_id = "moonshot-v1-8k"
    cost_per_1k_input = 0.012
    cost_per_1k_output = 0.012
    max_tokens = 8192
    timeout = 60
    
    # 支持的模型列表
    SUPPORTED_MODELS = {
        "moonshot-v1-8k": {"name": "Kimi 8K", "max_tokens": 8192},
        "moonshot-v1-32k": {"name": "Kimi 32K", "max_tokens": 32768},
        "moonshot-v1-128k": {"name": "Kimi 128K", "max_tokens": 131072},
    }
    
    def __init__(
        self,
        api_key: str = "",
        model: str = "moonshot-v1-8k",
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.model_id = model or self.model_id
        self.api_key = api_key
        
        # 根据模型更新 max_tokens
        if model in self.SUPPORTED_MODELS:
            self.max_tokens = self.SUPPORTED_MODELS[model]["max_tokens"]
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        发送对话请求到 Kimi API
        
        Args:
            messages: 消息列表
            stream: 是否流式输出
            temperature: 温度参数
            max_tokens: 最大输出 token 数
            **kwargs: 其他参数
            
        Returns:
            ModelResponse: 模型响应
        """
        start_time = time.time()
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        else:
            payload["max_tokens"] = self.max_tokens
        
        try:
            async with self.client as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                    except:
                        pass
                    return ModelResponse(
                        content="",
                        model=self.model_name,
                        error=f"API错误 ({response.status_code}): {error_msg}",
                        latency_ms=(time.time() - start_time) * 1000
                    )
                
                # 检测是否流式响应
                content_type = response.headers.get("content-type", "")
                is_streaming = "text/event-stream" in content_type or stream
                
                if is_streaming:
                    return await self._chat_stream_response(response, messages, start_time)
                
                # 非流式响应
                data = response.json()
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                cost = self.calculate_cost(input_tokens, output_tokens)
                latency_ms = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"Kimi 响应: {output_tokens} tokens, "
                    f"费用: ¥{cost:.6f}, 延迟: {latency_ms:.0f}ms"
                )
                
                return ModelResponse(
                    content=content,
                    model=self.model_name,
                    finish_reason=choice.get("finish_reason", "stop"),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    raw_response=data
                )
                
        except Exception as e:
            logger.error(f"Kimi 请求异常: {e}")
            return ModelResponse(
                content="",
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def _chat_stream_response(
        self,
        response,
        messages: List[Dict[str, str]],
        start_time: float
    ) -> ModelResponse:
        """解析 Kimi SSE 流式响应"""
        content = ""
        
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        content += delta
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
        
        input_tokens = self.count_tokens("\n".join([m.get("content", "") for m in messages]))
        output_tokens = self.count_tokens(content)
        cost = self.calculate_cost(input_tokens, output_tokens)
        latency_ms = (time.time() - start_time) * 1000
        
        logger.debug(f"Kimi 流式响应: {output_tokens} tokens, 延迟: {latency_ms:.0f}ms")
        
        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            latency_ms=latency_ms,
        )
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ):
        """流式输出生成器"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        
        try:
            async with self.client as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    async for line in response.aiter_lines():
                        if not line.strip() or not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield StreamChunk(content="", is_final=True, model=self.model_name)
                            break
                        
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                yield StreamChunk(content=delta, delta=delta, is_final=False, model=self.model_name)
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Kimi 流式输出异常: {e}")
            yield StreamChunk(content="", is_final=True, model=self.model_name, delta=str(e))
