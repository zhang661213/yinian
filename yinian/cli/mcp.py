"""
Yinian MCP CLI - MCP 相关命令
"""
import asyncio
import json

import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from yinian.mcp import YinianMCPClient, MCPConfig
from yinian.mcp.config import get_mcp_config

console = Console()


@click.group(name="mcp")
def mcp_group():
    """🤝 MCP (Model Context Protocol) 管理命令"""
    pass


@mcp_group.command(name="list")
@click.option("--server", "-s", help="筛选特定服务器")
def list_tools(server: str = None):
    """📋 列出已连接的 MCP 服务器和可用工具"""
    client = get_mcp_client()
    
    # 获取状态
    status = client.get_status()
    
    console.print("\n[bold cyan]📡 MCP 连接状态[/bold cyan]\n")
    
    if not status["connected_servers"]:
        console.print("[yellow]没有已连接的 MCP 服务器[/yellow]")
        console.print("使用 [bold]yinian mcp connect <name>[/bold] 连接服务器")
        return
    
    # 显示服务器状态
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("服务器")
    table.add_column("工具数")
    
    for srv in status["connected_servers"]:
        tool_count = status["tools_by_server"].get(srv, 0)
        table.add_row(srv, str(tool_count))
    
    console.print(table)
    
    # 显示工具列表
    tools = client.list_tools(server)
    
    if tools:
        console.print(f"\n[bold cyan]🔧 可用工具 ({len(tools)})[/bold cyan]\n")
        
        for tool in tools:
            console.print(f"  [green]{tool.name}[/green] ({tool.server_name})")
            if tool.description:
                console.print(f"    {tool.description[:80]}...")


@mcp_group.command(name="connect")
@click.argument("server_name")
def connect_server(server_name: str):
    """🔗 连接到 MCP 服务器"""
    async def _connect():
        client = get_mcp_client()
        config = get_mcp_config()
        
        # 检查服务器是否存在
        srv_config = config.get_server(server_name)
        if not srv_config:
            console.print(f"[red]服务器不存在: {server_name}[/red]")
            console.print("\n可用服务器:")
            for name, srv in config.list_servers().items():
                console.print(f"  - {name}: {srv.description}")
            return
        
        console.print(f"正在连接到 [bold]{server_name}[/bold]...")
        
        success = await client.connect(server_name)
        
        if success:
            console.print(f"[green]✓ 连接成功: {server_name}[/green]")
        else:
            console.print(f"[red]✗ 连接失败: {server_name}[/red]")
    
    asyncio.run(_connect())


@mcp_group.command(name="disconnect")
@click.argument("server_name")
def disconnect_server(server_name: str):
    """🔌 断开 MCP 服务器连接"""
    async def _disconnect():
        client = get_mcp_client()
        success = await client.disconnect(server_name)
        
        if success:
            console.print(f"[green]✓ 已断开: {server_name}[/green]")
        else:
            console.print(f"[red]✗ 断开失败: {server_name}[/red]")
    
    asyncio.run(_disconnect())


@mcp_group.command(name="status")
def mcp_status():
    """📊 显示 MCP 连接状态"""
    client = get_mcp_client()
    status = client.get_status()
    
    console.print("\n[bold cyan]📊 MCP 状态[/bold cyan]\n")
    console.print(f"已连接服务器: [bold]{len(status['connected_servers'])}[/bold]")
    console.print(f"可用工具: [bold]{status['total_tools']}[/bold]")
    
    if status["connected_servers"]:
        console.print("\n已连接的服务器:")
        for srv in status["connected_servers"]:
            console.print(f"  - [green]{srv}[/green]")


@mcp_group.command(name="call")
@click.argument("tool_name")
@click.option("--args", "-a", default="{}", help="工具参数 (JSON 格式)")
def call_tool(tool_name: str, args: str):
    """🛠️ 调用 MCP 工具"""
    async def _call():
        client = get_mcp_client()
        
        # 解析参数
        try:
            arguments = json.loads(args)
        except json.JSONDecodeError:
            console.print("[red]参数必须是有效的 JSON[/red]")
            return
        
        # 检查工具是否存在
        tool_info = client.get_tool(tool_name)
        if not tool_info:
            console.print(f"[red]工具不存在: {tool_name}[/red]")
            console.print("\n可用工具:")
            for tool in client.list_tools():
                console.print(f"  - {tool.name}")
            return
        
        console.print(f"调用 [bold]{tool_name}[/bold]...")
        
        result = await client.call_tool(tool_name, arguments)
        
        if result["success"]:
            console.print("[green]✓ 调用成功[/green]\n")
            console.print("结果:")
            for item in result.get("result", []):
                if isinstance(item, dict) and item.get("type") == "text":
                    console.print(item["text"])
                else:
                    console.print(str(item))
        else:
            console.print(f"[red]✗ 调用失败: {result.get('error')}[/red]")
    
    asyncio.run(_call())


@mcp_group.command(name="add")
@click.argument("name")
@click.option("--command", "-c", required=True, help="启动命令")
@click.option("--args", "-a", default="", help="命令参数 (逗号分隔)")
@click.option("--desc", "-d", default="", help="描述")
def add_server(name: str, command: str, args: str, desc: str):
    """➕ 添加 MCP 服务器配置"""
    config = get_mcp_config()
    
    from yinian.mcp.config import MCPServerConfig
    
    server_config = MCPServerConfig(
        name=name,
        command=command,
        args=args.split(",") if args else [],
        description=desc,
        enabled=True,
    )
    
    if config.add_server(name, server_config):
        console.print(f"[green]✓ 已添加服务器: {name}[/green]")
    else:
        console.print(f"[red]✗ 添加失败[/red]")


@mcp_group.command(name="remove")
@click.argument("name")
def remove_server(name: str):
    """➖ 移除 MCP 服务器配置"""
    config = get_mcp_config()
    
    if config.remove_server(name):
        console.print(f"[green]✓ 已移除服务器: {name}[/green]")
    else:
        console.print(f"[red]✗ 移除失败或服务器不存在[/red]")


@mcp_group.command(name="enable")
@click.argument("name")
def enable_server(name: str):
    """✅ 启用 MCP 服务器"""
    config = get_mcp_config()
    
    if config.enable_server(name):
        console.print(f"[green]✓ 已启用: {name}[/green]")
    else:
        console.print(f"[red]✗ 启用失败[/red]")


@mcp_group.command(name="disable")
@click.argument("name")
def disable_server(name: str):
    """🚫 禁用 MCP 服务器"""
    config = get_mcp_config()
    
    if config.disable_server(name):
        console.print(f"[green]✓ 已禁用: {name}[/green]")
    else:
        console.print(f"[red]✗ 禁用失败[/red]")


@mcp_group.command(name="servers")
def list_servers():
    """📋 列出所有配置的 MCP 服务器"""
    config = get_mcp_config()
    servers = config.list_servers()
    
    console.print("\n[bold cyan]📋 MCP 服务器配置[/bold cyan]\n")
    
    if not servers:
        console.print("[yellow]没有配置的服务器[/yellow]")
        console.print("使用 [bold]yinian mcp add <name> --command <cmd>[/bold] 添加")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("名称")
    table.add_column("命令")
    table.add_column("描述")
    table.add_column("状态")
    
    for name, srv in servers.items():
        status = "[green]启用[/green]" if srv.enabled else "[red]禁用[/red]"
        cmd = f"{srv.command} {' '.join(srv.args)}"
        table.add_row(name, cmd, srv.description or "-", status)
    
    console.print(table)
