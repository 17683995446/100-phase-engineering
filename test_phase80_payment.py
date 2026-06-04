"""
Phase 80 - 支付网关系统测试
验证支付处理、退款、对账和支付渠道管理功能
"""
import unittest
from src.utils.payment_gateway import (
    PaymentGateway,
    MockPaymentProcessor,
    PaymentRequest,
    PaymentResult,
    PaymentStatus,
    PaymentMethod,
    get_payment_gateway
)


class TestMockPaymentProcessor(unittest.TestCase):
    """模拟支付处理器测试"""

    def setUp(self):
        self.processor = MockPaymentProcessor("test", success_rate=1.0)

    def test_process_success(self):
        """测试成功支付"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = self.processor.process(request)
        self.assertEqual(result.status, PaymentStatus.SUCCESS)
        self.assertEqual(result.amount, 100.0)
        self.assertEqual(result.order_id, "order1")

    def test_process_failure(self):
        """测试失败支付"""
        processor = MockPaymentProcessor("fail", success_rate=0.0)
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = processor.process(request)
        self.assertEqual(result.status, PaymentStatus.FAILED)

    def test_refund_full(self):
        """测试全额退款"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = self.processor.process(request)
        refund = self.processor.refund(result.transaction_id, 100.0)
        self.assertEqual(refund.status, PaymentStatus.REFUNDED)

    def test_refund_partial(self):
        """测试部分退款"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = self.processor.process(request)
        refund = self.processor.refund(result.transaction_id, 50.0)
        self.assertEqual(refund.status, PaymentStatus.REFUNDED)
        # 原交易状态变为部分退款
        original = self.processor.query(result.transaction_id)
        self.assertEqual(original.status, PaymentStatus.PARTIALLY_REFUNDED)

    def test_refund_exceeds(self):
        """测试退款超额"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = self.processor.process(request)
        refund = self.processor.refund(result.transaction_id, 200.0)
        self.assertEqual(refund.status, PaymentStatus.FAILED)

    def test_refund_not_found(self):
        """测试退款不存在"""
        refund = self.processor.refund("nonexistent", 100.0)
        self.assertEqual(refund.status, PaymentStatus.FAILED)

    def test_query(self):
        """测试查询"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = self.processor.process(request)
        queried = self.processor.query(result.transaction_id)
        self.assertIsNotNone(queried)
        self.assertEqual(queried.transaction_id, result.transaction_id)

    def test_get_transactions(self):
        """测试获取交易"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        self.processor.process(request)
        transactions = self.processor.get_transactions()
        self.assertEqual(len(transactions), 1)


class TestPaymentGateway(unittest.TestCase):
    """支付网关测试"""

    def setUp(self):
        self.gateway = PaymentGateway()
        self.processor = MockPaymentProcessor("test", success_rate=1.0)
        self.gateway.register_processor(PaymentMethod.CREDIT_CARD, self.processor)

    def test_register_processor(self):
        """测试注册处理器"""
        stats = self.gateway.get_stats()
        self.assertEqual(stats["registered_processors"], 1)

    def test_process_payment(self):
        """测试支付"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = self.gateway.process_payment(request)
        self.assertEqual(result.status, PaymentStatus.SUCCESS)

    def test_process_no_processor(self):
        """测试无处理器"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.ALIPAY)
        result = self.gateway.process_payment(request)
        self.assertEqual(result.status, PaymentStatus.FAILED)

    def test_refund(self):
        """测试退款"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = self.gateway.process_payment(request)
        refund = self.gateway.refund(result.transaction_id, 100.0)
        self.assertEqual(refund.status, PaymentStatus.REFUNDED)

    def test_query_transaction(self):
        """测试查询交易"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        result = self.gateway.process_payment(request)
        queried = self.gateway.query_transaction(result.transaction_id)
        self.assertIsNotNone(queried)

    def test_get_transactions_by_order(self):
        """测试按订单查询"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        self.gateway.process_payment(request)
        transactions = self.gateway.get_transactions_by_order("order1")
        self.assertEqual(len(transactions), 1)

    def test_reconcile(self):
        """测试对账"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        self.gateway.process_payment(request)

        import time
        start = time.time() - 10
        end = time.time() + 10
        report = self.gateway.reconcile(start, end)
        self.assertEqual(report["total_transactions"], 1)
        self.assertEqual(report["success_count"], 1)
        self.assertEqual(report["total_amount"], 100.0)

    def test_stats(self):
        """测试统计信息"""
        request = PaymentRequest("order1", 100.0, "USD", PaymentMethod.CREDIT_CARD)
        self.gateway.process_payment(request)
        stats = self.gateway.get_stats()
        self.assertEqual(stats["total_transactions"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_payment_gateway(self):
        """测试获取全局支付网关"""
        g1 = get_payment_gateway()
        g2 = get_payment_gateway()
        self.assertIs(g1, g2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 80 - 支付网关系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMockPaymentProcessor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPaymentGateway))
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
