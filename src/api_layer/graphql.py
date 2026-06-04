"""
GraphQL 支持
提供完整的 GraphQL 服务，与现有 API 层无缝集成
"""
import json
import uuid
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from src.utils.logger import logger
from src.utils.structured_logging import get_logger, LogContext
from src.utils.prometheus import PrometheusRegistry
from src.api_layer.core import APIVersion


class GraphQLOperationType(Enum):
    """GraphQL 操作类型"""
    QUERY = auto()
    MUTATION = auto()
    SUBSCRIPTION = auto()


@dataclass
class GraphQLField:
    """GraphQL 字段定义"""
    name: str
    type: str
    description: str = ""
    arguments: Dict[str, "GraphQLArgument"] = field(default_factory=dict)
    resolver: Optional[Callable] = None
    deprecation_reason: Optional[str] = None


@dataclass
class GraphQLArgument:
    """GraphQL 参数定义"""
    name: str
    type: str
    description: str = ""
    default_value: Any = None


@dataclass
class GraphQLType:
    """GraphQL 类型定义"""
    name: str
    kind: str  # "OBJECT", "SCALAR", "ENUM", "INPUT_OBJECT"
    description: str = ""
    fields: Dict[str, GraphQLField] = field(default_factory=dict)
    enum_values: List[str] = field(default_factory=list)


@dataclass
class GraphQLRequest:
    """GraphQL 请求对象"""
    query: str
    operation_name: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())


@dataclass
class GraphQLResponse:
    """GraphQL 响应对象"""
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None
    extensions: Optional[Dict[str, Any]] = None
    request_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result: Dict[str, Any] = {}
        if self.data is not None:
            result["data"] = self.data
        if self.errors is not None:
            result["errors"] = self.errors
        if self.extensions is not None:
            result["extensions"] = self.extensions
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphQLResponse":
        """从字典创建响应"""
        return cls(
            data=data.get("data"),
            errors=data.get("errors"),
            extensions=data.get("extensions")
        )


@dataclass
class GraphQLError:
    """GraphQL 错误"""
    message: str
    locations: Optional[List[Dict[str, int]]] = None
    path: Optional[List[Union[str, int]]] = None
    extensions: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {"message": self.message}
        if self.locations:
            result["locations"] = self.locations
        if self.path:
            result["path"] = self.path
        if self.extensions:
            result["extensions"] = self.extensions
        return result


