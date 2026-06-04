"""
链路ID机制验证测试
"""

import pytest
import time
from datetime import datetime
from src.scheduling_layer.chain_id import (
    ChainID, SpanID, Span, Chain, ChainTracker,
    SpanType, SpanStatus, ChainContext, get_chain_tracker
)


class TestChainID:
    """测试链路ID"""
    
    def test_generate_chain_id(self):
        """测试生成链路ID"""
        task_id = "test-task-001"
        chain_id = ChainID.generate(task_id)
        
        assert chain_id is not None
        assert chain_id.task_id == task_id
        assert chain_id.chain_id.startswith("CH-")
        assert task_id in chain_id.chain_id
        assert len(chain_id.chain_id) > len(task_id)
        assert chain_id.version == 1
    
    def test_chain_id_uniqueness(self):
        """测试链路ID唯一性"""
        task_id = "test-task-002"
        chain_id_1 = ChainID.generate(task_id)
        chain_id_2 = ChainID.generate(task_id)
        
        assert chain_id_1.chain_id != chain_id_2.chain_id
    
    def test_chain_id_to_dict(self):
        """测试链路ID转字典"""
        task_id = "test-task-003"
        chain_id = ChainID.generate(task_id)
        
        result = chain_id.to_dict()
        
        assert isinstance(result, dict)
        assert result["chain_id"] == chain_id.chain_id
        assert result["task_id"] == task_id
        assert "created_at" in result


class TestSpanID:
    """测试Span ID"""
    
    def test_generate_span_id(self):
        """测试生成Span ID"""
        chain_id = "CH-test-123"
        span_id = SpanID.generate(chain_id, SpanType.TASK)
        
        assert span_id is not None
        assert span_id.chain_id == chain_id
        assert span_id.span_id.startswith("SP-")
        assert span_id.parent_span_id is None
        assert span_id.span_type == SpanType.TASK
    
    def test_span_id_with_parent(self):
        """测试带父Span的Span ID"""
        chain_id = "CH-test-456"
        parent_span_id = "SP-123456789"
        span_id = SpanID.generate(chain_id, SpanType.AGENT, parent_span_id)
        
        assert span_id.parent_span_id == parent_span_id


class TestSpan:
    """测试Span"""
    
    def test_span_creation(self):
        """测试Span创建"""
        span = Span(
            span_id="SP-test-001",
            chain_id="CH-test-123",
            span_type=SpanType.TASK,
            operation_name="process_task",
            start_time=datetime.now(),
            layer="scheduling_layer"
        )
        
        assert span.span_id == "SP-test-001"
        assert span.status == SpanStatus.STARTED
        assert span.end_time is None
    
    def test_span_complete(self):
        """测试Span完成"""
        span = Span(
            span_id="SP-test-002",
            chain_id="CH-test-123",
            span_type=SpanType.EXECUTION,
            operation_name="execute_code",
            start_time=datetime.now()
        )
        
        span.complete(SpanStatus.COMPLETED)
        
        assert span.status == SpanStatus.COMPLETED
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms >= 0
    
    def test_span_fail(self):
        """测试Span失败"""
        span = Span(
            span_id="SP-test-003",
            chain_id="CH-test-123",
            span_type=SpanType.VALIDATION,
            operation_name="validate_code",
            start_time=datetime.now()
        )
        
        error_msg = "Validation failed: syntax error"
        span.fail(error_msg)
        
        assert span.status == SpanStatus.FAILED
        assert span.error == error_msg
        assert span.tags.get("error") == "true"
    
    def test_span_add_tag(self):
        """测试Span添加标签"""
        span = Span(
            span_id="SP-test-004",
            chain_id="CH-test-123",
            span_type=SpanType.MESSAGE,
            operation_name="send_message",
            start_time=datetime.now()
        )
        
        span.add_tag("receiver", "agent-001")
        span.add_tag("priority", "high")
        
        assert span.tags["receiver"] == "agent-001"
        assert span.tags["priority"] == "high"
    
    def test_span_add_log(self):
        """测试Span添加日志"""
        span = Span(
            span_id="SP-test-005",
            chain_id="CH-test-123",
            span_type=SpanType.STATE_CHANGE,
            operation_name="update_state",
            start_time=datetime.now()
        )
        
        span.add_log("State updated", {"old_state": "pending", "new_state": "active"})
        span.add_log("Validation passed")
        
        assert len(span.logs) == 2
        assert span.logs[0]["message"] == "State updated"
        assert span.logs[0]["metadata"]["old_state"] == "pending"


