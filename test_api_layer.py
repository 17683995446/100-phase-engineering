"""
Tests for API Layer (Phase 28)
"""
import pytest
from datetime import datetime

from src.api_layer.core import (
    HTTPMethod,
    HTTPStatus,
    APIVersion,
    APIRequest,
    APIResponse,
    create_success_response,
    create_error_response,
    Route,
    RouteRegistry,
    APIMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    APIApp,
    api_route,
    validate_request,
    get_default_app,
    set_default_app
)


class TestHTTPMethod:
    """测试 HTTPMethod 枚举"""
    def test_enum_values(self):
        """测试枚举值"""
        assert HTTPMethod.GET is not None
        assert HTTPMethod.POST is not None
        assert HTTPMethod.PUT is not None
        assert HTTPMethod.PATCH is not None
        assert HTTPMethod.DELETE is not None
        assert HTTPMethod.OPTIONS is not None
        assert HTTPMethod.HEAD is not None


class TestHTTPStatus:
    """测试 HTTPStatus 枚举"""
    def test_enum_values(self):
        """测试枚举值"""
        assert HTTPStatus.OK.value == 200
        assert HTTPStatus.CREATED.value == 201
        assert HTTPStatus.ACCEPTED.value == 202
        assert HTTPStatus.NO_CONTENT.value == 204
        assert HTTPStatus.BAD_REQUEST.value == 400
        assert HTTPStatus.NOT_FOUND.value == 404
        assert HTTPStatus.INTERNAL_SERVER_ERROR.value == 500


class TestAPIVersion:
    """测试 APIVersion 枚举"""
    def test_enum_values(self):
        """测试枚举值"""
        assert APIVersion.V1.value == "v1"
        assert APIVersion.V2.value == "v2"
        assert APIVersion.V3.value == "v3"


class TestAPIRequest:
    """测试 APIRequest"""
    def test_basic_request(self):
        """测试基本请求"""
        request = APIRequest(
            method=HTTPMethod.GET,
            path="/test"
        )
        assert request.method == HTTPMethod.GET
        assert request.path == "/test"
        assert request.request_id != ""
        assert isinstance(request.timestamp, datetime)

    def test_full_request(self):
        """测试完整请求"""
        request = APIRequest(
            method=HTTPMethod.POST,
            path="/create",
            headers={"Content-Type": "application/json"},
            query_params={"limit": 10},
            body={"name": "test"},
            path_params={"id": 123},
            request_id="req-123"
        )
        assert request.method == HTTPMethod.POST
        assert request.path == "/create"
        assert request.headers["Content-Type"] == "application/json"
        assert request.query_params["limit"] == 10
        assert request.body["name"] == "test"
        assert request.path_params["id"] == 123
        assert request.request_id == "req-123"


class TestAPIResponse:
    """测试 APIResponse"""
    def test_basic_response(self):
        """测试基本响应"""
        response = APIResponse(status_code=200)
        assert response.status_code == 200
        assert isinstance(response.timestamp, datetime)

    def test_response_with_body(self):
        """测试带 body 的响应"""
        response = APIResponse(
            status_code=200,
            body={"result": "success"},
            headers={"X-Custom": "value"}
        )
        assert response.body["result"] == "success"
        assert response.headers["X-Custom"] == "value"


class TestResponseCreators:
    """测试响应创建函数"""
    def test_create_success_response(self):
        """测试创建成功响应"""
        response = create_success_response({"message": "ok"})
        assert response.status_code == 200
        assert response.body["success"] is True
        assert response.body["data"]["message"] == "ok"
        assert "timestamp" in response.body

    def test_create_success_response_with_status(self):
        """测试创建带状态码的成功响应"""
        response = create_success_response({"id": 1}, HTTPStatus.CREATED.value)
        assert response.status_code == 201
        assert response.body["success"] is True

    def test_create_error_response(self):
        """测试创建错误响应"""
        response = create_error_response(
            "VALIDATION_ERROR",
            "Invalid input"
        )
        assert response.status_code == 400
        assert response.body["success"] is False
        assert response.body["error"]["code"] == "VALIDATION_ERROR"
        assert response.body["error"]["message"] == "Invalid input"
        assert "timestamp" in response.body["error"]

    def test_create_error_response_with_details(self):
        """测试创建带详情的错误响应"""
        response = create_error_response(
            "CONFLICT",
            "Resource already exists",
            HTTPStatus.CONFLICT.value,
            {"field": "name", "value": "test"}
        )
        assert response.status_code == 409
        assert response.body["error"]["details"]["field"] == "name"


