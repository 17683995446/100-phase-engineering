"""
阶段依赖图与路线图
提供阶段定义、依赖关系管理和路线图生成功能
"""
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from src.utils.structured_logging import get_logger


class PhaseStatus(Enum):
    """阶段状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Phase:
    """阶段定义"""
    phase_id: str
    name: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    status: PhaseStatus = PhaseStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    deliverables: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "name": self.name,
            "description": self.description,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "duration": round(self.duration, 3),
            "deliverables": self.deliverables,
            "tags": self.tags
        }


class RoadmapManager:
    """路线图管理器"""

    def __init__(self):
        self._phases: Dict[str, Phase] = {}
        self._lock = object()
        self._logger = get_logger("roadmap.manager")

    def add_phase(self, phase_id: str, name: str, description: str,
                  depends_on: Optional[List[str]] = None,
                  deliverables: Optional[List[str]] = None,
                  tags: Optional[List[str]] = None) -> Phase:
        """添加阶段"""
        if phase_id in self._phases:
            raise ValueError(f"Phase already exists: {phase_id}")

        phase = Phase(
            phase_id=phase_id,
            name=name,
            description=description,
            depends_on=depends_on or [],
            deliverables=deliverables or [],
            tags=tags or []
        )
        self._phases[phase_id] = phase
        self._logger.info(f"Phase added: {phase_id} - {name}")
        return phase

    def get_phase(self, phase_id: str) -> Optional[Phase]:
        """获取阶段"""
        return self._phases.get(phase_id)

    def start_phase(self, phase_id: str) -> bool:
        """开始阶段"""
        phase = self._phases.get(phase_id)
        if not phase:
            return False

        # 检查依赖
        for dep_id in phase.depends_on:
            dep = self._phases.get(dep_id)
            if not dep or dep.status != PhaseStatus.COMPLETED:
                phase.status = PhaseStatus.BLOCKED
                self._logger.warning(f"Phase blocked: {phase_id} depends on {dep_id}")
                return False

        phase.status = PhaseStatus.IN_PROGRESS
        phase.start_time = time.time()
        self._logger.info(f"Phase started: {phase_id}")
        return True

    def complete_phase(self, phase_id: str) -> bool:
        """完成阶段"""
        phase = self._phases.get(phase_id)
        if not phase or phase.status != PhaseStatus.IN_PROGRESS:
            return False

        phase.status = PhaseStatus.COMPLETED
        phase.end_time = time.time()
        self._logger.info(f"Phase completed: {phase_id} duration={phase.duration:.3f}s")
        return True

    def get_execution_order(self) -> List[str]:
        """获取执行顺序（拓扑排序）"""
        visited: Set[str] = set()
        temp: Set[str] = set()
        order: List[str] = []

        def visit(phase_id: str) -> None:
            if phase_id in temp:
                raise ValueError(f"Circular dependency detected: {phase_id}")
            if phase_id in visited:
                return
            temp.add(phase_id)
            phase = self._phases.get(phase_id)
            if phase:
                for dep in phase.depends_on:
                    visit(dep)
            temp.remove(phase_id)
            visited.add(phase_id)
            order.append(phase_id)

        for pid in self._phases:
            if pid not in visited:
                visit(pid)

        return order

    def get_critical_path(self) -> List[str]:
        """获取关键路径（最长依赖链）"""
        def depth(phase_id: str, memo: Dict[str, int]) -> int:
            if phase_id in memo:
                return memo[phase_id]
            phase = self._phases.get(phase_id)
            if not phase or not phase.depends_on:
                memo[phase_id] = 1
                return 1
            max_dep = max(depth(d, memo) for d in phase.depends_on)
            memo[phase_id] = max_dep + 1
            return memo[phase_id]

        memo: Dict[str, int] = {}
        depths = {pid: depth(pid, memo) for pid in self._phases}
        if not depths:
            return []

        # 找到最深的路径
        max_depth = max(depths.values())
        critical = [pid for pid, d in depths.items() if d == max_depth]
        return critical

    def get_ready_phases(self) -> List[Phase]:
        """获取可执行的阶段"""
        ready = []
        for phase in self._phases.values():
            if phase.status == PhaseStatus.PENDING:
                deps_satisfied = all(
                    self._phases.get(d) and self._phases[d].status == PhaseStatus.COMPLETED
                    for d in phase.depends_on
                )
                if deps_satisfied:
                    ready.append(phase)
        return ready

    def list_phases(self, status: Optional[str] = None,
                    tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出阶段"""
        phases = self._phases.values()
        if status:
            phases = [p for p in phases if p.status.value == status]
        if tag:
            phases = [p for p in phases if tag in p.tags]
        return [p.to_dict() for p in phases]

    def generate_mermaid(self) -> str:
        """生成 Mermaid 流程图"""
        lines = ["graph TD"]
        for phase in self._phases.values():
            node_id = phase.phase_id.replace("-", "_")
            status_color = {
                PhaseStatus.PENDING: "#fff",
                PhaseStatus.IN_PROGRESS: "#ffeb3b",
                PhaseStatus.COMPLETED: "#4caf50",
                PhaseStatus.BLOCKED: "#f44336"
            }.get(phase.status, "#fff")
            lines.append(f'    {node_id}["{phase.name}"]')
            for dep in phase.depends_on:
                dep_id = dep.replace("-", "_")
                lines.append(f"    {dep_id} --> {node_id}")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self._phases)
        completed = sum(1 for p in self._phases.values() if p.status == PhaseStatus.COMPLETED)
        in_progress = sum(1 for p in self._phases.values() if p.status == PhaseStatus.IN_PROGRESS)
        pending = sum(1 for p in self._phases.values() if p.status == PhaseStatus.PENDING)
        blocked = sum(1 for p in self._phases.values() if p.status == PhaseStatus.BLOCKED)
        return {
            "total_phases": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "blocked": blocked,
            "completion_rate": round(completed / total * 100, 2) if total else 0.0
        }


# 全局实例
_manager: Optional[RoadmapManager] = None


def get_roadmap_manager() -> RoadmapManager:
    """获取全局路线图管理器"""
    global _manager
    if _manager is None:
        _manager = RoadmapManager()
    return _manager
