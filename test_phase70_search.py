"""
Phase 70 - 全文搜索引擎测试
验证倒排索引、分词、查询和相关性评分功能
"""
import unittest
from src.utils.search_engine import (
    SearchEngine,
    SearchDocument,
    Tokenizer,
    InvertedIndex,
    BM25Scorer,
    get_search_engine
)


class TestTokenizer(unittest.TestCase):
    """分词器测试"""

    def test_tokenize_english(self):
        """测试英文分词"""
        t = Tokenizer()
        tokens = t.tokenize("The quick brown fox jumps")
        self.assertIn("quick", tokens)
        self.assertIn("brown", tokens)
        self.assertIn("fox", tokens)
        self.assertIn("jumps", tokens)
        # 停用词应该被过滤
        self.assertNotIn("the", tokens)

    def test_tokenize_chinese(self):
        """测试中文分词（单字模式）"""
        t = Tokenizer()
        tokens = t.tokenize("搜索引擎测试")
        self.assertIn("搜", tokens)
        self.assertIn("索", tokens)
        self.assertIn("引", tokens)
        self.assertIn("擎", tokens)

    def test_tokenize_empty(self):
        """测试空文本"""
        t = Tokenizer()
        tokens = t.tokenize("")
        self.assertEqual(tokens, [])


class TestInvertedIndex(unittest.TestCase):
    """倒排索引测试"""

    def setUp(self):
        self.index = InvertedIndex()

    def test_add_document(self):
        """测试添加文档"""
        doc = SearchDocument("1", "Test", "hello world")
        self.index.add_document(doc, ["hello", "world"])
        self.assertEqual(self.index.get_stats()["total_documents"], 1)

    def test_remove_document(self):
        """测试移除文档"""
        doc = SearchDocument("1", "Test", "hello world")
        self.index.add_document(doc, ["hello", "world"])
        result = self.index.remove_document("1")
        self.assertTrue(result)
        self.assertEqual(self.index.get_stats()["total_documents"], 0)

    def test_get_term_frequency(self):
        """测试词频"""
        doc = SearchDocument("1", "Test", "hello hello world")
        self.index.add_document(doc, ["hello", "hello", "world"])
        self.assertEqual(self.index.get_term_frequency("hello", "1"), 2)
        self.assertEqual(self.index.get_term_frequency("world", "1"), 1)

    def test_get_document_frequency(self):
        """测试文档频率"""
        self.index.add_document(SearchDocument("1", "Test", "hello"), ["hello"])
        self.index.add_document(SearchDocument("2", "Test", "hello world"), ["hello", "world"])
        self.assertEqual(self.index.get_document_frequency("hello"), 2)
        self.assertEqual(self.index.get_document_frequency("world"), 1)

    def test_clear(self):
        """测试清空"""
        self.index.add_document(SearchDocument("1", "Test", "hello"), ["hello"])
        self.index.clear()
        self.assertEqual(self.index.get_stats()["total_documents"], 0)


class TestBM25Scorer(unittest.TestCase):
    """BM25评分测试"""

    def test_score(self):
        """测试评分"""
        index = InvertedIndex()
        index.add_document(SearchDocument("1", "Test", "hello world"), ["hello", "world"])
        index.add_document(SearchDocument("2", "Test", "hello hello world"), ["hello", "hello", "world"])

        scorer = BM25Scorer()
        score1 = scorer.score(index, ["hello"], "1")
        score2 = scorer.score(index, ["hello"], "2")

        # 文档2中hello出现更多次，得分应该更高
        self.assertGreater(score2, score1)


class TestSearchEngine(unittest.TestCase):
    """搜索引擎测试"""

    def setUp(self):
        self.engine = SearchEngine()
        # 索引一些测试文档
        self.engine.index_document(SearchDocument(
            "1", "Python Tutorial", "Python is a great programming language",
            {"category": "programming"}
        ))
        self.engine.index_document(SearchDocument(
            "2", "Java Guide", "Java is also a popular programming language",
            {"category": "programming"}
        ))
        self.engine.index_document(SearchDocument(
            "3", "Cooking Tips", "How to cook delicious food",
            {"category": "cooking"}
        ))

    def test_index_document(self):
        """测试索引文档"""
        result = self.engine.index_document(SearchDocument(
            "4", "New Doc", "New content"
        ))
        self.assertTrue(result)
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_documents"], 4)

    def test_search_basic(self):
        """测试基本搜索"""
        result = self.engine.search("python")
        self.assertGreaterEqual(result.total, 1)
        self.assertEqual(result.documents[0].doc_id, "1")

    def test_search_relevance(self):
        """测试相关性排序"""
        # 索引一个包含更多"programming"的文档
        self.engine.index_document(SearchDocument(
            "4", "Programming Deep Dive",
            "programming programming programming concepts"
        ))
        result = self.engine.search("programming")
        self.assertGreaterEqual(len(result.documents), 1)
        # 得分最高的应该是包含最多programming的文档
        self.assertEqual(result.documents[0].doc_id, "4")

    def test_search_no_results(self):
        """测试无结果搜索"""
        result = self.engine.search("nonexistent")
        self.assertEqual(result.total, 0)
        self.assertEqual(len(result.documents), 0)

    def test_search_filters(self):
        """测试过滤搜索"""
        result = self.engine.search("language", filters={"metadata": {"category": "cooking"}})
        # cooking分类的文档不包含"language"
        self.assertEqual(result.total, 0)

    def test_search_top_k(self):
        """测试限制结果数量"""
        result = self.engine.search("programming", top_k=1)
        self.assertLessEqual(len(result.documents), 1)

    def test_remove_document(self):
        """测试移除文档"""
        self.engine.remove_document("1")
        result = self.engine.search("python")
        self.assertEqual(result.total, 0)

    def test_get_document(self):
        """测试获取文档"""
        doc = self.engine.get_document("1")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.title, "Python Tutorial")

    def test_clear(self):
        """测试清空"""
        self.engine.clear()
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_documents"], 0)

    def test_stats(self):
        """测试统计信息"""
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_documents"], 3)
        self.assertGreater(stats["unique_terms"], 0)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_search_engine(self):
        """测试获取全局搜索引擎"""
        e1 = get_search_engine()
        e2 = get_search_engine()
        self.assertIs(e1, e2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 70 - 全文搜索引擎测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTokenizer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestInvertedIndex))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBM25Scorer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSearchEngine))
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
