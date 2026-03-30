"""
Yinian 智能路由引擎
根据问题类型自动选择最合适的模型
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from loguru import logger

from yinian.core.config import Config, get_config
from yinian.models.base import BaseModel
from yinian.models.factory import ModelFactory, get_factory


class QuestionType(Enum):
    """问题类型枚举"""
    CODE = "code"           # 代码相关
    MATH = "math"           # 数学/推理
    CHINESE = "chinese"     # 中文内容创作
    ENGLISH = "english"     # 英文内容
    QUICK = "quick"         # 快速问答
    GENERAL = "general"      # 通用问题


@dataclass
class RouterResult:
    """路由结果"""
    model_name: str
    question_type: QuestionType
    confidence: float  # 0.0 - 1.0
    reason: str
    fallback_models: List[str]  # 备用模型列表


class QuestionClassifier:
    """问题分类器"""
    
    # 代码相关关键词
    CODE_KEYWORDS = [
        r"\b(python|java|javascript|js|ts|typescript|c\+\+|cpp|c#|go|rust|ruby|php|swift|kotlin|sql|html|css|react|vue|angular|node|django|flask|spring)\b",
        r"\b(函数|方法|类|变量|数组|对象|接口|模块|包|库|代码|编程|开发|程序|算法|数据结构|递归|循环|排序|查找)\b",
        r"\b(def|class|import|from|return|if|else|for|while|try|except|finally|with|as|lambda|yield)\b",
        r"\b(code|function|class|variable|array|object|method|api|loop|recursive|algorithm)\b",
        r"\b(编写|写一个|如何写|怎么写|实现|调用|执行|运行|编译|调试|debug)\b",
        r"`{3}", r"```\w+",  # 代码块
        r"\b(linux|git|docker|kubernetes|k8s|nginx|apache|mysql|redis|mongodb|postgresql)\b",
    ]
    
    # 数学相关关键词
    MATH_KEYWORDS = [
        r"\b(数学|计算|求解|方程|函数|几何|代数|微积分|积分|导数|概率|统计|排列组合|矩阵|向量)\b",
        r"\b(证明|推导|计算|算法|推理|逻辑|博弈|优化|最小化|最大化)\b",
        r"\b(数学题|奥数|高考数学|考研数学|math|equation|calculate|solve|formula)\b",
        r"[\+\-\*\/\=\^√∑∏∫]",  # 数学符号
        r"\b(\d+\^|\d+!|sin|cos|tan|log|ln|sqrt)\b",
    ]
    
    # 中文内容关键词
    CHINESE_KEYWORDS = [
        r"[\u4e00-\u9fff]",  # 中文字符
        r"\b(中文|汉语|翻译成中文|用中文|中文回答)\b",
        r"\b(写一篇|写一首|写一封信|写文案|写文章|写作文|写故事|写小说)\b",
        r"\b(总结|概括|归纳|缩写|扩写|改写)\b",
    ]
    
    # 英文内容关键词
    ENGLISH_KEYWORDS = [
        r"\b(translate to english|english|翻译成英文|用英文)\b",
        r"\b(write an? |article|essay|blog|post|story|novel)\b",
        r"\b(english writing|english content|英文写作)\b",
    ]
    
    # 快速问答关键词
    QUICK_KEYWORDS = [
        r"\b(是什么|who is|what is|什么是|什么叫|请问|问一下)\b",
        r"\b(帮我查|查询|搜索|查找|找一下)\b",
        r"\b(解释|说明|讲讲|介绍一下)\b",
        r"^(?!.*[\u4e00-\u9fff]).{0,50}[?？]",  # 短句英文问句
    ]
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式"""
        self.code_pattern = re.compile("|".join(self.CODE_KEYWORDS), re.IGNORECASE)
        self.math_pattern = re.compile("|".join(self.MATH_KEYWORDS), re.IGNORECASE)
        self.chinese_pattern = re.compile("|".join(self.CHINESE_KEYWORDS), re.IGNORECASE)
        self.english_pattern = re.compile("|".join(self.ENGLISH_KEYWORDS), re.IGNORECASE)
        self.quick_pattern = re.compile("|".join(self.QUICK_KEYWORDS), re.IGNORECASE)
    
    def classify(self, question: str) -> Tuple[QuestionType, float]:
        """
        分类问题
        
        Args:
            question: 问题文本
            
        Returns:
            (问题类型, 置信度)
        """
        scores = {
            QuestionType.CODE: 0.0,
            QuestionType.MATH: 0.0,
            QuestionType.CHINESE: 0.0,
            QuestionType.ENGLISH: 0.0,
            QuestionType.QUICK: 0.0,
        }
        
        # 代码检测（高优先级）
        if self.code_pattern.search(question):
            scores[QuestionType.CODE] = 0.9
            # 检查是否是代码片段
            if "```" in question or "`" in question:
                scores[QuestionType.CODE] = 1.0
        
        # 数学检测
        if self.math_pattern.search(question):
            scores[QuestionType.MATH] = 0.85
        
        # 中文内容检测
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", question))
        total_chars = len(question)
        if total_chars > 0:
            chinese_ratio = chinese_chars / total_chars
            if chinese_ratio > 0.3:
                scores[QuestionType.CHINESE] = min(0.7, chinese_ratio)
        
        if self.chinese_pattern.search(question):
            scores[QuestionType.CHINESE] = max(scores[QuestionType.CHINESE], 0.8)
        
        # 英文内容检测
        if self.english_pattern.search(question):
            scores[QuestionType.ENGLISH] = 0.8
        
        # 快速问答检测（低优先级）
        if self.quick_pattern.search(question):
            scores[QuestionType.QUICK] = 0.6
        
        # 问题长度判断
        if len(question) < 30 and scores[QuestionType.QUICK] < 0.5:
            scores[QuestionType.QUICK] = max(scores[QuestionType.QUICK], 0.5)
        
        # 找出最高分
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # 如果最高分低于阈值，归为通用问题
        if best_score < 0.3:
            return QuestionType.GENERAL, 0.5
        
        return best_type, best_score
    
    def get_reason(self, question: str, qtype: QuestionType) -> str:
        """获取分类原因"""
        reasons = {
            QuestionType.CODE: "检测到代码相关关键词或代码格式",
            QuestionType.MATH: "检测到数学相关关键词或符号",
            QuestionType.CHINESE: "检测到中文内容或中文写作请求",
            QuestionType.ENGLISH: "检测到英文内容或英文写作请求",
            QuestionType.QUICK: "问题简短，判定为快速问答",
            QuestionType.GENERAL: "通用问题，使用默认模型",
        }
        return reasons.get(qtype, "未知类型")


