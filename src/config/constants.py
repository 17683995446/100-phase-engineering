"""
全局常量定义
遵循第一性原理，信息显式化
"""

from pathlib import Path
from enum import Enum


PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
INPUT_LAYER_DIR = SRC_DIR / "input_layer"
SCHEDULING_LAYER_DIR = SRC_DIR / "scheduling_layer"
AGENT_LAYER_DIR = SRC_DIR / "agent_layer"
EXECUTION_LAYER_DIR = SRC_DIR / "execution_layer"
CONFIG_DIR = SRC_DIR / "config"
UTILS_DIR = SRC_DIR / "utils"
LOGS_DIR = PROJECT_ROOT / "logs"
DOCS_DIR = PROJECT_ROOT / "docs"
TESTS_DIR = PROJECT_ROOT / "tests"

for dir_path in [LOGS_DIR, DOCS_DIR, TESTS_DIR]:
    dir_path.mkdir(exist_ok=True)


class TaskType:
    REQUIREMENT = "requirement"
    REFACTOR = "refactor"
    BUGFIX = "bugfix"
    REVIEW = "review"
    TEST = "test"


class StateType:
    SYSTEM = "system"
    TASK = "task"
    BUSINESS = "business"


class AgentRole:
    ORCHESTRATOR = "orchestrator"
    ANALYZER = "analyzer"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    DEBUGGER = "debugger"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DOCUMENTER = "documenter"


class ErrorCode(Enum):
    """全局错误码体系 - 1000-9999"""
    # 系统错误 1000-1999
    SYSTEM_INIT_FAILED = (1000, "系统初始化失败")
    SYSTEM_CONFIG_ERROR = (1001, "系统配置错误")
    SYSTEM_STATE_CORRUPTED = (1002, "系统状态损坏")
    SYSTEM_UNEXPECTED_SHUTDOWN = (1003, "系统异常关闭")
    
    # 输入层错误 2000-2999
    INPUT_TASK_INVALID = (2000, "无效的任务输入")
    INPUT_TASK_TOO_LONG = (2001, "任务描述过长")
    INPUT_TASK_TYPE_UNKNOWN = (2002, "未知任务类型")
    INPUT_METADATA_INVALID = (2003, "无效的元数据")
    INPUT_PRIORITY_INVALID = (2004, "无效的优先级")
    
    # 调度层错误 3000-3999
    SCHEDULE_WORKFLOW_ERROR = (3000, "工作流调度错误")
    SCHEDULE_DAG_CYCLE_DETECTED = (3001, "检测到循环依赖")
    SCHEDULE_STATE_MACHINE_ERROR = (3002, "状态机错误")
    SCHEDULE_TASK_NOT_FOUND = (3003, "任务未找到")
    SCHEDULE_TIMEOUT = (3004, "调度超时")
    
    # Agent层错误 4000-4999
    AGENT_NOT_FOUND = (4000, "Agent未找到")
    AGENT_INIT_FAILED = (4001, "Agent初始化失败")
    AGENT_COMMUNICATION_ERROR = (4002, "Agent通信错误")
    AGENT_ROLE_CONFLICT = (4003, "Agent角色冲突")
    AGENT_RESPONSE_INVALID = (4004, "Agent响应无效")
    AGENT_COLLABORATION_FAILED = (4005, "Agent协作失败")
    AGENT_RESPONSIBILITY_OVERLAP = (4006, "Agent职责重叠")
    AGENT_RESPONSIBILITY_GAP = (4007, "Agent职责空缺")
    
    # 执行层错误 5000-5999
    EXECUTION_CODE_PARSE_ERROR = (5000, "代码解析错误")
    EXECUTION_CODE_SYNTAX_ERROR = (5001, "代码语法错误")
    EXECUTION_ATOMIC_VIOLATION = (5002, "原子化约束违反")
    EXECUTION_DEPENDENCY_VIOLATION = (5003, "依赖约束违反")
    EXECUTION_TEST_FAILED = (5004, "测试执行失败")
    EXECUTION_REVIEW_FAILED = (5005, "代码评审失败")
    EXECUTION_FORMAT_ERROR = (5006, "格式化错误")
    
    # 架构约束错误 6000-6999
    ARCH_LAYER_VIOLATION = (6000, "违反层级约束")
    ARCH_DEPENDENCY_VIOLATION = (6001, "违反依赖约束")
    ARCH_STATE_LEAK = (6002, "状态泄露")
    ARCH_IMPLICIT_STATE = (6003, "存在隐式状态")
    ARCH_CIRCULAR_DEPENDENCY = (6004, "循环依赖")
    ARCH_RESPONSIBILITY_VIOLATION = (6005, "违反职责约束")
    
    # 业务错误 7000-7999
    BUSINESS_REQUIREMENT_INVALID = (7000, "无效的需求")
    BUSINESS_ARCHITECTURE_REJECTED = (7001, "架构方案被拒绝")
    BUSINESS_CODE_CHANGES_INVALID = (7002, "代码变更无效")
    BUSINESS_REVIEW_COMMENTS_INVALID = (7003, "评审意见无效")
    BUSINESS_TEST_CASES_INSUFFICIENT = (7004, "测试用例不足")
    BUSINESS_VALIDATION_FAILED = (7005, "业务验证失败")
    
    # 通用错误 9000-9999
    UNKNOWN_ERROR = (9000, "未知错误")
    VALIDATION_FAILED = (9001, "验证失败")
    OPERATION_NOT_ALLOWED = (9002, "操作不允许")
    RESOURCE_NOT_FOUND = (9003, "资源未找到")
    INSUFFICIENT_PERMISSIONS = (9004, "权限不足")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

    @classmethod
    def get_message(cls, code: int) -> str:
        for error in cls:
            if error.code == code:
                return error.message
        return cls.UNKNOWN_ERROR.message

    @classmethod
    def get_category(cls, code: int) -> str:
        if 1000 <= code < 2000:
            return "系统错误"
        elif 2000 <= code < 3000:
            return "输入层错误"
        elif 3000 <= code < 4000:
            return "调度层错误"
        elif 4000 <= code < 5000:
            return "Agent层错误"
        elif 5000 <= code < 6000:
            return "执行层错误"
        elif 6000 <= code < 7000:
            return "架构约束错误"
        elif 7000 <= code < 8000:
            return "业务错误"
        else:
            return "通用错误"


