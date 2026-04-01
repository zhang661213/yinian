"""
Yinian 配置系统
负责配置目录、API Key、模型参数的管理
"""
import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib

try:
    import tomli_w  # Write TOML
    HAS_TOMLI_W = True
except ImportError:
    try:
        import toml as tomli_w  # Fallback
        HAS_TOMLI_W = True
    except ImportError:
        HAS_TOMLI_W = False

from loguru import logger

# 平台判断
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"


def get_config_dir() -> Path:
    """获取配置目录 ~/.yinian"""
    home = Path.home()
    
    if IS_WINDOWS:
        # Windows: C:\Users\<user>\.yinian
        config_dir = home / ".yinian"
    elif IS_MAC:
        # Mac: ~/.yinian
        config_dir = home / ".yinian"
    else:
        # Linux: ~/.config/yinian (遵循 XDG 标准)
        xdg_config = os.environ.get("XDG_CONFIG_HOME", home / ".config")
        config_dir = Path(xdg_config) / "yinian"
    
    return config_dir


def get_cache_dir() -> Path:
    """获取缓存目录 ~/.yinian/cache"""
    config_dir = get_config_dir()
    return config_dir / "cache"


def get_sessions_dir() -> Path:
    """获取会话目录 ~/.yinian/sessions"""
    config_dir = get_config_dir()
    return config_dir / "sessions"


def get_skills_dir() -> Path:
    """获取技能目录 ~/.yinian/skills"""
    config_dir = get_config_dir()
    return config_dir / "skills"


