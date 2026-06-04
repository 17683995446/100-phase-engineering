"""
状态同步机制验证测试
"""

import pytest
from datetime import datetime, timedelta
from src.scheduling_layer.state_sync import (
    StateSynchronizer, StateChange, SyncBatch, ConflictRecord, SyncStats,
    SyncDirection, ConflictStrategy, SyncStatus
)
from src.scheduling_layer.state import StateManager, TaskStatus


class TestStateChange:
    """测试状态变更记录"""
    
    def test_change_creation(self):
        """测试创建状态变更"""
        change = StateChange(
            change_id="test-001",
            timestamp=datetime.now(),
            source="test-agent",
            layer="task",
            task_id="task-001",
            field_name="status",
            old_value="PENDING",
            new_value="IN_PROGRESS",
            change_type="update"
        )
        
        assert change.change_id == "test-001"
        assert change.source == "test-agent"
        assert change.layer == "task"
        assert change.task_id == "task-001"
    
    def test_compute_hash(self):
        """测试计算哈希值"""
        change = StateChange(
            change_id="test-002",
            timestamp=datetime.now(),
            source="test",
            layer="system",
            task_id=None,
            field_name="health_status",
            old_value="healthy",
            new_value="degraded",
            change_type="update"
        )
        
        hash_val = change.compute_hash()
        
        assert hash_val is not None
        assert len(hash_val) == 16


class TestSyncBatch:
    """测试同步批次"""
    
    def test_batch_creation(self):
        """测试创建同步批次"""
        batch = SyncBatch(
            batch_id="batch-001",
            source_node="node-a",
            target_node="node-b",
            direction=SyncDirection.PUSH
        )
        
        assert batch.batch_id == "batch-001"
        assert batch.source_node == "node-a"
        assert batch.target_node == "node-b"
        assert batch.status == SyncStatus.PENDING
        assert len(batch.changes) == 0
    
    def test_batch_compute_hash(self):
        """测试计算批次哈希"""
        batch = SyncBatch(
            batch_id="batch-002",
            source_node="node-a",
            target_node="node-b",
            direction=SyncDirection.PUSH
        )
        
        change = StateChange(
            change_id="change-001",
            timestamp=datetime.now(),
            source="test",
            layer="system",
            task_id=None,
            field_name="version",
            old_value="0.1.0",
            new_value="0.2.0",
            change_type="update"
        )
        batch.changes.append(change)
        
        hash_val = batch.compute_batch_hash()
        
        assert hash_val is not None
        assert len(hash_val) == 24


