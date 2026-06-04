# Phase 13: 定义全局可追溯链路ID机制

## 阶段目标

实现端到端全链路可追溯机制，为每个任务分配唯一链路ID，追踪从任务创建到完成的全生命周期。

## 核心成果

### 1. 链路ID生成器 (ChainID)

**文件**: `/workspace/src/scheduling_layer/chain_id.py`

**关键设计**:
- 生成格式: `CH-{task_id}-{random_hex}`
- 包含任务ID、创建时间、版本号
- 支持唯一性验证和字典序列化

**核心类**:
```python
@dataclass
class ChainID:
    chain_id: str
    task_id: str
    created_at: datetime
    version: int = 1
```

### 2. Span标识系统

**设计理念**: 将每个操作步骤标识为Span，形成完整的执行链路。

**关键类**:
- `SpanID`: 单个操作单元的标识
- `Span`: 包含操作名称、时间、状态、元数据、标签、日志
- `SpanType`: TASK, AGENT, EXECUTION, VALIDATION, MESSAGE, STATE_CHANGE
- `SpanStatus`: STARTED, RUNNING, COMPLETED, FAILED, CANCELLED

**Span特性**:
- 支持嵌套父子关系
- 自动记录执行时长
- 支持标签和日志记录
- 异常自动捕获和标记

### 3. 链路管理器 (Chain)

**设计理念**: 聚合整个生命周期的所有Span。

**关键类**:
```python
@dataclass
class Chain:
    chain_id: str
    task_id: str
    created_at: datetime
    root_span_id: Optional[str]
    spans: List[Span]
    metadata: Dict[str, Any]
    task_type: Optional[str]
    priority: Optional[int]
    source: Optional[str]
```

**功能**:
- 自动维护根Span
- 按类型查询Spans
- 统计链路性能指标
- 验证可追溯性

### 4. 链路追踪器 (ChainTracker)

**设计理念**: 全局管理器，维护所有链路和活跃Span上下文。

**核心功能**:
- 创建和完成链路
- 启动和结束Span
- 维护嵌套Span的上下文栈
- 全局统计和验证

**全局函数**:
- `get_chain_tracker()`: 获取全局追踪器
- `set_chain_tracker()`: 设置全局追踪器

### 5. 上下文管理器 (ChainContext)

**设计理念**: 简化Span的生命周期管理，自动处理异常。

**使用示例**:
```python
tracker = get_chain_tracker()
chain = tracker.create_chain(task_id="task-001")

with ChainContext(tracker, chain.chain_id, SpanType.TASK, "process") as span:
    # 执行操作
    pass  # 自动完成Span

# 异常自动捕获
try:
    with ChainContext(tracker, chain.chain_id, SpanType.EXECUTION, "execute") as span:
        raise ValueError("error")
except ValueError:
    pass  # Span自动标记为失败
```

## 技术特性

### 1. 端到端追踪

- 从任务创建到任务完成的完整链路
- 跨层追踪: input_layer → scheduling_layer → agent_layer → execution_layer
- 关联所有事件、消息、状态变化

### 2. 嵌套结构

- 支持多层级嵌套Span
- 自动维护父子关系
- 上下文栈管理

### 3. 性能度量

- 自动记录每个Span的时长
- 链路总时长统计
- 成功率和失败率统计

### 4. 可追溯性验证

- 验证链路完整性
- 检查失败Span的错误信息
- 生成统计报告

## 验证测试

**文件**: `/workspace/test_chain_id.py`

**测试覆盖**:
- ✅ ChainID生成和唯一性 (3个测试)
- ✅ SpanID生成和父子关系 (2个测试)
- ✅ Span生命周期管理 (5个测试)
- ✅ Chain聚合和查询 (5个测试)
- ✅ ChainTracker全局管理 (8个测试)
- ✅ ChainContext异常处理 (2个测试)
- ✅ 全局追踪器 (2个测试)
- ✅ 端到端追踪 (1个测试)

**测试结果**: 28个测试全部通过 ✓

## 与现有系统的集成

### 1. 与EventTracker集成

链路追踪与事件追踪互补：
- EventTracker: 记录离散事件
- ChainTracker: 追踪连续执行链路

### 2. 与State系统集成

- Span记录状态变化
- 支持状态转换追踪
- 关联TaskState和BusinessState

### 3. 与DAG验证集成

- Span遵循DAG依赖关系
- 支持依赖链路的可视化

### 4. 与原子实体集成

- 链路ID关联TaskAtomicEntity
- Span关联Agent、Message、State实体
- 支持EventAtomicEntity的事件记录

## 使用场景

### 1. 任务生命周期追踪

```python
tracker = get_chain_tracker()
chain = tracker.create_chain(task_id="req-001", task_type="requirement")

span = tracker.start_span(chain.chain_id, SpanType.TASK, "parse_requirement")
# ... 处理 ...
tracker.end_span(span.span_id, SpanStatus.COMPLETED)

tracker.complete_chain(chain.chain_id)
```

### 2. Agent协作追踪

```python
orchestrator_span = tracker.start_span(chain.chain_id, SpanType.AGENT, "orchestrate", agent_id="orchestrator")

analyzer_span = tracker.start_span(chain.chain_id, SpanType.AGENT, "analyze", agent_id="analyzer")
# ... 分析 ...
tracker.end_span(analyzer_span.span_id)

tracker.end_span(orchestrator_span.span_id)
```

### 3. 执行层追踪

```python
exec_span = tracker.start_span(chain.chain_id, SpanType.EXECUTION, "generate_code", layer="execution_layer")

validation_span = tracker.start_span(chain.chain_id, SpanType.VALIDATION, "validate", layer="execution_layer")
tracker.end_span(validation_span.span_id)

tracker.end_span(exec_span.span_id)
```

## 架构位置

**调度层 (scheduling_layer)** 核心组件：
- 位置: `src/scheduling_layer/chain_id.py`
- 导出: `src/scheduling_layer/__init__.py`
- 依赖: utils/logger.py

## 设计原则

1. **信息最小熵**: 所有操作显式化，消除隐式状态
2. **可追溯性**: 端到端全链路追踪
3. **上下文保持**: 自动维护父子关系
4. **性能意识**: 最小化追踪开销
5. **错误感知**: 异常自动捕获和标记

## 下一步

Phase 14将基于链路追踪机制，实现8个Agent角色的实例化和协作机制。

## 统计

- **代码行数**: ~560行
- **测试用例**: 28个
- **测试通过率**: 100%
- **核心类**: 7个
- **核心函数**: 4个
- **导出API**: 10个
