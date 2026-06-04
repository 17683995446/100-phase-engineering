"""
Phase 77 - 国际化与本地化系统测试
验证多语言支持、翻译管理、区域格式化和文化适配功能
"""
import unittest
from datetime import datetime
from src.utils.i18n import (
    I18nManager,
    Translator,
    LocaleFormatter,
    LocaleConfig,
    get_i18n_manager
)


class TestTranslator(unittest.TestCase):
    """翻译器测试"""

    def setUp(self):
        self.translator = Translator()
        self.translator.load_translations("en", {
            "hello": "Hello",
            "welcome": "Welcome, {name}!"
        })
        self.translator.load_translations("zh", {
            "hello": "你好",
            "welcome": "欢迎, {name}!"
        })

    def test_translate(self):
        """测试翻译"""
        self.assertEqual(self.translator.translate("hello", "en"), "Hello")
        self.assertEqual(self.translator.translate("hello", "zh"), "你好")

    def test_translate_with_params(self):
        """测试带参数的翻译"""
        result = self.translator.translate("welcome", "en", name="Alice")
        self.assertEqual(result, "Welcome, Alice!")

    def test_translate_missing(self):
        """测试缺失翻译"""
        self.assertEqual(self.translator.translate("missing", "en"), "missing")

    def test_has_translation(self):
        """测试检查翻译存在"""
        self.assertTrue(self.translator.has_translation("hello", "en"))
        self.assertFalse(self.translator.has_translation("missing", "en"))

    def test_get_available_locales(self):
        """测试获取可用区域"""
        locales = self.translator.get_available_locales()
        self.assertIn("en", locales)
        self.assertIn("zh", locales)

    def test_stats(self):
        """测试统计信息"""
        stats = self.translator.get_stats()
        self.assertEqual(stats["locales"], 2)
        self.assertEqual(stats["total_keys"], 4)


class TestLocaleFormatter(unittest.TestCase):
    """区域格式化器测试"""

    def setUp(self):
        self.formatter = LocaleFormatter()
        self.formatter.register_locale(LocaleConfig(
            locale="en_US",
            language="en",
            territory="US",
            currency="USD",
            date_format="%m/%d/%Y",
            number_format=",."
        ))
        self.formatter.register_locale(LocaleConfig(
            locale="de_DE",
            language="de",
            territory="DE",
            currency="EUR",
            date_format="%d.%m.%Y",
            number_format=".,"
        ))

    def test_format_date(self):
        """测试格式化日期"""
        dt = datetime(2024, 1, 15)
        self.assertEqual(self.formatter.format_date(dt, "en_US"), "01/15/2024")
        self.assertEqual(self.formatter.format_date(dt, "de_DE"), "15.01.2024")

    def test_format_datetime(self):
        """测试格式化日期时间"""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = self.formatter.format_datetime(dt, "en_US")
        self.assertEqual(result, "2024-01-15 10:30:00")

    def test_format_number(self):
        """测试格式化数字"""
        self.assertEqual(self.formatter.format_number(1234.56, "en_US"), "1,234.56")
        self.assertEqual(self.formatter.format_number(1234.56, "de_DE"), "1.234,56")

    def test_format_currency(self):
        """测试格式化货币"""
        result = self.formatter.format_currency(99.99, "en_US")
        self.assertIn("USD", result)
        self.assertIn("99.99", result)

    def test_list_locales(self):
        """测试列出区域"""
        locales = self.formatter.list_locales()
        self.assertIn("en_US", locales)
        self.assertIn("de_DE", locales)


class TestI18nManager(unittest.TestCase):
    """国际化管理器测试"""

    def setUp(self):
        self.i18n = I18nManager(default_locale="en")
        self.i18n.load_translations("en", {
            "hello": "Hello",
            "goodbye": "Goodbye"
        })
        self.i18n.load_translations("zh", {
            "hello": "你好"
        })

    def test_set_get_locale(self):
        """测试设置和获取区域"""
        self.i18n.set_locale("zh")
        self.assertEqual(self.i18n.get_locale(), "zh")

    def test_t(self):
        """测试快捷翻译"""
        self.assertEqual(self.i18n.t("hello"), "Hello")
        self.i18n.set_locale("zh")
        self.assertEqual(self.i18n.t("hello"), "你好")

    def test_translate_with_locale(self):
        """测试指定区域翻译"""
        self.assertEqual(self.i18n.translate("hello", locale="zh"), "你好")

    def test_load_translations(self):
        """测试加载翻译"""
        self.i18n.load_translations("fr", {"hello": "Bonjour"})
        self.assertEqual(self.i18n.translate("hello", locale="fr"), "Bonjour")

    def test_format_date(self):
        """测试格式化日期"""
        self.i18n.register_locale(LocaleConfig(
            locale="en",
            language="en",
            date_format="%Y-%m-%d"
        ))
        dt = datetime(2024, 1, 15)
        self.assertEqual(self.i18n.format_date(dt), "2024-01-15")

    def test_format_number(self):
        """测试格式化数字"""
        self.i18n.register_locale(LocaleConfig(
            locale="en",
            language="en",
            number_format=",."
        ))
        self.assertEqual(self.i18n.format_number(1234.56), "1,234.56")

    def test_format_currency(self):
        """测试格式化货币"""
        self.i18n.register_locale(LocaleConfig(
            locale="en",
            language="en",
            currency="USD",
            number_format=",."
        ))
        result = self.i18n.format_currency(100.50)
        self.assertIn("USD", result)

    def test_get_available_locales(self):
        """测试获取可用区域"""
        locales = self.i18n.get_available_locales()
        self.assertIn("en", locales)
        self.assertIn("zh", locales)

    def test_stats(self):
        """测试统计信息"""
        stats = self.i18n.get_stats()
        self.assertEqual(stats["current_locale"], "en")
        self.assertEqual(stats["default_locale"], "en")


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_i18n_manager(self):
        """测试获取全局国际化管理器"""
        i1 = get_i18n_manager()
        i2 = get_i18n_manager()
        self.assertIs(i1, i2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 77 - 国际化与本地化系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTranslator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLocaleFormatter))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestI18nManager))
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
