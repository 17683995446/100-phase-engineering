"""
调度层状态模型
遵循状态分离公理：系统、任务、业务三层状态隔离管控

三层状态隔离说明：
- SystemState: 系统底层状态，独立于具体业务和任务
- TaskState: 单个任务的执行状态，只属于该任务
- BusinessState: 业务领域状态，包含任务相关的业务数据
"""

from typing import TypedDict, Optional, Any, Dict, List, Generic, TypeVar
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field
from copy import deepcopy

from src.config.constants import TaskType, AgentRole
from src.utils.logger import logger


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = auto()      # 待处理
    ANALYZING = auto()    # 分析中
    IN_PROGRESS = auto()  # 进行中
    REVIEWING = auto()    # 审查中
    TESTING = auto()      # 测试中
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    CANCELLED = auto()    # 已取消


class SystemState(TypedDict, total=False):
    """
    系统状态层 - 底层系统运行状态
    与具体业务无关，只记录系统级信息
    """
    timestamp: datetime
    version: str
    uptime_seconds: float
    active_tasks: int
    total_tasks_processed: int
    health_status: str  # "healthy", "degraded", "unhealthy"
    last_error_time: Optional[datetime]
    last_error_msg: Optional[str]


class TaskState(TypedDict, total=False):
    """
    任务状态层 - 单个任务的执行状态
    只属于该任务，与系统层和业务层隔离
    """
    task_id: str
    task_type: str
    status: TaskStatus
    priority: int
    created_at: datetime
    updated_at: datetime
    assigned_agent: Optional[str]
    retry_count: int
    max_retries: int
    estimated_remaining: Optional[float]  # 预计剩余时间（秒）
    progress: float  # 0-1 进度
    task_history: List[Dict[str, Any]]  # 任务执行历史


class BusinessState(TypedDict, total=False):
    """
    业务状态层 - 业务领域相关状态
    包含任务相关的业务数据，独立于系统和任务执行状态
    """
    original_input: str
    analysis_result: Optional[str]
    architecture_design: Optional[str]
    code_changes: Optional[List[Dict[str, Any]]]
    review_comments: Optional[str]
    test_results: Optional[Dict[str, Any]]
    final_output: Optional[str]
    business_context: Dict[str, Any]  # 业务上下文数据
    validation_status: Optional[str]  # 业务验证状态


class GlobalState(TypedDict):
    """全局状态 - 三层状态聚合，仅用于统一访问接口"""
    system: SystemState
    task: TaskState
    business: BusinessState


