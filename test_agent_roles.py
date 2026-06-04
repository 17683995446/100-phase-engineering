"""
Agent角色体系验证测试
"""

import pytest
from datetime import datetime
from src.agent_layer.agent_roles import (
    AgentStatus,
    AgentCapability,
    CapabilityProfile,
    AgentContext,
    AgentMessage,
    AgentRegistry,
    AgentFactory,
    AgentCollaborationHub,
    OrchestratorAgent,
    AnalyzerAgent,
    ArchitectAgent,
    DeveloperAgent,
    DebuggerAgent,
    ReviewerAgent,
    TestAgent,
    DocumenterAgent,
    ALL_AGENT_ROLES,
    get_collaboration_hub
)
from src.config.constants import AgentRole
from src.agent_layer.base import BaseAgent


class TestAgentStatus:
    """测试Agent状态"""
    
    def test_agent_status_values(self):
        """测试状态枚举值"""
        assert AgentStatus.IDLE is not None
        assert AgentStatus.BUSY is not None
        assert AgentStatus.WAITING is not None
        assert AgentStatus.ERROR is not None
        assert AgentStatus.TERMINATED is not None


class TestAgentCapability:
    """测试Agent能力"""
    
    def test_capability_values(self):
        """测试能力枚举值"""
        assert AgentCapability.REQUIREMENT_ANALYSIS is not None
        assert AgentCapability.ARCHITECTURE_DESIGN is not None
        assert AgentCapability.CODE_GENERATION is not None
        assert AgentCapability.CODE_REVIEW is not None
        assert AgentCapability.BUG_DEBUGGING is not None
        assert AgentCapability.TEST_DESIGN is not None
        assert AgentCapability.TEST_EXECUTION is not None
        assert AgentCapability.DOCUMENTATION is not None
        assert AgentCapability.TASK_ORCHESTRATION is not None
        assert AgentCapability.QUALITY_ASSURANCE is not None


class TestCapabilityProfile:
    """测试能力画像"""
    
    def test_capability_profile_creation(self):
        """测试创建能力画像"""
        profile = CapabilityProfile(
            capability=AgentCapability.CODE_GENERATION,
            level=5,
            confidence=0.95
        )
        
        assert profile.capability == AgentCapability.CODE_GENERATION
        assert profile.level == 5
        assert profile.confidence == 0.95
    
    def test_capability_profile_defaults(self):
        """测试默认能力画像"""
        profile = CapabilityProfile(capability=AgentCapability.CODE_REVIEW)
        
        assert profile.level == 5
        assert profile.confidence == 1.0
        assert profile.examples == []


class TestAgentContext:
    """测试Agent上下文"""
    
    def test_context_creation(self):
        """测试创建上下文"""
        context = AgentContext(
            chain_id="CH-123",
            task_id="task-456",
            span_id="SP-789"
        )
        
        assert context.chain_id == "CH-123"
        assert context.task_id == "task-456"
        assert context.span_id == "SP-789"
    
    def test_context_to_dict(self):
        """测试上下文序列化"""
        context = AgentContext(
            chain_id="CH-123",
            task_id="task-456"
        )
        
        result = context.to_dict()
        
        assert isinstance(result, dict)
        assert result["chain_id"] == "CH-123"
        assert result["task_id"] == "task-456"


class TestAgentMessage:
    """测试Agent消息"""
    
    def test_message_creation(self):
        """测试创建消息"""
        message = AgentMessage(
            message_id="msg-001",
            sender="agent-analyzer",
            receiver="agent-architect",
            content="请设计架构",
            message_type="request",
            timestamp=datetime.now()
        )
        
        assert message.message_id == "msg-001"
        assert message.sender == "agent-analyzer"
        assert message.receiver == "agent-architect"
        assert message.content == "请设计架构"
    
    def test_message_to_dict(self):
        """测试消息序列化"""
        message = AgentMessage(
            message_id="msg-002",
            sender="agent-orchestrator",
            receiver="agent-developer",
            content="开始开发",
            message_type="command",
            timestamp=datetime.now()
        )
        
        result = message.to_dict()
        
        assert isinstance(result, dict)
        assert result["message_id"] == "msg-002"
        assert result["message_type"] == "command"


