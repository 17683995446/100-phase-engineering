"""
Phase 83 - 购物车系统测试
验证添加商品、修改数量、结算和持久化功能
"""
import unittest
from src.utils.shopping_cart import (
    CartManager,
    CartItem,
    CartStatus,
    get_cart_manager
)


class TestCartManager(unittest.TestCase):
    """购物车管理器测试"""

    def setUp(self):
        self.manager = CartManager()

    def test_create_cart(self):
        """测试创建购物车"""
        cart = self.manager.create_cart("cart1", "user1")
        self.assertEqual(cart.cart_id, "cart1")
        self.assertEqual(cart.user_id, "user1")
        self.assertEqual(cart.status, CartStatus.ACTIVE)

    def test_create_duplicate(self):
        """测试创建重复购物车"""
        self.manager.create_cart("cart1", "user1")
        with self.assertRaises(ValueError):
            self.manager.create_cart("cart1", "user1")

    def test_add_item(self):
        """测试添加商品"""
        self.manager.create_cart("cart1", "user1")
        item = CartItem("item1", "Product A", 2, 10.0)
        result = self.manager.add_item("cart1", item)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_cart("cart1").total_amount, 20.0)

    def test_add_existing_item(self):
        """测试添加已存在商品"""
        self.manager.create_cart("cart1", "user1")
        self.manager.add_item("cart1", CartItem("item1", "Product A", 2, 10.0))
        self.manager.add_item("cart1", CartItem("item1", "Product A", 3, 10.0))
        self.assertEqual(self.manager.get_cart("cart1").total_amount, 50.0)

    def test_update_quantity(self):
        """测试更新数量"""
        self.manager.create_cart("cart1", "user1")
        self.manager.add_item("cart1", CartItem("item1", "Product A", 2, 10.0))
        result = self.manager.update_quantity("cart1", "item1", 5)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_cart("cart1").total_amount, 50.0)

    def test_update_quantity_to_zero(self):
        """测试更新数量为0"""
        self.manager.create_cart("cart1", "user1")
        self.manager.add_item("cart1", CartItem("item1", "Product A", 2, 10.0))
        result = self.manager.update_quantity("cart1", "item1", 0)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_cart("cart1").total_items, 0)

    def test_remove_item(self):
        """测试移除商品"""
        self.manager.create_cart("cart1", "user1")
        self.manager.add_item("cart1", CartItem("item1", "Product A", 2, 10.0))
        result = self.manager.remove_item("cart1", "item1")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_cart("cart1").total_items, 0)

    def test_clear_cart(self):
        """测试清空购物车"""
        self.manager.create_cart("cart1", "user1")
        self.manager.add_item("cart1", CartItem("item1", "Product A", 2, 10.0))
        self.manager.add_item("cart1", CartItem("item2", "Product B", 1, 20.0))
        result = self.manager.clear_cart("cart1")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_cart("cart1").total_items, 0)

    def test_checkout(self):
        """测试结算"""
        self.manager.create_cart("cart1", "user1")
        self.manager.add_item("cart1", CartItem("item1", "Product A", 2, 10.0))
        result = self.manager.checkout("cart1")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, CartStatus.CHECKED_OUT)

    def test_checkout_empty(self):
        """测试空购物车结算"""
        self.manager.create_cart("cart1", "user1")
        result = self.manager.checkout("cart1")
        self.assertIsNone(result)

    def test_abandon_cart(self):
        """测试放弃购物车"""
        self.manager.create_cart("cart1", "user1")
        result = self.manager.abandon_cart("cart1")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_cart("cart1").status, CartStatus.ABANDONED)

    def test_get_user_carts(self):
        """测试获取用户购物车"""
        self.manager.create_cart("cart1", "user1")
        self.manager.create_cart("cart2", "user1")
        carts = self.manager.get_user_carts("user1")
        self.assertEqual(len(carts), 2)

    def test_merge_carts(self):
        """测试合并购物车"""
        self.manager.create_cart("cart1", "user1")
        self.manager.create_cart("cart2", "user1")
        self.manager.add_item("cart1", CartItem("item1", "Product A", 2, 10.0))
        self.manager.add_item("cart2", CartItem("item1", "Product A", 3, 10.0))
        result = self.manager.merge_carts("cart1", "cart2")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_cart("cart2").total_amount, 50.0)

    def test_list_carts(self):
        """测试列出购物车"""
        self.manager.create_cart("cart1", "user1")
        self.manager.create_cart("cart2", "user2")
        carts = self.manager.list_carts()
        self.assertEqual(len(carts), 2)

    def test_stats(self):
        """测试统计信息"""
        self.manager.create_cart("cart1", "user1")
        self.manager.add_item("cart1", CartItem("item1", "Product A", 2, 10.0))
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_carts"], 1)
        self.assertEqual(stats["active"], 1)
        self.assertEqual(stats["total_active_value"], 20.0)


class TestCartItem(unittest.TestCase):
    """购物车项测试"""

    def test_total_price(self):
        """测试总价"""
        item = CartItem("item1", "Product A", 3, 10.0)
        self.assertEqual(item.total_price, 30.0)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_cart_manager(self):
        """测试获取全局购物车管理器"""
        m1 = get_cart_manager()
        m2 = get_cart_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 83 - 购物车系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCartManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCartItem))
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
