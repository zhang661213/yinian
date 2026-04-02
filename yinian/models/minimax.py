"""
MiniMax 模型适配器
"""
import json
import time
from typing import Any, Dict, List, Optional

from yinian.models.base import BaseModel, ModelResponse, StreamChunk

from loguru import logger


class MiniMaxModel(BaseModel):
    """MiniMax 模型适配器"""
    
    model_name = "minimax"
    display_name = "MiniMax"
    base_url = "https://api.minimax.chat/v1"  # MiniMax API v1 版本
    model_id = "abab6.5s-chat"
    cost_per_1k_input = 0.01
    cost_per_1k_output = 0.01
    max_tokens = 16384
    timeout = 60
    
    # 支持的模型 (包括 M2.7)
    SUPPORTED_MODELS = {
        "abab6.5s-chat": {"name": "ABAB 6.5S", "cost_in": 0.01, "cost_out": 0.01, "max_tokens": 16384},
        "abab6.5-chat": {"name": "ABAB 6.5", "cost_in": 0.015, "cost_out": 0.015, "max_tokens": 16384},
        "abab5.5-chat": {"name": "ABAB 5.5", "cost_in": 0.005, "cost_out": 0.005, "max_tokens": 16384},
        "M2.7": {"name": "M2.7", "cost_in": 0.01, "cost_out": 0.01, "max_tokens": 16384},
        "MiniMax-M2.7": {"name": "MiniMax-M2.7", "cost_in": 0.01, "cost_out": 0.01, "max_tokens": 16384},
        "MiniMax-M2.7-highspeed": {"name": "M2.7 高速", "cost_in": 0.01, "cost_out": 0.01, "max_tokens": 16384},
        "MiniMax-M2.5": {"name": "MiniMax-M2.5", "cost_in": 0.01, "cost_out": 0.01, "max_tokens": 16384},
        "MiniMax-M2.5-highspeed": {"name": "M2.5 高速", "cost_in": 0.01, "cost_out": 0.01, "max_tokens": 16384},
        "MiniMax-Text-01": {"name": "Text-01", "cost_in": 0.01, "cost_out": 0.01, "max_tokens": 16384},
        "abab6.5g-chat": {"name": "ABAB 6.5G", "cost_in": 0.01, "cost_out": 0.01, "max_tokens": 16384},
    }
    
    def __init__(
        self,
        api_key: str = "",
        group_id: str = "",
        model: str = "abab6.5s-chat",
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.model_id = model or self.model_id
        self.api_key = api_key
        self.group_id = group_id
        
        # 如果模型名不在列表中，尝试匹配
        if self.model_id not in self.SUPPORTED_MODELS:
            for key in self.SUPPORTED_MODELS:
                if key.lower() in self.model_id.lower() or self.model_id.lower() in key.lower():
                    self.model_id = key
                    break
        
        if self.model_id in self.SUPPORTED_MODELS:
            cfg = self.SUPPORTED_MODELS[self.model_id]
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
        """发送对话请求到 MiniMax API"""
        start_time = time.time()
        
        url = f"{self.base_url}/text/chatcompletion_v2"
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
            payload["tokens_to_generate"] = max_tokens
        else:
            payload["tokens_to_generate"] = self.max_tokens
        
        # 额外参数
        if kwargs.get("top_p"):
            payload["top_p"] = kwargs["top_p"]
        if kwargs.get("request_id"):
            payload["request_id"] = kwargs["request_id"]
        
        try:
            async with self.client as client:
                logger.debug(f"MiniMax 请求 URL: {url}")
                
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"MiniMax 错误响应: {error_msg}")
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("base_resp", {}).get("error_msg", error_msg)
                    except:
                        pass
                    return ModelResponse(
                        content="",
                        model=self.model_name,
                        error=f"API错误 ({response.status_code}): {error_msg}",
                        latency_ms=(time.time() - start_time) * 1000
                    )
                
                # 判断是否流式响应（content-type 包含 event-stream）
                content_type = response.headers.get("content-type", "")
                is_streaming = "text/event-stream" in content_type
                
                if is_streaming:
                    # 流式响应解析
                    content = ""
                    # 记录真实 usage（从最后一个 chunk 获取）
                    usage_info = {}
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
                                if not choices:
                                    continue
                                
                                # 如果有 finish_reason=stop，这是最终 chunk，提取真实 usage
                                finish_reason = choices[0].get("finish_reason", "")
                                if finish_reason == "stop":
                                    usage_info = chunk.get("usage", {})
                                    msg = choices[0].get("message", {})
                                    if msg and msg.get("content"):
                                        content = msg.get("content", "")
                                        continue
                                
                                # 否则取 delta.content（增量流式）
                                delta = choices[0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    content += text
                                    
                            except json.JSONDecodeError:
                                continue
                            except Exception:
                                continue
                    
                    # 优先用真实 usage，否则估算
                    if usage_info:
                        input_tokens = usage_info.get("prompt_tokens", 0)
                        output_tokens = usage_info.get("completion_tokens", 0)
                        total_tokens = usage_info.get("total_tokens", 0)
                        logger.debug(
                            f"MiniMax 真实 usage: prompt={input_tokens}, "
                            f"completion={output_tokens}, total={total_tokens}"
                        )
                    else:
                        input_tokens = self.count_tokens("\n".join([m.get("content", "") for m in messages]))
                        output_tokens = self.count_tokens(content)
                        total_tokens = input_tokens + output_tokens
                    
                    cost = self.calculate_cost(input_tokens, output_tokens)
                    latency_ms = (time.time() - start_time) * 1000
                    
                    logger.debug(f"MiniMax 响应完成: {output_tokens} tokens")
                    return ModelResponse(
                        content=content,
                        model=self.model_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                        cost=cost,
                        latency_ms=latency_ms,
                    )
                
                # 非流式响应 - JSON 解析
                data = response.json()
                logger.debug(f"MiniMax 响应数据: {data}")
                
                # 检查 API 错误
                base_resp = data.get("base_resp", {})
                if base_resp.get("status_code"):
                    error_code = base_resp.get("status_code")
                    error_msg = base_resp.get("status_msg", "Unknown error")
                    return ModelResponse(
                        content="",
                        model=self.model_name,
                        error=f"MiniMax 错误 ({error_code}): {error_msg}",
                        latency_ms=(time.time() - start_time) * 1000
                    )
                
                # 提取真实 usage
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                # 提取内容
                choices = data.get("choices", [{}])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content", "") if msg else ""
                else:
                    content = ""
                
                # 如果 usage 为空则估算
                if not input_tokens:
                    input_tokens = self.count_tokens("\n".join([m.get("content", "") for m in messages]))
                if not output_tokens:
                    output_tokens = self.count_tokens(content)
                if not total_tokens:
                    total_tokens = input_tokens + output_tokens
                
                cost = self.calculate_cost(input_tokens, output_tokens)
                latency_ms = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"MiniMax 响应: {output_tokens} tokens, "
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
            logger.error(f"MiniMax 请求异常: {e}")
            return ModelResponse(
                content="",
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
