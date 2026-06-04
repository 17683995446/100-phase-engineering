"""
轻量级工作流引擎实现
不依赖LangGraph，保持架构灵活性
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Callable, Optional

from src.scheduling_layer.state import (
    GlobalState,
    TaskStatus,
    create_initial_state
)
from src.config.constants import TaskType
from src.utils.logger import logger


class LightweightWorkflow:
    """
    轻量级工作流
    不依赖外部库，简单易用
    """
    
    def __init__(self):
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, str] = {}
        self.entry_point: Optional[str] = None
        logger.info("轻量级工作流初始化")
    
    def add_node(self, name: str, func: Callable):
        """添加节点"""
        self.nodes[name] = func
        logger.debug(f"添加节点: {name}")
    
    def set_entry_point(self, name: str):
        """设置入口点"""
        self.entry_point = name
        logger.debug(f"设置入口点: {name}")
    
    def add_edge(self, from_node: str, to_node: str):
        """添加边"""
        self.edges[from_node] = to_node
        logger.debug(f"添加边: {from_node} -> {to_node}")
    
    def execute(self, initial_state: GlobalState) -> GlobalState:
        """
        执行工作流
        
        Args:
            initial_state: 初始状态
            
        Returns:
            最终状态
        """
        if not self.entry_point or self.entry_point not in self.nodes:
            raise ValueError("无效的入口点")
        
        state = initial_state
        current_node = self.entry_point
        
        logger.info(f"工作流开始执行: {initial_state['task']['task_id']}")
        
        while current_node:
            if current_node not in self.nodes:
                break
            
            # 执行节点
            logger.debug(f"执行节点: {current_node}")
            state = self.nodes[current_node](state)
            
            # 获取下一个节点
            current_node = self.edges.get(current_node)
        
        logger.info(f"工作流执行完成: {state['task']['task_id']}")
        return state


def node_input_process(state: GlobalState) -> GlobalState:
    """输入处理节点"""
    logger.info(f"处理输入: {state['task']['task_id']}")
    state["task"]["status"] = TaskStatus.ANALYZING
    state["task"]["updated_at"] = datetime.now()
    state["system"]["timestamp"] = datetime.now()
    return state


def node_analyze(state: GlobalState) -> GlobalState:
    """分析节点"""
    logger.info(f"分析任务: {state['task']['task_id']}")
    state["task"]["status"] = TaskStatus.IN_PROGRESS
    state["task"]["updated_at"] = datetime.now()
    state["system"]["timestamp"] = datetime.now()
    state["business"]["analysis_result"] = f"分析完成: {state['business']['original_input'][:50]}..."
    return state


def node_execute(state: GlobalState) -> GlobalState:
    """执行节点"""
    logger.info(f"执行任务: {state['task']['task_id']}")
    state["task"]["status"] = TaskStatus.REVIEWING
    state["task"]["updated_at"] = datetime.now()
    state["system"]["timestamp"] = datetime.now()
    state["business"]["final_output"] = f"执行结果: 任务 {state['task']['task_id']} 完成"
    return state


def node_complete(state: GlobalState) -> GlobalState:
    """完成节点"""
    logger.info(f"任务完成: {state['task']['task_id']}")
    state["task"]["status"] = TaskStatus.COMPLETED
    state["task"]["updated_at"] = datetime.now()
    state["system"]["timestamp"] = datetime.now()
    state["system"]["active_tasks"] = 0
    state["system"]["total_tasks_processed"] = 1
    return state


def create_workflow_graph() -> LightweightWorkflow:
    """
    创建工作流图
    
    Returns:
        配置好的轻量级工作流
    """
    workflow = LightweightWorkflow()
    
    # 添加节点
    workflow.add_node("input_process", node_input_process)
    workflow.add_node("analyze", node_analyze)
    workflow.add_node("execute", node_execute)
    workflow.add_node("complete", node_complete)
    
    # 设置入口点
    workflow.set_entry_point("input_process")
    
    # 添加边
    workflow.add_edge("input_process", "analyze")
    workflow.add_edge("analyze", "execute")
    workflow.add_edge("execute", "complete")
    
    return workflow


class WorkflowEngine:
    """
    轻量级工作流引擎
    封装简单的工作流，提供执行接口
    """
    
    def __init__(self):
        self.graph = create_workflow_graph()
        logger.info("工作流引擎初始化完成")
    
    def execute(
        self,
        task_id: str | None = None,
        initial_state: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task_id: 任务ID
            initial_state: 初始状态
            
        Returns:
            执行结果
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        # 创建初始状态
        if initial_state and "task" in initial_state:
            task_info = initial_state["task"]
            task_type = task_info.get("task_type", TaskType.REQUIREMENT)
            input_text = task_info.get("description", "")
        else:
            task_type = TaskType.REQUIREMENT
            input_text = ""
        
        state = create_initial_state(task_id, task_type, input_text)
        
        # 执行工作流
        final_state = self.graph.execute(state)
        
        return {
            "success": True,
            "task_id": task_id,
            "final_state": final_state,
            "status": final_state["task"]["status"],
        }
    
    def run_task(
        self,
        task_type: TaskType,
        input_text: str,
        task_id: str | None = None
    ) -> GlobalState:
        """
        运行任务（向后兼容接口）
        
        Args:
            task_type: 任务类型
            input_text: 输入文本
            task_id: 可选的任务ID
            
        Returns:
            最终状态
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        logger.info(f"启动任务: {task_id}, 类型: {task_type}")
        
        initial_state = create_initial_state(task_id, task_type, input_text)
        
        result = self.graph.execute(initial_state)
        
        logger.info(f"任务完成: {task_id}, 状态: {result['task']['status']}")
        return result
