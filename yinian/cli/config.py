"""
Yinian CLI - 配置命令
"""
import click
from rich.console import Console
from rich.table import Table

from yinian.core.config import get_config

console = Console()


@click.group(name="config")
def config_group():
    """配置管理命令"""
    pass


@config_group.command(name="list")
def config_list():
    """列出所有配置"""
    config = get_config()
    show = config.show()
    
    console.print("\n[bold cyan]📋 一念 配置信息[/bold cyan]\n")
    
    # 默认配置
    console.print("[yellow]默认设置:[/yellow]")
    defaults = show.get("defaults", {})
    for key, value in defaults.items():
        console.print(f"  {key}: [green]{value}[/green]")
    
    # 模型列表
    console.print("\n[yellow]已配置模型:[/yellow]")
    models = show.get("models", {})
    if models:
        table = Table(show_header=True)
        table.add_column("名称")
        table.add_column("模型")
        table.add_column("API Key")
        table.add_column("费用/1K Input")
        
        for name, cfg in models.items():
            api_key = cfg.get("api_key", "")
            cost_in = cfg.get("cost_per_1k_input", 0)
            model = cfg.get("model", "")
            display_name = cfg.get("name", name)
            table.add_row(
                display_name,
                model,
                api_key if api_key else "[dim]未设置[/dim]",
                f"¥{cost_in}"
            )
        console.print(table)
    else:
        console.print("  [dim]暂无配置模型[/dim]")
    
    # 路由策略
    console.print("\n[yellow]路由策略:[/yellow]")
    router = show.get("router", {})
    console.print(f"  策略: [green]{router.get('strategy', 'auto')}[/green]")
    
    # 缓存设置
    console.print("\n[yellow]缓存设置:[/yellow]")
    cache = show.get("cache", {})
    for key, value in cache.items():
        console.print(f"  {key}: [green]{value}[/green]")
    
    console.print()


@config_group.command(name="get")
@click.argument("key")
def config_get(key: str):
    """获取配置值"""
    config = get_config()
    value = config.get(key)
    
    if value is None:
        console.print(f"[red]未找到配置: {key}[/red]")
    else:
        console.print(f"[green]{value}[/green]")


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """设置配置值
    
    示例:
      yinian config set defaults.model deepseek
      yinian config set models.deepseek.api_key sk-xxxxx
    """
    config = get_config()
    
    # 特殊处理：如果是布尔值
    if value.lower() in ("true", "false"):
        value = value.lower() == "true"
    # 如果是数字
    elif value.replace(".", "").replace("-", "").isdigit():
        value = float(value) if "." in value else int(value)
    
    config.set(key, value)
    console.print(f"[green]✅ 已设置 {key} = {value}[/green]")


@config_group.command(name="init")
def config_init():
    """初始化配置文件（重置为默认）"""
    config = get_config()
    config.reset()
    console.print("[green]✅ 配置已初始化为默认值[/green]")


@config_group.command(name="path")
def config_path():
    """显示配置目录路径"""
    config = get_config()
    console.print(f"\n[cyan]配置目录:[/cyan] {config.config_dir}")
    console.print(f"[cyan]缓存目录:[/cyan] {config.cache_dir}")
    console.print(f"[cyan]会话目录:[/cyan] {config.sessions_dir}\n")
