"""
Tests for API 文档系统 (Phase 31)
"""
import pytest
import json

from src.api_layer import (
    DocumentationType,
    APIParameter,
    APIRequestBody,
    APIResponse,
    APIOperation,
    APITag,
    APIInfo,
    APIServer,
    WebSocketEndpoint,
    GraphQLEndpoint,
    APIDocumentation,
    APIDocumentationBuilder,
    get_default_api_doc,
    set_default_api_doc,
    HTTPMethod,
    Route
)


class TestDataModels:
    """测试数据模型"""

    def test_api_parameter(self):
        """测试 API 参数"""
        param = APIParameter(
            name="user_id",
            in_="path",
            type="string",
            description="User ID",
            required=True
        )
        assert param.name == "user_id"
        assert param.in_ == "path"
        assert param.required is True

    def test_api_request_body(self):
        """测试 API 请求体"""
        body = APIRequestBody(
            content_type="application/json",
            schema={"type": "object"},
            required=True
        )
        assert body.content_type == "application/json"
        assert body.required is True

    def test_api_response(self):
        """测试 API 响应"""
        resp = APIResponse(
            status_code="200",
            description="Success",
            schema={"type": "object"}
        )
        assert resp.status_code == "200"
        assert resp.description == "Success"

    def test_api_operation(self):
        """测试 API 操作"""
        op = APIOperation(
            path="/users/{id}",
            method=HTTPMethod.GET,
            summary="Get user by ID",
            tags=["users"]
        )
        assert op.path == "/users/{id}"
        assert op.method == HTTPMethod.GET
        assert "users" in op.tags
        assert op.operation_id != ""

    def test_api_tag(self):
        """测试 API 标签"""
        tag = APITag(
            name="users",
            description="User management operations"
        )
        assert tag.name == "users"

    def test_api_info(self):
        """测试 API 信息"""
        info = APIInfo(
            title="My API",
            version="2.0.0",
            description="Test API"
        )
        assert info.title == "My API"
        assert info.version == "2.0.0"

    def test_api_server(self):
        """测试 API 服务器"""
        server = APIServer(
            url="https://api.example.com",
            description="Production server"
        )
        assert server.url == "https://api.example.com"

    def test_websocket_endpoint(self):
        """测试 WebSocket 端点"""
        ws = WebSocketEndpoint(
            path="/ws/chat",
            description="Chat WebSocket"
        )
        assert ws.path == "/ws/chat"

    def test_graphql_endpoint(self):
        """测试 GraphQL 端点"""
        gql = GraphQLEndpoint(
            path="/graphql",
            schema_sdl="type Query { hello: String }"
        )
        assert gql.path == "/graphql"


class TestAPIDocumentation:
    """测试 API 文档"""

    def test_creation(self):
        """测试文档创建"""
        info = APIInfo(title="Test API", version="1.0")
        doc = APIDocumentation(info=info)
        assert doc.info.title == "Test API"
        assert len(doc.operations) == 0

    def test_add_server(self):
        """测试添加服务器"""
        doc = APIDocumentation()
        server = APIServer(url="http://localhost:8000")
        doc.add_server(server)
        assert len(doc.servers) == 1

    def test_add_tag(self):
        """测试添加标签"""
        doc = APIDocumentation()
        tag = APITag(name="users")
        doc.add_tag(tag)
        assert len(doc.tags) == 1

    def test_add_operation(self):
        """测试添加操作"""
        doc = APIDocumentation()
        op = APIOperation(path="/users", method=HTTPMethod.GET)
        doc.add_operation(op)
        assert len(doc.operations) == 1

    def test_add_websocket(self):
        """测试添加 WebSocket"""
        doc = APIDocumentation()
        ws = WebSocketEndpoint(path="/ws")
        doc.add_websocket_endpoint(ws)
        assert len(doc.websocket_endpoints) == 1

    def test_set_graphql(self):
        """测试设置 GraphQL"""
        doc = APIDocumentation()
        gql = GraphQLEndpoint()
        doc.set_graphql_endpoint(gql)
        assert doc.graphql_endpoint is not None

    def test_add_schema(self):
        """测试添加模式"""
        doc = APIDocumentation()
        schema = {"type": "object"}
        doc.add_schema("User", schema)
        assert "User" in doc.schemas


