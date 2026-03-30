"""
Yinian CLI - 缓存命令
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from yinian.core.cache import get_cache

console = Console()


@click.group(name="cache")
def cache_group():
    """缓存管理命令"""
    pass


@cache_group.command(name="stats")
def cache_stats():
    """显示缓存统计"""
    cache = get_cache()
    stats = cache.stats()
    
    console.print("\n[bold cyan]📦 缓存统计[/bold cyan]\n")
    
    console.print(Panel.fit(
        f"[yellow]总条目:[/yellow] {stats['total_count']}\n"
        f"[yellow]总命中:[/yellow] {stats['total_hits']}\n"
        f"[yellow]节省费用:[/yellow] ¥{stats['total_saved']:.6f}\n"
        f"[yellow]平均费用:[/yellow] ¥{stats['avg_cost']:.6f}\n"
        f"[yellow]过期条目:[/yellow] {stats['expired_count']}",
        title="缓存状态"
    ))
    
    status = "[green]已启用[/green]" if cache.enabled else "[red]已禁用[/red]"
    console.print(f"\n缓存状态: {status}")


@cache_group.command(name="clear")
@click.option("--expired", "-e", is_flag=True, help="只清理过期缓存")
@click.confirmation_option(prompt="确定要清理缓存吗？")
def cache_clear(expired: bool):
    """清空缓存"""
    cache = get_cache()
    
    if expired:
        count = cache.clear_expired()
        console.print(f"[green]✓ 已清理 {count} 条过期缓存[/green]")
    else:
        count = cache.clear_all()
        console.print(f"[green]✓ 已清空 {count} 条缓存[/green]")


@cache_group.command(name="toggle")
def cache_toggle():
    """切换缓存状态"""
    cache = get_cache()
    new_state = cache.toggle()
    
    if new_state:
        console.print("[green]✓ 缓存已启用[/green]")
    else:
        console.print("[yellow]○ 缓存已禁用[/yellow]")


@cache_group.command(name="recent")
@click.option("--limit", "-n", default=10, help="显示条数")
def cache_recent(limit: int):
    """显示最近缓存"""
    cache = get_cache()
    entries = cache.db.get_recent(limit)
    
    if not entries:
        console.print("[dim]暂无缓存记录[/dim]")
        return
    
    table = Table(show_header=True)
    table.add_column("问题")
    table.add_column("模型")
    table.add_column("命中次数")
    table.add_column("创建时间")
    
    for entry in entries:
        question = entry.question[:50] + "..." if len(entry.question) > 50 else entry.question
        table.add_row(
            question,
            entry.model,
            str(entry.hit_count),
            entry.created_at[:16]
        )
    
    console.print(table)
