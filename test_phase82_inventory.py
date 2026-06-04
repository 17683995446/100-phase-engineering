"""
Phase 82 - 库存管理系统测试
验证库存跟踪、预警、调拨和盘点功能
"""
import unittest
from src.utils.inventory_manager import (
    InventoryManager,
    StockItem,
    StockStatus,
    get_inventory_manager
)


class TestInventoryManager(unittest.TestCase):
    """库存管理器测试"""

    def setUp(self):
        self.manager = InventoryManager()

    def test_add_item(self):
        """测试添加库存项"""
        item = self.manager.add_item("SKU001", "Product A", 100)
        self.assertEqual(item.sku, "SKU001")
        self.assertEqual(item.quantity, 100)
        self.assertEqual(item.status, StockStatus.IN_STOCK)

    def test_add_duplicate(self):
        """测试添加重复SKU"""
        self.manager.add_item("SKU001", "Product A", 100)
        with self.assertRaises(ValueError):
            self.manager.add_item("SKU001", "Product B", 50)

    def test_get_item(self):
        """测试获取库存项"""
        self.manager.add_item("SKU001", "Product A", 100)
        item = self.manager.get_item("SKU001")
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "Product A")

    def test_update_quantity(self):
        """测试更新数量"""
        self.manager.add_item("SKU001", "Product A", 100)
        result = self.manager.update_quantity("SKU001", 50)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_item("SKU001").quantity, 50)

    def test_increase_stock(self):
        """测试增加库存"""
        self.manager.add_item("SKU001", "Product A", 100)
        result = self.manager.increase_stock("SKU001", 50)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_item("SKU001").quantity, 150)

    def test_decrease_stock(self):
        """测试减少库存"""
        self.manager.add_item("SKU001", "Product A", 100)
        result = self.manager.decrease_stock("SKU001", 30)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_item("SKU001").quantity, 70)

    def test_decrease_stock_insufficient(self):
        """测试库存不足"""
        self.manager.add_item("SKU001", "Product A", 10)
        result = self.manager.decrease_stock("SKU001", 20)
        self.assertFalse(result)

    def test_reserve_stock(self):
        """测试预留库存"""
        self.manager.add_item("SKU001", "Product A", 100)
        result = self.manager.reserve_stock("SKU001", 30)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_item("SKU001").reserved, 30)
        self.assertEqual(self.manager.get_item("SKU001").available, 70)

    def test_reserve_stock_insufficient(self):
        """测试预留库存不足"""
        self.manager.add_item("SKU001", "Product A", 10)
        result = self.manager.reserve_stock("SKU001", 20)
        self.assertFalse(result)

    def test_release_reservation(self):
        """测试释放预留"""
        self.manager.add_item("SKU001", "Product A", 100)
        self.manager.reserve_stock("SKU001", 30)
        result = self.manager.release_reservation("SKU001", 20)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_item("SKU001").reserved, 10)

    def test_transfer_stock(self):
        """测试调拨库存"""
        self.manager.add_item("SKU001", "Product A", 100, location="warehouse_a")
        result = self.manager.transfer_stock("SKU001", "warehouse_a", "warehouse_b", 50)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_item("SKU001").quantity, 50)
        self.assertEqual(self.manager.get_item("SKU001@warehouse_b").quantity, 50)

    def test_check_stock(self):
        """测试检查库存"""
        self.manager.add_item("SKU001", "Product A", 100)
        stock = self.manager.check_stock("SKU001")
        self.assertIsNotNone(stock)
        self.assertEqual(stock["quantity"], 100)

    def test_low_stock(self):
        """测试低库存"""
        self.manager.add_item("SKU001", "Product A", 5, reorder_level=10)
        items = self.manager.get_low_stock_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].sku, "SKU001")

    def test_out_of_stock(self):
        """测试缺货"""
        self.manager.add_item("SKU001", "Product A", 0)
        items = self.manager.get_out_of_stock_items()
        self.assertEqual(len(items), 1)

    def test_list_items(self):
        """测试列出库存"""
        self.manager.add_item("SKU001", "Product A", 100, location="A")
        self.manager.add_item("SKU002", "Product B", 50, location="B")
        items = self.manager.list_items()
        self.assertEqual(len(items), 2)
        items_a = self.manager.list_items(location="A")
        self.assertEqual(len(items_a), 1)

    def test_delete_item(self):
        """测试删除库存"""
        self.manager.add_item("SKU001", "Product A", 100)
        result = self.manager.delete_item("SKU001")
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_item("SKU001"))

    def test_stats(self):
        """测试统计信息"""
        self.manager.add_item("SKU001", "Product A", 100)
        self.manager.add_item("SKU002", "Product B", 5, reorder_level=10)
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_items"], 2)
        self.assertEqual(stats["total_quantity"], 105)
        self.assertEqual(stats["low_stock_count"], 1)


class TestStockItem(unittest.TestCase):
    """库存项测试"""

    def test_available(self):
        """测试可用数量"""
        item = StockItem("SKU001", "Product A", 100, reserved=30)
        self.assertEqual(item.available, 70)

    def test_status_in_stock(self):
        """测试有货状态"""
        item = StockItem("SKU001", "Product A", 100, reorder_level=10)
        self.assertEqual(item.status, StockStatus.IN_STOCK)

    def test_status_low_stock(self):
        """测试低库存状态"""
        item = StockItem("SKU001", "Product A", 5, reorder_level=10)
        self.assertEqual(item.status, StockStatus.LOW_STOCK)

    def test_status_out_of_stock(self):
        """测试缺货状态"""
        item = StockItem("SKU001", "Product A", 0)
        self.assertEqual(item.status, StockStatus.OUT_OF_STOCK)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_inventory_manager(self):
        """测试获取全局库存管理器"""
        m1 = get_inventory_manager()
        m2 = get_inventory_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 82 - 库存管理系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestInventoryManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStockItem))
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
