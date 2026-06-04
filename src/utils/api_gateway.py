"""
API网关与负载均衡
提供API路由、请求转发、负载均衡和限流功能
"""
import time
import random
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from urllib.parse import urlparse

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = auto()
    RANDOM = auto()
    LEAST_CONNECTIONS = auto()
    WEIGHTED_ROUND_ROBIN = auto()
    IP_HASH = auto()


class GatewayStatus(Enum):
    """网关状态"""
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()


@dataclass
class BackendServer:
    """后端服务器"""
    id: str
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    last_checked: Optional[datetime] = None
    
    @property
    def url(self) -> str:
        """获取URL"""
        return f"http://{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "host": self.host,
            "port": self.port,
            "weight": self.weight,
            "healthy": self.healthy,
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "url": self.url
        }


@dataclass
class RouteRule:
    """路由规则"""
    path: str
    target_servers: List[str]
    methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    strip_prefix: bool = False
    rewrite_path: Optional[str] = None
    rate_limit: Optional[int] = None
    require_auth: bool = False
    
    def matches(self, path: str, method: str) -> bool:
        """检查是否匹配"""
        if method not in self.methods:
            return False
        return path.startswith(self.path)
    
    def transform_path(self, path: str) -> str:
        """转换路径"""
        if self.rewrite_path:
            return path.replace(self.path, self.rewrite_path, 1)
        if self.strip_prefix:
            return path[len(self.path):] or "/"
        return path


@dataclass
class GatewayRequest:
    """网关请求"""
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    client_ip: str = ""
    query_params: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "client_ip": self.client_ip,
            "query_params": self.query_params
        }


@dataclass
class GatewayResponse:
    """网关响应"""
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    backend_server: Optional[str] = None
    response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "backend_server": self.backend_server,
            "response_time_ms": self.response_time_ms
        }


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self._servers: Dict[str, BackendServer] = {}
        self._round_robin_index = 0
        self._lock = threading.Lock()
        self._logger = get_logger("load.balancer")
    
    def add_server(self, server: BackendServer) -> None:
        """添加服务器"""
        with self._lock:
            self._servers[server.id] = server
        self._logger.info(f"Added backend server: {server.id} ({server.url})")
    
    def remove_server(self, server_id: str) -> bool:
        """移除服务器"""
        with self._lock:
            if server_id in self._servers:
                del self._servers[server_id]
                return True
            return False
    
    def get_server(self, client_ip: str = "") -> Optional[BackendServer]:
        """获取服务器"""
        with self._lock:
            healthy_servers = [
                s for s in self._servers.values()
                if s.healthy
            ]
            
            if not healthy_servers:
                return None
            
            if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
                return self._round_robin_select(healthy_servers)
            elif self.strategy == LoadBalanceStrategy.RANDOM:
                return random.choice(healthy_servers)
            elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
                return min(healthy_servers, key=lambda s: s.active_connections)
            elif self.strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
                return self._weighted_select(healthy_servers)
            elif self.strategy == LoadBalanceStrategy.IP_HASH:
                return self._ip_hash_select(healthy_servers, client_ip)
            
            return healthy_servers[0]
    
    def _round_robin_select(self, servers: List[BackendServer]) -> BackendServer:
        """轮询选择"""
        server = servers[self._round_robin_index % len(servers)]
        self._round_robin_index += 1
        return server
    
    def _weighted_select(self, servers: List[BackendServer]) -> BackendServer:
        """加权选择"""
        total_weight = sum(s.weight for s in servers)
        if total_weight == 0:
            return random.choice(servers)
        
        point = random.randint(1, total_weight)
        current = 0
        for server in servers:
            current += server.weight
            if point <= current:
                return server
        return servers[-1]
    
    def _ip_hash_select(self, servers: List[BackendServer], client_ip: str) -> BackendServer:
        """IP哈希选择"""
        if not client_ip:
            return random.choice(servers)
        hash_value = hash(client_ip)
        return servers[hash_value % len(servers)]
    
    def update_server_health(self, server_id: str, healthy: bool) -> None:
        """更新服务器健康状态"""
        with self._lock:
            if server_id in self._servers:
                self._servers[server_id].healthy = healthy
                self._servers[server_id].last_checked = datetime.now()
    
    def record_request_start(self, server_id: str) -> None:
        """记录请求开始"""
        with self._lock:
            if server_id in self._servers:
                self._servers[server_id].active_connections += 1
                self._servers[server_id].total_requests += 1
    
    def record_request_end(self, server_id: str, success: bool = True) -> None:
        """记录请求结束"""
        with self._lock:
            if server_id in self._servers:
                self._servers[server_id].active_connections -= 1
                if not success:
                    self._servers[server_id].failed_requests += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "strategy": self.strategy.name,
                "total_servers": len(self._servers),
                "healthy_servers": sum(1 for s in self._servers.values() if s.healthy),
                "servers": [s.to_dict() for s in self._servers.values()]
            }


