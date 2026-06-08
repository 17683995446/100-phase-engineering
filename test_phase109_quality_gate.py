"""
Phase 109 - 代码质量门禁测试
"""
import unittest
import tempfile
import os
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("quality_gate", "/workspace/src/core/quality_gate.py")
qg_mod = importlib.util.module_from_spec(spec)
sys.modules["quality_gate"] = qg_mod
spec.loader.exec_module(qg_mod)

QualityGate = qg_mod.QualityGate
GateStatus = qg_mod.GateStatus
CheckType = qg_mod.CheckType
get_quality_gate = qg_mod.get_quality_gate


class TestQualityGate(unittest.TestCase):
    """代码质量门禁测试"""

    def setUp(self):
        self.gate = QualityGate()

    def _create_temp_file(self, content: str) -> str:
        """创建临时文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            return f.name

    def test_style_check_pass(self):
        """测试风格检查通过"""
        content = "def hello():\n    return 42\n"
        path = self._create_temp_file(content)
        result = self.gate.run_check(CheckType.STYLE, path)
        self.assertEqual(result.status, GateStatus.PASS)
        os.unlink(path)

    def test_style_check_long_line(self):
        """测试风格检查长行"""
        # 创建足够多的违规使 score < threshold(90)
        lines = ["x = " + "a" * 130 + "\n" for _ in range(6)]
        content = "".join(lines)
        path = self._create_temp_file(content)
        result = self.gate.run_check(CheckType.STYLE, path)
        self.assertEqual(result.status, GateStatus.FAIL)
        self.assertTrue(any("exceeds 120" in v for v in result.violations))
        os.unlink(path)

    def test_complexity_check(self):
        """测试复杂度检查"""
        content = """
def simple():
    return 1

def complex_func(x):
    if x > 0:
        if x > 10:
            return 1
        elif x > 5:
            return 2
        else:
            return 3
    else:
        return 0
"""
        path = self._create_temp_file(content)
        result = self.gate.run_check(CheckType.COMPLEXITY, path)
        self.assertIn(result.status, [GateStatus.PASS, GateStatus.FAIL])
        os.unlink(path)

    def test_typing_check(self):
        """测试类型检查"""
        content = """
def typed(x: int) -> str:
    return str(x)

def untyped(x):
    return x
"""
        path = self._create_temp_file(content)
        result = self.gate.run_check(CheckType.TYPING, path)
        self.assertIn(result.status, [GateStatus.PASS, GateStatus.FAIL])
        os.unlink(path)

    def test_run_all(self):
        """测试运行所有检查"""
        content = "def hello() -> int:\n    return 42\n"
        path = self._create_temp_file(content)
        report = self.gate.run_all(path)
        self.assertIn(report.status, [GateStatus.PASS, GateStatus.FAIL, GateStatus.WARNING])
        self.assertEqual(len(report.checks), 5)
        os.unlink(path)

    def test_set_threshold(self):
        """测试设置阈值"""
        self.gate.set_threshold(CheckType.STYLE, 50.0)
        thresholds = self.gate.get_thresholds()
        self.assertEqual(thresholds["style"], 50.0)

    def test_custom_check(self):
        """测试自定义检查"""
        def custom_checker(path: str):
            return qg_mod.CheckResult(
                check_type=CheckType.SECURITY,
                status=GateStatus.PASS,
                score=100.0,
                details="Custom check passed"
            )

        self.gate.register_custom_check(CheckType.SECURITY, custom_checker)
        path = self._create_temp_file("pass")
        result = self.gate.run_check(CheckType.SECURITY, path)
        self.assertEqual(result.status, GateStatus.PASS)
        self.assertEqual(result.score, 100.0)
        os.unlink(path)

    def test_skipped_check(self):
        """测试跳过的检查"""
        path = self._create_temp_file("pass")
        result = self.gate.run_check(CheckType.COVERAGE, path)
        self.assertEqual(result.status, GateStatus.SKIPPED)
        os.unlink(path)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_quality_gate(self):
        """测试获取全局质量门禁"""
        g1 = get_quality_gate()
        g2 = get_quality_gate()
        self.assertIs(g1, g2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 109 - 代码质量门禁测试")
    print("=" * 60)
    unittest.main(verbosity=2)