class TestChain:
    """测试链路"""
    
    def test_chain_creation(self):
        """测试链路创建"""
        chain = Chain(
            chain_id="CH-test-789",
            task_id="test-task-789",
            created_at=datetime.now(),
            task_type="requirement"
        )
        
        assert chain.chain_id == "CH-test-789"
        assert chain.task_id == "test-task-789"
        assert chain.status == SpanStatus.STARTED
        assert len(chain.spans) == 0
    
    def test_chain_add_span(self):
        """测试链路添加Span"""
        chain = Chain(
            chain_id="CH-test-101",
            task_id="test-task-101",
            created_at=datetime.now()
        )
        
        span = Span(
            span_id="SP-root-001",
            chain_id=chain.chain_id,
            span_type=SpanType.TASK,
            operation_name="root_operation",
            start_time=datetime.now()
        )
        
        chain.add_span(span)
        
        assert len(chain.spans) == 1
        assert chain.root_span_id == "SP-root-001"
        
        child_span = Span(
            span_id="SP-child-001",
            chain_id=chain.chain_id,
            span_type=SpanType.AGENT,
            operation_name="child_operation",
            start_time=datetime.now(),
            parent_span_id="SP-root-001"
        )
        
        chain.add_span(child_span)
        
        assert len(chain.spans) == 2
    
    def test_chain_get_span(self):
        """测试链路获取Span"""
        chain = Chain(
            chain_id="CH-test-102",
            task_id="test-task-102",
            created_at=datetime.now()
        )
        
        span = Span(
            span_id="SP-find-me",
            chain_id=chain.chain_id,
            span_type=SpanType.EXECUTION,
            operation_name="find_me",
            start_time=datetime.now()
        )
        
        chain.add_span(span)
        
        found = chain.get_span("SP-find-me")
        assert found is not None
        assert found.span_id == "SP-find-me"
        
        not_found = chain.get_span("SP-does-not-exist")
        assert not_found is None
    
    def test_chain_get_spans_by_type(self):
        """测试链路按类型获取Spans"""
        chain = Chain(
            chain_id="CH-test-103",
            task_id="test-task-103",
            created_at=datetime.now()
        )
        
        chain.add_span(Span(
            span_id="SP-task-001",
            chain_id=chain.chain_id,
            span_type=SpanType.TASK,
            operation_name="task1",
            start_time=datetime.now()
        ))
        
        chain.add_span(Span(
            span_id="SP-agent-001",
            chain_id=chain.chain_id,
            span_type=SpanType.AGENT,
            operation_name="agent1",
            start_time=datetime.now()
        ))
        
        chain.add_span(Span(
            span_id="SP-task-002",
            chain_id=chain.chain_id,
            span_type=SpanType.TASK,
            operation_name="task2",
            start_time=datetime.now()
        ))
        
        task_spans = chain.get_spans_by_type(SpanType.TASK)
        assert len(task_spans) == 2
        
        agent_spans = chain.get_spans_by_type(SpanType.AGENT)
        assert len(agent_spans) == 1
    
    def test_chain_statistics(self):
        """测试链路统计"""
        chain = Chain(
            chain_id="CH-test-104",
            task_id="test-task-104",
            created_at=datetime.now()
        )
        
        span1 = Span(
            span_id="SP-1",
            chain_id=chain.chain_id,
            span_type=SpanType.TASK,
            operation_name="op1",
            start_time=datetime.now()
        )
        span1.complete(SpanStatus.COMPLETED)
        chain.add_span(span1)
        
        span2 = Span(
            span_id="SP-2",
            chain_id=chain.chain_id,
            span_type=SpanType.AGENT,
            operation_name="op2",
            start_time=datetime.now()
        )
        span2.complete(SpanStatus.FAILED)
        chain.add_span(span2)
        
        stats = chain.get_statistics()
        
        assert stats["total_spans"] == 2
        assert stats["completed_spans"] == 1
        assert stats["failed_spans"] == 1
        assert "spans_by_type" in stats
        assert "total_duration_ms" in stats


