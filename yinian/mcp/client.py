"""
Yinian MCP Client - MCP 客户端实现

使 Yinian 可以连接到 MCP Servers 并调用其工具
"""
import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
    
    使用临时连接模式：每次调用创建新连接，
    避免复杂的异步生命周期管理问题。
    """
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or get_mcp_config()
    
    def _ensure_node_in_path(self):
        """确保 Node.js 在 PATH 中"""
        node_path = "C:\\Program Files\\nodejs"
        if node_path not in os.environ.get("PATH", ""):
            os.environ["PATH"] = node_path + os.pathsep + os.environ.get("PATH", "")
    
    async def _connect_and_call(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """内部方法：创建连接并调用工具"""
        
        server_config = self.config.get_server(server_name)
        if not server_config:
            return {"success": False, "error": f"服务器配置不存在: {server_name}"}
        
        if not server_config.enabled:
            return {"success": False, "error": f"服务器已禁用: {server_name}"}
        
        # 确保 Node.js 在 PATH 中
        self._ensure_node_in_path()
        
        try:
            params = StdioServerParameters(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env if server_config.env else None,
            )
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 调用工具
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
    
    async def connect(self, server_name: str) -> bool:
        """连接到 MCP 服务器并返回工具列表"""
        
        server_config = self.config.get_server(server_name)
        if not server_config:
            logger.error(f"服务器配置不存在: {server_name}")
            return False
        
        if not server_config.enabled:
            logger.warning(f"服务器已禁用: {server_name}")
            return False
        
        self._ensure_node_in_path()
        
        try:
            params = StdioServerParameters(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env if server_config.env else None,
            )
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()
                    
                    logger.info(
                        f"MCP 服务器 {server_name} 已连接，发现 {len(tools_response.tools)} 个工具"
                    )
                    return True
                    
        except Exception as e:
            logger.error(f"连接 MCP 服务器 {server_name} 失败: {e}")
            return False
    
    async def list_tools(self, server_name: str) -> List[MCPToolInfo]:
        """获取服务器的工具列表"""
        
        server_config = self.config.get_server(server_name)
        if not server_config:
            return []
        
        self._ensure_node_in_path()
        
        try:
            params = StdioServerParameters(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env if server_config.env else None,
            )
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()
                    
                    return [
                        MCPToolInfo(
                            name=tool.name,
                            description=tool.description or "",
                            input_schema=tool.inputSchema or {},
                            server_name=server_name,
                        )
                        for tool in tools_response.tools
                    ]
                    
        except Exception as e:
            logger.error(f"获取工具列表失败: {e}")
            return []
    
    async def disconnect(self, server_name: str) -> bool:
        """断开连接（临时连接模式下无操作）"""
        return True
    
    async def disconnect_all(self) -> None:
        """断开所有连接（临时连接模式下无操作）"""
        pass
    
    def list_tools_sync(self, server_name: str) -> List[MCPToolInfo]:
        """同步版本：获取工具列表"""
        return asyncio.run(self.list_tools(server_name))
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        注意：这个方法需要知道工具属于哪个服务器。
        目前需要通过其他方式确定服务器名称。
        """
        # 简化版本：尝试每个已启用的服务器
        servers = self.config.list_servers(enabled_only=True)
        
        for server_name in servers:
            result = await self._connect_and_call(server_name, tool_name, arguments)
            if result["success"]:
                return result
        
        return {
            "success": False,
            "tool": tool_name,
            "error": "工具不存在或所有服务器均不可用"
        }
    
    async def call_tool_on_server(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """在指定服务器上调用工具"""
        return await self._connect_and_call(server_name, tool_name, arguments)
    
    def call_tool_sync(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """同步版本：在指定服务器上调用工具"""
        return asyncio.run(self._connect_and_call(server_name, tool_name, arguments))
    
    def get_status(self) -> Dict[str, Any]:
        """获取连接状态（临时模式总是返回未连接）"""
        return {
            "connected_servers": [],
            "total_tools": 0,
            "tools_by_server": {},
        }


# 全局单例
_mcp_client: Optional[YinianMCPClient] = None


def get_mcp_client() -> YinianMCPClient:
    """获取 MCP 客户端单例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = YinianMCPClient()
    return _mcp_client
