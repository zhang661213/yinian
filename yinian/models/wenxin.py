"""
文心一言 (Wenxin) 模型适配器
"""
import json
import time
from typing import Any, Dict, List, Optional

from yinian.models.base import BaseModel, ModelResponse, StreamChunk

from loguru import logger


class WenxinModel(BaseModel):
    """文心一言 (Wenxin) 模型适配器"""
    
    model_name = "wenxin"
    display_name = "文心一言"
    base_url = "https://qianfan.baidubce.com/v2"
    model_id = "ernie-bot"
    cost_per_1k_input = 0.012
    cost_per_1k_output = 0.012
    max_tokens = 8192
    timeout = 60
    
    # 支持的模型（2025年最新价格，数据来源：百度千帆官网）
    SUPPORTED_MODELS = {
        # ERNIE 4.0 系列
        "ernie-4.0-8k": {
            "name": "ERNIE 4.0 8K",
            "cost_in": 0.012, "cost_out": 0.024,
            "max_tokens": 8192,
        },
        "ernie-4.0-8k-128k": {
            "name": "ERNIE 4.0 128K",
            "cost_in": 0.004, "cost_out": 0.008,
            "max_tokens": 131072,
        },
        "ernie-4.0-8k-long": {
            "name": "ERNIE 4.0 长文本",
            "cost_in": 0.009, "cost_out": 0.018,
            "max_tokens": 28672,
        },
        # ERNIE Speed / Lite 系列
        "ernie-speed-8k": {
            "name": "ERNIE Speed 8K",
            "cost_in": 0.003, "cost_out": 0.006,
            "max_tokens": 8192,
        },
        "ernie-speed-lite": {
            "name": "ERNIE Speed Lite",
            "cost_in": 0.002, "cost_out": 0.004,
            "max_tokens": 8192,
        },
        # ERNIE 3.5（兼容旧版）
        "ernie-bot": {
            "name": "ERNIE 3.5 Bot",
            "cost_in": 0.008, "cost_out": 0.008,
            "max_tokens": 8192,
        },
    }
    
    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        model: str = "ernie-bot",
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.model_id = model or self.model_id
        self.api_key = api_key
        self.secret_key = secret_key
        self._access_token: Optional[str] = None
        self._access_token_expires_at: float = 0.0  # token 过期时间戳
        
        if model in self.SUPPORTED_MODELS:
            cfg = self.SUPPORTED_MODELS[model]
            self.cost_per_1k_input = cfg["cost_in"]
            self.cost_per_1k_output = cfg["cost_out"]
            self.max_tokens = cfg.get("max_tokens", 8192)
    
    async def _get_access_token(self) -> str:
        """获取 Access Token（百度需要），支持自动刷新过期 token"""
        import time as time_module
        
        # 如果有缓存且未过期，直接返回
        if self._access_token and time_module.time() < self._access_token_expires_at - 60:
            return self._access_token
        
        import base64
        
        # 构造 Basic Auth
        credentials = f"{self.api_key}:{self.secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        url = "https://qianfan.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }
        
        try:
            async with self.client as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access_token", "")
                    expires_in = data.get("expires_in", 0)
                    self._access_token_expires_at = time_module.time() + expires_in
                    return self._access_token
        except Exception as e:
            logger.error(f"获取 Access Token 失败: {e}")
        
        return ""
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """发送对话请求到文心一言 API"""
        start_time = time.time()
        
        access_token = await self._get_access_token()
        if not access_token:
            return ModelResponse(
                content="",
                model=self.model_name,
                error="无法获取 Access Token，请检查 API Key 和 Secret Key",
                latency_ms=(time.time() - start_time) * 1000
            )
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {access_token}",
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
                        error_msg = error_data.get("error_msg", error_msg)
                    except:
                        pass
                    return ModelResponse(
                        content="",
                        model=self.model_name,
                        error=f"API错误 ({response.status_code}): {error_msg}",
                        latency_ms=(time.time() - start_time) * 1000
                    )
                
                # 流式响应
                content_type = response.headers.get("content-type", "")
                is_streaming = "text/event-stream" in content_type or stream
                
                if is_streaming:
                    return await self._chat_stream_response(response, messages, start_time)
                
                # 非流式响应
                data = response.json()
                content = data.get("result", "")
                
                # 文心非流式有 usage 信息
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
            logger.error(f"文心一言 请求异常: {e}")
            return ModelResponse(
                content="",
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def _chat_stream_response(self, response, messages: List[Dict], start_time: float) -> ModelResponse:
        """解析文心 SSE 流式响应"""
        content = ""
        
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            # 文心 SSE 格式: data: {"choices": [{"messages": [{"role": "assistant", "content": "xxx"}]}]}
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    # 文心流式: choices[0].messages[-1].content
                    choices = chunk.get("choices", [{}])
                    if choices:
                        msgs = choices[0].get("messages", [])
                        if msgs and isinstance(msgs, list):
                            text = msgs[-1].get("content", "")
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
        
        logger.debug(f"文心流式响应: {output_tokens} tokens, 延迟: {latency_ms:.0f}ms")
        
        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            latency_ms=latency_ms,
        )
