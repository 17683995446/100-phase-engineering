"""
WebSocket管理器
提供WebSocket连接管理、消息广播和房间功能
"""
import threading
import json
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class ConnectionStatus(Enum):
    """连接状态"""
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    ERROR = auto()


@dataclass
class WebSocketConnection:
    """WebSocket连接"""
    connection_id: str
    client_id: str = ""
    status: ConnectionStatus = ConnectionStatus.CONNECTING
    rooms: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    connected_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "client_id": self.client_id,
            "status": self.status.name,
            "rooms": list(self.rooms),
            "connected_at": self.connected_at.isoformat() if self.connected_at else None
        }


class WebSocketManager:
    """WebSocket管理器"""
    
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._rooms: Dict[str, Set[str]] = {}
        self._message_handlers: List[Callable] = []
        self._lock = threading.RLock()
        self._logger = get_logger("websocket.manager")
    
    def connect(self, connection_id: str, client_id: str = "",
                metadata: Optional[Dict[str, Any]] = None) -> WebSocketConnection:
        """连接"""
        connection = WebSocketConnection(
            connection_id=connection_id,
            client_id=client_id,
            status=ConnectionStatus.CONNECTED,
            metadata=metadata or {},
            connected_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        with self._lock:
            self._connections[connection_id] = connection
        
        self._logger.info(f"WebSocket connected: {connection_id}")
        return connection
    
    def disconnect(self, connection_id: str) -> bool:
        """断开连接"""
        with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False
            
            # 从所有房间移除
            for room in list(connection.rooms):
                self._leave_room(connection_id, room)
            
            connection.status = ConnectionStatus.DISCONNECTED
            del self._connections[connection_id]
        
        self._logger.info(f"WebSocket disconnected: {connection_id}")
        return True
    
    def join_room(self, connection_id: str, room: str) -> bool:
        """加入房间"""
        with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False
            
            connection.rooms.add(room)
            
            if room not in self._rooms:
                self._rooms[room] = set()
            self._rooms[room].add(connection_id)
        
        self._logger.info(f"Connection {connection_id} joined room: {room}")
        return True
    
    def leave_room(self, connection_id: str, room: str) -> bool:
        """离开房间"""
        with self._lock:
            return self._leave_room(connection_id, room)
    
    def _leave_room(self, connection_id: str, room: str) -> bool:
        """离开房间（内部）"""
        connection = self._connections.get(connection_id)
        if connection:
            connection.rooms.discard(room)
        
        if room in self._rooms:
            self._rooms[room].discard(connection_id)
            if not self._rooms[room]:
                del self._rooms[room]
        
        return True
    
    def send_to_connection(self, connection_id: str, 
                           message: Dict[str, Any]) -> bool:
        """发送消息到指定连接"""
        with self._lock:
            connection = self._connections.get(connection_id)
            if not connection or connection.status != ConnectionStatus.CONNECTED:
                return False
            
            connection.last_activity = datetime.now()
        
        self._logger.info(f"Message sent to {connection_id}: {message.get('type', 'unknown')}")
        return True
    
    def broadcast(self, message: Dict[str, Any],
                  exclude: Optional[List[str]] = None) -> int:
        """广播消息"""
        exclude_set = set(exclude or [])
        count = 0
        
        with self._lock:
            connections = list(self._connections.keys())
        
        for connection_id in connections:
            if connection_id not in exclude_set:
                if self.send_to_connection(connection_id, message):
                    count += 1
        
        return count
    
    def broadcast_to_room(self, room: str, message: Dict[str, Any],
                          exclude: Optional[List[str]] = None) -> int:
        """广播到房间"""
        exclude_set = set(exclude or [])
        count = 0
        
        with self._lock:
            room_connections = list(self._rooms.get(room, set()))
        
        for connection_id in room_connections:
            if connection_id not in exclude_set:
                if self.send_to_connection(connection_id, message):
                    count += 1
        
        return count
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """获取连接"""
        with self._lock:
            return self._connections.get(connection_id)
    
    def get_room_connections(self, room: str) -> List[str]:
        """获取房间连接"""
        with self._lock:
            return list(self._rooms.get(room, set()))
    
    def get_all_connections(self) -> List[WebSocketConnection]:
        """获取所有连接"""
        with self._lock:
            return list(self._connections.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "connections": len(self._connections),
                "rooms": len(self._rooms),
                "total_room_members": sum(len(members) for members in self._rooms.values())
            }
    
    def add_message_handler(self, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        """添加消息处理器"""
        self._message_handlers.append(handler)
    
    def handle_message(self, connection_id: str, message: Dict[str, Any]) -> None:
        """处理消息"""
        for handler in self._message_handlers:
            try:
                handler(connection_id, message)
            except Exception as e:
                self._logger.error(f"Message handler error: {e}")


# 全局实例
_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """获取WebSocket管理器"""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager
