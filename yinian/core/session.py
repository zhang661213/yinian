"""
Yinian 会话管理
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from yinian.core.config import get_config


@dataclass
class Message:
    """消息"""
    role: str  # user / assistant / system
    content: str
    timestamp: str = ""
    model: str = ""
    tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "model": self.model,
            "tokens": self.tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
            model=data.get("model", ""),
            tokens=data.get("tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            cost=data.get("cost", 0.0),
        )


@dataclass
class Session:
    """会话"""
    name: str
    messages: List[Message] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    total_tokens: int = 0
    total_cost: float = 0.0
    important: bool = False          # 是否标记为重要
    summary: str = ""              # AI 生成的会话摘要
    auto_important_reason: str = ""  # 自动标记为重要的原因
    
    # 自动重要的判断阈值
    AUTO_IMPORTANT_MIN_ROUNDS = 5      # 至少5轮对话
    AUTO_IMPORTANT_MIN_TOKENS = 1500    # 至少消耗1500 tokens
    AUTO_IMPORTANT_MIN_COST = 0.005     # 至少消耗 ¥0.005
    AUTO_IMPORTANT_KEYWORDS = [
        "代码", "bug", "架构", "设计", "方案", "部署", "测试",
        "数据库", "接口", "API", "算法", "优化", "性能",
        "重构", "审查", "review", "code", "git",
        "服务器", "docker", "k8s", "CI/CD",
    ]
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
        if message.tokens:
            self.total_tokens += message.tokens
        if message.cost:
            self.total_cost += message.cost
    
    def is_important(self) -> bool:
        """判断是否为重要会话"""
        return self.important
    
    def mark_important(self, reason: str = "手动标记") -> None:
        """标记为重要"""
        self.important = True
        self.auto_important_reason = reason
        logger.info(f"会话 {self.name} 已标记为重要: {reason}")
    
    def unmark_important(self) -> None:
        """取消重要标记"""
        self.important = False
        self.auto_important_reason = ""
        logger.info(f"会话 {self.name} 已取消重要标记")
    
    def check_auto_important(self) -> bool:
        """自动检查是否应该标记为重要（检查并自动设置）"""
        if self.important:
            return True
        
        # 1. 多轮对话
        user_msgs = [m for m in self.messages if m.role == "user"]
        if len(user_msgs) >= self.AUTO_IMPORTANT_MIN_ROUNDS:
            self.mark_important(f"多轮对话（{len(user_msgs)}轮）")
            return True
        
        # 2. Token 消耗
        if self.total_tokens >= self.AUTO_IMPORTANT_MIN_TOKENS:
            self.mark_important(f"大量 Token（{self.total_tokens}）")
            return True
        
        # 3. 费用
        if self.total_cost >= self.AUTO_IMPORTANT_MIN_COST:
            self.mark_important(f"高消耗（¥{self.total_cost:.4f}）")
            return True
        
        # 4. 关键词
        all_text = " ".join(m.content for m in self.messages).lower()
        matched = [kw for kw in self.AUTO_IMPORTANT_KEYWORDS if kw.lower() in all_text]
        if matched:
            self.mark_important(f"包含关键词：{', '.join(matched[:3])}")
            return True
        
        return False
    
    def generate_summary_text(self) -> str:
        """生成会话摘要文本"""
        if len(self.messages) <= 2:
            return "简短问答，无需摘要"
        
        user_msgs = [m for m in self.messages if m.role == "user"]
        topics = [m.content[:80].strip() for m in user_msgs[:5] if m.content.strip()]
        
        lines = [
            f"会话: {self.name}",
            f"时间: {self.created_at[:19]}",
            f"轮次: {len(user_msgs)}轮",
            f"Token: {self.total_tokens:,} │ 费用: ¥{self.total_cost:.4f}",
            f"重要: {'✓ 是' if self.important else '✗ 否'}",
        ]
        if self.messages:
            lines.append(f"首问: {self.messages[0].content[:80].strip()}...")
        if topics:
            lines.append(f"话题 ({len(topics)}):")
            for t in topics[:3]:
                lines.append(f"  • {t[:70]}...")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "important": self.important,
            "summary": self.summary,
            "auto_important_reason": self.auto_important_reason,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            name=data.get("name", "default"),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            important=data.get("important", False),
            summary=data.get("summary", ""),
            auto_important_reason=data.get("auto_important_reason", ""),
        )
    
    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """获取发送给 API 的消息格式"""
        return [{"role": m.role, "content": m.content} for m in self.messages]
    
    def count_tokens(self) -> int:
        """估算总 token 数"""
        total = 0
        for m in self.messages:
            total += m.tokens or len(m.content) // 4  # 简单估算
        return total


class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.config = get_config()
        self.sessions_dir = self.config.sessions_dir
        self._sessions: Dict[str, Session] = {}
        self._current_session: Optional[Session] = None
        self._current_name: str = "default"
    
    def _get_session_file(self, name: str) -> Path:
        """获取会话文件路径"""
        return self.sessions_dir / f"{name}.json"
    
    def create_session(self, name: str) -> Session:
        """创建会话"""
        session = Session(name=name)
        self._sessions[name] = session
        self.save_session(name)
        logger.debug(f"创建会话: {name}")
        return session
    
    def get_session(self, name: str) -> Optional[Session]:
        """获取会话"""
        if name in self._sessions:
            return self._sessions[name]
        
        # 从文件加载
        session_file = self._get_session_file(name)
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = Session.from_dict(data)
                self._sessions[name] = session
                return session
            except Exception as e:
                logger.error(f"加载会话失败: {e}")
        
        return None
    
    def save_session(self, name: str) -> None:
        """保存会话"""
        if name not in self._sessions:
            return
        
        session = self._sessions[name]
        session_file = self._get_session_file(name)
        
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"保存会话: {name}")
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
    
    def delete_session(self, name: str) -> bool:
        """删除会话"""
        if name not in self._sessions and not self._get_session_file(name).exists():
            return False
        
        # 删除内存中的
        if name in self._sessions:
            del self._sessions[name]
        
        # 删除文件
        session_file = self._get_session_file(name)
        if session_file.exists():
            session_file.unlink()
        
        # 如果删除的是当前会话，切换到 default
        if self._current_name == name:
            self._current_name = "default"
            self._current_session = None
        
        logger.debug(f"删除会话: {name}")
        return True
    
    def list_sessions(self, important_only: bool = False, include_details: bool = False) -> List:
        """列出所有会话
        
        Args:
            important_only: 仅返回重要的会话
            include_details: 是否返回详细信息（用于表格显示）
        """
        sessions = {}
        
        # 从文件扫描
        if self.sessions_dir.exists():
            for f in self.sessions_dir.glob("*.json"):
                try:
                    with open(f, encoding="utf-8") as fp:
                        data = json.load(fp)
                    session = Session.from_dict(data)
                    sessions[session.name] = session
                except Exception:
                    continue
        
        # 从内存补充
        sessions.update(self._sessions)
        
        # 过滤
        if important_only:
            sessions = {n: s for n, s in sessions.items() if s.important}
        
        if include_details:
            result = []
            for name, s in sorted(sessions.items()):
                user_msgs = [m for m in s.messages if m.role == "user"]
                result.append({
                    "name": name,
                    "important": s.important,
                    "reason": s.auto_important_reason if s.important else "",
                    "rounds": len(user_msgs),
                    "tokens": s.total_tokens,
                    "cost": s.total_cost,
                    "updated": s.updated_at[:19] if s.updated_at else "-",
                })
            return result
        
        return sorted(sessions.keys())
    
    def clean_unimportant(
        self,
        older_than_days: int = 7,
        keep_min: int = 5,
        dry_run: bool = False,
    ) -> dict:
        """清理不重要会话
        
        Args:
            older_than_days: 删除多少天前的非重要会话
            keep_min: 最少保留多少个非重要会话
        
        Returns:
            清理统计 {"deleted": N, "kept": N, "details": [...]}
        """
        import time as time_module
        
        threshold = time_module.time() - (older_than_days * 86400)
        cutoff_date = datetime.fromtimestamp(threshold)
        
        # 收集所有会话
        all_sessions = self.list_sessions(include_details=True)
        
        deleted = []
        kept = []
        
        for info in all_sessions:
            name = info["name"]
            session = self.get_session(name)
            if not session:
                continue
            
            # 重要的永远保留
            if session.important:
                kept.append(name)
                continue
            
            # 检查是否超过清理日期
            try:
                updated = datetime.fromisoformat(info["updated"])
                is_old = updated < cutoff_date
            except Exception:
                is_old = True
            
            # 旧的 OR 超过最少保留数 → 删除
            can_delete = is_old or (len(all_sessions) - len(deleted) > keep_min)
            
            if can_delete:
                if not dry_run:
                    self.delete_session(name)
                deleted.append(name)
            else:
                kept.append(name)
        
        return {
            "deleted": len(deleted),
            "kept": len(kept),
            "details": deleted,
        }
    
    def switch_session(self, name: str) -> Session:
        """切换会话"""
        session = self.get_session(name)
        if session is None:
            session = self.create_session(name)
        
        self._current_session = session
        self._current_name = name
        return session
    
    @property
    def current(self) -> Session:
        """获取当前会话"""
        if self._current_session is None:
            self._current_session = self.get_session(self._current_name)
            if self._current_session is None:
                self._current_session = self.create_session(self._current_name)
        return self._current_session
    
    def add_to_current(self, role: str, content: str, **kwargs) -> Message:
        """添加消息到当前会话"""
        message = Message(
            role=role,
            content=content,
            model=kwargs.get("model", ""),
            tokens=kwargs.get("tokens", 0),
            cost=kwargs.get("cost", 0.0),
        )
        self.current.add_message(message)
        self.save_session(self._current_name)
        return message
    
    def clear_current(self) -> None:
        """清空当前会话"""
        self.current.messages.clear()
        self.current.total_tokens = 0
        self.current.total_cost = 0.0
        self.save_session(self._current_name)
    
    def get_history(self, limit: int = 50) -> List[Message]:
        """获取历史消息"""
        return self.current.messages[-limit:]
    
    def get_session_summary(self, name: str) -> str:
        """获取会话摘要"""
        session = self.get_session(name)
        if not session:
            return f"会话不存在: {name}"
        return session.generate_summary_text()
    
    def mark_current_important(self, reason: str = "手动标记") -> None:
        """标记当前会话为重要"""
        self.current.mark_important(reason)
        self.save_session(self._current_name)
    
    def unmark_current_important(self) -> None:
        """取消当前会话的重要标记"""
        self.current.unmark_important()
        self.save_session(self._current_name)


# 全局会话管理器
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取全局会话管理器"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