class TestRoute:
    """测试 Route 类"""
    def test_basic_route(self):
        """测试基本路由"""
        def dummy_handler(req):
            return create_success_response({})

        route = Route(
            path="/users",
            method=HTTPMethod.GET,
            handler=dummy_handler,
            name="get_users",
            description="Get all users",
            version=APIVersion.V1
        )
        assert route.path == "/users"
        assert route.method == HTTPMethod.GET
        assert route.name == "get_users"
        assert route.description == "Get all users"
        assert route.version == APIVersion.V1

    def test_get_full_path(self):
        """测试获取完整路径"""
        def dummy_handler(req):
            return create_success_response({})

        route = Route(
            path="/users",
            method=HTTPMethod.GET,
            handler=dummy_handler,
            version=APIVersion.V1
        )
        assert route.get_full_path() == "/v1/users"


class TestRouteRegistry:
    """测试 RouteRegistry"""
    def test_register_route(self):
        """测试注册路由"""
        registry = RouteRegistry()

        def dummy_handler(req):
            return create_success_response({})

        route = Route(
            path="/test",
            method=HTTPMethod.GET,
            handler=dummy_handler
        )
        registry.register(route)

        found = registry.find(HTTPMethod.GET, "/test")
        assert found is not None
        assert found.path == "/test"

    def test_list_routes(self):
        """测试列出路由"""
        registry = RouteRegistry()

        def dummy_handler(req):
            return create_success_response({})

        route1 = Route(path="/users", method=HTTPMethod.GET, handler=dummy_handler)
        route2 = Route(path="/posts", method=HTTPMethod.POST, handler=dummy_handler)
        registry.register(route1)
        registry.register(route2)

        routes = registry.list_routes()
        assert len(routes) == 2

    def test_route_not_found(self):
        """测试路由未找到"""
        registry = RouteRegistry()
        found = registry.find(HTTPMethod.GET, "/nonexistent")
        assert found is None


class TestAPIApp:
    """测试 APIApp"""
    def test_app_initialization(self):
        """测试应用初始化"""
        app = APIApp(name="test-api", version=APIVersion.V1)
        assert app.name == "test-api"
        assert app.version == APIVersion.V1
        assert app.route_registry is not None

    def test_add_route(self):
        """测试添加路由"""
        app = APIApp()

        def handler(req):
            return create_success_response({"message": "hello"})

        app.add_route("/hello", HTTPMethod.GET, handler, description="Hello endpoint")

        found = app.route_registry.find(HTTPMethod.GET, "/hello")
        assert found is not None

    def test_handle_request_success(self):
        """测试处理成功请求"""
        app = APIApp()

        def handler(req):
            return create_success_response({"message": "success"})

        app.add_route("/success", HTTPMethod.GET, handler)

        request = APIRequest(
            method=HTTPMethod.GET,
            path="/success"
        )
        response = app.handle_request(request)

        assert response.status_code == 200
        assert response.body["success"] is True

    def test_handle_request_not_found(self):
        """测试处理 404"""
        app = APIApp()

        request = APIRequest(
            method=HTTPMethod.GET,
            path="/nonexistent"
        )
        response = app.handle_request(request)

        assert response.status_code == 404
        assert response.body["success"] is False
        assert response.body["error"]["code"] == "NOT_FOUND"

    def test_get_status(self):
        """测试获取状态"""
        app = APIApp()
        response = app.get_status()
        assert response.status_code == 200
        assert response.body["success"] is True
        assert response.body["data"]["status"] == "healthy"

    def test_get_routes_info(self):
        """测试获取路由信息"""
        app = APIApp()
        response = app.get_routes_info()
        assert response.status_code == 200
        assert response.body["success"] is True
        assert "routes" in response.body["data"]
        # 应该包含默认路由
        assert len(response.body["data"]["routes"]) >= 3

    def test_get_metrics(self):
        """测试获取指标"""
        app = APIApp()
        response = app.get_metrics()
        assert response.status_code == 200
        assert "Content-Type" in response.headers


