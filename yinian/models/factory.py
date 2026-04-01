"""
Model Factory - 模型工厂
"""
import threading
from typing import Dict, List, Optional, Type, Any

from yinian.core.config import Config, get_config
from yinian.models.base import BaseModel

from yinian.models.deepseek import DeepSeekModel
from yinian.models.kimi import KimiModel
from yinian.models.qwen import QwenModel
from yinian.models.wenxin import WenxinModel
from yinian.models.zhipu import ZhipuModel
from yinian.models.minimax import MiniMaxModel
from yinian.models.hunyuan import HunyuanModel
from yinian.models.doubao import DoubaoModel
from yinian.models.llama import LlamaModel
from yinian.models.deepseek_reasoner import DeepSeekReasonerModel


# 全局锁
_model_lock = threading.Lock()

# 模型注册表
MODEL_REGISTRY: Dict[str, Type[BaseModel]] = {
    "deepseek": DeepSeekModel,
    "deepseek-r1": DeepSeekReasonerModel,
    "kimi": KimiModel,
    "qwen": QwenModel,
    "wenxin": WenxinModel,
    "zhipu": ZhipuModel,
    "minimax": MiniMaxModel,
    "hunyuan": HunyuanModel,
    "doubao": DoubaoModel,
    "llama": LlamaModel,
}


class ModelFactory:
    """模型工厂"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self._cache: Dict[str, BaseModel] = {}
    
    def get_model(self, name: str) -> Optional[BaseModel]:
        """获取模型实例（带缓存）"""
        if name in self._cache:
            return self._cache[name]
        
        model_cls = MODEL_REGISTRY.get(name)
        if not model_cls:
            return None
        
        cfg = self.config.get_model_config(name)
        if not cfg:
            return None
        
        try:
            model = model_cls(
                api_key=cfg.get("api_key", ""),
                model=cfg.get("model", ""),
                base_url=cfg.get("base_url", ""),
                timeout=cfg.get("timeout", 60),
            )
            self._cache[name] = model
            return model
        except Exception:
            return None
    
    def list_models(self) -> List[str]:
        """列出所有注册的模型"""
        return list(MODEL_REGISTRY.keys())
    
    def list_enabled_models(self) -> List[str]:
        """列出所有已配置的模型（不看 API Key 是否存在，用于路由决策）"""
        enabled = []
        for name in self.list_models():
            cfg = self.config.get_model_config(name)
            if not cfg:
                continue
            # 本地模型（api_key="local"）也加入列表参与路由
            raw_key = cfg.get("api_key", "") or ""
            if raw_key.lower() == "local":
                continue  # 本地模型不加入云端路由池
            enabled.append(name)
        return enabled
    
    def get_model_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        if name not in self.list_models():
            return None
        cfg = self.config.get_model_config(name)
        if not cfg:
            return None
        
        model = self.get_model(name)
        # api_key 为 "local" 表示本地模型，不算有 API Key
        raw_key = cfg.get("api_key", "") or ""
        is_local = raw_key.lower() == "local"
        # has_key 只看配置文件，不依赖 model 对象是否创建成功
        has_key = bool(raw_key and not is_local)
        
        return {
            "name": cfg.get("name", name),
            "model_id": cfg.get("model", ""),
            "display_name": cfg.get("name", name),
            "has_api_key": has_key,
            "is_local": is_local,
            "cost_per_1k_input": cfg.get("cost_per_1k_input", 0),
            "cost_per_1k_output": cfg.get("cost_per_1k_output", 0),
        }
    
    def find_cheapest_enabled_model(self) -> Optional[str]:
        """查找费用最低的可用模型（已配置 API Key）"""
        candidates = []
        for name in self.list_enabled_models():
            info = self.get_model_info(name)
            if not info or not info["has_api_key"]:
                continue
            total = info["cost_per_1k_input"] + info["cost_per_1k_output"]
            candidates.append((total, name))
        
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    def find_cheapest_any_model(self) -> Optional[str]:
        """查找费用最低的任意模型（不考虑 API Key）"""
        candidates = []
        for name in self.list_models():
            cfg = self.config.get_model_config(name)
            if not cfg:
                continue
            total = cfg.get("cost_per_1k_input", 0) + cfg.get("cost_per_1k_output", 0)
            candidates.append((total, name))
        
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]


# 全局单例
_factory: Optional[ModelFactory] = None


def get_factory() -> ModelFactory:
    """获取模型工厂单例"""
    global _factory
    if _factory is None:
        with _model_lock:
            if _factory is None:
                _factory = ModelFactory()
    return _factory
