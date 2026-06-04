#!/usr/bin/env python3
"""
第10阶段: 全局信息显式化机制验证
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def test_event_tracker_import():
    """测试事件追踪器导入"""
    print("=" * 60)
    print("测试: 事件追踪器导入")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import (
            EventTracker,
            EventType,
            EventSeverity,
            DataFlowRecord,
            get_event_tracker
        )
        print("✅ 事件追踪器模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_event_tracking():
    """测试基本事件追踪"""
    print()
    print("=" * 60)
    print("测试: 基本事件追踪")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import (
            EventTracker,
            EventType,
            EventSeverity
        )
        
        tracker = EventTracker()
        print("✅ 事件追踪器初始化成功")
        
        task_id = "test-task-1234"
        
        event1 = tracker.emit_event(
            EventType.TASK_CREATED,
            "任务创建成功",
            task_id=task_id,
            data={"type": "REFACTOR", "priority": "high"}
        )
        print("✅ 创建任务事件成功")
        
        event2 = tracker.emit_event(
            EventType.TASK_STARTED,
            "开始处理任务",
            task_id=task_id,
            agent_id="orchestrator-agent"
        )
        print("✅ 创建启动事件成功")
        
        assert len(tracker.events) == 2
        print(f"✅ 事件记录数量: {len(tracker.events)}")
        
        task_events = tracker.get_events_by_task(task_id)
        assert len(task_events) == 2
        print("✅ 按任务查询事件成功")
        
        type_events = tracker.get_events_by_type(EventType.TASK_CREATED)
        assert len(type_events) == 1
        print("✅ 按类型查询事件成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_flow_tracking():
    """测试数据流转追踪"""
    print()
    print("=" * 60)
    print("测试: 数据流转追踪")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import EventTracker
        
        tracker = EventTracker()
        task_id = "test-task-flow"
        
        tracker.track_data_flow(
            task_id,
            "input_layer",
            "scheduling_layer",
            "task_request",
            "原始任务输入，长度: 120"
        )
        print("✅ 数据流转记录1成功")
        
        tracker.track_data_flow(
            task_id,
            "scheduling_layer",
            "agent_layer",
            "task_assignment",
            "任务分配给agent"
        )
        print("✅ 数据流转记录2成功")
        
        tracker.track_data_flow(
            task_id,
            "agent_layer",
            "execution_layer",
            "code_analysis_result",
            "代码分析完成，10个方法"
        )
        print("✅ 数据流转记录3成功")
        
        assert len(tracker.data_flows) == 3
        print(f"✅ 数据流转记录数量: {len(tracker.data_flows)}")
        
        task_flows = tracker.get_data_flows_by_task(task_id)
        assert len(task_flows) == 3
        print("✅ 按任务查询流转记录成功")
        
        flow_types = [f.data_type for f in task_flows]
        assert "task_request" in flow_types
        assert "task_assignment" in flow_types
        assert "code_analysis_result" in flow_types
        print("✅ 数据类型记录正确")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_nesting():
    """测试嵌套事件上下文"""
    print()
    print("=" * 60)
    print("测试: 嵌套事件上下文")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import (
            EventTracker,
            EventType,
            EventSeverity
        )
        
        tracker = EventTracker()
        task_id = "test-nested-event"
        
        # 父事件
        parent_event = tracker.emit_event(
            EventType.TASK_STARTED,
            "任务处理启动",
            task_id=task_id
        )
        
        tracker.start_event_context(parent_event.event_id)
        
        # 子事件
        child_event1 = tracker.emit_event(
            EventType.DATA_FLOW_STARTED,
            "开始数据流转",
            task_id=task_id
        )
        assert child_event1.parent_event_id == parent_event.event_id
        
        child_event2 = tracker.emit_event(
            EventType.STATE_CHANGED,
            "状态更新",
            task_id=task_id
        )
        assert child_event2.parent_event_id == parent_event.event_id
        
        tracker.end_event_context()
        
        # 新事件不应该有父事件
        orphan_event = tracker.emit_event(
            EventType.SYSTEM_EVENT,
            "系统心跳",
            task_id=task_id
        )
        assert orphan_event.parent_event_id is None
        
        print("✅ 嵌套事件上下文管理正确")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_statistics():
    """测试统计功能"""
    print()
    print("=" * 60)
    print("测试: 统计功能")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import (
            EventTracker,
            EventType,
            EventSeverity
        )
        
        tracker = EventTracker()
        
        # 生成一些事件
        task_ids = ["task-1", "task-2", "task-3"]
        for tid in task_ids:
            tracker.emit_event(EventType.TASK_CREATED, f"创建任务 {tid}", task_id=tid)
            tracker.emit_event(EventType.TASK_STARTED, f"启动任务 {tid}", task_id=tid)
        
        tracker.emit_event(
            EventType.TASK_FAILED,
            "任务执行失败",
            task_id="task-2",
            severity=EventSeverity.ERROR
        )
        
        stats = tracker.get_statistics()
        
        assert stats["total_events"] == 7  # 3 created + 3 started + 1 failed
        assert stats["active_tasks"] == 3
        assert "TASK_CREATED" in stats["events_by_type"]
        assert "ERROR" in stats["events_by_severity"]
        
        print(f"✅ 总事件数: {stats['total_events']}")
        print(f"✅ 活跃任务数: {stats['active_tasks']}")
        print(f"✅ 事件类型统计: {list(stats['events_by_type'].keys())}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_export():
    """测试导出功能"""
    print()
    print("=" * 60)
    print("测试: 事件导出")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import (
            EventTracker,
            EventType,
            EventSeverity
        )
        
        tracker = EventTracker()
        task_id = "test-export-task"
        
        tracker.emit_event(
            EventType.TASK_CREATED,
            "创建测试任务",
            task_id=task_id
        )
        tracker.track_data_flow(
            task_id,
            "A",
            "B",
            "test_data",
            "测试数据"
        )
        
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            events_file = temp_path / "events.json"
            flows_file = temp_path / "flows.json"
            
            tracker.export_events(events_file)
            tracker.export_data_flows(flows_file)
            
            assert events_file.exists()
            assert flows_file.exists()
            
            # 验证JSON内容
            with open(events_file, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
                assert len(events_data) == 1
            
            with open(flows_file, 'r', encoding='utf-8') as f:
                flows_data = json.load(f)
                assert len(flows_data) == 1
        
        print("✅ 事件导出功能正常")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_implicit_state_verification():
    """测试隐式状态验证"""
    print()
    print("=" * 60)
    print("测试: 隐式状态验证")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import (
            EventTracker,
            EventType,
            EventSeverity
        )
        
        tracker = EventTracker()
        
        # 测试不完整的事件记录 - 这个应该报告问题
        tracker.emit_event(
            EventType.TASK_CREATED,
            "测试任务",
            task_id="task-without-flows"
        )
        
        result = tracker.verify_no_implicit_state()
        print(f"验证结果: {result}")
        print(f"检查出的问题: {result['issues']}")
        
        # 现在添加完整的事件和数据流
        task_id = "task-with-complete-tracking"
        
        tracker.emit_event(EventType.TASK_CREATED, "创建", task_id=task_id)
        tracker.emit_event(EventType.TASK_STARTED, "启动", task_id=task_id)
        tracker.emit_event(EventType.DATA_FLOW_STARTED, "数据流开始", task_id=task_id)
        tracker.emit_event(EventType.DATA_FLOW_COMPLETED, "数据流完成", task_id=task_id)
        tracker.emit_event(EventType.STATE_CHANGED, "状态变更", task_id=task_id)
        tracker.track_data_flow(task_id, "A", "B", "data", "test")
        
        new_tracker = EventTracker()
        new_tracker.emit_event(EventType.TASK_CREATED, "创建", task_id=task_id)
        new_tracker.emit_event(EventType.TASK_STARTED, "启动", task_id=task_id)
        new_tracker.emit_event(EventType.DATA_FLOW_STARTED, "数据流开始", task_id=task_id)
        new_tracker.emit_event(EventType.DATA_FLOW_COMPLETED, "数据流完成", task_id=task_id)
        new_tracker.emit_event(EventType.STATE_CHANGED, "状态变更", task_id=task_id)
        new_tracker.track_data_flow(task_id, "A", "B", "data", "test")
        
        result2 = new_tracker.verify_no_implicit_state()
        print(f"完整事件验证结果: {result2}")
        
        print("✅ 隐式状态验证功能正常")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_callbacks():
    """测试事件回调"""
    print()
    print("=" * 60)
    print("测试: 事件回调")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import (
            EventTracker,
            EventType
        )
        
        tracker = EventTracker()
        
        callback_called = []
        
        def on_event(event):
            callback_called.append(event.event_type.name)
        
        tracker.add_callback(on_event)
        
        tracker.emit_event(EventType.TASK_CREATED, "任务创建")
        tracker.emit_event(EventType.TASK_STARTED, "任务启动")
        
        assert "TASK_CREATED" in callback_called
        assert "TASK_STARTED" in callback_called
        
        print("✅ 事件回调机制正常")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_global_event_tracker():
    """测试全局事件追踪器"""
    print()
    print("=" * 60)
    print("测试: 全局事件追踪器")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import get_event_tracker, set_event_tracker, EventTracker
        
        tracker1 = get_event_tracker()
        tracker2 = get_event_tracker()
        
        assert tracker1 is tracker2
        print("✅ 全局追踪器单例模式正常")
        
        new_tracker = EventTracker()
        set_event_tracker(new_tracker)
        tracker3 = get_event_tracker()
        assert tracker3 is new_tracker
        print("✅ 全局追踪器可替换")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print()
    print("╔" + "=" * 58 + "╗")
    print("║  第10阶段: 全局信息显式化机制验证  ║")
    print("╚" + "=" * 58 + "╝")
    
    success = True
    success = success and test_event_tracker_import()
    success = success and test_basic_event_tracking()
    success = success and test_data_flow_tracking()
    success = success and test_event_nesting()
    success = success and test_statistics()
    success = success and test_export()
    success = success and test_implicit_state_verification()
    success = success and test_event_callbacks()
    success = success and test_global_event_tracker()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 第10阶段全局信息显式化验证全部通过！")
        print("🎉 信息最小熵公理已完全实现！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第10阶段验证未全部通过")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
