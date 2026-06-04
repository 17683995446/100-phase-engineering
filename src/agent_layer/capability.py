"""
Agent能力增强与动态学习系统
职责正交公理扩展：Agent能力可持续学习与进化
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum, auto
from datetime import datetime
import uuid
import json

from src.utils.logger import logger


class LearningMode(Enum):
    """学习模式"""
    SUPERVISED = auto()     # 监督学习
    REINFORCEMENT = auto()  # 强化学习
    IMITATION = auto()      # 模仿学习
    SELF_IMPROVEMENT = auto()  # 自我改进


class SkillLevel(Enum):
    """技能等级"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    MASTER = 6


@dataclass
class SkillRecord:
    """技能记录"""
    skill_id: str
    capability_name: str
    task_type: str
    outcome: str
    feedback: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "capability_name": self.capability_name,
            "task_type": self.task_type,
            "outcome": self.outcome,
            "feedback": self.feedback,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


@dataclass
class CapabilityMetrics:
    """能力指标"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_completion_time: float = 0.0
    avg_quality_score: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
    
    @property
    def failure_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.failed_tasks / self.total_tasks
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_completion_time": self.avg_completion_time,
            "avg_quality_score": self.avg_quality_score,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class LearnedPattern:
    """学到的模式"""
    pattern_id: str
    pattern_type: str
    description: str
    occurrences: int
    success_count: int
    confidence: float
    learned_at: datetime
    last_used: datetime
    code_snippet: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        if self.occurrences == 0:
            return 0.0
        return self.success_count / self.occurrences
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "occurrences": self.occurrences,
            "success_count": self.success_count,
            "confidence": self.confidence,
            "success_rate": self.success_rate,
            "learned_at": self.learned_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "code_snippet": self.code_snippet
        }


class AgentLearningEngine:
    """Agent学习引擎"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.skill_records: List[SkillRecord] = []
        self.learned_patterns: Dict[str, LearnedPattern] = {}
        self.capability_metrics: Dict[str, CapabilityMetrics] = {}
        logger.info(f"Agent学习引擎初始化: {agent_id}")
    
    def record_experience(
        self,
        capability_name: str,
        task_type: str,
        outcome: str,
        feedback: float,
        context: Optional[Dict[str, Any]] = None
    ) -> SkillRecord:
        """记录经验"""
        record = SkillRecord(
            skill_id=str(uuid.uuid4()),
            capability_name=capability_name,
            task_type=task_type,
            outcome=outcome,
            feedback=feedback,
            timestamp=datetime.now(),
            context=context or {}
        )
        
        self.skill_records.append(record)
        
        # 更新能力指标
        self._update_metrics(capability_name, outcome, feedback)
        
        logger.debug(f"记录经验: {capability_name} - {outcome} (feedback={feedback})")
        
        return record
    
    def _update_metrics(self, capability_name: str, outcome: str, feedback: float):
        """更新能力指标"""
        if capability_name not in self.capability_metrics:
            self.capability_metrics[capability_name] = CapabilityMetrics()
        
        metrics = self.capability_metrics[capability_name]
        metrics.total_tasks += 1
        
        if outcome == "success":
            metrics.successful_tasks += 1
        elif outcome == "failure":
            metrics.failed_tasks += 1
        
        # 更新平均质量分数
        old_total = metrics.avg_quality_score * (metrics.total_tasks - 1)
        metrics.avg_quality_score = (old_total + feedback) / metrics.total_tasks
        metrics.last_updated = datetime.now()
    
    def learn_from_pattern(
        self,
        pattern_type: str,
        description: str,
        success: bool,
        code_snippet: Optional[str] = None
    ) -> LearnedPattern:
        """从模式中学习"""
        pattern_key = f"{pattern_type}:{description}"
        
        if pattern_key in self.learned_patterns:
            pattern = self.learned_patterns[pattern_key]
            pattern.occurrences += 1
            if success:
                pattern.success_count += 1
            pattern.confidence = min(1.0, pattern.confidence + 0.05)
            pattern.last_used = datetime.now()
        else:
            pattern = LearnedPattern(
                pattern_id=str(uuid.uuid4()),
                pattern_type=pattern_type,
                description=description,
                occurrences=1,
                success_count=1 if success else 0,
                confidence=0.5,
                learned_at=datetime.now(),
                last_used=datetime.now(),
                code_snippet=code_snippet
            )
            self.learned_patterns[pattern_key] = pattern
        
        logger.info(f"学习新模式: {pattern_type} - {description}")
        
        return pattern
    
    def get_capability_metrics(self, capability_name: str) -> Optional[CapabilityMetrics]:
        """获取能力指标"""
        return self.capability_metrics.get(capability_name)
    
    def get_all_metrics(self) -> Dict[str, CapabilityMetrics]:
        """获取所有能力指标"""
        return self.capability_metrics
    
    def get_successful_patterns(self) -> List[LearnedPattern]:
        """获取成功的模式"""
        return [
            p for p in self.learned_patterns.values()
            if p.success_rate >= 0.7 and p.occurrences >= 3
        ]
    
    def suggest_improvement(self) -> List[str]:
        """建议改进"""
        suggestions = []
        
        for cap_name, metrics in self.capability_metrics.items():
            if metrics.success_rate < 0.7:
                suggestions.append(
                    f"{cap_name} 成功率较低 ({metrics.success_rate:.1%})，需要更多练习"
                )
            
            if metrics.failure_rate > 0.3:
                suggestions.append(
                    f"{cap_name} 失败率较高 ({metrics.failure_rate:.1%})，建议回顾失败案例"
                )
        
        return suggestions
    
    def export_learning_data(self) -> Dict[str, Any]:
        """导出学习数据"""
        return {
            "agent_id": self.agent_id,
            "skill_records_count": len(self.skill_records),
            "patterns_count": len(self.learned_patterns),
            "capability_metrics": {
                name: metrics.to_dict()
                for name, metrics in self.capability_metrics.items()
            },
            "successful_patterns": [
                p.to_dict() for p in self.get_successful_patterns()
            ]
        }


