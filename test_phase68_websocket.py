"""
Phase 68 - WebSocket管理器测试
验证WebSocket连接管理、消息广播和房间功能是否正常工作
"""
import unittest
from src.utils.websocket_manager import (
    WebSocketManager,
    WebSocketConnection,
    ConnectionStatus,
    get_websocket_manager
)


class TestWebSocketManager(unittest.TestCase):
    """WebSocket管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.manager = WebSocketManager()

    def test_connect(self):
        """测试连接"""
        conn = self.manager.connect("conn-1", "client-1")
        self.assertEqual(conn.connection_id, "conn-1")
        self.assertEqual(conn.status, ConnectionStatus.CONNECTED)
        self.assertIsNotNone(self.manager.get_connection("conn-1"))

    def test_disconnect(self):
        """测试断开连接"""
        self.manager.connect("conn-1")
        result = self.manager.disconnect("conn-1")
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_connection("conn-1"))

    def test_join_room(self):
        """测试加入房间"""
        self.manager.connect("conn-1")
        result = self.manager.join_room("conn-1", "room-1")
        self.assertTrue(result)
        self.assertIn("conn-1", self.manager.get_room_connections("room-1"))

    def test_leave_room(self):
        """测试离开房间"""
        self.manager.connect("conn-1")
        self.manager.join_room("conn-1", "room-1")
        result = self.manager.leave_room("conn-1", "room-1")
        self.assertTrue(result)
        self.assertNotIn("conn-1", self.manager.get_room_connections("room-1"))

    def test_disconnect_leaves_rooms(self):
        """测试断开连接自动离开房间"""
        self.manager.connect("conn-1")
        self.manager.join_room("conn-1", "room-1")
        self.manager.disconnect("conn-1")
        self.assertEqual(len(self.manager.get_room_connections("room-1")), 0)

    def test_send_to_connection(self):
        """测试发送消息到连接"""
        self.manager.connect("conn-1")
        result = self.manager.send_to_connection("conn-1", {"type": "test"})
        self.assertTrue(result)

    def test_send_to_disconnected(self):
        """测试发送到断开连接"""
        result = self.manager.send_to_connection("nonexistent", {"type": "test"})
        self.assertFalse(result)

    def test_broadcast(self):
        """测试广播"""
        self.manager.connect("conn-1")
        self.manager.connect("conn-2")
        self.manager.connect("conn-3")

        count = self.manager.broadcast({"type": "broadcast"})
        self.assertEqual(count, 3)

    def test_broadcast_exclude(self):
        """测试广播排除"""
        self.manager.connect("conn-1")
        self.manager.connect("conn-2")

        count = self.manager.broadcast({"type": "broadcast"}, exclude=["conn-1"])
        self.assertEqual(count, 1)

    def test_broadcast_to_room(self):
        """测试房间广播"""
        self.manager.connect("conn-1")
        self.manager.connect("conn-2")
        self.manager.connect("conn-3")
        self.manager.join_room("conn-1", "room-1")
        self.manager.join_room("conn-2", "room-1")

        count = self.manager.broadcast_to_room("room-1", {"type": "room-msg"})
        self.assertEqual(count, 2)

    def test_get_all_connections(self):
        """测试获取所有连接"""
        self.manager.connect("conn-1")
        self.manager.connect("conn-2")

        connections = self.manager.get_all_connections()
        self.assertEqual(len(connections), 2)

    def test_message_handler(self):
        """测试消息处理器"""
        received = []

        def handler(conn_id, msg):
            received.append((conn_id, msg))

        self.manager.add_message_handler(handler)
        self.manager.handle_message("conn-1", {"type": "test"})

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], "conn-1")

    def test_stats(self):
        """测试统计"""
        self.manager.connect("conn-1")
        self.manager.connect("conn-2")
        self.manager.join_room("conn-1", "room-1")
        self.manager.join_room("conn-2", "room-1")

        stats = self.manager.get_stats()
        self.assertEqual(stats["connections"], 2)
        self.assertEqual(stats["rooms"], 1)
        self.assertEqual(stats["total_room_members"], 2)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_websocket_manager(self):
        """测试获取全局管理器"""
        m1 = get_websocket_manager()
        m2 = get_websocket_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 68 - WebSocket管理器测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestWebSocketManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalInstance))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run_tests()
