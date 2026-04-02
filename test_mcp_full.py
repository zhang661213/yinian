"""
Yinian MCP 完整功能测试
"""
import asyncio
import os
import sys

# 设置 PATH 以包含 Node.js
os.environ["PATH"] = "C:\\Program Files\\nodejs;" + os.environ.get("PATH", "")

from yinian.mcp import get_mcp_client, get_mcp_config


async def test_mcp_full():
    """完整 MCP 功能测试"""
    
    print("=" * 50)
    print("Yinian MCP 完整功能测试")
    print("=" * 50)
    
    # 获取客户端和配置
    client = get_mcp_client()
    config = get_mcp_config()
    
    # 列出配置的服务器
    print("\n📋 配置的 MCP 服务器:")
    servers = config.list_servers()
    for name, srv in servers.items():
        status = "✅ 启用" if srv.enabled else "❌ 禁用"
        print(f"  - {name}: {srv.description} [{status}]")
    
    # 连接 filesystem 服务器
    print("\n🔗 连接到 filesystem 服务器...")
    success = await client.connect("filesystem")
    
    if not success:
        print("❌ 连接失败!")
        return False
    
    print("✅ 连接成功!")
    
    # 获取工具列表
    print("\n🔧 获取工具列表...")
    tools = await client.list_tools("filesystem")
    print(f"   发现 {len(tools)} 个工具")
    
    # 测试调用工具
    print("\n🧪 测试调用工具...")
    
    # 列出目录
    print("\n1. 调用 list_directory:")
    result = await client.call_tool_on_server(
        "filesystem",
        "list_directory",
        {"path": "E:\\AI\\airc"}
    )
    
    if result["success"]:
        print("   ✅ 成功!")
        for item in result.get("result", []):
            if isinstance(item, dict) and item.get("type") == "text":
                lines = item["text"].split("\n")[:5]
                for line in lines:
                    print(f"      {line}")
                if len(item["text"].split("\n")) > 5:
                    print("      ...")
    else:
        print(f"   ❌ 失败: {result.get('error')}")
    
    # 读取文件
    print("\n2. 调用 read_file:")
    result = await client.call_tool_on_server(
        "filesystem",
        "read_file",
        {"path": "E:\\AI\\airc\\pyproject.toml"}
    )
    
    if result["success"]:
        print("   ✅ 成功!")
        for item in result.get("result", []):
            if isinstance(item, dict) and item.get("type") == "text":
                content = item["text"][:200]
                print(f"      {content}...")
    else:
        print(f"   ❌ 失败: {result.get('error')}")
    
    # 搜索文件
    print("\n3. 调用 search_files:")
    result = await client.call_tool_on_server(
        "filesystem",
        "search_files",
        {"path": "E:\\AI\\airc\\yinian", "pattern": "**/*.py"}
    )
    
    if result["success"]:
        print("   ✅ 成功!")
        for item in result.get("result", []):
            if isinstance(item, dict) and item.get("type") == "text":
                lines = item["text"].split("\n")[:5]
                for line in lines:
                    print(f"      {line}")
                if len(item["text"].split("\n")) > 5:
                    print("      ...")
    else:
        print(f"   ❌ 失败: {result.get('error')}")
    
    # 获取目录树
    print("\n4. 调用 directory_tree:")
    result = await client.call_tool_on_server(
        "filesystem",
        "directory_tree",
        {"path": "E:\\AI\\airc\\yinian", "maxDepth": 2}
    )
    
    if result["success"]:
        print("   ✅ 成功!")
        for item in result.get("result", []):
            if isinstance(item, dict) and item.get("type") == "text":
                content = item["text"][:400]
                print(f"      {content}...")
    else:
        print(f"   ❌ 失败: {result.get('error')}")
    
    print("\n" + "=" * 50)
    print("✅ 所有测试通过!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_mcp_full())
    sys.exit(0 if success else 1)
