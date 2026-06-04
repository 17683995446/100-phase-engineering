"""
Phase 35 - 分布式追踪与OpenTelemetry集成测试
验证分布式追踪功能是否正常工作
"""
import time
import unittest
from src.api_layer.core import APIApp, HTTPMethod, APIRequest
from src.scheduling_layer.task_queue import AsyncTaskQueue, TaskPriority
from src.utils.telemetry import (
    TracerProvider,
    InMemorySpanExporter,
    get_tracer,
    trace,
    extract_context,
    inject_context,
    SpanContext,
    PropagationFormat,
)


class TestDistributedTracing(unittest.TestCase):
    """分布式追踪测试"""

    def setUp(self):
        """测试前设置"""
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider(exporter=self.exporter)
        TracerProvider.set_instance(self.provider)
        self.tracer = get_tracer("test")

    def tearDown(self):
        """测试后清理"""
        self.exporter.clear()

    def test_span_creation_and_export(self):
        """测试Span创建和导出"""
        with self.tracer.span("test.operation") as span:
            span.set_attribute("key", "value")
            span.add_event("test.event", {"data": "test"})
        
        spans = self.exporter.get_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "test.operation")
        self.assertEqual(spans[0].attributes.get("key"), "value")
        self.assertEqual(spans[0].status.name, "OK")

    def test_nested_spans(self):
        """测试嵌套Span"""
        with self.tracer.span("parent") as parent_span:
            parent_trace_id = parent_span.context.trace_id
            with self.tracer.span("child") as child_span:
                self.assertEqual(child_span.context.trace_id, parent_trace_id)
        
        spans = self.exporter.get_spans()
        self.assertEqual(len(spans), 2)

    def test_trace_decorator(self):
        """测试@trace装饰器"""
        @trace(name="decorated.function")
        def test_func(x, y):
            return x + y
        
        result = test_func(1, 2)
        self.assertEqual(result, 3)
        
        spans = self.exporter.get_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "decorated.function")

    def test_context_propagation(self):
        """测试上下文传播"""
        # 创建初始Span
        with self.tracer.span("initial.operation") as span:
            trace_id = span.context.trace_id
            span_id = span.context.span_id
            
            # 注入到headers
            headers = {}
            inject_context(headers, span.context)
            self.assertIn("traceparent", headers)
        
        # 从headers提取
        extracted = extract_context(headers)
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted.trace_id, trace_id)
        self.assertEqual(extracted.span_id, span_id)

    def test_api_layer_tracing(self):
        """测试API层分布式追踪"""
        app = APIApp("test_api")
        
        def test_handler(request):
            return {"message": "Hello"}
        
        app.add_route("/test", HTTPMethod.GET, test_handler)
        
        # 发送请求
        request = APIRequest(HTTPMethod.GET, "/test")
        response = app.handle_request(request)
        
        # 验证响应头包含追踪信息
        self.assertIn("traceparent", response.headers)
        
        # 验证Span被创建
        spans = self.exporter.get_spans()
        self.assertGreater(len(spans), 0)
        self.assertTrue(any("GET /test" in s.name for s in spans))

    def test_task_queue_tracing(self):
        """测试任务队列分布式追踪"""
        queue = AsyncTaskQueue("test_queue")
        
        # 记录初始追踪上下文
        with self.tracer.span("parent.operation") as parent_span:
            trace_id = parent_span.context.trace_id
            
            def test_task():
                return "task_result"
            
            # 入队任务
            task_id = queue.enqueue(test_task)
            
            # 启动队列
            queue.start(num_workers=1)
            
            # 等待任务完成
            time.sleep(0.5)
            
            # 停止队列
            queue.stop()
        
        # 验证Span被创建
        spans = self.exporter.get_spans()
        self.assertGreater(len(spans), 0)
        
        # 验证任务追踪是否关联了父追踪
        task_spans = [s for s in spans if "task.test_task" in s.name]
        self.assertGreater(len(task_spans), 0)

    def test_error_tracing(self):
        """测试错误情况的追踪"""
        @trace()
        def error_func():
            raise ValueError("Test error")
        
        try:
            error_func()
        except ValueError:
            pass
        
        spans = self.exporter.get_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].status.name, "ERROR")


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 35 - 分布式追踪与OpenTelemetry集成测试")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDistributedTracing)
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
    run_tests()
