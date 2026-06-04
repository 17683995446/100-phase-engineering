# Phase 17: 任务分发与负载均衡机制

## 阶段目标

实现任务分发与负载均衡机制，包括任务队列管理、负载均衡策略和任务状态追踪，遵循成本最小公理：任务分配最优、资源利用最大化。

## 核心成果

### 1. 负载均衡策略

**文件**: `/workspace/src/scheduling_layer/task_dispatcher.py`

#### 负载均衡策略枚举 (LoadBalancingStrategy)
```python
class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = auto()        # 轮询
    LEAST_LOADED = auto()       # 最小负载
    CAPABILITY_BASED = auto()    # 能力匹配
    AFFINITY = auto()           # 亲和性
    RANDOM = auto()             # 随机
```

### 2. Agent负载 (AgentLoad)

```python
@dataclass
class AgentLoad:
    agent_id: str                 # Agent ID
    role: str                    # 角色
    current_tasks: int           # 当前任务数
    max_capacity: int            # 最大容量
    load_percentage: float      # 负载百分比
    avg_completion_time_ms: float # 平均完成时间
    success_rate: float         # 成功率
    last_updated: datetime       # 最后更新时间
```

### 3. 任务项 (TaskItem)

```python
@dataclass
class TaskItem:
    task_id: str               # 任务ID
    task_type: TaskType        # 任务类型
    priority: MessagePriority   # 优先级
    required_capabilities: List[str] # 所需能力
    preferred_agent: Optional[str]   # 优先Agent
    affinity_agents: List[str] # 亲和Agent列表
    created_at: datetime       # 创建时间
    deadline: Optional[datetime]   # 截止时间
    metadata: Dict            # 元数据
```

### 4. 任务分配 (TaskAssignment)

```python
@dataclass
class TaskAssignment:
    assignment_id: str           # 分配ID
    task: TaskItem              # 任务项
    assigned_agent: str         # 分配的Agent
    assigned_at: datetime      # 分配时间
    status: str = "assigned"    # 状态
    started_at: Optional[datetime]    # 开始时间
    completed_at: Optional[datetime]   # 完成时间
    result: Optional[Dict]     # 结果
    error: Optional[str]       # 错误信息
```

### 5. 任务队列 (TaskQueue)

```python
class TaskQueue:
    name: str                           # 队列名称
    pending_tasks: List[TaskItem]       # 待处理任务
    running_tasks: Dict[str, Assignment] # 运行中任务
    completed_tasks: Dict[str, Assignment] # 已完成任务
    failed_tasks: Dict[str, Assignment]   # 失败任务
    
    def enqueue(task)          # 入队
    def dequeue()              # 出队
    def add_assignment()       # 添加分配
    def complete_assignment()   # 完成分配
    def fail_assignment()      # 失败分配
```

### 6. 负载均衡器 (LoadBalancer)

```python
class LoadBalancer:
    strategy: LoadBalancingStrategy     # 均衡策略
    agent_loads: Dict[str, AgentLoad]  # Agent负载
    
    def update_agent_load()            # 更新负载
    def increment_task()               # 增加任务
    def decrement_task()               # 减少任务
    def get_available_agents()          # 获取可用Agent
    def select_agent(task)             # 选择最佳Agent
```

### 7. 任务分发器 (TaskDispatcher)

```python
class TaskDispatcher:
    load_balancer: LoadBalancer       # 负载均衡器
    queues: Dict[str, TaskQueue]       # 任务队列
    assignments: Dict[str, Assignment] # 分配记录
    
    def create_queue(name)              # 创建队列
    def register_agent(agent_id, role, capacity) # 注册Agent
    def dispatch_task(task)             # 分发任务
    def dispatch_from_queue()           # 从队列分发
    def complete_assignment()           # 完成任务
    def fail_assignment()               # 任务失败
```

## 技术特性

### 1. 多策略负载均衡

