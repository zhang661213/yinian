"""
Yinian CLI - 问答命令
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.markdown import Markdown

from yinian.core.config import get_config
from yinian.core.router import Router, get_router, QuestionType
from yinian.core.input import get_input_handler
from yinian.models import get_factory, ModelResponse

console = Console()


def print_response(response: ModelResponse, color: bool = True):
    """打印模型响应"""
    if response.error:
        console.print(f"[red]错误: {response.error}[/red]")
        return
    
    if "```" in response.content or response.content.startswith("#"):
        md = Markdown(response.content)
        console.print(md)
    else:
        console.print(response.content)
    
    if response.input_tokens:
        console.print()
        console.print(
            f"[dim]│ 模型: {response.model} "
            f"│ 输入: {response.input_tokens} tokens │ "
            f"输出: {response.output_tokens} tokens │ "
            f"费用: ¥{response.cost:.6f} │ "
            f"延迟: {response.latency_ms:.0f}ms[/dim]"
        )


async def ask_single(
    question: str,
    model_name: Optional[str] = None,
    stream: bool = True,
    router: Optional[Router] = None,
    system_prompt: Optional[str] = None,
) -> ModelResponse:
    """单模型问答"""
    from yinian.core.cache import get_cache
    
    router = router or get_router()
    factory = get_factory()
    cache = get_cache()
    
    if not model_name:
        result = router.route(question)
        model_name = result.model_name
        if result.question_type != QuestionType.GENERAL:
            console.print(f"[dim]🔀 路由: {result.question_type.value} → {model_name} "
                         f"(置信度: {result.confidence:.0%}, {result.reason})[/dim]")
    
    # 先检查缓存
    if cache.enabled:
        cached = cache.get(question, model_name or "")
        if cached and not cached.is_expired():
            console.print(f"[green]💰 缓存命中 │ 省 ¥{cached.cost:.6f}[/green]\n")
            cached_resp = ModelResponse(
                content=cached.response,
                model=model_name or "unknown",
                input_tokens=cached.input_tokens,
                output_tokens=cached.output_tokens,
                total_tokens=cached.input_tokens + cached.output_tokens,
                cost=0.0,
                latency_ms=0,
            )
            print_response(cached_resp, color=True)
            return cached_resp
    
    model = factory.get_model(model_name)
    if not model:
        return ModelResponse(
            content="",
            model=model_name or "unknown",
            error=f"模型 {model_name} 不可用"
        )
    
    if not model.api_key:
        return ModelResponse(
            content="",
            model=model_name,
            error=f"模型 {model_name} 的 API Key 未设置。请运行: yinian config set models.{model_name}.api_key YOUR_KEY"
        )
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})
    
    try:
        response = await model.chat(messages, stream=stream)
        
        # 保存到缓存
        if response.content and not response.error and cache.enabled:
            cache.set(
                question=question,
                model=model_name or model.model_name,
                response=response.content,
                input_tokens=response.input_tokens or 0,
                output_tokens=response.output_tokens or 0,
                cost=response.cost or 0.0,
                latency_ms=response.latency_ms or 0.0,
            )
        
        return response
    except Exception as e:
        return ModelResponse(
            content="",
            model=model_name,
            error=str(e)
        )


async def ask_compare(
    question: str,
    model_names: List[str],
    stream: bool = True,
    system_prompt: Optional[str] = None,
) -> List[ModelResponse]:
    """多模型对比"""
    factory = get_factory()
    
    valid_models = []
    for name in model_names:
        model = factory.get_model(name)
        if model and model.api_key:
            valid_models.append(name)
        else:
            console.print(f"[yellow]⚠ 模型 {name} 未配置或无 API Key，跳过[/yellow]")
    
    if not valid_models:
        console.print("[red]错误: 没有可用的模型[/red]")
        return []
    
    console.print(f"[cyan]🔄 同时询问 {len(valid_models)} 个模型...[/cyan]\n")
    
    tasks = []
    for name in valid_models:
        model = factory.get_model(name)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})
        tasks.append(model.chat(messages, stream=stream))
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    results = []
    for name, response in zip(valid_models, responses):
        if isinstance(response, Exception):
            results.append(ModelResponse(content="", model=name, error=str(response)))
        else:
            results.append(response)
    
    return results


def process_input(
    question: Optional[str],
    file_path: Optional[str],
    input_handler
) -> Optional[str]:
    """处理输入，返回最终问题文本"""
    result_parts = []
    
    if input_handler.is_pipe_input():
        pipe_content = input_handler.read_stdin()
        if pipe_content:
            console.print("[dim]📥 检测到管道输入[/dim]")
            result_parts.append(pipe_content)
    
    if file_path:
        file_content = input_handler.read_file(file_path)
        if file_content:
            formatted = input_handler.format_file_content(file_path, file_content)
            result_parts.append(formatted)
            console.print(f"[dim]📄 已读取文件: {file_path}[/dim]")
    
    if question:
        result_parts.append(question)
    
    if not result_parts:
        return None
    
    return "\n\n".join(result_parts)


@click.command()
@click.argument("question", required=False)
@click.option("--model", "-m", "model_name", help="指定模型 (deepseek/kimi/qwen)")
@click.option("--compare", "-c", "compare_models", multiple=True, help="对比多个模型")
@click.option("--stream/--no-stream", default=True, help="流式输出")
@click.option("--fast", is_flag=True, help="快速模式（使用最便宜的模型）")
@click.option("--best", is_flag=True, help="精准模式（使用最强模型）")
@click.option("--dry-run", is_flag=True, help="仅显示路由结果，不实际调用")
@click.option("--file", "-f", "file_path", help="从文件读取内容")
@click.option("--type", "question_type", help="指定问题类型 (code/math/chinese/english/quick)")
@click.option("--system", "-s", "system_prompt", help="设置系统提示词（AI 角色设定）")
def ask(
    question: Optional[str],
    model_name: Optional[str],
    compare_models: tuple,
    stream: bool,
    fast: bool,
    best: bool,
    dry_run: bool,
    file_path: Optional[str],
    question_type: Optional[str],
    system_prompt: Optional[str] = None,
):
    """💬 向 AI 提问
    
    示例:
    
      yinian "如何用 Python 写快排？"
    
      yinian "翻译：Hello World" --model kimi
    
      yinian "你是一个代码审查员" --system "审查以下代码的问题" --file main.py
    """
    input_handler = get_input_handler()
    router = get_router()
    factory = get_factory()
    config = get_config()
    
    full_question = process_input(question, file_path, input_handler)
    
    if not full_question:
        if input_handler.is_pipe_input():
            full_question = input_handler.read_stdin()
        
        if not full_question:
            console.print("[red]错误: 请提供问题、管道输入或文件[/red]")
            console.print("示例: yinian \"你的问题\" 或 cat file.txt | yinian")
            return
    
    if file_path or input_handler.is_pipe_input():
        console.print(f"\n[bold]问题:[/bold]\n[dim]{full_question[:200]}{'...' if len(full_question) > 200 else ''}[/dim]\n")
    
    if fast:
        # 智能自动模式：Router 根据问题类型自动选最便宜的模型
        result = router.route(full_question, cheap=True)
        model_name = result.model_name
        info = factory.get_model_info(model_name)
        cost = (info["cost_per_1k_input"] + info["cost_per_1k_output"]) if info else 0
        console.print(f"[dim]⚡ 智能模式 → {result.question_type.value} → {model_name} "
                     f"(¥{cost:.4f}/1K, 置信度 {result.confidence:.0%})[/dim]")
    elif best:
        model_name = config.get("defaults.best_model", "deepseek-r1")
        console.print(f"[dim]🎯 精准模式 → {model_name}[/dim]")
    
    if dry_run:
        result = router.route(full_question)
        console.print(f"\n[bold cyan]🔍 路由分析结果[/bold cyan]")
        console.print(f"  问题类型: {result.question_type.value}")
        console.print(f"  置信度: {result.confidence:.0%}")
        console.print(f"  推荐模型: {result.model_name}")
        console.print(f"  原因: {result.reason}")
        console.print(f"  备用模型: {', '.join(result.fallback_models) or '无'}")
        console.print()
        return
    
    if compare_models:
        responses = asyncio.run(ask_compare(full_question, list(compare_models), stream, system_prompt))
        for i, response in enumerate(responses):
            console.print(f"\n[bold cyan]═══ {response.model} ═══[/bold cyan]")
            print_response(response, stream)
    else:
        response = asyncio.run(ask_single(full_question, model_name, stream, router, system_prompt))
        # 缓存命中时 ask_single 已打印，无需再打印
        if not (response.latency_ms == 0 and response.cost == 0):
            print_response(response, stream)


@click.command()
def models():
    """📋 列出所有可用的模型"""
    factory = get_factory()
    config = get_config()
    
    console.print("\n[bold cyan]📋 可用模型[/bold cyan]\n")
    
    for name in factory.list_models():
        info = factory.get_model_info(name)
        if not info:
            continue
        
        has_key = info["has_api_key"]
        status_icon = "[green]✓[/green]" if has_key else "[red]✗[/red]"
        
        console.print(f"  {status_icon} [bold]{info['display_name']}[/bold] ({name})")
        console.print(f"      模型: {info['model_id']}")
        console.print(f"      费用: ¥{info['cost_per_1k_input']:.4f}/1K 输入, "
                     f"¥{info['cost_per_1k_output']:.4f}/1K 输出")
        console.print(f"      API Key: {'已设置' if has_key else '[red]未设置[/red]'}")
        
        rules = config.get("router.rules", {})
        if name in rules.values():
            for qtype, model in rules.items():
                if model == name:
                    console.print(f"      路由: [dim]{qtype}[/dim]")
        
        console.print()


@click.command(name="shell")
@click.option("--model", "-m", "model_name", help="指定默认模型")
@click.option("--session", "-s", "session_name", help="指定会话名称")
def shell(model_name: Optional[str], session_name: Optional[str]):
    """🖥️ 交互式对话模式（无需每句加 yinian ask）
    
    示例:
    
      yinian shell
      yinian shell --model minimax
      yinian shell --session my-chat
    """
    from yinian.core.session import get_session_manager
    from rich.table import Table
    
    input_handler = get_input_handler()
    router = get_router()
    factory = get_factory()
    
    enabled_models = factory.list_enabled_models()
    if not enabled_models:
        console.print("[red]错误: 没有任何可用的模型（都没有配置 API Key）[/red]")
        console.print("请先配置至少一个模型的 API Key:")
        console.print("  yinian config set models.llama.api_key local")
        return
    
    current_model = model_name or enabled_models[0]
    
    # 会话管理器
    session_mgr = get_session_manager()
    current_session_name = session_name or "default"
    session_mgr.switch_session(current_session_name)
    session = session_mgr.current
    history: List[dict] = session.get_messages_for_api()
    
    # 当前 system prompt
    current_system: Optional[str] = None
    
    console.print(f"\n[bold cyan]🤖 一念 REPL — 交互式对话[/bold cyan]")
    console.print(f"[dim]模型: [bold]{current_model}[/bold]  │  会话: [bold]{current_session_name}[/bold][/dim]")
    console.print(f"[dim]输入 /help 查看命令[/dim]\n")
    
    if history:
        console.print(f"[dim]已加载 {len(history)} 条历史消息[/dim]\n")
    
    # REPL 设置
    current_temperature = 0.7
    current_max_tokens = 0
    max_history = 20
    cheap_mode = False  # 智能省心模式：每条消息自动路由到最便宜的
    
    while True:
        try:
            user_input = click.prompt(
                "",
                default="",
                show_default=False,
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再见！[/dim]")
            break
        
        if not user_input:
            continue
        
        # 去掉 BOM 字符（PowerShell 管道输入可能带 BOM）
        user_input = user_input.lstrip("\ufeff").strip()
        if not user_input:
            continue
        
        cmd = user_input.lstrip("/").lower()
        
        # 退出
        if cmd in ("exit", "quit", "q"):
            # 退出前：自动判断重要性
            was_important = session_mgr.current.important
            auto_marked = session_mgr.current.check_auto_important()
            if session_mgr.current.important and not was_important:
                reason = session_mgr.current.auto_important_reason
                console.print(f"\n[yellow]★ 会话已自动标记为重要: {reason}[/yellow]")
            session_mgr.save_session(current_session_name)
            user_msgs = [m for m in history if m["role"] == "user"]
            console.print(f"\n[dim]本次会话: {len(user_msgs)}轮 │ "
                         f"Token: {session_mgr.current.total_tokens:,} │ "
                         f"费用: ¥{session_mgr.current.total_cost:.4f}[/dim]")
            clean_result = session_mgr.clean_unimportant(older_than_days=7, keep_min=3)
            if clean_result["deleted"] > 0:
                console.print(f"[dim]已自动清理 {clean_result['deleted']} 个旧不重要会话[/dim]")
            console.print("[dim]再见！[/dim]")
            break
        
        # 帮助
        if cmd == "help":
            console.print("""
