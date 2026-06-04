"""
Phase 81 - 订单管理系统测试
验证订单创建、状态流转、取消和查询功能
"""
import unittest
from src.utils.order_manager import (
    OrderManager,
    OrderItem,
    OrderStatus,
    get_order_manager
)


class TestOrderManager(unittest.TestCase):
    """订单管理器测试"""

    def setUp(self):
        self.manager = OrderManager()

    def test_create_order(self):
        """测试创建订单"""
        items = [OrderItem("item1", "Product A", 2, 10.0)]
        order = self.manager.create_order("order1", "user1", items)
        self.assertEqual(order.order_id, "order1")
        self.assertEqual(order.user_id, "user1")
        self.assertEqual(order.total_amount, 20.0)
        self.assertEqual(order.status, OrderStatus.CREATED)

    def test_create_duplicate_order(self):
        """测试创建重复订单"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        with self.assertRaises(ValueError):
            self.manager.create_order("order1", "user1", items)

    def test_get_order(self):
        """测试获取订单"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        order = self.manager.get_order("order1")
        self.assertIsNotNone(order)
        self.assertEqual(order.order_id, "order1")

    def test_update_status(self):
        """测试更新状态"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        result = self.manager.update_status("order1", OrderStatus.PAID)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_order("order1").status, OrderStatus.PAID)

    def test_cancel_order(self):
        """测试取消订单"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        result = self.manager.cancel_order("order1", "User request")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_order("order1").status, OrderStatus.CANCELLED)

    def test_cancel_completed_order(self):
        """测试取消已完成订单"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        self.manager.update_status("order1", OrderStatus.COMPLETED)
        result = self.manager.cancel_order("order1")
        self.assertFalse(result)

    def test_add_item(self):
        """测试添加订单项"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        result = self.manager.add_item("order1", OrderItem("item2", "Product B", 1, 20.0))
        self.assertTrue(result)
        self.assertEqual(self.manager.get_order("order1").total_amount, 30.0)

    def test_add_item_after_paid(self):
        """测试支付后添加订单项"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        self.manager.update_status("order1", OrderStatus.PAID)
        result = self.manager.add_item("order1", OrderItem("item2", "Product B", 1, 20.0))
        self.assertFalse(result)

    def test_remove_item(self):
        """测试移除订单项"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        result = self.manager.remove_item("order1", "item1")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_order("order1").total_amount, 0.0)

    def test_list_orders(self):
        """测试列出订单"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        self.manager.create_order("order2", "user2", items)
        orders = self.manager.list_orders()
        self.assertEqual(len(orders), 2)

    def test_list_by_user(self):
        """测试按用户列出"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        self.manager.create_order("order2", "user2", items)
        orders = self.manager.list_orders(user_id="user1")
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].order_id, "order1")

    def test_list_by_status(self):
        """测试按状态列出"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        self.manager.create_order("order2", "user1", items)
        self.manager.update_status("order2", OrderStatus.PAID)
        orders = self.manager.list_orders(status=OrderStatus.PAID)
        self.assertEqual(len(orders), 1)

    def test_get_user_orders(self):
        """测试获取用户订单"""
        items = [OrderItem("item1", "Product A", 1, 10.0)]
        self.manager.create_order("order1", "user1", items)
        orders = self.manager.get_user_orders("user1")
        self.assertEqual(len(orders), 1)

    def test_stats(self):
        """测试统计信息"""
        items = [OrderItem("item1", "Product A", 1, 100.0)]
        self.manager.create_order("order1", "user1", items)
        self.manager.create_order("order2", "user1", items)
        self.manager.update_status("order1", OrderStatus.PAID)
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_orders"], 2)
        self.assertEqual(stats["total_revenue"], 100.0)


class TestOrderItem(unittest.TestCase):
    """订单项测试"""

    def test_total_price(self):
        """测试总价"""
        item = OrderItem("item1", "Product A", 3, 10.0)
        self.assertEqual(item.total_price, 30.0)

    def test_to_dict(self):
        """测试转字典"""
        item = OrderItem("item1", "Product A", 1, 10.0)
        d = item.to_dict()
        self.assertEqual(d["item_id"], "item1")
        self.assertEqual(d["total_price"], 10.0)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_order_manager(self):
        """测试获取全局订单管理器"""
        m1 = get_order_manager()
        m2 = get_order_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 81 - 订单管理系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOrderManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOrderItem))
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
