"""
Phase 63 - 规则引擎测试
验证规则定义、评估和执行功能是否正常工作
"""
import unittest
from src.utils.rule_engine import (
    RuleEngine,
    Rule,
    Condition,
    OperatorType,
    get_rule_engine
)


class TestCondition(unittest.TestCase):
    """条件测试"""

    def test_equals(self):
        """测试等于"""
        cond = Condition("age", OperatorType.EQUALS, 25)
        self.assertTrue(cond.evaluate({"age": 25}))
        self.assertFalse(cond.evaluate({"age": 30}))

    def test_not_equals(self):
        """测试不等于"""
        cond = Condition("status", OperatorType.NOT_EQUALS, "inactive")
        self.assertTrue(cond.evaluate({"status": "active"}))
        self.assertFalse(cond.evaluate({"status": "inactive"}))

    def test_greater_than(self):
        """测试大于"""
        cond = Condition("score", OperatorType.GREATER_THAN, 80)
        self.assertTrue(cond.evaluate({"score": 90}))
        self.assertFalse(cond.evaluate({"score": 70}))

    def test_less_than(self):
        """测试小于"""
        cond = Condition("price", OperatorType.LESS_THAN, 100)
        self.assertTrue(cond.evaluate({"price": 50}))
        self.assertFalse(cond.evaluate({"price": 150}))

    def test_contains(self):
        """测试包含"""
        cond = Condition("name", OperatorType.CONTAINS, "test")
        self.assertTrue(cond.evaluate({"name": "testing"}))
        self.assertFalse(cond.evaluate({"name": "hello"}))

    def test_in(self):
        """测试在列表中"""
        cond = Condition("role", OperatorType.IN, ["admin", "user"])
        self.assertTrue(cond.evaluate({"role": "admin"}))
        self.assertFalse(cond.evaluate({"role": "guest"}))


class TestRule(unittest.TestCase):
    """规则测试"""

    def test_rule_match(self):
        """测试规则匹配"""
        def action(data):
            return "matched"

        rule = Rule("r1", "Test Rule", [
            Condition("age", OperatorType.GREATER_THAN, 18)
        ], action)

        self.assertTrue(rule.evaluate({"age": 25}))
        self.assertFalse(rule.evaluate({"age": 15}))

    def test_rule_execute(self):
        """测试规则执行"""
        def action(data):
            return f"Hello {data['name']}"

        rule = Rule("r1", "Greeting", [
            Condition("name", OperatorType.EQUALS, "Alice")
        ], action)

        result = rule.execute({"name": "Alice"})
        self.assertEqual(result, "Hello Alice")

    def test_disabled_rule(self):
        """测试禁用规则"""
        rule = Rule("r1", "Disabled", [], lambda x: "ok")
        rule.enabled = False
        self.assertFalse(rule.evaluate({}))

    def test_multiple_conditions(self):
        """测试多条件"""
        rule = Rule("r1", "Multi", [
            Condition("age", OperatorType.GREATER_THAN, 18),
            Condition("status", OperatorType.EQUALS, "active")
        ], lambda x: "ok")

        self.assertTrue(rule.evaluate({"age": 25, "status": "active"}))
        self.assertFalse(rule.evaluate({"age": 25, "status": "inactive"}))


class TestRuleEngine(unittest.TestCase):
    """规则引擎测试"""

    def setUp(self):
        """测试前设置"""
        self.engine = RuleEngine()

    def test_add_rule(self):
        """测试添加规则"""
        rule = Rule("r1", "Test", [], lambda x: "ok")
        self.engine.add_rule(rule)
        self.assertIsNotNone(self.engine.get_rule("r1"))

    def test_remove_rule(self):
        """测试移除规则"""
        self.engine.add_rule(Rule("r1", "Test", [], lambda x: "ok"))
        result = self.engine.remove_rule("r1")
        self.assertTrue(result)
        self.assertIsNone(self.engine.get_rule("r1"))

    def test_enable_disable(self):
        """测试启用禁用"""
        self.engine.add_rule(Rule("r1", "Test", [], lambda x: "ok"))
        self.engine.disable_rule("r1")
        self.assertFalse(self.engine.get_rule("r1").enabled)
        self.engine.enable_rule("r1")
        self.assertTrue(self.engine.get_rule("r1").enabled)

    def test_evaluate(self):
        """测试评估"""
        self.engine.add_rule(Rule("r1", "High Score", [
            Condition("score", OperatorType.GREATER_THAN, 80)
        ], lambda x: "high"))

        matched = self.engine.evaluate({"score": 90})
        self.assertEqual(len(matched), 1)

        matched = self.engine.evaluate({"score": 70})
        self.assertEqual(len(matched), 0)

    def test_execute(self):
        """测试执行"""
        results = []

        def action(data):
            results.append(data["value"])
            return data["value"] * 2

        self.engine.add_rule(Rule("r1", "Double", [
            Condition("value", OperatorType.GREATER_THAN, 0)
        ], action))

        self.engine.execute({"value": 5})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], 5)

    def test_priority(self):
        """测试优先级"""
        order = []

        self.engine.add_rule(Rule("r1", "Low", [
            Condition("x", OperatorType.EQUALS, 1)
        ], lambda x: order.append("low"), priority=1))

        self.engine.add_rule(Rule("r2", "High", [
            Condition("x", OperatorType.EQUALS, 1)
        ], lambda x: order.append("high"), priority=10))

        self.engine.execute({"x": 1})
        self.assertEqual(order[0], "high")

    def test_stats(self):
        """测试统计"""
        self.engine.add_rule(Rule("r1", "Test", [], lambda x: "ok"))
        self.engine.add_rule(Rule("r2", "Test", [], lambda x: "ok"))
        self.engine.disable_rule("r2")

        stats = self.engine.get_stats()
        self.assertEqual(stats["total_rules"], 2)
        self.assertEqual(stats["enabled"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_rule_engine(self):
        """测试获取全局引擎"""
        e1 = get_rule_engine()
        e2 = get_rule_engine()
        self.assertIs(e1, e2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 63 - 规则引擎测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCondition))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRuleEngine))
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
