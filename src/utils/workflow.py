"""
工作流引擎
提供工作流定义、执行、状态管理和节点编排功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class NodeStatus(Enum):
    """节点状态"""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class WorkflowNode:
    """工作流节点"""
    node_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "status": self.status.name,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    workflow_id: str
    name: str
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    
    def add_node(self, node: WorkflowNode) -> None:
        """添加节点"""
        self.nodes[node.node_id] = node
    
    def get_execution_order(self) -> List[List[str]]:
        """获取执行顺序（按层级分组）"""
        executed: Set[str] = set()
        order: List[List[str]] = []
        remaining = set(self.nodes.keys())
        
        while remaining:
            layer = []
            for node_id in list(remaining):
                node = self.nodes[node_id]
                if all(dep in executed for dep in node.dependencies):
                    layer.append(node_id)
            
            if not layer:
                raise ValueError("Circular dependency detected")
            
            order.append(layer)
            executed.update(layer)
            remaining -= set(layer)
        
        return order


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._executions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("workflow.engine")
    
    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """注册工作流"""
        with self._lock:
            self._workflows[workflow.workflow_id] = workflow
        self._logger.info(f"Registered workflow: {workflow.name}")
    
    def execute_workflow(self, workflow_id: str, 
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行工作流"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        execution_id = f"{workflow_id}-{int(time.time())}"
        context = context or {}
        
        execution = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": WorkflowStatus.RUNNING,
            "started_at": datetime.now(),
            "completed_at": None,
            "node_results": {},
            "context": context
        }
        
        with self._lock:
            self._executions[execution_id] = execution
        
        try:
            order = workflow.get_execution_order()
            
            for layer in order:
                threads = []
                for node_id in layer:
                    node = workflow.nodes[node_id]
                    thread = threading.Thread(
                        target=self._execute_node,
                        args=(node, execution),
                        daemon=True
                    )
                    threads.append(thread)
                    thread.start()
                
                for thread in threads:
                    thread.join()
                
                # 检查是否有失败
                if any(workflow.nodes[nid].status == NodeStatus.FAILED for nid in layer):
                    execution["status"] = WorkflowStatus.FAILED
                    break
            else:
                execution["status"] = WorkflowStatus.COMPLETED
            
        except Exception as e:
            execution["status"] = WorkflowStatus.FAILED
            self._logger.error(f"Workflow execution failed: {e}")
        
        finally:
            execution["completed_at"] = datetime.now()
        
        return execution
    
    def _execute_node(self, node: WorkflowNode, execution: Dict[str, Any]) -> None:
        """执行节点"""
        if node.status != NodeStatus.PENDING:
            return
        
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.now()
        
        try:
            self._logger.info(f"Executing node: {node.name}")
            
            # 注入上下文
            kwargs = dict(node.kwargs)
            kwargs["_context"] = execution["context"]
            kwargs["_results"] = execution["node_results"]
            
            node.result = node.func(*node.args, **kwargs)
            node.status = NodeStatus.COMPLETED
            execution["node_results"][node.node_id] = node.result
            
            self._logger.info(f"Node completed: {node.name}")
            
        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = str(e)
            self._logger.error(f"Node failed: {node.name} - {e}")
        
        finally:
            node.completed_at = datetime.now()
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行记录"""
        with self._lock:
            return self._executions.get(execution_id)
    
    def get_workflow_status(self, execution_id: str) -> Optional[WorkflowStatus]:
        """获取工作流状态"""
        execution = self.get_execution(execution_id)
        return execution["status"] if execution else None
    
    def get_node_status(self, workflow_id: str, node_id: str) -> Optional[NodeStatus]:
        """获取节点状态"""
        workflow = self._workflows.get(workflow_id)
        if workflow and node_id in workflow.nodes:
            return workflow.nodes[node_id].status
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._executions)
            completed = sum(1 for e in self._executions.values() 
                          if e["status"] == WorkflowStatus.COMPLETED)
            failed = sum(1 for e in self._executions.values() 
                       if e["status"] == WorkflowStatus.FAILED)
            
            return {
                "workflows": len(self._workflows),
                "executions": total,
                "completed": completed,
                "failed": failed
            }


# 全局实例
_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """获取工作流引擎"""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
