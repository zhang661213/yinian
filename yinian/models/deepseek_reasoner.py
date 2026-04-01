"""
DeepSeek R1 (推理) 模型适配器
R1 使用独立的 /reasoner 端点，响应格式与 Chat 不同
"""
import json
import time
from typing import Any, Dict, List, Optional

from yinian.models.base import BaseModel, ModelResponse

from loguru import logger


class DeepSeekReasonerModel(BaseModel):
    """DeepSeek R1 推理模型适配器"""
    
    model_name = "deepseek-r1"
    display_name = "DeepSeek R1 (推理)"
    base_url = "https://api.deepseek.com"
    model_id = "deepseek-reasoner"
    cost_per_1k_input = 0.001
    cost_per_1k_output = 0.004
    max_tokens = 64000
    timeout = 120  # R1 推理较慢
    
    def __init__(self, api_key: str = "", model: str = "deepseek-reasoner", **kwargs):
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
        发送对话请求到 DeepSeek R1 API
        
        R1 使用 /reasoner 端点，支持思考过程输出。
        响应格式：
          {
            "id": "xxx",
            "output": "...(推理结论)...",
            "reasoning": "...(思考过程)...",
            "usage": {...}
          }
        """
        start_time = time.time()
        
        # R1 使用独立的 /reasoner 端点
        url = f"{self.base_url}/reasoner"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
        }
        
        # R1 不支持 temperature
        if max_tokens:
            payload["max_tokens"] = max_tokens
        else:
            payload["max_tokens"] = self.max_tokens
        
        try:
            if stream:
                return await self._chat_stream(messages, max_tokens, start_time)
            
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
                        error=f"DeepSeek R1 API错误 ({response.status_code}): {error_msg}",
                        latency_ms=(time.time() - start_time) * 1000
                    )
                
                data = response.json()
                
                # R1 响应格式：output 是结论，reasoning 是思考过程
                content = data.get("output", "")
                reasoning = data.get("reasoning", "")
                
                # 如果有思考过程，可以附加到回复中
                if reasoning and kwargs.get("include_reasoning", False):
                    content = f"[推理过程]\n{reasoning}\n\n[结论]\n{content}"
                
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                # 估算
                if not input_tokens:
                    input_tokens = self.count_tokens("\n".join([m.get("content", "") for m in messages]))
                if not output_tokens:
                    output_tokens = self.count_tokens(content)
                if not total_tokens:
                    total_tokens = input_tokens + output_tokens
                
                cost = self.calculate_cost(input_tokens, output_tokens)
                latency_ms = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"DeepSeek R1 响应: {output_tokens} tokens, "
                    f"费用: ¥{cost:.6f}, 延迟: {latency_ms:.0f}ms"
                )
                
                return ModelResponse(
                    content=content,
                    model=self.model_name,
                    finish_reason="stop",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    raw_response=data
                )
                
        except Exception as e:
            logger.error(f"DeepSeek R1 请求异常: {e}")
            return ModelResponse(
                content="",
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def _chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        start_time: float
    ) -> ModelResponse:
        """R1 流式响应"""
        url = f"{self.base_url}/reasoner"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "stream": True,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        else:
            payload["max_tokens"] = self.max_tokens
        
        full_content = ""
        
        try:
            async with self.client as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_text = await response.text()
                        return ModelResponse(
                            content="",
                            model=self.model_name,
                            error=f"DeepSeek R1 API错误 ({response.status_code}): {error_text}",
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
                                chunk = json.loads(data_str)
                                # R1 流式：delta 字段
                                delta = chunk.get("delta", "")
                                if delta:
                                    full_content += delta
                            except json.JSONDecodeError:
                                continue
                    
                    input_tokens = self.count_tokens("\n".join([m.get("content", "") for m in messages]))
                    output_tokens = self.count_tokens(full_content)
                    
                    return ModelResponse(
                        content=full_content,
                        model=self.model_name,
                        finish_reason="stop",
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                        cost=self.calculate_cost(input_tokens, output_tokens),
                        latency_ms=(time.time() - start_time) * 1000
                    )
        except Exception as e:
            logger.error(f"DeepSeek R1 流式异常: {e}")
            return ModelResponse(
                content=full_content,
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
