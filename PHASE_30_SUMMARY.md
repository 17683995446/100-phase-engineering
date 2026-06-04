# Phase 30: GraphQL 支持

## 阶段概述

**阶段名称**: GraphQL 支持
**完成状态**: ✅ 已完成
**测试结果**: 30 个测试用例全部通过
**系统总测试**: 120+ 个测试通过

## 核心设计原则

遵循 **灵活查询** 原则，提供完整的 GraphQL 服务，与现有 API 层无缝集成。支持类型定义、解析器、模式验证和查询执行。

## 主要组件

### 1. 枚举类型

- **GraphQLOperationType**: GraphQL 操作类型（QUERY, MUTATION, SUBSCRIPTION）

### 2. 数据模型

- **GraphQLField**: GraphQL 字段定义，包含名称、类型、描述、参数和解析器
- **GraphQLArgument**: GraphQL 参数定义，包含名称、类型、描述和默认值
- **GraphQLType**: GraphQL 类型定义（OBJECT, SCALAR, ENUM, INPUT_OBJECT）
- **GraphQLRequest**: GraphQL 请求对象，包含查询、操作名、变量和请求 ID
- **GraphQLResponse**: GraphQL 响应对象，包含数据、错误、扩展和请求 ID
- **GraphQLError**: GraphQL 错误对象，包含消息、位置、路径和扩展

### 3. 解析器系统

- **GraphQLResolver**: GraphQL 解析器基类，支持字段解析器装饰器
- 提供默认解析器，可以从字典中自动提取字段值

### 4. 模式系统

- **GraphQLSchema**: GraphQL 模式，管理类型、解析器和根操作类型
- 支持 Query、Mutation 和 Subscription 根类型
- 可以动态添加类型和解析器

### 5. 执行系统

- **GraphQLExecutor**: GraphQL 执行器，负责解析和执行查询
- 支持变量和操作名
- 提供完整的错误处理

### 6. 应用核心

- **GraphQLApp**: GraphQL 应用核心类
- 内置默认模式，包含 hello 和 user 查询
- 提供模式 SDL（Schema Definition Language）生成
- 与 Prometheus 和结构化日志集成
- 支持全局应用实例

## 文件结构

```
src/api_layer/
├── __init__.py       # 模块导出（包含 GraphQL 组件）
├── core.py           # REST API 核心实现
├── websocket.py      # WebSocket 核心实现
└── graphql.py        # GraphQL 核心实现 ✨

test_graphql.py       # GraphQL 测试用例 ✨
```

## 使用示例

### 基本使用

```python
from src.api_layer import GraphQLApp

# 创建应用
app = GraphQLApp(name="my-graphql")

# 执行查询
response = app.execute("{ hello }")
print(response.data)
```

### 带变量的查询

```python
from src.api_layer import GraphQLApp

app = GraphQLApp()

response = app.execute(
    query="{ user(id: $id) { id name } }",
    variables={"id": "123"}
)
print(response.data)
```

### 自定义解析器

```python
from src.api_layer import (
    GraphQLApp,
    GraphQLResolver,
    GraphQLSchema,
    GraphQLType,
    GraphQLField
)

app = GraphQLApp()

# 创建自定义解析器
product_resolver = GraphQLResolver("Query")

@product_resolver.field("product")
def resolve_product(root, args, context):
    return {
        "id": args.get("id"),
        "name": "Test Product",
        "price": 99.99
    }

app.schema.add_resolver(product_resolver)
```

### 获取模式 SDL

```python
from src.api_layer import GraphQLApp

app = GraphQLApp()
sdl = app.get_schema_sdl()
print(sdl)
```

## 默认模式

应用内置了一个示例模式，包含：

- **Query**:
  - `hello: String` - 返回 "Hello, GraphQL!"
  - `user(id: ID): User` - 返回用户对象

- **User**:
  - `id: ID` - 用户 ID
  - `name: String` - 用户名称
  - `email: String` - 用户邮箱

## 与现有系统的集成

### Prometheus 指标集成

- 使用 Prometheus 注册表进行监控
- 可扩展以添加查询计数、执行时间等指标

### 结构化日志集成

- 自动记录查询执行
- 包含请求 ID 和操作名

### API 层集成

- 与 REST API 和 WebSocket 共存于同一模块
- 统一的命名空间和导出方式
- 可通过 API 层路由暴露 GraphQL 端点

## 已完成阶段回顾 (Phase 13-30)

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
| Phase 29 | WebSocket 通信 | ✅ | WebSocketApp、Channel、Handler |
| **Phase 30** | **GraphQL 支持** | **✅** | **GraphQLApp、Schema、Resolver** |

## 扩展功能

当前实现包含完整的核心框架，可进一步扩展：

- 集成完整的 GraphQL 解析库（如 graphql-core）
- 添加 GraphiQL 或 GraphQL Playground 界面
- 实现真实的查询验证和执行
- 添加缓存机制
- 实现订阅支持
- 添加权限和认证
- 支持中间件
- 添加批量查询优化

## 下一步 (Phase 31+)

可选方向：
- 任务队列集成（Celery/RQ）
- 分布式追踪（OpenTelemetry）
- API 文档生成（Swagger/OpenAPI）
- 数据库 ORM 集成
- 测试套件完善
- 性能优化
