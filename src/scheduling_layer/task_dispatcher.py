"""
任务分发与负载均衡系统
成本最小公理：任务分配最优、资源利用最大化
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from src.agent_layer.protocol import MessagePriority
from src.config.constants import TaskType
from src.utils.logger import logger


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = auto()
    LEAST_LOADED = auto()
    CAPABILITY_BASED = auto()
    AFFINITY = auto()
    RANDOM = auto()


@dataclass
class AgentLoad:
    """Agent负载信息"""
    agent_id: str
    role: str
    current_tasks: int = 0
    max_capacity: int = 5
    load_percentage: float = 0.0
    avg_completion_time_ms: float = 0.0
    success_rate: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)

    def is_available(self) -> bool:
        """检查Agent是否可用"""
        return self.current_tasks < self.max_capacity

    def get_load_score(self) -> float:
        """计算负载分数（越低越好）"""
        if self.max_capacity == 0:
            return float('inf')

        base_load = self.current_tasks / self.max_capacity

        time_factor = self.avg_completion_time_ms / 1000.0 if self.avg_completion_time_ms > 0 else 0

        return base_load * 0.7 + min(time_factor / 10, 1.0) * 0.3


@dataclass
class TaskDistribution:
    """任务分发记录"""
    task_id: str
    assigned_agent: str
    assigned_at: datetime
    strategy: str
    reason: str


@dataclass
class TaskItem:
    """任务项"""
    task_id: str
    task_type: TaskType
    priority: MessagePriority
    required_capabilities: list[str] = field(default_factory=list)
    preferred_agent: str | None = None
    affinity_agents: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    deadline: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value if hasattr(self.task_type, 'value') else str(self.task_type),
            "priority": self.priority.name,
            "required_capabilities": self.required_capabilities,
            "preferred_agent": self.preferred_agent,
            "affinity_agents": self.affinity_agents,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "metadata": self.metadata
        }


@dataclass
class TaskAssignment:
    """任务分配"""
    assignment_id: str
    task: TaskItem
    assigned_agent: str
    assigned_at: datetime
    status: str = "assigned"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def start(self):
        """开始任务"""
        self.status = "running"
        self.started_at = datetime.now()

    def complete(self, result: dict[str, Any]):
        """完成任务"""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.result = result

    def fail(self, error: str):
        """任务失败"""
        self.status = "failed"
        self.completed_at = datetime.now()
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "task": self.task.to_dict(),
            "assigned_agent": self.assigned_agent,
            "assigned_at": self.assigned_at.isoformat(),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error
        }


class TaskQueue:
    """任务队列"""

    def __init__(self, name: str = "default"):
        self.name = name
        self.pending_tasks: list[TaskItem] = []
        self.running_tasks: dict[str, TaskAssignment] = {}
        self.completed_tasks: dict[str, TaskAssignment] = {}
        self.failed_tasks: dict[str, TaskAssignment] = {}
        logger.info(f"初始化任务队列: {name}")

    def enqueue(self, task: TaskItem) -> bool:
        """入队任务"""
        self.pending_tasks.append(task)
        logger.debug(f"任务入队: {task.task_id} (队列={self.name})")
        return True

    def dequeue(self) -> TaskItem | None:
        """出队任务"""
        if not self.pending_tasks:
            return None

        self.pending_tasks.sort(key=lambda t: (t.priority.value, t.created_at))

        task = self.pending_tasks.pop(0)
        logger.debug(f"任务出队: {task.task_id}")
        return task

    def get_pending_count(self) -> int:
        """获取待处理任务数"""
        return len(self.pending_tasks)

    def get_running_count(self) -> int:
        """获取运行中任务数"""
        return len(self.running_tasks)

    def add_assignment(self, assignment: TaskAssignment):
        """添加分配"""
        self.running_tasks[assignment.task.task_id] = assignment

    def complete_assignment(self, task_id: str, result: dict[str, Any]):
        """完成分配"""
        if task_id in self.running_tasks:
            assignment = self.running_tasks.pop(task_id)
            assignment.complete(result)
            self.completed_tasks[task_id] = assignment

    def fail_assignment(self, task_id: str, error: str):
        """失败分配"""
        if task_id in self.running_tasks:
            assignment = self.running_tasks.pop(task_id)
            assignment.fail(error)
            self.failed_tasks[task_id] = assignment

    def get_statistics(self) -> dict[str, Any]:
        """获取队列统计"""
        return {
            "queue_name": self.name,
            "pending": self.get_pending_count(),
            "running": self.get_running_count(),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks)
        }


class LoadBalancer:
    """负载均衡器"""

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED):
        self.strategy = strategy
        self.agent_loads: dict[str, AgentLoad] = {}
        self.round_robin_index: dict[str, int] = {}
        logger.info(f"初始化负载均衡器: {strategy.name}")

    def update_agent_load(self, agent_id: str, role: str, current_tasks: int, max_capacity: int = 5):
        """更新Agent负载"""
        load = AgentLoad(
            agent_id=agent_id,
            role=role,
            current_tasks=current_tasks,
            max_capacity=max_capacity,
            load_percentage=current_tasks / max_capacity if max_capacity > 0 else 1.0
        )

        self.agent_loads[agent_id] = load

        if agent_id not in self.round_robin_index:
            self.round_robin_index[agent_id] = 0

        logger.debug(f"更新Agent负载: {agent_id} (tasks={current_tasks}/{max_capacity})")

    def increment_task(self, agent_id: str):
        """增加任务计数"""
        if agent_id in self.agent_loads:
            self.agent_loads[agent_id].current_tasks += 1
            self.agent_loads[agent_id].last_updated = datetime.now()

    def decrement_task(self, agent_id: str, success: bool = True, completion_time_ms: float = 0):
        """减少任务计数"""
        if agent_id in self.agent_loads:
            load = self.agent_loads[agent_id]
            if load.current_tasks > 0:
                load.current_tasks -= 1

            load.last_updated = datetime.now()

            if completion_time_ms > 0:
                if load.avg_completion_time_ms == 0:
                    load.avg_completion_time_ms = completion_time_ms
                else:
                    load.avg_completion_time_ms = (load.avg_completion_time_ms + completion_time_ms) / 2

            if not success:
                load.success_rate = max(0.0, load.success_rate - 0.01)

    def get_available_agents(self, role: str | None = None) -> list[AgentLoad]:
        """获取可用的Agent"""
        available = []

        for load in self.agent_loads.values():
            if not load.is_available():
                continue

            if role and load.role != role:
                continue

            available.append(load)

        return available

    def select_agent(self, task: TaskItem) -> str | None:
        """选择最佳Agent"""
        if task.preferred_agent and task.preferred_agent in self.agent_loads:
            preferred_load = self.agent_loads[task.preferred_agent]
            if preferred_load.is_available():
                return task.preferred_agent

        if task.affinity_agents:
            for agent_id in task.affinity_agents:
                if agent_id in self.agent_loads:
                    load = self.agent_loads[agent_id]
                    if load.is_available():
                        return agent_id

        available = self.get_available_agents()

        if not available:
            logger.warning("没有可用的Agent")
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(available, task)

        elif self.strategy == LoadBalancingStrategy.LEAST_LOADED:
            return self._least_loaded_select(available)

        elif self.strategy == LoadBalancingStrategy.CAPABILITY_BASED:
            return self._capability_based_select(available, task)

        elif self.strategy == LoadBalancingStrategy.RANDOM:
            import random
            return random.choice(available).agent_id

        return available[0].agent_id if available else None

    def _round_robin_select(self, available: list[AgentLoad], task: TaskItem) -> str:
        """轮询选择"""
        if not available:
            return None

        for load in available:
            idx = self.round_robin_index.get(load.agent_id, 0)
            if idx < len(available):
                selected = available[idx]
                self.round_robin_index[load.agent_id] = (idx + 1) % len(available)
                return selected.agent_id

        return available[0].agent_id

    def _least_loaded_select(self, available: list[AgentLoad]) -> str:
        """最小负载选择"""
        if not available:
            return None

        return min(available, key=lambda x: x.get_load_score()).agent_id

    def _capability_based_select(self, available: list[AgentLoad], task: TaskItem) -> str:
        """能力匹配选择"""
        if not task.required_capabilities:
            return self._least_loaded_select(available)

        role_mapping = {
            "requirement_analysis": "analyzer",
            "architecture_design": "architect",
            "code_generation": "developer",
            "code_review": "reviewer",
            "testing": "tester",
            "documentation": "documenter",
            "debugging": "debugger"
        }

        preferred_role = None
        for cap in task.required_capabilities:
            if cap in role_mapping:
                preferred_role = role_mapping[cap]
                break

        if preferred_role:
            role_matches = [agent for agent in available if agent.role == preferred_role]
            if role_matches:
                return min(role_matches, key=lambda x: x.get_load_score()).agent_id

        return self._least_loaded_select(available)

    def get_statistics(self) -> dict[str, Any]:
        """获取负载统计"""
        total_agents = len(self.agent_loads)
        available_agents = len(self.get_available_agents())

        avg_load = 0.0
        if self.agent_loads:
            avg_load = sum(agent.load_percentage for agent in self.agent_loads.values()) / total_agents

        return {
            "strategy": self.strategy.name,
            "total_agents": total_agents,
            "available_agents": available_agents,
            "average_load": avg_load
        }


class TaskDispatcher:
    """任务分发器"""

    def __init__(self, load_balancer: LoadBalancer | None = None):
        self.load_balancer = load_balancer or LoadBalancer()
        self.queues: dict[str, TaskQueue] = {}
        self.assignments: dict[str, TaskAssignment] = {}
        self.distribution_history: list[TaskDistribution] = []
        logger.info("初始化任务分发器")

    def create_queue(self, name: str) -> TaskQueue:
        """创建队列"""
        queue = TaskQueue(name)
        self.queues[name] = queue
        return queue

    def get_queue(self, name: str = "default") -> TaskQueue | None:
        """获取队列"""
        return self.queues.get(name)

    def register_agent(self, agent_id: str, role: str, max_capacity: int = 5):
        """注册Agent"""
        self.load_balancer.update_agent_load(agent_id, role, 0, max_capacity)
        logger.info(f"注册Agent到分发器: {agent_id} (role={role}, capacity={max_capacity})")

    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self.load_balancer.agent_loads:
            del self.load_balancer.agent_loads[agent_id]
            logger.info(f"注销Agent: {agent_id}")

    def dispatch_task(
        self,
        task: TaskItem,
        queue_name: str = "default"
    ) -> TaskAssignment | None:
        """分发任务"""
        if queue_name not in self.queues:
            self.create_queue(queue_name)

        queue = self.queues[queue_name]

        selected_agent = self.load_balancer.select_agent(task)

        if not selected_agent:
            queue.enqueue(task)
            logger.warning(f"没有可用Agent，任务入队: {task.task_id}")
            return None

        assignment = TaskAssignment(
            assignment_id=str(uuid.uuid4()),
            task=task,
            assigned_agent=selected_agent,
            assigned_at=datetime.now()
        )

        self.assignments[assignment.assignment_id] = assignment
        queue.add_assignment(assignment)
        self.load_balancer.increment_task(selected_agent)

        distribution = TaskDistribution(
            task_id=task.task_id,
            assigned_agent=selected_agent,
            assigned_at=datetime.now(),
            strategy=self.load_balancer.strategy.name,
            reason=f"Selected by {self.load_balancer.strategy.name} strategy"
        )
        self.distribution_history.append(distribution)

        logger.info(f"任务分发: {task.task_id} -> {selected_agent}")

        return assignment

    def dispatch_from_queue(self, queue_name: str = "default") -> TaskAssignment | None:
        """从队列分发任务"""
        if queue_name not in self.queues:
            return None

        queue = self.queues[queue_name]
        task = queue.dequeue()

        if not task:
            return None

        return self.dispatch_task(task, queue_name)

    def complete_assignment(self, assignment_id: str, result: dict[str, Any]):
        """完成任务"""
        if assignment_id not in self.assignments:
            return

        assignment = self.assignments[assignment_id]
        task_id = assignment.task.task_id

        self.load_balancer.decrement_task(
            assignment.assigned_agent,
            success=True,
            completion_time_ms=(datetime.now() - assignment.assigned_at).total_seconds() * 1000
        )

        for queue in self.queues.values():
            if task_id in queue.running_tasks:
                queue.complete_assignment(task_id, result)
                break

        logger.info(f"任务完成: {assignment_id}")

    def fail_assignment(self, assignment_id: str, error: str):
        """任务失败"""
        if assignment_id not in self.assignments:
            return

        assignment = self.assignments[assignment_id]
        task_id = assignment.task.task_id

        self.load_balancer.decrement_task(assignment.assigned_agent, success=False)

        for queue in self.queues.values():
            if task_id in queue.running_tasks:
                queue.fail_assignment(task_id, error)
                break

        logger.error(f"任务失败: {assignment_id} - {error}")

    def get_pending_assignments(self) -> list[TaskAssignment]:
        """获取待处理分配"""
        return [a for a in self.assignments.values() if a.status == "assigned"]

    def get_running_assignments(self) -> list[TaskAssignment]:
        """获取运行中分配"""
        return [a for a in self.assignments.values() if a.status == "running"]

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total_assignments = len(self.assignments)
        completed = len([a for a in self.assignments.values() if a.status == "completed"])
        failed = len([a for a in self.assignments.values() if a.status == "failed"])
        running = len([a for a in self.assignments.values() if a.status == "running"])

        queue_stats = [q.get_statistics() for q in self.queues.values()]

        return {
            "total_assignments": total_assignments,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": total_assignments - completed - failed - running,
            "queues": queue_stats,
            "load_balancer": self.load_balancer.get_statistics(),
            "distribution_history_size": len(self.distribution_history)
        }


_global_dispatcher: TaskDispatcher | None = None


def get_task_dispatcher() -> TaskDispatcher:
    """获取全局任务分发器"""
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = TaskDispatcher()
    return _global_dispatcher


def create_task_item(
    task_type: str,
    priority: MessagePriority = MessagePriority.NORMAL,
    required_capabilities: list[str] | None = None,
    metadata: dict[str, Any] | None = None
) -> TaskItem:
    """创建任务项"""
    return TaskItem(
        task_id=str(uuid.uuid4()),
        task_type=task_type,
        priority=priority,
        required_capabilities=required_capabilities or [],
        metadata=metadata or {}
    )