class TestAgentRegistry:
    """测试Agent注册表"""
    
    def setup_method(self):
        """每个测试前清空注册表"""
        AgentRegistry.clear()
    
    def test_register_agent(self):
        """测试注册Agent"""
        agent = OrchestratorAgent("orchestrator-001")
        AgentRegistry.register(agent, "orchestrator-001")
        
        assert "orchestrator-001" in AgentRegistry._agents
    
    def test_get_by_id(self):
        """测试根据ID获取Agent"""
        agent = OrchestratorAgent("orchestrator-002")
        AgentRegistry.register(agent, "orchestrator-002")
        
        retrieved = AgentRegistry.get_by_id("orchestrator-002")
        assert retrieved is not None
        assert retrieved.name == "orchestrator-002"
    
    def test_get_by_role(self):
        """测试根据角色获取Agent"""
        agent = AnalyzerAgent("analyzer-001")
        AgentRegistry.register(agent, "analyzer-001")
        
        retrieved = AgentRegistry.get_by_role(AgentRole.ANALYZER)
        assert retrieved is not None
        assert retrieved.role == AgentRole.ANALYZER
    
    def test_get_all_agents(self):
        """测试获取所有Agent"""
        agent1 = OrchestratorAgent("orchestrator-003")
        agent2 = AnalyzerAgent("analyzer-002")
        
        AgentRegistry.register(agent1, "orchestrator-003")
        AgentRegistry.register(agent2, "analyzer-002")
        
        all_agents = AgentRegistry.get_all()
        assert len(all_agents) == 2
    
    def test_unregister_agent(self):
        """测试注销Agent"""
        agent = OrchestratorAgent("orchestrator-004")
        AgentRegistry.register(agent, "orchestrator-004")
        
        AgentRegistry.unregister("orchestrator-004")
        
        assert AgentRegistry.get_by_id("orchestrator-004") is None


class TestOrchestratorAgent:
    """测试协调器Agent"""
    
    def test_orchestrator_creation(self):
        """测试创建协调器"""
        agent = OrchestratorAgent("orchestrator-main")
        
        assert agent.role == AgentRole.ORCHESTRATOR
        assert agent.name == "orchestrator-main"
        assert AgentCapability.TASK_ORCHESTRATION in agent.capabilities
    
    def test_orchestrator_process(self):
        """测试协调器处理"""
        agent = OrchestratorAgent("orchestrator-test")
        
        result = agent.process({"task": "test_task"})
        
        assert result["role"] == "orchestrator"
        assert result["action"] == "orchestrate"
    
    def test_plan_workflow(self):
        """测试规划工作流程"""
        agent = OrchestratorAgent("orchestrator-plan")
        
        workflow = agent.plan_workflow({"type": "requirement"})
        
        assert len(workflow) == 5
        assert workflow[0]["role"] == "analyzer"
        assert workflow[-1]["role"] == "tester"


class TestAnalyzerAgent:
    """测试分析师Agent"""
    
    def test_analyzer_creation(self):
        """测试创建分析师"""
        agent = AnalyzerAgent("analyzer-main")
        
        assert agent.role == AgentRole.ANALYZER
        assert AgentCapability.REQUIREMENT_ANALYSIS in agent.capabilities
    
    def test_analyzer_process(self):
        """测试分析师处理"""
        agent = AnalyzerAgent("analyzer-test")
        
        result = agent.process({"requirement": "build a system"})
        
        assert result["role"] == "analyzer"
        assert result["action"] == "analyze"
        assert "analysis" in result


class TestArchitectAgent:
    """测试架构师Agent"""
    
    def test_architect_creation(self):
        """测试创建架构师"""
        agent = ArchitectAgent("architect-main")
        
        assert agent.role == AgentRole.ARCHITECT
        assert AgentCapability.ARCHITECTURE_DESIGN in agent.capabilities
    
    def test_architect_process(self):
        """测试架构师处理"""
        agent = ArchitectAgent("architect-test")
        
        result = agent.process({"analysis": {"type": "requirement"}})
        
        assert result["role"] == "architect"
        assert result["action"] == "design"
        assert "architecture" in result


class TestDeveloperAgent:
    """测试开发者Agent"""
    
    def test_developer_creation(self):
        """测试创建开发者"""
        agent = DeveloperAgent("developer-main")
        
        assert agent.role == AgentRole.DEVELOPER
        assert AgentCapability.CODE_GENERATION in agent.capabilities
    
    def test_developer_process(self):
        """测试开发者处理"""
        agent = DeveloperAgent("developer-test")
        
        result = agent.process({"architecture": {}})
        
        assert result["role"] == "developer"
        assert result["action"] == "implement"


class TestDebuggerAgent:
    """测试调试器Agent"""
    
    def test_debugger_creation(self):
        """测试创建调试器"""
        agent = DebuggerAgent("debugger-main")
        
        assert agent.role == AgentRole.DEBUGGER
        assert AgentCapability.BUG_DEBUGGING in agent.capabilities
    
    def test_debugger_process(self):
        """测试调试器处理"""
        agent = DebuggerAgent("debugger-test")
        
        result = agent.process({"error": {"type": "null_pointer"}})
        
        assert result["role"] == "debugger"
        assert result["action"] == "debug"


class TestReviewerAgent:
    """测试评审Agent"""
    
    def test_reviewer_creation(self):
        """测试创建评审员"""
        agent = ReviewerAgent("reviewer-main")
        
        assert agent.role == AgentRole.REVIEWER
        assert AgentCapability.CODE_REVIEW in agent.capabilities
    
    def test_reviewer_process(self):
        """测试评审员处理"""
        agent = ReviewerAgent("reviewer-test")
        
        result = agent.process({"code": {}})
        
        assert result["role"] == "reviewer"
        assert result["action"] == "review"


