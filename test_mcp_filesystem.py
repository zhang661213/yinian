"""
MCP Filesystem Server 测试脚本
"""
import asyncio
import sys

# 确保 Node.js 在 PATH 中
import os
os.environ["PATH"] = "C:\\Program Files\\nodejs;" + os.environ.get("PATH", "")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_filesystem_server():
    """测试连接 Filesystem MCP Server"""
    
    # 创建服务器参数
    params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "E:\\AI\\airc"],
    )
    
    print("正在连接 MCP Filesystem Server...")
    
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                # 初始化
                print("初始化中...")
                await session.initialize()
                print("✓ 初始化成功")
                
                # 获取工具列表
                print("\n获取工具列表...")
                tools_response = await session.list_tools()
                print(f"✓ 发现 {len(tools_response.tools)} 个工具:\n")
                
                for tool in tools_response.tools:
                    print(f"  📄 {tool.name}")
                    if tool.description:
                        print(f"      {tool.description[:60]}...")
                
                # 测试读取目录
                print("\n测试列出目录...")
                result = await session.call_tool(
                    "list_directory",
                    {"path": "E:\\AI\\airc"}
                )
                
                print(f"\n✓ 目录列表结果:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(content.text[:500])
                
                # 测试读取文件
                print("\n测试读取文件...")
                result = await session.call_tool(
                    "read_file",
                    {"path": "E:\\AI\\airc\\README.md"}
                )
                
                print(f"\n✓ README.md 内容 (前200字符):")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(content.text[:200])
                
                print("\n✅ Filesystem MCP Server 测试成功!")
                return True
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_filesystem_server())
    sys.exit(0 if success else 1)
