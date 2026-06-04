"""
统一异常类体系
"""


class MAESBaseException(Exception):
    """多Agent软件工程系统基础异常"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class InputLayerException(MAESBaseException):
    """输入层异常"""
    def __init__(self, message: str):
        super().__init__(message, error_code="INPUT_ERROR")


class SchedulingLayerException(MAESBaseException):
    """调度层异常"""
    def __init__(self, message: str):
        super().__init__(message, error_code="SCHEDULING_ERROR")


class AgentLayerException(MAESBaseException):
    """Agent层异常"""
    def __init__(self, message: str):
        super().__init__(message, error_code="AGENT_ERROR")


class ExecutionLayerException(MAESBaseException):
    """执行层异常"""
    def __init__(self, message: str):
        super().__init__(message, error_code="EXECUTION_ERROR")


class DependencyException(MAESBaseException):
    """依赖异常 - 违反单向依赖公理"""
    def __init__(self, message: str):
        super().__init__(message, error_code="DEPENDENCY_ERROR")
