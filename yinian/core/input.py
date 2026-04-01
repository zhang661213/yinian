"""
Yinian 管道与文件输入处理
"""
import sys
import os
from pathlib import Path
from typing import Optional, Union

from loguru import logger


class InputHandler:
    """输入处理器"""
    
    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {
        ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx",
        ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
        ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs", ".rb",
        ".php", ".swift", ".kt", ".scala", ".r", ".sql", ".sh",
        ".bat", ".ps1", ".log", ".csv", ".ini", ".conf", ".cfg",
    }
    
    # 文件大小限制 (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # 支持的编码
    ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]
    
    def __init__(self):
        self._stdin_text: Optional[str] = None
    
    def is_pipe_input(self) -> bool:
        """检测是否有管道输入"""
        try:
            if sys.stdin.isatty():
                return False
        except:
            return False
        
        # Windows 下不使用 select，直接尝试读取少量内容来检测
        try:
            import msvcrt
            import os
            
            # Windows: 检查 stdin 是否有可读内容
            if msvcrt.kbhit():
                return True
            
            # 回退：检查是否是重定向
            try:
                # 尝试获取 stdin 的 fileno
                fd = sys.stdin.fileno()
                if fd is not None:
                    # 检查是否是管道/重定向
                    mode = os.fstat(fd).st_mode
                    if not (mode & 0x8000):  # 不是普通文件
                        return True
            except:
                pass
            
        except Exception:
            pass
        
        return False
    
    def read_stdin(self) -> Optional[str]:
        """读取管道输入"""
        if self._stdin_text is not None:
            return self._stdin_text
        
        try:
            # 读取所有 stdin 内容
            content = sys.stdin.read()
            if content:
                self._stdin_text = content.strip()
                logger.debug(f"读取管道输入: {len(content)} 字符")
                return self._stdin_text
        except Exception as e:
            logger.error(f"读取管道输入失败: {e}")
        
        return None
    
    def read_file(self, path: Union[str, Path]) -> Optional[str]:
        """读取文件内容
        
        Args:
            path: 文件路径
            
        Returns:
            文件内容，如果读取失败返回 None
        """
        file_path = Path(path).expanduser().resolve()
        
        # 检查文件是否存在
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return None
        
        # 检查是否是文件
        if not file_path.is_file():
            logger.error(f"不是文件: {file_path}")
            return None
        
        # 检查扩展名
        ext = file_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"不支持的文件类型: {ext}")
            # 仍然尝试读取
        
        # 检查文件大小
        file_size = file_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            logger.error(f"文件过大: {file_size} bytes (最大 {self.MAX_FILE_SIZE})")
            return None
        
        # 尝试多种编码读取
        content = self._read_with_encoding(file_path)
        
        if content:
            logger.debug(f"读取文件: {file_path} ({len(content)} 字符)")
        
        return content
    
    def _read_with_encoding(self, path: Path) -> Optional[str]:
        """尝试多种编码读取文件"""
        for encoding in self.ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as f:
                    content = f.read()
                    # 验证内容
                    if self._is_valid_text(content):
                        return content
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.error(f"读取文件失败 ({encoding}): {e}")
                break
        
        return None
    
    def _is_valid_text(self, content: str) -> bool:
        """验证是否是有效的文本"""
        if not content:
            return True
        
        # 检查是否包含大量不可打印字符
        non_printable = sum(1 for c in content if ord(c) < 32 and c not in "\n\r\t")
        ratio = non_printable / len(content) if len(content) > 0 else 0
        
        return ratio < 0.1
    
    def read_multiple_files(self, paths: list) -> dict:
        """读取多个文件
        
        Returns:
            {filename: content} 字典
        """
        results = {}
        
        for path in paths:
            content = self.read_file(path)
            if content is not None:
                results[str(path)] = content
        
        return results
    
    def format_file_content(self, path: Union[str, Path], content: str) -> str:
        """格式化文件内容为可发送的消息"""
        file_path = Path(path)
        ext = file_path.suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".sql": "sql",
            ".sh": "bash",
            ".bat": "batch",
            ".ps1": "powershell",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".toml": "toml",
            ".ini": "ini",
            ".conf": "conf",
            ".cfg": "cfg",
            ".log": "log",
            ".csv": "csv",
        }
        
        lang = lang_map.get(ext, "")
        filename = file_path.name
        
        if lang:
            return f"【文件: {filename} ({lang})】\n```{lang}\n{content}\n```"
        else:
            return f"【文件: {filename}】\n{content}"


def get_input_handler() -> InputHandler:
    """获取输入处理器实例"""
    return InputHandler()
