"""
Agent工作流编排验证测试
"""

import pytest
from datetime import datetime
from src.agent_layer.workflow import (
    WorkflowStatus,
    StepStatus,
    StepType,
    WorkflowStep,
    StepResult,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowTemplate,
    AgentWorkflowEngine,
    get_workflow_engine
)


class TestWorkflowStatus:
    """测试工作流状态"""
    
    def test_workflow_status_values(self):
        """测试状态枚举值"""
        assert WorkflowStatus.PENDING is not None
        assert WorkflowStatus.RUNNING is not None
        assert WorkflowStatus.PAUSED is not None
        assert WorkflowStatus.COMPLETED is not None
        assert WorkflowStatus.FAILED is not None
        assert WorkflowStatus.CANCELLED is not None


class TestStepStatus:
    """测试步骤状态"""
    
    def test_step_status_values(self):
        """测试步骤状态枚举值"""
        assert StepStatus.PENDING is not None
        assert StepStatus.RUNNING is not None
        assert StepStatus.COMPLETED is not None
        assert StepStatus.SKIPPED is not None
        assert StepStatus.FAILED is not None


class TestStepType:
    """测试步骤类型"""
    
    def test_step_type_values(self):
        """测试步骤类型枚举值"""
        assert StepType.AGENT_TASK is not None
        assert StepType.CONDITIONAL is not None
        assert StepType.PARALLEL is not None
        assert StepType.SEQUENTIAL is not None
        assert StepType.LOOP is not None


class TestWorkflowStep:
    """测试工作流步骤"""
    
    def test_step_creation(self):
        """测试创建步骤"""
        step = WorkflowStep(
            step_id="step_001",
            name="测试步骤",
            step_type=StepType.AGENT_TASK,
            agent_role="analyzer",
            action="analyze"
        )
        
        assert step.step_id == "step_001"
        assert step.name == "测试步骤"
        assert step.agent_role == "analyzer"
    
    def test_step_with_dependencies(self):
        """测试带依赖的步骤"""
        step = WorkflowStep(
            step_id="step_002",
            name="依赖步骤",
            step_type=StepType.AGENT_TASK,
            depends_on=["step_001"]
        )
        
        assert len(step.depends_on) == 1
        assert "step_001" in step.depends_on
    
    def test_step_to_dict(self):
        """测试步骤序列化"""
        step = WorkflowStep(
            step_id="step_003",
            name="序列化测试",
            step_type=StepType.AGENT_TASK
        )
        
        result = step.to_dict()
        
        assert isinstance(result, dict)
        assert result["step_id"] == "step_003"