class CapabilityAssessment:
    """能力评估"""
    
    def __init__(self):
        self.assessment_id = str(uuid.uuid4())
        logger.info(f"能力评估初始化: {self.assessment_id}")
    
    def assess_agent_capability(
        self,
        metrics: CapabilityMetrics,
        patterns: List[LearnedPattern]
    ) -> Dict[str, Any]:
        """评估Agent能力"""
        if metrics.total_tasks == 0:
            return {
                "level": SkillLevel.NOVICE,
                "recommendation": "需要更多实践来建立基线"
            }
        
        success_rate = metrics.success_rate
        pattern_confidence = sum(p.confidence for p in patterns) / len(patterns) if patterns else 0
        
        # 综合评分
        composite_score = (success_rate * 0.6 + pattern_confidence * 0.4)
        
        # 确定等级
        if composite_score >= 0.9:
            level = SkillLevel.MASTER
            recommendation = "已达到大师级别，可指导其他Agent"
        elif composite_score >= 0.8:
            level = SkillLevel.EXPERT
            recommendation = "专家级别，可处理复杂任务"
        elif composite_score >= 0.7:
            level = SkillLevel.ADVANCED
            recommendation = "高级水平，可独立完成大部分任务"
        elif composite_score >= 0.5:
            level = SkillLevel.INTERMEDIATE
            recommendation = "中级水平，继续积累经验"
        elif composite_score >= 0.3:
            level = SkillLevel.BEGINNER
            recommendation = "初级水平，需要更多练习"
        else:
            level = SkillLevel.NOVICE
            recommendation = "新手水平，建议从简单任务开始"
        
        return {
            "assessment_id": self.assessment_id,
            "composite_score": composite_score,
            "level": level,
            "success_rate": success_rate,
            "pattern_confidence": pattern_confidence,
            "recommendation": recommendation,
            "assessed_at": datetime.now().isoformat()
        }
    
    def compare_agents(
        self,
        metrics_a: CapabilityMetrics,
        metrics_b: CapabilityMetrics
    ) -> Dict[str, Any]:
        """比较两个Agent的能力"""
        score_a = self._calculate_composite_score(metrics_a)
        score_b = self._calculate_composite_score(metrics_b)
        
        return {
            "agent_a_score": score_a,
            "agent_b_score": score_b,
            "better_agent": "A" if score_a > score_b else "B",
            "score_difference": abs(score_a - score_b)
        }
    
    def _calculate_composite_score(self, metrics: CapabilityMetrics) -> float:
        """计算综合分数"""
        if metrics.total_tasks == 0:
            return 0.0
        
        success_component = metrics.success_rate * 0.7
        quality_component = (metrics.avg_quality_score / 10.0) * 0.3
        
        return success_component + quality_component


