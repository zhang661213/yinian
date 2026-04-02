"""
测试 MCP Filesystem Server 路径问题
"""
import asyncio
import os
import sys
import subprocess

# 设置 PATH
os.environ["PATH"] = "C:\\Program Files\\nodejs;" + os.environ.get("PATH", "")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_with_ascii_path():
    """使用纯 ASCII 路径测试"""
    
    # 使用一个没有中文和空格的路径
    test_path = "C:\\Users\\Public\\Documents"
    
    print(f"测试路径: {test_path}")
    
    params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", test_path],
    )
    
    print(f"参数: {params.args}")
    
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 列出工具
                tools = await session.list_tools()
                print(f"\n发现 {len(tools.tools)} 个工具")
                
                # 测试列出目录
                result = await session.call_tool("list_directory", {"path": test_path})
                
                print(f"\n调用结果:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(content.text[:300])
                        
                return True
                
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_with_ascii_path())
    sys.exit(0 if success else 1)
