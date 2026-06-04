"""
Agent工作流编排系统
职责正交公理：工作流编排与Agent执行解耦
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from src.agent_layer.agent_roles import (
    AgentFactory,
    AgentRole,
)
from src.config.constants import TaskType
from src.scheduling_layer.chain_id import ChainTracker, SpanStatus, SpanType, get_chain_tracker
from src.utils.logger import logger


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class StepStatus(Enum):
    """步骤状态"""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    SKIPPED = auto()
    FAILED = auto()


class StepType(Enum):
    """步骤类型"""
    AGENT_TASK = auto()
    CONDITIONAL = auto()
    PARALLEL = auto()
    SEQUENTIAL = auto()
    LOOP = auto()


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    name: str
    step_type: StepType
    agent_role: str | None = None
    action: str | None = None
    input_mapping: dict[str, str] = field(default_factory=dict)
    output_mapping: dict[str, str] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    condition: str | None = None
    retry_count: int = 0
    timeout_seconds: int = 300

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "step_type": self.step_type.name,
            "agent_role": self.agent_role,
            "action": self.action,
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "depends_on": self.depends_on,
            "condition": self.condition,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds
        }


@dataclass
class StepResult:
    """步骤执行结果"""
    step_id: str
    status: StepStatus
    start_time: datetime
    end_time: datetime | None = None
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    agent_id: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "output": self.output,
            "error": self.error,
            "agent_id": self.agent_id,
            "duration_ms": self.duration_ms
        }


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    workflow_id: str
    name: str
    description: str
    task_type: str
    steps: list[WorkflowStep] = field(default_factory=list)
    entry_step: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> WorkflowStep | None:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_next_steps(self, step_id: str) -> list[WorkflowStep]:
        current_step = self.get_step(step_id)
        if not current_step:
            return []
        return [self.get_step(sid) for sid in current_step.depends_on if self.get_step(sid)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "steps": [s.to_dict() for s in self.steps],
            "entry_step": self.entry_step,
            "metadata": self.metadata
        }


@dataclass
class WorkflowExecution:
    """工作流执行实例"""
    execution_id: str
    workflow_id: str
    chain_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: datetime | None = None
    current_step: str | None = None
    step_results: dict[str, StepResult] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float | None = None

    def add_step_result(self, result: StepResult):
        self.step_results[result.step_id] = result

    def get_step_result(self, step_id: str) -> StepResult | None:
        return self.step_results.get(step_id)

    def is_step_completed(self, step_id: str) -> bool:
        result = self.step_results.get(step_id)
        return result is not None and result.status == StepStatus.COMPLETED

    def get_completed_steps(self) -> list[str]:
        return [sid for sid, result in self.step_results.items() if result.status == StepStatus.COMPLETED]

    def get_failed_steps(self) -> list[str]:
        return [sid for sid, result in self.step_results.items() if result.status == StepStatus.FAILED]

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "chain_id": self.chain_id,
            "status": self.status.name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_step": self.current_step,
            "step_results": {k: v.to_dict() for k, v in self.step_results.items()},
            "context": self.context,
            "error": self.error,
            "duration_ms": self.duration_ms
        }


class WorkflowTemplate:
    """工作流模板"""

    @staticmethod
    def requirement_workflow() -> WorkflowDefinition:
        """需求分析工作流"""
        workflow_id = f"wf-requirement-{uuid.uuid4().hex[:8]}"

        steps = [
            WorkflowStep(
                step_id="step_analyze",
                name="需求分析",
                step_type=StepType.AGENT_TASK,
                agent_role="analyzer",
                action="analyze",
                depends_on=[]
            ),
            WorkflowStep(
                step_id="step_design",
                name="架构设计",
                step_type=StepType.AGENT_TASK,
                agent_role="architect",
                action="design",
                depends_on=["step_analyze"]
            ),
            WorkflowStep(
                step_id="step_implement",
                name="代码实现",
                step_type=StepType.AGENT_TASK,
                agent_role="developer",
                action="implement",
                depends_on=["step_design"]
            ),
            WorkflowStep(
                step_id="step_review",
                name="代码评审",
                step_type=StepType.AGENT_TASK,
                agent_role="reviewer",
                action="review",
                depends_on=["step_implement"]
            ),
            WorkflowStep(
                step_id="step_test",
                name="测试执行",
                step_type=StepType.AGENT_TASK,
                agent_role="tester",
                action="test",
                depends_on=["step_review"]
            ),
            WorkflowStep(
                step_id="step_document",
                name="文档生成",
                step_type=StepType.AGENT_TASK,
                agent_role="documenter",
                action="document",
                depends_on=["step_test"]
            )
        ]

        return WorkflowDefinition(
            workflow_id=workflow_id,
            name="需求分析工作流",
            description="完整的需求分析到文档生成流程",
            task_type=TaskType.REQUIREMENT,
            steps=steps,
            entry_step="step_analyze"
        )

    @staticmethod
    def bugfix_workflow() -> WorkflowDefinition:
        """Bug修复工作流"""
        workflow_id = f"wf-bugfix-{uuid.uuid4().hex[:8]}"

        steps = [
            WorkflowStep(
                step_id="step_analyze",
                name="问题分析",
                step_type=StepType.AGENT_TASK,
                agent_role="analyzer",
                action="analyze",
                depends_on=[]
            ),
            WorkflowStep(
                step_id="step_debug",
                name="调试定位",
                step_type=StepType.AGENT_TASK,
                agent_role="debugger",
                action="debug",
                depends_on=["step_analyze"]
            ),
            WorkflowStep(
                step_id="step_fix",
                name="代码修复",
                step_type=StepType.AGENT_TASK,
                agent_role="developer",
                action="implement",
                depends_on=["step_debug"]
            ),
            WorkflowStep(
                step_id="step_review",
                name="代码评审",
                step_type=StepType.AGENT_TASK,
                agent_role="reviewer",
                action="review",
                depends_on=["step_fix"]
            ),
            WorkflowStep(
                step_id="step_test",
                name="测试验证",
                step_type=StepType.AGENT_TASK,
                agent_role="tester",
                action="test",
                depends_on=["step_review"]
            )
        ]

        return WorkflowDefinition(
            workflow_id=workflow_id,
            name="Bug修复工作流",
            description="从问题分析到测试验证的完整修复流程",
            task_type=TaskType.BUGFIX,
            steps=steps,
            entry_step="step_analyze"
        )

    @staticmethod
    def refactor_workflow() -> WorkflowDefinition:
        """重构工作流"""
        workflow_id = f"wf-refactor-{uuid.uuid4().hex[:8]}"

        steps = [
            WorkflowStep(
                step_id="step_analyze",
                name="现状分析",
                step_type=StepType.AGENT_TASK,
                agent_role="analyzer",
                action="analyze",
                depends_on=[]
            ),
            WorkflowStep(
                step_id="step_design",
                name="重构设计",
                step_type=StepType.AGENT_TASK,
                agent_role="architect",
                action="design",
                depends_on=["step_analyze"]
            ),
            WorkflowStep(
                step_id="step_refactor",
                name="执行重构",
                step_type=StepType.AGENT_TASK,
                agent_role="developer",
                action="implement",
                depends_on=["step_design"]
            ),
            WorkflowStep(
                step_id="step_review",
                name="评审验证",
                step_type=StepType.AGENT_TASK,
                agent_role="reviewer",
                action="review",
                depends_on=["step_refactor"]
            ),
            WorkflowStep(
                step_id="step_test",
                name="测试验证",
                step_type=StepType.AGENT_TASK,
                agent_role="tester",
                action="test",
                depends_on=["step_review"]
            )
        ]

        return WorkflowDefinition(
            workflow_id=workflow_id,
            name="重构工作流",
            description="代码重构的完整流程",
            task_type=TaskType.REFACTOR,
            steps=steps,
            entry_step="step_analyze"
        )


class AgentWorkflowEngine:
    """Agent工作流执行引擎"""

    def __init__(self, chain_tracker: ChainTracker | None = None):
        self.chain_tracker = chain_tracker or get_chain_tracker()
        self.active_executions: dict[str, WorkflowExecution] = {}
        self.completed_executions: dict[str, WorkflowExecution] = {}
        logger.info("Agent工作流引擎初始化")

    def create_execution(
        self,
        workflow: WorkflowDefinition,
        task_id: str,
        initial_context: dict[str, Any] | None = None
    ) -> WorkflowExecution:
        """创建工作流执行实例"""
        chain = self.chain_tracker.create_chain(
            task_id=task_id,
            task_type=workflow.task_type,
            metadata={"workflow_id": workflow.workflow_id}
        )

        execution = WorkflowExecution(
            execution_id=f"exec-{uuid.uuid4().hex[:12]}",
            workflow_id=workflow.workflow_id,
            chain_id=chain.chain_id,
            status=WorkflowStatus.PENDING,
            started_at=datetime.now(),
            context=initial_context or {}
        )

        self.active_executions[execution.execution_id] = execution

        logger.info(f"创建工作流执行: {execution.execution_id} (workflow={workflow.name})")

        return execution

    def execute_step(
        self,
        execution: WorkflowExecution,
        workflow: WorkflowDefinition,
        step: WorkflowStep
    ) -> StepResult:
        """执行单个步骤"""
        result = StepResult(
            step_id=step.step_id,
            status=StepStatus.RUNNING,
            start_time=datetime.now()
        )

        span = self.chain_tracker.start_span(
            chain_id=execution.chain_id,
            span_type=SpanType.AGENT,
            operation_name=f"{step.name} ({step.agent_role})",
            layer="agent_layer",
            agent_id=step.agent_role
        )

        try:
            if step.step_type == StepType.AGENT_TASK:
                result.output = self._execute_agent_task(step, execution.context)
            else:
                result.output = {"message": f"Step type {step.step_type} not implemented"}

            result.status = StepStatus.COMPLETED
            result.agent_id = step.agent_role

            if span:
                self.chain_tracker.end_span(span.span_id, SpanStatus.COMPLETED)

            logger.info(f"步骤完成: {step.name} ({step.step_id})")

        except Exception as e:
            result.status = StepStatus.FAILED
            result.error = str(e)

            if span:
                self.chain_tracker.end_span(span.span_id, SpanStatus.FAILED, error=str(e))

            logger.error(f"步骤失败: {step.name} ({step.step_id}): {e}")

        result.end_time = datetime.now()
        if result.start_time and result.end_time:
            result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000

        execution.add_step_result(result)

        return result

    def _execute_agent_task(self, step: WorkflowStep, context: dict[str, Any]) -> dict[str, Any]:
        """执行Agent任务"""
        if not step.agent_role:
            return {"error": "No agent role specified"}

        try:
            role = step.agent_role
            if hasattr(AgentRole, role.upper()):
                role = getattr(AgentRole, role.upper())
            else:
                role = step.agent_role

            agent = AgentFactory.create_agent(role, f"{step.agent_role}-{uuid.uuid4().hex[:6]}")

            input_data = {}
            for key, value in step.input_mapping.items():
                if value in context:
                    input_data[key] = context[value]
                else:
                    input_data[key] = value

            result = agent.process(input_data)

            for key, value in step.output_mapping.items():
                if key in result:
                    context[value] = result[key]

            return result

        except Exception as e:
            logger.error(f"Agent任务执行失败: {e}")
            return {"error": str(e)}

    def can_execute_step(self, execution: WorkflowExecution, step: WorkflowStep) -> bool:
        """检查步骤是否可以执行"""
        if not step.depends_on:
            return True

        for dep_id in step.depends_on:
            if not execution.is_step_completed(dep_id):
                return False

        return True

    def get_next_step(self, execution: WorkflowExecution, workflow: WorkflowDefinition) -> WorkflowStep | None:
        """获取下一个可执行的步骤"""
        for step in workflow.steps:
            if step.step_id in execution.step_results:
                continue

            if self.can_execute_step(execution, step):
                return step

        return None

    def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        task_id: str,
        initial_context: dict[str, Any] | None = None
    ) -> WorkflowExecution:
        """执行完整工作流"""
        execution = self.create_execution(workflow, task_id, initial_context)
        execution.status = WorkflowStatus.RUNNING

        logger.info(f"开始执行工作流: {workflow.name} ({execution.execution_id})")

        while True:
            next_step = self.get_next_step(execution, workflow)

            if not next_step:
                break

            execution.current_step = next_step.step_id

            result = self.execute_step(execution, workflow, next_step)

            if result.status == StepStatus.FAILED:
                failed_steps = execution.get_failed_steps()
                logger.warning(f"工作流中有失败步骤: {failed_steps}")

            if execution.status == WorkflowStatus.FAILED:
                break

        all_completed = all(
            execution.is_step_completed(step.step_id)
            for step in workflow.steps
        )

        if all_completed:
            execution.status = WorkflowStatus.COMPLETED
            logger.info(f"工作流完成: {workflow.name} ({execution.execution_id})")
        else:
            failed = execution.get_failed_steps()
            if failed:
                execution.status = WorkflowStatus.FAILED
                execution.error = f"Failed steps: {failed}"
            else:
                execution.status = WorkflowStatus.PAUSED

        execution.completed_at = datetime.now()
        if execution.started_at and execution.completed_at:
            execution.duration_ms = (execution.completed_at - execution.started_at).total_seconds() * 1000

        final_status = SpanStatus.COMPLETED if all_completed else SpanStatus.FAILED
        self.chain_tracker.complete_chain(execution.chain_id, final_status)

        del self.active_executions[execution.execution_id]
        self.completed_executions[execution.execution_id] = execution

        return execution

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """获取执行实例"""
        if execution_id in self.active_executions:
            return self.active_executions[execution_id]
        return self.completed_executions.get(execution_id)

    def get_active_executions(self) -> list[WorkflowExecution]:
        """获取活跃执行"""
        return list(self.active_executions.values())

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "active_executions": len(self.active_executions),
            "completed_executions": len(self.completed_executions),
            "total_executions": len(self.active_executions) + len(self.completed_executions)
        }


_global_workflow_engine: AgentWorkflowEngine | None = None


def get_workflow_engine() -> AgentWorkflowEngine:
    """获取全局工作流引擎"""
    global _global_workflow_engine
    if _global_workflow_engine is None:
        _global_workflow_engine = AgentWorkflowEngine()
    return _global_workflow_engine
