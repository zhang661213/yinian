"""
MCP 配置管理
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from loguru import logger

from yinian.core.config import get_config


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    description: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerConfig":
        return cls(
            name=data["name"],
            command=data["command"],
            args=data.get("args", []),
            env=data.get("env", {}),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "enabled": self.enabled,
            "description": self.description,
        }


class MCPConfig:
    """MCP 配置管理"""
    
    DEFAULT_SERVERS: Dict[str, Dict[str, Any]] = {
        "filesystem": {
            "name": "filesystem",
            "command": "npx",
            "args": [
                "-y", "@modelcontextprotocol/server-filesystem",
                "E:\\AI\\airc",  # 项目目录
                "C:\\Users\\Public",  # 公共目录
            ],
            "description": "本地文件系统访问",
            "enabled": True,
        },
        "git": {
            "name": "git",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-git"],
            "description": "Git 操作支持",
            "enabled": False,
        },
        "github": {
            "name": "github",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "description": "GitHub API 访问",
            "enabled": False,
        },
    }
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config = get_config()
        self.config_dir = config_dir or (self.config.config_dir / "mcp")
        self.config_file = self.config_dir / "servers.json"
        self._servers: Dict[str, MCPServerConfig] = {}
        self._load()
    
    def _load(self) -> None:
        """加载配置"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.config_file.exists():
            self._create_default_config()
        
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._servers = {}
            for name, server_data in data.items():
                self._servers[name] = MCPServerConfig.from_dict(server_data)
            
            logger.debug(f"已加载 {len(self._servers)} 个 MCP 服务器配置")
        except Exception as e:
            logger.error(f"加载 MCP 配置失败: {e}")
            self._servers = {}
    
    def _create_default_config(self) -> None:
        """创建默认配置"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.DEFAULT_SERVERS, f, indent=2, ensure_ascii=False)
        logger.info(f"已创建默认 MCP 配置: {self.config_file}")
    
    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """获取服务器配置"""
        return self._servers.get(name)
    
    def list_servers(self, enabled_only: bool = False) -> Dict[str, MCPServerConfig]:
        """列出所有服务器"""
        if enabled_only:
            return {k: v for k, v in self._servers.items() if v.enabled}
        return self._servers.copy()
    
    def add_server(self, name: str, config: MCPServerConfig) -> bool:
        """添加服务器"""
        try:
            self._servers[name] = config
            self._save()
            logger.info(f"已添加 MCP 服务器: {name}")
            return True
        except Exception as e:
            logger.error(f"添加 MCP 服务器失败: {e}")
            return False
    
    def remove_server(self, name: str) -> bool:
        """移除服务器"""
        if name in self._servers:
            del self._servers[name]
            self._save()
            logger.info(f"已移除 MCP 服务器: {name}")
            return True
        return False
    
    def enable_server(self, name: str) -> bool:
        """启用服务器"""
        if name in self._servers:
            self._servers[name].enabled = True
            self._save()
            return True
        return False
    
    def disable_server(self, name: str) -> bool:
        """禁用服务器"""
        if name in self._servers:
            self._servers[name].enabled = False
            self._save()
            return True
        return False
    
    def _save(self) -> None:
        """保存配置"""
        data = {k: v.to_dict() for k, v in self._servers.items()}
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# 全局单例
_mcp_config: Optional[MCPConfig] = None


def get_mcp_config() -> MCPConfig:
    """获取 MCP 配置单例"""
    global _mcp_config
    if _mcp_config is None:
        _mcp_config = MCPConfig()
    return _mcp_config
