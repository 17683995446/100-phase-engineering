"""
任务验证系统
遵循信息完整公理: 确保输入信息完整、正确、有效
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum, auto
from datetime import datetime
import re

from src.utils.logger import logger


class ValidationLevel(Enum):
    """验证级别"""
    STRICT = auto()    # 严格验证
    NORMAL = auto()    # 普通验证
    LENIENT = auto()   # 宽松验证


class ValidationErrorType(Enum):
    """验证错误类型"""
    EMPTY_FIELD = auto()
    INVALID_FORMAT = auto()
    LENGTH_VIOLATION = auto()
    INVALID_TYPE = auto()
    MISSING_REQUIRED = auto()
    INVALID_VALUE = auto()
    SECURITY_RISK = auto()


@dataclass
class ValidationError:
    """验证错误"""
    error_id: str
    field_name: str
    error_type: ValidationErrorType
    message: str
    severity: str = "error"
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.now)
    
    def add_error(
        self,
        error_id: str,
        field_name: str,
        error_type: ValidationErrorType,
        message: str,
        suggestion: Optional[str] = None
    ):
        """添加错误"""
        self.errors.append(ValidationError(
            error_id=error_id,
            field_name=field_name,
            error_type=error_type,
            message=message,
            suggestion=suggestion
        ))
        self.valid = False
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)
    
    def get_errors_by_field(self, field_name: str) -> List[ValidationError]:
        """获取特定字段的错误"""
        return [e for e in self.errors if e.field_name == field_name]
    
    def get_errors_by_type(self, error_type: ValidationErrorType) -> List[ValidationError]:
        """获取特定类型的错误"""
        return [e for e in self.errors if e.error_type == error_type]


@dataclass
class ValidationRule:
    """验证规则"""
    rule_id: str
    field_name: str
    validator: Callable[[Any], bool]
    error_message: str
    error_type: ValidationErrorType
    severity: str = "error"
    enabled: bool = True


class TaskValidator:
    """任务验证器"""
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.rules: List[ValidationRule] = []
        self._setup_default_rules()
        logger.info(f"任务验证器初始化 (level={level.name})")
    
    def _setup_default_rules(self):
        """设置默认验证规则"""
        # 任务ID验证
        self.add_rule(ValidationRule(
            rule_id="task_id_format",
            field_name="task_id",
            validator=lambda x: bool(x) and len(str(x)) > 0,
            error_message="任务ID不能为空",
            error_type=ValidationErrorType.EMPTY_FIELD
        ))
        
        # 任务描述验证
        self.add_rule(ValidationRule(
            rule_id="description_not_empty",
            field_name="task_description",
            validator=lambda x: bool(x) and len(str(x).strip()) > 0,
            error_message="任务描述不能为空",
            error_type=ValidationErrorType.EMPTY_FIELD
        ))
        
        # 描述长度验证
        if self.level == ValidationLevel.STRICT:
            self.add_rule(ValidationRule(
                rule_id="description_min_length",
                field_name="task_description",
                validator=lambda x: len(str(x)) >= 10,
                error_message="任务描述至少需要10个字符",
                error_type=ValidationErrorType.LENGTH_VIOLATION
            ))
        
        self.add_rule(ValidationRule(
            rule_id="description_max_length",
            field_name="task_description",
            validator=lambda x: len(str(x)) <= 10000,
            error_message="任务描述不能超过10000个字符",
            error_type=ValidationErrorType.LENGTH_VIOLATION
        ))
        
        # 任务类型验证
        self.add_rule(ValidationRule(
            rule_id="task_type_valid",
            field_name="task_type",
            validator=self._validate_task_type,
            error_message="任务类型无效",
            error_type=ValidationErrorType.INVALID_TYPE
        ))
        
        # 安全检查
        self.add_rule(ValidationRule(
            rule_id="no_sql_injection",
            field_name="task_description",
            validator=lambda x: not self._contains_sql_injection(str(x)),
            error_message="检测到潜在的SQL注入风险",
            error_type=ValidationErrorType.SECURITY_RISK
        ))
        
        self.add_rule(ValidationRule(
            rule_id="no_path_traversal",
            field_name="task_description",
            validator=lambda x: not self._contains_path_traversal(str(x)),
            error_message="检测到潜在的路径遍历风险",
            error_type=ValidationErrorType.SECURITY_RISK
        ))
    
    def add_rule(self, rule: ValidationRule):
        """添加验证规则"""
        self.rules.append(rule)
        logger.debug(f"添加验证规则: {rule.rule_id}")
    
    def remove_rule(self, rule_id: str):
        """移除验证规则"""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.debug(f"移除验证规则: {rule_id}")
    
    def validate_task(self, task_data: Dict[str, Any]) -> ValidationResult:
        """
        验证任务数据
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            验证结果
        """
        result = ValidationResult(valid=True)
        
        logger.info(f"开始验证任务: {task_data.get('task_id', 'unknown')}")
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if rule.field_name not in task_data:
                continue
            
            value = task_data[rule.field_name]
            
            try:
                is_valid = rule.validator(value)
                
                if not is_valid:
                    result.add_error(
                        error_id=rule.rule_id,
                        field_name=rule.field_name,
                        error_type=rule.error_type,
                        message=rule.error_message
                    )
                    
                    logger.warning(f"验证失败: {rule.field_name} - {rule.error_message}")
            except Exception as e:
                logger.error(f"验证器执行异常: {rule.rule_id} - {e}")
                result.add_error(
                    error_id=f"{rule.rule_id}_exception",
                    field_name=rule.field_name,
                    error_type=ValidationErrorType.INVALID_FORMAT,
                    message=f"验证器执行异常: {e}"
                )
        
        if result.valid:
            logger.info("任务验证通过")
        else:
            logger.warning(f"任务验证失败: {len(result.errors)} 个错误")
        
        return result
    
    def _validate_task_type(self, task_type: Any) -> bool:
        """验证任务类型"""
        valid_types = {
            "requirement", "bugfix", "refactor", "test",
            "documentation", "other", "REQUIREMENT", "BUGFIX",
            "REFACTOR", "TEST", "DOCUMENTATION", "OTHER"
        }
        return str(task_type).lower() in valid_types
    
    def _contains_sql_injection(self, text: str) -> bool:
        """检查SQL注入风险"""
        sql_patterns = [
            r"'\s*OR\s+'1'\s*=\s*'1",
            r"DROP\s+TABLE",
            r"DELETE\s+FROM",
            r"INSERT\s+INTO",
            r"UPDATE\s+.*\s+SET",
            r"--\s*$",
            r";\s*DROP",
        ]
        
        text_lower = text.lower()
        for pattern in sql_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_path_traversal(self, text: str) -> bool:
        """检查路径遍历风险"""
        patterns = [
            r"\.\./",
            r"\.\.\\",
            r"/etc/passwd",
            r"c:\\windows",
            r"file://",
        ]
        
        for pattern in patterns:
            if pattern.lower() in text.lower():
                return True
        
        return False


class InputSanitizer:
    """输入清理器"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 10000) -> str:
        """清理字符串"""
        if not isinstance(value, str):
            return str(value)
        
        # 去除首尾空白
        sanitized = value.strip()
        
        # 限制长度
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # 移除控制字符
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        return sanitized
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """清理字典"""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputSanitizer.sanitize_string(v) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def remove_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """移除敏感数据"""
        sensitive_keys = {
            "password", "secret", "token", "api_key", "apikey",
            "private_key", "privatekey", "access_token"
        }
        
        cleaned = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                cleaned[key] = "***REDACTED***"
            elif isinstance(value, dict):
                cleaned[key] = InputSanitizer.remove_sensitive_data(value)
            else:
                cleaned[key] = value
        
        return cleaned