class Config:
    """Yinian 配置类"""
    
    DEFAULT_CONFIG = {
        "version": "0.1.0",
        "defaults": {
            "model": "deepseek",
            "fast_model": "deepseek",
            "best_model": "deepseek-r1",
            "stream": True,
            "color": True,
        },
        "models": {
            # ─── DeepSeek ───────────────────────────────────────────────
            "deepseek": {
                "name": "DeepSeek V3",
                "api_key": "",
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "cost_per_1k_input": 0.001,
                "cost_per_1k_output": 0.002,
                "max_tokens": 64000,
                "timeout": 60,
                "enabled": True,
            },
            "deepseek-r1": {
                "name": "DeepSeek R1 (推理)",
                "api_key": "",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-reasoner",
                "cost_per_1k_input": 0.001,
                "cost_per_1k_output": 0.004,
                "max_tokens": 64000,
                "timeout": 120,
                "enabled": True,
            },
            # ─── Kimi (Moonshot) ────────────────────────────────────────
            "kimi": {
                "name": "Kimi (Moonshot)",
                "api_key": "",
                "base_url": "https://api.moonshot.cn/v1",
                "model": "moonshot-v1-8k",
                "cost_per_1k_input": 0.012,
                "cost_per_1k_output": 0.012,
                "max_tokens": 8192,
                "timeout": 60,
                "enabled": True,
            },
            # ─── 阿里云通义千问 ──────────────────────────────────────────
            "qwen": {
                "name": "通义千问 Qwen",
                "api_key": "",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qwen3.5-flash",
                "cost_per_1k_input": 0.0002,
                "cost_per_1k_output": 0.002,
                "max_tokens": 8192,
                "timeout": 60,
                "enabled": True,
            },
            # ─── 百度文心一言 ────────────────────────────────────────────
            "wenxin": {
                "name": "文心一言 ERNIE",
                "api_key": "",
                "secret_key": "",
                "base_url": "https://qianfan.baidubce.com/v2",
                "model": "ernie-4.0-8k",
                "cost_per_1k_input": 0.012,
                "cost_per_1k_output": 0.024,
                "max_tokens": 8192,
                "timeout": 60,
                "enabled": True,
            },
            # ─── 智谱 GLM ───────────────────────────────────────────────
            "zhipu": {
                "name": "智谱 GLM",
                "api_key": "",
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "model": "glm-4-flash",
                "cost_per_1k_input": 0.0001,
                "cost_per_1k_output": 0.0001,
                "max_tokens": 128000,
                "timeout": 60,
                "enabled": True,
            },
            # ─── MiniMax ─────────────────────────────────────────────────
            # M2.7/M2.5/M2.1 采用 Token Plan 订阅制（¥29/49/119/月）
            # Starter=40次/5h, Plus=100次/5h, Max=300次/5h
            "minimax": {
                "name": "MiniMax M2.7",
                "api_key": "",
                "group_id": "",
                "base_url": "https://api.minimax.chat/v1",
                "model": "MiniMax-M2.7",
                "cost_per_1k_input": 0.0,    # 订阅制，按 prompts 计次
                "cost_per_1k_output": 0.0,
                "max_tokens": 16384,
                "timeout": 60,
                "enabled": True,
            },
            # ─── 腾讯混元 ────────────────────────────────────────────────
            "hunyuan": {
                "name": "腾讯混元 Hunyuan",
                "secret_id": "",
                "secret_key": "",
                "base_url": "https://hunyuan.cloud.tencent.com",
                "model": "hunyuan-latest",
                "cost_per_1k_input": 0.006,
                "cost_per_1k_output": 0.006,
                "max_tokens": 16384,
                "timeout": 60,
                "enabled": True,
            },
            # ─── 字节豆包 ────────────────────────────────────────────────
            "doubao": {
                "name": "字节豆包 Doubao",
                "api_key": "",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-pro-32k",
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.003,
                "max_tokens": 32768,
                "timeout": 60,
                "enabled": True,
            },
            # ─── Llama.cpp 本地 ─────────────────────────────────────────
            "llama": {
                "name": "Llama.cpp (本地)",
                "api_key": "",
                "base_url": "http://localhost:8080/v1",
                "model": "Qwen3.5-9B-Q4_K_M",
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "max_tokens": 4096,
                "timeout": 120,
                "enabled": True,
            },
        },
        "router": {
            "strategy": "auto",  # auto, cost, speed, quality
            "rules": {
                "code": "deepseek",      # 代码相关
                "math": "deepseek-r1",   # 数学推理 → 用 R1
                "chinese": "doubao",     # 中文内容（豆包便宜）
                "english": "qwen",       # 英文内容
                "quick": "deepseek",     # 快速问答
            }
        },
        "cache": {
            "enabled": True,
            "ttl_hours": 24,
            "max_size_mb": 100,
        },
        "budget": {
            "monthly_limit": 100.0,
            "alert_threshold": 0.8,
        },
    }
    
    def __init__(self):
        self.config_dir = get_config_dir()
        self.cache_dir = get_cache_dir()
        self.sessions_dir = get_sessions_dir()
        self.skills_dir = get_skills_dir()
        self.config_file = self.config_dir / "config.toml"
        
        self._config: Dict[str, Any] = {}
        self._ensure_dirs()
        self._load()
    
    def _ensure_dirs(self) -> None:
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"配置目录: {self.config_dir}")
    
    def _load(self) -> None:
        """加载配置文件"""
        json_file = self.config_file.with_suffix('.json')
        
        # 优先加载 JSON 格式
        if json_file.exists():
            try:
                import json
                with open(json_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                logger.info(f"配置已加载: {json_file}")
                return
            except Exception as e:
                logger.warning(f"JSON配置加载失败: {e}")
        
        # 回退到 TOML 格式
        if self.config_file.exists():
            try:
                with open(self.config_file, "rb") as f:
                    self._config = tomllib.load(f)
                logger.info(f"配置已加载: {self.config_file}")
            except Exception as e:
                logger.error(f"配置加载失败: {e}")
                self._config = self.DEFAULT_CONFIG.copy()
                self._save()
        else:
            logger.info("配置文件不存在，使用默认配置")
            self._config = self.DEFAULT_CONFIG.copy()
            self._save()
    
    def _save(self) -> None:
        """保存配置文件"""
        try:
            import json
            # 使用 JSON 格式保存（简单可靠）
            with open(self.config_file.with_suffix('.json'), "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.debug(f"配置已保存: {self.config_file}")
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            # 回退到手动 TOML 格式
            try:
                with open(self.config_file, "w", encoding="utf-8") as f:
                    f.write(self._dict_to_toml(self._config, 0))
                logger.debug(f"配置已保存(TOML格式): {self.config_file}")
            except Exception as e2:
                logger.error(f"TOML保存也失败: {e2}")
    
    def _dict_to_toml(self, data: Dict, indent: int = 0) -> str:
        """字典转 TOML 格式字符串"""
        lines = []
        prefix = "  " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}[{key}]")
                lines.append(self._dict_to_toml(value, indent + 1))
            else:
                if isinstance(value, str):
                    # 转义字符串中的特殊字符
                    value_escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                    lines.append(f"{prefix}{key} = \"{value_escaped}\"")
                elif isinstance(value, bool):
                    lines.append(f"{prefix}{key} = {'true' if value else 'false'}")
                elif isinstance(value, (int, float)):
                    lines.append(f"{prefix}{key} = {value}")
                elif value is None:
                    lines.append(f"{prefix}{key} = \"\"")
                else:
                    lines.append(f"{prefix}{key} = \"{value}\"")
        
        return "\n".join(lines) + "\n"
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径，如 'models.deepseek.api_key'"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值，支持点号分隔的路径"""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save()
    
    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取指定模型的配置"""
        return self.get(f"models.{model_name}")
    
    def list_models(self) -> list:
        """列出所有已配置的模型"""
        models = self.get("models", {})
        return [
            name for name, cfg in models.items()
            if cfg.get("enabled", True)
        ]
    
    def add_model(self, name: str, **kwargs) -> bool:
        """添加自定义模型配置
        
        Args:
            name: 模型标识名（如 my-openai）
            kwargs: 模型配置参数
                - display_name: 显示名称
                - api_key: API Key
                - base_url: API 地址
                - model: 模型名称
                - cost_per_1k_input: 输入费用
                - cost_per_1k_output: 输出费用
                - max_tokens: 最大 Token
                - timeout: 超时时间
        
        Returns:
            bool: 是否添加成功
        """
        models = self.get("models", {})
        
        # 检查是否已存在
        if name in models:
            logger.warning(f"模型 {name} 已存在，将更新配置")
        
        # 构建模型配置
        model_config = {
            "name": kwargs.get("display_name", name),
            "api_key": kwargs.get("api_key", ""),
            "base_url": kwargs.get("base_url", "https://api.openai.com/v1"),
            "model": kwargs.get("model", "gpt-3.5-turbo"),
            "cost_per_1k_input": kwargs.get("cost_per_1k_input", 0.001),
            "cost_per_1k_output": kwargs.get("cost_per_1k_output", 0.002),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "timeout": kwargs.get("timeout", 60),
            "enabled": kwargs.get("enabled", True),
            "custom": True,  # 标记为自定义模型
        }
        
        # 设置到配置
        self.set(f"models.{name}", model_config)
        logger.info(f"已添加模型: {name}")
        return True
    
    def remove_model(self, name: str) -> bool:
        """删除模型配置
        
        Args:
            name: 模型标识名
        
        Returns:
            bool: 是否删除成功
        """
        models = self.get("models", {})
        
        if name not in models:
            logger.warning(f"模型 {name} 不存在")
            return False
        
        # 删除配置
        del models[name]
        self._config["models"] = models
        self._save()
        logger.info(f"已删除模型: {name}")
        return True
    
    def update_model(self, name: str, **kwargs) -> bool:
        """更新模型配置
        
        Args:
            name: 模型标识名
            kwargs: 要更新的配置参数
        
        Returns:
            bool: 是否更新成功
        """
        models = self.get("models", {})
        
        if name not in models:
            logger.warning(f"模型 {name} 不存在")
            return False
        
        # 更新配置
        for key, value in kwargs.items():
            if key == "display_name":
                models[name]["name"] = value
            else:
                models[name][key] = value
        
        self._config["models"] = models
        self._save()
        logger.info(f"已更新模型: {name}")
        return True
    
    def get_default_model(self) -> str:
        """获取默认模型"""
        return self.get("defaults.model", "deepseek")
    
    def get_api_key(self, model_name: str) -> str:
        """获取模型的 API Key"""
        return self.get(f"models.{model_name}.api_key", "")
    
    def set_api_key(self, model_name: str, api_key: str) -> None:
        """设置模型的 API Key"""
        self.set(f"models.{model_name}.api_key", api_key)
        logger.info(f"已设置 {model_name} 的 API Key")
    
    def reload(self) -> None:
        """重新加载配置"""
        self._load()
    
    def reset(self) -> None:
        """重置为默认配置"""
        self._config = self.DEFAULT_CONFIG.copy()
        self._save()
        logger.info("配置已重置为默认值")
    
    def show(self) -> Dict[str, Any]:
        """返回配置（隐藏 API Key）"""
        config = self._config.copy()
        for model in config.get("models", {}).values():
            if "api_key" in model and model["api_key"]:
                model["api_key"] = self._mask_key(model["api_key"])
        return config
    
    @staticmethod
    def _mask_key(key: str) -> str:
        """隐藏 API Key 的中间部分"""
        if len(key) <= 8:
            return "***"
        return key[:4] + "***" + key[-4:]
    
    def __repr__(self) -> str:
        return f"<Config dir={self.config_dir}>"


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config