@dataclass
class StateManager:
    """
    状态管理器
    严格管理三层状态的隔离访问和更新
    """
    system_state: SystemState = field(default_factory=dict)
    task_states: Dict[str, TaskState] = field(default_factory=dict)  # 支持多任务
    business_states: Dict[str, BusinessState] = field(default_factory=dict)
    global_states: Dict[str, GlobalState] = field(default_factory=dict)
    
    def __post_init__(self):
        logger.info("状态管理器初始化完成")
        self._initialize_system_state()
    
    def _initialize_system_state(self):
        """初始化系统状态"""
        if not self.system_state:
            self.system_state = {
                "timestamp": datetime.now(),
                "version": "0.1.0",
                "uptime_seconds": 0.0,
                "active_tasks": 0,
                "total_tasks_processed": 0,
                "health_status": "healthy",
                "last_error_time": None,
                "last_error_msg": None,
            }
            logger.info("系统状态初始化完成")
    
    # ========== 系统状态操作（SystemState） ==========
    
    def get_system_state(self) -> SystemState:
        """获取系统状态（只读访问）"""
        return deepcopy(self.system_state)
    
    def update_system_state(self, updates: Dict[str, Any]) -> SystemState:
        """
        更新系统状态
        只允许更新系统相关字段
        """
        valid_keys = [
            "timestamp", "version", "uptime_seconds",
            "active_tasks", "total_tasks_processed",
            "health_status", "last_error_time", "last_error_msg"
        ]
        
        for key, value in updates.items():
            if key in valid_keys:
                self.system_state[key] = value
                logger.debug(f"系统状态更新: {key} = {value}")
            else:
                logger.warning(f"无效的系统状态字段: {key}")
        
        self.system_state["timestamp"] = datetime.now()
        return self.get_system_state()
    
    def record_system_error(self, error_msg: str):
        """记录系统错误"""
        self.update_system_state({
            "last_error_time": datetime.now(),
            "last_error_msg": error_msg,
            "health_status": "degraded"
        })
        logger.error(f"系统错误记录: {error_msg}")
    
    # ========== 任务状态操作（TaskState） ==========
    
    def create_task_state(
        self,
        task_id: str,
        task_type: str,
        priority: int = 1,
        max_retries: int = 3
    ) -> TaskState:
        """创建任务状态"""
        now = datetime.now()
        task_state: TaskState = {
            "task_id": task_id,
            "task_type": task_type,
            "status": TaskStatus.PENDING,
            "priority": priority,
            "created_at": now,
            "updated_at": now,
            "assigned_agent": None,
            "retry_count": 0,
            "max_retries": max_retries,
            "estimated_remaining": None,
            "progress": 0.0,
            "task_history": [],
        }
        
        self.task_states[task_id] = task_state
        self.update_system_state({"active_tasks": len(self.task_states)})
        
        logger.info(f"创建任务状态: {task_id}")
        return deepcopy(task_state)
    
    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态（只读访问）"""
        if task_id in self.task_states:
            return deepcopy(self.task_states[task_id])
        logger.warning(f"任务状态不存在: {task_id}")
        return None
    
    def update_task_status(
        self,
        task_id: str,
        new_status: TaskStatus,
        progress: Optional[float] = None,
        agent: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Optional[TaskState]:
        """
        更新任务状态
        记录变更历史
        """
        if task_id not in self.task_states:
            return None
        
        task_state = self.task_states[task_id]
        old_status = task_state["status"]
        
        # 记录变更历史
        history_entry = {
            "timestamp": datetime.now(),
            "old_status": old_status.name if old_status else None,
            "new_status": new_status.name,
            "agent": agent,
            "comment": comment,
        }
        
        task_state["status"] = new_status
        task_state["updated_at"] = datetime.now()
        if progress is not None:
            task_state["progress"] = max(0.0, min(1.0, progress))
        if agent is not None:
            task_state["assigned_agent"] = agent
        
        task_state["task_history"].append(history_entry)
        
        logger.info(
            f"任务状态变更: {task_id} - {old_status.name if old_status else 'None'} → {new_status.name}"
        )
        return deepcopy(task_state)
    
    def increment_task_retry(self, task_id: str) -> Optional[bool]:
        """增加任务重试次数"""
        if task_id not in self.task_states:
            return None
        
        task_state = self.task_states[task_id]
        task_state["retry_count"] += 1
        task_state["updated_at"] = datetime.now()
        
        logger.info(f"任务重试: {task_id} - 次数: {task_state['retry_count']}")
        return task_state["retry_count"] <= task_state["max_retries"]
    
    def complete_task(self, task_id: str) -> Optional[TaskState]:
        """完成任务"""
        result = self.update_task_status(task_id, TaskStatus.COMPLETED, progress=1.0)
        
        if result:
            self.update_system_state({
                "active_tasks": len(self.task_states),
                "total_tasks_processed": self.system_state.get("total_tasks_processed", 0) + 1,
            })
        
        return result
    
    # ========== 业务状态操作（BusinessState） ==========
    
    def create_business_state(
        self,
        task_id: str,
        original_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> BusinessState:
        """创建业务状态"""
        business_state: BusinessState = {
            "original_input": original_input,
            "analysis_result": None,
            "architecture_design": None,
            "code_changes": None,
            "review_comments": None,
            "test_results": None,
            "final_output": None,
            "business_context": context or {},
            "validation_status": None,
        }
        
        self.business_states[task_id] = business_state
        logger.info(f"创建业务状态: {task_id}")
        return deepcopy(business_state)
    
    def get_business_state(self, task_id: str) -> Optional[BusinessState]:
        """获取业务状态（只读访问）"""
        if task_id in self.business_states:
            return deepcopy(self.business_states[task_id])
        logger.warning(f"业务状态不存在: {task_id}")
        return None
    
    def update_business_field(
        self,
        task_id: str,
        field_name: str,
        value: Any,
        validator: Optional[str] = None
    ) -> Optional[BusinessState]:
        """更新业务状态的特定字段"""
        if task_id not in self.business_states:
            return None
        
        business_state = self.business_states[task_id]
        
        valid_fields = [
            "original_input", "analysis_result", "architecture_design",
            "code_changes", "review_comments", "test_results",
            "final_output", "business_context", "validation_status"
        ]
        
        if field_name in valid_fields:
            business_state[field_name] = value  # type: ignore
            if validator:
                business_state["validation_status"] = validator
            
            logger.debug(f"业务状态更新: {task_id} - {field_name}")
            return deepcopy(business_state)
        else:
            logger.warning(f"无效的业务状态字段: {field_name}")
            return None
    
    # ========== 全局状态操作（GlobalState） ==========
    
    def create_global_state(
        self,
        task_id: str,
        task_type: str,
        original_input: str,
        priority: int = 1
    ) -> GlobalState:
        """
        创建全局状态（三层聚合）
        该方法同时创建系统、任务、业务状态
        """
        self.create_task_state(task_id, task_type, priority)
        self.create_business_state(task_id, original_input)
        
        global_state: GlobalState = {
            "system": self.get_system_state(),
            "task": self.get_task_state(task_id) or {},  # type: ignore
            "business": self.get_business_state(task_id) or {},  # type: ignore
        }
        
        self.global_states[task_id] = global_state
        logger.info(f"创建全局状态: {task_id}")
        return deepcopy(global_state)
    
    def get_global_state(self, task_id: str) -> Optional[GlobalState]:
        """获取全局状态（聚合视图，只读）"""
        if task_id not in self.global_states:
            return None
        
        # 重新聚合三层状态，确保一致性
        global_state: GlobalState = {
            "system": self.get_system_state(),
            "task": self.get_task_state(task_id) or {},  # type: ignore
            "business": self.get_business_state(task_id) or {},  # type: ignore
        }
        return global_state
    
    # ========== 验证和隔离检查 ==========
    
    def validate_state_isolation(self) -> Dict[str, Any]:
        """
        验证三层状态隔离
        检查是否有违规的交叉依赖
        """
        result = {
            "valid": True,
            "checks": {
                "system_independent": True,
                "task_independent": True,
                "business_independent": True,
                "no_cross_references": True,
            },
            "issues": []
        }
        
        # 检查系统状态是否包含任务或业务相关字段（排除允许的字段）
        allowed_system_keys = {
            "active_tasks", "total_tasks_processed"  # 允许系统级统计字段
        }
        system_keys = set(self.system_state.keys())
        for key in system_keys:
            key_lower = key.lower()
            if (("task" in key_lower or "business" in key_lower) 
                    and key not in allowed_system_keys):
                result["checks"]["system_independent"] = False
                result["issues"].append(f"系统状态包含违规字段: {key}")
                result["valid"] = False
        
        # 检查任务状态是否包含业务或系统相关字段
        for task_id, task_state in self.task_states.items():
            task_keys = set(task_state.keys())
            if any("business" in key.lower() or "system" in key.lower() for key in task_keys):
                result["checks"]["task_independent"] = False
                result["issues"].append(f"任务 {task_id} 状态包含其他层字段")
                result["valid"] = False
        
        # 检查业务状态是否包含任务或系统相关字段
        for task_id, business_state in self.business_states.items():
            business_keys = set(business_state.keys())
            for key in business_keys:
                key_lower = key.lower()
                if (("task" in key_lower or "system" in key_lower) 
                        and key != "business_context"):
                    result["checks"]["business_independent"] = False
                    result["issues"].append(f"业务 {task_id} 状态包含违规字段: {key}")
                    result["valid"] = False
        
        if result["valid"]:
            logger.info("三层状态隔离验证通过")
        else:
            logger.warning(f"三层状态隔离发现问题: {result['issues']}")
        
        return result
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        return {
            "system": self.get_system_state(),
            "active_tasks_count": len(self.task_states),
            "tasks_by_status": self._count_tasks_by_status(),
            "total_tasks_processed": self.system_state.get("total_tasks_processed", 0),
            "isolation_valid": self.validate_state_isolation()["valid"],
        }
    
    def _count_tasks_by_status(self) -> Dict[str, int]:
        """按状态统计任务数量"""
        counts: Dict[str, int] = {status.name: 0 for status in TaskStatus}
        for task_state in self.task_states.values():
            status = task_state.get("status")
            if status:
                counts[status.name] = counts.get(status.name, 0) + 1
        return counts


def create_initial_state(task_id: str, task_type: str, original_input: str) -> GlobalState:
    """
    创建初始全局状态（兼容旧接口）
    新代码应该使用 StateManager
    """
    manager = StateManager()
    return manager.create_global_state(task_id, task_type, original_input)
