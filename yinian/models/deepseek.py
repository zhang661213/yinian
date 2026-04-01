"""
DeepSeek 模型适配器
"""
import json
import time
from typing import Any, Dict, List, Optional

from yinian.models.base import BaseModel, ModelResponse, StreamChunk

from loguru import logger


class DeepSeekModel(BaseModel):
    """DeepSeek 模型适配器"""
    
    model_name = "deepseek"
    display_name = "DeepSeek"
    base_url = "https://api.deepseek.com/v1"
    model_id = "deepseek-chat"
    cost_per_1k_input = 0.001
    cost_per_1k_output = 0.002
    max_tokens = 4096
    timeout = 60
    
    def __init__(self, api_key: str = "", model: str = "deepseek-chat", **kwargs):
        super().__init__(api_key, **kwargs)
        self.model_id = model or self.model_id
        self.api_key = api_key
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        发送对话请求到 DeepSeek API
        
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
        
        # 添加额外参数
        if kwargs:
            for key, value in kwargs.items():
                if key in ("top_p", "frequency_penalty", "presence_penalty", "stop"):
                    payload[key] = value
        
        try:
            if stream:
                return await self._chat_stream(messages, temperature, max_tokens, **kwargs)
            
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
                
                data = response.json()
                
                # 解析响应
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
                    f"DeepSeek 响应: {output_tokens} tokens, "
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
            logger.error(f"DeepSeek 请求异常: {e}")
            return ModelResponse(
                content="",
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def _chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """流式请求处理"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        else:
            payload["max_tokens"] = self.max_tokens
        
        full_content = ""
        start_time = time.time()
        
        try:
            async with self.client as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_text = await response.text()
                        return ModelResponse(
                            content="",
                            model=self.model_name,
                            error=f"API错误 ({response.status_code}): {error_text}",
                            latency_ms=(time.time() - start_time) * 1000
                        )
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    full_content += delta
                            except json.JSONDecodeError:
                                continue
                    
                    # 流式完成后，发送一个假的非流式请求来获取 usage 信息
                    # 因为 DeepSeek 流式响应不包含 usage
                    usage = await self._get_usage_estimate(len(messages), full_content)
                    
                    return ModelResponse(
                        content=full_content,
                        model=self.model_name,
                        finish_reason="stop",
                        input_tokens=usage["input_tokens"],
                        output_tokens=usage["output_tokens"],
                        total_tokens=usage["total_tokens"],
                        cost=self.calculate_cost(usage["input_tokens"], usage["output_tokens"]),
                        latency_ms=(time.time() - start_time) * 1000
                    )
                    
        except Exception as e:
            logger.error(f"DeepSeek 流式请求异常: {e}")
            return ModelResponse(
                content=full_content,
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def _get_usage_estimate(self, messages_count: int, content: str) -> Dict[str, int]:
        """估算 token 使用量"""
        # 简单估算
        input_tokens = messages_count * 10  # 每条消息约 10 tokens
        output_tokens = self.count_tokens(content)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
    
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
            logger.error(f"DeepSeek 流式输出异常: {e}")
            yield StreamChunk(content="", is_final=True, model=self.model_name, delta=str(e))
