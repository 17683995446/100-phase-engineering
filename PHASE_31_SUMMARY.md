# Phase 31: API 文档系统 (Swagger/OpenAPI)

## 阶段概述

**阶段名称**: API 文档系统
**完成状态**: ✅ 已完成
**测试结果**: 30 个测试用例全部通过
**系统总测试**: 257+ 个测试通过

## 核心设计原则

遵循 **文档即代码** 原则，提供完整的 Swagger/OpenAPI 文档生成功能，支持 REST API、WebSocket 和 GraphQL 的统一文档管理。

## 主要组件

### 1. 枚举类型

- **DocumentationType**: 文档类型枚举
  - SWAGGER: Swagger 2.0 格式
  - OPENAPI_3: OpenAPI 3.x 格式
  - REDOC: ReDoc 格式
  - RAPIDOC: RapiDoc 格式

### 2. 数据模型

- **APIParameter**: API 参数定义
  - name: 参数名称
  - in_: 参数位置 (path/query/header/cookie)
  - type: 参数类型
  - description: 描述
  - required: 是否必填
  - default: 默认值
  - enum: 枚举值

- **APIRequestBody**: API 请求体
- **APIResponse**: API 响应定义
- **APIOperation**: API 操作定义
  - path: 路径
  - method: HTTP 方法
  - summary: 摘要
  - description: 描述
  - operation_id: 操作 ID
  - tags: 标签
  - parameters: 参数列表
  - request_body: 请求体
  - responses: 响应字典

- **APITag**: API 标签
- **APIInfo**: API 信息（标题、版本、描述等）
- **APIServer**: API 服务器
- **WebSocketEndpoint**: WebSocket 端点
- **GraphQLEndpoint**: GraphQL 端点

### 3. 文档系统

- **APIDocumentation**: API 文档核心类
  - 管理服务器、标签、操作
  - 支持 WebSocket 和 GraphQL 端点
  - 提供 OpenAPI 3 和 Swagger 2.0 格式输出
  - JSON 和 YAML 格式支持

- **APIDocumentationBuilder**: 文档构建器
  - 链式调用 API
  - 从 Route 对象自动导入
  - 预配置默认文档

### 4. 全局实例

- **get_default_api_doc()**: 获取默认文档
- **set_default_api_doc()**: 设置默认文档

## 文件结构

```
src/api_layer/
├── __init__.py          # 模块导出（包含文档组件）
├── core.py              # REST API 核心实现
├── websocket.py         # WebSocket 核心实现
├── graphql.py           # GraphQL 核心实现
└── documentation.py     # 文档系统核心实现 ✨

test_documentation.py    # 文档系统测试用例 ✨
```

## 与现有系统的集成

### API 层集成

- 与 Phase 28 (REST API) 完美集成
- 与 Phase 29 (WebSocket) 完美集成
- 与 Phase 30 (GraphQL) 完美集成
- 可以从 Route 对象自动导入

### 结构化日志

- 自动记录文档操作
- 包含请求上下文

## 使用示例

### 基本使用

```python
from src.api_layer import (
    APIDocumentationBuilder,
    APITag,
    APIOperation,
    APIResponse,
    HTTPMethod
)

# 使用构建器
doc = (
    APIDocumentationBuilder(title="My API", version="1.0")
    .with_server("http://localhost:8000", "Local server")
    .with_tag("users", "User operations")
    .build()
)

# 添加操作
doc.add_operation(APIOperation(
    path="/users",
    method=HTTPMethod.GET,
    summary="Get all users",
    tags=["users"],
    responses={
        "200": APIResponse(status_code="200", description="Success")
    }
))

# 生成 OpenAPI JSON
openapi_json = doc.to_json()

# 生成 Swagger JSON
swagger_json = doc.to_json(DocumentationType.SWAGGER)

# 生成 YAML
openapi_yaml = doc.to_yaml()
```

### 从 Route 导入

```python
from src.api_layer import APIDocumentationBuilder, Route, HTTPMethod

# 创建路由
route = Route(
    path="/users/{id}",
    method=HTTPMethod.GET,
    handler=get_user_handler,
    description="Get user by ID"
)

# 导入到文档
doc = (
    APIDocumentationBuilder()
    .with_route(route)
    .build()
)
```

### 完整示例

```python
from src.api_layer import (
    APIDocumentation,
    APIInfo,
    APIServer,
    APITag,
    APIOperation,
    APIParameter,
    APIResponse,
    HTTPMethod,
    WebSocketEndpoint,
    GraphQLEndpoint,
    DocumentationType
)

# 创建文档
doc = APIDocumentation(
    info=APIInfo(
        title="Multi-Agent API",
        version="1.0.0",
        description="Complete API for multi-agent system"
    )
)

# 添加服务器
doc.add_server(APIServer(
    url="https://api.example.com/v1",
    description="Production"
))
doc.add_server(APIServer(
    url="http://localhost:8000",
    description="Local dev"
))

# 添加标签
doc.add_tag(APITag(name="agents", description="Agent management"))
doc.add_tag(APITag(name="tasks", description="Task management"))

# 添加操作
doc.add_operation(APIOperation(
    path="/agents",
    method=HTTPMethod.GET,
    summary="Get all agents",
    tags=["agents"],
    parameters=[
        APIParameter(name="page", in_="query", type="integer", description="Page number")
    ],
    responses={
        "200": APIResponse(status_code="200", description="Success"),
        "500": APIResponse(status_code="500", description="Error")
    }
))

# 添加 WebSocket
doc.add_websocket_endpoint(WebSocketEndpoint(
    path="/ws/events",
    description="Real-time event stream"
))

# 添加 GraphQL
doc.set_graphql_endpoint(GraphQLEndpoint(
    path="/graphql",
    description="GraphQL API"
))

# 输出文档
print("OpenAPI 3 JSON:")
print(doc.to_json())
print("\nSwagger 2 JSON:")
print(doc.to_json(DocumentationType.SWAGGER))
print("\nYAML:")
print(doc.to_yaml())
```

## 已完成阶段回顾 (Phase 13-31)

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
| Phase 30 | GraphQL 支持 | ✅ | GraphQLApp、Schema、Resolver |
| **Phase 31** | **API 文档系统** | **✅** | **APIDocumentation、Builder、OpenAPI** |

## 下一步 (Phase 32+)

可选方向：
- 任务队列集成（Celery/RQ）
- 分布式追踪（OpenTelemetry）
- 数据库 ORM 集成
- 性能优化与基准测试
- 部署与容器化
- 安全与认证
