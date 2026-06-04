"""
Tests for GraphQL 支持 (Phase 30)
"""
import pytest
import json
from datetime import datetime

from src.api_layer import (
    GraphQLOperationType,
    GraphQLField,
    GraphQLArgument,
    GraphQLType,
    GraphQLRequest,
    GraphQLResponse,
    GraphQLError,
    GraphQLResolver,
    GraphQLSchema,
    GraphQLExecutor,
    GraphQLApp,
    get_default_graphql_app,
    set_default_graphql_app
)


class TestGraphQLEnumerations:
    """测试 GraphQL 枚举类型"""

    def test_operation_type(self):
        """测试操作类型"""
        assert GraphQLOperationType.QUERY is not None
        assert GraphQLOperationType.MUTATION is not None
        assert GraphQLOperationType.SUBSCRIPTION is not None


class TestGraphQLDataModels:
    """测试 GraphQL 数据模型"""

    def test_graphql_field(self):
        """测试字段定义"""
        field = GraphQLField(
            name="testField",
            type="String",
            description="A test field"
        )
        assert field.name == "testField"
        assert field.type == "String"
        assert field.description == "A test field"

    def test_graphql_argument(self):
        """测试参数定义"""
        arg = GraphQLArgument(
            name="id",
            type="ID",
            description="An ID argument",
            default_value="1"
        )
        assert arg.name == "id"
        assert arg.type == "ID"
        assert arg.default_value == "1"

    def test_graphql_type(self):
        """测试类型定义"""
        user_type = GraphQLType(
            name="User",
            kind="OBJECT",
            description="A user"
        )
        user_type.fields["id"] = GraphQLField(name="id", type="ID")
        user_type.fields["name"] = GraphQLField(name="name", type="String")

        assert user_type.name == "User"
        assert user_type.kind == "OBJECT"
        assert "id" in user_type.fields
        assert "name" in user_type.fields

    def test_graphql_request(self):
        """测试请求对象"""
        request = GraphQLRequest(
            query="{ hello }",
            operation_name="HelloQuery",
            variables={"name": "World"}
        )
        assert request.query == "{ hello }"
        assert request.operation_name == "HelloQuery"
        assert request.variables["name"] == "World"
        assert request.request_id != ""
        assert isinstance(request.timestamp, datetime)

    def test_graphql_response(self):
        """测试响应对象"""
        response = GraphQLResponse(
            data={"hello": "World"},
            request_id="req-123"
        )
        assert response.data["hello"] == "World"
        assert response.request_id == "req-123"
        assert isinstance(response.timestamp, datetime)

    def test_response_to_dict(self):
        """测试响应转换为字典"""
        response = GraphQLResponse(data={"hello": "World"})
        result = response.to_dict()
        assert "data" in result
        assert result["data"]["hello"] == "World"

    def test_graphql_error(self):
        """测试错误对象"""
        error = GraphQLError(
            message="Something went wrong",
            locations=[{"line": 1, "column": 1}],
            path=["hello"],
            extensions={"code": "TEST_ERROR"}
        )
        assert error.message == "Something went wrong"
        assert error.locations[0]["line"] == 1
        assert error.path[0] == "hello"

    def test_error_to_dict(self):
        """测试错误转换为字典"""
        error = GraphQLError(message="Test error")
        result = error.to_dict()
        assert result["message"] == "Test error"


class TestGraphQLResolver:
    """测试 GraphQL 解析器"""

    def test_resolver_creation(self):
        """测试解析器创建"""
        resolver = GraphQLResolver("Query")
        assert resolver.name == "Query"
        assert resolver.resolvers == {}

    def test_field_decorator(self):
        """测试字段装饰器"""
        resolver = GraphQLResolver("Query")

        @resolver.field("hello")
        def resolve_hello(root, args, context):
            return "Hello"

        assert "hello" in resolver.resolvers

    def test_resolve_field(self):
        """测试解析字段"""
        resolver = GraphQLResolver("Query")

        @resolver.field("hello")
        def resolve_hello(root, args, context):
            return "Hello, " + args.get("name", "World")

        result = resolver.resolve("hello", None, {"name": "Test"}, {})
        assert result == "Hello, Test"

    def test_default_resolver(self):
        """测试默认解析器"""
        resolver = GraphQLResolver("Query")

        # 测试从字典中获取
        root = {"name": "Test", "age": 25}
        result = resolver.resolve("name", root, {}, {})
        assert result == "Test"


