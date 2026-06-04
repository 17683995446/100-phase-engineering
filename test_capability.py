"""
Agent能力增强与动态学习系统验证测试
"""

import pytest
from datetime import datetime
from src.agent_layer.capability import (
    LearningMode,
    SkillLevel,
    SkillRecord,
    CapabilityMetrics,
    LearnedPattern,
    AgentLearningEngine,
    CapabilityAssessment,
    DynamicCapabilityManager,
    get_capability_manager
)


class TestCapabilityMetrics:
    """测试能力指标"""
    
    def test_metrics_creation(self):
        """测试创建指标"""
        metrics = CapabilityMetrics()
        
        assert metrics.total_tasks == 0
        assert metrics.successful_tasks == 0
        assert metrics.failed_tasks == 0
        assert metrics.avg_completion_time == 0.0
    
    def test_success_rate(self):
        """测试成功率计算"""
        metrics = CapabilityMetrics()
        metrics.total_tasks = 10
        metrics.successful_tasks = 7
        
        assert metrics.success_rate == 0.7
    
    def test_failure_rate(self):
        """测试失败率计算"""
        metrics = CapabilityMetrics()
        metrics.total_tasks = 10
        metrics.failed_tasks = 3
        
        assert metrics.failure_rate == 0.3
    
    def test_zero_tasks(self):
        """测试零任务情况"""
        metrics = CapabilityMetrics()
        
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 0.0


class TestLearnedPattern:
    """测试学习到的模式"""
    
    def test_pattern_creation(self):
        """测试创建模式"""
        pattern = LearnedPattern(
            pattern_id="p-001",
            pattern_type="code_structure",
            description="使用列表推导式",
            occurrences=5,
            success_count=4,
            confidence=0.8,
            learned_at=datetime.now(),
            last_used=datetime.now()
        )
        
        assert pattern.pattern_id == "p-001"
        assert pattern.occurrences == 5
    
    def test_success_rate(self):
        """测试模式成功率"""
        pattern = LearnedPattern(
            pattern_id="p-002",
            pattern_type="test",
            description="Test pattern",
            occurrences=10,
            success_count=8,
            confidence=0.8,
            learned_at=datetime.now(),
            last_used=datetime.now()
        )
        
        assert pattern.success_rate == 0.8


class TestAgentLearningEngine:
    """测试Agent学习引擎"""
    
    def test_engine_creation(self):
        """测试创建引擎"""
        engine = AgentLearningEngine("agent-001")
        
        assert engine.agent_id == "agent-001"
        assert len(engine.skill_records) == 0
        assert len(engine.learned_patterns) == 0
    
    def test_record_experience(self):
        """测试记录经验"""
        engine = AgentLearningEngine("agent-002")
        
        record = engine.record_experience(
            capability_name="code_generation",
            task_type="function",
            outcome="success",
            feedback=8.5
        )
        
        assert record.capability_name == "code_generation"
        assert record.feedback == 8.5
        assert len(engine.skill_records) == 1
    
    def test_learn_from_pattern(self):
        """测试从模式学习"""
        engine = AgentLearningEngine("agent-003")
        
        pattern = engine.learn_from_pattern(
            pattern_type="solution",
            description="使用递归",
            success=True
        )
        
        assert pattern.pattern_type == "solution"
        assert pattern.occurrences == 1
        assert len(engine.learned_patterns) == 1
    
    def test_pattern_accumulation(self):
        """测试模式累积"""
        engine = AgentLearningEngine("agent-004")
        
        engine.learn_from_pattern("code", "模式A", True)
        engine.learn_from_pattern("code", "模式A", True)
        engine.learn_from_pattern("code", "模式A", False)
        
        pattern = engine.learned_patterns.get("code:模式A")
        assert pattern is not None
        assert pattern.occurrences == 3
        assert pattern.success_count == 2
    
    def test_get_capability_metrics(self):
        """测试获取能力指标"""
        engine = AgentLearningEngine("agent-005")
        
        engine.record_experience("analysis", "task1", "success", 9.0)
        engine.record_experience("analysis", "task2", "success", 8.0)
        
        metrics = engine.get_capability_metrics("analysis")
        
        assert metrics is not None
        assert metrics.total_tasks == 2
        assert metrics.successful_tasks == 2
    
    def test_suggest_improvement(self):
        """测试建议改进"""
        engine = AgentLearningEngine("agent-006")
        
        for i in range(10):
            engine.record_experience("debugging", f"task{i}", "failure", 3.0)
        
        suggestions = engine.suggest_improvement()
        
        assert len(suggestions) > 0


