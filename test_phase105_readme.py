"""
Phase 105 - README 与项目文档测试
验证 README 和文档的完整性
"""
import unittest
import os


class TestDocumentation(unittest.TestCase):
    """文档完整性测试"""

    def test_readme_exists(self):
        """测试 README 文件存在"""
        self.assertTrue(os.path.exists("/workspace/README.md"))

    def test_readme_not_empty(self):
        """测试 README 文件非空"""
        with open("/workspace/README.md", "r") as f:
            content = f.read()
        self.assertGreater(len(content), 1000)

    def test_readme_has_title(self):
        """测试 README 有标题"""
        with open("/workspace/README.md", "r") as f:
            content = f.read()
        self.assertIn("# 100阶段工程化项目", content)

    def test_readme_has_quick_start(self):
        """测试 README 有快速开始"""
        with open("/workspace/README.md", "r") as f:
            content = f.read()
        self.assertIn("## 快速开始", content)

    def test_readme_has_structure(self):
        """测试 README 有项目结构"""
        with open("/workspace/README.md", "r") as f:
            content = f.read()
        self.assertIn("## 项目结构", content)

    def test_readme_has_module_index(self):
        """测试 README 有模块索引"""
        with open("/workspace/README.md", "r") as f:
            content = f.read()
        self.assertIn("## 模块索引", content)

    def test_readme_has_architecture(self):
        """测试 README 有架构设计"""
        with open("/workspace/README.md", "r") as f:
            content = f.read()
        self.assertIn("## 架构设计", content)

    def test_readme_has_development_guide(self):
        """测试 README 有开发规范"""
        with open("/workspace/README.md", "r") as f:
            content = f.read()
        self.assertIn("## 开发规范", content)

    def test_architecture_doc_exists(self):
        """测试架构文档存在"""
        self.assertTrue(os.path.exists("/workspace/docs/ARCHITECTURE.md"))

    def test_pyproject_exists(self):
        """测试 pyproject.toml 存在"""
        self.assertTrue(os.path.exists("/workspace/pyproject.toml"))


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 105 - README 与项目文档测试")
    print("=" * 60)
    unittest.main(verbosity=2)
