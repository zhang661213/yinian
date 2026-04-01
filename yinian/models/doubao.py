"""
字节跳动豆包 (Doubao) 模型适配器
"""
import json
import time
from typing import Any, Dict, List, Optional

from yinian.models.base import BaseModel, ModelResponse, StreamChunk

from loguru import logger


class DoubaoModel(BaseModel):
    """字节跳动豆包 (Doubao) 模型适配器"""
    
    model_name = "doubao"
    display_name = "字节豆包"
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model_id = "doubao-pro-32k"
    cost_per_1k_input = 0.003
    cost_per_1k_output = 0.003
    max_tokens = 32768
    timeout = 60
    
    # 支持的模型（2025年最新价格，数据来源：火山引擎官网）
    SUPPORTED_MODELS = {
        "doubao-pro-32k": {
            "name": "豆包 Pro 32K",
            "cost_in": 0.003, "cost_out": 0.003,
            "max_tokens": 32768,
        },
        "doubao-pro-128k": {
            "name": "豆包 Pro 128K",
            "cost_in": 0.005, "cost_out": 0.005,
            "max_tokens": 131072,
        },
        "doubao-lite-32k": {
            "name": "豆包 Lite 32K",
            "cost_in": 0.0005, "cost_out": 0.0005,
            "max_tokens": 32768,
        },
        "doubao-lite-4k": {
            "name": "豆包 Lite 4K",
            "cost_in": 0.0003, "cost_out": 0.0003,
            "max_tokens": 4096,
        },
    }
    
    def __init__(
        self,
        api_key: str = "",
        model: str = "doubao-pro-32k",
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
        """发送对话请求到豆包 API"""
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
        
        # 额外参数
        if kwargs.get("top_p"):
            payload["top_p"] = kwargs["top_p"]
        
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
                
                data = response.json()
                
                if stream:
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
                else:
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                
                cost = self.calculate_cost(input_tokens, output_tokens)
                latency_ms = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"豆包 响应: {output_tokens} tokens, "
                    f"费用: ¥{cost:.6f}, 延迟: {latency_ms:.0f}ms"
                )
                
                return ModelResponse(
                    content=content,
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    raw_response=data
                )
                
        except Exception as e:
            logger.error(f"豆包 请求异常: {e}")
            return ModelResponse(
                content="",
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