class EnhancedTaskInputHandler:
    """增强的任务输入处理器"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.NORMAL):
        self.validator = TaskValidator(validation_level)
        self.sanitizer = InputSanitizer()
        logger.info("增强任务输入处理器初始化")
    
    def process_task_input(
        self,
        task_description: str,
        task_type: str = "requirement",
        task_id: Optional[str] = None,
        priority: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理任务输入: 清理 + 验证 + 增强
        
        Args:
            task_description: 任务描述
            task_type: 任务类型
            task_id: 任务ID
            priority: 优先级
            metadata: 元数据
            
        Returns:
            处理结果
        """
        import uuid
        
        # 生成任务ID
        if not task_id:
            task_id = str(uuid.uuid4())
        
        # 准备任务数据
        task_data = {
            "task_id": task_id,
            "task_description": task_description,
            "task_type": task_type,
            "priority": priority or 2,
            "metadata": metadata or {}
        }
        
        # 清理输入
        sanitized = self.sanitizer.sanitize_dict(task_data)
        
        # 验证
        validation_result = self.validator.validate_task(sanitized)
        
        # 构建结果
        result = {
            "task_id": sanitized["task_id"],
            "task_type": sanitized["task_type"],
            "task_description": sanitized["task_description"],
            "priority": sanitized["priority"],
            "metadata": sanitized["metadata"],
            "validation": {
                "valid": validation_result.valid,
                "errors": [
                    {
                        "field": e.field_name,
                        "message": e.message,
                        "type": e.error_type.name
                    }
                    for e in validation_result.errors
                ],
                "warnings": validation_result.warnings
            },
            "processed_at": datetime.now().isoformat()
        }
        
        # 添加验证警告作为建议
        if validation_result.warnings:
            result["suggestions"] = validation_result.warnings
        
        logger.info(f"任务输入处理完成: {task_id}, 验证结果: {validation_result.valid}")
        
        return result
    
    def validate_only(self, task_data: Dict[str, Any]) -> ValidationResult:
        """仅验证"""
        return self.validator.validate_task(task_data)
    
    def sanitize_only(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """仅清理"""
        return self.sanitizer.sanitize_dict(task_data)
