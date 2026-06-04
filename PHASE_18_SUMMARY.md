# Phase 18: 状态同步机制

## 阶段目标

实现状态同步机制，确保信息一致性、完整性和可追溯，遵循信息完整公理。

## 核心成果

### 1. 状态同步核心类型

**文件**: `/workspace/src/scheduling_layer/state_sync.py`

#### 同步方向 (SyncDirection)
```python
class SyncDirection(Enum):
    PUSH = auto()              # 推送
    PULL = auto()              # 拉取
    BIDIRECTIONAL = auto()     # 双向
```

#### 冲突解决策略 (ConflictStrategy)
```python
class ConflictStrategy(Enum):
    LATEST_TIMESTAMP = auto()  # 最新时间戳
    AGENT_PRIORITY = auto()    # 代理优先级
    MERGE = auto()             # 合并
    REJECT = auto()            # 拒绝
    CUSTOM = auto()            # 自定义
```

#### 同步状态 (SyncStatus)
```python
class SyncStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    CONFLICT = auto()
    FAILED = auto()
```

### 2. 状态变更 (StateChange)

```python
@dataclass
class StateChange:
    change_id: str
    timestamp: datetime
    source: str
    layer: str
    task_id: Optional[str]
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str
    metadata: Dict[str, Any]
    - compute_hash()  # 计算变更哈希值
```

### 3. 同步批次 (SyncBatch)

```python
@dataclass
class SyncBatch:
    batch_id: str
    source_node: str
    target_node: str
    direction: SyncDirection
    changes: List[StateChange]
    created_at: datetime
    processed_at: Optional[datetime]
    status: SyncStatus
    - compute_batch_hash()  # 计算批次哈希
```

### 4. 冲突记录 (ConflictRecord)

```python
@dataclass
class ConflictRecord:
    conflict_id: str
    change_id: str
    batch_id: str
    local_value: Any
    remote_value: Any
    resolution: Optional[str]
    resolved: bool
    timestamp: datetime
```

### 5. 同步统计 (SyncStats)

```python
@dataclass
class SyncStats:
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    conflicts_detected: int
    conflicts_resolved: int
    changes_synced: int
    sync_latency_ms: float
    last_sync_time: Optional[datetime]
```

### 6. 状态同步器 (StateSynchronizer)

```python
class StateSynchronizer:
    - record_change(source, layer, task_id, field_name, old_value, new_value)
    - create_sync_batch(target_node, direction, task_id, since)
    - apply_change(change)
    - apply_batch(batch)
    - get_changes_since(task_id, since)
    - get_conflicts(resolved)
    - get_stats()
    - cleanup_old_changes(before)
```

## 技术特性

### 1. 变更追踪
```python
# 记录每次状态变更
change = sync.record_change(
    source="agent-a",
    layer="task",
    task_id="task-001",
    field_name="status",
    old_value="PENDING",
    new_value="IN_PROGRESS"
)
```

### 2. 同步批次管理
```python
# 创建同步批次，包含自某时间点以来的所有变更
batch = sync.create_sync_batch(
    target_node="node-b",
    direction=SyncDirection.PUSH,
    task_id="task-001",
    since=datetime.now() - timedelta(hours=1)
)
```

### 3. 冲突检测与解决
```python
# 自动检测状态变更冲突
# 支持多种解决策略：LATEST_TIMESTAMP, REJECT, MERGE, CUSTOM
sync.conflict_strategy = ConflictStrategy.LATEST_TIMESTAMP
```

### 4. 完整性验证
```python
# 变更计算哈希值，确保内容完整性
hash = change.compute_hash()
batch_hash = batch.compute_batch_hash()
```

### 5. 统计监控
```python
# 获取同步统计信息
stats = sync.get_stats()
# {
#     "total_syncs": 10,
#     "successful_syncs": 9,
#     "failed_syncs": 1,
#     "conflicts_detected": 2,
#     ...
# }
```

## 验证测试

**文件**: `/workspace/test_state_sync.py`

**测试覆盖**:
- 状态变更记录 (2 tests)
- 同步批次管理 (2 tests)
- 状态同步器核心功能 (9 tests)
- 冲突检测与解决 (2 tests)
- 全局实例与清理 (2 tests)

**测试结果**: 17 tests passed ✓

## 与现有系统集成

### 1. 与状态管理系统集成
- 基于 Phase 9 的 StateManager
- 支持 SystemState、TaskState、BusinessState 三层状态同步
- 保持状态隔离原则

### 2. 与任务分发集成
- TaskDispatcher 可以使用同步机制
- 负载均衡与状态同步配合

### 3. 与其他调度层组件集成
- 与 EventTracker、ChainTracker 互补
- 完整的可追溯系统

## 使用示例

### 1. 基本同步
```python
from src.scheduling_layer.state_sync import (
    StateSynchronizer, SyncDirection, ConflictStrategy
)

sync = StateSynchronizer()

# 记录变更
sync.record_change(
    source="agent-a",
    layer="task",
    task_id="task-001",
    field_name="status",
    old_value="PENDING",
    new_value="IN_PROGRESS"
)

# 创建同步批次
batch = sync.create_sync_batch(
    target_node="node-b",
    direction=SyncDirection.PUSH,
    task_id="task-001"
)

# 应用批次
result = sync.apply_batch(batch)
```

### 2. 冲突解决
```python
# 设置冲突策略
sync.conflict_strategy = ConflictStrategy.LATEST_TIMESTAMP

# 或者自定义解决器
def custom_resolver(conflict, change):
    # 自定义逻辑
    pass

sync.custom_conflict_resolver = custom_resolver
sync.conflict_strategy = ConflictStrategy.CUSTOM
```

### 3. 监控与统计
```python
# 获取同步统计
stats = sync.get_stats()
print(f"成功同步: {stats['stats']['successful_syncs']}")
print(f"检测到冲突: {stats['stats']['conflicts_detected']}")

# 清理旧变更
sync.cleanup_old_changes(datetime.now() - timedelta(days=7))
```

## 架构位置

**调度层 (scheduling_layer)** 核心组件：
- 位置: `src/scheduling_layer/state_sync.py`
- 导出: `src/scheduling_layer/__init__.py`
- 依赖: state.py

## 设计原则

1. **信息完整性**: 每次变更都完整记录，支持哈希验证
2. **一致性保证**: 支持冲突检测与多种解决策略
3. **可追溯性**: 完整的变更日志与同步历史
4. **效率优先**: 批量同步，避免不必要的传输
5. **灵活配置**: 支持多种同步策略与方向

## 下一步

Phase 19-20 将实现监控与告警系统等高级功能。

## 统计

- **代码行数**: ~480行
- **测试用例**: 17个
- **测试通过率**: 100%
- **同步策略**: 5种冲突解决策略
- **核心类**: 6个
- **导出API**: 12个
