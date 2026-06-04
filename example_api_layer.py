"""
API Layer Example Usage
"""
from src.api_layer import (
    APIApp,
    APIRequest,
    HTTPMethod,
    APIVersion,
    create_success_response,
    create_error_response,
    api_route,
    validate_request,
    APIMiddleware
)


def example_basic_usage():
    """示例：基本使用"""
    print("=" * 60)
    print("Example 1: Basic API App Usage")
    print("=" * 60)

    # 创建应用
    app = APIApp(name="my-app", version=APIVersion.V1)

    # 添加路由
    @api_route(app, "/hello", HTTPMethod.GET, description="Hello World endpoint")
    def hello_handler(req):
        return create_success_response({"message": "Hello, World!"})

    @api_route(app, "/greet", HTTPMethod.POST, description="Greet someone")
    @validate_request({"name": str})
    def greet_handler(req):
        name = req.body["name"]
        return create_success_response({"message": f"Hello, {name}!"})

    # 处理请求
    req1 = APIRequest(method=HTTPMethod.GET, path="/hello")
    resp1 = app.handle_request(req1)
    print(f"GET /hello - Status: {resp1.status_code}")
    print(f"Response: {resp1.body}")

    req2 = APIRequest(
        method=HTTPMethod.POST,
        path="/greet",
        body={"name": "Alice"}
    )
    resp2 = app.handle_request(req2)
    print(f"\nPOST /greet - Status: {resp2.status_code}")
    print(f"Response: {resp2.body}")

    print()


def example_middleware():
    """示例：使用中间件"""
    print("=" * 60)
    print("Example 2: Using Middleware")
    print("=" * 60)

    # 创建自定义中间件
    class AuthMiddleware(APIMiddleware):
        def before_request(self, request):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return create_error_response(
                    "UNAUTHORIZED",
                    "Missing Authorization header",
                    401
                )
            return None

    # 创建应用并添加中间件
    app = APIApp(name="secure-app")
    app.add_middleware(AuthMiddleware())

    # 添加需要认证的路由
    @api_route(
        app,
        "/protected",
        HTTPMethod.GET,
        description="Protected endpoint",
        requires_auth=True
    )
    def protected_handler(req):
        return create_success_response({"data": "Secret information"})

    # 无认证请求
    req1 = APIRequest(method=HTTPMethod.GET, path="/protected")
    resp1 = app.handle_request(req1)
    print("Request without auth:")
    print(f"  Status: {resp1.status_code}")
    print(f"  Response: {resp1.body}")

    # 有认证请求
    req2 = APIRequest(
        method=HTTPMethod.GET,
        path="/protected",
        headers={"Authorization": "Bearer token"}
    )
    resp2 = app.handle_request(req2)
    print("\nRequest with auth:")
    print(f"  Status: {resp2.status_code}")
    print(f"  Response: {resp2.body}")

    print()


def example_system_routes():
    """示例：系统路由"""
    print("=" * 60)
    print("Example 3: System Routes")
    print("=" * 60)

    app = APIApp(name="system-app")

    # 获取状态
    req_status = APIRequest(method=HTTPMethod.GET, path="/status")
    resp_status = app.handle_request(req_status)
    print("GET /status - Status:", resp_status.status_code)
    print("Response:", resp_status.body)

    # 获取路由列表
    req_routes = APIRequest(method=HTTPMethod.GET, path="/routes")
    resp_routes = app.handle_request(req_routes)
    print("\nGET /routes - Status:", resp_routes.status_code)
    print("Routes found:", len(resp_routes.body["data"]["routes"]))

    # 获取指标
    req_metrics = APIRequest(method=HTTPMethod.GET, path="/metrics")
    resp_metrics = app.handle_request(req_metrics)
    print("\nGET /metrics - Status:", resp_metrics.status_code)
    print("Metrics preview:", str(resp_metrics.body)[:100])

    print()


def example_task_api():
    """示例：完整的任务管理 API"""
    print("=" * 60)
    print("Example 4: Task Management API")
    print("=" * 60)

    app = APIApp(name="task-api")
    tasks = []

    # 获取所有任务
    @api_route(app, "/tasks", HTTPMethod.GET, description="Get all tasks")
    def get_tasks(req):
        return create_success_response({"tasks": tasks})

    # 创建任务
    @api_route(app, "/tasks", HTTPMethod.POST, description="Create a task")
    @validate_request({"title": str})
    def create_task(req):
        task = {
            "id": len(tasks) + 1,
            "title": req.body["title"],
            "completed": False,
            "created_at": req.timestamp.isoformat()
        }
        tasks.append(task)
        return create_success_response(task, 201)

    # 获取单个任务
    @api_route(app, "/tasks/<id>", HTTPMethod.GET, description="Get a single task")
    def get_task(req):
        task_id = req.path_params.get("id")
        if task_id:
            # 简单处理
            for task in tasks:
                if task["id"] == int(task_id):
                    return create_success_response(task)
        return create_error_response("NOT_FOUND", "Task not found", 404)

    # 测试创建任务
    print("Creating tasks...")
    for i in range(3):
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/tasks",
            body={"title": f"Task {i + 1}"}
        )
        resp = app.handle_request(req)
        print(f"  Created task: {resp.body['data']['title']}")

    # 测试获取所有任务
    print("\nGetting all tasks...")
    req = APIRequest(method=HTTPMethod.GET, path="/tasks")
    resp = app.handle_request(req)
    print(f"  Tasks: {len(resp.body['data']['tasks'])}")

    print()


if __name__ == "__main__":
    example_basic_usage()
    example_middleware()
    example_system_routes()
    example_task_api()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
