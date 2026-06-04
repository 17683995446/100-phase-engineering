"""
Phase 44 - 消息队列与事件驱动测试
验证事件系统是否正常工作
"""
import time
import unittest
from src.utils.event_bus import (
    EventBus,
    Event,
    EventPriority,
    MessageQueue,
    get_event_bus,
    get_message_queue
)


class TestEventBus(unittest.TestCase):
    """事件总线测试"""
    
    def setUp(self):
        """测试前设置"""
        self.bus = EventBus("test")
        self.received_events = []
    
    def event_handler(self, event):
        """事件处理器"""
        self.received_events.append(event)
    
    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        self.bus.subscribe("test.event", self.event_handler)
        
        event = Event(event_type="test.event", payload={"data": "hello"})
        self.bus.publish_sync(event)
        
        self.assertEqual(len(self.received_events), 1)
        self.assertEqual(self.received_events[0].payload["data"], "hello")
    
    def test_async_publish(self):
        """测试异步发布"""
        self.bus.subscribe("async.event", self.event_handler)
        self.bus.start()
        
        event = Event(event_type="async.event", payload={"data": "async"})
        self.bus.publish(event)
        
        # 等待处理
        time.sleep(0.1)
        
        self.assertEqual(len(self.received_events), 1)
        self.bus.stop()
    
    def test_priority(self):
        """测试优先级"""
        priorities = []
        
        def handler(event):
            priorities.append(event.priority)
        
        self.bus.subscribe("priority.event", handler)
        
        # 发布不同优先级的事件
        self.bus.publish_sync(Event(event_type="priority.event", priority=EventPriority.LOW))
        self.bus.publish_sync(Event(event_type="priority.event", priority=EventPriority.HIGH))
        self.bus.publish_sync(Event(event_type="priority.event", priority=EventPriority.NORMAL))
        
        self.assertEqual(len(priorities), 3)
    
    def test_unsubscribe(self):
        """测试取消订阅"""
        self.bus.subscribe("unsub.event", self.event_handler)
        self.bus.unsubscribe("unsub.event", self.event_handler)
        
        event = Event(event_type="unsub.event")
        self.bus.publish_sync(event)
        
        self.assertEqual(len(self.received_events), 0)
    
    def test_history(self):
        """测试历史记录"""
        for i in range(5):
            event = Event(event_type="history.event", payload={"index": i})
            self.bus.publish_sync(event)
        
        history = self.bus.get_history("history.event")
        self.assertEqual(len(history), 5)


class TestMessageQueue(unittest.TestCase):
    """消息队列测试"""
    
    def setUp(self):
        """测试前设置"""
        self.mq = MessageQueue("test", max_size=100)
        self.consumed_messages = []
    
    def consumer(self, message):
        """消费者"""
        self.consumed_messages.append(message)
    
    def test_produce_and_consume(self):
        """测试生产和消费"""
        self.mq.produce({"data": "message1"})
        self.mq.produce({"data": "message2"})
        
        msg1 = self.mq.consume(timeout=1)
        msg2 = self.mq.consume(timeout=1)
        
        self.assertEqual(msg1["data"], "message1")
        self.assertEqual(msg2["data"], "message2")
    
    def test_consumer_threads(self):
        """测试消费者线程"""
        self.mq.register_consumer(self.consumer)
        self.mq.start_consumers(count=2)
        
        # 生产消息
        for i in range(5):
            self.mq.produce({"index": i})
        
        # 等待消费
        time.sleep(0.2)
        
        self.assertEqual(len(self.consumed_messages), 5)
        self.mq.stop_consumers()
    
    def test_queue_full(self):
        """测试队列满"""
        mq = MessageQueue("small", max_size=2)
        
        self.assertTrue(mq.produce({"data": 1}))
        self.assertTrue(mq.produce({"data": 2}))
        self.assertFalse(mq.produce({"data": 3}))  # 应该失败


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 44 - 消息队列与事件驱动测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEventBus))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMessageQueue))
    
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
