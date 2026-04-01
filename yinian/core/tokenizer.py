"""
统一 Token 计数模块 v3
优先使用 tiktoken (o200k_base)，回退到 BPE 字符估算

o200k_base 覆盖：OpenAI, DeepSeek, Qwen, Kimi, GLM, 豆包, 混元, MiniMax 等
Llama.cpp 本地模型：用字符估算（tokenizer 与 GGUF 模型相关，无法统一）
"""
import re
from typing import Optional, Dict, List

import tiktoken

# 全局编码器缓存
_ENCODER_CACHE: Dict[str, tiktoken.Encoding] = {}


# ─── 编码器映射 ──────────────────────────────────────────────────────────────

ENCODER_MAP: Dict[str, Optional[str]] = {
    # 用 tiktoken 的模型（o200k_base 对大多数国产模型都兼容）
    "deepseek": "o200k_base",
    "deepseek-r1": "o200k_base",
    "kimi": "o200k_base",
    "moonshot": "o200k_base",
    "qwen": "o200k_base",
    "qwen-turbo": "o200k_base",
    "qwen-plus": "o200k_base",
    "qwen-max": "o200k_base",
    "qwen3.5": "o200k_base",
    "zhipu": "o200k_base",
    "glm": "o200k_base",
    "hunyuan": "o200k_base",
    "doubao": "o200k_base",
    "minimax": "o200k_base",
    "wenxin": "o200k_base",
    "ernie": "o200k_base",
    # Llama.cpp 本地模型 — 无法用 tiktoken，用字符估算
    "llama": None,
}


def _get_encoder(name: str) -> Optional[tiktoken.Encoding]:
    """获取编码器，优先从缓存"""
    encoder_name = ENCODER_MAP.get(name)
    if encoder_name is None:
        return None  # 用字符估算
    
    if encoder_name in _ENCODER_CACHE:
        return _ENCODER_CACHE[encoder_name]
    
    try:
        enc = tiktoken.get_encoding(encoder_name)
        _ENCODER_CACHE[encoder_name] = enc
        return enc
    except Exception:
        return None


def _estimate_chars(text: str) -> int:
    """字符估算（Llama.cpp 等不支持 tiktoken 的模型用）"""
    if not text:
        return 0
    
    chinese_pat = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]+')
    english_pat = re.compile(r'[a-zA-Z]+')
    code_pat = re.compile(r'[(){}\[\];:,=<>+\-*\/%@#$^&|~`\\"\'_]+')
    digit_pat = re.compile(r'[0-9]+')
    
    chinese = ''.join(chinese_pat.findall(text))
    english_words = english_pat.findall(text)
    code_chars = len(''.join(code_pat.findall(text)))
    digit_chars = len(''.join(digit_pat.findall(text)))
    other_chars = len(text) - len(chinese) - len(''.join(english_words)) - code_chars - digit_chars
    
    # BPE 风格估算
    chinese_tokens = sum(max(1, len(chunk) // 2) for chunk in [chinese[i:i+3] for i in range(0, max(len(chinese), 1), 3)] or [''])
    english_tokens = sum(len(w) for w in english_words)
    
    return max(1, int(
        chinese_tokens * 0.5 +
        english_tokens * 0.75 +
        code_chars * 0.4 +
        digit_chars * 0.25 +
        other_chars * 0.15 +
        4  # overhead
    ))


def count_tokens(text: str, model_name: Optional[str] = None) -> int:
    """精确计算 token 数量"""
    if not text:
        return 0
    
    enc = None
    if model_name:
        # 精确匹配模型名
        enc = _get_encoder(model_name)
        if enc is None:
            # 模糊匹配
            for key in ENCODER_MAP:
                if key in model_name.lower():
                    enc = _get_encoder(key)
                    break
    
    if enc is None:
        # 默认用 o200k_base（最通用的）
        enc = _get_encoder("deepseek")
    
    if enc is not None:
        try:
            return len(enc.encode(text))
        except Exception:
            pass
    
    return _estimate_chars(text)


def count_messages_tokens(messages: List[dict], model_name: Optional[str] = None) -> int:
    """计算消息列表总 token 数（包含格式 overhead）"""
    if not messages:
        return 0
    
    total = 0
    for msg in messages:
        content = msg.get("content", "") or ""
        total += count_tokens(content, model_name)
        # role + 消息格式 overhead: ~4 tokens
        total += len(msg.get("role", "")) // 10 + 4
    
    return max(1, total)


def get_encoder_name(model_name: str) -> str:
    """获取编码器名称"""
    for key in ENCODER_MAP:
        if key in model_name.lower():
            enc = _get_encoder(key)
            if enc is not None:
                return f"tiktoken({key})"
            return f"估算({key})"
    return "tiktoken(o200k_base)"
