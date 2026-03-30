"""
Yinian Core 模块
"""
from yinian.core.config import Config, get_config
from yinian.core.router import Router, get_router, QuestionClassifier, QuestionType

__all__ = [
    "Config",
    "get_config",
    "Router",
    "get_router",
    "QuestionClassifier",
    "QuestionType",
]
