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
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
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
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        sessions = set(self._sessions.keys())
        
        # 扫描会话目录
        if self.sessions_dir.exists():
            for f in self.sessions_dir.glob("*.json"):
                sessions.add(f.stem)
        
        return sorted(list(sessions))
    
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


# 全局会话管理器
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取全局会话管理器"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
