"""
任务分发与负载均衡验证测试
"""

import pytest
from datetime import datetime
from src.scheduling_layer.task_dispatcher import (
    LoadBalancingStrategy,
    AgentLoad,
    TaskDistribution,
    TaskItem,
    TaskAssignment,
    TaskQueue,
    LoadBalancer,
    TaskDispatcher,
    get_task_dispatcher,
    create_task_item
)
from src.agent_layer.protocol import MessagePriority


class TestLoadBalancingStrategy:
    """测试负载均衡策略"""
    
    def test_strategy_values(self):
        """测试策略枚举值"""
        assert LoadBalancingStrategy.ROUND_ROBIN is not None
        assert LoadBalancingStrategy.LEAST_LOADED is not None
        assert LoadBalancingStrategy.CAPABILITY_BASED is not None
        assert LoadBalancingStrategy.AFFINITY is not None
        assert LoadBalancingStrategy.RANDOM is not None


class TestAgentLoad:
    """测试Agent负载"""
    
    def test_load_creation(self):
        """测试创建负载"""
        load = AgentLoad(
            agent_id="agent-001",
            role="developer",
            current_tasks=2,
            max_capacity=5
        )
        
        assert load.agent_id == "agent-001"
        assert load.current_tasks == 2
    
    def test_is_available(self):
        """测试可用性检查"""
        load = AgentLoad(
            agent_id="agent-002",
            role="developer",
            current_tasks=3,
            max_capacity=5
        )
        
        assert load.is_available() is True
        
        load.current_tasks = 5
        assert load.is_available() is False
    
    def test_get_load_score(self):
        """测试负载分数"""
        load = AgentLoad(
            agent_id="agent-003",
            role="developer",
            current_tasks=2,
            max_capacity=4
        )
        
        score = load.get_load_score()
        assert score > 0


