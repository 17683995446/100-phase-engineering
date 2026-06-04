"""
全局配置管理
"""

import os
from typing import Optional
from pathlib import Path


class Settings:
    """全局配置类"""
    
    def __init__(self):
        # 日志配置
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE: Optional[Path] = None
        
        # 调试模式
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # 最大重试次数
        self.MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
        
        # 超时设置（秒）
        self.TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "3600"))


# 全局配置实例
settings = Settings()