class Router:
    """智能路由器"""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        factory: Optional[ModelFactory] = None
    ):
        self.config = config or get_config()
        self.factory = factory or get_factory()
        self.classifier = QuestionClassifier()
        
        # 加载路由规则
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict[str, str]:
        """从配置加载路由规则"""
        return self.config.get("router.rules", {
            "code": "deepseek",
            "math": "deepseek",
            "chinese": "kimi",
            "english": "qwen",
            "quick": "deepseek",
            "general": "deepseek",
        })
    
    def route(self, question: str) -> RouterResult:
        """
        路由问题到最合适的模型
        
        Args:
            question: 用户问题
            
        Returns:
            RouterResult: 路由结果
        """
        # 分类问题
        qtype, confidence = self.classifier.classify(question)
        reason = self.classifier.get_reason(question, qtype)
        
        # 获取对应模型
        model_key = qtype.value
        model_name = self.rules.get(model_key, self.rules.get("general", "deepseek"))
        
        # 验证模型是否可用
        available_models = self.factory.list_enabled_models()
        if model_name not in available_models:
            logger.warning(f"路由模型 {model_name} 不可用，尝试备用")
            if available_models:
                model_name = available_models[0]
            else:
                model_name = self.config.get_default_model()
        
        # 构建备用模型列表
        fallback = [m for m in available_models if m != model_name]
        
        logger.debug(
            f"路由结果: 问题类型={qtype.value}, "
            f"模型={model_name}, 置信度={confidence:.2f}"
        )
        
        return RouterResult(
            model_name=model_name,
            question_type=qtype,
            confidence=confidence,
            reason=reason,
            fallback_models=fallback
        )
    
    def route_with_models(
        self,
        question: str,
        model_names: List[str]
    ) -> List[Tuple[str, BaseModel, float]]:
        """
        为多模型对比进行路由
        
        Args:
            question: 用户问题
            model_names: 指定模型列表
            
        Returns:
            [(model_name, model_instance, priority), ...]
        """
        if not model_names:
            # 没有指定，使用路由结果
            result = self.route(question)
            model = self.factory.get_model(result.model_name)
            if model:
                return [(result.model_name, model, 1.0)]
            return []
        
        # 使用指定的模型
        models = []
        for name in model_names:
            model = self.factory.get_model(name)
            if model:
                # 第一个指定的模型优先级最高
                priority = len(model_names) - model_names.index(name)
                models.append((name, model, priority))
        
        return models
    
    def get_strategy(self) -> str:
        """获取当前路由策略"""
        return self.config.get("router.strategy", "auto")
    
    def set_rule(self, question_type: str, model_name: str) -> None:
        """
        设置路由规则
        
        Args:
            question_type: 问题类型 (code/math/chinese/english/quick/general)
            model_name: 模型名称
        """
        if question_type not in [t.value for t in QuestionType]:
            raise ValueError(f"未知问题类型: {question_type}")
        
        rules = self.rules.copy()
        rules[question_type] = model_name
        self.config.set("router.rules", rules)
        self.rules = rules
        
        logger.info(f"路由规则已更新: {question_type} -> {model_name}")


def get_router() -> Router:
    """获取路由器实例"""
    return Router()