class TestStepResult:
    """测试步骤结果"""
    
    def test_result_creation(self):
        """测试创建结果"""
        result = StepResult(
            step_id="step_001",
            status=StepStatus.COMPLETED,
            start_time=datetime.now()
        )
        
        assert result.step_id == "step_001"
        assert result.status == StepStatus.COMPLETED
    
    def test_result_to_dict(self):
        """测试结果序列化"""
        result = StepResult(
            step_id="step_002",
            status=StepStatus.FAILED,
            start_time=datetime.now(),
            error="Test error"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["status"] == "FAILED"
        assert result_dict["error"] == "Test error"


class TestWorkflowDefinition:
    """测试工作流定义"""
    
    def test_definition_creation(self):
        """测试创建工作流定义"""
        workflow = WorkflowDefinition(
            workflow_id="wf_001",
            name="测试工作流",
            description="测试描述",
            task_type="requirement"
        )
        
        assert workflow.workflow_id == "wf_001"
        assert workflow.name == "测试工作流"
        assert len(workflow.steps) == 0
    
    def test_add_steps(self):
        """测试添加步骤"""
        workflow = WorkflowDefinition(
            workflow_id="wf_002",
            name="测试工作流",
            description="测试描述",
            task_type="requirement"
        )
        
        step1 = WorkflowStep(
            step_id="step_001",
            name="步骤1",
            step_type=StepType.AGENT_TASK
        )
        
        step2 = WorkflowStep(
            step_id="step_002",
            name="步骤2",
            step_type=StepType.AGENT_TASK,
            depends_on=["step_001"]
        )
        
        workflow.steps = [step1, step2]
        
        assert len(workflow.steps) == 2
    
    def test_get_step(self):
        """测试获取步骤"""
        workflow = WorkflowDefinition(
            workflow_id="wf_003",
            name="测试工作流",
            description="测试描述",
            task_type="requirement"
        )
        
        step = WorkflowStep(
            step_id="find_me",
            name="查找步骤",
            step_type=StepType.AGENT_TASK
        )
        
        workflow.steps = [step]
        
        found = workflow.get_step("find_me")
        assert found is not None
        assert found.step_id == "find_me"
        
        not_found = workflow.get_step("not_exists")
        assert not_found is None


class TestWorkflowExecution:
    """测试工作流执行"""
    
    def test_execution_creation(self):
        """测试创建执行实例"""
        execution = WorkflowExecution(
            execution_id="exec_001",
            workflow_id="wf_001",
            chain_id="CH-001",
            status=WorkflowStatus.PENDING,
            started_at=datetime.now()
        )
        
        assert execution.execution_id == "exec_001"
        assert execution.status == WorkflowStatus.PENDING
        assert len(execution.step_results) == 0
    
    def test_add_step_result(self):
        """测试添加步骤结果"""
        execution = WorkflowExecution(
            execution_id="exec_002",
            workflow_id="wf_001",
            chain_id="CH-001",
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now()
        )
        
        result = StepResult(
            step_id="step_001",
            status=StepStatus.COMPLETED,
            start_time=datetime.now()
        )
        
        execution.add_step_result(result)
        
        assert len(execution.step_results) == 1
        assert execution.is_step_completed("step_001")
    
    def test_is_step_completed(self):
        """测试步骤完成检查"""
        execution = WorkflowExecution(
            execution_id="exec_003",
            workflow_id="wf_001",
            chain_id="CH-001",
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now()
        )
        
        assert not execution.is_step_completed("step_001")
        
        result = StepResult(
            step_id="step_001",
            status=StepStatus.COMPLETED,
            start_time=datetime.now()
        )
        execution.add_step_result(result)
        
        assert execution.is_step_completed("step_001")
    
    def test_get_completed_steps(self):
        """测试获取完成的步骤"""
        execution = WorkflowExecution(
            execution_id="exec_004",
            workflow_id="wf_001",
            chain_id="CH-001",
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now()
        )
        
        execution.add_step_result(StepResult(
            step_id="step_001",
            status=StepStatus.COMPLETED,
            start_time=datetime.now()
        ))
        
        execution.add_step_result(StepResult(
            step_id="step_002",
            status=StepStatus.FAILED,
            start_time=datetime.now()
        ))
        
        execution.add_step_result(StepResult(
            step_id="step_003",
            status=StepStatus.COMPLETED,
            start_time=datetime.now()
        ))
        
        completed = execution.get_completed_steps()
        assert len(completed) == 2
        assert "step_001" in completed
        assert "step_003" in completed


class TestWorkflowTemplate:
    """测试工作流模板"""
    
    def test_requirement_workflow(self):
        """测试需求工作流"""
        workflow = WorkflowTemplate.requirement_workflow()
        
        assert workflow.name == "需求分析工作流"
        assert len(workflow.steps) == 6
        assert workflow.task_type == "requirement"
    
    def test_bugfix_workflow(self):
        """测试Bug修复工作流"""
        workflow = WorkflowTemplate.bugfix_workflow()
        
        assert workflow.name == "Bug修复工作流"
        assert len(workflow.steps) == 5
        assert workflow.task_type == "bugfix"
    
    def test_refactor_workflow(self):
        """测试重构工作流"""
        workflow = WorkflowTemplate.refactor_workflow()
        
        assert workflow.name == "重构工作流"
        assert len(workflow.steps) == 5
        assert workflow.task_type == "refactor"


class TestAgentWorkflowEngine:
    """测试Agent工作流引擎"""
    
    def test_engine_creation(self):
        """测试引擎创建"""
        engine = AgentWorkflowEngine()
        
        assert engine is not None
        assert len(engine.active_executions) == 0
    
    def test_create_execution(self):
        """测试创建执行"""
        engine = AgentWorkflowEngine()
        workflow = WorkflowTemplate.requirement_workflow()
        
        execution = engine.create_execution(workflow, "task_001")
        
        assert execution is not None
        assert execution.workflow_id == workflow.workflow_id
        assert len(engine.active_executions) == 1
    
    def test_can_execute_step(self):
        """测试步骤可执行性检查"""
        engine = AgentWorkflowEngine()
        workflow = WorkflowTemplate.requirement_workflow()
        execution = engine.create_execution(workflow, "task_002")
        
        first_step = workflow.steps[0]
        assert engine.can_execute_step(execution, first_step)
        
        execution.add_step_result(StepResult(
            step_id="step_analyze",
            status=StepStatus.COMPLETED,
            start_time=datetime.now()
        ))
        
        second_step = workflow.steps[1]
        assert second_step.depends_on == ["step_analyze"]
    
    def test_get_next_step(self):
        """测试获取下一步"""
        engine = AgentWorkflowEngine()
        workflow = WorkflowTemplate.requirement_workflow()
        execution = engine.create_execution(workflow, "task_003")
        
        next_step = engine.get_next_step(execution, workflow)
        assert next_step is not None
        assert next_step.step_id == "step_analyze"
        
        execution.add_step_result(StepResult(
            step_id="step_analyze",
            status=StepStatus.COMPLETED,
            start_time=datetime.now()
        ))
        
        next_step = engine.get_next_step(execution, workflow)
        assert next_step is not None
        assert next_step.step_id == "step_design"
    
    def test_execute_workflow(self):
        """测试执行工作流"""
        engine = AgentWorkflowEngine()
        workflow = WorkflowTemplate.bugfix_workflow()
        
        execution = engine.execute_workflow(workflow, "task_bugfix_001")
        
        assert execution is not None
        assert len(execution.step_results) == len(workflow.steps)
    
    def test_get_statistics(self):
        """测试统计信息"""
        engine = AgentWorkflowEngine()
        workflow = WorkflowTemplate.requirement_workflow()
        
        engine.execute_workflow(workflow, "task_stat_001")
        
        stats = engine.get_statistics()
        
        assert "active_executions" in stats
        assert "completed_executions" in stats
        assert "total_executions" in stats


def test_workflow_execution_integration():
    """测试工作流执行集成"""
    engine = AgentWorkflowEngine()
    
    workflow = WorkflowTemplate.requirement_workflow()
    
    execution = engine.execute_workflow(
        workflow,
        "integration_test_001",
        initial_context={"requirement": "测试需求"}
    )
    
    assert execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
    assert execution.workflow_id == workflow.workflow_id
    assert len(execution.step_results) > 0


def test_get_global_workflow_engine():
    """测试获取全局工作流引擎"""
    engine1 = get_workflow_engine()
    engine2 = get_workflow_engine()
    
    assert engine1 is engine2
