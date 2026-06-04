"""
执行层基类
代码解析、重构修改、规范校验、测试生成
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from src.utils.logger import logger


class BaseCodeProcessor(ABC):
    """
    代码处理器基类
    """
    
    def __init__(self, language: str = "python"):
        self.language = language
        logger.info(f"初始化代码处理器: {language}")
    
    @abstractmethod
    def parse_code(self, code: str) -> Dict[str, Any]:
        """
        解析代码
        
        Args:
            code: 源代码字符串
            
        Returns:
            解析结果
        """
        pass
    
    @abstractmethod
    def analyze_structure(self, parse_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析代码结构
        
        Args:
            parse_result: 解析结果
            
        Returns:
            结构分析结果
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(language={self.language})"
