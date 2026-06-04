"""
Phase 58 - 自然语言处理工具测试
验证文本预处理、分词、关键词提取和相似度计算功能是否正常工作
"""
import unittest
from src.utils.nlp_utils import (
    TextPreprocessor,
    KeywordExtractor,
    TextSimilarity,
    SentimentAnalyzer,
    TextSearchEngine,
    TextDocument,
    get_text_search_engine
)


class TestTextPreprocessor(unittest.TestCase):
    """文本预处理器测试"""

    def test_tokenize(self):
        """测试分词"""
        preprocessor = TextPreprocessor()
        tokens = preprocessor.tokenize("Hello world! This is a test.")
        self.assertEqual(tokens, ["hello", "world", "this", "is", "a", "test"])

    def test_remove_stopwords(self):
        """测试移除停用词"""
        preprocessor = TextPreprocessor()
        tokens = ["hello", "the", "world", "is", "great"]
        filtered = preprocessor.remove_stopwords(tokens)
        self.assertEqual(filtered, ["hello", "world", "great"])

    def test_preprocess(self):
        """测试预处理"""
        preprocessor = TextPreprocessor()
        tokens = preprocessor.preprocess("The quick brown fox.")
        self.assertEqual(tokens, ["quick", "brown", "fox"])

    def test_extract_sentences(self):
        """测试提取句子"""
        preprocessor = TextPreprocessor()
        sentences = preprocessor.extract_sentences("Hello world. How are you? I am fine!")
        self.assertEqual(len(sentences), 3)


class TestKeywordExtractor(unittest.TestCase):
    """关键词提取器测试"""

    def test_extract_tf(self):
        """测试TF提取"""
        extractor = KeywordExtractor()
        text = "machine learning is great. machine learning is powerful."
        keywords = extractor.extract_tf(text, top_k=3)
        self.assertTrue(len(keywords) > 0)
        self.assertEqual(keywords[0][0], "machine")

    def test_extract_tfidf(self):
        """测试TF-IDF提取"""
        extractor = KeywordExtractor()
        docs = [
            "machine learning is great",
            "deep learning is powerful",
            "machine learning and deep learning"
        ]
        results = extractor.extract_tfidf(docs, top_k=2)
        self.assertEqual(len(results), 3)


class TestTextSimilarity(unittest.TestCase):
    """文本相似度测试"""

    def test_cosine_similarity_identical(self):
        """测试相同文本的余弦相似度"""
        similarity = TextSimilarity()
        score = similarity.cosine_similarity("hello world", "hello world")
        self.assertAlmostEqual(score, 1.0, places=5)

    def test_cosine_similarity_different(self):
        """测试不同文本的余弦相似度"""
        similarity = TextSimilarity()
        score = similarity.cosine_similarity("hello world", "goodbye world")
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_jaccard_similarity(self):
        """测试Jaccard相似度"""
        similarity = TextSimilarity()
        score = similarity.jaccard_similarity("hello world test", "hello world example")
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestSentimentAnalyzer(unittest.TestCase):
    """情感分析器测试"""

    def test_positive_sentiment(self):
        """测试正面情感"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("This is a great and amazing product!")
        self.assertEqual(result["sentiment"], "positive")
        self.assertGreater(result["score"], 0)

    def test_negative_sentiment(self):
        """测试负面情感"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("This is a terrible and awful product!")
        self.assertEqual(result["sentiment"], "negative")
        self.assertLess(result["score"], 0)

    def test_neutral_sentiment(self):
        """测试中性情感"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("This is a product.")
        self.assertEqual(result["sentiment"], "neutral")


class TestTextSearchEngine(unittest.TestCase):
    """文本搜索引擎测试"""

    def setUp(self):
        """测试前设置"""
        self.engine = TextSearchEngine()
        self.engine.add_document(TextDocument("doc1", "machine learning is powerful"))
        self.engine.add_document(TextDocument("doc2", "deep learning is amazing"))
        self.engine.add_document(TextDocument("doc3", "python programming is great"))

    def test_search(self):
        """测试搜索"""
        results = self.engine.search("machine learning")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0][0], "doc1")

    def test_search_no_match(self):
        """测试无匹配搜索"""
        results = self.engine.search("javascript")
        self.assertEqual(len(results), 0)

    def test_get_document(self):
        """测试获取文档"""
        doc = self.engine.get_document("doc1")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.doc_id, "doc1")

    def test_stats(self):
        """测试统计"""
        stats = self.engine.get_stats()
        self.assertEqual(stats["documents"], 3)
        self.assertTrue(stats["terms"] > 0)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_text_search_engine(self):
        """测试获取全局搜索引擎"""
        e1 = get_text_search_engine()
        e2 = get_text_search_engine()
        self.assertIs(e1, e2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 58 - 自然语言处理工具测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTextPreprocessor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestKeywordExtractor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTextSimilarity))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSentimentAnalyzer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTextSearchEngine))
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