[bold]一念 REPL 命令:[/bold]
  /help          显示帮助
  /exit, /quit   退出 REPL（退出时自动判断重要会话）
  /model <name>  切换模型（如 /model deepseek）
  /models        查看可用模型
  /cheap         开启/关闭智能省心模式（每条消息自动路由到最便宜）
  /stats         查看用量统计
  /sessions      查看所有会话（★=重要）
  /save <name>   保存当前会话
  /load <name>   加载会话
  /new           新建会话
  /clear         清空当前对话历史
  /delete <name> 删除会话
  /important     标记当前会话为重要
  /unimportant   取消重要标记
  /summary       查看当前会话摘要
  /set temp 0.8 设置温度
  /set max 2048  设置最大输出 token
  /set view      查看当前设置
  /system 你是一个Python专家  设定 AI 角色
  /system clear   清除 System Prompt
""")
            continue
        
        # 切换模型
        if cmd.startswith("model "):
            target = cmd[6:].strip()
            if target not in enabled_models:
                console.print(f"[red]模型 {target} 不可用或未配置 API Key[/red]")
            else:
                current_model = target
                console.print(f"[green]已切换到模型: {current_model}[/green]")
            continue
        
        # 查看可用模型
        if cmd == "models":
            console.print("\n[bold]可用模型:[/bold]")
            for name in enabled_models:
                info = factory.get_model_info(name)
                if info:
                    marker = " ← 当前" if name == current_model else ""
                    console.print(f"  [cyan]{name}[/cyan] ({info['display_name']}){marker}")
            console.print()
            continue
        
        # 最便宜模型（智能省心模式：每条消息自动路由到最便宜的）
        if cmd == "cheap":
            if cheap_mode:
                cheap_mode = False
                console.print(f"[yellow]已关闭智能省心模式，当前模型: {current_model}[/yellow]")
            else:
                cheap_mode = True
                console.print("[green]✓ 已开启智能省心模式 (/cheap)：每条消息自动路由到最便宜的模型[/green]")
            continue
        
        # 用量统计
        if cmd == "stats":
            console.print("[dim]正在查询用量...[/dim]\n")
            from yinian.cli.stats import stats_summary
            stats_summary()
            continue
        
        # 查看所有会话
        if cmd == "sessions":
            sessions = session_mgr.list_sessions(include_details=True)
            if not sessions:
                console.print("[dim]暂无会话[/dim]")
            else:
                table = Table(show_header=True)
                table.add_column("会话名")
                table.add_column("重要")
                table.add_column("轮次")
                table.add_column("Token")
                table.add_column("费用")
                table.add_column("最后更新")
                for s in sessions:
                    marker = "[yellow]★[/yellow]" if s["important"] else "[dim]-[/dim]"
                    table.add_row(
                        s["name"], marker,
                        str(s["rounds"]),
                        f"{s['tokens']:,}",
                        f"¥{s['cost']:.4f}",
                        s["updated"],
                    )
                console.print(table)
                console.print()
                important_n = sum(1 for s in sessions if s["important"])
                console.print(f"[dim]共 {len(sessions)} 个会话，{important_n} 个重要[/dim]\n")
            continue
        
        # 保存会话
        if cmd.startswith("save "):
            save_name = cmd[5:].strip()
            if not save_name:
                console.print("[yellow]请指定会话名，如 /save my-chat[/yellow]")
                continue
            session_mgr.switch_session(save_name)
            for msg in history:
                session_mgr.add_to_current(msg["role"], msg["content"])
            session_mgr.save_session(save_name)
            current_session_name = save_name
            console.print(f"[green]✓ 会话已保存为: {save_name}[/green]")
            continue
        
        # 加载会话
        if cmd.startswith("load "):
            load_name = cmd[5:].strip()
            s = session_mgr.get_session(load_name)
            if s is None:
                console.print(f"[yellow]会话不存在: {load_name}[/yellow]")
            else:
                session_mgr.switch_session(load_name)
                history = session_mgr.current.get_messages_for_api()
                current_session_name = load_name
                console.print(f"[green]✓ 已加载会话: {load_name}（{len(history)} 条消息）[/green]")
            continue
        
        # 新建会话
        if cmd == "new":
            session_mgr.current.check_auto_important()
            if session_mgr.current.important:
                session_mgr.save_session(session_mgr.current.name)
            session_mgr.switch_session("default")
            history = []
            current_session_name = "default"
            console.print("[green]✓ 已新建会话（当前: default）[/green]")
            continue
        
        # 标记重要
        if cmd in ("important", "star", "⭐"):
            if session_mgr.current.important:
                console.print(f"[yellow]当前会话已标记为重要[/yellow]")
                console.print(f"   原因: {session_mgr.current.auto_important_reason}")
            else:
                session_mgr.mark_current_important("手动标记")
                console.print("[green]✓ 当前会话已标记为重要[/green]")
            continue
        
        # 取消重要标记
        if cmd in ("unimportant", "unstar"):
            if not session_mgr.current.important:
                console.print("[yellow]当前会话本来就不是重要[/yellow]")
            else:
                session_mgr.unmark_current_important()
                console.print("[green]✓ 已取消重要标记[/green]")
            continue
        
        # 会话摘要
        if cmd in ("summary", "summarize"):
            summary = session_mgr.get_session_summary(current_session_name)
            console.print(f"\n[bold]📋 会话摘要[/bold]\n")
            console.print(summary)
            console.print()
            continue
        
        # 清空历史
        if cmd == "clear":
            session_mgr.clear_current()
            history = []
            console.print("[dim]对话历史已清空[/dim]")
            continue
        
        # 删除会话
        if cmd.startswith("delete "):
            del_name = cmd[7:].strip()
            if session_mgr.delete_session(del_name):
                console.print(f"[green]✓ 已删除会话: {del_name}[/green]")
                if current_session_name == del_name:
                    current_session_name = "default"
                    history = []
                    session_mgr.switch_session("default")
            else:
                console.print(f"[yellow]会话不存在: {del_name}[/yellow]")
            continue
        
        # 设置参数
        if cmd.startswith("set "):
            parts = cmd[4:].strip().split()
            if not parts:
                console.print("[yellow]用法: /set temp 0.8  或  /set max 2048  或  /set view[/yellow]")
                continue
            key = parts[0]
            if key == "temp":
                try:
                    val = float(parts[1]) if len(parts) > 1 else None
                    if val is None:
                        console.print(f"[yellow]当前温度: {current_temperature}[/yellow]")
                    elif 0 <= val <= 2.0:
                        current_temperature = val
                        console.print(f"[green]✓ 温度已设为: {val}[/green]")
                    else:
                        console.print("[red]温度需在 0.0~2.0 之间[/red]")
                except (ValueError, IndexError):
                    console.print("[red]用法: /set temp 0.8[/red]")
            elif key == "max":
                try:
                    val = int(parts[1]) if len(parts) > 1 else None
                    if val is None:
                        console.print(f"[yellow]当前最大 token: {current_max_tokens or '默认'}[/yellow]")
                    elif val >= 0:
                        current_max_tokens = val
                        console.print(f"[green]✓ 最大 token 已设为: {val}[/green]")
                    else:
                        console.print("[red]最大 token 需 >= 0[/red]")
                except (ValueError, IndexError):
                    console.print("[red]用法: /set max 2048[/red]")
            elif key in ("view", "show"):
                console.print(f"\n[bold]当前 REPL 设置:[/bold]")
                console.print(f"  模型: {current_model}")
                console.print(f"  温度: {current_temperature}")
                console.print(f"  最大 token: {current_max_tokens or '默认'}")
                console.print(f"  会话: {current_session_name}")
                cheap_status = "[green]✓ 开启[/green]" if cheap_mode else "[dim]✗ 关闭[/dim]"
                console.print(f"  智能省心: {cheap_status}")
                console.print()
            else:
                console.print(f"[yellow]未知设置项: {key}，可用: temp, max, view[/yellow]")
            continue
        
        # System Prompt
        if cmd.startswith("system "):
            system_text = cmd[7:].strip()
            if system_text:
                current_system = system_text
                console.print(f"[green]✓ System Prompt 已设定:[/green]")
                console.print(f"[dim]{system_text}[/dim]\n")
            else:
                console.print("[yellow]当前 System Prompt:[/yellow]")
                if current_system:
                    console.print(f"[dim]{current_system}[/dim]\n")
                else:
                    console.print("[dim]（未设置）[/dim]\n")
            continue
        
        # 清除 System Prompt
        if cmd in ("system clear", "system reset"):
            current_system = None
            console.print("[dim]System Prompt 已清除[/dim]")
            continue
        
        # 正常对话
        messages = []
        if current_system:
            messages.append({"role": "system", "content": current_system})
        
        # 滑动窗口
        effective_max = max_history - 1
        if effective_max > 0 and len(history) > effective_max:
            trimmed = history[-effective_max:]
            removed = len(history) - effective_max
            if removed > 0:
                console.print(f"[dim]（已截断 {removed} 条早期消息）[/dim]")
            messages.extend(trimmed)
        else:
            messages.extend(history)
        
        messages.append({"role": "user", "content": user_input})
        
        console.print(f"\n[dim]{'─' * 40}[/dim]")
        console.print(f"[bold cyan]你:[/bold cyan] {user_input}\n")
        
        # 智能省心模式：每条消息自动路由到最便宜的
        if cheap_mode:
            route_result = router.route(user_input, cheap=True)
            current_model = route_result.model_name
            info = factory.get_model_info(current_model)
            cost = (info["cost_per_1k_input"] + info["cost_per_1k_output"]) if info else 0
            console.print(f"[dim]⚡ {route_result.question_type.value} → {current_model} "
                         f"(¥{cost:.4f}/1K)[/dim]")
        
        console.print(f"[bold green]AI:[/bold green] ", end="", soft_wrap=True)
        
        model = factory.get_model(current_model)
        if not model or not model.api_key:
            console.print(f"\n[red]模型 {current_model} 未配置 API Key[/red]")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": f"错误: 模型 {current_model} 未配置 API Key"})
            session_mgr.add_to_current("user", user_input, model=current_model)
            session_mgr.add_to_current("assistant", f"错误: 模型 {current_model} 未配置 API Key", model=current_model)
            continue
        
        try:
            chat_kwargs = {"temperature": current_temperature}
            if current_max_tokens > 0:
                chat_kwargs["max_tokens"] = current_max_tokens
            response = asyncio.run(model.chat(messages, stream=True, **chat_kwargs))
            
            if response.error:
                console.print(f"\n[red]错误: {response.error}[/red]")
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": f"错误: {response.error}"})
                session_mgr.add_to_current("user", user_input, model=current_model)
                session_mgr.add_to_current("assistant", f"错误: {response.error}", model=current_model)
            else:
                console.print(response.content)
                console.print()
                console.print(
                    f"[dim]│ {response.output_tokens} tokens │ "
                    f"¥{response.cost:.6f} │ "
                    f"{response.latency_ms:.0f}ms[/dim]"
                )
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": response.content})
                session_mgr.add_to_current("user", user_input, model=current_model,
                                          tokens=response.input_tokens or 0,
                                          total_tokens=(response.input_tokens or 0) + (response.output_tokens or 0),
                                          cost=0.0)
                session_mgr.add_to_current("assistant", response.content, model=current_model,
                                         tokens=response.output_tokens,
                                         total_tokens=(response.input_tokens or 0) + (response.output_tokens or 0),
                                         cost=response.cost)
        
        except Exception as e:
            console.print(f"\n[red]请求异常: {e}[/red]")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": f"异常: {e}"})
            session_mgr.add_to_current("user", user_input, model=current_model)
            session_mgr.add_to_current("assistant", f"异常: {e}", model=current_model)
