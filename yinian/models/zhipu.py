"""
智谱 ChatGLM 模型适配器
"""
import json
import time
from typing import Any, Dict, List, Optional

from yinian.models.base import BaseModel, ModelResponse, StreamChunk

from loguru import logger


class ZhipuModel(BaseModel):
    """智谱 ChatGLM 模型适配器"""
    
    model_name = "zhipu"
    display_name = "智谱 ChatGLM"
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    model_id = "glm-4-flash"
    cost_per_1k_input = 0.001
    cost_per_1k_output = 0.001
    max_tokens = 128000
    timeout = 60
    
    # 支持的模型
    SUPPORTED_MODELS = {
        "glm-4-flash": {"name": "GLM-4 Flash", "cost_in": 0.001, "cost_out": 0.001, "max_tokens": 128000},
        "glm-4": {"name": "GLM-4", "cost_in": 0.1, "cost_out": 0.1, "max_tokens": 128000},
        "glm-4-plus": {"name": "GLM-4 Plus", "cost_in": 0.1, "cost_out": 0.1, "max_tokens": 128000},
        "glm-4v-flash": {"name": "GLM-4V Flash", "cost_in": 0.001, "cost_out": 0.001, "max_tokens": 8192},
        "glm-3-turbo": {"name": "GLM-3 Turbo", "cost_in": 0.001, "cost_out": 0.001, "max_tokens": 128000},
    }
    
    def __init__(
        self,
        api_key: str = "",
        model: str = "glm-4-flash",
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.model_id = model or self.model_id
        self.api_key = api_key
        
        if model in self.SUPPORTED_MODELS:
            cfg = self.SUPPORTED_MODELS[model]
            self.cost_per_1k_input = cfg["cost_in"]
            self.cost_per_1k_output = cfg["cost_out"]
            self.max_tokens = cfg["max_tokens"]
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """发送对话请求到智谱 API"""
        start_time = time.time()
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "stream": stream,
        }
        
        if temperature:
            payload["temperature"] = temperature
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
                
                # 先检测是否流式（关键！不能在 stream=True 时先调用 response.json()）
                content_type = response.headers.get("content-type", "")
                is_streaming = "text/event-stream" in content_type or stream
                
                if is_streaming:
                    # 流式响应解析
                    content = ""
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    content += delta
                            except:
                                continue
                    input_tokens = self.count_tokens("\n".join([m.get("content", "") for m in messages]))
                    output_tokens = self.count_tokens(content)
                    cost = self.calculate_cost(input_tokens, output_tokens)
                    latency_ms = (time.time() - start_time) * 1000
                    return ModelResponse(
                        content=content,
                        model=self.model_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                        cost=cost,
                        latency_ms=latency_ms,
                    )
                
                # 非流式响应
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                if not input_tokens:
                    input_tokens = self.count_tokens("\n".join([m.get("content", "") for m in messages]))
                if not output_tokens:
                    output_tokens = self.count_tokens(content)
                if not total_tokens:
                    total_tokens = input_tokens + output_tokens
                
                cost = self.calculate_cost(input_tokens, output_tokens)
                latency_ms = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"智谱 响应: {output_tokens} tokens, "
                    f"费用: ¥{cost:.6f}, 延迟: {latency_ms:.0f}ms"
                )
                
                return ModelResponse(
                    content=content,
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    raw_response=data
                )
                
        except Exception as e:
            logger.error(f"智谱 请求异常: {e}")
            return ModelResponse(
                content="",
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
