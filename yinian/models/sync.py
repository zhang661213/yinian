"""
Yinian 模型同步功能
自动检测各家套餐支持的模型
"""
import asyncio
import httpx
from typing import Dict, List, Optional, Tuple

from loguru import logger

from yinian.core.config import get_config


# MiniMax 支持的模型列表（常见）
MINIMAX_MODELS = [
    ("abab6.5s-chat", "ABAB 6.5S"),
    ("abab6.5-chat", "ABAB 6.5"),
    ("abab5.5-chat", "ABAB 5.5"),
    ("abab6.5s-chat-32k", "ABAB 6.5S 32K"),
]

# DeepSeek 支持的模型
DEEPSEEK_MODELS = [
    ("deepseek-chat", "DeepSeek Chat"),
    ("deepseek-coder", "DeepSeek Coder"),
    ("deepseek-reasoner", "DeepSeek R1 (Reasoner)"),
]

# Kimi 支持的模型
KIMI_MODELS = [
    ("moonshot-v1-8k", "Kimi 8K"),
    ("moonshot-v1-32k", "Kimi 32K"),
    ("moonshot-v1-128k", "Kimi 128K"),
]

# 通义千问支持的模型
QWEN_MODELS = [
    ("qwen-turbo", "Qwen Turbo"),
    ("qwen-plus", "Qwen Plus"),
    ("qwen-max", "Qwen Max"),
    ("qwen-max-longcontext", "Qwen Max (长文本)"),
]


async def test_model_works(
    provider: str,
    model: str,
    api_key: str
) -> Tuple[bool, str]:
    """测试某个模型是否在用户套餐支持范围内"""
    
    test_messages = [{"role": "user", "content": "hi"}]
    
    if provider == "minimax":
        url = "https://api.minimax.chat/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": test_messages}
        
    elif provider == "deepseek":
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": test_messages}
        
    elif provider == "kimi":
        url = "https://api.moonshot.cn/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": test_messages}
        
    elif provider == "qwen":
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": test_messages}
        
    else:
        return False, f"未知提供商: {provider}"
    
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                return True, ""
            else:
                try:
                    error = response.json()
                    msg = error.get("error", {}).get("message", error.get("message", ""))
                except:
                    msg = response.text[:100]
                
                # 识别特定错误
                if "not support" in msg.lower() or "not supported" in msg.lower():
                    return False, "套餐不支持"
                if "invalid" in msg.lower() or "unauthorized" in msg.lower():
                    return False, "API Key 无效"
                return False, msg[:50]
                
    except httpx.ConnectError:
        return False, "连接失败"
    except Exception as e:
        return False, str(e)[:50]


async def sync_minimax(api_key: str) -> Tuple[bool, List[Tuple[str, str]], str]:
    """同步 MiniMax 模型"""
    working_models = []
    
    for model, name in MINIMAX_MODELS:
        works, error = await test_model_works("minimax", model, api_key)
        if works:
            working_models.append((model, name))
            logger.debug(f"MiniMax: {model} 可用")
        else:
            logger.debug(f"MiniMax: {model} 不可用 - {error}")
    
    if working_models:
        return True, working_models, ""
    else:
        return False, [], "未找到可用的模型"


async def sync_deepseek(api_key: str) -> Tuple[bool, List[Tuple[str, str]], str]:
    """同步 DeepSeek 模型"""
    working_models = []
    
    for model, name in DEEPSEEK_MODELS:
        works, error = await test_model_works("deepseek", model, api_key)
        if works:
            working_models.append((model, name))
    
    if working_models:
        return True, working_models, ""
    else:
        return False, [], "未找到可用的模型"


async def sync_kimi(api_key: str) -> Tuple[bool, List[Tuple[str, str]], str]:
    """同步 Kimi 模型"""
    working_models = []
    
    for model, name in KIMI_MODELS:
        works, error = await test_model_works("kimi", model, api_key)
        if works:
            working_models.append((model, name))
    
    if working_models:
        return True, working_models, ""
    else:
        return False, [], "未找到可用的模型"


async def sync_qwen(api_key: str) -> Tuple[bool, List[Tuple[str, str]], str]:
    """同步通义千问模型"""
    working_models = []
    
    for model, name in QWEN_MODELS:
        works, error = await test_model_works("qwen", model, api_key)
        if works:
            working_models.append((model, name))
    
    if working_models:
        return True, working_models, ""
    else:
        return False, [], "未找到可用的模型"


async def sync_provider(provider: str, api_key: str) -> Tuple[bool, List[Tuple[str, str]], str]:
    """同步指定提供商的模型"""
    if provider == "minimax":
        return await sync_minimax(api_key)
    elif provider == "deepseek":
        return await sync_deepseek(api_key)
    elif provider == "kimi":
        return await sync_kimi(api_key)
    elif provider == "qwen":
        return await sync_qwen(api_key)
    else:
        return False, [], f"不支持的提供商: {provider}"


async def sync_all(config) -> Dict[str, Tuple[bool, List[Tuple[str, str]], str]]:
    """同步所有已配置 API Key 的提供商"""
    results = {}
    providers = ["minimax", "deepseek", "kimi", "qwen"]
    
    for provider in providers:
        api_key = config.get_api_key(provider)
        if not api_key:
            results[provider] = (False, [], "API Key 未设置")
            continue
        
        success, models, error = await sync_provider(provider, api_key)
        results[provider] = (success, models, error)
    
    return results


def update_config_with_working_model(config, provider: str, model: str):
    """更新配置使用可用的模型"""
    if provider == "minimax":
        config.set("models.minimax.model", model)
    elif provider == "deepseek":
        config.set("models.deepseek.model", model)
    elif provider == "kimi":
        config.set("models.kimi.model", model)
    elif provider == "qwen":
        config.set("models.qwen.model", model)
