"""
Tests for WebSocket 通信模块 (Phase 29)
"""
import pytest
import json
from datetime import datetime

from src.api_layer.websocket import (
    WebSocketOp,
    WebSocketStatus,
    WebSocketMessage,
    WebSocketConnection,
    WebSocketHandler,
    EchoHandler,
    BroadcastHandler,
    WebSocketChannel,
    WebSocketRouter,
    WebSocketApp,
    create_text_message,
    create_error_message,
    get_default_ws_app,
    set_default_ws_app
)


class TestWebSocketOp:
    """测试 WebSocket 操作类型"""

    def test_enum_values(self):
        """测试枚举值"""
        assert WebSocketOp.CONNECT is not None
        assert WebSocketOp.DISCONNECT is not None
        assert WebSocketOp.MESSAGE is not None
        assert WebSocketOp.ERROR is not None
        assert WebSocketOp.PING is not None
        assert WebSocketOp.PONG is not None


class TestWebSocketStatus:
    """测试 WebSocket 状态"""

    def test_enum_values(self):
        """测试枚举值"""
        assert WebSocketStatus.CONNECTING is not None
        assert WebSocketStatus.OPEN is not None
        assert WebSocketStatus.CLOSING is not None
        assert WebSocketStatus.CLOSED is not None


class TestWebSocketMessage:
    """测试 WebSocket 消息"""

    def test_create_message(self):
        """测试创建消息"""
        msg = WebSocketMessage(op=WebSocketOp.MESSAGE, data={"key": "value"})
        assert msg.op == WebSocketOp.MESSAGE
        assert msg.data == {"key": "value"}
        assert msg.message_id != ""
        assert isinstance(msg.timestamp, datetime)

    def test_message_to_dict(self):
        """测试消息转换为字典"""
        msg = WebSocketMessage(op=WebSocketOp.MESSAGE, data={"hello": "world"})
        msg_dict = msg.to_dict()
        assert msg_dict["op"] == "message"
        assert msg_dict["data"] == {"hello": "world"}
        assert msg_dict["message_id"] == msg.message_id

    def test_message_from_dict(self):
        """测试从字典创建消息"""
        data = {
            "op": "message",
            "data": {"test": "data"},
            "message_id": "test-id"
        }
        msg = WebSocketMessage.from_dict(data)
        assert msg.op == WebSocketOp.MESSAGE
        assert msg.data == {"test": "data"}
        assert msg.message_id == "test-id"

    def test_message_json_serialization(self):
        """测试 JSON 序列化"""
        original = WebSocketMessage(op=WebSocketOp.MESSAGE, data={"hello": "world"})
        json_str = original.to_json()
        parsed = WebSocketMessage.from_json(json_str)
        assert parsed.op == original.op
        assert parsed.data == original.data
        assert parsed.message_id == original.message_id

    def test_ping_message(self):
        """测试 PING/PONG"""
        ping_msg = WebSocketMessage(op=WebSocketOp.PING)
        assert ping_msg.op == WebSocketOp.PING

        pong_msg = WebSocketMessage(op=WebSocketOp.PONG)
        assert pong_msg.op == WebSocketOp.PONG

    def test_error_message(self):
        """测试错误消息"""
        msg = WebSocketMessage(op=WebSocketOp.ERROR, error="Test error")
        assert msg.op == WebSocketOp.ERROR
        assert msg.error == "Test error"


class TestWebSocketConnection:
    """测试 WebSocket 连接"""

    def test_create_connection(self):
        """测试创建连接"""
        conn = WebSocketConnection(
            connection_id="test-id",
            path="/test"
        )
        assert conn.connection_id == "test-id"
        assert conn.path == "/test"
        assert conn.status == WebSocketStatus.CONNECTING
        assert isinstance(conn.connected_at, datetime)

    def test_connection_metadata(self):
        """测试连接元数据"""
        conn = WebSocketConnection(
            connection_id="test-id",
            path="/test",
            metadata={"user_id": "123", "role": "admin"}
        )
        assert conn.metadata["user_id"] == "123"
        assert conn.metadata["role"] == "admin"


class TestWebSocketHandler:
    """测试 WebSocket 处理器基类"""

    def test_base_handler_methods(self):
        """测试基类方法"""
        handler = WebSocketHandler()
        conn = WebSocketConnection(connection_id="test", path="/test")
        msg = WebSocketMessage(op=WebSocketOp.MESSAGE)

        connect_result = handler.on_connect(conn)
        assert connect_result is None

        message_result = handler.on_message(conn, msg)
        assert message_result is None

        # on_disconnect 不返回任何内容
        handler.on_disconnect(conn)


class TestEchoHandler:
    """测试 Echo 处理器"""

    def test_echo(self):
        """测试 Echo 功能"""
        handler = EchoHandler()
        conn = WebSocketConnection(connection_id="test", path="/echo")

        original_msg = WebSocketMessage(op=WebSocketOp.MESSAGE, data={"hello": "world"})
        response = handler.on_message(conn, original_msg)

        assert response is not None
        assert response.op == WebSocketOp.MESSAGE
        assert response.data["echo"] == {"hello": "world"}
        assert response.data["connection_id"] == "test"