class TestChainTracker:
    """测试链路追踪器"""
    
    def test_tracker_creation(self):
        """测试追踪器创建"""
        tracker = ChainTracker()
        
        assert tracker is not None
        assert len(tracker.chains) == 0
        assert len(tracker.active_chains) == 0
    
    def test_create_chain(self):
        """测试创建链路"""
        tracker = ChainTracker()
        chain = tracker.create_chain(
            task_id="task-001",
            task_type="requirement",
            priority=5
        )
        
        assert chain is not None
        assert chain.task_id == "task-001"
        assert chain.task_type == "requirement"
        assert chain.priority == 5
        assert chain.chain_id in tracker.chains
        assert chain.chain_id in tracker.active_chains
    
    def test_start_and_end_span(self):
        """测试开始和结束Span"""
        tracker = ChainTracker()
        chain = tracker.create_chain(task_id="task-002")
        
        span = tracker.start_span(
            chain_id=chain.chain_id,
            span_type=SpanType.TASK,
            operation_name="process_task",
            layer="scheduling_layer",
            agent_id="agent-orchestrator"
        )
        
        assert span is not None
        assert span.operation_name == "process_task"
        assert span.layer == "scheduling_layer"
        assert span.agent_id == "agent-orchestrator"
        
        time.sleep(0.01)
        
        tracker.end_span(span.span_id, SpanStatus.COMPLETED)
        
        ended_span = chain.get_span(span.span_id)
        assert ended_span is not None
        assert ended_span.status == SpanStatus.COMPLETED
        assert ended_span.duration_ms is not None
    
    def test_nested_spans(self):
        """测试嵌套Span"""
        tracker = ChainTracker()
        chain = tracker.create_chain(task_id="task-003")
        
        parent_span = tracker.start_span(
            chain_id=chain.chain_id,
            span_type=SpanType.TASK,
            operation_name="parent_operation"
        )
        
        child_span = tracker.start_span(
            chain_id=chain.chain_id,
            span_type=SpanType.AGENT,
            operation_name="child_operation"
        )
        
        assert child_span.parent_span_id == parent_span.span_id
        
        tracker.end_span(child_span.span_id)
        tracker.end_span(parent_span.span_id)
        
        assert len(chain.spans) == 2
    
    def test_complete_chain(self):
        """测试完成链路"""
        tracker = ChainTracker()
        chain = tracker.create_chain(task_id="task-004")
        
        span = tracker.start_span(
            chain_id=chain.chain_id,
            span_type=SpanType.TASK,
            operation_name="final_task"
        )
        tracker.end_span(span.span_id)
        
        tracker.complete_chain(chain.chain_id, SpanStatus.COMPLETED)
        
        completed_chain = tracker.get_chain(chain.chain_id)
        assert completed_chain is not None
        assert completed_chain.status == SpanStatus.COMPLETED
        assert completed_chain.completed_at is not None
        assert chain.chain_id not in tracker.active_chains
    
    def test_get_chain_by_task(self):
        """测试根据任务ID获取链路"""
        tracker = ChainTracker()
        chain = tracker.create_chain(task_id="unique-task-123")
        
        found = tracker.get_chain_by_task("unique-task-123")
        assert found is not None
        assert found.chain_id == chain.chain_id
        
        not_found = tracker.get_chain_by_task("non-existent-task")
        assert not_found is None
    
    def test_tracker_statistics(self):
        """测试追踪器统计"""
        tracker = ChainTracker()
        
        chain1 = tracker.create_chain(task_id="task-stat-1")
        chain2 = tracker.create_chain(task_id="task-stat-2")
        
        tracker.start_span(chain1.chain_id, SpanType.TASK, "op1")
        tracker.start_span(chain1.chain_id, SpanType.AGENT, "op2")
        tracker.start_span(chain2.chain_id, SpanType.TASK, "op3")
        
        stats = tracker.get_statistics()
        
        assert stats["total_chains"] == 2
        assert stats["active_chains"] == 2
        assert stats["total_spans"] == 3
    
    def test_verify_traceability(self):
        """测试验证可追溯性"""
        tracker = ChainTracker()
        chain = tracker.create_chain(task_id="task-trace")
        
        span = tracker.start_span(
            chain_id=chain.chain_id,
            span_type=SpanType.TASK,
            operation_name="test_op"
        )
        span.fail("Test error")
        tracker.end_span(span.span_id)
        
        tracker.complete_chain(chain.chain_id)
        
        result = tracker.verify_traceability()
        
        assert "valid" in result
        assert "issues" in result
        assert "metrics" in result


