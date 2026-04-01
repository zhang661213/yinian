"""
Yinian CLI - 主入口
"""
import sys

import click
from rich.console import Console

from yinian.cli.config import config_group
from yinian.cli.ask import ask, models, shell
from yinian.cli.session import session_group
from yinian.cli.stats import stats_group
from yinian.cli.cache import cache_group
from yinian.cli.sync import models_sync
from yinian.cli.skill import skill_group

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.2", prog_name="一念")
@click.pass_context
def cli(ctx):
    """🤖 一念 - 最省钱的 AI 助手 CLI
    
    自动选择最合适的 AI 模型，智能省 Token，管道友好。
    
    示例:
      yinian           # 进入交互式对话模式（仅交互式终端）
      yinian "如何用 Python 写快排？"
      yinian "翻译：Hello World" --model kimi
      yinian "代码审查" --compare
      cat error.log | yinian "分析这个报错"
    """
    import sys
    # 如果没有子命令 → 检查是否真正交互式终端
    if ctx.invoked_subcommand is None:
        # 交互式终端 → 进入 REPL
        # 非交互式（脚本/管道）→ 显示帮助并退出
        if sys.stdin.isatty():
            from yinian.cli.ask import shell
            ctx.invoke(shell)
        else:
            # 非交互式，显示帮助
            from yinian.cli.ask import ask as ask_cmd
            ctx.invoke(ask_cmd, question=None)


def main():
    """入口点"""
    import sys
    try:
        cli(standalone_mode=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)


# 注册子命令
cli.add_command(config_group)
cli.add_command(ask, name="ask")
cli.add_command(models)
cli.add_command(models_sync, name="sync")
cli.add_command(session_group, name="session")
cli.add_command(stats_group, name="stats")
cli.add_command(cache_group, name="cache")
cli.add_command(shell, name="shell")
cli.add_command(skill_group, name="skill")


@cli.command(name="doctor")
def doctor():
    """🔍 检查环境配置"""
    import platform
    from yinian.core.config import get_config
    from yinian.models import get_factory
    from yinian.core.cache import get_cache
    
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
    
    # 缓存状态
    cache = get_cache()
    cache_stats = cache.stats()
    cache_status = "[green]✓ 已启用[/green]" if cache.enabled else "[red]✗ 已禁用[/red]"
    console.print(f"\n[yellow]缓存状态:[/yellow] {cache_status}")
    console.print(f"[yellow]缓存条目:[/yellow] {cache_stats['total_count']}")
    
    console.print()


if __name__ == "__main__":
    main()