class TestBroadcastHandler:
    """测试 Broadcast 处理器"""

    def test_broadcast_connect(self):
        """测试连接建立"""
        handler = BroadcastHandler()
        conn = WebSocketConnection(connection_id="test1", path="/broadcast")

        response = handler.on_connect(conn)

        assert response is not None
        assert response.op == WebSocketOp.MESSAGE
        assert response.data["message"] == "Connected"
        assert response.data["connection_id"] == "test1"
        assert "test1" in handler.connections

    def test_broadcast_message(self):
        """测试消息广播"""
        handler = BroadcastHandler()
        conn = WebSocketConnection(connection_id="test1", path="/broadcast")
        handler.on_connect(conn)

        msg = WebSocketMessage(op=WebSocketOp.MESSAGE, data={"text": "Hello everyone!"})
        response = handler.on_message(conn, msg)

        assert response is not None
        assert response.data["from"] == "test1"
        assert response.data["message"] == {"text": "Hello everyone!"}

    def test_broadcast_disconnect(self):
        """测试断开连接"""
        handler = BroadcastHandler()
        conn = WebSocketConnection(connection_id="test1", path="/broadcast")
        handler.on_connect(conn)

        handler.on_disconnect(conn)

        assert "test1" not in handler.connections


class TestWebSocketChannel:
    """测试 WebSocket 频道"""

    def test_create_channel(self):
        """测试创建频道"""
        channel = WebSocketChannel("test-channel")
        assert channel.name == "test-channel"

    def test_subscribe(self):
        """测试订阅"""
        channel = WebSocketChannel("test")
        channel.subscribe("conn1")
        channel.subscribe("conn2")

        assert "conn1" in channel.get_subscribers()
        assert "conn2" in channel.get_subscribers()
        assert len(channel.get_subscribers()) == 2

    def test_unsubscribe(self):
        """测试取消订阅"""
        channel = WebSocketChannel("test")
        channel.subscribe("conn1")
        channel.subscribe("conn2")
        channel.unsubscribe("conn1")

        assert "conn1" not in channel.get_subscribers()
        assert "conn2" in channel.get_subscribers()


class TestWebSocketRouter:
    """测试 WebSocket 路由"""

    def test_add_route(self):
        """测试添加路由"""
        router = WebSocketRouter()
        handler = EchoHandler()

        router.add_route("/test", handler)

        assert router.get_handler("/test") is handler
        assert router.get_handler("/v1/test") is handler

    def test_get_or_create_channel(self):
        """测试获取或创建频道"""
        router = WebSocketRouter()

        channel1 = router.get_or_create_channel("test")
        channel2 = router.get_or_create_channel("test")

        assert channel1 is channel2
        assert channel1.name == "test"


class TestWebSocketApp:
    """测试 WebSocket 应用"""

    def test_app_initialization(self):
        """测试应用初始化"""
        app = WebSocketApp(name="test-app")
        assert app.name == "test-app"
        assert app.router is not None

    def test_handle_connect(self):
        """测试处理连接"""
        app = WebSocketApp()

        conn = app.handle_connect("/echo")

        assert conn.status == WebSocketStatus.OPEN
        assert conn.connection_id in app.connections

    def test_handle_message_echo(self):
        """测试处理 Echo 消息"""
        app = WebSocketApp()

        conn = app.handle_connect("/echo")
        msg = WebSocketMessage(op=WebSocketOp.MESSAGE, data={"test": "data"})

        response = app.handle_message(conn, msg)

        assert response is not None
        assert response.op == WebSocketOp.MESSAGE
        assert response.data["echo"] == {"test": "data"}

    def test_handle_ping(self):
        """测试处理 PING"""
        app = WebSocketApp()
        conn = app.handle_connect("/echo")

        ping_msg = WebSocketMessage(op=WebSocketOp.PING)
        response = app.handle_message(conn, ping_msg)

        assert response is not None
        assert response.op == WebSocketOp.PONG

    def test_handle_disconnect(self):
        """测试处理断开连接"""
        app = WebSocketApp()

        conn = app.handle_connect("/echo")
        assert conn.connection_id in app.connections

        app.handle_disconnect(conn)

        assert conn.connection_id not in app.connections

    def test_get_stats(self):
        """测试获取统计信息"""
        app = WebSocketApp()

        app.handle_connect("/echo")
        app.handle_connect("/broadcast")

        stats = app.get_stats()

        assert stats["active_connections"] == 2
        assert "/echo" in stats["routes"]
        assert "/broadcast" in stats["routes"]


class TestHelperFunctions:
    """测试辅助函数"""

    def test_create_text_message(self):
        """测试创建文本消息"""
        msg = create_text_message({"hello": "world"})
        assert msg.op == WebSocketOp.MESSAGE
        assert msg.data == {"hello": "world"}

    def test_create_error_message(self):
        """测试创建错误消息"""
        msg = create_error_message("Something went wrong", {"details": "test"})
        assert msg.op == WebSocketOp.ERROR
        assert msg.error == "Something went wrong"
        assert msg.data == {"details": "test"}


class TestGlobalApp:
    """测试全局应用实例"""

    def test_get_default_ws_app(self):
        """测试获取默认应用"""
        app1 = get_default_ws_app()
        assert app1 is not None

        app2 = get_default_ws_app()
        assert app1 is app2

    def test_set_default_ws_app(self):
        """测试设置默认应用"""
        custom = WebSocketApp(name="custom")
        set_default_ws_app(custom)

        app = get_default_ws_app()
        assert app.name == "custom"


def test_integration():
    """集成测试"""
    app = WebSocketApp(name="integration-test")

    # 连接
    conn = app.handle_connect("/echo")

    # 发送消息
    msg = create_text_message({"action": "test"})
    response = app.handle_message(conn, msg)

    assert response is not None
    assert response.data["echo"]["action"] == "test"

    # 断开连接
    app.handle_disconnect(conn)

    assert conn.connection_id not in app.connections


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
