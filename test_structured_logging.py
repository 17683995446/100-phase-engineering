"""
结构化日志系统测试
遵循信息显式化公理：验证日志结构化和可追溯性
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime
from io import StringIO

from src.utils.structured_logging import (
    LogLevel,
    LogFormat,
    LogDestination,
    LogEntry,
    LogContext,
    LogFormatter,
    TextFormatter,
    JSONFormatter,
    CSVFormatter,
    LogHandler,
    ConsoleHandler,
    FileHandler,
    MemoryHandler,
    StructuredLogger,
    LoggerAdapter,
    LogAggregator,
    get_logger,
    create_test_logger,
    create_memory_logger,
    TimerLogger,
)


class TestLogEntry:
    """日志条目测试"""

    def test_create_entry(self):
        """测试创建日志条目"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            logger_name="test",
            message="test message"
        )
        assert entry.logger_name == "test"
        assert entry.level == LogLevel.INFO

    def test_to_dict(self):
        """测试转换为字典"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            logger_name="test",
            message="error message",
            context={"error_code": 500}
        )
        data = entry.to_dict()
        assert data["level"] == "ERROR"
        assert data["message"] == "error message"
        assert data["context"]["error_code"] == 500


class TestLogContext:
    """日志上下文测试"""

    def test_set_and_get_context(self):
        """测试设置和获取上下文"""
        LogContext.set_context(task_id="123", agent_id="agent_1")
        context = LogContext.get_context()
        assert context["task_id"] == "123"
        assert context["agent_id"] == "agent_1"

    def test_clear_context(self):
        """测试清除上下文"""
        LogContext.set_context(key="value")
        LogContext.clear_context()
        assert len(LogContext.get_context()) == 0

    def test_get_value(self):
        """测试获取单个值"""
        LogContext.set_context(user_id=42)
        value = LogContext.get_value("user_id")
        assert value == 42

    def test_get_value_default(self):
        """测试默认值"""
        value = LogContext.get_value("nonexistent", default="default")
        assert value == "default"


class TestFormatters:
    """格式化器测试"""

    def test_text_formatter(self):
        """测试文本格式化器"""
        formatter = TextFormatter()
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            logger_name="test",
            message="test message"
        )
        output = formatter.format(entry)
        assert "INFO" in output
        assert "test" in output
        assert "test message" in output

    def test_json_formatter(self):
        """测试JSON格式化器"""
        formatter = JSONFormatter()
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.DEBUG,
            logger_name="test",
            message="debug message"
        )
        output = formatter.format(entry)
        data = json.loads(output)
        assert data["level"] == "DEBUG"
        assert data["message"] == "debug message"

    def test_json_formatter_with_context(self):
        """测试带上下文的JSON格式化"""
        formatter = JSONFormatter()
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.WARNING,
            logger_name="test",
            message="warning",
            context={"code": 100}
        )
        output = formatter.format(entry)
        data = json.loads(output)
        assert data["context"]["code"] == 100

    def test_csv_formatter(self):
        """测试CSV格式化器"""
        formatter = CSVFormatter()
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            logger_name="test",
            message="error"
        )
        output = formatter.format(entry)
        assert output.startswith('"')


class TestMemoryHandler:
    """内存处理器测试"""

    def test_basic_handling(self):
        """测试基本处理"""
        handler = MemoryHandler(level=LogLevel.DEBUG)
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            logger_name="test",
            message="test"
        )
        handler.emit(entry)
        assert len(handler.entries) == 1

    def test_level_filtering(self):
        """测试级别过滤"""
        handler = MemoryHandler(level=LogLevel.WARNING)
        handler.emit(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.DEBUG,
            logger_name="test",
            message="debug"
        ))
        handler.emit(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            logger_name="test",
            message="error"
        ))
        assert len(handler.entries) == 1

    def test_get_entries(self):
        """测试获取条目"""
        handler = MemoryHandler()
        for i in range(10):
            handler.emit(LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                logger_name="test",
                message=f"message {i}"
            ))

        entries = handler.get_entries(limit=5)
        assert len(entries) == 5

    def test_clear(self):
        """测试清空"""
        handler = MemoryHandler()
        handler.emit(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            logger_name="test",
            message="test"
        ))
        handler.clear()
        assert len(handler.entries) == 0


class TestStructuredLogger:
    """结构化日志记录器测试"""

    def test_logger_creation(self):
        """测试日志记录器创建"""
        logger = create_test_logger("test_logger")
        assert logger.name == "test_logger"
        assert len(logger.handlers) > 0

    def test_memory_logger(self):
        """测试内存日志记录器"""
        logger, handler = create_memory_logger("memory_test")
        logger.info("test message")
        assert len(handler.entries) == 1
        assert handler.entries[0].message == "test message"

    def test_log_levels(self):
        """测试日志级别"""
        logger, handler = create_memory_logger("level_test")
        logger.level = LogLevel.INFO

        logger.trace("trace message")
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

        assert len(handler.entries) == 4

    def test_context_logging(self):
        """测试上下文日志"""
        logger, handler = create_memory_logger("context_test")
        logger.info("user action", user_id=42, action="login")
        entry = handler.entries[0]
        assert entry.context["user_id"] == 42
        assert entry.context["action"] == "login"

    def test_exception_logging(self):
        """测试异常日志"""
        logger, handler = create_memory_logger("exception_test")
        try:
            raise ValueError("test error")
        except ValueError as e:
            logger.error("operation failed", exception=e)

        entry = handler.entries[0]
        assert entry.exception is not None
        assert "ValueError" in entry.exception

    def test_adapter(self):
        """测试日志适配器"""
        logger, handler = create_memory_logger("adapter_test")
        adapter = LoggerAdapter(logger, task_id="task_123")

        adapter.info("processing")
        entry = handler.entries[0]
        assert entry.context["task_id"] == "task_123"
        assert entry.message == "processing"


class TestLogAggregator:
    """日志聚合器测试"""

    def test_get_logger(self):
        """测试获取日志记录器"""
        aggregator = LogAggregator()
        logger = aggregator.get_logger("test")
        assert logger.name == "test"

    def test_singleton_loggers(self):
        """测试单例日志记录器"""
        aggregator = LogAggregator()
        logger1 = aggregator.get_logger("singleton")
        logger2 = aggregator.get_logger("singleton")
        assert logger1 is logger2

    def test_set_level(self):
        """测试设置级别"""
        aggregator = LogAggregator()
        logger = aggregator.get_logger("level_test")
        original_level = logger.level

        aggregator.set_level("level_test", LogLevel.DEBUG)
        assert logger.level == LogLevel.DEBUG

        logger.level = original_level

    def test_set_all_level(self):
        """测试设置所有级别"""
        aggregator = LogAggregator()
        aggregator.get_logger("logger1")
        aggregator.get_logger("logger2")

        aggregator.set_all_level(LogLevel.CRITICAL)

        assert aggregator.loggers["logger1"].level == LogLevel.CRITICAL
        assert aggregator.loggers["logger2"].level == LogLevel.CRITICAL

    def test_list_loggers(self):
        """测试列出日志记录器"""
        aggregator = LogAggregator()
        aggregator.get_logger("log1")
        aggregator.get_logger("log2")

        names = aggregator.list_loggers()
        assert "log1" in names
        assert "log2" in names


class TestTimerLogger:
    """计时日志测试"""

    def test_successful_operation(self):
        """测试成功操作"""
        logger, handler = create_memory_logger("timer_test")

        with TimerLogger(logger, "database query"):
            time.sleep(0.01)

        assert len(handler.entries) == 2
        assert "开始" in handler.entries[0].message
        assert "完成" in handler.entries[1].message

    def test_failed_operation(self):
        """测试失败操作"""
        logger, handler = create_memory_logger("timer_error_test")

        try:
            with TimerLogger(logger, "risky operation"):
                raise RuntimeError("operation failed")
        except RuntimeError:
            pass

        assert len(handler.entries) == 2
        assert "失败" in handler.entries[1].message


class TestGetLogger:
    """全局日志器测试"""

    def test_default_logger(self):
        """测试默认日志器"""
        logger = get_logger()
        assert logger is not None
        assert logger.name == "maes"

    def test_custom_logger(self):
        """测试自定义日志器"""
        logger = get_logger("custom", LogLevel.DEBUG, LogFormat.JSON)
        assert logger.name == "custom"
        assert logger.level == LogLevel.DEBUG


class TestIntegration:
    """集成测试"""

    def test_multi_handler_logging(self):
        """测试多处理器日志"""
        logger = StructuredLogger(
            name="multi_handler",
            level=LogLevel.DEBUG,
            log_format=LogFormat.TEXT,
            destination=LogDestination.CONSOLE
        )

        handler1 = MemoryHandler()
        handler2 = MemoryHandler()

        logger.handlers.append(handler1)
        logger.handlers.append(handler2)

        logger.info("multi handler test")

        assert len(handler1.entries) == 1
        assert len(handler2.entries) == 1

    def test_context_integration(self):
        """测试上下文集成"""
        LogContext.set_context(request_id="req_123")

        logger, handler = create_memory_logger("context_integration")

        logger.info("processing request")

        entry = handler.entries[0]
        assert entry.context.get("request_id") == "req_123"

        LogContext.clear_context()

    def test_filter_chain(self):
        """测试过滤器链"""
        logger, handler = create_memory_logger("filter_test")

        def error_only_filter(entry: LogEntry) -> bool:
            return entry.level == LogLevel.ERROR

        handler.add_filter(error_only_filter)

        logger.info("should not appear")
        logger.error("should appear")

        assert len(handler.entries) == 1
        assert handler.entries[0].level == LogLevel.ERROR


def test_logger_thread_safety():
    """测试线程安全"""
    import threading

    logger, handler = create_memory_logger("thread_test")

    def log_messages(count):
        for i in range(count):
            logger.info(f"message {i}")

    threads = []
    for _ in range(5):
        t = threading.Thread(target=log_messages, args=(20,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(handler.entries) == 100


def test_log_levels_hierarchy():
    """测试日志级别层次"""
    assert LogLevel.TRACE.value < LogLevel.DEBUG.value
    assert LogLevel.DEBUG.value < LogLevel.INFO.value
    assert LogLevel.INFO.value < LogLevel.WARNING.value
    assert LogLevel.WARNING.value < LogLevel.ERROR.value
    assert LogLevel.ERROR.value < LogLevel.CRITICAL.value