class TestTestAgent:
    """测试测试Agent"""
    
    def test_tester_creation(self):
        """测试创建测试员"""
        agent = TestAgent("tester-main")
        
        assert agent.role == AgentRole.TESTER
        assert AgentCapability.TEST_DESIGN in agent.capabilities
        assert AgentCapability.TEST_EXECUTION in agent.capabilities
    
    def test_tester_process(self):
        """测试测试员处理"""
        agent = TestAgent("tester-test")
        
        result = agent.process({"code": {}})
        
        assert result["role"] == "tester"
        assert result["action"] == "test"


class TestDocumenterAgent:
    """测试文档Agent"""
    
    def test_documenter_creation(self):
        """测试创建文档员"""
        agent = DocumenterAgent("documenter-main")
        
        assert agent.role == AgentRole.DOCUMENTER
        assert AgentCapability.DOCUMENTATION in agent.capabilities
    
    def test_documenter_process(self):
        """测试文档员处理"""
        agent = DocumenterAgent("documenter-test")
        
        result = agent.process({"artifact": {}})
        
        assert result["role"] == "documenter"
        assert result["action"] == "document"


class TestAgentFactory:
    """测试Agent工厂"""
    
    def setup_method(self):
        """每个测试前清空注册表"""
        AgentRegistry.clear()
    
    def test_create_agent(self):
        """测试创建Agent"""
        agent = AgentFactory.create_agent(AgentRole.ANALYZER, "factory-analyzer")
        
        assert agent is not None
        assert agent.role == AgentRole.ANALYZER
    
    def test_create_all_roles(self):
        """测试创建所有角色"""
        for role in ALL_AGENT_ROLES:
            agent = AgentFactory.create_agent(role, f"factory-{role}")
            assert agent.role == role


class TestAgentCollaborationHub:
    """测试Agent协作中心"""
    
    def setup_method(self):
        """每个测试前重置协作中心"""
        self.hub = AgentCollaborationHub()
    
    def test_send_message(self):
        """测试发送消息"""
        message = self.hub.send_message(
            sender="agent-a",
            receiver="agent-b",
            content="Hello",
            chain_id="CH-123"
        )
        
        assert message is not None
        assert message.sender == "agent-a"
        assert message.receiver == "agent-b"
    
    def test_broadcast(self):
        """测试广播"""
        receivers = ["agent-b", "agent-c", "agent-d"]
        messages = self.hub.broadcast("agent-a", receivers, "Announcement")
        
        assert len(messages) == 3
    
    def test_get_messages_for_agent(self):
        """测试获取发送给Agent的消息"""
        self.hub.send_message("agent-a", "agent-b", "msg1")
        self.hub.send_message("agent-a", "agent-b", "msg2")
        self.hub.send_message("agent-a", "agent-c", "msg3")
        
        messages = self.hub.get_messages_for("agent-b")
        assert len(messages) == 2
    
    def test_assign_task(self):
        """测试分配任务"""
        self.hub.assign_task("agent-a", "task-001", "CH-123")
        
        agents = self.hub.get_task_agents("task-001")
        assert "agent-a" in agents
    
    def test_complete_task(self):
        """测试完成任务"""
        self.hub.assign_task("agent-a", "task-002", "CH-123")
        self.hub.complete_task("task-002", "agent-a")
        
        agents = self.hub.get_task_agents("task-002")
        assert len(agents) == 0


def test_all_eight_agents_created():
    """测试所有8个Agent角色都能被创建"""
    AgentRegistry.clear()
    
    for role in ALL_AGENT_ROLES:
        agent = AgentFactory.create_agent(role)
        assert agent is not None
        assert agent.role == role


def test_responsibility_orthogonal():
    """测试职责正交性 - 每个Agent有独特能力"""
    AgentRegistry.clear()
    
    capabilities_map = {}
    
    for role in ALL_AGENT_ROLES:
        agent = AgentFactory.create_agent(role)
        caps = agent.capabilities
        
        for cap in caps:
            assert cap not in capabilities_map.get(role, [])
        
        capabilities_map[role] = caps


def test_collaboration_workflow():
    """测试协作工作流程"""
    AgentRegistry.clear()
    hub = get_collaboration_hub()
    
    orchestrator = AgentFactory.create_agent(AgentRole.ORCHESTRATOR, "orchestrator")
    
    workflow = orchestrator.plan_workflow({"type": "requirement"})
    
    for step in workflow:
        role = step["role"]
        action = step["action"]
        
        agent = AgentFactory.create_agent(role, f"agent-for-{role}")
        assert agent is not None
        
        result = agent.process({"requirement": "test"})
        assert result["action"] == action