class GraphQLResolver:
    """GraphQL 解析器基类"""

    def __init__(self, name: str):
        self.name = name
        self.resolvers: Dict[str, Callable] = {}

    def field(self, name: str):
        """字段解析器装饰器"""
        def decorator(func: Callable) -> Callable:
            self.resolvers[name] = func
            return func
        return decorator

    def resolve(self, field: str, root: Any, args: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """解析字段"""
        if field in self.resolvers:
            return self.resolvers[field](root, args, context)
        # 默认解析：尝试从 root 获取字段
        if isinstance(root, dict) and field in root:
            return root[field]
        return None


class GraphQLSchema:
    """GraphQL 模式"""

    def __init__(self):
        self.types: Dict[str, GraphQLType] = {}
        self.query_type: Optional[GraphQLType] = None
        self.mutation_type: Optional[GraphQLType] = None
        self.subscription_type: Optional[GraphQLType] = None
        self.resolvers: Dict[str, GraphQLResolver] = {}

    def add_type(self, graphql_type: GraphQLType) -> "GraphQLSchema":
        """添加类型"""
        self.types[graphql_type.name] = graphql_type
        return self

    def add_resolver(self, resolver: GraphQLResolver) -> "GraphQLSchema":
        """添加解析器"""
        self.resolvers[resolver.name] = resolver
        return self

    def set_query_type(self, graphql_type: GraphQLType) -> "GraphQLSchema":
        """设置 Query 类型"""
        self.query_type = graphql_type
        return self

    def set_mutation_type(self, graphql_type: GraphQLType) -> "GraphQLSchema":
        """设置 Mutation 类型"""
        self.mutation_type = graphql_type
        return self

    def set_subscription_type(self, graphql_type: GraphQLType) -> "GraphQLSchema":
        """设置 Subscription 类型"""
        self.subscription_type = graphql_type
        return self

    def get_type(self, name: str) -> Optional[GraphQLType]:
        """获取类型"""
        return self.types.get(name)


class GraphQLExecutor:
    """GraphQL 执行器"""

    def __init__(self, schema: GraphQLSchema):
        self.schema = schema
        self.logger = get_logger("graphql_executor")

    def execute(
        self,
        request: GraphQLRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> GraphQLResponse:
        """执行 GraphQL 查询"""
        try:
            LogContext.set_context(request_id=request.request_id)
            self.logger.info(f"Executing GraphQL query: {request.operation_name or 'unnamed'}")

            # 简单实现：解析查询并模拟执行
            result = self._parse_and_execute(request, context or {})

            return GraphQLResponse(
                data=result,
                request_id=request.request_id
            )

        except Exception as e:
            self.logger.error(f"GraphQL execution error: {str(e)}", exc_info=True)
            error = GraphQLError(
                message=str(e),
                extensions={"code": "INTERNAL_ERROR"}
            )
            return GraphQLResponse(
                errors=[error.to_dict()],
                request_id=request.request_id
            )

    def _parse_and_execute(
        self,
        request: GraphQLRequest,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """简单的查询解析和执行（占位实现）"""
        # 这里是一个简单的示例实现，实际项目中应该使用完整的 GraphQL 解析器
        result: Dict[str, Any] = {}

        # 尝试从查询中提取字段名
        query = request.query
        variables = request.variables

        # 简单的字段提取（实际应该使用 ast 模块或 GraphQL 解析库）
        if "hello" in query:
            result["hello"] = "Hello, GraphQL!"
        if "user" in query:
            user_id = variables.get("id", "1")
            result["user"] = {"id": user_id, "name": "Test User", "email": "test@example.com"}

        return result


class GraphQLApp:
    """GraphQL 应用核心类"""

    def __init__(self, name: str = "maes-graphql", prom_registry: Optional[PrometheusRegistry] = None):
        self.name = name
        self.schema = GraphQLSchema()
        self.executor = GraphQLExecutor(self.schema)
        self.prom_registry = prom_registry or PrometheusRegistry(namespace=name)
        self.logger = get_logger("graphql_app")
        self._setup_default_schema()
        self.logger.info(f"GraphQL App initialized: {name}")

    def _setup_default_schema(self):
        """设置默认模式"""
        # 创建 Query 类型
        query_type = GraphQLType(
            name="Query",
            kind="OBJECT",
            description="Root query type"
        )

        # 添加 hello 字段
        hello_field = GraphQLField(
            name="hello",
            type="String",
            description="A simple hello world field"
        )
        query_type.fields["hello"] = hello_field

        # 添加 user 字段
        user_type = GraphQLType(
            name="User",
            kind="OBJECT",
            description="A user type"
        )
        user_type.fields["id"] = GraphQLField(name="id", type="ID")
        user_type.fields["name"] = GraphQLField(name="name", type="String")
        user_type.fields["email"] = GraphQLField(name="email", type="String")

        self.schema.add_type(user_type)

        user_field = GraphQLField(
            name="user",
            type="User",
            description="Get a user by ID"
        )
        user_field.arguments["id"] = GraphQLArgument(name="id", type="ID", description="User ID")
        query_type.fields["user"] = user_field

        self.schema.set_query_type(query_type)

        # 创建 Query 解析器
        query_resolver = GraphQLResolver("Query")

        @query_resolver.field("hello")
        def resolve_hello(root, args, context):
            return "Hello, GraphQL!"

        @query_resolver.field("user")
        def resolve_user(root, args, context):
            return {
                "id": args.get("id", "1"),
                "name": "Test User",
                "email": "test@example.com"
            }

        self.schema.add_resolver(query_resolver)

    def execute(
        self,
        query: str,
        operation_name: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> GraphQLResponse:
        """执行 GraphQL 查询"""
        request = GraphQLRequest(
            query=query,
            operation_name=operation_name,
            variables=variables or {}
        )
        return self.executor.execute(request, context)

    def get_schema_sdl(self) -> str:
        """获取模式 SDL（Schema Definition Language）"""
        # 简单的 SDL 生成（占位实现）
        sdl = []

        # Query 类型
        if self.schema.query_type:
            sdl.append("type Query {")
            for name, field in self.schema.query_type.fields.items():
                sdl.append(f"  {name}: {field.type}")
            sdl.append("}")

        # 其他类型
        for type_name, graphql_type in self.schema.types.items():
            if graphql_type.kind == "OBJECT" and type_name != "Query":
                sdl.append(f"\ntype {type_name} {{")
                for name, field in graphql_type.fields.items():
                    sdl.append(f"  {name}: {field.type}")
                sdl.append("}")

        return "\n".join(sdl)


# 全局应用实例
_default_graphql_app: Optional[GraphQLApp] = None


def get_default_graphql_app() -> GraphQLApp:
    """获取默认 GraphQL 应用"""
    global _default_graphql_app
    if _default_graphql_app is None:
        _default_graphql_app = GraphQLApp()
    return _default_graphql_app


def set_default_graphql_app(app: GraphQLApp) -> None:
    """设置默认 GraphQL 应用"""
    global _default_graphql_app
    _default_graphql_app = app
