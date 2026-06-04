"""
Agent 基类
遵循职责正交公理：Agent职责无重叠、无空缺，分工互补无冲突
"""

from abc import ABC, abstractmethod
from typing import Any

from src.config.constants import AgentRole
from src.utils.logger import logger


class BaseAgent(ABC):
    """
    所有Agent的基类
    """

    def __init__(self, role: AgentRole, name: str | None = None):
        self.role = role
        if name:
            self.name = name
        elif hasattr(role, 'value'):
            self.name = role.value
        else:
            self.name = str(role)
        logger.info(f"初始化Agent: {self.name} ({self.role})")

    @abstractmethod
    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        处理输入，返回输出

        Args:
            input_data: 输入数据

        Returns:
            处理结果
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(role={self.role}, name={self.name})"
