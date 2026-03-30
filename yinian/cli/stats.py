"""
Yinian CLI - 统计命令
"""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from yinian.core.stats import get_stats
from yinian.core.config import get_config

console = Console()


@click.group(name="stats")
def stats_group():
    """用量统计命令"""
    pass


@stats_group.command(name="show")
@click.option("--days", "-d", default=30, help="统计天数")
def stats_show(days: int):
    """显示用量统计"""
    stats = get_stats()
    config = get_config()
    
    summary = stats.get_summary()
    model_stats = stats.get_model_breakdown()
    
    # 概览
    console.print(f"\n[bold cyan]📊 用量统计 (最近 {days} 天)[/bold cyan]\n")
    
    console.print(Panel.fit(
        f"[yellow]本月费用:[/yellow] ¥{summary['monthly_cost']:.4f} / ¥{summary['monthly_limit']:.2f}\n"
        f"[yellow]总费用:[/yellow] ¥{summary['total_cost']:.4f}\n"
        f"[yellow]总 Token:[/yellow] {summary['total_tokens']:,}\n"
        f"[yellow]总请求:[/yellow] {summary['total_requests']}",
        title="概览"
    ))
    
    console.print()
    
    # 模型分解
    if model_stats:
        console.print("[bold]按模型统计:[/bold]\n")
        
        table = Table(show_header=True)
        table.add_column("模型")
        table.add_column("请求数")
        table.add_column("输入 Token")
        table.add_column("输出 Token")
        table.add_column("总 Token")
        table.add_column("费用")
        table.add_column("平均延迟")
        
        for stat in model_stats:
            table.add_row(
                stat["model"],
                str(stat["request_count"]),
                f"{stat['input_tokens']:,}",
                f"{stat['output_tokens']:,}",
                f"{stat['total_tokens']:,}",
                f"¥{stat['total_cost']:.4f}",
                f"{stat['avg_latency']:.0f}ms"
            )
        
        console.print(table)
    else:
        console.print("[dim]暂无统计数据[/dim]")
    
    console.print()


@stats_group.command(name="budget")
@click.option("--set", "new_limit", type=float, help="设置月度预算（元）")
def stats_budget(new_limit: float):
    """管理预算"""
    config = get_config()
    
    if new_limit:
        config.set("budget.monthly_limit", new_limit)
        console.print(f"[green]✓ 月度预算已设置为: ¥{new_limit:.2f}[/green]")
    else:
        current = config.get("budget.monthly_limit", 100.0)
        console.print(f"当前月度预算: [yellow]¥{current:.2f}[/yellow]")
    
    # 显示本月消费
    stats = get_stats()
    summary = stats.get_summary()
    console.print(f"本月已消费: [yellow]¥{summary['monthly_cost']:.4f}[/yellow]")
    
    remaining = current - summary['monthly_cost']
    if remaining > 0:
        console.print(f"剩余预算: [green]¥{remaining:.2f}[/green]")
    else:
        console.print(f"超出预算: [red]¥{-remaining:.2f}[/red]")


@stats_group.command(name="export")
@click.argument("path", type=click.Path(), default="yinian-stats.csv")
def stats_export(path: str):
    """导出统计数据"""
    stats = get_stats()
    
    export_path = Path(path).expanduser()
    stats.export_csv(export_path)
    
    console.print(f"[green]✓ 统计数据已导出到: {export_path}[/green]")
