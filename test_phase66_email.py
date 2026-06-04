"""
Phase 66 - 邮件通知系统测试
验证邮件模板、发送队列和批量发送功能是否正常工作
"""
import unittest
from src.utils.email_notifier import (
    EmailNotifier,
    EmailMessage,
    EmailStatus,
    get_email_notifier
)


class TestEmailNotifier(unittest.TestCase):
    """邮件通知器测试"""

    def setUp(self):
        """测试前设置"""
        self.notifier = EmailNotifier()

    def test_create_message(self):
        """测试创建消息"""
        msg = self.notifier.create_message(
            ["user@example.com"],
            "Test Subject",
            "Test Body"
        )
        self.assertEqual(msg.to, ["user@example.com"])
        self.assertEqual(msg.subject, "Test Subject")
        self.assertEqual(msg.status, EmailStatus.PENDING)

    def test_send(self):
        """测试发送"""
        msg = EmailMessage(["user@example.com"], "Test", "Body")
        result = self.notifier.send(msg)
        self.assertTrue(result)
        self.assertEqual(msg.status, EmailStatus.SENT)
        self.assertIsNotNone(msg.sent_at)

    def test_send_disabled(self):
        """测试禁用时发送"""
        self.notifier.set_enabled(False)
        msg = EmailMessage(["user@example.com"], "Test", "Body")
        result = self.notifier.send(msg)
        self.assertFalse(result)
        self.assertEqual(msg.status, EmailStatus.FAILED)

    def test_queue(self):
        """测试队列"""
        msg = EmailMessage(["user@example.com"], "Test", "Body")
        self.notifier.queue(msg)
        self.assertEqual(self.notifier.get_queue_size(), 1)
        self.assertEqual(msg.status, EmailStatus.QUEUED)

    def test_process_queue(self):
        """测试处理队列"""
        self.notifier.queue(EmailMessage(["a@example.com"], "Test1", "Body"))
        self.notifier.queue(EmailMessage(["b@example.com"], "Test2", "Body"))

        result = self.notifier.process_queue()
        self.assertEqual(result["sent"], 2)
        self.assertEqual(self.notifier.get_queue_size(), 0)
        self.assertEqual(self.notifier.get_sent_count(), 2)

    def test_send_bulk(self):
        """测试批量发送"""
        messages = [
            EmailMessage(["a@example.com"], "Test1", "Body"),
            EmailMessage(["b@example.com"], "Test2", "Body"),
        ]
        result = self.notifier.send_bulk(messages)
        self.assertEqual(result["sent"], 2)

    def test_template(self):
        """测试模板"""
        self.notifier.register_template("welcome", "Hello {name}, welcome!")
        msg = self.notifier.create_message(
            ["user@example.com"],
            "Welcome",
            "",
            template_name="welcome",
            template_context={"name": "Alice"}
        )
        self.assertEqual(msg.body, "Hello Alice, welcome!")

    def test_clear_queue(self):
        """测试清空队列"""
        self.notifier.queue(EmailMessage(["a@example.com"], "Test", "Body"))
        self.notifier.clear_queue()
        self.assertEqual(self.notifier.get_queue_size(), 0)

    def test_clear_sent(self):
        """测试清空已发送"""
        self.notifier.send(EmailMessage(["a@example.com"], "Test", "Body"))
        self.notifier.clear_sent()
        self.assertEqual(self.notifier.get_sent_count(), 0)

    def test_stats(self):
        """测试统计"""
        self.notifier.register_template("t1", "test")
        self.notifier.send(EmailMessage(["a@example.com"], "Test", "Body"))

        stats = self.notifier.get_stats()
        self.assertEqual(stats["sent"], 1)
        self.assertEqual(stats["templates"], 1)
        self.assertTrue(stats["enabled"])


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_email_notifier(self):
        """测试获取全局通知器"""
        n1 = get_email_notifier()
        n2 = get_email_notifier()
        self.assertIs(n1, n2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 66 - 邮件通知系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEmailNotifier))
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
