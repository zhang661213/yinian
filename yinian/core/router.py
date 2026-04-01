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
    
    # 代码相关关键词（用 IGNORECASE 标志，不用 \b 避免中英混合失效）
    CODE_KEYWORDS = [
        # 编程语言
        r"(python|java|javascript|js|ts|typescript|c\+\+|cpp|c#|go|rust|ruby|php|swift|kotlin|sql|html|css|react|vue|angular|node|django|flask|spring)",
        # 中文代码词
        r"(函数|方法|类|变量|数组|对象|接口|模块|包|库|代码|编程|开发|程序|算法|数据结构|递归|循环|排序|查找)",
        # 英文代码词
        r"(def|class|import|from|return|if|else|for|while|try|except|finally|with|as|lambda|yield|code|function|variable|array|object|method|api|loop|recursive|algorithm)",
        # 中文编程动作
        r"(编写|写一个|如何写|怎么写|实现|调用|执行|运行|编译|调试|debug)",
        # 代码块标记
        r"```",
        # 工具/软件
        r"(linux|git|docker|kubernetes|k8s|nginx|apache|mysql|redis|mongodb|postgresql)",
    ]
    
    # 数学相关关键词
    MATH_KEYWORDS = [
        r"(数学|计算|求解|方程|函数|几何|代数|微积分|积分|导数|概率|统计|排列组合|矩阵|向量|证明|推导|算法|推理|逻辑|博弈|优化)",
        r"(math|equation|calculate|solve|formula|sin|cos|tan|log|ln|sqrt)",
        r"[\+\-\*\/\=\^√∑∏∫]",  # 数学符号
        r"(\d+\^|\d+!)",  # 指数和阶乘
    ]
    
    # 中文内容关键词
    CHINESE_KEYWORDS = [
        r"[\u4e00-\u9fff]",  # 中文字符（任何连续中文）
        r"(中文|汉语|翻译成中文|用中文|中文回答|中文写作)",
        r"(写一篇|写一首|写一封信|写文案|写文章|写作文|写故事|写小说)",
        r"(总结|概括|归纳|缩写|扩写|改写)",
    ]
    
    # 英文内容关键词
    ENGLISH_KEYWORDS = [
        r"(translate to english|translation to english|translate to chinese)",
        r"(write an article|write an essay|write a blog|write a post|write a story|write a novel)",
        r"(article|essay|blog post|english writing|english content)",
    ]
    
    # 快速问答关键词
    QUICK_KEYWORDS = [
        r"(是什么|who is|what is|什么是|什么叫|请问|问一下|帮我查|查询|搜索|查找)",
        r"(解释|说明|讲讲|介绍一下)",
        r"^[A-Za-z0-9\s]{0,50}[?？]$",  # 短句英文问句（不含中文）
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
        
        # 代码检测（最高优先级）
        if self.code_pattern.search(question):
            scores[QuestionType.CODE] = 0.95
            if "```" in question or "`" in question:
                scores[QuestionType.CODE] = 1.0
        
        # 数学检测
        if self.math_pattern.search(question):
            scores[QuestionType.MATH] = 0.85
        
        # 中文内容检测（低优先级，不覆盖代码检测）
        if scores[QuestionType.CODE] < 0.5:
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
    
    def route(self, question: str, cheap: bool = False) -> RouterResult:
        """
        路由问题到最合适的模型
        
        智能适配：根据用户实际配置的模型动态决定路由，
        优先使用有 API Key 的模型，同时保持任务类型适配性。
        
        Args:
            question: 用户问题
            cheap: True=选最便宜的, False=选配置指定的模型
            
        Returns:
            RouterResult: 路由结果
        """
        # 分类问题
        qtype, confidence = self.classifier.classify(question)
        reason = self.classifier.get_reason(question, qtype)
        
        available_models = self.factory.list_enabled_models()
        
        # 获取对应模型
        if cheap:
            # --fast 模式：按任务类型选最便宜的
            model_name = self._find_cheapest_for_type(qtype, available_models)
        else:
            # 正常模式：按任务类型选最合适的（考虑偏好）
            model_name = self._find_best_for_type(qtype, available_models)
        
        # 构建备用模型列表
        fallback = [m for m in available_models if m != model_name]
        
        logger.debug(
            f"路由结果: 问题类型={qtype.value}, "
            f"模型={model_name}, 置信度={confidence:.2f}, cheap={cheap}"
        )
        
        return RouterResult(
            model_name=model_name,
            question_type=qtype,
            confidence=confidence,
            reason=reason,
            fallback_models=fallback
        )
    
    # 各问题类型偏好的模型列表（按优先级排序，优先选有 key 的）
    # 这个列表体现了"最适合"而非"最便宜"
    TYPE_PREFERENCE = {
        "code": ["zhipu", "deepseek", "qwen", "kimi", "doubao"],
        "math": ["deepseek", "zhipu", "qwen", "kimi", "doubao"],
        "chinese": ["doubao", "kimi", "deepseek", "qwen", "zhipu"],
        "english": ["qwen", "zhipu", "deepseek", "doubao", "kimi"],
        "quick": ["deepseek", "qwen", "zhipu", "doubao", "kimi"],
        "general": ["deepseek", "qwen", "zhipu", "doubao", "kimi"],
    }
    
    def _find_best_for_type(
        self,
        qtype: "QuestionType",
        available_models: List[str]
    ) -> str:
        """
        针对问题类型，智能选最合适的模型。
        
        策略：
        1. 从 TYPE_PREFERENCE 读取该类型的偏好模型列表
        2. 在偏好列表中，找第一个有真实 API Key 的模型
        3. 如果偏好列表都没有 Key → 从 available_models 中选最便宜的
        4. 如果 available_models 也没有 → 用本地模型
        """
        if not available_models:
            # 没有任何云端模型 → 用本地模型
            return self._get_local_fallback()
        
        # 获取该问题类型偏好的模型列表
        preference = self.TYPE_PREFERENCE.get(qtype.value, self.TYPE_PREFERENCE["general"])
        
        # 第一步：在偏好列表中找有 API Key 的
        for name in preference:
            if name not in available_models:
                continue
            info = self.factory.get_model_info(name)
            if not info:
                continue
            if info.get("is_local", False):
                continue  # 跳过本地模型
            if info["has_api_key"]:
                logger.debug(f"路由 [{qtype.value}]: 偏好模型 {name} 有 API Key，直接使用")
                return name
        
        # 第二步：没有偏好模型有 Key，按费用排序选最便宜的
        candidates = []
        for name in available_models:
            info = self.factory.get_model_info(name)
            if not info or info.get("is_local", False):
                continue
            if info["has_api_key"]:
                total = info["cost_per_1k_input"] + info["cost_per_1k_output"]
                candidates.append((total, name))
        
        if candidates:
            candidates.sort(key=lambda x: x[0])
            cheapest = candidates[0][1]
            logger.debug(f"路由 [{qtype.value}]: 偏好模型都无 Key，选用最便宜的 {cheapest}")
            return cheapest
        
        # 第三步：没有任何有 Key 的云端模型 → 用本地模型
        return self._get_local_fallback()
    
    def _get_local_fallback(self) -> str:
        """获取本地模型兜底"""
        for name in self.factory.list_models():
            info = self.factory.get_model_info(name)
            if info and info.get("is_local", False):
                return name
        return "deepseek"
    
    def _find_cheapest_for_type(
        self,
        qtype: "QuestionType",
        available_models: List[str]
    ) -> str:
        """
        针对问题类型，选最便宜的模型（忽略偏好，直接按费用排序）。
        
        策略：
        1. 从 available_models 中筛选有 API Key 的云端模型
        2. 按 (input_cost + output_cost) 升序排列
        3. 返回最便宜的；如果没有有 Key 的模型 → 用本地模型
        """
        if not available_models:
            return self._get_local_fallback()
        
        candidates = []
        for name in available_models:
            info = self.factory.get_model_info(name)
            if not info:
                continue
            if info.get("is_local", False):
                continue
            if not info["has_api_key"]:
                continue
            total = info["cost_per_1k_input"] + info["cost_per_1k_output"]
            candidates.append((total, name, info))
        
        if not candidates:
            return self._get_local_fallback()
        
        # 按总费用升序，相同费用按偏好顺序
        preference = self.TYPE_PREFERENCE.get(qtype.value, [])
        candidates.sort(key=lambda x: (x[0], preference.index(x[1]) if x[1] in preference else 999))
        
        logger.debug(f"路由 [{qtype.value}] (cheap): 选用最便宜的 {candidates[0][1]} (¥{candidates[0][0]:.4f}/1K)")
        return candidates[0][1]
    
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
