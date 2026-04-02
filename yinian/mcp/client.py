"""
Yinian MCP Client - MCP 客户端实现

使 Yinian 可以连接到 MCP Servers 并调用其工具
"""
import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Awaitable
from enum import Enum

from loguru import logger

try:
    import mcp
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool as MCPTool, TextContent as MCPToolContent
except ImportError:
    raise ImportError(
        "MCP SDK 未安装。请运行: pip install mcp"
    )

from yinian.mcp.config import MCPConfig, get_mcp_config, MCPServerConfig


@dataclass
class MCPToolInfo:
    """MCP 工具信息"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "server": self.server_name,
        }


class YinianMCPClient:
    """
    Yinian MCP 客户端
    
    负责：
    1. 连接到 MCP 服务器
    2. 发现可用工具
    3. 调用工具
    4. 管理连接生命周期
    """
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or get_mcp_config()
        self._sessions: Dict[str, ClientSession] = {}
        self._tools: Dict[str, MCPToolInfo] = {}  # tool_name -> info
        self._connected: Dict[str, bool] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, server_name: str) -> bool:
        """
        连接到 MCP 服务器
        
        Args:
            server_name: 服务器名称
            
        Returns:
            是否连接成功
        """
        async with self._lock:
            if server_name in self._sessions:
                logger.debug(f"MCP 服务器 {server_name} 已连接")
                return True
            
            server_config = self.config.get_server(server_name)
            if not server_config:
                logger.error(f"MCP 服务器配置不存在: {server_name}")
                return False
            
            if not server_config.enabled:
                logger.warning(f"MCP 服务器已禁用: {server_name}")
                return False
            
            try:
                logger.info(f"正在连接 MCP 服务器: {server_name}")
                
                # 创建服务器参数
                params = StdioServerParameters(
                    command=server_config.command,
                    args=server_config.args,
                    env=server_config.env if server_config.env else None,
                )
                
                # 连接
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        # 初始化
                        await session.initialize()
                        
                        # 获取工具列表
                        tools_response = await session.list_tools()
                        
                        # 存储 session
                        self._sessions[server_name] = session
                        self._connected[server_name] = True
                        
                        # 注册工具
                        for tool in tools_response.tools:
                            tool_info = MCPToolInfo(
                                name=tool.name,
                                description=tool.description or "",
                                input_schema=tool.inputSchema or {},
                                server_name=server_name,
                            )
                            self._tools[tool.name] = tool_info
                        
                        logger.info(
                            f"MCP 服务器 {server_name} 已连接，发现 {len(tools_response.tools)} 个工具"
                        )
                        return True
                        
            except Exception as e:
                logger.error(f"连接 MCP 服务器 {server_name} 失败: {e}")
                return False
    
    async def disconnect(self, server_name: str) -> bool:
        """断开 MCP 服务器连接"""
        async with self._lock:
            if server_name in self._sessions:
                try:
                    del self._sessions[server_name]
                    self._connected[server_name] = False
                    
                    # 移除该服务器的工县
                    self._tools = {
                        k: v for k, v in self._tools.items()
                        if v.server_name != server_name
                    }
                    
                    logger.info(f"已断开 MCP 服务器: {server_name}")
                    return True
                except Exception as e:
                    logger.error(f"断开 MCP 服务器 {server_name} 失败: {e}")
                    return False
            return False
    
    async def connect_all(self) -> Dict[str, bool]:
        """连接所有已启用的服务器"""
        results = {}
        servers = self.config.list_servers(enabled_only=True)
        
        for name in servers:
            results[name] = await self.connect(name)
        
        return results
    
    async def disconnect_all(self) -> None:
        """断开所有服务器连接"""
        async with self._lock:
            for name in list(self._sessions.keys()):
                await self.disconnect(name)
    
    def list_tools(self, server_name: Optional[str] = None) -> List[MCPToolInfo]:
        """
        列出可用工具
        
        Args:
            server_name: 可选，筛选特定服务器的工具
            
        Returns:
            工具信息列表
        """
        if server_name:
            return [t for t in self._tools.values() if t.server_name == server_name]
        return list(self._tools.values())
    
    def get_tool(self, tool_name: str) -> Optional[MCPToolInfo]:
        """获取工具信息"""
        return self._tools.get(tool_name)
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        tool_info = self._tools.get(tool_name)
        if not tool_info:
            return {
                "success": False,
                "error": f"工具不存在: {tool_name}"
            }
        
        server_name = tool_info.server_name
        if server_name not in self._sessions:
            # 尝试连接
            connected = await self.connect(server_name)
            if not connected:
                return {
                    "success": False,
                    "error": f"无法连接到服务器: {server_name}"
                }
        
        try:
            session = self._sessions[server_name]
            
            logger.debug(f"调用 MCP 工具: {tool_name}({arguments})")
            
            result = await session.call_tool(tool_name, arguments)
            
            # 解析结果
            contents = []
            for content in result.content:
                if isinstance(content, MCPToolContent):
                    contents.append({
                        "type": content.type,
                        "text": content.text,
                    })
                else:
                    contents.append(str(content))
            
            return {
                "success": True,
                "tool": tool_name,
                "server": server_name,
                "result": contents,
            }
            
        except Exception as e:
            logger.error(f"调用 MCP 工具 {tool_name} 失败: {e}")
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
            }
    
    @property
    def is_connected(self) -> bool:
        """检查是否有活跃连接"""
        return any(self._connected.values())
    
    def get_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return {
            "connected_servers": list(self._sessions.keys()),
            "total_tools": len(self._tools),
            "tools_by_server": {
                name: len([t for t in self._tools.values() if t.server_name == name])
                for name in self._sessions.keys()
            },
        }


# 全局单例
_mcp_client: Optional[YinianMCPClient] = None


def get_mcp_client() -> YinianMCPClient:
    """获取 MCP 客户端单例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = YinianMCPClient()
    return _mcp_client
