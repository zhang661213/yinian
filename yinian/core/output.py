"""
Yinian 流式输出
"""
import sys
import time
from typing import AsyncIterator

from rich.console import Console
from rich.control import Control
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from yinian.models.base import StreamChunk, ModelResponse


class StreamOutput:
    """流式输出处理器"""
    
    def __init__(self, console: Console = None, color: bool = True):
        self.console = console or Console(color=color)
        self._buffer = ""
        self._lines = 0
        self._last_update = 0
    
    def clear(self):
        """清除输出"""
        self.console.control(Control.clear())
    
    def print_chunk(self, chunk: StreamChunk) -> None:
        """打印流式块"""
        if chunk.is_final:
            return
        
        self._buffer += chunk.delta
        
        # 节流更新（每 30ms 最多一次）
        now = time.time()
        if now - self._last_update < 0.03 and chunk.delta:
            return
        self._last_update = now
        
        # 检测内容类型
        if self._is_code(self._buffer):
            self._print_code(self._buffer)
        elif self._is_markdown(self._buffer):
            self._print_markdown(self._buffer)
        else:
            self._print_plain(self._buffer)
    
    def print_final(self, response: ModelResponse) -> None:
        """打印最终结果"""
        if response.error:
            self.console.print(f"[red]错误: {response.error}[/red]")
            return
        
        content = response.content
        
        # 根据内容类型选择渲染方式
        if self._is_code(content):
            self._print_code(content)
        elif self._is_markdown(content):
            self._print_markdown(content)
        else:
            self._print_plain(content)
        
        # 统计信息
        self._print_stats(response)
    
    def _is_code(self, text: str) -> bool:
        """判断是否为代码"""
        return "```" in text or text.startswith("    ") or "def " in text or "class " in text
    
    def _is_markdown(self, text: str) -> bool:
        """判断是否为 Markdown"""
        lines = text.split("\n")
        for line in lines[:10]:  # 只检查前几行
            line = line.strip()
            if line.startswith("# ") or line.startswith("## ") or line.startswith("**"):
                return True
        return False
    
    def _print_code(self, code: str) -> None:
        """打印代码"""
        # 提取语言
        language = "python"
        if "```" in code:
            import re
            match = re.search(r"```(\w+)", code)
            if match:
                language = match.group(1)
        
        syntax = Syntax(code.strip(), language, theme="monokai", line_numbers=True)
        self.console.print(syntax)
    
    def _print_markdown(self, content: str) -> None:
        """打印 Markdown"""
        md = Markdown(content.strip(), code_theme="monokai")
        self.console.print(md)
    
    def _print_plain(self, content: str) -> None:
        """打印纯文本"""
        self.console.print(content.strip())
    
    def _print_stats(self, response: ModelResponse) -> None:
        """打印统计信息"""
        if not response.input_tokens:
            return
        
        stats = (
            f"[dim]│ 模型: {response.model} "
            f"│ 输入: {response.input_tokens} tokens "
            f"│ 输出: {response.output_tokens} tokens "
            f"│ 费用: ¥{response.cost:.6f} "
            f"│ 延迟: {response.latency_ms:.0f}ms[/dim]"
        )
        self.console.print(stats)


async def stream_to_console(
    chunks: AsyncIterator[StreamChunk],
    response: ModelResponse,
    console: Console = None,
    color: bool = True
) -> ModelResponse:
    """将流式输出到控制台"""
    output = StreamOutput(console, color)
    full_content = ""
    
    async for chunk in chunks:
        if chunk.delta:
            full_content += chunk.delta
            output.print_chunk(chunk)
    
    response.content = full_content
    return response


def print_response_pretty(response: ModelResponse, color: bool = True) -> None:
    """格式化打印响应"""
    console = Console(color=color)
    output = StreamOutput(console, color)
    output.print_final(response)
