"""
API 文档系统
提供 Swagger/OpenAPI 文档生成，支持 REST API、WebSocket 和 GraphQL
"""
import json
import uuid
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.logger import logger
from src.utils.structured_logging import get_logger
from src.utils.prometheus import PrometheusRegistry
from src.api_layer.core import HTTPMethod, HTTPStatus, APIVersion, Route


class DocumentationType(Enum):
    """文档类型"""
    SWAGGER = auto()
    OPENAPI_3 = auto()
    REDOC = auto()
    RAPIDOC = auto()


@dataclass
class APIParameter:
    """API 参数"""
    name: str
    in_: str  # "path", "query", "header", "cookie"
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None


@dataclass
class APIRequestBody:
    """API 请求体"""
    content_type: str = "application/json"
    schema: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    required: bool = False


@dataclass
class APIResponse:
    """API 响应定义"""
    status_code: str
    description: str
    content_type: str = "application/json"
    schema: Optional[Dict[str, Any]] = None


@dataclass
class APIOperation:
    """API 操作定义"""
    path: str
    method: HTTPMethod
    summary: str = ""
    description: str = ""
    operation_id: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[APIParameter] = field(default_factory=list)
    request_body: Optional[APIRequestBody] = None
    responses: Dict[str, APIResponse] = field(default_factory=dict)
    deprecated: bool = False

    def __post_init__(self):
        if not self.operation_id:
            self.operation_id = f"{self.method.name.lower()}_{self.path.replace('/', '_').replace('{', '').replace('}', '')}"


@dataclass
class APITag:
    """API 标签"""
    name: str
    description: str = ""


@dataclass
class APIInfo:
    """API 信息"""
    title: str = "Multi-Agent API"
    version: str = "1.0.0"
    description: str = "Multi-Agent Engineering System API"
    terms_of_service: Optional[str] = None
    contact: Optional[Dict[str, str]] = None
    license: Optional[Dict[str, str]] = None


@dataclass
class APIServer:
    """API 服务器"""
    url: str
    description: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebSocketEndpoint:
    """WebSocket 端点"""
    path: str
    description: str = ""
    protocols: List[str] = field(default_factory=list)
    message_types: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GraphQLEndpoint:
    """GraphQL 端点"""
    path: str = "/graphql"
    description: str = "GraphQL API endpoint"
    schema_sdl: Optional[str] = None