class DynamicCapabilityManager:
    """动态能力管理器"""
    
    def __init__(self):
        self.agent_engines: Dict[str, AgentLearningEngine] = {}
        self.assessment = CapabilityAssessment()
        logger.info("动态能力管理器初始化")
    
    def get_or_create_engine(self, agent_id: str) -> AgentLearningEngine:
        """获取或创建学习引擎"""
        if agent_id not in self.agent_engines:
            self.agent_engines[agent_id] = AgentLearningEngine(agent_id)
        return self.agent_engines[agent_id]
    
    def record_task_result(
        self,
        agent_id: str,
        capability_name: str,
        task_type: str,
        outcome: str,
        feedback: float,
        context: Optional[Dict[str, Any]] = None
    ):
        """记录任务结果"""
        engine = self.get_or_create_engine(agent_id)
        engine.record_experience(capability_name, task_type, outcome, feedback, context)
    
    def learn_pattern(
        self,
        agent_id: str,
        pattern_type: str,
        description: str,
        success: bool,
        code_snippet: Optional[str] = None
    ):
        """学习模式"""
        engine = self.get_or_create_engine(agent_id)
        engine.learn_from_pattern(pattern_type, description, success, code_snippet)
    
    def assess_capability(self, agent_id: str, capability_name: str) -> Dict[str, Any]:
        """评估能力"""
        engine = self.agent_engines.get(agent_id)
        
        if not engine:
            return {"error": "Agent未找到"}
        
        metrics = engine.get_capability_metrics(capability_name)
        
        if not metrics:
            return {"error": "没有足够的数据进行评估"}
        
        patterns = engine.get_successful_patterns()
        
        return self.assessment.assess_agent_capability(metrics, patterns)
    
    def get_agent_summary(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent摘要"""
        engine = self.agent_engines.get(agent_id)
        
        if not engine:
            return {"error": "Agent未找到"}
        
        return engine.export_learning_data()
    
    def find_best_agent_for_task(
        self,
        capability_name: str,
        min_success_rate: float = 0.7
    ) -> Optional[str]:
        """为任务找到最佳Agent"""
        best_agent = None
        best_score = 0.0
        
        for agent_id, engine in self.agent_engines.items():
            metrics = engine.get_capability_metrics(capability_name)
            
            if metrics and metrics.success_rate >= min_success_rate:
                score = metrics.success_rate * metrics.avg_quality_score / 10.0
                if score > best_score:
                    best_score = score
                    best_agent = agent_id
        
        return best_agent
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计"""
        total_agents = len(self.agent_engines)
        total_patterns = sum(
            len(e.learned_patterns) for e in self.agent_engines.values()
        )
        total_records = sum(
            len(e.skill_records) for e in self.agent_engines.values()
        )
        
        return {
            "total_agents": total_agents,
            "total_patterns": total_patterns,
            "total_skill_records": total_records,
            "avg_patterns_per_agent": total_patterns / total_agents if total_agents > 0 else 0
        }


_global_capability_manager: Optional[DynamicCapabilityManager] = None


def get_capability_manager() -> DynamicCapabilityManager:
    """获取全局能力管理器"""
    global _global_capability_manager
    if _global_capability_manager is None:
        _global_capability_manager = DynamicCapabilityManager()
    return _global_capability_manager
