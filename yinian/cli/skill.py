"""
Yinian CLI - 技能命令
"""
import sys
import importlib.util
import os
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from yinian.core.config import get_config, get_skills_dir

console = Console()


class Skill:
    """技能"""
    
    def __init__(self, name: str, path: Path, module):
        self.name = name
        self.path = path
        self.module = module
    
    @property
    def description(self) -> str:
        return getattr(self.module, "description", "无描述")
    
    @property
    def author(self) -> str:
        return getattr(self.module, "author", "未知")
    
    @property
    def version(self) -> str:
        return getattr(self.module, "version", "1.0.0")
    
    def run(self, args: List[str]) -> str:
        """运行技能"""
        run_fn = getattr(self.module, "run", None)
        if run_fn is None:
            raise Exception(f"技能 {self.name} 未定义 run() 函数")
        return run_fn(args)


def load_skill(name: str) -> Optional[Skill]:
    """加载指定技能"""
    skills_dir = get_skills_dir()
    skill_path = skills_dir / f"{name}.py"
    
    if not skill_path.exists():
        return None
    
    try:
        spec = importlib.util.spec_from_file_location(f"yinian_skill_{name}", skill_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"yinian_skill_{name}"] = module
        spec.loader.exec_module(module)
        return Skill(name, skill_path, module)
    except Exception as e:
        console.print(f"[red]加载技能失败: {e}[/red]")
        return None


def list_skills() -> List[Skill]:
    """列出所有技能"""
    skills_dir = get_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    skills = []
    for py_file in skills_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        name = py_file.stem
        skill = load_skill(name)
        if skill:
            skills.append(skill)
    return skills


@click.group(name="skill")
def skill_group():
    """技能管理命令"""
    pass


@skill_group.command(name="list")
def skill_list():
    """列出所有已安装的技能"""
    skills = list_skills()
    
    console.print("\n[bold cyan]📦 一念技能[/bold cyan]\n")
    
    if not skills:
        console.print("[dim]暂无技能，运行以下命令安装：[/dim]")
        console.print("  [cyan]yinian skill install <技能文件>[/cyan]")
        console.print("\n[dim]技能目录:[/dim]")
        console.print(f"  {get_skills_dir()}")
        console.print()
        return
    
    table = Table(show_header=True)
    table.add_column("名称")
    table.add_column("描述")
    table.add_column("作者")
    table.add_column("版本")
    table.add_column("文件")
    
    for skill in skills:
        table.add_row(
            skill.name,
            skill.description,
            skill.author,
            skill.version,
            skill.path.name,
        )
    
    console.print(table)
    console.print()
    console.print(f"[dim]技能目录: {get_skills_dir()}[/dim]\n")


@skill_group.command(name="run")
@click.argument("name")
@click.argument("args", nargs=-1, required=False)
def skill_run(name: str, args: tuple):
    """运行指定技能
    
    示例:
      yinian skill run 代码审查 --file main.py
      yinian skill run 翻译 你好世界 --from zh --to en
    """
    skill = load_skill(name)
    
    if skill is None:
        console.print(f"[red]技能不存在: {name}[/red]")
        console.print(f"[dim]技能目录: {get_skills_dir()}[/dim]")
        console.print()
        skills = list_skills()
        if skills:
            console.print("[dim]可用技能:[/dim]")
            for s in skills:
                console.print(f"  [cyan]{s.name}[/cyan] - {s.description}")
        return
    
    try:
        args_list = list(args) if args else []
        console.print(f"[dim]运行技能: {skill.name}[/dim]")
        console.print()
        
        result = skill.run(args_list)
        
        if result:
            console.print(result)
        else:
            console.print("[dim]（无输出）[/dim]")
    
    except Exception as e:
        console.print(f"[red]技能执行失败: {e}[/red]")
        import traceback
        traceback.print_exc()


@skill_group.command(name="install")
@click.argument("path", type=click.Path(exists=True))
@click.option("--name", "-n", help="指定技能名称（默认用文件名）")
def skill_install(path: str, name: Optional[str]):
    """安装技能（从文件或目录）
    
    示例:
      yinian skill install ./my-skill.py
      yinian skill install ./my-skill/ --name custom
    """
    src = Path(path)
    skills_dir = get_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    if src.is_file():
        # 单文件技能
        skill_name = name or src.stem
        dest = skills_dir / f"{skill_name}.py"
        import shutil
        shutil.copy2(src, dest)
        console.print(f"[green]✓ 已安装技能: {skill_name}[/green]")
        console.print(f"  路径: {dest}")
    
    elif src.is_dir():
        # 目录技能
        skill_name = name or src.name
        dest = skills_dir / f"{skill_name}.py"
        # 找目录中的 .py 文件（排除 __init__.py）
        py_files = list(src.glob("*.py"))
        if not py_files:
            console.print(f"[red]目录中没有 .py 文件[/red]")
            return
        # 取第一个非 __init__.py 的文件
        main_file = next((f for f in py_files if f.name != "__init__.py"), py_files[0])
        import shutil
        shutil.copy2(main_file, dest)
        console.print(f"[green]✓ 已安装技能: {skill_name}[/green]")
        console.print(f"  源文件: {main_file}")
        console.print(f"  安装路径: {dest}")


@skill_group.command(name="uninstall")
@click.argument("name")
def skill_uninstall(name: str):
    """卸载技能
    
    示例:
      yinian skill uninstall my-skill
    """
    skills_dir = get_skills_dir()
    skill_path = skills_dir / f"{name}.py"
    
    if not skill_path.exists():
        console.print(f"[yellow]技能不存在: {name}[/yellow]")
        return
    
    skill_path.unlink()
    console.print(f"[green]✓ 已卸载技能: {name}[/green]")


@skill_group.command(name="init")
def skill_init():
    """初始化技能目录，创建示例技能
    
    示例:
      yinian skill init
    """
    skills_dir = get_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    sample = skills_dir / "hello.py"
    if sample.exists():
        console.print(f"[yellow]示例技能已存在: {sample}[/yellow]")
        return
    
    sample.write_text('''"""
一念技能示例 - Hello World
"""
description = "打招呼技能"
author = "一念"
version = "1.0.0"


def run(args: list[str]) -> str:
    """运行技能
    
    Args:
        args: 命令行参数列表
    
    Returns:
        str: 技能输出
    """
    name = args[0] if args else "世界"
    return f"你好，{name}！来自一念技能系统 🎉"


if __name__ == "__main__":
    import sys
    print(run(sys.argv[1:]))
''', encoding="utf-8")
    
    console.print(f"[green]✓ 已创建示例技能:[/green]")
    console.print(f"  {sample}")
    console.print()
    console.print("[dim]查看示例:[/dim]")
    console.print(f"  yinian skill run hello 一念")
    console.print()
    console.print("[dim]查看所有技能:[/dim]")
    console.print(f"  yinian skill list")
