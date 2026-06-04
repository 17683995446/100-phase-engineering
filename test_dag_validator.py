#!/usr/bin/env python3
"""
第8阶段: DAG单向依赖校验验证脚本
验证全局DAG单向依赖校验机制
"""

import sys


def test_dag_imports():
    """测试DAG模块导入"""
    print("=" * 60)
    print("测试: DAG模块导入")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import DAG, DAGNode, DAGValidator
        print("✅ DAG模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_dag():
    """测试基本DAG操作"""
    print()
    print("=" * 60)
    print("测试: 基本DAG操作")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import DAG
        
        dag = DAG("test_basic")
        print("✅ 创建DAG实例成功")
        
        dag.add_node("A")
        dag.add_node("B")
        dag.add_node("C")
        print("✅ 添加节点成功")
        
        dag.add_edge("B", "A")
        dag.add_edge("C", "B")
        print("✅ 添加边成功")
        
        deps_b = dag.get_dependencies("B")
        print(f"   B的依赖: {deps_b}")
        assert "A" in deps_b
        
        deps_c = dag.get_dependencies("C")
        print(f"   C的依赖: {deps_c}")
        assert "B" in deps_c
        
        dependents_a = dag.get_dependents("A")
        print(f"   A的依赖者: {dependents_a}")
        assert "B" in dependents_a
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_topological_sort():
    """测试拓扑排序"""
    print()
    print("=" * 60)
    print("测试: 拓扑排序")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import DAG
        
        dag = DAG("test_sort")
        
        dag.add_edge("scheduling_layer", "input_layer")
        dag.add_edge("agent_layer", "scheduling_layer")
        dag.add_edge("execution_layer", "agent_layer")
        print("✅ 添加四层依赖关系（后面的层依赖前面的层）")
        
        sorted_nodes = dag.topological_sort()
        print(f"✅ 拓扑排序成功: {sorted_nodes}")
        
        assert sorted_nodes is not None
        assert len(sorted_nodes) == 4
        assert sorted_nodes.index("input_layer") < sorted_nodes.index("scheduling_layer")
        assert sorted_nodes.index("scheduling_layer") < sorted_nodes.index("agent_layer")
        assert sorted_nodes.index("agent_layer") < sorted_nodes.index("execution_layer")
        print("✅ 拓扑排序验证通过（单向依赖正确）")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cycle_detection():
    """测试循环检测"""
    print()
    print("=" * 60)
    print("测试: 循环依赖检测")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import DAG
        
        print("测试1: 检测无环图")
        dag = DAG("no_cycle")
        dag.add_edge("B", "A")
        dag.add_edge("C", "B")
        dag.add_edge("D", "C")
        
        validation = dag.validate()
        print(f"   验证结果: {'有效' if validation['valid'] else '无效'}")
        assert validation["valid"]
        print("✅ 无环图验证通过")
        
        print()
        print("测试2: 检测有环图")
        dag2 = DAG("has_cycle")
        dag2.add_edge("B", "A")
        dag2.add_edge("C", "B")
        dag2.add_edge("A", "C")
        
        validation2 = dag2.validate()
        print(f"   验证结果: {'有效' if validation2['valid'] else '无效'}")
        assert not validation2["valid"]
        print(f"   检测到的循环: {validation2['cycles']}")
        assert len(validation2['cycles']) > 0
        print("✅ 有环图检测成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dag_validator():
    """测试DAG验证器"""
    print()
    print("=" * 60)
    print("测试: DAG验证器")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import DAGValidator
        
        validator = DAGValidator()
        print("✅ DAG验证器初始化成功")
        
        dag = validator.create_dag("architecture")
        dag.add_edge("scheduling_layer", "input_layer")
        dag.add_edge("agent_layer", "scheduling_layer")
        dag.add_edge("execution_layer", "agent_layer")
        print("✅ 创建架构DAG成功")
        
        result = validator.validate_architecture()
        print(f"   验证结果: {'有效' if result['valid'] else '无效'}")
        print(f"   DAG数量: {result['dag_count']}")
        assert result["valid"]
        print("✅ 架构DAG验证通过")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_circular_import_check():
    """测试循环导入检查"""
    print()
    print("=" * 60)
    print("测试: 循环导入检查")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import DAGValidator
        
        validator = DAGValidator()
        
        print("测试1: 无循环导入")
        good_deps = {
            "module_a": [],
            "module_b": ["module_a"],
            "module_c": ["module_b"]
        }
        result = validator.check_circular_import(good_deps)
        print(f"   结果: {'有循环' if result['has_circular'] else '无循环'}")
        assert not result["has_circular"]
        print("✅ 无循环导入检查通过")
        
        print()
        print("测试2: 有循环导入")
        bad_deps = {
            "module_x": ["module_y"],
            "module_y": ["module_z"],
            "module_z": ["module_x"]
        }
        result2 = validator.check_circular_import(bad_deps)
        print(f"   结果: {'有循环' if result2['has_circular'] else '无循环'}")
        print(f"   循环模块: {result2['circular_modules']}")
        assert result2["has_circular"]
        print("✅ 有循环导入检测成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_four_layer_architecture_validation():
    """测试四层架构DAG验证"""
    print()
    print("=" * 60)
    print("测试: 四层架构DAG验证")
    print("=" * 60)
    print()
    
    try:
        from src.scheduling_layer import DAGValidator
        
        validator = DAGValidator()
        dag = validator.create_dag("four_layer_architecture")
        
        dag.add_edge("scheduling_layer", "input_layer")
        dag.add_edge("agent_layer", "scheduling_layer")
        dag.add_edge("execution_layer", "agent_layer")
        print("✅ 创建四层架构DAG")
        
        sorted_layers = dag.topological_sort()
        print(f"✅ 拓扑排序: {' → '.join(sorted_layers)}")
        assert sorted_layers == ["input_layer", "scheduling_layer", "agent_layer", "execution_layer"]
        
        validation = dag.validate()
        print(f"✅ 验证结果: {'有效' if validation['valid'] else '无效'}")
        assert validation["valid"]
        
        all_deps = dag.get_all_dependencies("execution_layer")
        print(f"   执行层依赖的所有层: {all_deps}")
        assert "input_layer" in all_deps
        assert "scheduling_layer" in all_deps
        assert "agent_layer" in all_deps
        
        print()
        print("✅ 四层架构DAG验证完全通过")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print()
    print("╔" + "=" * 58 + "╗")
    print("║  第8阶段: DAG单向依赖校验机制验证  ║")
    print("╚" + "=" * 58 + "╝")
    
    success = True
    success = success and test_dag_imports()
    success = success and test_basic_dag()
    success = success and test_topological_sort()
    success = success and test_cycle_detection()
    success = success and test_dag_validator()
    success = success and test_circular_import_check()
    success = success and test_four_layer_architecture_validation()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 第8阶段DAG单向依赖校验验证全部通过！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第8阶段验证未全部通过")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
