# Phase 21: 输入层增强与任务验证

## 阶段目标

增强输入层功能，实现任务验证系统，确保输入信息完整、正确、有效，遵循信息完整公理。

## 核心成果

### 1. 验证系统核心类型

**文件**: `/workspace/src/input_layer/task_validator.py`

#### 验证级别 (ValidationLevel)
```python
class ValidationLevel(Enum):
    STRICT = auto()    # 严格验证
    NORMAL = auto()    # 普通验证
    LENIENT = auto()   # 宽松验证
```

#### 验证错误类型 (ValidationErrorType)
```python
class ValidationErrorType(Enum):
    EMPTY_FIELD = auto()      # 字段为空
    INVALID_FORMAT = auto()    # 格式无效
    LENGTH_VIOLATION = auto()  # 长度违规
    INVALID_TYPE = auto()       # 类型无效
    MISSING_REQUIRED = auto()  # 缺少必需字段
    INVALID_VALUE = auto()     # 值无效
    SECURITY_RISK = auto()     # 安全风险
```

### 2. 验证结果 (ValidationResult)

```python
@dataclass
class ValidationResult:
    valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    validated_at: datetime
    
    def add_error(error_id, field_name, error_type, message)
    def add_warning(warning)
    def get_errors_by_field(field_name)
    def get_errors_by_type(error_type)
```

### 3. 验证规则 (ValidationRule)

```python
@dataclass
class ValidationRule:
    rule_id: str
    field_name: str
    validator: Callable[[Any], bool]
    error_message: str
    error_type: ValidationErrorType
    severity: str
    enabled: bool
```

### 4. 任务验证器 (TaskValidator)

核心功能：
- `validate_task(task_data)` - 验证任务数据
- `add_rule(rule)` - 添加验证规则
- `remove_rule(rule_id)` - 移除验证规则
- 内置安全检查：SQL注入、路径遍历

### 5. 输入清理器 (InputSanitizer)

```python
class InputSanitizer:
    @staticmethod
    def sanitize_string(value, max_length=10000)  # 清理字符串
    
    @staticmethod
    def sanitize_dict(data)  # 清理字典
    
    @staticmethod
    def remove_sensitive_data(data)  # 移除敏感数据
```

### 6. 增强任务输入处理器 (EnhancedTaskInputHandler)

```python
class EnhancedTaskInputHandler:
    def process_task_input(...)  # 清理 + 验证 + 增强
    def validate_only(task_data)  # 仅验证
    def sanitize_only(task_data)  # 仅清理
```

## 技术特性

### 1. 多级验证

支持三种验证级别：
```python
validator_strict = TaskValidator(ValidationLevel.STRICT)  # 最严格
validator_normal = TaskValidator(ValidationLevel.NORMAL)  # 普通
validator_lenient = TaskValidator(ValidationLevel.LENIENT)  # 最宽松
```

### 2. 安全检查

防止常见的安全威胁：
- SQL注入检测
- 路径遍历检测
- 控制字符移除

### 3. 输入清理

自动清理用户输入：
- 去除首尾空白
- 限制最大长度
- 移除控制字符
- 敏感数据脱敏

### 4. 可扩展规则

支持自定义验证规则：
```python
validator.add_rule(ValidationRule(
    rule_id="custom",
    field_name="field",
    validator=lambda x: x > 0,
    error_message="必须大于0",
    error_type=ValidationErrorType.INVALID_VALUE
))
```

## 验证测试

**文件**: `/workspace/test_task_validator.py`

**测试覆盖**:
- 验证结果类 (4个测试)
- 任务验证器 (9个测试)
- 输入清理器 (4个测试)
- 增强处理器 (5个测试)
- 辅助功能 (4个测试)

**测试结果**: 26个测试全部通过 ✓

**整体系统测试**: 所有291个测试通过 ✓

## 与现有系统集成

### 1. 输入层导出

已将验证器导出到输入层：
```python
# src/input_layer/__init__.py
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
```

### 2. 任务处理器增强

在现有 TaskInputHandler 基础上增强：
- 保持原有接口兼容性
- 新增验证功能
- 新增清理功能

## 使用示例

### 1. 基本验证

```python
from src.input_layer.task_validator import TaskValidator

validator = TaskValidator()

task_data = {
    "task_id": "task-001",
    "task_description": "这是一个有效的任务描述",
    "task_type": "requirement"
}

result = validator.validate_task(task_data)
print(f"Valid: {result.valid}")
```

### 2. 增强处理

```python
from src.input_layer.task_validator import EnhancedTaskInputHandler

handler = EnhancedTaskInputHandler()

result = handler.process_task_input(
    task_description="  任务描述  ",
    task_type="requirement"
)

print(f"任务ID: {result['task_id']}")
print(f"清理后描述: {result['task_description']}")
print(f"验证结果: {result['validation']['valid']}")
```

### 3. 自定义规则

```python
from src.input_layer.task_validator import TaskValidator, ValidationRule, ValidationErrorType

validator = TaskValidator()

validator.add_rule(ValidationRule(
    rule_id="priority_range",
    field_name="priority",
    validator=lambda x: 1 <= x <= 5,
    error_message="优先级必须在1-5之间",
    error_type=ValidationErrorType.INVALID_VALUE
))
```

### 4. 安全清理

```python
from src.input_layer.task_validator import InputSanitizer

sanitized = InputSanitizer.sanitize_string("  原始输入  ")
print(f"清理后: {sanitized}")

cleaned = InputSanitizer.remove_sensitive_data({
    "username": "user",
    "password": "secret"
})
print(f"脱敏后: {cleaned}")  # password变为 "***REDACTED***"
```

## 架构位置

**输入层 (input_layer)** 核心组件：
- 位置: `src/input_layer/task_validator.py`
- 导出: `src/input_layer/__init__.py`
- 依赖: 无外部依赖

## 设计原则

1. **信息完整性**: 确保输入信息完整、正确、有效
2. **安全性**: 防止SQL注入、路径遍历等安全威胁
3. **可扩展性**: 支持自定义验证规则
4. **灵活性**: 支持三种验证级别
5. **友好性**: 提供清晰的错误信息和修复建议

## 统计

- **代码行数**: ~430行
- **测试用例**: 26个
- **测试通过率**: 100%
- **验证级别**: 3种
- **错误类型**: 7种
- **导出API**: 8个

## 下一步

Phase 22-100 将继续完善系统，增加更多高级功能和特性。
