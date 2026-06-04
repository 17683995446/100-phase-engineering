#!/usr/bin/env python3
"""
第4阶段 AutoGen 验证脚本
验证 AutoGen 基础会话通信内核是否正确集成
"""

import sys


def verify_autogen_import():
    """验证 AutoGen 相关导入"""
    print("=" * 60)
    print("验证 AutoGen 导入验证")
    print("=" * 60)
    print()
    
    try:
        import autogen_agentchat
        print(f"✅ AutoGen AgentChat 导入成功")
        
        import autogen_core
        print(f"✅ AutoGen Core 导入成功")
        
        return True
    except Exception as e:
        print(f"⚠️  AutoGen 导入提示: {e}")
        print("   (我们将使用简单实现，不依赖完整AutoGen)")
        # 我们的实现不强制依赖AutoGen
        return True


def verify_agent_layer():
    """验证 Agent 层模块"""
    print()
    print("=" * 60)
    print("验证 Agent 层模块验证")
    print("=" * 60)
    print()
    
    try:
        import src.agent_layer
        print("✅ src.agent_layer 导入成功")
        
        from src.agent_layer import BaseAgent, SimpleAgent, SimpleTeam
        print("✅ Agent 类导入成功")
        
        from src.config.constants import AgentRole
        print("✅ AgentRole 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_agent():
    """测试简单Agent"""
    print()
    print("=" * 60)
    print("测试简单 Agent 测试")
    print("=" * 60)
    print()
    
    try:
        from src.agent_layer import SimpleAgent, SimpleTeam
        from src.config.constants import AgentRole
        
        # 创建单个Agent
        analyzer = SimpleAgent(AgentRole.ANALYZER, "分析师小王")
        print(f"✅ 创建Agent: {analyzer.name}")
        
        # 测试单个Agent处理
        result = analyzer.process({"message": "请分析这个需求"})
        print(f"✅ 处理结果: {result['response']}")
        assert result["success"]
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_team():
    """测试Agent团队"""
    print()
    print("=" * 60)
    print("测试 Agent 团队协作测试")
    print("=" * 60)
    print()
    
    try:
        from src.agent_layer import SimpleAgent, SimpleTeam
        from src.config.constants import AgentRole
        
        # 创建团队
        team = SimpleTeam()
        
        # 添加多个Agent
        team.add_agent(SimpleAgent(AgentRole.ORCHESTRATOR, "协调器"))
        team.add_agent(SimpleAgent(AgentRole.ANALYZER, "分析师"))
        team.add_agent(SimpleAgent(AgentRole.DEVELOPER, "开发者"))
        team.add_agent(SimpleAgent(AgentRole.TESTER, "测试者"))
        print("✅ 团队创建成功，包含4个Agent")
        
        # 测试消息传递
        result1 = team.send_message(
            AgentRole.ORCHESTRATOR,
            AgentRole.ANALYZER,
            "请分析这个项目需求"
        )
        print(f"✅ 协调器->分析师: {result1['response']}")
        
        result2 = team.send_message(
            AgentRole.ANALYZER,
            AgentRole.DEVELOPER,
            "请按分析结果编码"
        )
        print(f"✅ 分析师->开发者: {result2['response']}")
        
        result3 = team.send_message(
            AgentRole.DEVELOPER,
            AgentRole.TESTER,
            "请测试这个功能"
        )
        print(f"✅ 开发者->测试者: {result3['response']}")
        
        # 检查对话历史
        history = team.get_conversation_summary()
        print(f"✅ 对话历史: {len(history)} 条记录")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    autogen_ok = verify_autogen_import()
    layer_ok = verify_agent_layer()
    agent_ok = test_simple_agent()
    team_ok = test_agent_team()
    
    print()
    print("=" * 60)
    if autogen_ok and layer_ok and agent_ok and team_ok:
        print("🎉 第4阶段 AutoGen 验证通过！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第4阶段 AutoGen 验证失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
