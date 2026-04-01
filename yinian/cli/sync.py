"""
Yinian CLI - 模型同步命令
"""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from yinian.models.sync import sync_provider, sync_all, update_config_with_working_model
from yinian.core.config import get_config

console = Console()


@click.command(name="sync")
@click.option("--provider", "-p", help="指定提供商 (minimax/deepseek/kimi/qwen)")
@click.option("--auto-update", "-a", is_flag=True, help="自动更新配置为第一个可用的模型")
def models_sync(provider: str, auto_update: bool):
    """🔄 同步模型列表
    
    自动检测各家套餐支持的模型（通过实际调用测试）
    
    示例:
    
      yinian sync                   # 同步所有已配置 Key 的提供商
      yinian sync -p minimax         # 只同步 MiniMax
      yinian sync -p minimax -a     # 同步并自动更新配置
    """
    console.print("\n[bold cyan]🔄 正在同步模型列表...[/bold cyan]\n")
    console.print("[dim]通过实际调用 API 测试各模型是否在套餐范围内[/dim]\n")
    
    config = get_config()
    results = {}
    
    if provider:
        # 同步指定提供商
        api_key = config.get_api_key(provider)
        if not api_key:
            console.print(f"[red]错误: {provider} 的 API Key 未设置[/red]")
            return
        
        success, models, error = asyncio.run(sync_provider(provider, api_key))
        results[provider] = (success, models, error)
    else:
        # 同步所有
        results = asyncio.run(sync_all(config))
    
    # 显示结果
    table = Table(show_header=True)
    table.add_column("提供商")
    table.add_column("状态")
    table.add_column("可用模型")
    
    has_success = False
    
    for prov, (success, models, error) in results.items():
        if success:
            has_success = True
            model_names = "\n".join([f"• {name} ({model})" for model, name in models])
            table.add_row(
                prov,
                "[green]✓[/green]",
                model_names
            )
            
            # 自动更新配置
            if auto_update and models:
                first_model = models[0][0]
                update_config_with_working_model(config, prov, first_model)
                console.print(f"[green]✓ {prov}: 已更新默认模型为 {first_model}[/green]")
        else:
            table.add_row(
                prov,
                "[red]✗[/red]",
                f"[red]{error[:40]}[/red]"
            )
    
    console.print(table)
    
    # 总结
    success_count = sum(1 for s, _, _ in results.values() if s)
    total_count = len(results)
    
    if has_success:
        console.print(f"\n[bold]同步完成: {success_count}/{total_count} 个提供商成功[/bold]")
    else:
        console.print(f"\n[yellow]所有提供商的同步都失败了，请检查 API Key 是否正确[/yellow]")
    
    if auto_update:
        console.print("[dim]配置已自动更新[/dim]")
    
    console.print()