支持5种负载均衡策略：
```python
balancer = LoadBalancer(LoadBalancingStrategy.LEAST_LOADED)
balancer = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)
balancer = LoadBalancer(LoadBalancingStrategy.CAPABILITY_BASED)
```

### 2. Agent容量管理

每个Agent有最大容量限制：
```python
dispatcher.register_agent("agent-001", "developer", max_capacity=5)
```

### 3. 任务优先级

支持优先级队列，高优先级任务优先处理：
```python
task = TaskItem(
    task_id="task-001",
    priority=MessagePriority.HIGH  # 高优先级
)
```

### 4. 能力匹配

基于任务所需能力分配Agent：
```python
task = TaskItem(
    required_capabilities=["code_generation", "testing"]
)
```

### 5. 亲和性调度

支持任务与Agent的亲和性：
```python
task = TaskItem(
    preferred_agent="agent-001",
    affinity_agents=["agent-002", "agent-003"]
)
```

## 验证测试

**文件**: `/workspace/test_task_dispatcher.py`

**测试覆盖**:
- 负载均衡策略测试 (1个)
- Agent负载测试 (3个)
- 任务项测试 (2个)
- 任务分配测试 (4个)
- 任务队列测试 (5个)
- 负载均衡器测试 (6个)
- 任务分发器测试 (8个)
- 全局函数测试 (2个)
- 集成测试 (2个)

**测试结果**: 33个测试全部通过 ✓

## 与现有系统集成

### 1. 与Phase 16 协作协议集成

- TaskItem包含MessagePriority
- 任务分发使用优先级队列
- 与AgentCollaborationHub互补

### 2. 与Phase 15 工作流集成

- 工作流步骤作为TaskItem分发
- TaskDispatcher支持工作流执行
- 任务状态与工作流状态同步

### 3. 与Phase 14 Agent角色集成

- 基于Agent角色分发任务
- 负载均衡考虑Agent能力
- AgentRegistry管理Agent注册

### 4. 与Phase 13 链路追踪集成

- TaskAssignment可关联链路ID
- 任务执行纳入链路追踪

## 使用示例

### 1. 基本任务分发
```python
from src.scheduling_layer.task_dispatcher import TaskDispatcher, TaskItem

dispatcher = TaskDispatcher()

dispatcher.register_agent("agent-001", "developer", max_capacity=5)

task = TaskItem(
    task_id="task-001",
    task_type="requirement",
    priority=MessagePriority.NORMAL
)

assignment = dispatcher.dispatch_task(task)
print(f"任务分配给: {assignment.assigned_agent}")
```

### 2. 使用队列
```python
dispatcher.create_queue("my-queue")

task = TaskItem(
    task_id="task-002",
    priority=MessagePriority.HIGH
)

dispatcher.get_queue("my-queue").enqueue(task)

assignment = dispatcher.dispatch_from_queue("my-queue")
```

### 3. 完成任务
```python
dispatcher.complete_assignment(
    assignment_id,
    {"result": "success", "output": "..."}
)
```

### 4. 获取统计
```python
stats = dispatcher.get_statistics()
print(f"总分配: {stats['total_assignments']}")
print(f"成功率: {stats['completed'] / stats['total_assignments']}")
```

## 架构位置

**调度层 (scheduling_layer)** 核心组件：
- 位置: `src/scheduling_layer/task_dispatcher.py`
- 导出: `src/scheduling_layer/__init__.py`
- 依赖: agent_roles.py, protocol.py, constants.py

## 设计原则

1. **成本最小**: 最小负载优先，最大化资源利用
2. **容量保护**: Agent有最大容量限制，防止过载
3. **优先级调度**: 高优先级任务优先处理
4. **能力匹配**: 任务分配给最合适的Agent
5. **可追溯**: 完整分配历史和统计

## 下一步

Phase 18-20将实现状态同步机制、错误处理与恢复机制、监控与告警系统等高级功能。

## 统计

- **代码行数**: ~570行
- **测试用例**: 33个
- **测试通过率**: 100%
- **核心类**: 7个
- **负载均衡策略**: 5种
- **导出API**: 10个