class TestStateSynchronizer:
    """测试状态同步器"""
    
    def test_synchronizer_creation(self):
        """测试创建同步器"""
        sync = StateSynchronizer()
        
        assert sync is not None
        assert len(sync.change_log) == 0
        assert len(sync.pending_batches) == 0
        assert sync.sync_stats.total_syncs == 0
    
    def test_record_change(self):
        """测试记录状态变更"""
        sync = StateSynchronizer()
        
        change = sync.record_change(
            source="agent-a",
            layer="task",
            task_id="task-001",
            field_name="status",
            old_value="PENDING",
            new_value="IN_PROGRESS"
        )
        
        assert change is not None
        assert change.source == "agent-a"
        assert change.task_id == "task-001"
        
        assert "task-001" in sync.change_log
        assert len(sync.change_log["task-001"]) == 1
    
    def test_create_sync_batch(self):
        """测试创建同步批次"""
        sync = StateSynchronizer()
        
        # 记录一些变更
        sync.record_change(
            source="agent-a",
            layer="task",
            task_id="task-001",
            field_name="status",
            old_value="PENDING",
            new_value="IN_PROGRESS"
        )
        
        batch = sync.create_sync_batch(
            target_node="node-b",
            direction=SyncDirection.PUSH,
            task_id="task-001"
        )
        
        assert batch is not None
        assert len(batch.changes) == 1
        assert batch.source_node == sync.node_id
        assert len(sync.pending_batches) == 1
    
    def test_apply_system_change(self):
        """测试应用系统状态变更"""
        sync = StateSynchronizer()
        
        change = sync.record_change(
            source="system",
            layer="system",
            task_id=None,
            field_name="health_status",
            old_value="healthy",
            new_value="degraded"
        )
        
        success = sync.apply_change(change)
        
        assert success is True
        assert sync.sync_stats.changes_synced == 1
    
    def test_apply_task_change(self):
        """测试应用任务状态变更"""
        sync = StateSynchronizer()
        
        # 先创建任务状态
        sync.state_manager.create_task_state("task-001", "requirement")
        
        change = sync.record_change(
            source="agent-a",
            layer="task",
            task_id="task-001",
            field_name="status",
            old_value="PENDING",
            new_value="IN_PROGRESS"
        )
        
        success = sync.apply_change(change)
        
        assert success is True
    
    def test_apply_business_change(self):
        """测试应用业务状态变更"""
        sync = StateSynchronizer()
        
        # 先创建业务状态
        sync.state_manager.create_business_state("task-001", "test input")
        
        change = sync.record_change(
            source="agent-b",
            layer="business",
            task_id="task-001",
            field_name="analysis_result",
            old_value=None,
            new_value="分析结果"
        )
        
        success = sync.apply_change(change)
        
        assert success is True
    
    def test_conflict_detection(self):
        """测试冲突检测"""
        sync = StateSynchronizer()
        
        # 先创建任务状态
        sync.state_manager.create_task_state("task-001", "requirement")
        
        # 本地修改
        sync.state_manager.update_task_status(
            "task-001",
            TaskStatus.IN_PROGRESS,
            progress=0.5
        )
        
        # 现在尝试应用一个变更，old_value 与当前不匹配（冲突）
        change = StateChange(
            change_id="conflict-001",
            timestamp=datetime.now(),
            source="remote-agent",
            layer="task",
            task_id="task-001",
            field_name="progress",
            old_value=0.0,  # 与当前 0.5 不匹配
            new_value=0.75,
            change_type="update"
        )
        
        success = sync.apply_change(change)
        
        # 冲突应该被处理
        assert len(sync.conflict_records) == 1
        assert sync.sync_stats.conflicts_detected >= 1
    
    def test_conflict_resolution_strategy(self):
        """测试冲突解决策略"""
        sync = StateSynchronizer()
        sync.conflict_strategy = ConflictStrategy.LATEST_TIMESTAMP
        
        sync.state_manager.create_task_state("task-001", "requirement")
        
        sync.state_manager.update_task_status(
            "task-001",
            TaskStatus.IN_PROGRESS
        )
        
        change = StateChange(
            change_id="conflict-002",
            timestamp=datetime.now(),
            source="remote",
            layer="task",
            task_id="task-001",
            field_name="status",
            old_value="PENDING",
            new_value="REVIEWING",
            change_type="update"
        )
        
        sync.apply_change(change)
        
        assert len(sync.conflict_records) == 1
        assert sync.conflict_records[0].resolved is True
    
    def test_apply_batch(self):
        """测试应用同步批次"""
        sync = StateSynchronizer()
        
        # 创建任务
        sync.state_manager.create_task_state("task-001", "requirement")
        sync.state_manager.create_business_state("task-001", "test input")
        
        # 创建批次
        batch = SyncBatch(
            batch_id="batch-test",
            source_node="node-a",
            target_node="node-b",
            direction=SyncDirection.PUSH
        )
        
        # 添加变更
        batch.changes.append(StateChange(
            change_id="change-1",
            timestamp=datetime.now(),
            source="test",
            layer="task",
            task_id="task-001",
            field_name="status",
            old_value="PENDING",
            new_value="IN_PROGRESS",
            change_type="update"
        ))
        
        batch.changes.append(StateChange(
            change_id="change-2",
            timestamp=datetime.now(),
            source="test",
            layer="business",
            task_id="task-001",
            field_name="analysis_result",
            old_value=None,
            new_value="测试结果",
            change_type="update"
        ))
        
        # 应用批次
        result = sync.apply_batch(batch)
        
        assert result["status"] == "COMPLETED"
        assert sync.sync_stats.total_syncs >= 1
        assert sync.sync_stats.successful_syncs >= 1
    
    def test_get_changes_since(self):
        """测试获取某时间点之后的变更"""
        sync = StateSynchronizer()
        now = datetime.now()
        
        # 先记录一个旧的变更
        old_change = sync.record_change(
            source="test",
            layer="task",
            task_id="task-001",
            field_name="status",
            old_value="PENDING",
            new_value="IN_PROGRESS"
        )
        old_change.timestamp = now - timedelta(hours=1)
        
        # 记录一个新的变更
        new_change = sync.record_change(
            source="test",
            layer="task",
            task_id="task-001",
            field_name="progress",
            old_value=0.0,
            new_value=0.5
        )
        new_change.timestamp = now
        
        # 只获取最近30分钟的变更
        changes = sync.get_changes_since("task-001", now - timedelta(minutes=30))
        
        assert len(changes) >= 1
    
    def test_get_stats(self):
        """测试获取统计信息"""
        sync = StateSynchronizer()
        
        stats = sync.get_stats()
        
        assert "node_id" in stats
        assert "stats" in stats
        assert "pending_batches" in stats
        assert "pending_conflicts" in stats


def test_global_synchronizer():
    """测试获取全局同步器"""
    from src.scheduling_layer.state_sync import get_state_synchronizer
    
    sync1 = get_state_synchronizer()
    sync2 = get_state_synchronizer()
    
    assert sync1 is sync2


def test_cleanup_old_changes():
    """测试清理旧的变更记录"""
    sync = StateSynchronizer()
    now = datetime.now()
    
    # 添加旧变更
    change1 = sync.record_change(
        source="test",
        layer="task",
        task_id="task-001",
        field_name="field1",
        old_value=1,
        new_value=2
    )
    change1.timestamp = now - timedelta(days=2)
    
    # 添加新变更
    change2 = sync.record_change(
        source="test",
        layer="task",
        task_id="task-001",
        field_name="field2",
        old_value=3,
        new_value=4
    )
    change2.timestamp = now - timedelta(hours=1)
    
    # 清理一天前的变更
    removed = sync.cleanup_old_changes(now - timedelta(days=1))
    
    assert removed >= 1
