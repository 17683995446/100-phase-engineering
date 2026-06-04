# Phase 26: 日志系统增强

## 阶段概述

**阶段名称**: 日志系统增强
**完成状态**: ✅ 已完成
**测试结果**: 34个测试用例全部通过
**系统总测试**: 442个测试全部通过

## 核心设计原则

遵循 **信息显式化公理**: 日志结构化、可追溯、可分析。所有日志信息必须明确、无歧义、可机器解析。

## 核心架构

### 日志级别

```python
class LogLevel(Enum):
    TRACE = 5      # 最详细级别
    DEBUG = 10     # 调试信息
    INFO = 20      # 一般信息
    WARNING = 30   # 警告信息
    ERROR = 40    # 错误信息
    CRITICAL = 50  # 严重错误
```

### 日志格式

```python
class LogFormat(Enum):
    TEXT = auto()      # 文本格式
    JSON = auto()      # JSON格式
    CSV = auto()       # CSV格式
    STRUCTURED = auto() # 结构化文本
```

### 日志目标

```python
class LogDestination(Enum):
    CONSOLE = auto()
    FILE = auto()
    CONSOLE_AND_FILE = auto()
```

## 主要组件

### 数据结构

#### LogEntry - 日志条目
包含完整的日志信息：
- 时间戳
- 日志级别
- 记录器名称
- 消息内容
- 上下文信息
- 模块/函数/行号
- 线程ID/进程ID
- 异常信息

#### LogContext - 日志上下文
线程本地上下文管理：
- 设置上下文键值对
- 获取当前上下文
- 清除上下文
- 自动合并到日志

### 格式化器

#### TextFormatter
- 可配置的格式模板
- 支持上下文格式化
- 异常堆栈格式化

#### JSONFormatter
- 结构化JSON输出
- 适合日志收集系统
- 支持自定义缩进

#### CSVFormatter
- 逗号分隔值
- 适合数据分析
- 字段引用

### 处理器

#### ConsoleHandler
- 彩色终端输出
- 支持ANSI颜色
- 标准输出/错误分流

#### FileHandler
- 文件日志输出
- 自动轮转（大小/时间）
- GZIP压缩旧日志
- 多备份保留

#### MemoryHandler
- 内存存储（测试用）
- 限制最大条目数
- 查询和过滤

### 记录器

#### StructuredLogger
- 多处理器支持
- 自动上下文合并
- 异常跟踪
- 线程安全

#### LoggerAdapter
- 上下文绑定的日志包装器
- 自动上下文注入
- 简化日志调用

#### LogAggregator
- 多日志器统一管理
- 动态级别控制
- 单例模式

### 工具

#### TimerLogger
- 上下文管理器
- 自动计时
- 成功/失败记录
- 性能分析

## 功能特性

### 1. 多格式支持
- 文本（开发调试）
- JSON（生产收集）
- CSV（数据分析）
- 结构化文本（混合）

### 2. 多目标输出
- 控制台（实时查看）
- 文件（持久存储）
- 内存（测试分析）

### 3. 自动轮转
- 基于大小轮转
- 自动压缩旧日志
- 多备份保留

### 4. 上下文管理
- 线程本地存储
- 自动上下文注入
- 链路追踪支持

### 5. 异常跟踪
- 自动堆栈信息
- 异常类型记录
- 完整错误链

### 6. 过滤器链
- 可扩展过滤器
- 多条件组合
- 动态控制

### 7. 性能计时
- 上下文管理器
- 自动耗时计算
- 成功失败区分

### 8. 线程安全
- 读写锁保护
- 多线程并发
- 无数据竞争

## 使用示例

### 基本使用

```python
from src.utils.structured_logging import get_logger, LogLevel, LogFormat

logger = get_logger("my_app", level=LogLevel.DEBUG, log_format=LogFormat.JSON)
logger.info("Application started", version="1.0.0")
logger.error("Database connection failed", host="localhost", port=5432)
```

### 上下文日志

```python
from src.utils.structured_logging import LogContext, get_logger

LogContext.set_context(task_id="task_123", user_id="user_456")
logger = get_logger()

logger.info("Processing request")
# 自动包含 task_id 和 user_id
```

### 计时操作

```python
from src.utils.structured_logging import TimerLogger, create_memory_logger

logger, handler = create_memory_logger("performance")

with TimerLogger(logger, "database query", query_id="q_001"):
    # 执行数据库查询
    time.sleep(0.1)

# 自动记录开始、完成/失败、耗时
```

### 文件日志轮转

```python
from src.utils.structured_logging import StructuredLogger, LogFormat, LogDestination

logger = StructuredLogger(
    name="production",
    level=LogLevel.INFO,
    log_format=LogFormat.JSON,
    destination=LogDestination.CONSOLE_AND_FILE,
    log_dir=Path("/var/log/myapp")
)

logger.info("Service started")
```

### JSON格式输出

```python
from src.utils.structured_logging import StructuredLogger, LogFormat

logger = StructuredLogger(
    name="json_logger",
    log_format=LogFormat.JSON
)

logger.info("Event processed",
    event_type="user_login",
    user_id=12345,
    ip_address="192.168.1.1"
)

# 输出:
# {
#   "timestamp": "2026-05-27T10:30:00",
#   "level": "INFO",
#   "logger": "json_logger",
#   "message": "Event processed",
#   "context": {
#     "event_type": "user_login",
#     "user_id": 12345,
#     "ip_address": "192.168.1.1"
#   }
# }
```

## 测试覆盖

| 测试类别 | 用例数 | 状态 |
|---------|--------|------|
| 数据结构 | 2 | ✅ |
| 上下文管理 | 4 | ✅ |
| 格式化器 | 4 | ✅ |
| 内存处理器 | 4 | ✅ |
| 结构化记录器 | 7 | ✅ |
| 日志聚合器 | 5 | ✅ |
| 计时日志 | 2 | ✅ |
| 全局记录器 | 2 | ✅ |
| 集成测试 | 3 | ✅ |
| 线程安全 | 1 | ✅ |
| **总计** | **34** | **✅** |

## 与现有模块集成

### 继承自
- [src/utils/logger.py](file:///workspace/src/utils/logger.py): 基础日志功能

### 为以下模块提供支持
- 所有Agent层模块
- 调度层模块
- 执行层模块
- 输入层模块

## 性能考虑

1. **避免频繁I/O**: 使用缓冲和异步
2. **控制日志级别**: 生产环境使用INFO+
3. **合理上下文**: 不要添加过多上下文
4. **JSON vs 文本**: JSON更适合机器解析

## 文件清单

| 文件路径 | 描述 |
|---------|------|
| [src/utils/structured_logging.py](file:///workspace/src/utils/structured_logging.py) | 结构化日志核心实现 |
| [test_structured_logging.py](file:///workspace/test_structured_logging.py) | 34个测试用例 |
| [src/utils/__init__.py](file:///workspace/src/utils/__init__.py) | 模块导出更新 |
| [PHASE_26_SUMMARY.md](file:///workspace/PHASE_26_SUMMARY.md) | 本阶段总结 |

## 下一阶段 (Phase 27)

可选方向：
- **指标收集系统** (Prometheus格式)
- **分布式追踪集成** (OpenTelemetry)
- **API接口层** (REST/GraphQL)
- **WebSocket通信层**
- **任务队列系统**

## 扩展建议

1. **异步日志**: 使用队列异步写入
2. **日志收集**: 集成ELK/Graylog
3. **告警集成**: 错误日志自动告警
4. **日志审计**: 关键操作审计日志