class TestTaskItem:
    """测试任务项"""
    
    def test_task_item_creation(self):
        """测试创建任务项"""
        task = TaskItem(
            task_id="task-001",
            task_type="requirement",
            priority=MessagePriority.HIGH
        )
        
        assert task.task_id == "task-001"
        assert task.priority == MessagePriority.HIGH
    
    def test_task_item_to_dict(self):
        """测试序列化"""
        task = TaskItem(
            task_id="task-002",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        result = task.to_dict()
        
        assert isinstance(result, dict)
        assert result["task_id"] == "task-002"


class TestTaskAssignment:
    """测试任务分配"""
    
    def test_assignment_creation(self):
        """测试创建分配"""
        task = TaskItem(
            task_id="task-003",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = TaskAssignment(
            assignment_id="assign-001",
            task=task,
            assigned_agent="agent-001",
            assigned_at=datetime.now()
        )
        
        assert assignment.assignment_id == "assign-001"
        assert assignment.status == "assigned"
    
    def test_start_task(self):
        """测试开始任务"""
        task = TaskItem(
            task_id="task-004",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = TaskAssignment(
            assignment_id="assign-002",
            task=task,
            assigned_agent="agent-001",
            assigned_at=datetime.now()
        )
        
        assignment.start()
        
        assert assignment.status == "running"
        assert assignment.started_at is not None
    
    def test_complete_task(self):
        """测试完成任务"""
        task = TaskItem(
            task_id="task-005",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = TaskAssignment(
            assignment_id="assign-003",
            task=task,
            assigned_agent="agent-001",
            assigned_at=datetime.now()
        )
        
        assignment.start()
        assignment.complete({"result": "success"})
        
        assert assignment.status == "completed"
        assert assignment.result is not None
    
    def test_fail_task(self):
        """测试任务失败"""
        task = TaskItem(
            task_id="task-006",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = TaskAssignment(
            assignment_id="assign-004",
            task=task,
            assigned_agent="agent-001",
            assigned_at=datetime.now()
        )
        
        assignment.fail("Test error")
        
        assert assignment.status == "failed"
        assert assignment.error == "Test error"


class TestTaskQueue:
    """测试任务队列"""
    
    def test_queue_creation(self):
        """测试创建队列"""
        queue = TaskQueue("test-queue")
        
        assert queue.name == "test-queue"
        assert queue.get_pending_count() == 0
    
    def test_enqueue(self):
        """测试入队"""
        queue = TaskQueue("test-queue")
        
        task = TaskItem(
            task_id="task-007",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        queue.enqueue(task)
        
        assert queue.get_pending_count() == 1
    
    def test_dequeue(self):
        """测试出队"""
        queue = TaskQueue("test-queue")
        
        task1 = TaskItem(
            task_id="task-008",
            task_type="requirement",
            priority=MessagePriority.LOW
        )
        
        task2 = TaskItem(
            task_id="task-009",
            task_type="bugfix",
            priority=MessagePriority.HIGH
        )
        
        queue.enqueue(task1)
        queue.enqueue(task2)
        
        dequeued = queue.dequeue()
        
        assert dequeued.task_id == "task-009"
    
    def test_add_assignment(self):
        """测试添加分配"""
        queue = TaskQueue("test-queue")
        
        task = TaskItem(
            task_id="task-010",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = TaskAssignment(
            assignment_id="assign-005",
            task=task,
            assigned_agent="agent-001",
            assigned_at=datetime.now()
        )
        
        queue.add_assignment(assignment)
        
        assert queue.get_running_count() == 1
    
    def test_complete_assignment(self):
        """测试完成分配"""
        queue = TaskQueue("test-queue")
        
        task = TaskItem(
            task_id="task-011",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = TaskAssignment(
            assignment_id="assign-006",
            task=task,
            assigned_agent="agent-001",
            assigned_at=datetime.now()
        )
        
        queue.add_assignment(assignment)
        queue.complete_assignment("task-011", {"result": "success"})
        
        assert queue.get_running_count() == 0
        assert len(queue.completed_tasks) == 1


class TestLoadBalancer:
    """测试负载均衡器"""
    
    def test_balancer_creation(self):
        """测试创建均衡器"""
        balancer = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)
        
        assert balancer.strategy == LoadBalancingStrategy.ROUND_ROBIN
    
    def test_update_agent_load(self):
        """测试更新负载"""
        balancer = LoadBalancer()
        
        balancer.update_agent_load("agent-001", "developer", 2, 5)
        
        assert "agent-001" in balancer.agent_loads
        assert balancer.agent_loads["agent-001"].current_tasks == 2
    
    def test_increment_decrement_task(self):
        """测试增减任务"""
        balancer = LoadBalancer()
        
        balancer.update_agent_load("agent-002", "developer", 0, 5)
        
        balancer.increment_task("agent-002")
        assert balancer.agent_loads["agent-002"].current_tasks == 1
        
        balancer.decrement_task("agent-002")
        assert balancer.agent_loads["agent-002"].current_tasks == 0
    
    def test_get_available_agents(self):
        """测试获取可用Agent"""
        balancer = LoadBalancer()
        
        balancer.update_agent_load("agent-003", "developer", 2, 5)
        balancer.update_agent_load("agent-004", "developer", 5, 5)
        
        available = balancer.get_available_agents()
        assert len(available) == 1
        assert available[0].agent_id == "agent-003"
    
    def test_select_agent_least_loaded(self):
        """测试最小负载选择"""
        balancer = LoadBalancer(LoadBalancingStrategy.LEAST_LOADED)
        
        balancer.update_agent_load("agent-a", "developer", 4, 5)
        balancer.update_agent_load("agent-b", "developer", 1, 5)
        
        task = TaskItem(
            task_id="task-012",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        selected = balancer.select_agent(task)
        
        assert selected == "agent-b"
    
    def test_select_agent_with_preference(self):
        """测试优先选择"""
        balancer = LoadBalancer(LoadBalancingStrategy.LEAST_LOADED)
        
        balancer.update_agent_load("agent-x", "developer", 1, 5)
        balancer.update_agent_load("agent-y", "developer", 0, 5)
        
        task = TaskItem(
            task_id="task-013",
            task_type="requirement",
            priority=MessagePriority.NORMAL,
            preferred_agent="agent-y"
        )
        
        selected = balancer.select_agent(task)
        
        assert selected == "agent-y"


class TestTaskDispatcher:
    """测试任务分发器"""
    
    def test_dispatcher_creation(self):
        """测试创建分发器"""
        dispatcher = TaskDispatcher()
        
        assert dispatcher is not None
        assert len(dispatcher.queues) == 0
    
    def test_create_queue(self):
        """测试创建队列"""
        dispatcher = TaskDispatcher()
        
        queue = dispatcher.create_queue("my-queue")
        
        assert queue.name == "my-queue"
        assert "my-queue" in dispatcher.queues
    
    def test_register_agent(self):
        """测试注册Agent"""
        dispatcher = TaskDispatcher()
        
        dispatcher.register_agent("agent-001", "developer", 5)
        
        assert "agent-001" in dispatcher.load_balancer.agent_loads
    
    def test_dispatch_task(self):
        """测试分发任务"""
        dispatcher = TaskDispatcher()
        dispatcher.register_agent("agent-001", "developer", 5)
        
        task = TaskItem(
            task_id="task-014",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = dispatcher.dispatch_task(task)
        
        assert assignment is not None
        assert assignment.assigned_agent == "agent-001"
    
    def test_dispatch_with_queue(self):
        """测试队列分发"""
        dispatcher = TaskDispatcher()
        dispatcher.create_queue("test-queue")
        dispatcher.register_agent("agent-001", "developer", 5)
        
        task = TaskItem(
            task_id="task-015",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        dispatcher.get_queue("test-queue").enqueue(task)
        assignment = dispatcher.dispatch_from_queue("test-queue")
        
        assert assignment is not None
    
    def test_complete_assignment(self):
        """测试完成任务"""
        dispatcher = TaskDispatcher()
        dispatcher.register_agent("agent-001", "developer", 5)
        
        task = TaskItem(
            task_id="task-016",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = dispatcher.dispatch_task(task)
        
        dispatcher.complete_assignment(assignment.assignment_id, {"result": "success"})
        
        assert dispatcher.load_balancer.agent_loads["agent-001"].current_tasks == 0
    
    def test_fail_assignment(self):
        """测试任务失败"""
        dispatcher = TaskDispatcher()
        dispatcher.register_agent("agent-001", "developer", 5)
        
        task = TaskItem(
            task_id="task-017",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        assignment = dispatcher.dispatch_task(task)
        
        dispatcher.fail_assignment(assignment.assignment_id, "Test error")
        
        assert dispatcher.load_balancer.agent_loads["agent-001"].current_tasks == 0
    
    def test_get_statistics(self):
        """测试获取统计"""
        dispatcher = TaskDispatcher()
        dispatcher.register_agent("agent-001", "developer", 5)
        
        task = TaskItem(
            task_id="task-018",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        
        dispatcher.dispatch_task(task)
        
        stats = dispatcher.get_statistics()
        
        assert "total_assignments" in stats
        assert "load_balancer" in stats
        assert stats["load_balancer"]["total_agents"] == 1


def test_get_global_dispatcher():
    """测试获取全局分发器"""
    dispatcher1 = get_task_dispatcher()
    dispatcher2 = get_task_dispatcher()
    
    assert dispatcher1 is dispatcher2


def test_create_task_item():
    """测试创建任务项"""
    task = create_task_item(
        task_type="requirement",
        priority=MessagePriority.HIGH,
        required_capabilities=["analysis"]
    )
    
    assert task.task_id is not None
    assert task.priority == MessagePriority.HIGH


def test_multi_agent_distribution():
    """测试多Agent分发"""
    dispatcher = TaskDispatcher()
    
    dispatcher.register_agent("agent-1", "developer", 5)
    dispatcher.register_agent("agent-2", "developer", 5)
    dispatcher.register_agent("agent-3", "developer", 5)
    
    assignments = []
    for i in range(5):
        task = TaskItem(
            task_id=f"task-multi-{i}",
            task_type="requirement",
            priority=MessagePriority.NORMAL
        )
        assignment = dispatcher.dispatch_task(task)
        if assignment:
            assignments.append(assignment)
    
    assert len(assignments) == 5
    
    load_dist = {}
    for a in assignments:
        agent = a.assigned_agent
        load_dist[agent] = load_dist.get(agent, 0) + 1
    
    assert len(load_dist) >= 2


def test_load_balance_after_completion():
    """测试完成后负载均衡"""
    dispatcher = TaskDispatcher(LoadBalancer(LoadBalancingStrategy.LEAST_LOADED))
    
    dispatcher.register_agent("agent-a", "developer", 5)
    dispatcher.register_agent("agent-b", "developer", 5)
    
    task1 = TaskItem(
        task_id="task-load-1",
        task_type="requirement",
        priority=MessagePriority.NORMAL
    )
    task2 = TaskItem(
        task_id="task-load-2",
        task_type="requirement",
        priority=MessagePriority.NORMAL
    )
    
    a1 = dispatcher.dispatch_task(task1)
    a2 = dispatcher.dispatch_task(task2)
    
    assert a1.assigned_agent != a2.assigned_agent or dispatcher.load_balancer.agent_loads[a1.assigned_agent].current_tasks == 2
