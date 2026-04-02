"""
Yinian MCP - Model Context Protocol 支持模块

为 Yinian 提供 MCP 协议支持，使其可以连接 MCP Servers
"""
from yinian.mcp.client import YinianMCPClient, get_mcp_client
from yinian.mcp.config import MCPConfig, get_mcp_config

__all__ = ["YinianMCPClient", "get_mcp_client", "MCPConfig", "get_mcp_config"]
