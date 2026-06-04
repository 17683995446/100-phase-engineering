"""
全文搜索引擎
提供倒排索引、分词、查询和相关性评分功能
"""
import re
import math
import threading
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from src.utils.structured_logging import get_logger


@dataclass
class SearchDocument:
    """搜索文档"""
    doc_id: str
    title: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "metadata": self.metadata,
            "score": round(self.score, 4)
        }


@dataclass
class SearchResult:
    """搜索结果"""
    total: int
    documents: List[SearchDocument]
    query: str = ""
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "query": self.query,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "documents": [d.to_dict() for d in self.documents]
        }


class Tokenizer:
    """简单分词器"""

    def __init__(self):
        self._logger = get_logger("search.tokenizer")

    def tokenize(self, text: str) -> List[str]:
        """分词：提取小写单词和中文字符"""
        if not text:
            return []
        # 保留中文字符和英文单词
        tokens = re.findall(r'[a-zA-Z]+|[\u4e00-\u9fff]', text.lower())
        # 过滤停用词（英文停用词，中文字符保留）
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
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
                      "your", "his", "its", "our", "their"}
        result = []
        for t in tokens:
            # 中文字符直接保留
            if '\u4e00' <= t <= '\u9fff':
                result.append(t)
            elif t not in stop_words and len(t) > 1:
                result.append(t)
        return result


class InvertedIndex:
    """倒排索引"""

    def __init__(self):
        # token -> {doc_id -> frequency}
        self._index: Dict[str, Dict[str, int]] = defaultdict(dict)
        # doc_id -> document length (token count)
        self._doc_lengths: Dict[str, int] = {}
        # doc_id -> original document
        self._documents: Dict[str, SearchDocument] = {}
        self._total_docs = 0
        self._lock = threading.RLock()
        self._logger = get_logger("search.index")

    def add_document(self, document: SearchDocument, tokens: List[str]) -> None:
        """添加文档到索引"""
        with self._lock:
            doc_id = document.doc_id
            self._documents[doc_id] = document
            self._doc_lengths[doc_id] = len(tokens)

            # 统计词频
            token_counts = defaultdict(int)
            for token in tokens:
                token_counts[token] += 1

            for token, count in token_counts.items():
                self._index[token][doc_id] = count

            self._total_docs = len(self._documents)

    def remove_document(self, doc_id: str) -> bool:
        """从索引中移除文档"""
        with self._lock:
            if doc_id not in self._documents:
                return False

            del self._documents[doc_id]
            del self._doc_lengths[doc_id]

            for token in list(self._index.keys()):
                if doc_id in self._index[token]:
                    del self._index[token][doc_id]
                if not self._index[token]:
                    del self._index[token]

            self._total_docs = len(self._documents)
            return True

    def get_document_frequency(self, token: str) -> int:
        """获取包含该词的文档数"""
        with self._lock:
            return len(self._index.get(token, {}))

    def get_term_frequency(self, token: str, doc_id: str) -> int:
        """获取词在文档中的频率"""
        with self._lock:
            return self._index.get(token, {}).get(doc_id, 0)

    def get_postings(self, token: str) -> Dict[str, int]:
        """获取倒排列表"""
        with self._lock:
            return dict(self._index.get(token, {}))

    def get_document(self, doc_id: str) -> Optional[SearchDocument]:
        """获取文档"""
        with self._lock:
            return self._documents.get(doc_id)

    def get_all_doc_ids(self) -> Set[str]:
        """获取所有文档ID"""
        with self._lock:
            return set(self._documents.keys())

    def get_avg_doc_length(self) -> float:
        """获取平均文档长度"""
        with self._lock:
            if not self._doc_lengths:
                return 0.0
            return sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def clear(self) -> None:
        """清空索引"""
        with self._lock:
            self._index.clear()
            self._doc_lengths.clear()
            self._documents.clear()
            self._total_docs = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_documents": self._total_docs,
                "unique_terms": len(self._index),
                "avg_doc_length": round(self.get_avg_doc_length(), 2)
            }


class BM25Scorer:
    """BM25相关性评分"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._logger = get_logger("search.bm25")

    def score(self, index: InvertedIndex, query_tokens: List[str],
              doc_id: str) -> float:
        """计算文档与查询的相关性得分"""
        score = 0.0
        doc_length = index._doc_lengths.get(doc_id, 0)
        avg_length = index.get_avg_doc_length()
        total_docs = max(index._total_docs, 1)

        for token in query_tokens:
            tf = index.get_term_frequency(token, doc_id)
            if tf == 0:
                continue

            df = index.get_document_frequency(token)
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)

            tf_component = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * (doc_length / max(avg_length, 1)))
            )

            score += idf * tf_component

        return score


class SearchEngine:
    """全文搜索引擎"""

    def __init__(self):
        self._index = InvertedIndex()
        self._tokenizer = Tokenizer()
        self._scorer = BM25Scorer()
        self._lock = threading.RLock()
        self._logger = get_logger("search.engine")

    def index_document(self, document: SearchDocument) -> bool:
        """索引文档"""
        try:
            text = f"{document.title} {document.content}"
            tokens = self._tokenizer.tokenize(text)
            self._index.add_document(document, tokens)
            return True
        except Exception as e:
            self._logger.error(f"Failed to index document {document.doc_id}: {e}")
            return False

    def remove_document(self, doc_id: str) -> bool:
        """移除文档"""
        return self._index.remove_document(doc_id)

    def search(self, query: str, top_k: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> SearchResult:
        """搜索文档"""
        import time
        start = time.time()

        query_tokens = self._tokenizer.tokenize(query)
        if not query_tokens:
            return SearchResult(total=0, documents=[], query=query)

        # 获取候选文档（包含任意查询词的文档）
        candidate_ids: Set[str] = set()
        for token in query_tokens:
            postings = self._index.get_postings(token)
            candidate_ids.update(postings.keys())

        # 应用过滤器
        if filters:
            filtered_ids = set()
            for doc_id in candidate_ids:
                doc = self._index.get_document(doc_id)
                if doc and self._match_filters(doc, filters):
                    filtered_ids.add(doc_id)
            candidate_ids = filtered_ids

        # 评分并排序
        scored_docs: List[Tuple[str, float]] = []
        for doc_id in candidate_ids:
            score = self._scorer.score(self._index, query_tokens, doc_id)
            scored_docs.append((doc_id, score))

        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 构建结果
        results: List[SearchDocument] = []
        for doc_id, score in scored_docs[:top_k]:
            doc = self._index.get_document(doc_id)
            if doc:
                doc.score = score
                results.append(doc)

        elapsed = (time.time() - start) * 1000

        return SearchResult(
            total=len(candidate_ids),
            documents=results,
            query=query,
            elapsed_ms=elapsed
        )

    def _match_filters(self, doc: SearchDocument,
                       filters: Dict[str, Any]) -> bool:
        """检查文档是否匹配过滤器"""
        for key, value in filters.items():
            if key == "title_contains":
                if value.lower() not in doc.title.lower():
                    return False
            elif key == "metadata":
                for meta_key, meta_value in value.items():
                    if doc.metadata.get(meta_key) != meta_value:
                        return False
            else:
                if doc.metadata.get(key) != value:
                    return False
        return True

    def get_document(self, doc_id: str) -> Optional[SearchDocument]:
        """获取文档"""
        return self._index.get_document(doc_id)

    def clear(self) -> None:
        """清空索引"""
        self._index.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._index.get_stats()


# 全局实例
_engine: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    """获取全局搜索引擎"""
    global _engine
    if _engine is None:
        _engine = SearchEngine()
    return _engine
