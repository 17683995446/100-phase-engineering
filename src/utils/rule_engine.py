"""
规则引擎
提供规则定义、评估和执行功能
"""
import operator
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class OperatorType(Enum):
    """操作符类型"""
    EQUALS = auto()
    NOT_EQUALS = auto()
    GREATER_THAN = auto()
    LESS_THAN = auto()
    GREATER_EQUAL = auto()
    LESS_EQUAL = auto()
    CONTAINS = auto()
    IN = auto()
    AND = auto()
    OR = auto()


@dataclass
class Condition:
    """条件"""
    field: str
    operator: OperatorType
    value: Any
    
    def evaluate(self, data: Dict[str, Any]) -> bool:
        """评估条件"""
        actual_value = data.get(self.field)
        
        if self.operator == OperatorType.EQUALS:
            return actual_value == self.value
        elif self.operator == OperatorType.NOT_EQUALS:
            return actual_value != self.value
        elif self.operator == OperatorType.GREATER_THAN:
            return actual_value is not None and actual_value > self.value
        elif self.operator == OperatorType.LESS_THAN:
            return actual_value is not None and actual_value < self.value
        elif self.operator == OperatorType.GREATER_EQUAL:
            return actual_value is not None and actual_value >= self.value
        elif self.operator == OperatorType.LESS_EQUAL:
            return actual_value is not None and actual_value <= self.value
        elif self.operator == OperatorType.CONTAINS:
            return actual_value is not None and self.value in str(actual_value)
        elif self.operator == OperatorType.IN:
            return actual_value is not None and actual_value in self.value
        
        return False


@dataclass
class Rule:
    """规则"""
    rule_id: str
    name: str
    conditions: List[Condition]
    action: Callable
    priority: int = 0
    enabled: bool = True
    
    def evaluate(self, data: Dict[str, Any]) -> bool:
        """评估规则"""
        if not self.enabled:
            return False
        
        return all(condition.evaluate(data) for condition in self.conditions)
    
    def execute(self, data: Dict[str, Any]) -> Any:
        """执行规则"""
        if self.evaluate(data):
            return self.action(data)
        return None


class RuleEngine:
    """规则引擎"""
    
    def __init__(self):
        self._rules: Dict[str, Rule] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("rule.engine")
    
    def add_rule(self, rule: Rule) -> None:
        """添加规则"""
        with self._lock:
            self._rules[rule.rule_id] = rule
        self._logger.info(f"Rule added: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除规则"""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                return True
            return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                rule.enabled = True
                return True
            return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                rule.enabled = False
                return True
            return False
    
    def evaluate(self, data: Dict[str, Any]) -> List[Rule]:
        """评估所有规则"""
        with self._lock:
            rules = sorted(self._rules.values(), key=lambda r: r.priority, reverse=True)
            matched = [rule for rule in rules if rule.evaluate(data)]
        return matched
    
    def execute(self, data: Dict[str, Any]) -> List[Any]:
        """执行匹配的规则"""
        results = []
        matched_rules = self.evaluate(data)
        
        for rule in matched_rules:
            try:
                result = rule.execute(data)
                if result is not None:
                    results.append(result)
            except Exception as e:
                self._logger.error(f"Rule execution failed: {e}")
        
        return results
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """获取规则"""
        with self._lock:
            return self._rules.get(rule_id)
    
    def get_all_rules(self) -> List[Rule]:
        """获取所有规则"""
        with self._lock:
            return list(self._rules.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._rules)
            enabled = sum(1 for r in self._rules.values() if r.enabled)
            return {
                "total_rules": total,
                "enabled": enabled,
                "disabled": total - enabled
            }


# 全局实例
_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """获取规则引擎"""
    global _engine
    if _engine is None:
        _engine = RuleEngine()
    return _engine
