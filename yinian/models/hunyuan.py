"""
腾讯混元 (Hunyuan) 模型适配器
"""
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from yinian.models.base import BaseModel, ModelResponse, StreamChunk

from loguru import logger


class HunyuanModel(BaseModel):
    """腾讯混元 (Hunyuan) 模型适配器"""
    
    model_name = "hunyuan"
    display_name = "腾讯混元"
    base_url = "https://hunyuan.cloud.tencent.com"
    model_id = "hunyuan-latest"
    cost_per_1k_input = 0.006
    cost_per_1k_output = 0.006
    max_tokens = 16384
    timeout = 60
    
    # 支持的模型
    SUPPORTED_MODELS = {
        "hunyuan-latest": {"name": "混元 Pro", "cost_in": 0.006, "cost_out": 0.006, "max_tokens": 16384},
        "hunyuan-standard": {"name": "混元标准版", "cost_in": 0.005, "cost_out": 0.005, "max_tokens": 16384},
        "hunyuan-code": {"name": "混元代码版", "cost_in": 0.008, "cost_out": 0.008, "max_tokens": 16384},
    }
    
    def __init__(
        self,
        secret_id: str = "",
        secret_key: str = "",
        model: str = "hunyuan-latest",
        **kwargs
    ):
        super().__init__("", **kwargs)
        self.model_id = model or self.model_id
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.api_key = secret_id  # 兼容
        
        if model in self.SUPPORTED_MODELS:
            cfg = self.SUPPORTED_MODELS[model]
            self.cost_per_1k_input = cfg["cost_in"]
            self.cost_per_1k_output = cfg["cost_out"]
            self.max_tokens = cfg["max_tokens"]
    
    def _generate_signature(self, payload: Dict[str, Any]) -> tuple:
        """生成腾讯云 API 签名（TC3-HMAC-SHA256）
        
        Args:
            payload: 请求体字典，用于计算 payload_hash
        """
        import base64
        
        # 获取当前时间戳
        timestamp = int(datetime.now().timestamp())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        # 签名算法
        canonical_uri = "/api/chat/completion"
        canonical_headers = f"content-type:application/json\nhost:hunyuan.cloud.tencent.com\n"
        signed_headers = "content-type;host"
        algorithm = "TC3-HMAC-SHA256"
        
        # 计算 payload 的 SHA256 哈希（关键修复！之前传的是 b"" 导致签名永远失败）
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        
        canonical_request = f"POST\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        credential_scope = f"{date}/tc3_request"
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        
        # 计算签名
        secret_date = self._hmac_sha256(f"TC3{self.secret_key}".encode(), date)
        secret_signing = self._hmac_sha256(secret_date, "tc3_request")
        signature = hmac.new(
            secret_signing,
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # 构造 Authorization
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        return authorization, timestamp
    
    def _hmac_sha256(self, key: bytes, msg: str) -> bytes:
        """HMAC-SHA256"""
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """发送对话请求到腾讯混元 API"""
        start_time = time.time()
        
        url = f"{self.base_url}/api/chat/completion"
        headers = {
            "Content-Type": "application/json",
            "Host": "hunyuan.cloud.tencent.com",
        }
        
        # 生成签名（需要先构建 payload 以便计算正确的 payload_hash）
        authorization, timestamp = self._generate_signature(payload)
        headers["Authorization"] = authorization
        headers["X-TC-Timestamp"] = str(timestamp)
        
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
                    f"腾讯混元 响应: {output_tokens} tokens, "
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
            logger.error(f"腾讯混元 请求异常: {e}")
            return ModelResponse(
                content="",
                model=self.model_name,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
