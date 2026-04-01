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


@config_group.command(name="add-model")
@click.argument("name")
@click.option("--api-key", "-k", help="API Key")
@click.option("--base-url", "-u", default="https://api.openai.com/v1", help="API 地址")
@click.option("--model", "-m", default="gpt-3.5-turbo", help="模型名称")
@click.option("--display-name", "-n", help="显示名称")
@click.option("--cost-input", "-i", type=float, default=0.001, help="每1K输入token费用(元)")
@click.option("--cost-output", "-o", type=float, default=0.002, help="每1K输出token费用(元)")
@click.option("--max-tokens", "-t", type=int, default=4096, help="最大token数")
@click.option("--timeout", type=int, default=60, help="超时时间(秒)")
def config_add_model(name, api_key, base_url, model, display_name, cost_input, cost_output, max_tokens, timeout):
    """添加自定义模型配置
    
    示例:
      # 添加 OpenAI 模型
      yinian config add-model openai --api-key sk-xxx --base-url https://api.openai.com/v1 --model gpt-4o
      
      # 添加硅基流动模型
      yinian config add-model silicon --api-key sk-xxx --base-url https://api.siliconflow.cn/v1 --model Qwen/Qwen2-7B-Instruct --cost-input 0.001 --cost-output 0.001
    """
    config = get_config()
    
    result = config.add_model(
        name,
        api_key=api_key or "",
        base_url=base_url,
        model=model,
        display_name=display_name or name,
        cost_per_1k_input=cost_input,
        cost_per_1k_output=cost_output,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    
    if result:
        console.print(f"[green]✅ 已添加模型: {name}[/green]")
        console.print(f"   API地址: {base_url}")
        console.print(f"   模型名: {model}")
    else:
        console.print(f"[red]❌ 添加模型失败: {name}[/red]")


@config_group.command(name="remove-model")
@click.argument("name")
def config_remove_model(name: str):
    """删除自定义模型配置
    
    示例:
      yinian config remove-model my-custom-model
    """
    config = get_config()
    
    # 检查是否是内置模型
    builtins = ["deepseek", "kimi", "qwen", "wenxin", "zhipu", "minimax", "hunyuan", "doubao"]
    if name in builtins:
        console.print(f"[yellow]⚠️ {name} 是内置模型，无法删除（可使用 --force 强制删除）[/yellow]")
        return
    
    result = config.remove_model(name)
    
    if result:
        console.print(f"[green]✅ 已删除模型: {name}[/green]")
    else:
        console.print(f"[red]❌ 模型不存在: {name}[/red]")


@config_group.command(name="edit-model")
@click.argument("name")
@click.option("--api-key", "-k", help="API Key")
@click.option("--base-url", "-u", help="API 地址")
@click.option("--model", "-m", help="模型名称")
@click.option("--display-name", "-n", help="显示名称")
@click.option("--cost-input", "-i", type=float, help="每1K输入token费用(元)")
@click.option("--cost-output", "-o", type=float, help="每1K输出token费用(元)")
@click.option("--max-tokens", "-t", type=int, help="最大token数")
@click.option("--timeout", type=int, help="超时时间(秒)")
def config_edit_model(name, api_key, base_url, model, display_name, cost_input, cost_output, max_tokens, timeout):
    """编辑自定义模型配置
    
    示例:
      yinian config edit-model my-model --api-key sk-xxx
      yinian config edit-model my-model --cost-input 0.0005 --cost-output 0.001
    """
    config = get_config()
    
    # 收集要更新的参数
    kwargs = {}
    if api_key is not None:
        kwargs["api_key"] = api_key
    if base_url is not None:
        kwargs["base_url"] = base_url
    if model is not None:
        kwargs["model"] = model
    if display_name is not None:
        kwargs["display_name"] = display_name
    if cost_input is not None:
        kwargs["cost_per_1k_input"] = cost_input
    if cost_output is not None:
        kwargs["cost_per_1k_output"] = cost_output
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if timeout is not None:
        kwargs["timeout"] = timeout
    
    if not kwargs:
        console.print("[yellow]⚠️ 未提供任何要更新的参数[/yellow]")
        return
    
    result = config.update_model(name, **kwargs)
    
    if result:
        console.print(f"[green]✅ 已更新模型: {name}[/green]")
        for key in kwargs:
            console.print(f"   {key}: {kwargs[key]}")
    else:
        console.print(f"[red]❌ 模型不存在: {name}[/red]")
