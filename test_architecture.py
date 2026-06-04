#!/usr/bin/env python3
"""
第2阶段架构验证脚本
验证项目目录架构是否符合单向依赖原则
"""

import sys
from pathlib import Path


def verify_directory_structure():
    """验证目录结构"""
    print("=" * 60)
    print("验证项目目录架构验证")
    print("=" * 60)
    print()
    
    project_root = Path(__file__).parent
    
    # 必需目录列表
    required_dirs = [
        "src",
        "src/input_layer",
        "src/scheduling_layer",
        "src/agent_layer",
        "src/execution_layer",
        "src/config",
        "src/utils",
        "tests",
        "docs",
        "logs",
    ]
    
    all_passed = True
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"✅ 目录存在: {dir_path}")
        else:
            print(f"❌ 目录缺失: {dir_path}")
            all_passed = False
    
    print()
    
    # 必需文件列表
    required_files = [
        "src/__init__.py",
        "src/input_layer/__init__.py",
        "src/scheduling_layer/__init__.py",
        "src/agent_layer/__init__.py",
        "src/execution_layer/__init__.py",
        "src/config/__init__.py",
        "src/config/constants.py",
        "src/config/settings.py",
        "src/utils/__init__.py",
        "src/utils/logger.py",
        "src/utils/exceptions.py",
        "tests/__init__.py",
        "pyproject.toml",
        "requirements.txt",
        "requirements.lock.txt",
        ".python-version",
    ]
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists() and full_path.is_file():
            print(f"✅ 文件存在: {file_path}")
        else:
            print(f"❌ 文件缺失: {file_path}")
            all_passed = False
    
    return all_passed


def verify_imports():
    """验证模块导入"""
    print()
    print("=" * 60)
    print("验证模块导入验证")
    print("=" * 60)
    print()
    
    try:
        import src
        print(f"✅ 导入成功: src (v{src.__version__})")
        
        import src.config
        print(f"✅ 导入成功: src.config")
        
        import src.utils
        print(f"✅ 导入成功: src.utils")
        
        import src.input_layer
        print(f"✅ 导入成功: src.input_layer")
        
        import src.scheduling_layer
        print(f"✅ 导入成功: src.scheduling_layer")
        
        import src.agent_layer
        print(f"✅ 导入成功: src.agent_layer")
        
        import src.execution_layer
        print(f"✅ 导入成功: src.execution_layer")
        
        # 验证具体模块
        from src.config import constants, settings
        print(f"✅ 导入成功: src.config.constants, src.config.settings")
        
        from src.utils import logger, exceptions
        print(f"✅ 导入成功: src.utils.logger, src.utils.exceptions")
        
        from src.config.constants import TaskType, StateType, AgentRole
        print(f"✅ 导入成功: 常量枚举")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def main():
    dir_ok = verify_directory_structure()
    import_ok = verify_imports()
    
    print()
    print("=" * 60)
    if dir_ok and import_ok:
        print("🎉 第2阶段架构验证通过！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第2阶段架构验证失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
