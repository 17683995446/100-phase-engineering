"""
原子实体定义模块
任务可分性公理：复杂任务可拆解至不可再分原子动作
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum, auto
import re
from src.config.constants import ValidationRule


class EntityCategory(Enum):
    """实体类别"""
    TASK = auto()
    CODE = auto()
    MESSAGE = auto()
    STATE = auto()
    AGENT = auto()
    EVENT = auto()


@dataclass
class EntityDefinition:
    """实体定义"""
    name: str
    category: EntityCategory
    description: str
    fields: Dict[str, str]
    constraints: List[str]
    validation_rules: Dict[str, Any]
    is_atomic: bool = True
    parent_entity: Optional[str] = None


class TaskAtomicEntity:
    """任务原子实体"""
    
    TASK_REQUEST = EntityDefinition(
        name="task_request",
        category=EntityCategory.TASK,
        description="任务请求实体，包含任务的所有输入信息",
        fields={
            "task_id": "string: 唯一标识符",
            "task_type": "string: 任务类型 (requirement/refactor/bugfix/review/test)",
            "task_description": "string: 任务描述，最大10000字符",
            "priority": "int: 优先级 1-10",
            "metadata": "dict: 元数据",
            "created_at": "datetime: 创建时间",
            "input_source": "string: 输入来源"
        },
        constraints=[
            "task_id必须唯一",
            "task_type必须为有效枚举值",
            "task_description不能为空且不超过10000字符",
            "priority必须在1-10之间"
        ],
        validation_rules={
            "task_id_pattern": ValidationRule.TASK_ID_PATTERN,
            "max_description_length": ValidationRule.TASK_DESCRIPTION_MAX_LENGTH,
            "priority_range": ValidationRule.TASK_PRIORITY_RANGE
        },
        is_atomic=True
    )
    
    TASK_RESULT = EntityDefinition(
        name="task_result",
        category=EntityCategory.TASK,
        description="任务结果实体，包含任务的执行结果",
        fields={
            "task_id": "string: 任务ID",
            "status": "string: 执行状态",
            "output": "any: 执行输出",
            "artifacts": "dict: 产物",
            "completed_at": "datetime: 完成时间",
            "execution_time_ms": "float: 执行时间毫秒",
            "agent_id": "string: 执行Agent ID"
        },
        constraints=[
            "task_id必须与请求匹配",
            "status必须为有效状态",
            "output必须有结构化格式"
        ],
        validation_rules={},
        is_atomic=True
    )
    
    SUBTASK = EntityDefinition(
        name="subtask",
        category=EntityCategory.TASK,
        description="子任务实体，任务的最小分解单位",
        fields={
            "subtask_id": "string: 子任务ID",
            "parent_task_id": "string: 父任务ID",
            "description": "string: 子任务描述",
            "assigned_agent": "string: 分配的Agent",
            "status": "string: 子任务状态",
            "dependencies": "list: 依赖的子任务ID列表"
        },
        constraints=[
            "subtask_id必须唯一",
            "parent_task_id必须存在",
            "dependencies不能形成循环"
        ],
        validation_rules={},
        is_atomic=True
    )


class CodeAtomicEntity:
    """代码原子实体"""
    
    VARIABLE = EntityDefinition(
        name="variable",
        category=EntityCategory.CODE,
        description="变量实体，代码中的最小数据单元",
        fields={
            "name": "string: 变量名",
            "type": "string: 类型",
            "value": "any: 值",
            "scope": "string: 作用域",
            "line_number": "int: 行号",
            "is_mutable": "bool: 是否可变"
        },
        constraints=[
            "变量名必须符合标识符规则",
            "类型必须为有效类型",
            "作用域必须在有效范围内"
        ],
        validation_rules={
            "name_pattern": ValidationRule.VARIABLE_NAME_PATTERN
        },
        is_atomic=True
    )
    
    METHOD = EntityDefinition(
        name="method",
        category=EntityCategory.CODE,
        description="方法实体，代码中的最小功能单元",
        fields={
            "name": "string: 方法名",
            "parameters": "list: 参数列表",
            "return_type": "string: 返回类型",
            "body": "string: 方法体",
            "line_count": "int: 代码行数",
            "cyclomatic_complexity": "int: 圈复杂度",
            "variables": "list: 内部变量列表"
        },
        constraints=[
            "方法名必须符合标识符规则",
            "代码行数不超过200行",
            "参数列表不能超过20个",
            "圈复杂度不超过10"
        ],
        validation_rules={
            "max_lines": ValidationRule.METHOD_MAX_LINES,
            "max_parameters": 20,
            "max_complexity": 10
        },
        is_atomic=True
    )
    
    CLASS_ENTITY = EntityDefinition(
        name="class_entity",
        category=EntityCategory.CODE,
        description="类实体，代码中的基本组织单元",
        fields={
            "name": "string: 类名",
            "bases": "list: 基类列表",
            "methods": "list: 方法列表",
            "attributes": "list: 属性列表",
            "line_count": "int: 代码行数",
            "public_methods": "int: 公共方法数",
            "private_methods": "int: 私有方法数"
        },
        constraints=[
            "类名必须符合标识符规则",
            "方法数不超过50个",
            "代码行数不超过1000行",
            "必须遵循单一职责原则"
        ],
        validation_rules={
            "max_methods": ValidationRule.CLASS_MAX_METHODS,
            "max_lines": ValidationRule.MODULE_MAX_LINES
        },
        is_atomic=True
    )
    
    MODULE = EntityDefinition(
        name="module",
        category=EntityCategory.CODE,
        description="模块实体，代码的最高组织单元",
        fields={
            "name": "string: 模块名",
            "path": "string: 文件路径",
            "classes": "list: 类列表",
            "functions": "list: 函数列表",
            "imports": "list: 导入列表",
            "exports": "list: 导出列表",
            "line_count": "int: 代码行数",
            "dependencies": "list: 依赖模块列表"
        },
        constraints=[
            "模块名必须唯一",
            "代码行数不超过1000行",
            "不能形成循环依赖",
            "必须有明确的边界"
        ],
        validation_rules={
            "max_lines": ValidationRule.MODULE_MAX_LINES,
            "no_circular_dependency": True
        },
        is_atomic=True
    )


class MessageAtomicEntity:
    """消息原子实体"""
    
    MESSAGE = EntityDefinition(
        name="message",
        category=EntityCategory.MESSAGE,
        description="消息实体，Agent间通信的最小单元",
        fields={
            "message_id": "string: 消息ID",
            "message_type": "string: 消息类型 (request/response/event)",
            "content": "string: 消息内容",
            "sender": "string: 发送者",
            "receiver": "string: 接收者",
            "timestamp": "datetime: 时间戳",
            "metadata": "dict: 元数据"
        },
        constraints=[
            "message_id必须唯一",
            "content不能超过50000字符",
            "sender和receiver必须不同",
            "时间戳必须是有效datetime"
        ],
        validation_rules={
            "message_id_pattern": ValidationRule.MESSAGE_ID_PATTERN,
            "max_content_length": ValidationRule.MESSAGE_CONTENT_MAX_LENGTH
        },
        is_atomic=True
    )
    
    CONVERSATION = EntityDefinition(
        name="conversation",
        category=EntityCategory.MESSAGE,
        description="对话实体，一组相关的消息序列",
        fields={
            "conversation_id": "string: 对话ID",
            "participants": "list: 参与者列表",
            "messages": "list: 消息列表",
            "start_time": "datetime: 开始时间",
            "end_time": "datetime: 结束时间",
            "status": "string: 状态"
        },
        constraints=[
            "conversation_id必须唯一",
            "至少包含2个参与者",
            "消息列表不能为空"
        ],
        validation_rules={},
        is_atomic=True
    )


class StateAtomicEntity:
    """状态原子实体"""
    
    STATE = EntityDefinition(
        name="state",
        category=EntityCategory.STATE,
        description="状态实体，系统/任务/业务状态的抽象",
        fields={
            "state_id": "string: 状态ID",
            "state_type": "string: 状态类型 (system/task/business)",
            "value": "any: 状态值",
            "timestamp": "datetime: 时间戳",
            "source": "string: 来源",
            "version": "int: 版本号"
        },
        constraints=[
            "state_id必须唯一",
            "state_type必须为有效类型",
            "版本号必须递增"
        ],
        validation_rules={
            "state_id_pattern": ValidationRule.STATE_ID_PATTERN
        },
        is_atomic=True
    )
    
    STATE_TRANSITION = EntityDefinition(
        name="state_transition",
        category=EntityCategory.STATE,
        description="状态转换实体，状态变更的记录",
        fields={
            "transition_id": "string: 转换ID",
            "from_state": "string: 源状态",
            "to_state": "string: 目标状态",
            "trigger": "string: 触发条件",
            "timestamp": "datetime: 时间戳",
            "agent_id": "string: 执行Agent"
        },
        constraints=[
            "from_state和to_state必须不同",
            "触发条件必须有明确语义",
            "时间戳必须递增"
        ],
        validation_rules={},
        is_atomic=True
    )


class AgentAtomicEntity:
    """Agent原子实体"""
    
    AGENT = EntityDefinition(
        name="agent",
        category=EntityCategory.AGENT,
        description="Agent实体，智能体的抽象表示",
        fields={
            "agent_id": "string: Agent ID",
            "agent_role": "string: 角色 (orchestrator/analyzer/architect/developer/debugger/reviewer/tester/documenter)",
            "capabilities": "list: 能力列表",
            "status": "string: 状态",
            "current_task": "string: 当前任务ID",
            "message_queue": "list: 消息队列"
        },
        constraints=[
            "agent_id必须唯一",
            "agent_role必须为有效枚举",
            "capabilities不能为空",
            "同一时间只能执行一个任务"
        ],
        validation_rules={
            "agent_id_pattern": ValidationRule.AGENT_ID_PATTERN,
            "agent_role_pattern": ValidationRule.AGENT_ROLE_PATTERN
        },
        is_atomic=True
    )
    
    AGENT_CAPABILITY = EntityDefinition(
        name="agent_capability",
        category=EntityCategory.AGENT,
        description="Agent能力实体，描述Agent的具体能力",
        fields={
            "capability_id": "string: 能力ID",
            "name": "string: 能力名称",
            "description": "string: 能力描述",
            "parameters": "dict: 参数定义",
            "return_type": "string: 返回类型",
            "confidence": "float: 置信度 0-1"
        },
        constraints=[
            "capability_id必须唯一",
            "置信度必须在0-1之间",
            "参数定义必须完整"
        ],
        validation_rules={},
        is_atomic=True
    )


class EventAtomicEntity:
    """事件原子实体"""
    
    EVENT = EntityDefinition(
        name="event",
        category=EntityCategory.EVENT,
        description="事件实体，系统操作的记录",
        fields={
            "event_id": "string: 事件ID",
            "event_type": "string: 事件类型",
            "timestamp": "datetime: 时间戳",
            "source": "string: 来源",
            "data": "dict: 事件数据",
            "severity": "string: 严重程度 (info/warning/error/critical)"
        },
        constraints=[
            "event_id必须唯一",
            "event_type必须有明确语义",
            "时间戳必须递增"
        ],
        validation_rules={
            "event_id_pattern": ValidationRule.EVENT_ID_PATTERN
        },
        is_atomic=True
    )
    
    EVENT_TRACE = EntityDefinition(
        name="event_trace",
        category=EntityCategory.EVENT,
        description="事件追踪实体，关联的事件序列",
        fields={
            "trace_id": "string: 追踪ID",
            "events": "list: 事件列表",
            "root_event_id": "string: 根事件ID",
            "start_time": "datetime: 开始时间",
            "end_time": "datetime: 结束时间",
            "depth": "int: 嵌套深度"
        },
        constraints=[
            "trace_id必须唯一",
            "events列表不能为空",
            "深度不能超过100"
        ],
        validation_rules={
            "max_depth": 100
        },
        is_atomic=True
    )


class AtomicEntityRegistry:
    """原子实体注册表"""
    
    _entities: Dict[str, EntityDefinition] = {}
    _categories: Dict[EntityCategory, List[str]] = {}
    
    @classmethod
    def register(cls, entity: EntityDefinition):
        """注册原子实体"""
        cls._entities[entity.name] = entity
        if entity.category not in cls._categories:
            cls._categories[entity.category] = []
        cls._categories[entity.category].append(entity.name)
    
    @classmethod
    def get(cls, name: str) -> Optional[EntityDefinition]:
        """获取原子实体定义"""
        return cls._entities.get(name)
    
    @classmethod
    def get_by_category(cls, category: EntityCategory) -> List[EntityDefinition]:
        """按类别获取原子实体"""
        names = cls._categories.get(category, [])
        return [cls._entities[name] for name in names]
    
    @classmethod
    def get_all(cls) -> List[EntityDefinition]:
        """获取所有原子实体"""
        return list(cls._entities.values())
    
    @classmethod
    def get_all_categories(cls) -> List[EntityCategory]:
        """获取所有类别"""
        return list(cls._categories.keys())


# 注册所有原子实体
def _register_all_entities():
    """注册所有原子实体"""
    # Task entities
    AtomicEntityRegistry.register(TaskAtomicEntity.TASK_REQUEST)
    AtomicEntityRegistry.register(TaskAtomicEntity.TASK_RESULT)
    AtomicEntityRegistry.register(TaskAtomicEntity.SUBTASK)
    
    # Code entities
    AtomicEntityRegistry.register(CodeAtomicEntity.VARIABLE)
    AtomicEntityRegistry.register(CodeAtomicEntity.METHOD)
    AtomicEntityRegistry.register(CodeAtomicEntity.CLASS_ENTITY)
    AtomicEntityRegistry.register(CodeAtomicEntity.MODULE)
    
    # Message entities
    AtomicEntityRegistry.register(MessageAtomicEntity.MESSAGE)
    AtomicEntityRegistry.register(MessageAtomicEntity.CONVERSATION)
    
    # State entities
    AtomicEntityRegistry.register(StateAtomicEntity.STATE)
    AtomicEntityRegistry.register(StateAtomicEntity.STATE_TRANSITION)
    
    # Agent entities
    AtomicEntityRegistry.register(AgentAtomicEntity.AGENT)
    AtomicEntityRegistry.register(AgentAtomicEntity.AGENT_CAPABILITY)
    
    # Event entities
    AtomicEntityRegistry.register(EventAtomicEntity.EVENT)
    AtomicEntityRegistry.register(EventAtomicEntity.EVENT_TRACE)


_register_all_entities()
