"""
Phase 87 - 审计日志系统测试
验证操作记录、日志查询、合规性检查和审计报告功能
"""
import time
import unittest
from src.utils.audit_log import (
    AuditLogger,
    AuditReport,
    AuditAction,
    AuditLevel,
    get_audit_logger
)


class TestAuditLogger(unittest.TestCase):
    """审计日志记录器测试"""

    def setUp(self):
        self.logger = AuditLogger()

    def test_log(self):
        """测试记录日志"""
        entry = self.logger.log("user1", AuditAction.CREATE, "article", "123")
        self.assertEqual(entry.user_id, "user1")
        self.assertEqual(entry.action, AuditAction.CREATE)
        self.assertEqual(entry.resource, "article")
        self.assertEqual(entry.result, "success")

    def test_log_with_details(self):
        """测试带详情记录"""
        entry = self.logger.log("user1", AuditAction.UPDATE, "article", "123",
                                 details={"field": "title"})
        self.assertEqual(entry.details["field"], "title")

    def test_query_by_user(self):
        """测试按用户查询"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.log("user2", AuditAction.CREATE, "article", "2")
        results = self.logger.query(user_id="user1")
        self.assertEqual(len(results), 1)

    def test_query_by_action(self):
        """测试按动作查询"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.log("user1", AuditAction.DELETE, "article", "2")
        results = self.logger.query(action=AuditAction.CREATE)
        self.assertEqual(len(results), 1)

    def test_query_by_resource(self):
        """测试按资源查询"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.log("user1", AuditAction.CREATE, "comment", "1")
        results = self.logger.query(resource="article")
        self.assertEqual(len(results), 1)

    def test_query_by_time(self):
        """测试按时间查询"""
        start = time.time()
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        end = time.time()
        results = self.logger.query(start_time=start, end_time=end)
        self.assertEqual(len(results), 1)

    def test_query_by_level(self):
        """测试按级别查询"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1", level=AuditLevel.INFO)
        self.logger.log("user1", AuditAction.DELETE, "article", "2", level=AuditLevel.ERROR)
        results = self.logger.query(level=AuditLevel.ERROR)
        self.assertEqual(len(results), 1)

    def test_query_by_result(self):
        """测试按结果查询"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1", result="success")
        self.logger.log("user1", AuditAction.DELETE, "article", "2", result="failure")
        results = self.logger.query(result="failure")
        self.assertEqual(len(results), 1)

    def test_get_entries_by_resource(self):
        """测试获取资源条目"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.log("user1", AuditAction.CREATE, "article", "2")
        results = self.logger.get_entries_by_resource("article")
        self.assertEqual(len(results), 2)

    def test_get_entries_by_user(self):
        """测试获取用户条目"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.log("user1", AuditAction.CREATE, "article", "2")
        results = self.logger.get_entries_by_user("user1")
        self.assertEqual(len(results), 2)

    def test_get_recent_entries(self):
        """测试获取最近条目"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.log("user1", AuditAction.CREATE, "article", "2")
        results = self.logger.get_recent_entries(limit=1)
        self.assertEqual(len(results), 1)

    def test_clear(self):
        """测试清空"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.clear()
        self.assertEqual(len(self.logger.query()), 0)

    def test_stats(self):
        """测试统计信息"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.log("user1", AuditAction.DELETE, "article", "2", result="failure")
        stats = self.logger.get_stats()
        self.assertEqual(stats["total_entries"], 2)
        self.assertEqual(stats["by_action"]["create"], 1)
        self.assertEqual(stats["by_result"]["failure"], 1)


class TestAuditReport(unittest.TestCase):
    """审计报告测试"""

    def setUp(self):
        self.logger = AuditLogger()
        self.report = AuditReport(self.logger)

    def test_generate_report(self):
        """测试生成报告"""
        start = time.time()
        self.logger.log("user1", AuditAction.CREATE, "article", "1")
        self.logger.log("user1", AuditAction.UPDATE, "article", "2")
        end = time.time()

        report = self.report.generate_report(start, end)
        self.assertEqual(report["total_entries"], 2)
        self.assertEqual(report["user_activity"]["user1"], 2)
        self.assertEqual(report["failure_rate"], 0.0)

    def test_check_compliance(self):
        """测试合规性检查"""
        self.logger.log("user1", AuditAction.CREATE, "article", "1", result="failure")

        def check_success(entry):
            return entry.result == "success"

        violations = self.report.check_compliance([check_success])
        self.assertEqual(len(violations), 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_audit_logger(self):
        """测试获取全局审计日志"""
        l1 = get_audit_logger()
        l2 = get_audit_logger()
        self.assertIs(l1, l2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 87 - 审计日志系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAuditLogger))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAuditReport))
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
