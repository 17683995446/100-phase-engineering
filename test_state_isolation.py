#!/usr/bin/env python3
"""
第9阶段: 任务状态、业务状态、系统状态三层隔离验证
"""

import sys
from datetime import datetime


def test_state_imports():
    """测试状态模块导入"""
    print("=" * 60)
    print("测试: 状态模块导入")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import (
            SystemState, TaskState, BusinessState, GlobalState,
            TaskStatus, StateManager
        )
        print("✅ 状态模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_manager_initialization():
    """测试状态管理器初始化"""
    print()
    print("=" * 60)
    print("测试: 状态管理器初始化")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import StateManager
        
        manager = StateManager()
        print("✅ 状态管理器初始化成功")
        
        # 验证系统状态
        system_state = manager.get_system_state()
        print(f"   系统健康状态: {system_state.get('health_status')}")
        assert system_state.get("health_status") == "healthy"
        assert system_state.get("active_tasks") == 0
        assert system_state.get("version") is not None
        print("✅ 系统状态验证通过")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_three_layer_separation():
    """测试三层状态分离"""
    print()
    print("=" * 60)
    print("测试: 三层状态分离")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import StateManager, TaskStatus
        
        manager = StateManager()
        
        # 创建任务状态
        task_id = "test_task_001"
        task_state = manager.create_task_state(task_id, "REFACTOR", priority=2)
        print(f"✅ 创建任务状态: {task_id}")
        assert task_state.get("status") == TaskStatus.PENDING
        assert task_state.get("priority") == 2
        
        # 创建业务状态
        business_state = manager.create_business_state(
            task_id,
            "Refactor the calculator module",
            {"project": "demo"}
        )
        print("✅ 创建业务状态")
        assert "business_context" in business_state
        
        # 验证三层状态独立
        system_state = manager.get_system_state()
        assert system_state.get("active_tasks") == 1
        print(f"   系统状态 - 活跃任务: {system_state.get('active_tasks')}")
        
        task_result = manager.get_task_state(task_id)
        assert task_result is not None
        assert task_result.get("task_id") == task_id
        
        business_result = manager.get_business_state(task_id)
        assert business_result is not None
        assert business_result.get("original_input") == "Refactor the calculator module"
        
        # 验证状态隔离
        validation = manager.validate_state_isolation()
        assert validation["valid"], f"状态隔离验证失败: {validation['issues']}"
        print("✅ 三层状态隔离验证通过")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_update_and_history():
    """测试状态更新和历史记录"""
    print()
    print("=" * 60)
    print("测试: 状态更新和历史记录")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import StateManager, TaskStatus
        
        manager = StateManager()
        task_id = "test_task_002"
        
        manager.create_task_state(task_id, "BUG_FIX")
        
        # 第一次状态变更
        updated = manager.update_task_status(
            task_id, TaskStatus.ANALYZING,
            progress=0.25,
            agent="analyzer_agent",
            comment="开始分析问题"
        )
        assert updated is not None
        assert updated.get("status") == TaskStatus.ANALYZING
        assert updated.get("progress") == 0.25
        print("✅ 任务状态变更 - 分析中")
        
        # 第二次状态变更
        updated = manager.update_task_status(
            task_id, TaskStatus.IN_PROGRESS,
            progress=0.5,
            agent="developer_agent",
            comment="开始修复"
        )
        assert updated is not None
        assert len(updated.get("task_history", [])) == 2
        print("✅ 任务状态变更 - 进行中")
        
        # 验证历史记录
        history = updated.get("task_history", [])
        assert len(history) == 2
        assert history[0]["new_status"] == "ANALYZING"
        assert history[1]["new_status"] == "IN_PROGRESS"
        print("✅ 任务历史记录验证通过")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_business_state_updates():
    """测试业务状态更新"""
    print()
    print("=" * 60)
    print("测试: 业务状态更新")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import StateManager
        
        manager = StateManager()
        task_id = "test_task_003"
        
        manager.create_business_state(task_id, "Implement feature X")
        
        # 更新分析结果
        manager.update_business_field(
            task_id, "analysis_result",
            "The feature requires changes to 3 modules",
            validator="analyzer_agent"
        )
        print("✅ 更新业务状态 - 分析结果")
        
        # 更新架构设计
        manager.update_business_field(
            task_id, "architecture_design",
            "Add new interface and refactor existing code"
        )
        print("✅ 更新业务状态 - 架构设计")
        
        # 更新最终输出
        manager.update_business_field(
            task_id, "final_output",
            "Feature X implemented successfully"
        )
        print("✅ 更新业务状态 - 最终输出")
        
        # 验证业务状态
        business_state = manager.get_business_state(task_id)
        assert business_state is not None
        assert business_state.get("analysis_result") is not None
        assert business_state.get("architecture_design") is not None
        assert business_state.get("final_output") is not None
        print("✅ 业务状态更新验证通过")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_global_state_aggregation():
    """测试全局状态聚合"""
    print()
    print("=" * 60)
    print("测试: 全局状态聚合")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import StateManager, TaskStatus
        
        manager = StateManager()
        task_id = "test_task_004"
        
        # 创建全局状态
        global_state = manager.create_global_state(
            task_id,
            "FEATURE",
            "Create a new reporting module",
            priority=3
        )
        print("✅ 创建全局状态成功")
        
        # 验证三层状态都存在
        assert "system" in global_state
        assert "task" in global_state
        assert "business" in global_state
        print("✅ 三层状态在全局中都存在")
        
        # 更新状态
        manager.update_task_status(
            task_id, TaskStatus.COMPLETED, progress=1.0
        )
        manager.update_business_field(
            task_id, "final_output", "Reporting module created"
        )
        
        # 重新获取全局状态
        refreshed = manager.get_global_state(task_id)
        assert refreshed is not None
        assert refreshed["task"]["status"] == TaskStatus.COMPLETED
        assert refreshed["business"]["final_output"] == "Reporting module created"
        print("✅ 全局状态更新正确")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_system_error_recording():
    """测试系统错误记录"""
    print()
    print("=" * 60)
    print("测试: 系统错误记录")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import StateManager
        
        manager = StateManager()
        
        # 记录错误
        error_msg = "Database connection failed"
        manager.record_system_error(error_msg)
        print("✅ 系统错误记录成功")
        
        # 验证
        system_state = manager.get_system_state()
        assert system_state.get("health_status") == "degraded"
        assert system_state.get("last_error_msg") == error_msg
        assert system_state.get("last_error_time") is not None
        print("✅ 系统错误验证通过")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_tasks():
    """测试多任务支持"""
    print()
    print("=" * 60)
    print("测试: 多任务支持")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import StateManager, TaskStatus
        
        manager = StateManager()
        
        # 创建多个任务
        task_ids = [f"multi_task_{i:03d}" for i in range(3)]
        for i, task_id in enumerate(task_ids):
            manager.create_global_state(
                task_id,
                ["FEATURE", "BUG_FIX", "REFACTOR"][i],
                f"Task {i + 1} input"
            )
        print("✅ 创建多个任务成功")
        
        # 验证系统状态
        system_state = manager.get_system_state()
        assert system_state.get("active_tasks") == 3
        print(f"   活跃任务: {system_state.get('active_tasks')}")
        
        # 更新第一个任务
        manager.update_task_status(task_ids[0], TaskStatus.IN_PROGRESS)
        manager.update_business_field(task_ids[0], "analysis_result", "Done analysis")
        
        # 完成第二个任务
        manager.complete_task(task_ids[1])
        
        # 获取状态摘要
        summary = manager.get_status_summary()
        assert summary["active_tasks_count"] == 3
        assert summary["total_tasks_processed"] == 1
        print("✅ 多任务状态摘要验证通过")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_readonly_access():
    """测试只读访问保护"""
    print()
    print("=" * 60)
    print("测试: 只读访问保护")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import StateManager, TaskStatus
        
        manager = StateManager()
        task_id = "readonly_test"
        
        manager.create_global_state(
            task_id,
            "FEATURE",
            "Test readonly access"
        )
        
        # 获取状态（应该是深拷贝）
        task_state = manager.get_task_state(task_id)
        assert task_state is not None
        
        # 尝试修改返回的状态（不应该影响原始状态）
        original_status = task_state.get("status")
        task_state["status"] = TaskStatus.COMPLETED
        
        # 重新获取验证
        refreshed = manager.get_task_state(task_id)
        assert refreshed is not None
        assert refreshed.get("status") == original_status
        print("✅ 只读访问保护验证通过 - 修改副本不影响原始状态")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print()
    print("╔" + "=" * 58 + "╗")
    print("║  第9阶段: 三层状态隔离验证  ║")
    print("╚" + "=" * 58 + "╝")
    
    success = True
    success = success and test_state_imports()
    success = success and test_state_manager_initialization()
    success = success and test_three_layer_separation()
    success = success and test_state_update_and_history()
    success = success and test_business_state_updates()
    success = success and test_global_state_aggregation()
    success = success and test_system_error_recording()
    success = success and test_multiple_tasks()
    success = success and test_readonly_access()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 第9阶段三层状态隔离验证全部通过！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第9阶段验证未全部通过")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
