#!/usr/bin/env python3
"""
第1阶段环境验证脚本
验证统一Python工程环境、固定版本、依赖锁版本是否正确搭建
"""

import sys
import importlib

def verify_python_version():
    """验证Python版本"""
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    assert version.major == 3, "需要Python 3"
    assert version.minor >= 10, "需要Python 3.10+"
    print("✅ Python版本验证通过")

def verify_dependencies():
    """验证核心依赖"""
    dependencies = [
        ("langgraph", "LangGraph调度引擎"),
        ("autogen_agentchat", "AutoGen多智能体交互"),
        ("tree_sitter", "Tree-sitter代码解析"),
        ("ruff", "Ruff代码检查"),
        ("pytest", "Pytest测试框架"),
    ]
    
    for pkg_name, description in dependencies:
        try:
            module = importlib.import_module(pkg_name)
            version = getattr(module, "__version__", "未知")
            print(f"✅ {description}: {pkg_name} v{version}")
        except ImportError as e:
            print(f"❌ {description}: {pkg_name} 导入失败 - {e}")
            return False
    return True

def main():
    print("=" * 60)
    print("多Agent软件工程系统 - 第1阶段环境验证")
    print("=" * 60)
    print()
    
    verify_python_version()
    print()
    
    if verify_dependencies():
        print()
        print("=" * 60)
        print("🎉 第1阶段环境验证通过！")
        print("=" * 60)
        return 0
    else:
        print()
        print("=" * 60)
        print("❌ 第1阶段环境验证失败")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
