"""
Phase 47 - API网关与负载均衡测试
验证API网关和负载均衡功能是否正常工作
"""
import unittest
from src.utils.api_gateway import (
    APIGateway,
    LoadBalancer,
    BackendServer,
    RouteRule,
    GatewayRequest,
    LoadBalanceStrategy,
    GatewayStatus,
    get_api_gateway
)


class TestBackendServer(unittest.TestCase):
    """后端服务器测试"""
    
    def test_server_creation(self):
        """测试服务器创建"""
        server = BackendServer(id="srv1", host="localhost", port=8080)
        self.assertEqual(server.id, "srv1")
        self.assertEqual(server.host, "localhost")
        self.assertEqual(server.port, 8080)
        self.assertEqual(server.url, "http://localhost:8080")
    
    def test_server_to_dict(self):
        """测试转换为字典"""
        server = BackendServer(id="srv1", host="localhost", port=8080, weight=2)
        d = server.to_dict()
        self.assertEqual(d["id"], "srv1")
        self.assertEqual(d["weight"], 2)
        self.assertTrue(d["healthy"])


class TestRouteRule(unittest.TestCase):
    """路由规则测试"""
    
    def test_route_match(self):
        """测试路由匹配"""
        route = RouteRule(path="/api/users", target_servers=["srv1"])
        self.assertTrue(route.matches("/api/users", "GET"))
        self.assertTrue(route.matches("/api/users/123", "GET"))
        self.assertFalse(route.matches("/api/other", "GET"))
    
    def test_route_methods(self):
        """测试路由方法限制"""
        route = RouteRule(path="/api", target_servers=["srv1"], methods=["GET"])
        self.assertTrue(route.matches("/api", "GET"))
        self.assertFalse(route.matches("/api", "POST"))
    
    def test_transform_path(self):
        """测试路径转换"""
        route = RouteRule(path="/api", target_servers=["srv1"], strip_prefix=True)
        self.assertEqual(route.transform_path("/api/users"), "/users")
        
        route2 = RouteRule(path="/old", target_servers=["srv1"], rewrite_path="/new")
        self.assertEqual(route2.transform_path("/old/path"), "/new/path")


