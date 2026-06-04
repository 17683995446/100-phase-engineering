"""
API Layer - REST/GraphQL Interface
遵循清晰的架构原则，提供可扩展的 API 接口
"""
import json
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
import uuid

from src.utils.logger import logger
from src.utils.structured_logging import get_logger, LogContext
from src.utils.exceptions import MAESBaseException, InputLayerException
from src.utils.prometheus import (
    PrometheusRegistry,
    Counter,
    Histogram,
    counter,
    histogram,
    timer,
)
from src.utils.telemetry import (
    Tracer,
    get_tracer,
    SpanKind,
    SpanStatus,
    extract_context,
    inject_context,
    PropagationFormat,
)


class HTTPMethod(Enum):
    """HTTP 请求方法"""
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()
    OPTIONS = auto()
    HEAD = auto()


class HTTPStatus(Enum):
    """HTTP 响应状态"""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    SERVICE_UNAVAILABLE = 503


class APIVersion(Enum):
    """API 版本"""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"


@dataclass
class APIRequest:
    """API 请求对象"""
    method: HTTPMethod
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    path_params: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())


@dataclass
class APIResponse:
    """API 响应对象"""
    status_code: int
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    request_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[Dict[str, Any]] = None


def create_success_response(data: Any, status_code: int = HTTPStatus.OK.value) -> APIResponse:
    """创建成功响应"""
    return APIResponse(
        status_code=status_code,
        body={
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    )


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = HTTPStatus.BAD_REQUEST.value,
    details: Optional[Dict[str, Any]] = None
) -> APIResponse:
    """创建错误响应"""
    error_data = {
        "code": error_code,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        error_data["details"] = details
    return APIResponse(
        status_code=status_code,
        body={
            "success": False,
            "error": error_data
        },
        error=error_data
    )


class Route:
    """路由定义"""
    def __init__(
        self,
        path: str,
        method: HTTPMethod,
        handler: Callable,
        name: Optional[str] = None,
        description: str = "",
        version: APIVersion = APIVersion.V1,
        requires_auth: bool = False
    ):
        self.path = path
        self.method = method
        self.handler = handler
        self.name = name or f"{method.name}:{path}"
        self.description = description
        self.version = version
        self.requires_auth = requires_auth

    def get_full_path(self) -> str:
        """获取完整路径（包含版本）"""
        return f"/{self.version.value}{self.path}"


class RouteRegistry:
    """路由注册表"""
    def __init__(self):
        self._routes: Dict[str, Route] = {}
        self._method_routes: Dict[HTTPMethod, Dict[str, Route]] = {
            method: {} for method in HTTPMethod
        }

    def register(self, route: Route) -> None:
        """注册路由"""
        full_path = route.get_full_path()
        self._routes[f"{route.method.name}:{full_path}"] = route
        self._method_routes[route.method][full_path] = route
        logger.debug(f"Registered route: {route.method.name} {full_path}")

    def find(
        self,
        method: HTTPMethod,
        path: str
    ) -> Optional[Route]:
        """查找路由"""
        # 先尝试完全匹配
        for version in APIVersion:
            full_path = f"/{version.value}{path}"
            if full_path in self._method_routes[method]:
                return self._method_routes[method][full_path]
        return None

    def list_routes(self) -> List[Dict[str, Any]]:
        """列出所有路由"""
        return [
            {
                "name": route.name,
                "method": route.method.name,
                "path": route.get_full_path(),
                "description": route.description,
                "requires_auth": route.requires_auth,
                "version": route.version.value
            }
            for route in self._routes.values()
        ]


class APIMiddleware:
    """API 中间件基类"""
    def before_request(self, request: APIRequest) -> Optional[APIResponse]:
        """请求前处理
        返回非 None 的响应将中断请求处理
        """
        return None

    def after_request(self, request: APIRequest, response: APIResponse) -> APIResponse:
        """请求后处理"""
        return response

    def on_error(self, request: APIRequest, exception: Exception) -> APIResponse:
        """错误处理"""
        logger.error(f"API Error: {str(exception)}", exc_info=True)
        return create_error_response(
            "INTERNAL_ERROR",
            str(exception),
            HTTPStatus.INTERNAL_SERVER_ERROR.value
        )


class LoggingMiddleware(APIMiddleware):
    """日志中间件"""
    def __init__(self):
        self._logger = get_logger("api_access")

    def before_request(self, request: APIRequest) -> Optional[APIResponse]:
        LogContext.set_context(
            request_id=request.request_id,
            method=request.method.name,
            path=request.path
        )
        self._logger.info(
            f"Request received: {request.method.name} {request.path}",
            request_id=request.request_id
        )
        return None

    def after_request(self, request: APIRequest, response: APIResponse) -> APIResponse:
        self._logger.info(
            f"Response sent: {response.status_code}",
            request_id=request.request_id,
            status_code=response.status_code
        )
        return response


class MetricsMiddleware(APIMiddleware):
    """指标收集中间件"""
    def __init__(self, registry: PrometheusRegistry):
        self._registry = registry
        self._request_count = registry.create_counter(
            "api_requests_total",
            help_text="Total API requests"
        )
        self._request_duration = registry.create_histogram(
            "api_request_duration_seconds",
            help_text="API request duration"
        )
        self._error_count = registry.create_counter(
            "api_errors_total",
            help_text="Total API errors"
        )
        self._start_time: Optional[float] = None

    def before_request(self, request: APIRequest) -> Optional[APIResponse]:
        import time
        self._start_time = time.time()
        self._request_count.inc()
        return None

    def after_request(self, request: APIRequest, response: APIResponse) -> APIResponse:
        import time
        if self._start_time:
            duration = time.time() - self._start_time
            self._request_duration.observe(duration)

        if response.status_code >= 400:
            self._error_count.inc()
        return response


class TracingMiddleware(APIMiddleware):
    """分布式追踪中间件"""
    def __init__(self, tracer_name: str = "api.layer"):
        self._tracer = get_tracer(tracer_name)
        self._logger = get_logger("api.tracing")

    def before_request(self, request: APIRequest) -> Optional[APIResponse]:
        """请求前创建Span并设置上下文"""
        # 从请求头提取追踪上下文
        context = extract_context(request.headers)
        
        # 开始Span
        span = self._tracer.start_span(
            name=f"{request.method.name} {request.path}",
            kind=SpanKind.SERVER,
            context=context,
            attributes={
                "http.method": request.method.name,
                "http.route": request.path,
                "http.request_id": request.request_id,
            }
        )
        
        # 将Span保存到request headers中，供后续处理使用
        request.headers["X-Trace-Id"] = span.context.trace_id
        request.headers["X-Span-Id"] = span.context.span_id
        
        self._logger.debug(
            f"Started tracing span for {request.method.name} {request.path}",
            trace_id=span.context.trace_id,
            span_id=span.context.span_id
        )
        return None

    def after_request(self, request: APIRequest, response: APIResponse) -> APIResponse:
        """请求后结束Span并注入响应头"""
        span = self._tracer.current_span
        if span:
            # 设置Span状态
            if response.status_code < 400:
                span.set_status(SpanStatus.OK)
            else:
                span.set_status(SpanStatus.ERROR, f"HTTP {response.status_code}")
            
            # 添加响应属性
            span.set_attributes({
                "http.status_code": response.status_code,
            })
            
            # 注入追踪上下文到响应头
            inject_context(response.headers, span.context)
            
            # 结束Span
            self._tracer.end_current_span()
            
            self._logger.debug(
                f"Completed tracing span",
                trace_id=span.context.trace_id,
                span_id=span.context.span_id,
                duration_ms=span.duration_ms
            )
        
        return response

    def on_error(self, request: APIRequest, exception: Exception) -> APIResponse:
        """错误时记录Span状态"""
        span = self._tracer.current_span
        if span:
            span.set_status(SpanStatus.ERROR, str(exception))
            span.add_event("exception", {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            })
            self._tracer.end_current_span()
        
        # 继续默认错误处理
        return super().on_error(request, exception)


class APIApp:
    """API 应用核心类"""
    def __init__(self, name: str = "maes-api", version: APIVersion = APIVersion.V1):
        self.name = name
        self.version = version
        self.route_registry = RouteRegistry()
        self._middlewares: List[APIMiddleware] = []
        self._prom_registry = PrometheusRegistry(namespace=name)

        # 内置中间件
        self.add_middleware(TracingMiddleware())
        self.add_middleware(LoggingMiddleware())
        self.add_middleware(MetricsMiddleware(self._prom_registry))

        # 内置指标
        self._setup_default_routes()
        self._setup_health_routes()
        self._setup_observability_routes()
        self._setup_config_routes()
        logger.info(f"API App initialized: {name} {version.value}")

    def add_middleware(self, middleware: APIMiddleware) -> None:
        """添加中间件"""
        self._middlewares.append(middleware)

    def add_route(
        self,
        path: str,
        method: HTTPMethod,
        handler: Callable,
        name: Optional[str] = None,
        description: str = "",
        version: Optional[APIVersion] = None,
        requires_auth: bool = False
    ) -> None:
        """添加路由"""
        route = Route(
            path=path,
            method=method,
            handler=handler,
            name=name,
            description=description,
            version=version or self.version,
            requires_auth=requires_auth
        )
        self.route_registry.register(route)

    def handle_request(self, request: APIRequest) -> APIResponse:
        """处理请求"""
        try:
            # 前置中间件
            for middleware in self._middlewares:
                early_response = middleware.before_request(request)
                if early_response:
                    return early_response

            # 查找路由
            route = self.route_registry.find(request.method, request.path)
            if not route:
                return create_error_response(
                    "NOT_FOUND",
                    f"Route not found: {request.method.name} {request.path}",
                    HTTPStatus.NOT_FOUND.value
                )

            # 调用处理函数
            response_data = route.handler(request)

            # 自动包装返回值
            if isinstance(response_data, APIResponse):
                response = response_data
            else:
                response = create_success_response(response_data)

            # 后置中间件
            for middleware in self._middlewares:
                response = middleware.after_request(request, response)

            return response

        except MAESBaseException as e:
            logger.error(f"API Exception: {str(e)}", exc_info=True)
            for middleware in self._middlewares:
                response = middleware.on_error(request, e)
                if response:
                    return response
            return create_error_response(
                "BUSINESS_ERROR",
                str(e),
                HTTPStatus.BAD_REQUEST.value
            )
        except Exception as e:
            logger.error(f"Unexpected API Error: {str(e)}", exc_info=True)
            for middleware in self._middlewares:
                response = middleware.on_error(request, e)
                if response:
                    return response
            return create_error_response(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )

    def get_routes_info(self) -> APIResponse:
        """获取路由信息"""
        routes = self.route_registry.list_routes()
        return create_success_response({
            "app_name": self.name,
            "app_version": self.version.value,
            "routes": routes
        })

    def get_metrics(self) -> APIResponse:
        """获取 Prometheus 指标"""
        metrics_text = self._prom_registry.generate_text_format()
        return APIResponse(
            status_code=HTTPStatus.OK.value,
            body=metrics_text,
            headers={"Content-Type": "text/plain; version=0.0.4"}
        )

    def get_status(self) -> APIResponse:
        """获取系统状态"""
        return create_success_response({
            "status": "healthy",
            "app_name": self.name,
            "app_version": self.version.value,
            "timestamp": datetime.now().isoformat()
        })

    def _setup_default_routes(self) -> None:
        """设置默认路由"""
        self.add_route(
            "/status",
            HTTPMethod.GET,
            lambda req: self.get_status(),
            description="Get API status"
        )
        self.add_route(
            "/metrics",
            HTTPMethod.GET,
            lambda req: self.get_metrics(),
            description="Get Prometheus metrics"
        )
        self.add_route(
            "/routes",
            HTTPMethod.GET,
            lambda req: self.get_routes_info(),
            description="List all routes"
        )
    
    def _setup_health_routes(self) -> None:
        """设置健康检查路由"""
        self.add_route(
            "/health",
            HTTPMethod.GET,
            lambda req: self.get_health(),
            description="Get overall health status"
        )
        self.add_route(
            "/health/live",
            HTTPMethod.GET,
            lambda req: self.get_liveness(),
            description="Kubernetes liveness probe"
        )
        self.add_route(
            "/health/ready",
            HTTPMethod.GET,
            lambda req: self.get_readiness(),
            description="Kubernetes readiness probe"
        )
        self.add_route(
            "/health/startup",
            HTTPMethod.GET,
            lambda req: self.get_startup(),
            description="Kubernetes startup probe"
        )
    
    def get_health(self) -> APIResponse:
        """获取整体健康状态"""
        try:
            from src.utils.system_health import get_liveness_status
            
            health_data = get_liveness_status()
            status_code = HTTPStatus.OK.value if health_data.get("status") != "UNHEALTHY" else HTTPStatus.SERVICE_UNAVAILABLE.value
            
            return APIResponse(
                status_code=status_code,
                body={
                    "success": True,
                    "data": health_data,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Health check error: {str(e)}", exc_info=True)
            return create_error_response(
                "HEALTH_CHECK_ERROR",
                f"Failed to get health status: {str(e)}",
                HTTPStatus.SERVICE_UNAVAILABLE.value
            )
    
    def get_liveness(self) -> APIResponse:
        """Kubernetes存活探针"""
        try:
            from src.utils.system_health import get_liveness_status
            
            health_data = get_liveness_status()
            is_healthy = health_data.get("status") == "HEALTHY"
            
            if is_healthy:
                return APIResponse(
                    status_code=HTTPStatus.OK.value,
                    body={"status": "alive"}
                )
            else:
                return APIResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    body={"status": "dead", "details": health_data}
                )
        except Exception as e:
            logger.error(f"Liveness probe error: {str(e)}", exc_info=True)
            return APIResponse(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                body={"status": "dead", "error": str(e)}
            )
    
    def get_readiness(self) -> APIResponse:
        """Kubernetes就绪探针"""
        try:
            from src.utils.system_health import get_readiness_status
            
            health_data = get_readiness_status()
            is_ready = health_data.get("status") in ["HEALTHY", "DEGRADED"]
            
            if is_ready:
                return APIResponse(
                    status_code=HTTPStatus.OK.value,
                    body={"status": "ready", "details": health_data}
                )
            else:
                return APIResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    body={"status": "not_ready", "details": health_data}
                )
        except Exception as e:
            logger.error(f"Readiness probe error: {str(e)}", exc_info=True)
            return APIResponse(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                body={"status": "not_ready", "error": str(e)}
            )
    
    def get_startup(self) -> APIResponse:
        """Kubernetes启动探针"""
        try:
            from src.utils.system_health import get_startup_status
            
            health_data = get_startup_status()
            is_started = health_data.get("status") in ["HEALTHY", "DEGRADED"]
            
            if is_started:
                return APIResponse(
                    status_code=HTTPStatus.OK.value,
                    body={"status": "started"}
                )
            else:
                return APIResponse(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    body={"status": "starting", "details": health_data}
                )
        except Exception as e:
            logger.error(f"Startup probe error: {str(e)}", exc_info=True)
            return APIResponse(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
                    body={"status": "starting", "error": str(e)}
                )
    
    def get_dashboard_overview(self) -> APIResponse:
        """获取仪表板总览"""
        try:
            from src.utils.observability_dashboard import get_observability_dashboard
            dashboard = get_observability_dashboard()
            overview = dashboard.get_dashboard_overview()
            return create_success_response(overview)
        except Exception as e:
            logger.error(f"Dashboard overview error: {str(e)}", exc_info=True)
            return create_error_response(
                "DASHBOARD_ERROR",
                f"Failed to get dashboard overview: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def get_health_widgets(self) -> APIResponse:
        """获取健康检查组件"""
        try:
            from src.utils.observability_dashboard import get_observability_dashboard
            dashboard = get_observability_dashboard()
            widgets = dashboard.get_health_widgets()
            return create_success_response(widgets)
        except Exception as e:
            logger.error(f"Health widgets error: {str(e)}", exc_info=True)
            return create_error_response(
                "HEALTH_WIDGETS_ERROR",
                f"Failed to get health widgets: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def get_alert_widgets(self, request: APIRequest) -> APIResponse:
        """获取告警组件"""
        try:
            from src.utils.observability_dashboard import get_observability_dashboard
            dashboard = get_observability_dashboard()
            limit = request.params.get("limit", 50)
            widgets = dashboard.get_alert_widgets(int(limit))
            return create_success_response(widgets)
        except Exception as e:
            logger.error(f"Alert widgets error: {str(e)}", exc_info=True)
            return create_error_response(
                "ALERT_WIDGETS_ERROR",
                f"Failed to get alert widgets: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def get_trace_widgets(self, request: APIRequest) -> APIResponse:
        """获取追踪组件"""
        try:
            from src.utils.observability_dashboard import get_observability_dashboard
            dashboard = get_observability_dashboard()
            limit = request.params.get("limit", 50)
            widgets = dashboard.get_trace_widgets(int(limit))
            return create_success_response(widgets)
        except Exception as e:
            logger.error(f"Trace widgets error: {str(e)}", exc_info=True)
            return create_error_response(
                "TRACE_WIDGETS_ERROR",
                f"Failed to get trace widgets: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def run_health_checks(self) -> APIResponse:
        """立即运行健康检查"""
        try:
            from src.utils.observability_dashboard import get_observability_dashboard
            dashboard = get_observability_dashboard()
            result = dashboard.run_health_checks()
            return create_success_response(result)
        except Exception as e:
            logger.error(f"Run health checks error: {str(e)}", exc_info=True)
            return create_error_response(
                "RUN_HEALTH_CHECKS_ERROR",
                f"Failed to run health checks: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def acknowledge_alert_api(self, request: APIRequest) -> APIResponse:
        """确认告警API"""
        try:
            from src.utils.observability_dashboard import get_observability_dashboard
            dashboard = get_observability_dashboard()
            alert_id = request.params.get("alert_id", "")
            acknowledged_by = request.body.get("acknowledged_by", "anonymous") if request.body else "anonymous"
            success = dashboard.acknowledge_alert(alert_id, acknowledged_by)
            return create_success_response({
                "success": success,
                "alert_id": alert_id
            })
        except Exception as e:
            logger.error(f"Acknowledge alert error: {str(e)}", exc_info=True)
            return create_error_response(
                "ACKNOWLEDGE_ALERT_ERROR",
                f"Failed to acknowledge alert: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def resolve_alert_api(self, request: APIRequest) -> APIResponse:
        """解决告警API"""
        try:
            from src.utils.observability_dashboard import get_observability_dashboard
            dashboard = get_observability_dashboard()
            alert_id = request.params.get("alert_id", "")
            resolved_by = request.body.get("resolved_by", "anonymous") if request.body else "anonymous"
            resolution_note = request.body.get("resolution_note", "") if request.body else ""
            success = dashboard.resolve_alert(alert_id, resolved_by, resolution_note)
            return create_success_response({
                "success": success,
                "alert_id": alert_id
            })
        except Exception as e:
            logger.error(f"Resolve alert error: {str(e)}", exc_info=True)
            return create_error_response(
                "RESOLVE_ALERT_ERROR",
                f"Failed to resolve alert: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def get_configs(self, request: APIRequest) -> APIResponse:
        """获取配置"""
        try:
            from src.utils.config import get_config_manager, ConfigScope
            manager = get_config_manager()
            
            scope_param = request.params.get("scope")
            scope = ConfigScope[scope_param.upper()] if scope_param else None
            
            configs = manager.get_config_dict(scope)
            return create_success_response(configs)
        except Exception as e:
            logger.error(f"Get configs error: {str(e)}", exc_info=True)
            return create_error_response(
                "GET_CONFIGS_ERROR",
                f"Failed to get configs: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def get_config(self, request: APIRequest) -> APIResponse:
        """获取单个配置"""
        try:
            from src.utils.config import get_config_manager
            manager = get_config_manager()
            
            key = request.params.get("key")
            default = request.params.get("default")
            
            value = manager.get_config(key, default)
            if value is None and not manager.get_config_value(key):
                return create_error_response(
                    "CONFIG_NOT_FOUND",
                    f"Config not found: {key}",
                    HTTPStatus.NOT_FOUND.value
                )
            
            return create_success_response({key: value})
        except Exception as e:
            logger.error(f"Get config error: {str(e)}", exc_info=True)
            return create_error_response(
                "GET_CONFIG_ERROR",
                f"Failed to get config: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def update_config(self, request: APIRequest) -> APIResponse:
        """更新配置"""
        try:
            from src.utils.config import get_config_manager, ConfigScope
            manager = get_config_manager()
            
            body = request.body or {}
            key = request.params.get("key") or body.get("key")
            value = body.get("value")
            scope_str = body.get("scope", "GLOBAL")
            description = body.get("description", "")
            
            scope = ConfigScope[scope_str.upper()]
            change = manager.set_config(key, value, scope=scope, description=description)
            
            return create_success_response({
                "success": True,
                "change": change.to_dict() if change else None
            })
        except Exception as e:
            logger.error(f"Update config error: {str(e)}", exc_info=True)
            return create_error_response(
                "UPDATE_CONFIG_ERROR",
                f"Failed to update config: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def delete_config(self, request: APIRequest) -> APIResponse:
        """删除配置"""
        try:
            from src.utils.config import get_config_manager
            manager = get_config_manager()
            
            key = request.params.get("key")
            change = manager.delete_config(key)
            
            return create_success_response({
                "success": change is not None,
                "change": change.to_dict() if change else None
            })
        except Exception as e:
            logger.error(f"Delete config error: {str(e)}", exc_info=True)
            return create_error_response(
                "DELETE_CONFIG_ERROR",
                f"Failed to delete config: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def reset_config(self, request: APIRequest) -> APIResponse:
        """重置配置"""
        try:
            from src.utils.config import get_config_manager
            manager = get_config_manager()
            
            key = request.params.get("key")
            change = manager.reset_config(key)
            
            return create_success_response({
                "success": change is not None,
                "change": change.to_dict() if change else None
            })
        except Exception as e:
            logger.error(f"Reset config error: {str(e)}", exc_info=True)
            return create_error_response(
                "RESET_CONFIG_ERROR",
                f"Failed to reset config: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def batch_update_configs(self, request: APIRequest) -> APIResponse:
        """批量更新配置"""
        try:
            from src.utils.config import get_config_manager
            manager = get_config_manager()
            
            body = request.body or {}
            updates = body.get("updates", {})
            
            changes = manager.batch_update(updates)
            
            return create_success_response({
                "success": True,
                "changes": [c.to_dict() for c in changes]
            })
        except Exception as e:
            logger.error(f"Batch update configs error: {str(e)}", exc_info=True)
            return create_error_response(
                "BATCH_UPDATE_ERROR",
                f"Failed to batch update configs: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def save_configs(self, request: APIRequest) -> APIResponse:
        """保存配置"""
        try:
            from src.utils.config import get_config_manager
            manager = get_config_manager()
            
            body = request.body or {}
            path = body.get("path", "configs/app_config.json")
            
            success = manager.save(path)
            
            return create_success_response({
                "success": success,
                "path": path
            })
        except Exception as e:
            logger.error(f"Save configs error: {str(e)}", exc_info=True)
            return create_error_response(
                "SAVE_CONFIGS_ERROR",
                f"Failed to save configs: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def load_configs(self, request: APIRequest) -> APIResponse:
        """加载配置"""
        try:
            from src.utils.config import get_config_manager
            manager = get_config_manager()
            
            body = request.body or {}
            path = body.get("path", "configs/app_config.json")
            
            success = manager.load(path)
            
            return create_success_response({
                "success": success,
                "path": path
            })
        except Exception as e:
            logger.error(f"Load configs error: {str(e)}", exc_info=True)
            return create_error_response(
                "LOAD_CONFIGS_ERROR",
                f"Failed to load configs: {str(e)}",
                HTTPStatus.INTERNAL_SERVER_ERROR.value
            )
    
    def _setup_config_routes(self) -> None:
        """设置配置管理路由"""
        self.add_route(
            "/configs",
            HTTPMethod.GET,
            lambda req: self.get_configs(req),
            description="Get all configs"
        )
        self.add_route(
            "/configs/{key}",
            HTTPMethod.GET,
            lambda req: self.get_config(req),
            description="Get a single config"
        )
        self.add_route(
            "/configs/{key}",
            HTTPMethod.PUT,
            lambda req: self.update_config(req),
            description="Update a config"
        )
        self.add_route(
            "/configs/{key}",
            HTTPMethod.DELETE,
            lambda req: self.delete_config(req),
            description="Delete a config"
        )
        self.add_route(
            "/configs/{key}/reset",
            HTTPMethod.POST,
            lambda req: self.reset_config(req),
            description="Reset a config to default"
        )
        self.add_route(
            "/configs/batch",
            HTTPMethod.POST,
            lambda req: self.batch_update_configs(req),
            description="Batch update configs"
        )
        self.add_route(
            "/configs/save",
            HTTPMethod.POST,
            lambda req: self.save_configs(req),
            description="Save configs to file"
        )
        self.add_route(
            "/configs/load",
            HTTPMethod.POST,
            lambda req: self.load_configs(req),
            description="Load configs from file"
        )
    
    def _setup_observability_routes(self) -> None:
        """设置可观测性仪表板路由"""
        self.add_route(
            "/observability/dashboard/overview",
            HTTPMethod.GET,
            lambda req: self.get_dashboard_overview(),
            description="Get dashboard overview"
        )
        self.add_route(
            "/observability/dashboard/health",
            HTTPMethod.GET,
            lambda req: self.get_health_widgets(),
            description="Get health widgets"
        )
        self.add_route(
            "/observability/dashboard/alerts",
            HTTPMethod.GET,
            lambda req: self.get_alert_widgets(req),
            description="Get alert widgets"
        )
        self.add_route(
            "/observability/dashboard/traces",
            HTTPMethod.GET,
            lambda req: self.get_trace_widgets(req),
            description="Get trace widgets"
        )
        self.add_route(
            "/observability/dashboard/health/run",
            HTTPMethod.POST,
            lambda req: self.run_health_checks(),
            description="Run health checks now"
        )
        self.add_route(
            "/observability/dashboard/alerts/{alert_id}/acknowledge",
            HTTPMethod.POST,
            lambda req: self.acknowledge_alert_api(req),
            description="Acknowledge an alert"
        )
        self.add_route(
            "/observability/dashboard/alerts/{alert_id}/resolve",
            HTTPMethod.POST,
            lambda req: self.resolve_alert_api(req),
            description="Resolve an alert"
        )


def api_route(
    app: APIApp,
    path: str,
    method: HTTPMethod = HTTPMethod.GET,
    name: Optional[str] = None,
    description: str = "",
    version: Optional[APIVersion] = None,
    requires_auth: bool = False
) -> Callable:
    """API 路由装饰器"""
    def decorator(handler: Callable) -> Callable:
        app.add_route(
            path=path,
            method=method,
            handler=handler,
            name=name,
            description=description,
            version=version,
            requires_auth=requires_auth
        )
        return handler
    return decorator


def validate_request(schema: Dict[str, Any]) -> Callable:
    """请求验证装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request: APIRequest) -> APIResponse:
            if request.body:
                # 简单的验证
                for key, value_type in schema.items():
                    if key not in request.body:
                        return create_error_response(
                            "MISSING_FIELD",
                            f"Required field missing: {key}",
                            HTTPStatus.BAD_REQUEST.value
                        )
                    if not isinstance(request.body[key], value_type):
                        return create_error_response(
                            "INVALID_TYPE",
                            f"Invalid type for field {key}: expected {value_type.__name__}",
                            HTTPStatus.BAD_REQUEST.value
                        )
            return func(request)
        return wrapper
    return decorator


# 全局应用实例（可选）
_default_app: Optional[APIApp] = None


def get_default_app() -> APIApp:
    """获取默认应用实例"""
    global _default_app
    if _default_app is None:
        _default_app = APIApp()
    return _default_app


def set_default_app(app: APIApp) -> None:
    """设置默认应用实例"""
    global _default_app
    _default_app = app
