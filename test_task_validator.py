"""
任务验证系统验证测试
"""

import pytest
from datetime import datetime
from src.input_layer.task_validator import (
    ValidationLevel,
    ValidationErrorType,
    ValidationError,
    ValidationResult,
    ValidationRule,
    TaskValidator,
    InputSanitizer,
    EnhancedTaskInputHandler
)


class TestValidationResult:
    """测试验证结果"""
    
    def test_result_creation(self):
        """测试创建验证结果"""
        result = ValidationResult(valid=True)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_add_error(self):
        """测试添加错误"""
        result = ValidationResult(valid=True)
        
        result.add_error(
            error_id="test_error",
            field_name="test_field",
            error_type=ValidationErrorType.EMPTY_FIELD,
            message="Test error message"
        )
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field_name == "test_field"
    
    def test_add_warning(self):
        """测试添加警告"""
        result = ValidationResult(valid=True)
        
        result.add_warning("This is a warning")
        
        assert len(result.warnings) == 1
    
    def test_get_errors_by_field(self):
        """测试按字段获取错误"""
        result = ValidationResult(valid=False)
        
        result.add_error("e1", "field_a", ValidationErrorType.EMPTY_FIELD, "Error 1")
        result.add_error("e2", "field_b", ValidationErrorType.INVALID_FORMAT, "Error 2")
        result.add_error("e3", "field_a", ValidationErrorType.LENGTH_VIOLATION, "Error 3")
        
        errors = result.get_errors_by_field("field_a")
        assert len(errors) == 2


class TestTaskValidator:
    """测试任务验证器"""
    
    def test_validator_creation(self):
        """测试创建验证器"""
        validator = TaskValidator()
        assert validator is not None
        assert len(validator.rules) > 0
    
    def test_validator_with_strict_level(self):
        """测试严格级别验证器"""
        validator = TaskValidator(ValidationLevel.STRICT)
        assert validator.level == ValidationLevel.STRICT
        # 严格模式应该有更多规则
        assert len(validator.rules) > 5
    
    def test_validate_valid_task(self):
        """测试验证有效任务"""
        validator = TaskValidator()
        
        task_data = {
            "task_id": "task-001",
            "task_description": "这是一个有效的任务描述",
            "task_type": "requirement"
        }
        
        result = validator.validate_task(task_data)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_empty_description(self):
        """测试验证空描述"""
        validator = TaskValidator()
        
        task_data = {
            "task_id": "task-002",
            "task_description": "",
            "task_type": "requirement"
        }
        
        result = validator.validate_task(task_data)
        
        assert result.valid is False
        errors = result.get_errors_by_field("task_description")
        assert len(errors) > 0
    
    def test_validate_empty_task_id(self):
        """测试验证空任务ID"""
        validator = TaskValidator()
        
        task_data = {
            "task_id": "",
            "task_description": "有效描述",
            "task_type": "requirement"
        }
        
        result = validator.validate_task(task_data)
        
        assert result.valid is False
    
    def test_validate_sql_injection(self):
        """测试验证SQL注入"""
        validator = TaskValidator()
        
        task_data = {
            "task_id": "task-003",
            "task_description": "'; DROP TABLE users; --",
            "task_type": "requirement"
        }
        
        result = validator.validate_task(task_data)
        
        assert result.valid is False
        errors = result.get_errors_by_type(ValidationErrorType.SECURITY_RISK)
        assert len(errors) > 0
    
    def test_validate_path_traversal(self):
        """测试验证路径遍历"""
        validator = TaskValidator()
        
        task_data = {
            "task_id": "task-004",
            "task_description": "读取 /etc/passwd 文件",
            "task_type": "requirement"
        }
        
        result = validator.validate_task(task_data)
        
        assert result.valid is False
        errors = result.get_errors_by_type(ValidationErrorType.SECURITY_RISK)
        assert len(errors) > 0
    
    def test_validate_description_too_long(self):
        """测试验证描述过长"""
        validator = TaskValidator()
        
        task_data = {
            "task_id": "task-005",
            "task_description": "x" * 20000,  # 超过10000字符
            "task_type": "requirement"
        }
        
        result = validator.validate_task(task_data)
        
        assert result.valid is False
        errors = result.get_errors_by_type(ValidationErrorType.LENGTH_VIOLATION)
        assert len(errors) > 0
    
    def test_validate_invalid_task_type(self):
        """测试验证无效任务类型"""
        validator = TaskValidator()
        
        task_data = {
            "task_id": "task-006",
            "task_description": "有效描述",
            "task_type": "invalid_type"
        }
        
        result = validator.validate_task(task_data)
        
        assert result.valid is False
    
    def test_add_remove_rule(self):
        """测试添加和移除规则"""
        validator = TaskValidator()
        
        initial_count = len(validator.rules)
        
        rule = ValidationRule(
            rule_id="custom_rule",
            field_name="custom_field",
            validator=lambda x: bool(x),
            error_message="Custom error",
            error_type=ValidationErrorType.INVALID_VALUE
        )
        
        validator.add_rule(rule)
        assert len(validator.rules) == initial_count + 1
        
        validator.remove_rule("custom_rule")
        assert len(validator.rules) == initial_count


