"""
Agent角色体系
职责正交公理：Agent职责无重叠、无空缺，分工互补无冲突
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from src.agent_layer.base import BaseAgent
from src.config.constants import AgentRole
from src.utils.logger import logger

ALL_AGENT_ROLES = [
    AgentRole.ORCHESTRATOR,
    AgentRole.ANALYZER,
    AgentRole.ARCHITECT,
    AgentRole.DEVELOPER,
    AgentRole.DEBUGGER,
    AgentRole.REVIEWER,
    AgentRole.TESTER,
    AgentRole.DOCUMENTER
]


class AgentStatus(Enum):
    """Agent状态"""
    IDLE = auto()
    BUSY = auto()
    WAITING = auto()
    ERROR = auto()
    TERMINATED = auto()


class AgentCapability(Enum):
    """Agent能力枚举"""
    REQUIREMENT_ANALYSIS = auto()
    ARCHITECTURE_DESIGN = auto()
    CODE_GENERATION = auto()
    CODE_REVIEW = auto()
    BUG_DEBUGGING = auto()
    TEST_DESIGN = auto()
    TEST_EXECUTION = auto()
    DOCUMENTATION = auto()
    TASK_ORCHESTRATION = auto()
    QUALITY_ASSURANCE = auto()


@dataclass
class CapabilityProfile:
    """能力画像"""
    capability: AgentCapability
    level: int = 5
    confidence: float = 1.0
    examples: list[str] = field(default_factory=list)


@dataclass
class AgentContext:
    """Agent执行上下文"""
    chain_id: str
    task_id: str
    span_id: str | None = None
    parent_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "task_id": self.task_id,
            "span_id": self.span_id,
            "parent_agent": self.parent_agent,
            "metadata": self.metadata
        }


@dataclass
class AgentMessage:
    """Agent间消息"""
    message_id: str
    sender: str
    receiver: str
    content: str
    message_type: str
    timestamp: datetime
    chain_id: str | None = None
    task_id: str | None = None
    reply_to: str | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "chain_id": self.chain_id,
            "task_id": self.task_id,
            "reply_to": self.reply_to,
            "attachments": self.attachments,
            "metadata": self.metadata
        }


class AgentRegistry:
    """Agent注册表"""
    _agents: dict[str, BaseAgent] = {}
    _roles: dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, agent: BaseAgent, agent_id: str):
        """注册Agent"""
        cls._agents[agent_id] = agent
        cls._roles[agent.role] = agent
        logger.debug(f"注册Agent: {agent_id} ({agent.role})")

    @classmethod
    def unregister(cls, agent_id: str):
        """注销Agent"""
        if agent_id in cls._agents:
            agent = cls._agents[agent_id]
            cls._roles.pop(agent.role, None)
            del cls._agents[agent_id]

    @classmethod
    def get_by_id(cls, agent_id: str) -> BaseAgent | None:
        """根据ID获取Agent"""
        return cls._agents.get(agent_id)

    @classmethod
    def get_by_role(cls, role: str) -> BaseAgent | None:
        """根据角色获取Agent"""
        return cls._roles.get(role)

    @classmethod
    def get_all(cls) -> list[BaseAgent]:
        """获取所有Agent"""
        return list(cls._agents.values())

    @classmethod
    def clear(cls):
        """清空注册表"""
        cls._agents.clear()
        cls._roles.clear()


class OrchestratorAgent(BaseAgent):
    """协调器Agent - 总指挥，负责全局调度"""

    def __init__(self, name: str | None = None):
        super().__init__(AgentRole.ORCHESTRATOR, name)
        self.capabilities = [
            AgentCapability.TASK_ORCHESTRATION,
            AgentCapability.QUALITY_ASSURANCE
        ]
        self.active_workflows: list[str] = []

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        context = input_data.get("context")
        logger.info(f"协调器 {self.name} 处理任务")

        return {
            "agent": self.name,
            "role": self.role,
            "action": "orchestrate",
            "result": "任务协调完成",
            "context": context.to_dict() if context else None
        }

    def plan_workflow(self, task_data: dict[str, Any]) -> list[dict[str, Any]]:
        """规划工作流程"""
        return [
            {"role": "analyzer", "action": "analyze", "order": 1},
            {"role": "architect", "action": "design", "order": 2},
            {"role": "developer", "action": "implement", "order": 3},
            {"role": "reviewer", "action": "review", "order": 4},
            {"role": "tester", "action": "test", "order": 5},
        ]

    def coordinate(self, agents: list[BaseAgent], task: dict[str, Any]) -> dict[str, Any]:
        """协调多Agent协作"""
        results = []
        for agent in agents:
            result = agent.process({"task": task})
            results.append(result)

        return {
            "orchestrated": True,
            "results": results
        }


class AnalyzerAgent(BaseAgent):
    """分析师Agent - 需求分析、问题诊断"""

    def __init__(self, name: str | None = None):
        super().__init__(AgentRole.ANALYZER, name)
        self.capabilities = [AgentCapability.REQUIREMENT_ANALYSIS]

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"分析师 {self.name} 分析需求")

        requirement = input_data.get("requirement", "")

        return {
            "agent": self.name,
            "role": self.role,
            "action": "analyze",
            "analysis": {
                "type": "requirement_analysis",
                "components": self._decompose(requirement),
                "complexity": "medium"
            }
        }

    def _decompose(self, requirement: str) -> list[str]:
        """分解需求为组件"""
        return ["component_a", "component_b", "component_c"]


class ArchitectAgent(BaseAgent):
    """架构师Agent - 系统设计、技术选型"""

    def __init__(self, name: str | None = None):
        super().__init__(AgentRole.ARCHITECT, name)
        self.capabilities = [
            AgentCapability.ARCHITECTURE_DESIGN,
            AgentCapability.CODE_GENERATION
        ]

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"架构师 {self.name} 设计架构")

        input_data.get("analysis", {})

        return {
            "agent": self.name,
            "role": self.role,
            "action": "design",
            "architecture": {
                "layers": ["input", "scheduling", "agent", "execution"],
                "patterns": ["dAG", "Observer"],
                "technology_stack": ["Python", "LangGraph"]
            }
        }

    def design_for_requirement(self, requirement: str) -> dict[str, Any]:
        """为需求设计架构"""
        return {
            "components": [],
            "interfaces": [],
            "data_flow": ""
        }


class DeveloperAgent(BaseAgent):
    """开发者Agent - 代码实现、重构"""

    def __init__(self, name: str | None = None):
        super().__init__(AgentRole.DEVELOPER, name)
        self.capabilities = [AgentCapability.CODE_GENERATION]

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"开发者 {self.name} 编写代码")

        input_data.get("architecture", {})

        return {
            "agent": self.name,
            "role": self.role,
            "action": "implement",
            "code": {
                "files_created": ["src/module.py"],
                "lines_of_code": 150
            }
        }

    def implement_component(self, component_spec: dict[str, Any]) -> dict[str, Any]:
        """实现组件"""
        return {"code": "", "tests": ""}


class DebuggerAgent(BaseAgent):
    """调试器Agent - 错误定位、性能分析"""

    def __init__(self, name: str | None = None):
        super().__init__(AgentRole.DEBUGGER, name)
        self.capabilities = [AgentCapability.BUG_DEBUGGING]

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"调试器 {self.name} 定位问题")

        input_data.get("error", {})

        return {
            "agent": self.name,
            "role": self.role,
            "action": "debug",
            "diagnosis": {
                "root_cause": "null_pointer",
                "location": "line 42",
                "fix_suggestion": "add null check"
            }
        }

    def diagnose(self, error_data: dict[str, Any]) -> dict[str, Any]:
        """诊断错误"""
        return {"cause": "", "location": "", "fix": ""}


class ReviewerAgent(BaseAgent):
    """评审Agent - 代码评审、质量把控"""

    def __init__(self, name: str | None = None):
        super().__init__(AgentRole.REVIEWER, name)
        self.capabilities = [
            AgentCapability.CODE_REVIEW,
            AgentCapability.QUALITY_ASSURANCE
        ]

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"评审员 {self.name} 评审代码")

        input_data.get("code", {})

        return {
            "agent": self.name,
            "role": self.role,
            "action": "review",
            "review": {
                "issues_found": 0,
                "quality_score": 9.5,
                "approval": True
            }
        }

    def review_code(self, code_data: dict[str, Any]) -> dict[str, Any]:
        """评审代码"""
        return {"approved": True, "issues": []}


class TestAgent(BaseAgent):
    """测试Agent - 测试用例设计、执行"""

    def __init__(self, name: str | None = None):
        super().__init__(AgentRole.TESTER, name)
        self.capabilities = [
            AgentCapability.TEST_DESIGN,
            AgentCapability.TEST_EXECUTION
        ]

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"测试员 {self.name} 执行测试")

        input_data.get("code", {})

        return {
            "agent": self.name,
            "role": self.role,
            "action": "test",
            "test_result": {
                "tests_passed": 10,
                "tests_failed": 0,
                "coverage": 85.0
            }
        }

    def design_tests(self, code_data: dict[str, Any]) -> list[dict[str, Any]]:
        """设计测试用例"""
        return []

    def run_tests(self, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        """运行测试"""
        return {"passed": 0, "failed": 0}


class DocumenterAgent(BaseAgent):
    """文档Agent - 文档生成、维护"""

    def __init__(self, name: str | None = None):
        super().__init__(AgentRole.DOCUMENTER, name)
        self.capabilities = [AgentCapability.DOCUMENTATION]

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"文档员 {self.name} 生成文档")

        input_data.get("artifact", {})

        return {
            "agent": self.name,
            "role": self.role,
            "action": "document",
            "documentation": {
                "files_created": ["README.md"],
                "sections": ["overview", "usage", "api"]
            }
        }

    def generate_docs(self, artifact_data: dict[str, Any]) -> dict[str, Any]:
        """生成文档"""
        return {"content": "", "format": "markdown"}


class AgentFactory:
    """Agent工厂"""

    _role_classes: dict[str, type] = {
        AgentRole.ORCHESTRATOR: OrchestratorAgent,
        AgentRole.ANALYZER: AnalyzerAgent,
        AgentRole.ARCHITECT: ArchitectAgent,
        AgentRole.DEVELOPER: DeveloperAgent,
        AgentRole.DEBUGGER: DebuggerAgent,
        AgentRole.REVIEWER: ReviewerAgent,
        AgentRole.TESTER: TestAgent,
        AgentRole.DOCUMENTER: DocumenterAgent,
    }

    @classmethod
    def create_agent(cls, role: str, name: str | None = None) -> BaseAgent:
        """创建Agent"""
        agent_class = cls._role_classes.get(role)
        if not agent_class:
            raise ValueError(f"未知Agent角色: {role}")

        agent_id = f"agent-{role}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        agent = agent_class(name)

        AgentRegistry.register(agent, agent_id)

        return agent

    @classmethod
    def create_team(cls) -> dict[str, BaseAgent]:
        """创建完整Agent团队"""
        team = {}
        for role in ALL_AGENT_ROLES:
            agent = cls.create_agent(role)
            team[role] = agent
        return team

    @classmethod
    def register_role_class(cls, role: str, agent_class: type):
        """注册角色类"""
        cls._role_classes[role] = agent_class


class AgentCollaborationHub:
    """Agent协作中心"""

    def __init__(self):
        self.message_queue: list[AgentMessage] = []
        self.active_tasks: dict[str, list[str]] = {}
        logger.info("初始化Agent协作中心")

    def send_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        message_type: str = "request",
        chain_id: str | None = None,
        task_id: str | None = None
    ) -> AgentMessage:
        """发送消息"""
        import uuid

        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
            timestamp=datetime.now(),
            chain_id=chain_id,
            task_id=task_id
        )

        self.message_queue.append(message)
        logger.debug(f"消息发送: {sender} -> {receiver}")

        return message

    def broadcast(
        self,
        sender: str,
        receivers: list[str],
        content: str,
        message_type: str = "broadcast"
    ) -> list[AgentMessage]:
        """广播消息"""
        messages = []
        for receiver in receivers:
            msg = self.send_message(sender, receiver, content, message_type)
            messages.append(msg)
        return messages

    def get_messages_for(self, agent_id: str) -> list[AgentMessage]:
        """获取发送给特定Agent的消息"""
        return [m for m in self.message_queue if m.receiver == agent_id]

    def get_messages_from(self, agent_id: str) -> list[AgentMessage]:
        """获取来自特定Agent的消息"""
        return [m for m in self.message_queue if m.sender == agent_id]

    def acknowledge_message(self, message_id: str):
        """确认消息"""
        for msg in self.message_queue:
            if msg.message_id == message_id:
                msg.metadata["acknowledged"] = True
                break

    def assign_task(self, agent_id: str, task_id: str, chain_id: str):
        """分配任务"""
        if task_id not in self.active_tasks:
            self.active_tasks[task_id] = []
        self.active_tasks[task_id].append(agent_id)

        logger.info(f"任务分配: {task_id} -> {agent_id}")

    def complete_task(self, task_id: str, agent_id: str):
        """完成任务"""
        if task_id in self.active_tasks:
            if agent_id in self.active_tasks[task_id]:
                self.active_tasks[task_id].remove(agent_id)

            if not self.active_tasks[task_id]:
                del self.active_tasks[task_id]
                logger.info(f"任务完成: {task_id}")

    def get_task_agents(self, task_id: str) -> list[str]:
        """获取任务相关的Agent"""
        return self.active_tasks.get(task_id, [])


_global_collaboration_hub: AgentCollaborationHub | None = None


def get_collaboration_hub() -> AgentCollaborationHub:
    """获取全局协作中心"""
    global _global_collaboration_hub
    if _global_collaboration_hub is None:
        _global_collaboration_hub = AgentCollaborationHub()
    return _global_collaboration_hub
