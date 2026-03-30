"""
Yinian CLI - 会话命令
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from yinian.core.session import get_session_manager

console = Console()


@click.group(name="session")
def session_group():
    """会话管理命令"""
    pass


@session_group.command(name="list")
def session_list():
    """列出所有会话"""
    manager = get_session_manager()
    sessions = manager.list_sessions()
    current = manager._current_name
    
    if not sessions:
        console.print("[dim]暂无会话记录[/dim]")
        return
    
    table = Table(show_header=True)
    table.add_column("名称")
    table.add_column("消息数")
    table.add_column("总 Token")
    table.add_column("总费用")
    table.add_column("更新时间")
    
    for name in sessions:
        session = manager.get_session(name)
        if session:
            updated = session.updated_at[:16] if session.updated_at else "-"
            table.add_row(
                f"[bold]{name}[/bold]" if name == current else name,
                str(len(session.messages)),
                str(session.total_tokens),
                f"¥{session.total_cost:.4f}",
                updated
            )
    
    console.print(table)


@session_group.command(name="switch")
@click.argument("name")
def session_switch(name: str):
    """切换会话"""
    manager = get_session_manager()
    manager.switch_session(name)
    console.print(f"[green]✓ 已切换到会话: {name}[/green]")


@session_group.command(name="current")
def session_current():
    """显示当前会话"""
    manager = get_session_manager()
    current = manager.current
    
    console.print(f"\n[bold cyan]当前会话: {current.name}[/bold cyan]")
    console.print(f"消息数: {len(current.messages)}")
    console.print(f"总 Token: {current.total_tokens}")
    console.print(f"总费用: ¥{current.total_cost:.4f}")
    console.print()


@session_group.command(name="clear")
@click.confirmation_option(prompt="确定要清空当前会话吗？")
def session_clear():
    """清空当前会话"""
    manager = get_session_manager()
    manager.clear_current()
    console.print("[green]✓ 当前会话已清空[/green]")


@session_group.command(name="delete")
@click.argument("name")
@click.confirmation_option(prompt="确定要删除这个会话吗？")
def session_delete(name: str):
    """删除会话"""
    manager = get_session_manager()
    if manager.delete_session(name):
        console.print(f"[green]✓ 会话已删除: {name}[/green]")
    else:
        console.print(f"[red]会话不存在: {name}[/red]")