class RateLimiter:
    """网关限流器"""
    
    def __init__(self, default_limit: int = 100, window_seconds: float = 60.0):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._logger = get_logger("gateway.rate.limiter")
    
    def is_allowed(self, key: str, limit: Optional[int] = None) -> bool:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - self.window_seconds
        max_requests = limit or self.default_limit
        
        with self._lock:
            if key not in self._requests:
                self._requests[key] = []
            
            # 清理过期请求
            self._requests[key] = [
                t for t in self._requests[key]
                if t > window_start
            ]
            
            if len(self._requests[key]) >= max_requests:
                self._logger.warning(f"Rate limit exceeded: {key}")
                return False
            
            self._requests[key].append(now)
            return True
    
    def get_remaining(self, key: str, limit: Optional[int] = None) -> int:
        """获取剩余请求数"""
        now = time.time()
        window_start = now - self.window_seconds
        max_requests = limit or self.default_limit
        
        with self._lock:
            if key not in self._requests:
                return max_requests
            
            self._requests[key] = [
                t for t in self._requests[key]
                if t > window_start
            ]
            
            return max(0, max_requests - len(self._requests[key]))


class APIGateway:
    """API网关"""
    
    def __init__(self):
        self._routes: List[RouteRule] = []
        self._load_balancers: Dict[str, LoadBalancer] = {}
        self._rate_limiter = RateLimiter()
        self._middlewares: List[Callable] = []
        self._lock = threading.Lock()
        self._logger = get_logger("api.gateway")
        self._request_count = 0
        self._error_count = 0
        self._total_response_time = 0.0
    
    def add_route(self, route: RouteRule) -> None:
        """添加路由"""
        with self._lock:
            self._routes.append(route)
        self._logger.info(f"Added route: {route.path}")
    
    def add_middleware(self, middleware: Callable) -> None:
        """添加中间件"""
        self._middlewares.append(middleware)
    
    def register_backend(self, route_path: str, servers: List[BackendServer], 
                         strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN) -> None:
        """注册后端服务"""
        lb = LoadBalancer(strategy)
        for server in servers:
            lb.add_server(server)
        
        with self._lock:
            self._load_balancers[route_path] = lb
        
        self._logger.info(f"Registered backend for {route_path} with {len(servers)} servers")
    
    def route_request(self, request: GatewayRequest) -> GatewayResponse:
        """路由请求"""
        start_time = time.time()
        self._request_count += 1
        
        # 查找匹配的路由
        route = self._match_route(request.path, request.method)
        if not route:
            self._error_count += 1
            return GatewayResponse(
                status_code=404,
                body='{"error": "Route not found"}'
            )
        
        # 限流检查
        if route.rate_limit:
            client_key = f"{request.client_ip}:{route.path}"
            if not self._rate_limiter.is_allowed(client_key, route.rate_limit):
                self._error_count += 1
                return GatewayResponse(
                    status_code=429,
                    body='{"error": "Rate limit exceeded"}'
                )
        
        # 获取负载均衡器
        lb = self._load_balancers.get(route.path)
        if not lb:
            self._error_count += 1
            return GatewayResponse(
                status_code=503,
                body='{"error": "No backend available"}'
            )
        
        # 选择后端服务器
        server = lb.get_server(request.client_ip)
        if not server:
            self._error_count += 1
            return GatewayResponse(
                status_code=503,
                body='{"error": "No healthy backend"}'
            )
        
        # 记录请求开始
        lb.record_request_start(server.id)
        
        try:
            # 转换路径
            target_path = route.transform_path(request.path)
            
            # 模拟转发请求（实际实现中会进行HTTP请求）
            response = self._forward_request(request, server, target_path)
            
            # 记录请求结束
            lb.record_request_end(server.id, success=response.status_code < 500)
            
            response_time = (time.time() - start_time) * 1000
            response.response_time_ms = response_time
            self._total_response_time += response_time
            
            return response
            
        except Exception as e:
            lb.record_request_end(server.id, success=False)
            self._error_count += 1
            self._logger.error(f"Request forwarding failed: {e}")
            return GatewayResponse(
                status_code=502,
                body=f'{{"error": "Bad Gateway: {str(e)}"}}'
            )
    
    def _match_route(self, path: str, method: str) -> Optional[RouteRule]:
        """匹配路由"""
        with self._lock:
            for route in self._routes:
                if route.matches(path, method):
                    return route
        return None
    
    def _forward_request(self, request: GatewayRequest, server: BackendServer, 
                         target_path: str) -> GatewayResponse:
        """转发请求（模拟实现）"""
        # 模拟处理延迟
        time.sleep(0.001)
        
        return GatewayResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=f'{{"status": "ok", "server": "{server.id}", "path": "{target_path}"}}',
            backend_server=server.id
        )
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        with self._lock:
            total_backends = sum(
                len(lb._servers) for lb in self._load_balancers.values()
            )
            healthy_backends = sum(
                sum(1 for s in lb._servers.values() if s.healthy)
                for lb in self._load_balancers.values()
            )
            
            return {
                "status": GatewayStatus.HEALTHY.name if healthy_backends > 0 else GatewayStatus.UNHEALTHY.name,
                "routes": len(self._routes),
                "backends": {
                    "total": total_backends,
                    "healthy": healthy_backends
                }
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        avg_response_time = (
            self._total_response_time / self._request_count
            if self._request_count > 0 else 0
        )
        
        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / self._request_count if self._request_count > 0 else 0,
            "avg_response_time_ms": avg_response_time,
            "routes": len(self._routes),
            "backends": len(self._load_balancers)
        }
    
    def get_backend_stats(self) -> Dict[str, Any]:
        """获取后端统计"""
        with self._lock:
            return {
                path: lb.get_stats()
                for path, lb in self._load_balancers.items()
            }


# 全局实例
_gateway: Optional[APIGateway] = None


def get_api_gateway() -> APIGateway:
    """获取API网关"""
    global _gateway
    if _gateway is None:
        _gateway = APIGateway()
    return _gateway