class TestOpenAPIGeneration:
    """测试 OpenAPI 生成"""

    def test_to_openapi_dict(self):
        """测试转换为 OpenAPI 字典"""
        doc = APIDocumentation()
        doc.add_server(APIServer(url="http://localhost:8000"))
        doc.add_tag(APITag(name="users"))
        doc.add_operation(APIOperation(
            path="/users",
            method=HTTPMethod.GET,
            summary="Get all users"
        ))
        result = doc.to_openapi_dict()
        assert "openapi" in result
        assert "info" in result
        assert "paths" in result
        assert "/users" in result["paths"]

    def test_to_swagger_dict(self):
        """测试转换为 Swagger 字典"""
        doc = APIDocumentation()
        result = doc.to_swagger_dict()
        assert "swagger" in result
        assert "info" in result

    def test_to_json(self):
        """测试转换为 JSON"""
        doc = APIDocumentation()
        json_str = doc.to_json()
        parsed = json.loads(json_str)
        assert "openapi" in parsed

    def test_to_json_swagger(self):
        """测试转换为 Swagger JSON"""
        doc = APIDocumentation()
        json_str = doc.to_json(DocumentationType.SWAGGER)
        parsed = json.loads(json_str)
        assert "swagger" in parsed

    def test_to_yaml(self):
        """测试转换为 YAML"""
        doc = APIDocumentation()
        yaml_str = doc.to_yaml()
        assert yaml_str is not None


class TestDocumentationBuilder:
    """测试文档构建器"""

    def test_basic_usage(self):
        """测试基本使用"""
        builder = APIDocumentationBuilder(title="Builder API", version="1.0")
        doc = builder.build()
        assert doc.info.title == "Builder API"

    def test_with_server(self):
        """测试添加服务器"""
        builder = APIDocumentationBuilder()
        builder.with_server("https://api.example.com")
        doc = builder.build()
        assert len(doc.servers) == 1

    def test_with_tag(self):
        """测试添加标签"""
        builder = APIDocumentationBuilder()
        builder.with_tag("test", "Test tag")
        doc = builder.build()
        assert len(doc.tags) == 1

    def test_with_route(self):
        """测试从 Route 添加"""
        route = Route(
            path="/test",
            method=HTTPMethod.GET,
            handler=lambda r: r,
            description="Test route"
        )
        builder = APIDocumentationBuilder()
        builder.with_route(route)
        doc = builder.build()
        assert len(doc.operations) == 1

    def test_chained_builder(self):
        """测试链式调用"""
        doc = (
            APIDocumentationBuilder(title="Chained API", version="2.0")
            .with_server("http://localhost:8000", "Local")
            .with_tag("users", "User ops")
            .build()
        )
        assert doc.info.title == "Chained API"
        assert len(doc.servers) == 1
        assert len(doc.tags) == 1


class TestGlobalApp:
    """测试全局实例"""

    def test_get_default(self):
        """测试获取默认文档"""
        doc = get_default_api_doc()
        assert doc is not None
        assert doc.info.title == "Multi-Agent Engineering API"

    def test_set_default(self):
        """测试设置默认文档"""
        custom = APIDocumentation(info=APIInfo(title="Custom API"))
        set_default_api_doc(custom)
        doc = get_default_api_doc()
        assert doc.info.title == "Custom API"


class TestCompleteScenario:
    """完整场景测试"""

    def test_full_documentation(self):
        """测试完整文档"""
        # 创建文档
        doc = APIDocumentation(
            info=APIInfo(
                title="Multi-Agent API",
                version="1.0.0",
                description="Complete API documentation"
            )
        )

        # 添加服务器
        doc.add_server(APIServer(
            url="https://api.example.com/v1",
            description="Production API server"
        ))
        doc.add_server(APIServer(
            url="http://localhost:8000",
            description="Local development"
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
            responses={
                "200": APIResponse(status_code="200", description="Success"),
                "500": APIResponse(status_code="500", description="Error")
            }
        ))
        doc.add_operation(APIOperation(
            path="/agents/{id}",
            method=HTTPMethod.GET,
            summary="Get agent by ID",
            tags=["agents"],
            parameters=[
                APIParameter(name="id", in_="path", type="string", required=True)
            ]
        ))

        # 添加 WebSocket
        doc.add_websocket_endpoint(WebSocketEndpoint(
            path="/ws/agent-events",
            description="Agent event stream"
        ))

        # 添加 GraphQL
        doc.set_graphql_endpoint(GraphQLEndpoint(
            path="/graphql",
            description="GraphQL API"
        ))

        # 生成文档
        openapi_dict = doc.to_openapi_dict()
        json_doc = doc.to_json()
        swagger_json = doc.to_json(DocumentationType.SWAGGER)

        # 验证
        assert openapi_dict["info"]["title"] == "Multi-Agent API"
        assert "/agents" in openapi_dict["paths"]
        assert len(openapi_dict["servers"]) == 2
        assert len(json_doc) > 0

    def test_builder_integration(self):
        """测试构建器集成"""
        route1 = Route(
            path="/api/v1/tasks",
            method=HTTPMethod.GET,
            handler=lambda r: r,
            description="Get tasks"
        )
        route2 = Route(
            path="/api/v1/tasks/{id}",
            method=HTTPMethod.GET,
            handler=lambda r: r,
            description="Get task by ID"
        )

        doc = (
            APIDocumentationBuilder(title="Task API", version="1.0")
            .with_server("https://api.example.com")
            .with_tag("tasks", "Task operations")
            .with_route(route1)
            .with_route(route2)
            .build()
        )

        assert len(doc.operations) == 2
        assert "/api/v1/tasks" in [op.path for op in doc.operations]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
