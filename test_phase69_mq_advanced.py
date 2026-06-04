"""
Phase 69 - 消息队列高级功能测试
验证优先级队列、延迟队列和死信队列功能是否正常工作
"""
import time
import unittest
from src.utils.message_queue_advanced import (
    PriorityQueue,
    DelayedQueue,
    DeadLetterQueue,
    AdvancedMessageQueue,
    QueueMessage,
    MessagePriority,
    get_advanced_message_queue
)


class TestPriorityQueue(unittest.TestCase):
    """优先级队列测试"""

    def test_enqueue_dequeue(self):
        """测试入队出队"""
        pq = PriorityQueue()
        pq.enqueue(QueueMessage("1", "low", MessagePriority.LOW))
        pq.enqueue(QueueMessage("2", "high", MessagePriority.HIGH))
        pq.enqueue(QueueMessage("3", "critical", MessagePriority.CRITICAL))

        msg = pq.dequeue()
        self.assertEqual(msg.priority, MessagePriority.CRITICAL)

    def test_peek(self):
        """测试查看队首"""
        pq = PriorityQueue()
        pq.enqueue(QueueMessage("1", "normal"))
        msg = pq.peek()
        self.assertEqual(msg.message_id, "1")
        self.assertEqual(pq.size(), 1)

    def test_is_empty(self):
        """测试是否为空"""
        pq = PriorityQueue()
        self.assertTrue(pq.is_empty())
        pq.enqueue(QueueMessage("1", "test"))
        self.assertFalse(pq.is_empty())


class TestDelayedQueue(unittest.TestCase):
    """延迟队列测试"""

    def test_enqueue_dequeue_ready(self):
        """测试到期消息出队"""
        dq = DelayedQueue()
        dq.enqueue(QueueMessage("1", "test"), 0.1)
        time.sleep(0.15)
        msg = dq.dequeue()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.message_id, "1")

    def test_enqueue_dequeue_not_ready(self):
        """测试未到期消息不出队"""
        dq = DelayedQueue()
        dq.enqueue(QueueMessage("1", "test"), 10)
        msg = dq.dequeue()
        self.assertIsNone(msg)

    def test_ready_count(self):
        """测试已到期计数"""
        dq = DelayedQueue()
        dq.enqueue(QueueMessage("1", "test"), 0.1)
        dq.enqueue(QueueMessage("2", "test"), 10)
        time.sleep(0.15)
        self.assertEqual(dq.ready_count(), 1)


class TestDeadLetterQueue(unittest.TestCase):
    """死信队列测试"""

    def test_add(self):
        """测试添加"""
        dlq = DeadLetterQueue()
        dlq.add(QueueMessage("1", "test"), "Failed")
        self.assertEqual(dlq.size(), 1)

    def test_get_messages(self):
        """测试获取消息"""
        dlq = DeadLetterQueue()
        dlq.add(QueueMessage("1", "test"))
        msgs = dlq.get_messages()
        self.assertEqual(len(msgs), 1)

    def test_clear(self):
        """测试清空"""
        dlq = DeadLetterQueue()
        dlq.add(QueueMessage("1", "test"))
        dlq.clear()
        self.assertEqual(dlq.size(), 0)


class TestAdvancedMessageQueue(unittest.TestCase):
    """高级消息队列测试"""

    def setUp(self):
        """测试前设置"""
        self.mq = AdvancedMessageQueue()

    def test_publish_priority(self):
        """测试发布优先级消息"""
        self.mq.publish(QueueMessage("1", "low", MessagePriority.LOW))
        self.mq.publish(QueueMessage("2", "high", MessagePriority.HIGH))

        msg = self.mq.consume()
        self.assertEqual(msg.priority, MessagePriority.HIGH)

    def test_publish_delayed(self):
        """测试发布延迟消息"""
        self.mq.publish(QueueMessage("1", "test"), delay_seconds=0.1)
        msg = self.mq.consume()
        self.assertIsNone(msg)

        time.sleep(0.15)
        msg = self.mq.consume()
        self.assertIsNotNone(msg)

    def test_process_success(self):
        """测试成功处理"""
        msg = QueueMessage("1", "test")
        result = self.mq.process_message(msg, lambda x: True)
        self.assertTrue(result)
        self.assertEqual(self.mq.get_stats()["processed"], 1)

    def test_process_failure_retry(self):
        """测试失败重试"""
        msg = QueueMessage("1", "test", max_retries=3)
        result = self.mq.process_message(msg, lambda x: False)
        self.assertFalse(result)
        self.assertEqual(msg.retry_count, 1)

    def test_process_failure_dlq(self):
        """测试失败进入死信队列"""
        msg = QueueMessage("1", "test", max_retries=1)
        self.mq.process_message(msg, lambda x: False)
        self.mq.process_message(msg, lambda x: False)

        stats = self.mq.get_stats()
        self.assertEqual(stats["dlq_size"], 1)
        self.assertEqual(stats["failed"], 1)

    def test_process_exception(self):
        """测试异常处理"""
        msg = QueueMessage("1", "test", max_retries=1)

        def fail_handler(x):
            raise ValueError("Error")

        self.mq.process_message(msg, fail_handler)
        self.mq.process_message(msg, fail_handler)

        stats = self.mq.get_stats()
        self.assertEqual(stats["dlq_size"], 1)

    def test_stats(self):
        """测试统计"""
        self.mq.publish(QueueMessage("1", "test"))
        stats = self.mq.get_stats()
        self.assertEqual(stats["priority_queue_size"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_advanced_message_queue(self):
        """测试获取全局队列"""
        q1 = get_advanced_message_queue()
        q2 = get_advanced_message_queue()
        self.assertIs(q1, q2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 69 - 消息队列高级功能测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPriorityQueue))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDelayedQueue))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDeadLetterQueue))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdvancedMessageQueue))
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
