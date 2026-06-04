"""
Phase 57 - 推荐系统引擎测试
验证基于内容和协同过滤的推荐功能是否正常工作
"""
import unittest
from src.utils.recommendation_engine import (
    RecommendationEngine,
    ContentBasedRecommender,
    CollaborativeFilteringRecommender,
    Item,
    UserProfile,
    get_recommendation_engine
)


class TestContentBasedRecommender(unittest.TestCase):
    """基于内容推荐器测试"""

    def setUp(self):
        """测试前设置"""
        self.recommender = ContentBasedRecommender()
        self.recommender.add_item(Item("item1", {"genre": "action", "rating": 5}, tags=["action"]))
        self.recommender.add_item(Item("item2", {"genre": "comedy", "rating": 4}, tags=["comedy"]))
        self.recommender.add_item(Item("item3", {"genre": "action", "rating": 3}, tags=["action"]))

    def test_recommend(self):
        """测试推荐"""
        profile = UserProfile("user1", {"action": 1.0, "genre": "action"})
        recommendations = self.recommender.recommend(profile, top_k=2)

        self.assertEqual(len(recommendations), 2)
        self.assertEqual(recommendations[0].item_id, "item1")

    def test_exclude_history(self):
        """测试排除历史"""
        profile = UserProfile("user1", {"action": 1.0}, history=["item1"])
        recommendations = self.recommender.recommend(profile)

        self.assertNotIn("item1", [r.item_id for r in recommendations])


class TestCollaborativeFilteringRecommender(unittest.TestCase):
    """协同过滤推荐器测试"""

    def setUp(self):
        """测试前设置"""
        self.recommender = CollaborativeFilteringRecommender()
        # 用户1喜欢item1, item2
        self.recommender.add_interaction("user1", "item1", 5.0)
        self.recommender.add_interaction("user1", "item2", 4.0)
        # 用户2喜欢item1, item2, item3
        self.recommender.add_interaction("user2", "item1", 5.0)
        self.recommender.add_interaction("user2", "item2", 4.0)
        self.recommender.add_interaction("user2", "item3", 3.0)
        # 用户3喜欢item2, item3
        self.recommender.add_interaction("user3", "item2", 4.0)
        self.recommender.add_interaction("user3", "item3", 5.0)

    def test_recommend(self):
        """测试推荐"""
        recommendations = self.recommender.recommend("user1", top_k=2)

        # user1和user2相似，应该推荐item3
        self.assertTrue(len(recommendations) > 0)
        item_ids = [r.item_id for r in recommendations]
        self.assertIn("item3", item_ids)

    def test_no_interactions(self):
        """测试无交互用户"""
        recommendations = self.recommender.recommend("user_new")
        self.assertEqual(len(recommendations), 0)


class TestRecommendationEngine(unittest.TestCase):
    """推荐引擎测试"""

    def setUp(self):
        """测试前设置"""
        self.engine = RecommendationEngine()

    def test_add_item(self):
        """测试添加物品"""
        self.engine.add_item(Item("item1", {"genre": "action"}))
        stats = self.engine.get_stats()
        self.assertEqual(stats["items"], 1)

    def test_set_user_profile(self):
        """测试设置用户画像"""
        profile = UserProfile("user1", {"action": 1.0})
        self.engine.set_user_profile(profile)
        self.assertIsNotNone(self.engine.get_user_profile("user1"))

    def test_content_recommendation(self):
        """测试内容推荐"""
        self.engine.add_item(Item("item1", {"genre": "action"}, tags=["action"]))
        self.engine.add_item(Item("item2", {"genre": "comedy"}, tags=["comedy"]))
        self.engine.set_user_profile(UserProfile("user1", {"action": 1.0}))

        recommendations = self.engine.recommend("user1", strategy="content")
        self.assertTrue(len(recommendations) > 0)
        self.assertEqual(recommendations[0].item_id, "item1")

    def test_collaborative_recommendation(self):
        """测试协同过滤推荐"""
        self.engine.add_interaction("user1", "item1", 5.0)
        self.engine.add_interaction("user1", "item2", 4.0)
        self.engine.add_interaction("user2", "item1", 5.0)
        self.engine.add_interaction("user2", "item2", 4.0)
        self.engine.add_interaction("user2", "item3", 3.0)

        recommendations = self.engine.recommend("user1", strategy="collaborative")
        self.assertTrue(len(recommendations) > 0)

    def test_hybrid_recommendation(self):
        """测试混合推荐"""
        self.engine.add_item(Item("item1", {"genre": "action"}, tags=["action"]))
        self.engine.add_item(Item("item2", {"genre": "comedy"}, tags=["comedy"]))
        self.engine.set_user_profile(UserProfile("user1", {"action": 1.0}))
        self.engine.add_interaction("user1", "item1", 5.0)
        self.engine.add_interaction("user2", "item1", 5.0)
        self.engine.add_interaction("user2", "item2", 4.0)

        recommendations = self.engine.recommend("user1", strategy="hybrid")
        self.assertTrue(len(recommendations) > 0)

    def test_add_interaction_updates_history(self):
        """测试交互更新历史"""
        self.engine.set_user_profile(UserProfile("user1", {}))
        self.engine.add_interaction("user1", "item1")

        profile = self.engine.get_user_profile("user1")
        self.assertIn("item1", profile.history)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_recommendation_engine(self):
        """测试获取全局引擎"""
        e1 = get_recommendation_engine()
        e2 = get_recommendation_engine()
        self.assertIs(e1, e2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 57 - 推荐系统引擎测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestContentBasedRecommender))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCollaborativeFilteringRecommender))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRecommendationEngine))
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
