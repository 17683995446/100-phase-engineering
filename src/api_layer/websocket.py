"""
WebSocket 通信模块
支持实时双向通信，与现有 API 层完美集成
"""
import json
import uuid
from typing import Dict, Any, Optional, List, Callable, Set
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from src.utils.logger import logger
from src.utils.structured_logging import get_logger, LogContext
from src.utils.prometheus import PrometheusRegistry, Counter, Histogram
from src.api_layer.core import APIVersion


class WebSocketOp(Enum):
    """WebSocket 操作类型"""
    CONNECT = auto()
    DISCONNECT = auto()
    MESSAGE = auto()
    ERROR = auto()
    PING = auto()
    PONG = auto()


class WebSocketStatus(Enum):
    """WebSocket 连接状态"""
    CONNECTING = auto()
    OPEN = auto()
    CLOSING = auto()
    CLOSED = auto()


@dataclass
class WebSocketMessage:
    """WebSocket 消息对象"""
    op: WebSocketOp
    data: Optional[Dict[str, Any]] = None
    message_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "op": self.op.name.lower(),
            "data": self.data,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSocketMessage":
        """从字典创建消息对象"""
        op_name = data.get("op", "message").upper()
        try:
            op = WebSocketOp[op_name]
        except KeyError:
            op = WebSocketOp.MESSAGE

        return cls(
            op=op,
            data=data.get("data"),
            message_id=data.get("message_id", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            error=data.get("error"),
            metadata=data.get("metadata", {})
        )

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "WebSocketMessage":
        """从 JSON 字符串创建消息对象"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class WebSocketConnection:
    """WebSocket 连接对象"""
    connection_id: str
    path: str
    status: WebSocketStatus = WebSocketStatus.CONNECTING
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    subscriptions: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if not self.connection_id:
            self.connection_id = str(uuid.uuid4())


class WebSocketHandler:
    """WebSocket 处理器基类"""

    def on_connect(self, connection: WebSocketConnection) -> Optional[WebSocketMessage]:
        """连接建立时调用"""
        return None

    def on_message(self, connection: WebSocketConnection, message: WebSocketMessage) -> Optional[WebSocketMessage]:
        """收到消息时调用"""
        return None

    def on_disconnect(self, connection: WebSocketConnection) -> None:
        """连接关闭时调用"""
        pass

    def on_error(self, connection: WebSocketConnection, error: Exception) -> Optional[WebSocketMessage]:
        """错误发生时调用"""
        logger.error(f"WebSocket error for {connection.connection_id}: {str(error)}")
        return WebSocketMessage(
            op=WebSocketOp.ERROR,
            error=str(error)
        )


class EchoHandler(WebSocketHandler):
    """简单的 Echo 处理器，原样返回消息"""

    def on_message(self, connection: WebSocketConnection, message: WebSocketMessage) -> Optional[WebSocketMessage]:
        return WebSocketMessage(
            op=WebSocketOp.MESSAGE,
            data={
                "echo": message.data,
                "connection_id": connection.connection_id
            }
        )


class BroadcastHandler(WebSocketHandler):
    """广播处理器，支持向所有连接发送消息"""

    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}

    def on_connect(self, connection: WebSocketConnection) -> Optional[WebSocketMessage]:
        self.connections[connection.connection_id] = connection
        return WebSocketMessage(
            op=WebSocketOp.MESSAGE,
            data={
                "message": "Connected",
                "connection_id": connection.connection_id
            }
        )

    def on_message(self, connection: WebSocketConnection, message: WebSocketMessage) -> Optional[WebSocketMessage]:
        # 广播消息给所有连接
        return WebSocketMessage(
            op=WebSocketOp.MESSAGE,
            data={
                "from": connection.connection_id,
                "message": message.data
            }
        )

    def on_disconnect(self, connection: WebSocketConnection) -> None:
        if connection.connection_id in self.connections:
            del self.connections[connection.connection_id]


class WebSocketChannel:
    """WebSocket 频道，用于发布订阅模式"""

    def __init__(self, name: str):
        self.name = name
        self.subscribers: Set[str] = set()
        self.logger = get_logger(f"websocket_channel_{name}")

    def subscribe(self, connection_id: str) -> None:
        """订阅频道"""
        self.subscribers.add(connection_id)
        self.logger.info(f"Connection {connection_id} subscribed to {self.name}")

    def unsubscribe(self, connection_id: str) -> None:
        """取消订阅"""
        self.subscribers.discard(connection_id)
        self.logger.info(f"Connection {connection_id} unsubscribed from {self.name}")

    def get_subscribers(self) -> Set[str]:
        """获取所有订阅者"""
        return self.subscribers.copy()


class WebSocketRouter:
    """WebSocket 路由系统"""

    def __init__(self):
        self.routes: Dict[str, WebSocketHandler] = {}
        self.channels: Dict[str, WebSocketChannel] = {}
        self.logger = get_logger("websocket_router")

    def add_route(self, path: str, handler: WebSocketHandler, version: APIVersion = APIVersion.V1) -> None:
        """添加路由"""
        full_path = f"/{version.value}{path}"
        self.routes[full_path] = handler
        self.routes[path] = handler  # 同时支持带版本和不带版本的路径
        self.logger.info(f"Added WebSocket route: {full_path}")

    def get_handler(self, path: str) -> Optional[WebSocketHandler]:
        """获取处理器"""
        return self.routes.get(path)

    def get_or_create_channel(self, name: str) -> WebSocketChannel:
        """获取或创建频道"""
        if name not in self.channels:
            self.channels[name] = WebSocketChannel(name)
        return self.channels[name]


class WebSocketApp:
    """WebSocket 应用核心类"""

    def __init__(self, name: str = "maes-websocket", prom_registry: Optional[PrometheusRegistry] = None):
        self.name = name
        self.router = WebSocketRouter()
        self.connections: Dict[str, WebSocketConnection] = {}
        self.logger = get_logger("websocket_app")

        # 指标收集
        self.prom_registry = prom_registry or PrometheusRegistry(namespace=name)
        self.connection_count = self.prom_registry.create_gauge(
            "websocket_connections",
            "当前 WebSocket 连接数"
        )
        self.message_counter = self.prom_registry.create_counter(
            "websocket_messages_total",
            "WebSocket 消息总数"
        )
        self.error_counter = self.prom_registry.create_counter(
            "websocket_errors_total",
            "WebSocket 错误总数"
        )

        # 注册默认处理器
        self.router.add_route("/echo", EchoHandler())
        self.router.add_route("/broadcast", BroadcastHandler())

        self.logger.info(f"WebSocket App initialized: {name}")

    def handle_connect(self, path: str, headers: Dict[str, str] = None, query_params: Dict[str, Any] = None) -> WebSocketConnection:
        """处理连接建立"""
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            path=path,
            status=WebSocketStatus.OPEN,
            headers=headers or {},
            query_params=query_params or {},
            connected_at=datetime.now()
        )

        self.connections[connection.connection_id] = connection
        self.connection_count.inc()
        self.logger.info(f"WebSocket connected: {connection.connection_id} at {path}")

        # 调用处理器的 on_connect
        handler = self.router.get_handler(path)
        if handler:
            response = handler.on_connect(connection)
            # 这里可以发送响应消息

        return connection

    def handle_message(self, connection: WebSocketConnection, message: WebSocketMessage) -> Optional[WebSocketMessage]:
        """处理收到的消息"""
        self.message_counter.inc()
        connection.last_activity = datetime.now()

        self.logger.debug(
            f"Received message: {message.op} from {connection.connection_id}",
            message_id=message.message_id
        )

        # 处理 PING
        if message.op == WebSocketOp.PING:
            return WebSocketMessage(op=WebSocketOp.PONG)

        # 查找处理器
        handler = self.router.get_handler(connection.path)
        if handler:
            try:
                response = handler.on_message(connection, message)
                return response
            except Exception as e:
                self.error_counter.inc()
                error_response = handler.on_error(connection, e)
                return error_response

        return None

    def handle_disconnect(self, connection: WebSocketConnection) -> None:
        """处理连接断开"""
        connection.status = WebSocketStatus.CLOSED

        if connection.connection_id in self.connections:
            del self.connections[connection.connection_id]
            self.connection_count.dec()

        self.logger.info(f"WebSocket disconnected: {connection.connection_id}")

        # 调用处理器的 on_disconnect
        handler = self.router.get_handler(connection.path)
        if handler:
            handler.on_disconnect(connection)

    def add_route(self, path: str, handler: WebSocketHandler, version: APIVersion = APIVersion.V1) -> None:
        """添加路由（便捷方法）"""
        self.router.add_route(path, handler, version)

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """获取连接"""
        return self.connections.get(connection_id)

    def get_all_connections(self) -> List[WebSocketConnection]:
        """获取所有连接"""
        return list(self.connections.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "active_connections": len(self.connections),
            "routes": list(self.router.routes.keys()),
            "channels": list(self.router.channels.keys())
        }


def create_text_message(data: Any) -> WebSocketMessage:
    """创建文本消息"""
    return WebSocketMessage(
        op=WebSocketOp.MESSAGE,
        data=data
    )


def create_error_message(error: str, data: Dict[str, Any] = None) -> WebSocketMessage:
    """创建错误消息"""
    return WebSocketMessage(
        op=WebSocketOp.ERROR,
        data=data,
        error=error
    )


# 全局应用实例
_default_ws_app: Optional[WebSocketApp] = None


def get_default_ws_app() -> WebSocketApp:
    """获取默认 WebSocket 应用"""
    global _default_ws_app
    if _default_ws_app is None:
        _default_ws_app = WebSocketApp()
    return _default_ws_app


def set_default_ws_app(app: WebSocketApp) -> None:
    """设置默认 WebSocket 应用"""
    global _default_ws_app
    _default_ws_app = app
