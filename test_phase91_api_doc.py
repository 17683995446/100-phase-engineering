"""
Phase 91 - API文档生成器测试
验证API解析、文档生成、OpenAPI导出和版本管理功能
"""
import unittest
from src.utils.api_doc_generator import (
    APIDocGenerator,
    APIEndpoint,
    APIParameter,
    HttpMethod,
    get_api_doc_generator
)


class TestAPIDocGenerator(unittest.TestCase):
    """API文档生成器测试"""

    def setUp(self):
        self.generator = APIDocGenerator()

    def test_create_document(self):
        """测试创建文档"""
        doc = self.generator.create_document("doc1", "API", "1.0")
        self.assertEqual(doc.title, "API")
        self.assertEqual(doc.version, "1.0")

    def test_create_duplicate(self):
        """测试创建重复文档"""
        self.generator.create_document("doc1", "API", "1.0")
        with self.assertRaises(ValueError):
            self.generator.create_document("doc1", "API2", "2.0")

    def test_add_endpoint(self):
        """测试添加端点"""
        self.generator.create_document("doc1", "API", "1.0")
        endpoint = APIEndpoint("/users", HttpMethod.GET, summary="Get users")
        result = self.generator.add_endpoint("doc1", endpoint)
        self.assertTrue(result)
        self.assertEqual(len(self.generator.get_document("doc1").endpoints), 1)

    def test_remove_endpoint(self):
        """测试移除端点"""
        self.generator.create_document("doc1", "API", "1.0")
        self.generator.add_endpoint("doc1", APIEndpoint("/users", HttpMethod.GET))
        result = self.generator.remove_endpoint("doc1", "/users", HttpMethod.GET)
        self.assertTrue(result)
        self.assertEqual(len(self.generator.get_document("doc1").endpoints), 0)

    def test_export_openapi(self):
        """测试导出OpenAPI"""
        self.generator.create_document("doc1", "API", "1.0")
        endpoint = APIEndpoint(
            "/users",
            HttpMethod.GET,
            summary="Get users",
            responses={"200": "Success"}
        )
        self.generator.add_endpoint("doc1", endpoint)
        openapi = self.generator.export_openapi("doc1")
        self.assertIsNotNone(openapi)
        self.assertIn("openapi", openapi)
        self.assertIn("3.0.0", openapi)

    def test_export_markdown(self):
        """测试导出Markdown"""
        self.generator.create_document("doc1", "API", "1.0")
        endpoint = APIEndpoint("/users", HttpMethod.GET, summary="Get users")
        self.generator.add_endpoint("doc1", endpoint)
        md = self.generator.export_markdown("doc1")
        self.assertIsNotNone(md)
        self.assertIn("# API", md)
        self.assertIn("GET /users", md)

    def test_list_documents(self):
        """测试列出文档"""
        self.generator.create_document("doc1", "API1", "1.0")
        self.generator.create_document("doc2", "API2", "1.0")
        docs = self.generator.list_documents()
        self.assertEqual(len(docs), 2)

    def test_delete_document(self):
        """测试删除文档"""
        self.generator.create_document("doc1", "API", "1.0")
        result = self.generator.delete_document("doc1")
        self.assertTrue(result)
        self.assertIsNone(self.generator.get_document("doc1"))

    def test_stats(self):
        """测试统计信息"""
        self.generator.create_document("doc1", "API", "1.0")
        self.generator.add_endpoint("doc1", APIEndpoint("/users", HttpMethod.GET))
        stats = self.generator.get_stats()
        self.assertEqual(stats["total_documents"], 1)
        self.assertEqual(stats["total_endpoints"], 1)


class TestAPIEndpoint(unittest.TestCase):
    """API端点测试"""

    def test_to_dict(self):
        """测试转字典"""
        endpoint = APIEndpoint(
            "/users",
            HttpMethod.GET,
            summary="Get users",
            parameters=[APIParameter("id", "string", required=True)]
        )
        d = endpoint.to_dict()
        self.assertEqual(d["path"], "/users")
        self.assertEqual(d["method"], "GET")
        self.assertEqual(len(d["parameters"]), 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_api_doc_generator(self):
        """测试获取全局API文档生成器"""
        g1 = get_api_doc_generator()
        g2 = get_api_doc_generator()
        self.assertIs(g1, g2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 91 - API文档生成器测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAPIDocGenerator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAPIEndpoint))
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
