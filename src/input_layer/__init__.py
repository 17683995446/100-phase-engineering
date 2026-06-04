"""
输入收敛层 - Layer 1
统一接收任务、类型判定、基础预处理、任务验证
"""

from .task_handler import TaskRequest, TaskPriority, TaskPreprocessor, TaskInputHandler
from .task_validator import (
    ValidationLevel,
    ValidationErrorType,
    ValidationError,
    ValidationResult,
    ValidationRule,
    TaskValidator,
    InputSanitizer,
    EnhancedTaskInputHandler
)

__all__ = [
    "TaskRequest",
    "TaskPriority",
    "TaskPreprocessor",
    "TaskInputHandler",
    "ValidationLevel",
    "ValidationErrorType",
    "ValidationError",
    "ValidationResult",
    "ValidationRule",
    "TaskValidator",
    "InputSanitizer",
    "EnhancedTaskInputHandler"
]
