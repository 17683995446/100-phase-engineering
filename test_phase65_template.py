"""
Phase 65 - 模板引擎测试
验证模板解析、变量替换和条件渲染功能是否正常工作
"""
import unittest
from src.utils.template_engine import (
    TemplateEngine,
    get_template_engine
)


class TestTemplateEngine(unittest.TestCase):
    """模板引擎测试"""

    def setUp(self):
        """测试前设置"""
        self.engine = TemplateEngine()

    def test_simple_variable(self):
        """测试简单变量"""
        result = self.engine.render_string("Hello {{ name }}", {"name": "World"})
        self.assertEqual(result, "Hello World")

    def test_nested_variable(self):
        """测试嵌套变量"""
        result = self.engine.render_string("{{ user.name }}", {"user": {"name": "Alice"}})
        self.assertEqual(result, "Alice")

    def test_filter_upper(self):
        """测试大写过滤器"""
        result = self.engine.render_string("{{ name|upper }}", {"name": "hello"})
        self.assertEqual(result, "HELLO")

    def test_filter_lower(self):
        """测试小写过滤器"""
        result = self.engine.render_string("{{ name|lower }}", {"name": "HELLO"})
        self.assertEqual(result, "hello")

    def test_filter_default(self):
        """测试默认过滤器"""
        result = self.engine.render_string("{{ name|default:Guest }}", {})
        self.assertEqual(result, "Guest")

    def test_filter_length(self):
        """测试长度过滤器"""
        result = self.engine.render_string("{{ items|length }}", {"items": [1, 2, 3]})
        self.assertEqual(result, "3")

    def test_conditional_true(self):
        """测试条件为真"""
        template = "{% if show %}visible{% endif %}"
        result = self.engine.render_string(template, {"show": True})
        self.assertEqual(result, "visible")

    def test_conditional_false(self):
        """测试条件为假"""
        template = "{% if show %}visible{% endif %}"
        result = self.engine.render_string(template, {"show": False})
        self.assertEqual(result, "")

    def test_loop(self):
        """测试循环"""
        template = "{% for item in items %}{{ item }}{% endfor %}"
        result = self.engine.render_string(template, {"items": ["a", "b", "c"]})
        self.assertEqual(result, "abc")

    def test_loop_with_variable(self):
        """测试带变量的循环"""
        template = "{% for user in users %}{{ user.name }}{% endfor %}"
        result = self.engine.render_string(template, {
            "users": [{"name": "Alice"}, {"name": "Bob"}]
        })
        self.assertEqual(result, "AliceBob")

    def test_register_template(self):
        """测试注册模板"""
        self.engine.register_template("greeting", "Hello {{ name }}")
        result = self.engine.render("greeting", {"name": "World"})
        self.assertEqual(result, "Hello World")

    def test_template_not_found(self):
        """测试模板不存在"""
        with self.assertRaises(ValueError):
            self.engine.render("nonexistent", {})

    def test_register_filter(self):
        """测试注册过滤器"""
        self.engine.register_filter("double", lambda x: str(x) * 2)
        result = self.engine.render_string("{{ name|double }}", {"name": "hi"})
        self.assertEqual(result, "hihi")

    def test_stats(self):
        """测试统计"""
        self.engine.register_template("t1", "test")
        stats = self.engine.get_stats()
        self.assertEqual(stats["templates"], 1)
        self.assertTrue(stats["filters"] > 0)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_template_engine(self):
        """测试获取全局引擎"""
        e1 = get_template_engine()
        e2 = get_template_engine()
        self.assertIs(e1, e2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 65 - 模板引擎测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTemplateEngine))
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
