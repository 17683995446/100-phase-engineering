#!/usr/bin/env python3
"""
第3阶段 LangGraph 验证脚本
验证 LangGraph 基础调度内核是否正确集成
"""

import sys


def verify_langgraph_import():
    """验证 LangGraph 相关导入"""
    print("=" * 60)
    print("验证 LangGraph 导入验证")
    print("=" * 60)
    print()
    
    try:
        import langgraph
        print(f"✅ LangGraph 版本: {getattr(langgraph, '__version__', 'unknown')}")
        
        from langgraph.graph import StateGraph, END
        print("✅ StateGraph, END 导入成功")
        
        from langgraph.checkpoint.memory import MemorySaver
        print("✅ MemorySaver 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def verify_scheduling_layer():
    """验证调度层模块"""
    print()
    print("=" * 60)
    print("验证调度层模块验证")
    print("=" * 60)
    print()
    
    try:
        import src.scheduling_layer
        print("✅ src.scheduling_layer 导入成功")
        
        from src.scheduling_layer import (
            GlobalState,
            TaskStatus,
            create_initial_state,
            WorkflowEngine
        )
        print("✅ 状态模型导入成功")
        
        from src.config.constants import TaskType
        print("✅ 常量导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_engine():
    """测试工作流引擎"""
    print()
    print("=" * 60)
    print("测试工作流引擎测试")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import WorkflowEngine, TaskStatus
        from src.config.constants import TaskType
        
        # 创建引擎
        engine = WorkflowEngine()
        print("✅ WorkflowEngine 初始化成功")
        
        # 运行测试任务
        test_input = "这是一个测试任务输入"
        result = engine.run_task(TaskType.REQUIREMENT, test_input)
        
        print(f"✅ 任务执行完成: {result['task']['task_id']}")
        print(f"   任务状态: {result['task']['status']}")
        print(f"   最终输出: {result['business']['final_output']}")
        
        # 验证结果
        assert result["task"]["status"] == TaskStatus.COMPLETED
        assert result["business"]["final_output"] is not None
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    import_ok = verify_langgraph_import()
    layer_ok = verify_scheduling_layer()
    test_ok = test_workflow_engine()
    
    print()
    print("=" * 60)
    if import_ok and layer_ok and test_ok:
        print("🎉 第3阶段 LangGraph 验证通过！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第3阶段 LangGraph 验证失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
