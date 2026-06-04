"""
推荐系统引擎
提供基于内容和协同过滤的推荐功能
"""
import math
import threading
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


@dataclass
class Item:
    """推荐项"""
    item_id: str
    features: Dict[str, Any] = field(default_factory=dict)
    category: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "features": self.features,
            "category": self.category,
            "tags": self.tags
        }


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    preferences: Dict[str, float] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "preferences": self.preferences,
            "history": self.history
        }


@dataclass
class Recommendation:
    """推荐结果"""
    item_id: str
    score: float
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "score": self.score,
            "reason": self.reason
        }


class ContentBasedRecommender:
    """基于内容的推荐器"""
    
    def __init__(self):
        self._items: Dict[str, Item] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("content.recommender")
    
    def add_item(self, item: Item) -> None:
        """添加物品"""
        with self._lock:
            self._items[item.item_id] = item
    
    def recommend(self, user_profile: UserProfile, 
                  top_k: int = 10) -> List[Recommendation]:
        """基于内容推荐"""
        with self._lock:
            items = list(self._items.values())
        
        scores = []
        for item in items:
            if item.item_id in user_profile.history:
                continue
            
            score = self._calculate_similarity(user_profile.preferences, item)
            if score > 0:
                scores.append(Recommendation(
                    item_id=item.item_id,
                    score=score,
                    reason="content_similarity"
                ))
        
        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[:top_k]
    
    def _calculate_similarity(self, preferences: Dict[str, float], 
                              item: Item) -> float:
        """计算相似度"""
        score = 0.0
        for key, value in preferences.items():
            if key in item.features:
                item_value = item.features[key]
                if isinstance(item_value, (int, float)):
                    score += 1.0 - abs(value - item_value) / max(abs(value), abs(item_value), 1)
                elif str(item_value).lower() == str(value).lower():
                    score += 1.0
        
        # 标签匹配
        for tag in item.tags:
            if tag in preferences:
                score += preferences[tag]
        
        return score


class CollaborativeFilteringRecommender:
    """协同过滤推荐器"""
    
    def __init__(self):
        self._user_item_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._item_user_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._lock = threading.RLock()
        self._logger = get_logger("cf.recommender")
    
    def add_interaction(self, user_id: str, item_id: str, 
                        rating: float = 1.0) -> None:
        """添加用户-物品交互"""
        with self._lock:
            self._user_item_matrix[user_id][item_id] = rating
            self._item_user_matrix[item_id][user_id] = rating
    
    def recommend(self, user_id: str, top_k: int = 10) -> List[Recommendation]:
        """协同过滤推荐"""
        with self._lock:
            user_ratings = self._user_item_matrix.get(user_id, {})
            if not user_ratings:
                return []
            
            # 找到相似用户
            similar_users = self._find_similar_users(user_id)
            
            # 推荐相似用户喜欢的物品
            item_scores: Dict[str, float] = defaultdict(float)
            item_counts: Dict[str, int] = defaultdict(int)
            
            for similar_user, similarity in similar_users:
                for item_id, rating in self._user_item_matrix[similar_user].items():
                    if item_id not in user_ratings:
                        item_scores[item_id] += rating * similarity
                        item_counts[item_id] += 1
            
            recommendations = []
            for item_id, score in item_scores.items():
                if item_counts[item_id] > 0:
                    recommendations.append(Recommendation(
                        item_id=item_id,
                        score=score / item_counts[item_id],
                        reason="collaborative_filtering"
                    ))
            
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations[:top_k]
    
    def _find_similar_users(self, user_id: str, 
                            top_n: int = 10) -> List[Tuple[str, float]]:
        """找到相似用户"""
        target_ratings = self._user_item_matrix.get(user_id, {})
        similarities = []
        
        for other_user, other_ratings in self._user_item_matrix.items():
            if other_user == user_id:
                continue
            
            similarity = self._cosine_similarity(target_ratings, other_ratings)
            if similarity > 0:
                similarities.append((other_user, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]
    
    def _cosine_similarity(self, ratings1: Dict[str, float], 
                           ratings2: Dict[str, float]) -> float:
        """计算余弦相似度"""
        common_items = set(ratings1.keys()) & set(ratings2.keys())
        if not common_items:
            return 0.0
        
        dot_product = sum(ratings1[item] * ratings2[item] for item in common_items)
        norm1 = math.sqrt(sum(r ** 2 for r in ratings1.values()))
        norm2 = math.sqrt(sum(r ** 2 for r in ratings2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class RecommendationEngine:
    """推荐引擎"""
    
    def __init__(self):
        self._content_recommender = ContentBasedRecommender()
        self._cf_recommender = CollaborativeFilteringRecommender()
        self._user_profiles: Dict[str, UserProfile] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("recommendation.engine")
    
    def add_item(self, item: Item) -> None:
        """添加物品"""
        self._content_recommender.add_item(item)
    
    def set_user_profile(self, profile: UserProfile) -> None:
        """设置用户画像"""
        with self._lock:
            self._user_profiles[profile.user_id] = profile
    
    def add_interaction(self, user_id: str, item_id: str, 
                        rating: float = 1.0) -> None:
        """添加交互"""
        self._cf_recommender.add_interaction(user_id, item_id, rating)
        
        with self._lock:
            if user_id in self._user_profiles:
                self._user_profiles[user_id].history.append(item_id)
    
    def recommend(self, user_id: str, top_k: int = 10,
                  strategy: str = "hybrid") -> List[Recommendation]:
        """推荐"""
        recommendations = []
        
        if strategy in ("content", "hybrid"):
            profile = self._user_profiles.get(user_id)
            if profile:
                content_recs = self._content_recommender.recommend(profile, top_k)
                recommendations.extend(content_recs)
        
        if strategy in ("collaborative", "hybrid"):
            cf_recs = self._cf_recommender.recommend(user_id, top_k)
            recommendations.extend(cf_recs)
        
        # 去重并排序
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec.item_id not in seen:
                seen.add(rec.item_id)
                unique_recs.append(rec)
        
        unique_recs.sort(key=lambda x: x.score, reverse=True)
        return unique_recs[:top_k]
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像"""
        with self._lock:
            return self._user_profiles.get(user_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "users": len(self._user_profiles),
                "items": len(self._content_recommender._items)
            }


# 全局实例
_engine: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    """获取推荐引擎"""
    global _engine
    if _engine is None:
        _engine = RecommendationEngine()
    return _engine
