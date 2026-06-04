"""
统一日志模块
信息显式化，可追溯
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from src.config.constants import LOGS_DIR
from src.config.settings import settings


def setup_logger(name: str = "maes") -> logging.Logger:
    """
    设置统一的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    log_file = LOGS_DIR / f"maes_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# 全局日志实例
logger = setup_logger()
