"""
Yinian 模型工厂
负责模型的创建、管理和路由
"""
from typing import Dict, List, Optional, Type

from loguru import logger

from yinian.core.config import Config, get_config
from yinian.models.base import BaseModel, ModelResponse
from yinian.models.deepseek import DeepSeekModel
from yinian.models.kimi import KimiModel
from yinian.models.qwen import QwenModel


# 模型注册表
MODEL_REGISTRY: Dict[str, Type[BaseModel]] = {
    "deepseek": DeepSeekModel,
    "kimi": KimiModel,
    "qwen": QwenModel,
}


class ModelFactory:
    """模型工厂类"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self._models: Dict[str, BaseModel] = {}
    
    def list_models(self) -> List[str]:
        """列出所有可用的模型"""
        return list(MODEL_REGISTRY.keys())
    
    def list_enabled_models(self) -> List[str]:
        """列出所有已启用且已配置 API Key 的模型"""
        enabled = []
        for name in MODEL_REGISTRY.keys():
            model_cfg = self.config.get_model_config(name)
            if model_cfg and model_cfg.get("enabled", True):
                api_key = self.config.get_api_key(name)
                if api_key:
                    enabled.append(name)
        return enabled
    
    def get_model(self, name: str) -> Optional[BaseModel]:
        """
        获取模型实例（带缓存）
        
        Args:
            name: 模型名称 (deepseek, kimi, qwen)
            
        Returns:
            BaseModel: 模型实例，如果未注册或未启用则返回 None
        """
        # 检查是否在注册表中
        if name not in MODEL_REGISTRY:
            logger.error(f"未知模型: {name}")
            return None
        
        # 检查是否已缓存
        if name in self._models:
            return self._models[name]
        
        # 检查配置
        model_cfg = self.config.get_model_config(name)
        if not model_cfg:
            logger.error(f"模型 {name} 未在配置中找到")
            return None
        
        if not model_cfg.get("enabled", True):
            logger.error(f"模型 {name} 已禁用")
            return None
        
        api_key = self.config.get_api_key(name)
        if not api_key:
            logger.warning(f"模型 {name} 未设置 API Key")
            # 返回实例但不包含 API Key
            model_class = MODEL_REGISTRY[name]
            model = model_class(api_key="")
            self._models[name] = model
            return model
        
        # 创建模型实例
        model_class = MODEL_REGISTRY[name]
        model = model_class(
            api_key=api_key,
            base_url=model_cfg.get("base_url", ""),
            model=model_cfg.get("model", ""),
            cost_per_1k_input=model_cfg.get("cost_per_1k_input", 0),
            cost_per_1k_output=model_cfg.get("cost_per_1k_output", 0),
            max_tokens=model_cfg.get("max_tokens", 4096),
            timeout=model_cfg.get("timeout", 60),
        )
        
        self._models[name] = model
        logger.debug(f"创建模型实例: {name}")
        
        return model
    
    def create_model(self, name: str) -> Optional[BaseModel]:
        """
        创建新的模型实例（不使用缓存）
        
        Args:
            name: 模型名称
            
        Returns:
            BaseModel: 新模型实例
        """
        if name not in MODEL_REGISTRY:
            return None
        
        model_cfg = self.config.get_model_config(name)
        if not model_cfg:
            return None
        
        api_key = self.config.get_api_key(name)
        
        model_class = MODEL_REGISTRY[name]
        return model_class(
            api_key=api_key or "",
            base_url=model_cfg.get("base_url", ""),
            model=model_cfg.get("model", ""),
        )
    
    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有已配置模型的状态"""
        results = {}
        
        for name in MODEL_REGISTRY.keys():
            model = self.get_model(name)
            if model and self.config.get_api_key(name):
                results[name] = await model.health_check()
            else:
                results[name] = False
        
        return results
    
    def clear_cache(self) -> None:
        """清除模型缓存"""
        self._models.clear()
        logger.debug("模型缓存已清除")
    
    def get_model_info(self, name: str) -> Optional[Dict]:
        """获取模型信息"""
        if name not in MODEL_REGISTRY:
            return None
        
        model_cfg = self.config.get_model_config(name)
        if not model_cfg:
            return None
        
        model_class = MODEL_REGISTRY[name]
        
        return {
            "name": name,
            "display_name": model_class.display_name,
            "model_id": model_cfg.get("model", ""),
            "enabled": model_cfg.get("enabled", True),
            "has_api_key": bool(self.config.get_api_key(name)),
            "cost_per_1k_input": model_cfg.get("cost_per_1k_input", 0),
            "cost_per_1k_output": model_cfg.get("cost_per_1k_output", 0),
            "max_tokens": model_cfg.get("max_tokens", 4096),
        }
    
    def get_all_models_info(self) -> List[Dict]:
        """获取所有模型的信息"""
        return [
            self.get_model_info(name)
            for name in MODEL_REGISTRY.keys()
            if self.get_model_info(name) is not None
        ]
    
    def __repr__(self) -> str:
        return f"<ModelFactory models={list(self._models.keys())}>"


# 全局工厂实例
_factory: Optional[ModelFactory] = None


def get_factory() -> ModelFactory:
    """获取全局模型工厂实例"""
    global _factory
    if _factory is None:
        _factory = ModelFactory()
    return _factory
