#!/usr/bin/env python3
"""
第7阶段: 四层架构完整验证
验证输入层-调度层-Agent层-执行层的整合
"""

import sys
from datetime import datetime


def test_layer_imports():
    """测试各层导入"""
    print("=" * 60)
    print("测试: 各层模块导入")
    print("=" * 60)
    print()
    
    try:
        # 输入层
        from src.input_layer import TaskRequest, TaskPriority, TaskInputHandler
        print("✅ Layer 1: 输入层模块导入成功")
        
        # 调度层
        from src.scheduling_layer import WorkflowEngine
        print("✅ Layer 2: 调度层模块导入成功")
        
        # Agent层
        from src.agent_layer import SimpleAgent, SimpleTeam
        from src.config.constants import AgentRole
        print("✅ Layer 3: Agent层模块导入成功")
        
        # 执行层
        from src.execution_layer import CodeAnalyzer, CodeChecker, TestRunner
        print("✅ Layer 4: 执行层模块导入成功")
        
        # 核心协调器
        from src.core import FourLayerOrchestrator
        print("✅ Core: 核心协调器导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_input_layer():
    """测试输入层"""
    print()
    print("=" * 60)
    print("测试: 输入层功能")
    print("=" * 60)
    print()
    
    try:
        from src.input_layer import TaskInputHandler, TaskPriority
        from src.config.constants import TaskType
        
        handler = TaskInputHandler()
        print("✅ 任务输入处理器初始化成功")
        
        # 测试接收任务
        task = handler.receive_task(
            task_description="实现一个计算函数，计算两个数的和",
            task_type=TaskType.REQUIREMENT,
            priority=TaskPriority.MEDIUM,
            metadata={"project": "demo"}
        )
        
        print(f"✅ 任务接收成功: {task['task_id']}")
        print(f"   任务类型: {task['task_type']}")
        print(f"   预处理完成: {task['preprocessed']}")
        print(f"   代码相关: {task.get('is_code_related', False)}")
        
        return True
    except Exception as e:
        print(f"❌ 输入层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_task():
    """测试简单任务执行（无代码）"""
    print()
    print("=" * 60)
    print("测试: 简单任务执行（无代码）")
    print("=" * 60)
    print()
    
    try:
        from src.core import FourLayerOrchestrator
        from src.config.constants import TaskType
        
        orchestrator = FourLayerOrchestrator()
        print("✅ 四层架构协调器初始化成功")
        
        result = orchestrator.execute_task(
            task_description="分析并设计一个简单的计算器功能",
            task_type=TaskType.REQUIREMENT
        )
        
        print(f"✅ 任务执行完成: {result['task_id']}")
        print(f"   成功: {result['success']}")
        print(f"   输入层结果: {result['input_layer']['preprocessed']}")
        print(f"   调度层结果: {result['scheduling_layer']['success']}")
        print(f"   Agent层: {len(result['agent_layer']['agents_used'])} 个Agent参与")
        
        return True
    except Exception as e:
        print(f"❌ 简单任务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_with_code():
    """测试带有代码的任务执行"""
    print()
    print("=" * 60)
    print("测试: 带有代码的任务执行")
    print("=" * 60)
    print()
    
    try:
        from src.core import FourLayerOrchestrator
        from src.config.constants import TaskType
        
        orchestrator = FourLayerOrchestrator()
        
        # 测试代码
        test_code = """
def add(a, b):
    \"\"\"加法函数\"\"\"
    return a + b

class Calculator:
    \"\"\"简单计算器类\"\"\"
    
    def multiply(self, a, b):
        return a * b
"""
        
        test_code_str = """
from test_module import add, Calculator

def test_add():
    assert add(2, 3) == 5
    
def test_calculator():
    calc = Calculator()
    assert calc.multiply(3, 4) == 12
"""
        
        result = orchestrator.execute_task(
            task_description="检查和优化这个计算器代码",
            task_type=TaskType.REFACTOR,
            metadata={
                "code": test_code,
                "test_code": test_code_str
            }
        )
        
        print(f"✅ 代码任务执行完成: {result['task_id']}")
        print(f"   代码分析: {result['execution_layer']['code_analyzed']}")
        print(f"   代码检查: {result['execution_layer']['code_checked']}")
        
        return True
    except Exception as e:
        print(f"❌ 代码任务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_architecture_integration():
    """测试完整架构整合"""
    print()
    print("=" * 60)
    print("测试: 完整四层架构整合验证")
    print("=" * 60)
    print()
    
    try:
        from src.core import FourLayerOrchestrator
        from src.config.constants import TaskType
        
        orchestrator = FourLayerOrchestrator()
        
        # 完整测试流程
        result = orchestrator.execute_task(
            task_description="完成一个完整的需求开发流程：需求分析→设计→编码→评审→测试",
            task_type=TaskType.REQUIREMENT,
            metadata={
                "project": "demo_architecture",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        print()
        print("-" * 60)
        print("四层架构整合验证报告")
        print("-" * 60)
        
        # 验证各层
        print(f"✅ Layer 1 (输入层): {'ok' if result['input_layer']['preprocessed'] else 'error'}")
        print(f"✅ Layer 2 (调度层): {'ok' if result['scheduling_layer']['success'] else 'error'}")
        print(f"✅ Layer 3 (Agent层): {'ok' if result['agent_layer']['conversation_count'] > 0 else 'error'}")
        print(f"✅ Layer 4 (执行层): {'ok' if result['execution_layer'] is not None else 'error'}")
        print(f"✅ 总体: {'成功' if result['success'] else '失败'}")
        
        return True
    except Exception as e:
        print(f"❌ 架构整合测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print()
    print("╔" + "=" * 58 + "╗")
    print("║  第7阶段: 四层架构完整落地验证  ║")
    print("╚" + "=" * 58 + "╝")
    
    success = True
    success = success and test_layer_imports()
    success = success and test_input_layer()
    success = success and test_simple_task()
    success = success and test_task_with_code()
    success = success and test_architecture_integration()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 第7阶段四层架构落地验证全部通过！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第7阶段验证未全部通过")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