class TestLoadBalancer(unittest.TestCase):
    """负载均衡器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.lb = LoadBalancer(LoadBalanceStrategy.ROUND_ROBIN)
        self.s1 = BackendServer(id="s1", host="localhost", port=8081)
        self.s2 = BackendServer(id="s2", host="localhost", port=8082)
        self.lb.add_server(self.s1)
        self.lb.add_server(self.s2)
    
    def test_add_server(self):
        """测试添加服务器"""
        self.assertEqual(len(self.lb._servers), 2)
    
    def test_round_robin(self):
        """测试轮询策略"""
        results = []
        for _ in range(4):
            server = self.lb.get_server()
            results.append(server.id)
        
        # 轮询应该交替返回
        self.assertEqual(results[0], "s1")
        self.assertEqual(results[1], "s2")
        self.assertEqual(results[2], "s1")
        self.assertEqual(results[3], "s2")
    
    def test_random_strategy(self):
        """测试随机策略"""
        lb = LoadBalancer(LoadBalanceStrategy.RANDOM)
        lb.add_server(self.s1)
        lb.add_server(self.s2)
        
        server = lb.get_server()
        self.assertIn(server.id, ["s1", "s2"])
    
    def test_least_connections(self):
        """测试最少连接策略"""
        lb = LoadBalancer(LoadBalanceStrategy.LEAST_CONNECTIONS)
        s1 = BackendServer(id="s1", host="localhost", port=8081)
        s2 = BackendServer(id="s2", host="localhost", port=8082)
        lb.add_server(s1)
        lb.add_server(s2)
        
        # 模拟s1有更多连接
        lb.record_request_start("s1")
        lb.record_request_start("s1")
        
        server = lb.get_server()
        self.assertEqual(server.id, "s2")
    
    def test_ip_hash(self):
        """测试IP哈希策略"""
        lb = LoadBalancer(LoadBalanceStrategy.IP_HASH)
        lb.add_server(self.s1)
        lb.add_server(self.s2)
        
        # 相同IP应该总是路由到同一服务器
        server1 = lb.get_server("192.168.1.1")
        server2 = lb.get_server("192.168.1.1")
        self.assertEqual(server1.id, server2.id)
    
    def test_weighted_round_robin(self):
        """测试加权轮询"""
        lb = LoadBalancer(LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN)
        s1 = BackendServer(id="s1", host="localhost", port=8081, weight=3)
        s2 = BackendServer(id="s2", host="localhost", port=8082, weight=1)
        lb.add_server(s1)
        lb.add_server(s2)
        
        # 加权选择应该更倾向于高权重服务器
        results = []
        for _ in range(100):
            server = lb.get_server()
            results.append(server.id)
        
        s1_count = results.count("s1")
        s2_count = results.count("s2")
        self.assertGreater(s1_count, s2_count)
    
    def test_unhealthy_server(self):
        """测试不健康服务器"""
        self.lb.update_server_health("s1", False)
        
        server = self.lb.get_server()
        self.assertEqual(server.id, "s2")
    
    def test_remove_server(self):
        """测试移除服务器"""
        self.assertTrue(self.lb.remove_server("s1"))
        self.assertEqual(len(self.lb._servers), 1)
        self.assertFalse(self.lb.remove_server("nonexistent"))
    
    def test_record_request(self):
        """测试记录请求"""
        self.lb.record_request_start("s1")
        self.assertEqual(self.lb._servers["s1"].active_connections, 1)
        self.assertEqual(self.lb._servers["s1"].total_requests, 1)
        
        self.lb.record_request_end("s1")
        self.assertEqual(self.lb._servers["s1"].active_connections, 0)
    
    def test_stats(self):
        """测试统计"""
        stats = self.lb.get_stats()
        self.assertEqual(stats["total_servers"], 2)
        self.assertEqual(stats["healthy_servers"], 2)
        self.assertEqual(stats["strategy"], "ROUND_ROBIN")


class TestAPIGateway(unittest.TestCase):
    """API网关测试"""
    
    def setUp(self):
        """测试前设置"""
        self.gateway = APIGateway()
        
        # 添加路由
        self.gateway.add_route(RouteRule(
            path="/api/users",
            target_servers=["s1", "s2"]
        ))
        
        # 注册后端
        servers = [
            BackendServer(id="s1", host="localhost", port=8081),
            BackendServer(id="s2", host="localhost", port=8082)
        ]
        self.gateway.register_backend("/api/users", servers)
    
    def test_add_route(self):
        """测试添加路由"""
        self.assertEqual(len(self.gateway._routes), 1)
    
    def test_register_backend(self):
        """测试注册后端"""
        self.assertEqual(len(self.gateway._load_balancers), 1)
        self.assertIn("/api/users", self.gateway._load_balancers)
    
    def test_route_request(self):
        """测试路由请求"""
        request = GatewayRequest(method="GET", path="/api/users")
        response = self.gateway.route_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.backend_server)
        self.assertIn(response.backend_server, ["s1", "s2"])
    
    def test_route_not_found(self):
        """测试路由不存在"""
        request = GatewayRequest(method="GET", path="/notfound")
        response = self.gateway.route_request(request)
        
        self.assertEqual(response.status_code, 404)
    
    def test_method_not_allowed(self):
        """测试方法不允许"""
        self.gateway.add_route(RouteRule(
            path="/api/readonly",
            target_servers=["s1"],
            methods=["GET"]
        ))
        servers = [BackendServer(id="s1", host="localhost", port=8081)]
        self.gateway.register_backend("/api/readonly", servers)
        
        request = GatewayRequest(method="POST", path="/api/readonly")
        response = self.gateway.route_request(request)
        
        self.assertEqual(response.status_code, 404)
    
    def test_rate_limit(self):
        """测试限流"""
        self.gateway.add_route(RouteRule(
            path="/api/limited",
            target_servers=["s1"],
            rate_limit=2
        ))
        servers = [BackendServer(id="s1", host="localhost", port=8081)]
        self.gateway.register_backend("/api/limited", servers)
        
        # 前2次应该成功
        request = GatewayRequest(method="GET", path="/api/limited", client_ip="1.2.3.4")
        self.assertEqual(self.gateway.route_request(request).status_code, 200)
        self.assertEqual(self.gateway.route_request(request).status_code, 200)
        
        # 第3次应该被限流
        self.assertEqual(self.gateway.route_request(request).status_code, 429)
    
    def test_path_transform(self):
        """测试路径转换"""
        self.gateway.add_route(RouteRule(
            path="/api/v1",
            target_servers=["s1"],
            strip_prefix=True
        ))
        servers = [BackendServer(id="s1", host="localhost", port=8081)]
        self.gateway.register_backend("/api/v1", servers)
        
        request = GatewayRequest(method="GET", path="/api/v1/users")
        response = self.gateway.route_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("/users", response.body)
    
    def test_health_check(self):
        """测试健康检查"""
        health = self.gateway.health_check()
        self.assertEqual(health["status"], GatewayStatus.HEALTHY.name)
        self.assertEqual(health["routes"], 1)
        self.assertEqual(health["backends"]["total"], 2)
    
    def test_health_check_unhealthy(self):
        """测试不健康状态"""
        lb = self.gateway._load_balancers["/api/users"]
        lb.update_server_health("s1", False)
        lb.update_server_health("s2", False)
        
        health = self.gateway.health_check()
        self.assertEqual(health["status"], GatewayStatus.UNHEALTHY.name)
    
    def test_stats(self):
        """测试统计"""
        # 发送一些请求
        for _ in range(5):
            request = GatewayRequest(method="GET", path="/api/users")
            self.gateway.route_request(request)
        
        stats = self.gateway.get_stats()
        self.assertEqual(stats["request_count"], 5)
        self.assertEqual(stats["error_count"], 0)
        self.assertEqual(stats["error_rate"], 0.0)
        self.assertEqual(stats["routes"], 1)
    
    def test_backend_stats(self):
        """测试后端统计"""
        stats = self.gateway.get_backend_stats()
        self.assertIn("/api/users", stats)
        self.assertEqual(stats["/api/users"]["total_servers"], 2)


class TestGatewayRequest(unittest.TestCase):
    """网关请求测试"""
    
    def test_request_creation(self):
        """测试请求创建"""
        request = GatewayRequest(
            method="POST",
            path="/api/users",
            headers={"Content-Type": "application/json"},
            client_ip="192.168.1.1"
        )
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/api/users")
        self.assertEqual(request.client_ip, "192.168.1.1")


class TestGlobalGateway(unittest.TestCase):
    """全局网关测试"""
    
    def test_get_api_gateway(self):
        """测试获取全局网关"""
        gateway1 = get_api_gateway()
        gateway2 = get_api_gateway()
        self.assertIs(gateway1, gateway2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 47 - API网关与负载均衡测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBackendServer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRouteRule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLoadBalancer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAPIGateway))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGatewayRequest))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalGateway))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run_tests()