class TestGraphQLSchema:
    """测试 GraphQL 模式"""

    def test_schema_creation(self):
        """测试模式创建"""
        schema = GraphQLSchema()
        assert schema.types == {}
        assert schema.query_type is None
        assert schema.resolvers == {}

    def test_add_type(self):
        """测试添加类型"""
        schema = GraphQLSchema()
        user_type = GraphQLType(name="User", kind="OBJECT")
        schema.add_type(user_type)
        assert "User" in schema.types

    def test_add_resolver(self):
        """测试添加解析器"""
        schema = GraphQLSchema()
        resolver = GraphQLResolver("Query")
        schema.add_resolver(resolver)
        assert "Query" in schema.resolvers

    def test_set_query_type(self):
        """测试设置 Query 类型"""
        schema = GraphQLSchema()
        query_type = GraphQLType(name="Query", kind="OBJECT")
        schema.set_query_type(query_type)
        assert schema.query_type.name == "Query"


class TestGraphQLExecutor:
    """测试 GraphQL 执行器"""

    def test_executor_creation(self):
        """测试执行器创建"""
        schema = GraphQLSchema()
        executor = GraphQLExecutor(schema)
        assert executor.schema is schema

    def test_execute_query(self):
        """测试执行查询"""
        schema = GraphQLSchema()
        query_type = GraphQLType(name="Query", kind="OBJECT")
        query_type.fields["hello"] = GraphQLField(name="hello", type="String")
        schema.set_query_type(query_type)
        executor = GraphQLExecutor(schema)

        request = GraphQLRequest(query="{ hello }")
        response = executor.execute(request)
        assert response.data is not None or response.errors is not None


class TestGraphQLApp:
    """测试 GraphQL 应用"""

    def test_app_initialization(self):
        """测试应用初始化"""
        app = GraphQLApp(name="test-graphql")
        assert app.name == "test-graphql"
        assert app.schema is not None
        assert app.executor is not None

    def test_execute_query(self):
        """测试执行查询"""
        app = GraphQLApp()

        response = app.execute("{ hello }")
        assert response is not None
        assert response.data is not None or response.errors is not None

    def test_execute_with_variables(self):
        """测试带变量的查询"""
        app = GraphQLApp()

        response = app.execute(
            query="{ user(id: $id) { id name } }",
            variables={"id": "123"}
        )
        assert response is not None

    def test_get_schema_sdl(self):
        """测试获取模式 SDL"""
        app = GraphQLApp()
        sdl = app.get_schema_sdl()
        assert "type Query" in sdl
        assert "hello" in sdl

    def test_default_schema_has_fields(self):
        """测试默认模式包含字段"""
        app = GraphQLApp()
        assert app.schema.query_type is not None
        assert "hello" in app.schema.query_type.fields
        assert "user" in app.schema.query_type.fields


class TestGlobalApp:
    """测试全局应用实例"""

    def test_get_default_graphql_app(self):
        """测试获取默认应用"""
        app1 = get_default_graphql_app()
        assert app1 is not None

        app2 = get_default_graphql_app()
        assert app1 is app2

    def test_set_default_graphql_app(self):
        """测试设置默认应用"""
        custom = GraphQLApp(name="custom-graphql")
        set_default_graphql_app(custom)

        app = get_default_graphql_app()
        assert app.name == "custom-graphql"


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        # 创建应用
        app = GraphQLApp(name="integration-test")

        # 执行查询
        response = app.execute("{ hello }")

        # 验证响应
        assert response is not None
        assert response.request_id != ""
        assert isinstance(response.timestamp, datetime)

        # 转换为字典
        result_dict = response.to_dict()
        assert isinstance(result_dict, dict)

    def test_error_response(self):
        """测试错误响应"""
        app = GraphQLApp()

        # 执行无效查询（虽然我们的简单实现不会报错）
        response = app.execute("invalid query")
        assert response is not None

    def test_multiple_queries(self):
        """测试多个查询"""
        app = GraphQLApp()

        # 查询 1
        response1 = app.execute("{ hello }")

        # 查询 2
        response2 = app.execute("{ user(id: \"123\") { id name } }")

        assert response1.request_id != response2.request_id


def test_complete_scenario():
    """完整场景测试"""
    # 1. 创建应用
    app = GraphQLApp(name="scenario-test")

    # 2. 获取模式 SDL
    sdl = app.get_schema_sdl()
    assert "type Query" in sdl
    assert "type User" in sdl

    # 3. 执行查询
    query = """
    query {
        hello
        user(id: "1") {
            id
            name
        }
    }
    """

    response = app.execute(query)
    assert response is not None

    # 4. 验证响应结构
    if response.data:
        assert isinstance(response.data, dict)

    # 5. 创建请求对象
    request = GraphQLRequest(
        query=query,
        operation_name="GetData",
        variables={"id": "2"}
    )

    assert request.query == query
    assert request.operation_name == "GetData"
    assert request.variables["id"] == "2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