class TestMiddleware:
    """测试中间件"""
    def test_custom_middleware(self):
        """测试自定义中间件"""
        class CustomMiddleware(APIMiddleware):
            def __init__(self):
                self.before_called = False
                self.after_called = False

            def before_request(self, request):
                self.before_called = True
                return None

            def after_request(self, request, response):
                self.after_called = True
                return response

        app = APIApp()
        middleware = CustomMiddleware()
        app.add_middleware(middleware)

        def handler(req):
            return create_success_response({})

        app.add_route("/test", HTTPMethod.GET, handler)

        request = APIRequest(method=HTTPMethod.GET, path="/test")
        app.handle_request(request)

        assert middleware.before_called
        assert middleware.after_called

    def test_middleware_early_response(self):
        """测试中间件提前响应"""
        class EarlyResponseMiddleware(APIMiddleware):
            def before_request(self, request):
                return create_error_response(
                    "EARLY_RETURN",
                    "Blocked by middleware",
                    HTTPStatus.FORBIDDEN.value
                )

        app = APIApp()
        app.add_middleware(EarlyResponseMiddleware())

        def handler(req):
            return create_success_response({})

        app.add_route("/test", HTTPMethod.GET, handler)

        request = APIRequest(method=HTTPMethod.GET, path="/test")
        response = app.handle_request(request)

        assert response.status_code == 403
        assert response.body["error"]["code"] == "EARLY_RETURN"


class TestDecorators:
    """测试装饰器"""
    def test_api_route_decorator(self):
        """测试 api_route 装饰器"""
        app = APIApp()

        @api_route(app, "/decorated", HTTPMethod.GET, description="Decorated route")
        def decorated_handler(req):
            return create_success_response({"decorated": True})

        request = APIRequest(method=HTTPMethod.GET, path="/decorated")
        response = app.handle_request(request)

        assert response.status_code == 200
        assert response.body["data"]["decorated"] is True

    def test_validate_request_decorator(self):
        """测试 validate_request 装饰器"""
        schema = {
            "name": str,
            "age": int
        }

        @validate_request(schema)
        def handler(req):
            return create_success_response({"valid": True})

        # 有效请求
        valid_req = APIRequest(
            method=HTTPMethod.POST,
            path="/test",
            body={"name": "John", "age": 30}
        )
        response = handler(valid_req)
        assert response.body["data"]["valid"] is True

        # 缺少字段
        missing_field_req = APIRequest(
            method=HTTPMethod.POST,
            path="/test",
            body={"name": "John"}
        )
        response = handler(missing_field_req)
        assert response.status_code == 400
        assert response.body["error"]["code"] == "MISSING_FIELD"

        # 类型错误
        invalid_type_req = APIRequest(
            method=HTTPMethod.POST,
            path="/test",
            body={"name": "John", "age": "30"}
        )
        response = handler(invalid_type_req)
        assert response.status_code == 400
        assert response.body["error"]["code"] == "INVALID_TYPE"


class TestGlobalApp:
    """测试全局应用实例"""
    def test_default_app(self):
        """测试默认应用"""
        app = get_default_app()
        assert app is not None

    def test_set_default_app(self):
        """测试设置默认应用"""
        custom_app = APIApp(name="custom-app")
        set_default_app(custom_app)

        app = get_default_app()
        assert app.name == "custom-app"


def test_integration():
    """集成测试"""
    app = APIApp(name="integration-test")

    # 添加多个路由
    tasks = []

    @api_route(app, "/tasks", HTTPMethod.GET, description="Get all tasks")
    def get_tasks(req):
        return create_success_response({"tasks": tasks})

    @api_route(app, "/tasks", HTTPMethod.POST, description="Create a task")
    @validate_request({"title": str})
    def create_task(req):
        task = {"id": len(tasks) + 1, "title": req.body["title"]}
        tasks.append(task)
        return create_success_response(task, HTTPStatus.CREATED.value)

    # 测试获取空任务列表
    request = APIRequest(method=HTTPMethod.GET, path="/tasks")
    response = app.handle_request(request)
    assert response.body["data"]["tasks"] == []

    # 测试创建任务
    request = APIRequest(
        method=HTTPMethod.POST,
        path="/tasks",
        body={"title": "Test Task"}
    )
    response = app.handle_request(request)
    assert response.status_code == 201
    assert response.body["data"]["title"] == "Test Task"

    # 测试获取任务列表
    request = APIRequest(method=HTTPMethod.GET, path="/tasks")
    response = app.handle_request(request)
    assert len(response.body["data"]["tasks"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