class TestChainContext:
    """测试链路上下文管理器"""
    
    def test_context_manager_success(self):
        """测试上下文管理器成功场景"""
        tracker = ChainTracker()
        chain = tracker.create_chain(task_id="task-context-1")
        
        with ChainContext(tracker, chain.chain_id, SpanType.TASK, "context_operation") as span:
            assert span is not None
            assert span.operation_name == "context_operation"
        
        completed_span = chain.get_span(span.span_id)
        assert completed_span.status == SpanStatus.COMPLETED
    
    def test_context_manager_with_exception(self):
        """测试上下文管理器异常场景"""
        tracker = ChainTracker()
        chain = tracker.create_chain(task_id="task-context-2")
        
        try:
            with ChainContext(tracker, chain.chain_id, SpanType.EXECUTION, "context_with_error") as span:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        failed_span = chain.get_span(span.span_id)
        assert failed_span.status == SpanStatus.FAILED
        assert failed_span.error is not None
        assert "ValueError" in failed_span.error


class TestGlobalTracker:
    """测试全局追踪器"""
    
    def test_get_global_tracker(self):
        """测试获取全局追踪器"""
        tracker1 = get_chain_tracker()
        tracker2 = get_chain_tracker()
        
        assert tracker1 is tracker2
    
    def test_set_global_tracker(self):
        """测试设置全局追踪器"""
        from src.scheduling_layer.chain_id import set_chain_tracker
        
        new_tracker = ChainTracker()
        set_chain_tracker(new_tracker)
        
        retrieved = get_chain_tracker()
        assert retrieved is new_tracker


def test_end_to_end_trace():
    """端到端追踪测试"""
    tracker = ChainTracker()
    
    chain = tracker.create_chain(
        task_id="e2e-task-001",
        task_type="requirement",
        priority=8,
        source="user_input",
        metadata={"description": "End-to-end test task"}
    )
    
    input_span = tracker.start_span(
        chain_id=chain.chain_id,
        span_type=SpanType.TASK,
        operation_name="parse_input",
        layer="input_layer"
    )
    
    time.sleep(0.01)
    tracker.end_span(input_span.span_id, SpanStatus.COMPLETED)
    
    agent_span = tracker.start_span(
        chain_id=chain.chain_id,
        span_type=SpanType.AGENT,
        operation_name="analyze_requirement",
        layer="agent_layer",
        agent_id="agent-analyzer"
    )
    
    time.sleep(0.01)
    tracker.end_span(agent_span.span_id, SpanStatus.COMPLETED)
    
    exec_span = tracker.start_span(
        chain_id=chain.chain_id,
        span_type=SpanType.EXECUTION,
        operation_name="generate_code",
        layer="execution_layer"
    )
    
    time.sleep(0.01)
    tracker.end_span(exec_span.span_id, SpanStatus.COMPLETED)
    
    tracker.complete_chain(chain.chain_id, SpanStatus.COMPLETED)
    
    assert chain.status == SpanStatus.COMPLETED
    assert len(chain.spans) == 3
    assert chain.root_span_id is not None
    
    stats = chain.get_statistics()
    assert stats["total_spans"] == 3
    assert stats["completed_spans"] == 3
    assert stats["failed_spans"] == 0
    
    verification = tracker.verify_traceability()
    assert verification["valid"] is True
