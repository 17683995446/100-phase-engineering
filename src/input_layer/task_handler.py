"""
输入层任务处理器
统一接收任务、类型判定、基础预处理
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union
from enum import Enum, auto

from src.config.constants import TaskType
from src.utils.logger import logger


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class TaskRequest:
    """任务请求对象"""
    
    def __init__(
        self,
        task_id: Optional[str] = None,
        task_type: str = TaskType.REQUIREMENT,
        task_description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.task_id = task_id or str(uuid.uuid4())
        self.task_type = task_type
        self.task_description = task_description
        self.priority = priority
        self.created_at = datetime.now()
        self.metadata = metadata or {}
        
        logger.info(f"创建任务请求: {self.task_id}, 类型: {self.task_type}")


class TaskPreprocessor:
    """任务预处理器"""
    
    def __init__(self):
        logger.info("初始化任务预处理器")
    
    def preprocess(self, task_request: TaskRequest) -> Dict[str, Any]:
        """
        预处理任务请求
        
        Args:
            task_request: 任务请求对象
            
        Returns:
            预处理后的任务信息
        """
        logger.info(f"预处理任务: {task_request.task_id}")
        
        # 基础预处理
        processed = {
            "task_id": task_request.task_id,
            "task_type": task_request.task_type,
            "description": task_request.task_description,
            "priority": task_request.priority,
            "created_at": task_request.created_at,
            "metadata": task_request.metadata,
            "preprocessed": True,
            "preprocessing_time": datetime.now(),
        }
        
        # 分析任务描述，提取关键信息
        analysis = self._analyze_description(task_request.task_description)
        processed.update(analysis)
        
        return processed
    
    def _analyze_description(self, description: str) -> Dict[str, Any]:
        """
        分析任务描述
        
        Args:
            description: 任务描述
            
        Returns:
            分析结果
        """
        analysis = {
            "length": len(description),
            "word_count": len(description.split()),
            "keywords": self._extract_keywords(description),
            "is_code_related": self._is_code_related(description),
            "is_test_related": self._is_test_related(description),
            "is_refactor_related": self._is_refactor_related(description),
        }
        return analysis
    
    def _extract_keywords(self, description: str) -> list:
        """
        提取关键词
        
        Args:
            description: 任务描述
            
        Returns:
            关键词列表
        """
        keywords = []
        common_terms = ["代码", "函数", "类", "模块", "测试", "修复", "重构", "实现", "需求"]
        for term in common_terms:
            if term in description:
                keywords.append(term)
        return keywords
    
    def _is_code_related(self, description: str) -> bool:
        """判断是否与代码相关"""
        code_keywords = ["代码", "函数", "类", "模块", "实现", "编码"]
        return any(keyword in description for keyword in code_keywords)
    
    def _is_test_related(self, description: str) -> bool:
        """判断是否与测试相关"""
        test_keywords = ["测试", "用例", "验证", "检查"]
        return any(keyword in description for keyword in test_keywords)
    
    def _is_refactor_related(self, description: str) -> bool:
        """判断是否与重构相关"""
        refactor_keywords = ["重构", "优化", "改进", "清理"]
        return any(keyword in description for keyword in refactor_keywords)


class TaskInputHandler:
    """任务输入处理器 - 入口层核心"""
    
    def __init__(self):
        self.preprocessor = TaskPreprocessor()
        logger.info("初始化任务输入处理器")
    
    def receive_task(
        self,
        task_description: str,
        task_type: str = TaskType.REQUIREMENT,
        priority: TaskPriority = TaskPriority.MEDIUM,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        接收任务并预处理
        
        Args:
            task_description: 任务描述
            task_type: 任务类型
            priority: 优先级
            task_id: 可选的任务ID
            metadata: 可选的元数据
            
        Returns:
            处理后的任务信息
        """
        logger.info("接收新任务")
        
        # 创建任务请求
        task_request = TaskRequest(
            task_id=task_id,
            task_type=task_type,
            task_description=task_description,
            priority=priority,
            metadata=metadata
        )
        
        # 预处理
        processed_task = self.preprocessor.preprocess(task_request)
        
        logger.info(f"任务处理完成: {task_request.task_id}")
        
        return processed_task
