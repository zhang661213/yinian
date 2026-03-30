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
    
    # 如果是 Markdown 格式
    if "```" in response.content or response.content.startswith("#"):
        md = Markdown(response.content)
        console.print(md)
    else:
        # 普通文本
        console.print(response.content)
    
    # 显示统计信息
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
    router: Optional[Router] = None
) -> ModelResponse:
    """单模型问答"""
    router = router or get_router()
    factory = get_factory()
    
    # 如果没有指定模型，使用路由
    if not model_name:
        result = router.route(question)
        model_name = result.model_name
        if result.question_type != QuestionType.GENERAL:
            console.print(f"[dim]🔀 路由: {result.question_type.value} → {model_name} "
                         f"(置信度: {result.confidence:.0%}, {result.reason})[/dim]")
    
    model = factory.get_model(model_name)
    if not model:
        return ModelResponse(
            content="",
            model=model_name or "unknown",
            error=f"模型 {model_name} 不可用"
        )
    
    # 检查 API Key
    if not model.api_key:
        return ModelResponse(
            content="",
            model=model_name,
            error=f"模型 {model_name} 的 API Key 未设置。请运行: yinian config set models.{model_name}.api_key YOUR_KEY"
        )
    
    # 发送请求
    messages = [{"role": "user", "content": question}]
    
    try:
        response = await model.chat(messages, stream=stream)
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
    stream: bool = True
) -> List[ModelResponse]:
    """多模型对比"""
    factory = get_factory()
    
    # 验证模型
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
    
    # 并发请求
    tasks = []
    for name in valid_models:
        model = factory.get_model(name)
        messages = [{"role": "user", "content": question}]
        tasks.append(model.chat(messages, stream=stream))
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理结果
    results = []
    for name, response in zip(valid_models, responses):
        if isinstance(response, Exception):
            results.append(ModelResponse(
                content="",
                model=name,
                error=str(response)
            ))
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
    
    # 1. 管道输入
    if input_handler.is_pipe_input():
        pipe_content = input_handler.read_stdin()
        if pipe_content:
            console.print("[dim]📥 检测到管道输入[/dim]")
            result_parts.append(pipe_content)
    
    # 2. 文件输入
    if file_path:
        file_content = input_handler.read_file(file_path)
        if file_content:
            formatted = input_handler.format_file_content(file_path, file_content)
            result_parts.append(formatted)
            console.print(f"[dim]📄 已读取文件: {file_path}[/dim]")
    
    # 3. 命令行问题
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
def ask(
    question: Optional[str],
    model_name: Optional[str],
    compare_models: tuple,
    stream: bool,
    fast: bool,
    best: bool,
    dry_run: bool,
    file_path: Optional[str],
    question_type: Optional[str]
):
    """💬 向 AI 提问
    
    示例:
    
      yinian "如何用 Python 写快排？"
    
      yinian "翻译：Hello World" --model kimi
    
      yinian "分析这段代码" --compare
    
      cat error.log | yinian "分析这个报错"
    
      yinian --file error.log "分析这个错误"
    """
    input_handler = get_input_handler()
    router = get_router()
    config = get_config()
    
    # 处理输入（管道 + 文件 + 命令行）
    full_question = process_input(question, file_path, input_handler)
    
    if not full_question:
        # 尝试仅从 stdin 读取
        if input_handler.is_pipe_input():
            full_question = input_handler.read_stdin()
        
        if not full_question:
            console.print("[red]错误: 请提供问题、管道输入或文件[/red]")
            console.print("示例: yinian \"你的问题\" 或 cat file.txt | yinian")
            return
    
    # 显示完整问题（如果来自文件或管道）
    if file_path or input_handler.is_pipe_input():
        console.print(f"\n[bold]问题:[/bold]\n[dim]{full_question[:200]}{'...' if len(full_question) > 200 else ''}[/dim]\n")
    
    # 处理 --fast 和 --best
    if fast:
        model_name = config.get("defaults.fast_model", "deepseek")
        console.print(f"[dim]⚡ 快速模式 → {model_name}[/dim]")
    elif best:
        model_name = config.get("defaults.best_model", "deepseek-r1")
        console.print(f"[dim]🎯 精准模式 → {model_name}[/dim]")
    
    # Dry run 模式
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
    
    # 对比模式
    if compare_models:
        responses = asyncio.run(ask_compare(full_question, list(compare_models), stream))
        
        for i, response in enumerate(responses):
            console.print(f"\n[bold cyan]═══ {response.model} ═══[/bold cyan]")
            print_response(response, stream)
    
    # 单模型模式
    else:
        response = asyncio.run(ask_single(full_question, model_name, stream, router))
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
        
        # 显示路由信息
        rules = config.get("router.rules", {})
        if name in rules.values():
            for qtype, model in rules.items():
                if model == name:
                    console.print(f"      路由: [dim]{qtype}[/dim]")
        
        console.print()
