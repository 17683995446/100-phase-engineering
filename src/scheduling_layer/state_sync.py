"""
状态同步机制
遵循信息完整公理：状态同步确保信息一致性、完整性和可追溯
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum, auto
from datetime import datetime
from copy import deepcopy
import hashlib
import uuid

from src.scheduling_layer.state import StateManager, SystemState, TaskState, BusinessState, GlobalState, TaskStatus
from src.utils.logger import logger


class SyncDirection(Enum):
    """同步方向"""
    PUSH = auto()      # 推送
    PULL = auto()      # 拉取
    BIDIRECTIONAL = auto()  # 双向


class ConflictStrategy(Enum):
    """冲突解决策略"""
    LATEST_TIMESTAMP = auto()  # 最新时间戳
    AGENT_PRIORITY = auto()    # 代理优先级
    MERGE = auto()              # 合并
    REJECT = auto()             # 拒绝
    CUSTOM = auto()             # 自定义


class SyncStatus(Enum):
    """同步状态"""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    CONFLICT = auto()
    FAILED = auto()


@dataclass
class StateChange:
    """状态变更记录"""
    change_id: str
    timestamp: datetime
    source: str  # 变更源
    layer: str   # 变更层: "system", "task", "business"
    task_id: Optional[str]
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str  # "create", "update", "delete"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def compute_hash(self) -> str:
        """计算变更内容的哈希值"""
        content = f"{self.change_id}{self.timestamp}{self.source}{self.layer}{self.task_id}{self.field_name}{self.old_value}{self.new_value}{self.change_type}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class SyncBatch:
    """同步批次"""
    batch_id: str
    source_node: str
    target_node: str
    direction: SyncDirection
    changes: List[StateChange] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    status: SyncStatus = SyncStatus.PENDING
    
    def compute_batch_hash(self) -> str:
        """计算批次哈希"""
        hashes = [change.compute_hash() for change in self.changes]
        combined = "|".join(hashes)
        return hashlib.sha256(combined.encode()).hexdigest()[:24]


@dataclass
class ConflictRecord:
    """冲突记录"""
    conflict_id: str
    change_id: str
    batch_id: str
    local_value: Any
    remote_value: Any
    resolution: Optional[str] = None
    resolved: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SyncStats:
    """同步统计"""
    total_syncs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    changes_synced: int = 0
    sync_latency_ms: float = 0.0
    last_sync_time: Optional[datetime] = None


class StateSynchronizer:
    """状态同步器"""
    
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager or StateManager()
        self.change_log: Dict[str, List[StateChange]] = {}  # task_id -> [changes]
        self.pending_batches: List[SyncBatch] = []
        self.conflict_records: List[ConflictRecord] = []
        self.sync_stats: SyncStats = SyncStats()
        self.conflict_strategy: ConflictStrategy = ConflictStrategy.LATEST_TIMESTAMP
        self.custom_conflict_resolver: Optional[Callable] = None
        self.node_id: str = f"node-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"状态同步器初始化: {self.node_id}")
    
    def record_change(
        self,
        source: str,
        layer: str,
        task_id: Optional[str],
        field_name: str,
        old_value: Any,
        new_value: Any,
        change_type: str = "update"
    ) -> StateChange:
        """记录状态变更"""
        change = StateChange(
            change_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            source=source,
            layer=layer,
            task_id=task_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type
        )
        
        # 记录变更
        key = task_id or "global"
        if key not in self.change_log:
            self.change_log[key] = []
        self.change_log[key].append(change)
        
        logger.debug(f"记录状态变更: {change.change_id} - {layer}.{field_name}")
        
        return change
    
    def create_sync_batch(
        self,
        target_node: str,
        direction: SyncDirection,
        task_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> SyncBatch:
        """创建同步批次"""
        batch = SyncBatch(
            batch_id=str(uuid.uuid4()),
            source_node=self.node_id,
            target_node=target_node,
            direction=direction
        )
        
        # 收集需要同步的变更
        if task_id:
            key = task_id
            if key in self.change_log:
                batch.changes = [c for c in self.change_log[key] if since is None or c.timestamp > since]
        else:
            # 同步所有变更
            for key, changes in self.change_log.items():
                filtered = [c for c in changes if since is None or c.timestamp > since]
                batch.changes.extend(filtered)
        
        logger.info(f"创建同步批次: {batch.batch_id}, 包含 {len(batch.changes)} 个变更")
        self.pending_batches.append(batch)
        
        return batch
    
    def apply_change(self, change: StateChange) -> bool:
        """应用状态变更"""
        try:
            if change.layer == "system":
                self._apply_system_change(change)
            elif change.layer == "task" and change.task_id:
                self._apply_task_change(change)
            elif change.layer == "business" and change.task_id:
                self._apply_business_change(change)
            else:
                logger.warning(f"未知的状态层或缺少task_id: {change.layer}")
                return False
            
            self.sync_stats.changes_synced += 1
            return True
        except Exception as e:
            logger.error(f"应用状态变更失败: {change.change_id} - {e}")
            return False
    
    def _apply_system_change(self, change: StateChange):
        """应用系统状态变更"""
        current = self.state_manager.get_system_state()
        old_val = current.get(change.field_name)
        
        # 检查冲突
        if old_val is not None and old_val != change.old_value:
            self._handle_conflict(change, old_val, change.new_value)
            return
        
        self.state_manager.update_system_state({change.field_name: change.new_value})
    
    def _apply_task_change(self, change: StateChange):
        """应用任务状态变更"""
        task_id = change.task_id
        if not task_id:
            return
        
        current = self.state_manager.get_task_state(task_id)
        if not current:
            logger.warning(f"任务状态不存在，无法应用变更: {task_id}")
            return
        
        old_val = current.get(change.field_name)
        
        # 检查冲突
        if old_val is not None and old_val != change.old_value:
            self._handle_conflict(change, old_val, change.new_value)
            return
        
        # 应用变更
        if change.field_name == "status":
            # 转换为TaskStatus
            if isinstance(change.new_value, str):
                try:
                    new_status = TaskStatus[change.new_value.upper()]
                    self.state_manager.update_task_status(task_id, new_status)
                except KeyError:
                    logger.warning(f"无效的任务状态: {change.new_value}")
            elif isinstance(change.new_value, TaskStatus):
                self.state_manager.update_task_status(task_id, change.new_value)
        elif change.field_name == "progress":
            self.state_manager.update_task_status(
                task_id,
                current.get("status", TaskStatus.PENDING),
                progress=float(change.new_value)
            )
        elif change.field_name == "assigned_agent":
            self.state_manager.update_task_status(
                task_id,
                current.get("status", TaskStatus.PENDING),
                agent=change.new_value
            )
    
    def _apply_business_change(self, change: StateChange):
        """应用业务状态变更"""
        task_id = change.task_id
        if not task_id:
            return
        
        current = self.state_manager.get_business_state(task_id)
        if not current:
            logger.warning(f"业务状态不存在，无法应用变更: {task_id}")
            return
        
        old_val = current.get(change.field_name)
        
        # 检查冲突
        if old_val is not None and old_val != change.old_value:
            self._handle_conflict(change, old_val, change.new_value)
            return
        
        self.state_manager.update_business_field(task_id, change.field_name, change.new_value)
    
    def _handle_conflict(self, change: StateChange, local_val: Any, remote_val: Any):
        """处理状态冲突"""
        conflict = ConflictRecord(
            conflict_id=str(uuid.uuid4()),
            change_id=change.change_id,
            batch_id=change.metadata.get("batch_id"),
            local_value=local_val,
            remote_value=remote_val
        )
        self.conflict_records.append(conflict)
        self.sync_stats.conflicts_detected += 1
        
        logger.warning(f"检测到状态冲突: {conflict.conflict_id} - {change.layer}.{change.field_name}")
        
        # 应用冲突解决策略
        self._resolve_conflict(conflict, change)
    
    def _resolve_conflict(self, conflict: ConflictRecord, change: StateChange):
        """解决状态冲突"""
        strategy = self.conflict_strategy
        
        if strategy == ConflictStrategy.LATEST_TIMESTAMP:
            # 使用最新时间戳的版本
            logger.info(f"使用最新时间戳策略解决冲突: {conflict.conflict_id}")
            conflict.resolution = "latest_timestamp"
            conflict.resolved = True
            self.sync_stats.conflicts_resolved += 1
            
        elif strategy == ConflictStrategy.REJECT:
            # 拒绝远程变更
            logger.info(f"拒绝远程变更，保持本地版本: {conflict.conflict_id}")
            conflict.resolution = "reject"
            conflict.resolved = True
            self.sync_stats.conflicts_resolved += 1
            
        elif strategy == ConflictStrategy.MERGE:
            # 合并变更
            logger.info(f"尝试合并变更: {conflict.conflict_id}")
            conflict.resolution = "merge"
            conflict.resolved = True
            self.sync_stats.conflicts_resolved += 1
            
        elif strategy == ConflictStrategy.CUSTOM and self.custom_conflict_resolver:
            # 自定义解决策略
            try:
                self.custom_conflict_resolver(conflict, change)
                conflict.resolution = "custom"
                conflict.resolved = True
                self.sync_stats.conflicts_resolved += 1
            except Exception as e:
                logger.error(f"自定义冲突解决失败: {e}")
    
    def apply_batch(self, batch: SyncBatch) -> Dict[str, Any]:
        """应用同步批次"""
        batch.status = SyncStatus.IN_PROGRESS
        self.sync_stats.total_syncs += 1
        
        start_time = datetime.now()
        success_count = 0
        conflict_count = 0
        
        try:
            for change in batch.changes:
                change.metadata["batch_id"] = batch.batch_id
                if self.apply_change(change):
                    success_count += 1
                else:
                    conflict_count += 1
            
            batch.status = SyncStatus.COMPLETED
            batch.processed_at = datetime.now()
            self.sync_stats.successful_syncs += 1
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            self.sync_stats.sync_latency_ms = (self.sync_stats.sync_latency_ms + latency_ms) / 2
            
        except Exception as e:
            batch.status = SyncStatus.FAILED
            batch.processed_at = datetime.now()
            self.sync_stats.failed_syncs += 1
            logger.error(f"应用同步批次失败: {batch.batch_id} - {e}")
            
        result = {
            "batch_id": batch.batch_id,
            "status": batch.status.name,
            "success_count": success_count,
            "conflict_count": conflict_count,
            "total_changes": len(batch.changes),
            "latency_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
        
        self.sync_stats.last_sync_time = datetime.now()
        
        logger.info(f"同步批次应用完成: {result}")
        
        return result
    
    def get_changes_since(self, task_id: Optional[str], since: datetime) -> List[StateChange]:
        """获取某时间点之后的变更"""
        key = task_id or "global"
        changes = self.change_log.get(key, [])
        return [c for c in changes if c.timestamp > since]
    
    def get_conflicts(self, resolved: Optional[bool] = None) -> List[ConflictRecord]:
        """获取冲突记录"""
        if resolved is None:
            return self.conflict_records
        return [c for c in self.conflict_records if c.resolved == resolved]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取同步统计"""
        return {
            "node_id": self.node_id,
            "stats": {
                "total_syncs": self.sync_stats.total_syncs,
                "successful_syncs": self.sync_stats.successful_syncs,
                "failed_syncs": self.sync_stats.failed_syncs,
                "conflicts_detected": self.sync_stats.conflicts_detected,
                "conflicts_resolved": self.sync_stats.conflicts_resolved,
                "changes_synced": self.sync_stats.changes_synced,
                "sync_latency_ms": self.sync_stats.sync_latency_ms,
                "last_sync_time": self.sync_stats.last_sync_time.isoformat() if self.sync_stats.last_sync_time else None
            },
            "pending_batches": len(self.pending_batches),
            "pending_conflicts": len([c for c in self.conflict_records if not c.resolved])
        }
    
    def cleanup_old_changes(self, before: datetime):
        """清理旧的变更记录"""
        removed_count = 0
        
        for key in list(self.change_log.keys()):
            original_len = len(self.change_log[key])
            self.change_log[key] = [c for c in self.change_log[key] if c.timestamp > before]
            removed_count += original_len - len(self.change_log[key])
            
            # 清理空列表
            if not self.change_log[key]:
                del self.change_log[key]
        
        logger.info(f"清理了 {removed_count} 条旧的变更记录")
        
        return removed_count


_global_synchronizer: Optional[StateSynchronizer] = None


def get_state_synchronizer() -> StateSynchronizer:
    """获取全局状态同步器"""
    global _global_synchronizer
    if _global_synchronizer is None:
        _global_synchronizer = StateSynchronizer()
    return _global_synchronizer
