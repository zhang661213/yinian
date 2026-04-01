"""
Llama.cpp 模型适配器
支持 llama-server 的 OpenAI 兼容 API
"""
import json
import time
from typing import Any, Dict, List, Optional

from yinian.models.base import BaseModel, ModelResponse

from loguru import logger

from loguru import logger


class LlamaModel(BaseModel):
    """Llama.cpp 模型适配器"""
    
    model_name = "llama"
    display_name = "Llama.cpp (本地)"
    base_url = "http://localhost:8080/v1"
    model_id = "default"
    cost_per_1k_input = 0.0  # 本地模型免费
    cost_per_1k_output = 0.0
    max_tokens = 4096
    timeout = 120  # 本地模型可能较慢
    # Llama.cpp 特殊: 是否使用 chat template
    use_chat_template = True
    
    def __init__(
        self,
        api_key: str = "",
        model: str = "default",
        use_chat_template: bool = True,
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.model_id = model or self.model_id
        self.api_key = api_key
        self.use_chat_template = use_chat_template
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """发送对话请求到 Llama.cpp"""
        start_time = time.time()
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
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
                        error=f"Llama.cpp 错误 ({response.status_code}): {error_msg}",
                        latency_ms=(time.time() - start_time) * 1000
                    )
                
                # 判断是否流式响应
                content_type = response.headers.get("content-type", "")
                is_streaming = "text/event-stream" in content_type
                
                if is_streaming or stream:
                    return await self._chat_stream_response(response, messages, start_time)
                
                # 非流式响应
                data = response.json()
                return self._parse_non_stream_response(data, messages, start_time)
        
        except Exception as e:
            logger.error(f"Llama.cpp 请求异常: {e}")
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
        """解析流式响应"""
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
                    choices = chunk.get("choices", [{}])
                    if choices:
                        delta = choices[0].get("delta", {})
                        text = delta.get("content", "")
                        if text:
                            content += text
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
        
        input_tokens = self.count_tokens("\n".join([m.get("content", "") for m in messages]))
        output_tokens = self.count_tokens(content)
        cost = self.calculate_cost(input_tokens, output_tokens)
        latency_ms = (time.time() - start_time) * 1000
        
        logger.debug(f"Llama.cpp 响应: {output_tokens} tokens, 延迟: {latency_ms:.0f}ms")
        
        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
        )
    
    def _parse_non_stream_response(
        self,
        data: Dict,
        messages: List[Dict[str, str]],
        start_time: float
    ) -> ModelResponse:
        """解析非流式响应"""
        choices = data.get("choices", [{}])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
        else:
            content = ""
        
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0) or self.count_tokens(
            "\n".join([m.get("content", "") for m in messages])
        )
        output_tokens = usage.get("completion_tokens", 0) or self.count_tokens(content)
        cost = self.calculate_cost(input_tokens, output_tokens)
        latency_ms = (time.time() - start_time) * 1000
        
        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            raw_response=data
        )
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with self.client as client:
                response = await client.get(f"{self.base_url}/models")
                if response.status_code != 200:
                    logger.warning(f"Llama health_check 失败: HTTP {response.status_code}")
                    return False
                return True
        except Exception as e:
            logger.warning(f"Llama health_check 失败: {e}")
            return False