class APIDocumentation:
    """API 文档"""

    def __init__(self, info: Optional[APIInfo] = None):
        self.info = info or APIInfo()
        self.servers: List[APIServer] = []
        self.tags: List[APITag] = []
        self.operations: List[APIOperation] = []
        self.websocket_endpoints: List[WebSocketEndpoint] = []
        self.graphql_endpoint: Optional[GraphQLEndpoint] = None
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger("api_documentation")

    def add_server(self, server: APIServer) -> "APIDocumentation":
        """添加服务器"""
        self.servers.append(server)
        return self

    def add_tag(self, tag: APITag) -> "APIDocumentation":
        """添加标签"""
        self.tags.append(tag)
        return self

    def add_operation(self, operation: APIOperation) -> "APIDocumentation":
        """添加操作"""
        self.operations.append(operation)
        self.logger.debug(f"Added API operation: {operation.method} {operation.path}")
        return self

    def add_websocket_endpoint(self, endpoint: WebSocketEndpoint) -> "APIDocumentation":
        """添加 WebSocket 端点"""
        self.websocket_endpoints.append(endpoint)
        return self

    def set_graphql_endpoint(self, endpoint: GraphQLEndpoint) -> "APIDocumentation":
        """设置 GraphQL 端点"""
        self.graphql_endpoint = endpoint
        return self

    def add_schema(self, name: str, schema: Dict[str, Any]) -> "APIDocumentation":
        """添加模式"""
        self.schemas[name] = schema
        return self

    def to_openapi_dict(self) -> Dict[str, Any]:
        """转换为 OpenAPI 3 格式"""
        result: Dict[str, Any] = {
            "openapi": "3.0.3",
            "info": {
                "title": self.info.title,
                "version": self.info.version,
                "description": self.info.description
            },
            "servers": [],
            "paths": {},
            "components": {
                "schemas": self.schemas
            },
            "tags": []
        }

        if self.info.contact:
            result["info"]["contact"] = self.info.contact
        if self.info.license:
            result["info"]["license"] = self.info.license

        # 服务器
        for server in self.servers:
            server_dict = {"url": server.url}
            if server.description:
                server_dict["description"] = server.description
            if server.variables:
                server_dict["variables"] = server.variables
            result["servers"].append(server_dict)

        # 标签
        for tag in self.tags:
            result["tags"].append({
                "name": tag.name,
                "description": tag.description
            })

        # 路径和操作
        paths: Dict[str, Dict[str, Any]] = {}
        for op in self.operations:
            if op.path not in paths:
                paths[op.path] = {}
            paths[op.path][op.method.name.lower()] = self._operation_to_dict(op)
        result["paths"] = paths

        # WebSocket 和 GraphQL 扩展
        if self.websocket_endpoints or self.graphql_endpoint:
            result["x-extension"] = {}
            if self.websocket_endpoints:
                result["x-extension"]["websockets"] = [
                    {"path": ws.path, "description": ws.description}
                    for ws in self.websocket_endpoints
                ]
            if self.graphql_endpoint:
                result["x-extension"]["graphql"] = {
                    "path": self.graphql_endpoint.path,
                    "description": self.graphql_endpoint.description
                }

        return result

    def _operation_to_dict(self, op: APIOperation) -> Dict[str, Any]:
        """操作转换为字典"""
        result: Dict[str, Any] = {
            "operationId": op.operation_id,
            "tags": op.tags,
            "responses": {}
        }
        if op.summary:
            result["summary"] = op.summary
        if op.description:
            result["description"] = op.description
        if op.deprecated:
            result["deprecated"] = True

        # 参数
        if op.parameters:
            result["parameters"] = [
                {
                    "name": p.name,
                    "in": p.in_,
                    "description": p.description,
                    "required": p.required,
                    "schema": {"type": p.type}
                }
                for p in op.parameters
            ]

        # 请求体
        if op.request_body:
            result["requestBody"] = {
                "required": op.request_body.required,
                "content": {
                    op.request_body.content_type: {
                        "schema": op.request_body.schema
                    }
                }
            }
            if op.request_body.description:
                result["requestBody"]["description"] = op.request_body.description

        # 响应
        for status_code, resp in op.responses.items():
            resp_dict: Dict[str, Any] = {"description": resp.description}
            if resp.schema:
                resp_dict["content"] = {
                    resp.content_type: {"schema": resp.schema}
                }
            result["responses"][status_code] = resp_dict

        return result

    def to_swagger_dict(self) -> Dict[str, Any]:
        """转换为 Swagger 2.0 格式"""
        openapi = self.to_openapi_dict()
        # 简化的转换（实际项目应该使用完整的转换逻辑）
        swagger = {
            "swagger": "2.0",
            "info": openapi["info"],
            "host": "localhost",
            "basePath": "/",
            "paths": openapi.get("paths", {}),
            "definitions": openapi.get("components", {}).get("schemas", {})
        }
        return swagger

    def to_json(self, doc_type: DocumentationType = DocumentationType.OPENAPI_3) -> str:
        """转换为 JSON"""
        if doc_type == DocumentationType.SWAGGER:
            return json.dumps(self.to_swagger_dict(), indent=2, ensure_ascii=False)
        else:
            return json.dumps(self.to_openapi_dict(), indent=2, ensure_ascii=False)

    def to_yaml(self, doc_type: DocumentationType = DocumentationType.OPENAPI_3) -> str:
        """转换为 YAML"""
        import json
        try:
            import yaml
            if doc_type == DocumentationType.SWAGGER:
                return yaml.dump(self.to_swagger_dict(), allow_unicode=True)
            else:
                return yaml.dump(self.to_openapi_dict(), allow_unicode=True)
        except ImportError:
            self.logger.warning("PyYAML not available, falling back to JSON")
            return self.to_json(doc_type)


class APIDocumentationBuilder:
    """API 文档构建器"""

    def __init__(self, title: str = "Multi-Agent API", version: str = "1.0.0"):
        self.doc = APIDocumentation(
            info=APIInfo(title=title, version=version)
        )

    def with_server(self, url: str, description: str = "") -> "APIDocumentationBuilder":
        """添加服务器"""
        self.doc.add_server(APIServer(url=url, description=description))
        return self

    def with_tag(self, name: str, description: str = "") -> "APIDocumentationBuilder":
        """添加标签"""
        self.doc.add_tag(APITag(name=name, description=description))
        return self

    def with_route(self, route: Route) -> "APIDocumentationBuilder":
        """从 Route 对象添加操作"""
        responses = {
            "200": APIResponse(
                status_code="200",
                description="Successful response"
            ),
            "400": APIResponse(
                status_code="400",
                description="Bad request"
            ),
            "500": APIResponse(
                status_code="500",
                description="Internal server error"
            )
        }
        operation = APIOperation(
            path=route.path,
            method=route.method,
            summary=route.name or f"{route.method} {route.path}",
            description=route.description or "",
            tags=[],
            responses=responses
        )
        self.doc.add_operation(operation)
        return self

    def build(self) -> APIDocumentation:
        """构建文档"""
        return self.doc


# 全局文档实例
_default_api_doc: Optional[APIDocumentation] = None


def get_default_api_doc() -> APIDocumentation:
    """获取默认 API 文档"""
    global _default_api_doc
    if _default_api_doc is None:
        _default_api_doc = (
            APIDocumentationBuilder(title="Multi-Agent Engineering API", version="1.0.0")
            .with_server("http://localhost:8000", "Local development server")
            .with_tag("agents", "Agent management operations")
            .with_tag("tasks", "Task management operations")
            .with_tag("monitoring", "Monitoring and metrics")
            .build()
        )
    return _default_api_doc


def set_default_api_doc(doc: APIDocumentation) -> None:
    """设置默认 API 文档"""
    global _default_api_doc
    _default_api_doc = doc