class TestInputSanitizer:
    """测试输入清理器"""
    
    def test_sanitize_string(self):
        """测试清理字符串"""
        sanitized = InputSanitizer.sanitize_string("  原始字符串  ")
        assert sanitized == "原始字符串"
    
    def test_sanitize_max_length(self):
        """测试长度限制"""
        long_string = "x" * 20000
        sanitized = InputSanitizer.sanitize_string(long_string, max_length=100)
        assert len(sanitized) == 100
    
    def test_sanitize_dict(self):
        """测试清理字典"""
        data = {
            "name": "  测试  ",
            "description": "描述内容"
        }
        
        sanitized = InputSanitizer.sanitize_dict(data)
        
        assert sanitized["name"] == "测试"
        assert sanitized["description"] == "描述内容"
    
    def test_remove_sensitive_data(self):
        """测试移除敏感数据"""
        data = {
            "username": "testuser",
            "password": "secret123",
            "token": "abc123"
        }
        
        cleaned = InputSanitizer.remove_sensitive_data(data)
        
        assert cleaned["username"] == "testuser"
        assert cleaned["password"] == "***REDACTED***"
        assert cleaned["token"] == "***REDACTED***"


class TestEnhancedTaskInputHandler:
    """测试增强的任务输入处理器"""
    
    def test_handler_creation(self):
        """测试创建处理器"""
        handler = EnhancedTaskInputHandler()
        assert handler is not None
        assert handler.validator is not None
    
    def test_process_valid_input(self):
        """测试处理有效输入"""
        handler = EnhancedTaskInputHandler()
        
        result = handler.process_task_input(
            task_description="这是一个有效的任务描述",
            task_type="requirement"
        )
        
        assert result["task_id"] is not None
        assert result["validation"]["valid"] is True
        assert len(result["validation"]["errors"]) == 0
    
    def test_process_invalid_input(self):
        """测试处理无效输入"""
        handler = EnhancedTaskInputHandler()
        
        result = handler.process_task_input(
            task_description="",
            task_type="requirement"
        )
        
        assert result["validation"]["valid"] is False
        assert len(result["validation"]["errors"]) > 0
    
    def test_process_with_security_risk(self):
        """测试处理有安全风险的输入"""
        handler = EnhancedTaskInputHandler()
        
        result = handler.process_task_input(
            task_description="'; DROP TABLE users; --",
            task_type="requirement"
        )
        
        assert result["validation"]["valid"] is False
        error_types = [e["type"] for e in result["validation"]["errors"]]
        assert "SECURITY_RISK" in error_types
    
    def test_validate_only(self):
        """测试仅验证"""
        handler = EnhancedTaskInputHandler()
        
        task_data = {
            "task_id": "task-007",
            "task_description": "测试描述",
            "task_type": "requirement"
        }
        
        result = handler.validate_only(task_data)
        
        assert result.valid is True
    
    def test_sanitize_only(self):
        """测试仅清理"""
        handler = EnhancedTaskInputHandler()
        
        data = {
            "field": "  原始数据  "
        }
        
        sanitized = handler.sanitize_only(data)
        
        assert sanitized["field"] == "原始数据"


def test_sanitizer_control_characters():
    """测试移除控制字符"""
    original = "Hello\x00World\x1f"
    sanitized = InputSanitizer.sanitize_string(original)
    assert "\x00" not in sanitized
    assert "\x1f" not in sanitized


def test_sanitizer_nested_dict():
    """测试嵌套字典清理"""
    data = {
        "outer": {
            "inner": "  嵌套值  ",
            "list": ["  值1  ", "  值2  "]
        }
    }
    
    sanitized = InputSanitizer.sanitize_dict(data)
    
    assert sanitized["outer"]["inner"] == "嵌套值"
    assert sanitized["outer"]["list"][0] == "值1"
