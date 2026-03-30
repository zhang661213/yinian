"""
Yinian CLI - 主入口
"""
import sys

import click
from rich.console import Console

from yinian.cli.config import config_group
from yinian.cli.ask import ask, models
from yinian.cli.session import session_group
from yinian.cli.stats import stats_group

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="一念")
def cli():
    """🤖 一念 - 最省钱的 AI 助手 CLI
    
    自动选择最合适的 AI 模型，智能省 Token，管道友好。
    
    示例:
      yinian "如何用 Python 写快排？"
      yinian "翻译：Hello World" --model kimi
      yinian "代码审查" --compare
      cat error.log | yinian "分析这个报错"
    """
    pass


# 注册子命令
cli.add_command(config_group)
cli.add_command(ask, name="ask")
cli.add_command(models)
cli.add_command(session_group, name="session")
cli.add_command(stats_group, name="stats")


@cli.command(name="doctor")
def doctor():
    """🔍 检查环境配置"""
    import platform
    from yinian.core.config import get_config
    from yinian.models import get_factory
    
    console.print("\n[bold cyan]🔍 一念 环境检查[/bold cyan]\n")
    
    # Python 版本
    console.print(f"[yellow]Python:[/yellow] {platform.python_version()}")
    console.print(f"[yellow]平台:[/yellow] {platform.platform()}")
    
    # 配置
    config = get_config()
    console.print(f"[yellow]配置目录:[/yellow] {config.config_dir}")
    console.print(f"[yellow]配置文件:[/yellow] {config.config_file}")
    
    # 模型状态
    factory = get_factory()
    console.print("\n[yellow]API Key 状态:[/yellow]")
    for name in factory.list_models():
        info = factory.get_model_info(name)
        has_key = info["has_api_key"] if info else False
        status = "[green]✓ 已设置[/green]" if has_key else "[red]✗ 未设置[/red]"
        display = info["display_name"] if info else name
        console.print(f"  {display}: {status}")
    
    console.print()


def main():
    """入口点"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
