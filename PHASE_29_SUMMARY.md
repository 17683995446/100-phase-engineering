# Phase 29: WebSocket 通信支持

## 阶段概述

**阶段名称**: WebSocket 通信支持
**完成状态**: ✅ 已完成
**测试结果**: 31 个测试用例全部通过
**系统总测试**: 197+ 个测试通过

## 核心设计原则

遵循 **实时双向通信** 原则，提供与现有 API 层完美集成的 WebSocket 支持。

## 主要组件

### 1. 枚举类型

- **WebSocketOp**: WebSocket 操作类型（CONNECT、DISCONNECT、MESSAGE、ERROR、PING、PONG）
- **WebSocketStatus**: WebSocket 连接状态（CONNECTING、OPEN、CLOSING、CLOSED）

### 2. 数据模型

- **WebSocketMessage**: WebSocket 消息对象
  - 支持 JSON 序列化/反序列化
  - 包含操作类型、数据、消息 ID、时间戳、错误信息、元数据
- **WebSocketConnection**: WebSocket 连接对象
  - 管理连接状态
  - 包含订阅信息、元数据、最后活动时间

### 3. 处理器系统

- **WebSocketHandler**: WebSocket 处理器基类
  - `on_connect(connection)`: 连接建立时调用
  - `on_message(connection, message)`: 收到消息时调用
  - `on_disconnect(connection)`: 连接断开时调用
  - `on_error(connection, error)`: 错误发生时调用
- **EchoHandler**: 简单的 Echo 处理器，原样返回消息
- **BroadcastHandler**: 广播处理器，支持向所有连接发送消息

### 4. 频道系统

- **WebSocketChannel**: WebSocket 频道，用于发布订阅模式
  - 支持订阅/取消订阅
  - 管理订阅者列表

### 5. 路由系统

- **WebSocketRouter**: WebSocket 路由系统
  - 管理路由和频道
  - 支持版本化路径（/v1/path 和 /path）

### 6. 应用核心

- **WebSocketApp**: WebSocket 应用核心类
  - 集成路由、连接管理、指标收集
  - 内置默认路由（/echo 和 /broadcast）
  - 自动记录 Prometheus 指标
  - 提供连接统计信息

## 文件结构

```
src/api_layer/
├── __init__.py       # 模块导出（包含 WebSocket 组件）
├── core.py           # REST API 核心实现
└── websocket.py      # WebSocket 核心实现 ✨

test_websocket.py     # WebSocket 测试用例 ✨
example_api_layer.py  # API 层使用示例
```

## 与现有系统的集成

### Prometheus 指标集成

- `websocket_connections`: 当前连接数（Gauge）
- `websocket_messages_total`: 消息总数（Counter）
- `websocket_errors_total`: 错误总数（Counter）

### 结构化日志集成

- 自动记录连接建立、断开、消息处理
- 包含请求 ID、方法、路径等上下文信息

## 使用示例

### 基本使用

```python
from src.api_layer import (
    WebSocketApp,
    WebSocketMessage,
    create_text_message,
    create_error_message
)

# 创建应用
app = WebSocketApp(name="my-app")

# 处理连接
conn = app.handle_connect("/echo")

# 发送和接收消息
msg = create_text_message({"hello": "world"})
response = app.handle_message(conn, msg)

# 断开连接
app.handle_disconnect(conn)
```

### 自定义处理器

```python
from src.api_layer import WebSocketHandler, WebSocketMessage, WebSocketApp

class MyHandler(WebSocketHandler):
    def on_connect(self, connection):
        return WebSocketMessage(
            op=WebSocketOp.MESSAGE,
            data={"status": "connected"}
        )

    def on_message(self, connection, message):
        return WebSocketMessage(
            op=WebSocketOp.MESSAGE,
            data={"received": message.data}
        )

app = WebSocketApp()
app.add_route("/my-path", MyHandler())
```

### 频道订阅

```python
from src.api_layer import WebSocketApp

app = WebSocketApp()
channel = app.router.get_or_create_channel("updates")

# 订阅
channel.subscribe("conn-1")

# 取消订阅
channel.unsubscribe("conn-1")
```

## 已完成阶段回顾 (Phase 13-29)

| 阶段 | 名称 | 状态 | 关键组件 |
|------|------|------|---------|
| Phase 13 | 链路追踪 | ✅ | ChainID、Span |
| Phase 14 | Agent 角色 | ✅ | AgentRoles、Registry |
| Phase 15 | 工作流编排 | ✅ | WorkflowEngine |
| Phase 16 | 协作协议 | ✅ | MessageProtocol |
| Phase 17 | 任务分发与负载均衡 | ✅ | TaskDispatcher |
| Phase 18 | 状态同步 | ✅ | StateSync |
| Phase 19 | 监控与告警 | ✅ | MetricsRegistry、AlertManager |
| Phase 20 | 系统集成与协调 | ✅ | SystemCoordinator |
| Phase 21 | 输入层增强 | ✅ | TaskValidator |
| Phase 22 | 代码解析 | ✅ | EnhancedASTProcessor |
| Phase 23 | Agent 能力增强 | ✅ | AgentLearningEngine |
| Phase 24 | 配置与持久化 | ✅ | ConfigPersistence |
| Phase 25 | 缓存管理 | ✅ | CacheManager |
| Phase 26 | 日志系统增强 | ✅ | StructuredLogger |
| Phase 27 | Prometheus 指标 | ✅ | PrometheusRegistry |
| Phase 28 | API 接口层 | ✅ | APIApp、Route、Middleware |
| **Phase 29** | **WebSocket 通信** | **✅** | **WebSocketApp、Channel、Handler** |

## 下一步 (Phase 30+)

可选方向:
- GraphQL 支持
- 任务队列集成（Celery/RQ）
- 分布式追踪（OpenTelemetry）
- API 文档生成（Swagger/OpenAPI）
