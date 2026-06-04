"""
自然语言处理工具
提供文本预处理、分词、关键词提取和相似度计算功能
"""
import re
import math
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


@dataclass
class TextDocument:
    """文本文档"""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "content": self.content[:100] + "..." if len(self.content) > 100 else self.content,
            "metadata": self.metadata
        }


class TextPreprocessor:
    """文本预处理器"""
    
    def __init__(self):
        self._logger = get_logger("text.preprocessor")
        self._stopwords = self._load_default_stopwords()
    
    def _load_default_stopwords(self) -> Set[str]:
        """加载默认停用词"""
        return {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "and", "but", "or", "yet", "so",
            "if", "because", "although", "though", "while", "where",
            "when", "that", "which", "who", "whom", "whose", "what",
            "this", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "me", "him", "her", "us", "them", "my",
            "your", "his", "its", "our", "their"
        }
    
    def tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单基于空格和标点的分词
        text = text.lower()
        tokens = re.findall(r'\b[a-z]+\b', text)
        return tokens
    
    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """移除停用词"""
        return [token for token in tokens if token not in self._stopwords]
    
    def preprocess(self, text: str, remove_stop: bool = True) -> List[str]:
        """预处理文本"""
        tokens = self.tokenize(text)
        if remove_stop:
            tokens = self.remove_stopwords(tokens)
        return tokens
    
    def extract_sentences(self, text: str) -> List[str]:
        """提取句子"""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]


class KeywordExtractor:
    """关键词提取器"""
    
    def __init__(self):
        self._preprocessor = TextPreprocessor()
        self._logger = get_logger("keyword.extractor")
    
    def extract_tf(self, text: str, top_k: int = 10) -> List[Tuple[str, int]]:
        """基于词频提取关键词"""
        tokens = self._preprocessor.preprocess(text)
        freq = Counter(tokens)
        return freq.most_common(top_k)
    
    def extract_tfidf(self, documents: List[str], 
                      top_k: int = 10) -> Dict[str, Dict[str, float]]:
        """基于TF-IDF提取关键词"""
        # 预处理所有文档
        processed_docs = []
        for doc in documents:
            tokens = self._preprocessor.preprocess(doc)
            processed_docs.append(tokens)
        
        # 计算IDF
        idf = self._compute_idf(processed_docs)
        
        results = {}
        for i, tokens in enumerate(processed_docs):
            tf = Counter(tokens)
            tfidf = {}
            for term, count in tf.items():
                tfidf[term] = (count / len(tokens)) * idf.get(term, 0)
            
            sorted_terms = sorted(tfidf.items(), key=lambda x: x[1], reverse=True)
            results[f"doc_{i}"] = dict(sorted_terms[:top_k])
        
        return results
    
    def _compute_idf(self, documents: List[List[str]]) -> Dict[str, float]:
        """计算IDF"""
        N = len(documents)
        doc_freq = Counter()
        
        for tokens in documents:
            unique_terms = set(tokens)
            for term in unique_terms:
                doc_freq[term] += 1
        
        idf = {}
        for term, freq in doc_freq.items():
            idf[term] = math.log(N / (freq + 1)) + 1
        
        return idf


class TextSimilarity:
    """文本相似度"""
    
    def __init__(self):
        self._preprocessor = TextPreprocessor()
        self._logger = get_logger("text.similarity")
    
    def cosine_similarity(self, text1: str, text2: str) -> float:
        """计算余弦相似度"""
        tokens1 = Counter(self._preprocessor.preprocess(text1))
        tokens2 = Counter(self._preprocessor.preprocess(text2))
        
        all_terms = set(tokens1.keys()) | set(tokens2.keys())
        
        dot_product = sum(tokens1.get(term, 0) * tokens2.get(term, 0) for term in all_terms)
        norm1 = math.sqrt(sum(count ** 2 for count in tokens1.values()))
        norm2 = math.sqrt(sum(count ** 2 for count in tokens2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def jaccard_similarity(self, text1: str, text2: str) -> float:
        """计算Jaccard相似度"""
        tokens1 = set(self._preprocessor.preprocess(text1))
        tokens2 = set(self._preprocessor.preprocess(text2))
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)


class SentimentAnalyzer:
    """情感分析器（简单实现）"""
    
    def __init__(self):
        self._positive_words = {
            "good", "great", "excellent", "amazing", "wonderful", "fantastic",
            "love", "like", "happy", "pleased", "satisfied", "perfect",
            "best", "awesome", "brilliant", "outstanding", "superb"
        }
        self._negative_words = {
            "bad", "terrible", "awful", "horrible", "hate", "dislike",
            "angry", "sad", "disappointed", "poor", "worst", "ugly",
            "boring", "annoying", "frustrated", "unhappy", "unsatisfied"
        }
        self._logger = get_logger("sentiment.analyzer")
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """分析情感"""
        preprocessor = TextPreprocessor()
        tokens = preprocessor.preprocess(text, remove_stop=False)
        
        positive_count = sum(1 for token in tokens if token in self._positive_words)
        negative_count = sum(1 for token in tokens if token in self._negative_words)
        total = positive_count + negative_count
        
        if total == 0:
            sentiment = "neutral"
            score = 0.0
        else:
            score = (positive_count - negative_count) / total
            if score > 0.1:
                sentiment = "positive"
            elif score < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "score": score,
            "positive_words": positive_count,
            "negative_words": negative_count
        }


class TextSearchEngine:
    """文本搜索引擎"""
    
    def __init__(self):
        self._documents: Dict[str, TextDocument] = {}
        self._inverted_index: Dict[str, Set[str]] = {}
        self._preprocessor = TextPreprocessor()
        self._lock = threading.RLock()
        self._logger = get_logger("text.search")
    
    def add_document(self, document: TextDocument) -> None:
        """添加文档"""
        tokens = self._preprocessor.preprocess(document.content)
        
        with self._lock:
            self._documents[document.doc_id] = document
            
            for token in tokens:
                if token not in self._inverted_index:
                    self._inverted_index[token] = set()
                self._inverted_index[token].add(document.doc_id)
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """搜索文档"""
        query_tokens = self._preprocessor.preprocess(query)
        
        if not query_tokens:
            return []
        
        with self._lock:
            scores: Dict[str, float] = {}
            
            for token in query_tokens:
                doc_ids = self._inverted_index.get(token, set())
                for doc_id in doc_ids:
                    scores[doc_id] = scores.get(doc_id, 0) + 1
            
            # 归一化
            for doc_id in scores:
                doc = self._documents[doc_id]
                doc_tokens = self._preprocessor.preprocess(doc.content)
                scores[doc_id] /= len(doc_tokens) if doc_tokens else 1
            
            results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            return results[:top_k]
    
    def get_document(self, doc_id: str) -> Optional[TextDocument]:
        """获取文档"""
        with self._lock:
            return self._documents.get(doc_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "documents": len(self._documents),
                "terms": len(self._inverted_index)
            }


# 全局实例
_search_engine: Optional[TextSearchEngine] = None


def get_text_search_engine() -> TextSearchEngine:
    """获取文本搜索引擎"""
    global _search_engine
    if _search_engine is None:
        _search_engine = TextSearchEngine()
    return _search_engine