class LayerName:
    """四层架构名称"""
    INPUT_LAYER = "input_layer"
    SCHEDULING_LAYER = "scheduling_layer"
    AGENT_LAYER = "agent_layer"
    EXECUTION_LAYER = "execution_layer"

    @classmethod
    def get_all(cls):
        return [
            cls.INPUT_LAYER,
            cls.SCHEDULING_LAYER,
            cls.AGENT_LAYER,
            cls.EXECUTION_LAYER
        ]

    @classmethod
    def get_dependency_order(cls):
        return [
            cls.INPUT_LAYER,
            cls.SCHEDULING_LAYER,
            cls.AGENT_LAYER,
            cls.EXECUTION_LAYER
        ]


class AtomicEntity:
    """原子实体定义 - 不可再分的最小实体"""
    # 任务相关
    TASK = "task"
    TASK_ID = "task_id"
    TASK_STATUS = "task_status"
    TASK_PRIORITY = "task_priority"
    
    # 代码相关
    VARIABLE = "variable"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"
    
    # 消息相关
    MESSAGE = "message"
    MESSAGE_ID = "message_id"
    MESSAGE_TYPE = "message_type"
    MESSAGE_CONTENT = "message_content"
    
    # 状态相关
    STATE = "state"
    STATE_ID = "state_id"
    STATE_TYPE = "state_type"
    STATE_VALUE = "state_value"
    
    # Agent相关
    AGENT = "agent"
    AGENT_ID = "agent_id"
    AGENT_ROLE = "agent_role"
    AGENT_CAPABILITY = "agent_capability"
    
    # 事件相关
    EVENT = "event"
    EVENT_ID = "event_id"
    EVENT_TYPE = "event_type"
    EVENT_DATA = "event_data"

    @classmethod
    def get_all(cls):
        return [
            # 任务实体
            cls.TASK, cls.TASK_ID, cls.TASK_STATUS, cls.TASK_PRIORITY,
            # 代码实体
            cls.VARIABLE, cls.METHOD, cls.CLASS, cls.MODULE,
            # 消息实体
            cls.MESSAGE, cls.MESSAGE_ID, cls.MESSAGE_TYPE, cls.MESSAGE_CONTENT,
            # 状态实体
            cls.STATE, cls.STATE_ID, cls.STATE_TYPE, cls.STATE_VALUE,
            # Agent实体
            cls.AGENT, cls.AGENT_ID, cls.AGENT_ROLE, cls.AGENT_CAPABILITY,
            # 事件实体
            cls.EVENT, cls.EVENT_ID, cls.EVENT_TYPE, cls.EVENT_DATA,
        ]


