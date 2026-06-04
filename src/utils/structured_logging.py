"""
结构化日志系统
遵循信息显式化公理：日志结构化、可追溯、可分析
"""

import logging
import json
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from collections import deque
import threading
import gzip
import os

from src.config.constants import LOGS_DIR


class LogLevel(Enum):
    """日志级别"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogFormat(Enum):
    """日志格式"""
    TEXT = auto()      # 文本格式
    JSON = auto()      # JSON格式
    CSV = auto()       # CSV格式（简单）
    STRUCTURED = auto() # 结构化文本


class LogDestination(Enum):
    """日志目标"""
    CONSOLE = auto()
    FILE = auto()
    CONSOLE_AND_FILE = auto()


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    logger_name: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    module: str = ""
    function: str = ""
    line_number: int = 0
    thread_id: int = 0
    process_id: int = 0
    exception: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "logger": self.logger_name,
            "message": self.message,
            "context": self.context,
            "module": self.module,
            "function": self.function,
            "line": self.line_number,
            "thread_id": self.thread_id,
            "process_id": self.process_id,
            "exception": self.exception
        }


class LogContext:
    """日志上下文管理器"""

    _local = threading.local()

    @classmethod
    def set_context(cls, **kwargs):
        """设置上下文"""
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        cls._local.context.update(kwargs)

    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """获取当前上下文"""
        return getattr(cls._local, 'context', {}).copy()

    @classmethod
    def clear_context(cls):
        """清除上下文"""
        cls._local.context = {}

    @classmethod
    def get_value(cls, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        return cls.get_context().get(key, default)


class LogFormatter:
    """日志格式化器基类"""

    def format(self, entry: LogEntry) -> str:
        """格式化日志条目"""
        raise NotImplementedError


class TextFormatter(LogFormatter):
    """文本格式化器"""

    def __init__(
        self,
        fmt: str = "%(timestamp)s [%(level)s] %(logger)s: %(message)s",
        timestamp_fmt: str = "%Y-%m-%d %H:%M:%S"
    ):
        self.fmt = fmt
        self.timestamp_fmt = timestamp_fmt

    def format(self, entry: LogEntry) -> str:
        """格式化日志为文本"""
        parts = {
            "timestamp": entry.timestamp.strftime(self.timestamp_fmt),
            "level": entry.level.name,
            "logger": entry.logger_name,
            "message": entry.message,
            "module": entry.module,
            "function": entry.function,
            "line": entry.line_number
        }

        message = self.fmt % parts

        if entry.context:
            context_str = " | ".join(f"{k}={v}" for k, v in entry.context.items())
            message = f"{message} | {context_str}"

        if entry.exception:
            message = f"{message}\n{entry.exception}"

        return message


class JSONFormatter(LogFormatter):
    """JSON格式化器"""

    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def format(self, entry: LogEntry) -> str:
        """格式化日志为JSON"""
        data = entry.to_dict()
        return json.dumps(data, indent=self.indent, ensure_ascii=self.ensure_ascii)


class CSVFormatter(LogFormatter):
    """CSV格式化器（简单）"""

    def format(self, entry: LogEntry) -> str:
        """格式化日志为CSV"""
        fields = [
            entry.timestamp.isoformat(),
            entry.level.name,
            entry.logger_name,
            entry.message.replace(',', ';'),
            str(entry.context).replace(',', ';'),
            entry.module,
            str(entry.line_number)
        ]
        return ",".join(f'"{f}"' for f in fields)


class LogHandler:
    """日志处理器基类"""

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        formatter: Optional[LogFormatter] = None
    ):
        self.level = level
        self.formatter = formatter or TextFormatter()
        self.filters: List[Callable[[LogEntry], bool]] = []

    def add_filter(self, filter_func: Callable[[LogEntry], bool]):
        """添加过滤器"""
        self.filters.append(filter_func)

    def emit(self, entry: LogEntry):
        """输出日志"""
        raise NotImplementedError

    def should_emit(self, entry: LogEntry) -> bool:
        """检查是否应该输出"""
        if entry.level.value < self.level.value:
            return False

        for filter_func in self.filters:
            if not filter_func(entry):
                return False

        return True


class ConsoleHandler(LogHandler):
    """控制台处理器"""

    def __init__(self, level: LogLevel = LogLevel.INFO, colorize: bool = True):
        super().__init__(level)
        self.colorize = colorize
        self._colors = {
            LogLevel.TRACE: "\033[36m",     # 青色
            LogLevel.DEBUG: "\033[34m",     # 蓝色
            LogLevel.INFO: "\033[32m",      # 绿色
            LogLevel.WARNING: "\033[33m",   # 黄色
            LogLevel.ERROR: "\033[31m",     # 红色
            LogLevel.CRITICAL: "\033[35m",  # 紫色
        }
        self._reset = "\033[0m"

    def emit(self, entry: LogEntry):
        """输出到控制台"""
        if not self.should_emit(entry):
            return

        message = self.formatter.format(entry)

        if self.colorize and sys.stdout.isatty():
            color = self._colors.get(entry.level, "")
            message = f"{color}{message}{self._reset}"

        print(message, file=sys.stdout if entry.level.value < LogLevel.ERROR.value else sys.stderr)


class FileHandler(LogHandler):
    """文件处理器"""

    def __init__(
        self,
        file_path: Union[str, Path],
        level: LogLevel = LogLevel.DEBUG,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        encoding: str = "utf-8"
    ):
        super().__init__(level)
        self.file_path = Path(file_path)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.encoding = encoding
        self._lock = threading.RLock()

        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, entry: LogEntry):
        """输出到文件"""
        if not self.should_emit(entry):
            return

        with self._lock:
            self._rotate_if_needed()

            message = self.formatter.format(entry) + "\n"

            with open(self.file_path, "a", encoding=self.encoding) as f:
                f.write(message)

    def _rotate_if_needed(self):
        """检查并轮转文件"""
        if self.file_path.exists() and self.file_path.stat().st_size >= self.max_bytes:
            self._rotate()

    def _rotate(self):
        """执行文件轮转"""
        for i in range(self.backup_count - 1, 0, -1):
            current = self.file_path.with_suffix(f".{i}")
            next_file = self.file_path.with_suffix(f".{i + 1}")

            if current.exists():
                if next_file.exists():
                    next_file.unlink()
                current.rename(next_file)

        if self.file_path.exists():
            self.file_path.rename(self.file_path.with_suffix(".1"))

        self._compress_old_logs()

    def _compress_old_logs(self):
        """压缩旧日志"""
        for i in range(1, self.backup_count + 1):
            old_file = self.file_path.with_suffix(f".{i}")
            compressed = old_file.with_suffix(".gz")

            if old_file.exists() and not compressed.exists():
                try:
                    with open(old_file, 'rb') as f_in:
                        with gzip.open(compressed, 'wb') as f_out:
                            f_out.writelines(f_in)
                    old_file.unlink()
                except Exception:
                    pass


class MemoryHandler(LogHandler):
    """内存处理器（用于测试）"""

    def __init__(self, level: LogLevel = LogLevel.DEBUG, max_entries: int = 1000):
        super().__init__(level)
        self.max_entries = max_entries
        self.entries: deque = deque(maxlen=max_entries)
        self._lock = threading.RLock()

    def emit(self, entry: LogEntry):
        """添加到内存"""
        if not self.should_emit(entry):
            return

        with self._lock:
            self.entries.append(entry)

    def get_entries(
        self,
        level: Optional[LogLevel] = None,
        limit: Optional[int] = None
    ) -> List[LogEntry]:
        """获取日志条目"""
        with self._lock:
            entries = list(self.entries)

            if level:
                entries = [e for e in entries if e.level == level]

            if limit:
                entries = entries[-limit:]

            return entries

    def clear(self):
        """清空内存"""
        with self._lock:
            self.entries.clear()


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        log_format: LogFormat = LogFormat.TEXT,
        destination: LogDestination = LogDestination.CONSOLE_AND_FILE,
        log_dir: Optional[Path] = None
    ):
        self.name = name
        self.level = level
        self.log_format = log_format
        self.destination = destination
        self.handlers: List[LogHandler] = []
        self._lock = threading.RLock()

        formatter = self._create_formatter()

        if destination in [LogDestination.CONSOLE, LogDestination.CONSOLE_AND_FILE]:
            console_handler = ConsoleHandler(level, colorize=True)
            console_handler.formatter = formatter
            self.handlers.append(console_handler)

        if destination in [LogDestination.FILE, LogDestination.CONSOLE_AND_FILE]:
            log_dir = log_dir or LOGS_DIR
            log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = FileHandler(log_file, level)
            file_handler.formatter = formatter
            self.handlers.append(file_handler)

    def _create_formatter(self) -> LogFormatter:
        """创建格式化器"""
        if self.log_format == LogFormat.TEXT:
            return TextFormatter()
        elif self.log_format == LogFormat.JSON:
            return JSONFormatter()
        elif self.log_format == LogFormat.CSV:
            return CSVFormatter()
        elif self.log_format == LogFormat.STRUCTURED:
            return TextFormatter("%(timestamp)s [%(level)s] %(logger)s: %(message)s | context=%(context)s")
        else:
            return TextFormatter()

    def _create_entry(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ) -> LogEntry:
        """创建日志条目"""
        frame = sys._getframe(3)

        log_context = LogContext.get_context()
        merged_context = {**log_context, **(context or {})}

        return LogEntry(
            timestamp=datetime.now(),
            level=level,
            logger_name=self.name,
            message=message,
            context=merged_context,
            module=frame.f_code.co_filename.split('/')[-1] if frame else "",
            function=frame.f_code.co_name if frame else "",
            line_number=frame.f_lineno if frame else 0,
            thread_id=threading.current_thread().ident,
            process_id=os.getpid(),
            exception=traceback.format_exc() if exception else None
        )

    def _emit(self, entry: LogEntry):
        """发送日志到所有处理器"""
        with self._lock:
            for handler in self.handlers:
                try:
                    handler.emit(entry)
                except Exception:
                    pass

    def trace(self, message: str, **kwargs):
        """TRACE级别日志"""
        if self.level.value <= LogLevel.TRACE.value:
            entry = self._create_entry(LogLevel.TRACE, message, kwargs)
            self._emit(entry)

    def debug(self, message: str, **kwargs):
        """DEBUG级别日志"""
        if self.level.value <= LogLevel.DEBUG.value:
            entry = self._create_entry(LogLevel.DEBUG, message, kwargs)
            self._emit(entry)

    def info(self, message: str, **kwargs):
        """INFO级别日志"""
        if self.level.value <= LogLevel.INFO.value:
            entry = self._create_entry(LogLevel.INFO, message, kwargs)
            self._emit(entry)

    def warning(self, message: str, **kwargs):
        """WARNING级别日志"""
        if self.level.value <= LogLevel.WARNING.value:
            entry = self._create_entry(LogLevel.WARNING, message, kwargs)
            self._emit(entry)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """ERROR级别日志"""
        if self.level.value <= LogLevel.ERROR.value:
            entry = self._create_entry(LogLevel.ERROR, message, kwargs, exception)
            self._emit(entry)

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """CRITICAL级别日志"""
        if self.level.value <= LogLevel.CRITICAL.value:
            entry = self._create_entry(LogLevel.CRITICAL, message, kwargs, exception)
            self._emit(entry)

    def log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ):
        """通用日志方法"""
        if self.level.value <= level.value:
            entry = self._create_entry(level, message, context, exception)
            self._emit(entry)


class LoggerAdapter:
    """日志适配器（支持上下文）"""

    def __init__(self, logger: StructuredLogger, **context):
        self.logger = logger
        self.context = context

    def trace(self, message: str, **kwargs):
        merged_context = {**self.context, **kwargs}
        self.logger.trace(message, **merged_context)

    def debug(self, message: str, **kwargs):
        merged_context = {**self.context, **kwargs}
        self.logger.debug(message, **merged_context)

    def info(self, message: str, **kwargs):
        merged_context = {**self.context, **kwargs}
        self.logger.info(message, **merged_context)

    def warning(self, message: str, **kwargs):
        merged_context = {**self.context, **kwargs}
        self.logger.warning(message, **merged_context)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        merged_context = {**self.context, **kwargs}
        self.logger.error(message, exception, **merged_context)

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        merged_context = {**self.context, **kwargs}
        self.logger.critical(message, exception, **merged_context)


class LogAggregator:
    """日志聚合器"""

    def __init__(self):
        self.loggers: Dict[str, StructuredLogger] = {}
        self._lock = threading.RLock()

    def get_logger(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        log_format: LogFormat = LogFormat.TEXT,
        destination: LogDestination = LogDestination.CONSOLE_AND_FILE
    ) -> StructuredLogger:
        """获取或创建日志记录器"""
        with self._lock:
            if name not in self.loggers:
                self.loggers[name] = StructuredLogger(name, level, log_format, destination)
            return self.loggers[name]

    def set_level(self, name: str, level: LogLevel):
        """设置日志级别"""
        with self._lock:
            if name in self.loggers:
                self.loggers[name].level = level

    def set_all_level(self, level: LogLevel):
        """设置所有日志级别"""
        with self._lock:
            for logger in self.loggers.values():
                logger.level = level

    def list_loggers(self) -> List[str]:
        """列出所有日志记录器"""
        with self._lock:
            return list(self.loggers.keys())


_default_aggregator = LogAggregator()


def get_logger(
    name: str = "maes",
    level: LogLevel = LogLevel.INFO,
    log_format: LogFormat = LogFormat.TEXT,
    destination: LogDestination = LogDestination.CONSOLE_AND_FILE
) -> StructuredLogger:
    """获取结构化日志记录器"""
    return _default_aggregator.get_logger(name, level, log_format, destination)


def create_test_logger(name: str = "test") -> StructuredLogger:
    """创建测试用日志记录器"""
    return StructuredLogger(
        name=name,
        level=LogLevel.DEBUG,
        log_format=LogFormat.TEXT,
        destination=LogDestination.CONSOLE
    )


def create_memory_logger(name: str = "memory") -> tuple:
    """创建内存日志记录器（用于测试）"""
    logger = StructuredLogger(
        name=name,
        level=LogLevel.DEBUG,
        log_format=LogFormat.TEXT,
        destination=LogDestination.CONSOLE
    )
    memory_handler = MemoryHandler()
    logger.handlers.append(memory_handler)
    return logger, memory_handler


class TimerLogger:
    """计时日志上下文管理器"""

    def __init__(
        self,
        logger: StructuredLogger,
        operation: str,
        level: LogLevel = LogLevel.INFO,
        **context
    ):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.context = context
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(self.level, f"开始: {self.operation}", **self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time

        if exc_type is None:
            self.logger.log(
                self.level,
                f"完成: {self.operation} (耗时: {elapsed:.3f}s)",
                **self.context
            )
        else:
            self.logger.error(
                f"失败: {self.operation} (耗时: {elapsed:.3f}s)",
                exception=exc_val,
                error_type=exc_type.__name__,
                **self.context
            )

        return False