class TestCapabilityAssessment:
    """测试能力评估"""
    
    def test_assessment_creation(self):
        """测试创建评估"""
        assessment = CapabilityAssessment()
        assert assessment.assessment_id is not None
    
    def test_assess_novel_agent(self):
        """测试评估新手Agent"""
        assessment = CapabilityAssessment()
        
        metrics = CapabilityMetrics()
        
        result = assessment.assess_agent_capability(metrics, [])
        
        assert result["level"] == SkillLevel.NOVICE
    
    def test_assess_experienced_agent(self):
        """测试评估有经验的Agent"""
        assessment = CapabilityAssessment()
        
        metrics = CapabilityMetrics()
        metrics.total_tasks = 100
        metrics.successful_tasks = 90
        metrics.avg_quality_score = 8.5
        
        result = assessment.assess_agent_capability(metrics, [])
        
        assert result["composite_score"] > 0.5
    
    def test_compare_agents(self):
        """测试比较Agent"""
        assessment = CapabilityAssessment()
        
        metrics_a = CapabilityMetrics()
        metrics_a.total_tasks = 10
        metrics_a.successful_tasks = 9
        
        metrics_b = CapabilityMetrics()
        metrics_b.total_tasks = 10
        metrics_b.successful_tasks = 7
        
        result = assessment.compare_agents(metrics_a, metrics_b)
        
        assert result["better_agent"] == "A"


class TestDynamicCapabilityManager:
    """测试动态能力管理器"""
    
    def test_manager_creation(self):
        """测试创建管理器"""
        manager = DynamicCapabilityManager()
        
        assert len(manager.agent_engines) == 0
    
    def test_get_or_create_engine(self):
        """测试获取或创建引擎"""
        manager = DynamicCapabilityManager()
        
        engine1 = manager.get_or_create_engine("agent-new")
        engine2 = manager.get_or_create_engine("agent-new")
        
        assert engine1 is engine2
        assert len(manager.agent_engines) == 1
    
    def test_record_task_result(self):
        """测试记录任务结果"""
        manager = DynamicCapabilityManager()
        
        manager.record_task_result(
            agent_id="agent-001",
            capability_name="coding",
            task_type="function",
            outcome="success",
            feedback=9.0
        )
        
        engine = manager.agent_engines.get("agent-001")
        assert engine is not None
        assert len(engine.skill_records) == 1
    
    def test_learn_pattern(self):
        """测试学习模式"""
        manager = DynamicCapabilityManager()
        
        manager.learn_pattern(
            agent_id="agent-002",
            pattern_type="solution",
            description="使用DP",
            success=True
        )
        
        engine = manager.agent_engines.get("agent-002")
        assert len(engine.learned_patterns) == 1
    
    def test_find_best_agent(self):
        """测试找到最佳Agent"""
        manager = DynamicCapabilityManager()
        
        manager.record_task_result("agent-a", "analysis", "task1", "success", 9.0)
        manager.record_task_result("agent-a", "analysis", "task2", "success", 9.0)
        
        manager.record_task_result("agent-b", "analysis", "task1", "success", 7.0)
        
        best = manager.find_best_agent_for_task("analysis", min_success_rate=0.5)
        
        assert best == "agent-a"
    
    def test_assess_capability(self):
        """测试评估能力"""
        manager = DynamicCapabilityManager()
        
        manager.record_task_result("agent-003", "coding", "task1", "success", 8.0)
        
        result = manager.assess_capability("agent-003", "coding")
        
        assert "level" in result
    
    def test_get_system_statistics(self):
        """测试获取系统统计"""
        manager = DynamicCapabilityManager()
        
        manager.get_or_create_engine("agent-x")
        manager.get_or_create_engine("agent-y")
        
        stats = manager.get_system_statistics()
        
        assert stats["total_agents"] == 2


def test_global_capability_manager():
    """测试全局能力管理器"""
    manager1 = get_capability_manager()
    manager2 = get_capability_manager()
    
    assert manager1 is manager2
