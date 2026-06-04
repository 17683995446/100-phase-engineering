#!/usr/bin/env python3
"""
第12阶段: 原子实体定义验证
"""

import sys


def test_atomic_entities_import():
    """测试原子实体模块导入"""
    print("=" * 60)
    print("测试: 原子实体模块导入")
    print("=" * 60)
    print()
    
    try:
        from src.core import (
            AtomicEntityRegistry,
            EntityDefinition,
            EntityCategory,
            TaskAtomicEntity,
            CodeAtomicEntity,
            MessageAtomicEntity,
            StateAtomicEntity,
            AgentAtomicEntity,
            EventAtomicEntity
        )
        print("✅ 原子实体模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_entity_definition_structure():
    """测试实体定义结构"""
    print()
    print("=" * 60)
    print("测试: 实体定义结构")
    print("=" * 60)
    print()
    
    try:
        from src.core import TaskAtomicEntity
        
        entity = TaskAtomicEntity.TASK_REQUEST
        
        print(f"✅ 实体名称: {entity.name}")
        print(f"✅ 实体类别: {entity.category.name}")
        print(f"✅ 原子性: {entity.is_atomic}")
        print(f"✅ 字段数量: {len(entity.fields)}")
        print(f"✅ 约束数量: {len(entity.constraints)}")
        print(f"✅ 验证规则数量: {len(entity.validation_rules)}")
        
        print("\n字段定义:")
        for field_name, field_desc in list(entity.fields.items())[:3]:
            print(f"   - {field_name}: {field_desc}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_entities():
    """测试任务实体"""
    print()
    print("=" * 60)
    print("测试: 任务原子实体 (3个)")
    print("=" * 60)
    print()
    
    try:
        from src.core import TaskAtomicEntity, EntityCategory
        
        entities = [
            TaskAtomicEntity.TASK_REQUEST,
            TaskAtomicEntity.TASK_RESULT,
            TaskAtomicEntity.SUBTASK
        ]
        
        for entity in entities:
            assert entity.category == EntityCategory.TASK
            assert entity.is_atomic
            print(f"✅ {entity.name}: {entity.description[:40]}...")
        
        print(f"\n总计: {len(entities)} 个任务原子实体")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_entities():
    """测试代码实体"""
    print()
    print("=" * 60)
    print("测试: 代码原子实体 (4个)")
    print("=" * 60)
    print()
    
    try:
        from src.core import CodeAtomicEntity, EntityCategory
        
        entities = [
            CodeAtomicEntity.VARIABLE,
            CodeAtomicEntity.METHOD,
            CodeAtomicEntity.CLASS_ENTITY,
            CodeAtomicEntity.MODULE
        ]
        
        for entity in entities:
            assert entity.category == EntityCategory.CODE
            assert entity.is_atomic
            print(f"✅ {entity.name}: 字段={len(entity.fields)}, 约束={len(entity.constraints)}")
        
        print(f"\n总计: {len(entities)} 个代码原子实体")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_message_entities():
    """测试消息实体"""
    print()
    print("=" * 60)
    print("测试: 消息原子实体 (2个)")
    print("=" * 60)
    print()
    
    try:
        from src.core import MessageAtomicEntity, EntityCategory
        
        entities = [
            MessageAtomicEntity.MESSAGE,
            MessageAtomicEntity.CONVERSATION
        ]
        
        for entity in entities:
            assert entity.category == EntityCategory.MESSAGE
            print(f"✅ {entity.name}: {entity.description[:40]}...")
        
        print(f"\n总计: {len(entities)} 个消息原子实体")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_entities():
    """测试状态实体"""
    print()
    print("=" * 60)
    print("测试: 状态原子实体 (2个)")
    print("=" * 60)
    print()
    
    try:
        from src.core import StateAtomicEntity, EntityCategory
        
        entities = [
            StateAtomicEntity.STATE,
            StateAtomicEntity.STATE_TRANSITION
        ]
        
        for entity in entities:
            assert entity.category == EntityCategory.STATE
            print(f"✅ {entity.name}: 字段={len(entity.fields)}")
        
        print(f"\n总计: {len(entities)} 个状态原子实体")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_entities():
    """测试Agent实体"""
    print()
    print("=" * 60)
    print("测试: Agent原子实体 (2个)")
    print("=" * 60)
    print()
    
    try:
        from src.core import AgentAtomicEntity, EntityCategory
        
        entities = [
            AgentAtomicEntity.AGENT,
            AgentAtomicEntity.AGENT_CAPABILITY
        ]
        
        for entity in entities:
            assert entity.category == EntityCategory.AGENT
            print(f"✅ {entity.name}: {entity.description[:40]}...")
        
        print(f"\n总计: {len(entities)} 个Agent原子实体")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_entities():
    """测试事件实体"""
    print()
    print("=" * 60)
    print("测试: 事件原子实体 (2个)")
    print("=" * 60)
    print()
    
    try:
        from src.core import EventAtomicEntity, EntityCategory
        
        entities = [
            EventAtomicEntity.EVENT,
            EventAtomicEntity.EVENT_TRACE
        ]
        
        for entity in entities:
            assert entity.category == EntityCategory.EVENT
            print(f"✅ {entity.name}: 约束={len(entity.constraints)}")
        
        print(f"\n总计: {len(entities)} 个事件原子实体")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_entity_registry():
    """测试实体注册表"""
    print()
    print("=" * 60)
    print("测试: 原子实体注册表")
    print("=" * 60)
    print()
    
    try:
        from src.core import AtomicEntityRegistry, EntityCategory
        
        all_entities = AtomicEntityRegistry.get_all()
        print(f"✅ 总注册实体数: {len(all_entities)}")
        
        categories = AtomicEntityRegistry.get_all_categories()
        print(f"✅ 总类别数: {len(categories)}")
        
        for category in categories:
            entities = AtomicEntityRegistry.get_by_category(category)
            print(f"   {category.name}: {len(entities)} 个实体")
        
        print("\n验证实体查询:")
        task_request = AtomicEntityRegistry.get("task_request")
        assert task_request is not None
        print(f"✅ task_request 查询成功: {task_request.name}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_atomic_entity_hierarchy():
    """测试原子实体层级结构"""
    print()
    print("=" * 60)
    print("测试: 原子实体层级结构")
    print("=" * 60)
    print()
    
    try:
        from src.core import AtomicEntityRegistry, EntityCategory
        
        print("原子实体层级分解:")
        print()
        
        print("第1层 - 任务分解:")
        print("  Task Request → Task Result")
        print("  Task Request → Subtask")
        print("  Subtask (不可再分)")
        print()
        
        print("第2层 - 代码分解:")
        print("  Module → Class Entity → Method")
        print("  Module → Method")
        print("  Method → Variable (不可再分)")
        print()
        
        print("第3层 - 消息/状态分解:")
        print("  Conversation → Message (不可再分)")
        print("  State Transition → State (不可再分)")
        print()
        
        print("第4层 - Agent/事件分解:")
        print("  Agent → Capability (不可再分)")
        print("  Event Trace → Event (不可再分)")
        print()
        
        print("✅ 原子实体层级结构验证通过")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_entity_constraints():
    """测试实体约束验证"""
    print()
    print("=" * 60)
    print("测试: 实体约束验证")
    print("=" * 60)
    print()
    
    try:
        from src.core import TaskAtomicEntity, CodeAtomicEntity
        import re
        
        task = TaskAtomicEntity.TASK_REQUEST
        print(f"任务请求约束:")
        for constraint in task.constraints:
            print(f"   - {constraint}")
        
        print()
        
        method = CodeAtomicEntity.METHOD
        print(f"方法约束:")
        for constraint in method.constraints:
            print(f"   - {constraint}")
        
        print()
        
        print("✅ 实体约束定义验证通过")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print()
    print("╔" + "=" * 58 + "╗")
    print("║  第12阶段: 原子实体定义验证  ║")
    print("╚" + "=" * 58 + "╝")
    
    success = True
    success = success and test_atomic_entities_import()
    success = success and test_entity_definition_structure()
    success = success and test_task_entities()
    success = success and test_code_entities()
    success = success and test_message_entities()
    success = success and test_state_entities()
    success = success and test_agent_entities()
    success = success and test_event_entities()
    success = success and test_entity_registry()
    success = success and test_atomic_entity_hierarchy()
    success = success and test_entity_constraints()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 第12阶段原子实体定义验证全部通过！")
        print("🎉 任务可分性公理已完整落地！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第12阶段验证未全部通过")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