class ValidationRule:
    """全局验证规则"""
    # 任务验证
    TASK_ID_PATTERN = r'^[a-zA-Z0-9_-]{1,128}$'
    TASK_DESCRIPTION_MAX_LENGTH = 10000
    TASK_PRIORITY_RANGE = (1, 10)
    
    # 代码验证
    VARIABLE_NAME_PATTERN = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    METHOD_MAX_LINES = 200
    CLASS_MAX_METHODS = 50
    MODULE_MAX_LINES = 1000
    
    # 消息验证
    MESSAGE_ID_PATTERN = r'^[a-zA-Z0-9_-]{1,64}$'
    MESSAGE_CONTENT_MAX_LENGTH = 50000
    
    # 状态验证
    STATE_ID_PATTERN = r'^[a-zA-Z0-9_-]{1,64}$'
    
    # Agent验证
    AGENT_ID_PATTERN = r'^[a-zA-Z0-9_-]{1,64}$'
    AGENT_ROLE_PATTERN = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    
    # 事件验证
    EVENT_ID_PATTERN = r'^[a-zA-Z0-9_-]{1,64}$'

    @classmethod
    def get_all_rules(cls):
        return {
            "task_id_pattern": cls.TASK_ID_PATTERN,
            "task_description_max_length": cls.TASK_DESCRIPTION_MAX_LENGTH,
            "task_priority_range": cls.TASK_PRIORITY_RANGE,
            "variable_name_pattern": cls.VARIABLE_NAME_PATTERN,
            "method_max_lines": cls.METHOD_MAX_LINES,
            "class_max_methods": cls.CLASS_MAX_METHODS,
            "module_max_lines": cls.MODULE_MAX_LINES,
            "message_id_pattern": cls.MESSAGE_ID_PATTERN,
            "message_content_max_length": cls.MESSAGE_CONTENT_MAX_LENGTH,
            "state_id_pattern": cls.STATE_ID_PATTERN,
            "agent_id_pattern": cls.AGENT_ID_PATTERN,
            "agent_role_pattern": cls.AGENT_ROLE_PATTERN,
            "event_id_pattern": cls.EVENT_ID_PATTERN,
        }


class ConstraintType:
    """约束类型"""
    LAYER_DEPENDENCY = "layer_dependency"
    ATOMIC_INTEGRITY = "atomic_integrity"
    STATE_ISOLATION = "state_isolation"
    RESPONSIBILITY_ORTHOGONAL = "responsibility_orthogonal"
    NO_IMPLICIT_STATE = "no_implicit_state"
    NO_CIRCULAR_DEPENDENCY = "no_circular_dependency"
    UNIDIRECTIONAL_FLOW = "unidirectional_flow"

    @classmethod
    def get_all(cls):
        return [
            cls.LAYER_DEPENDENCY,
            cls.ATOMIC_INTEGRITY,
            cls.STATE_ISOLATION,
            cls.RESPONSIBILITY_ORTHOGONAL,
            cls.NO_IMPLICIT_STATE,
            cls.NO_CIRCULAR_DEPENDENCY,
            cls.UNIDIRECTIONAL_FLOW,
        ]
