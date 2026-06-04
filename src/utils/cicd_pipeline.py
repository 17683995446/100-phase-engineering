"""
CI/CD 流水线管理器
提供流水线定义、阶段执行、任务编排、状态追踪和日志收集功能
"""
import time
import threading
import uuid
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from src.utils.structured_logging import get_logger


class PipelineStatus(Enum):
    """流水线状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class StageStatus(Enum):
    """阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class PipelineStage:
    """流水线阶段"""
    stage_id: str
    name: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    status: StageStatus = StageStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    logs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    allow_failure: bool = False

    @property
    def duration(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "status": self.status.value,
            "duration": round(self.duration, 3),
            "steps": len(self.steps),
            "depends_on": self.depends_on,
            "allow_failure": self.allow_failure
        }


@dataclass
class PipelineRun:
    """流水线运行实例"""
    run_id: str
    pipeline_id: str
    trigger: str
    status: PipelineStatus = PipelineStatus.PENDING
    stages: Dict[str, PipelineStage] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "pipeline_id": self.pipeline_id,
            "trigger": self.trigger,
            "status": self.status.value,
            "duration": round(self.duration, 3),
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "variables": self.variables,
            "artifacts": self.artifacts
        }


@dataclass
class PipelineDefinition:
    """流水线定义"""
    pipeline_id: str
    name: str
    stages: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    triggers: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "stages": self.stages,
            "variables": self.variables,
            "triggers": self.triggers,
            "created_at": self.created_at
        }


class CICDPipelineManager:
    """CI/CD 流水线管理器"""

    def __init__(self):
        self._pipelines: Dict[str, PipelineDefinition] = {}
        self._runs: Dict[str, PipelineRun] = {}
        self._history: deque = deque(maxlen=1000)
        self._lock = threading.RLock()
        self._logger = get_logger("cicd.pipeline")
        self._step_handlers: Dict[str, Callable] = {}

    def register_step_handler(self, step_type: str,
                              handler: Callable[[PipelineStage, Dict[str, Any]], bool]) -> None:
        """注册步骤处理器"""
        with self._lock:
            self._step_handlers[step_type] = handler

    def create_pipeline(self, pipeline_id: str, name: str,
                        stages: Optional[List[Dict[str, Any]]] = None,
                        variables: Optional[Dict[str, Any]] = None,
                        triggers: Optional[List[str]] = None) -> PipelineDefinition:
        """创建流水线定义"""
        with self._lock:
            if pipeline_id in self._pipelines:
                raise ValueError(f"Pipeline already exists: {pipeline_id}")

            pipeline = PipelineDefinition(
                pipeline_id=pipeline_id,
                name=name,
                stages=stages or [],
                variables=variables or {},
                triggers=triggers or []
            )
            self._pipelines[pipeline_id] = pipeline
            self._logger.info(f"Pipeline created: {pipeline_id}")
            return pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineDefinition]:
        """获取流水线定义"""
        with self._lock:
            return self._pipelines.get(pipeline_id)

    def list_pipelines(self) -> List[Dict[str, Any]]:
        """列出所有流水线"""
        with self._lock:
            return [p.to_dict() for p in self._pipelines.values()]

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """删除流水线定义"""
        with self._lock:
            if pipeline_id in self._pipelines:
                del self._pipelines[pipeline_id]
                self._logger.info(f"Pipeline deleted: {pipeline_id}")
                return True
            return False

    def trigger_pipeline(self, pipeline_id: str,
                         trigger: str = "manual",
                         variables: Optional[Dict[str, Any]] = None) -> PipelineRun:
        """触发流水线运行"""
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            run_id = f"run_{uuid.uuid4().hex[:8]}"
            run = PipelineRun(
                run_id=run_id,
                pipeline_id=pipeline_id,
                trigger=trigger,
                variables={**pipeline.variables, **(variables or {})}
            )

            # 初始化阶段
            for stage_def in pipeline.stages:
                stage = PipelineStage(
                    stage_id=stage_def.get("stage_id", str(uuid.uuid4().hex[:6])),
                    name=stage_def.get("name", "unnamed"),
                    steps=stage_def.get("steps", []),
                    depends_on=stage_def.get("depends_on", []),
                    allow_failure=stage_def.get("allow_failure", False)
                )
                run.stages[stage.stage_id] = stage

            self._runs[run_id] = run
            self._logger.info(f"Pipeline triggered: {pipeline_id} run={run_id}")
            return run

    def run_pipeline(self, run_id: str) -> PipelineRun:
        """执行流水线"""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise ValueError(f"Run not found: {run_id}")

        run.status = PipelineStatus.RUNNING
        run.start_time = time.time()
        self._logger.info(f"Pipeline running: {run_id}")

        try:
            # 按依赖顺序执行阶段（在try外解析，让循环依赖错误直接抛出）
            stages_order = self._resolve_dependencies(run.stages)
            executed: Set[str] = set()

            for stage_id in stages_order:
                stage = run.stages[stage_id]
                if not self._can_run_stage(stage, executed):
                    stage.status = StageStatus.SKIPPED
                    continue

                self._execute_stage(run, stage)

                if stage.status == StageStatus.FAILED and not stage.allow_failure:
                    run.status = PipelineStatus.FAILED
                    break

                executed.add(stage_id)
            else:
                run.status = PipelineStatus.SUCCESS

            # 将因依赖失败而未执行的阶段标记为SKIPPED
            for stage_id in stages_order:
                stage = run.stages[stage_id]
                if stage.status == StageStatus.PENDING and not self._can_run_stage(stage, executed):
                    stage.status = StageStatus.SKIPPED

        except Exception as e:
            run.status = PipelineStatus.FAILED
            self._logger.error(f"Pipeline error: {run_id} - {e}")
            raise

        run.end_time = time.time()
        self._history.append({
            "run_id": run.run_id,
            "pipeline_id": run.pipeline_id,
            "status": run.status.value,
            "duration": run.duration,
            "timestamp": time.time()
        })
        self._logger.info(f"Pipeline completed: {run_id} status={run.status.value}")
        return run

    def _resolve_dependencies(self, stages: Dict[str, PipelineStage]) -> List[str]:
        """解析阶段依赖顺序"""
        result: List[str] = []
        visited: Set[str] = set()
        temp: Set[str] = set()

        def visit(stage_id: str) -> None:
            if stage_id in temp:
                raise ValueError(f"Circular dependency detected: {stage_id}")
            if stage_id in visited:
                return
            temp.add(stage_id)
            stage = stages.get(stage_id)
            if stage:
                for dep in stage.depends_on:
                    if dep in stages:
                        visit(dep)
            temp.remove(stage_id)
            visited.add(stage_id)
            result.append(stage_id)

        for sid in stages:
            if sid not in visited:
                visit(sid)

        return result

    def _can_run_stage(self, stage: PipelineStage, executed: Set[str]) -> bool:
        """检查阶段是否可以运行"""
        return all(dep in executed for dep in stage.depends_on)

    def _execute_stage(self, run: PipelineRun, stage: PipelineStage) -> None:
        """执行阶段"""
        stage.status = StageStatus.RUNNING
        stage.start_time = time.time()
        self._logger.info(f"Stage running: {stage.name}")

        try:
            stage_failed = False
            for step in stage.steps:
                step_type = step.get("type", "shell")
                handler = self._step_handlers.get(step_type)
                if handler:
                    success = handler(stage, step)
                    if not success:
                        stage_failed = True
                        if not stage.allow_failure:
                            stage.status = StageStatus.FAILED
                            break
                else:
                    # 默认 shell 步骤模拟
                    stage.logs.append(f"Executing: {step.get('command', 'noop')}")
                    time.sleep(0.001)
            else:
                if stage_failed:
                    stage.status = StageStatus.FAILED
                else:
                    stage.status = StageStatus.SUCCESS
        except Exception as e:
            stage.status = StageStatus.FAILED
            stage.logs.append(str(e))
            self._logger.error(f"Stage error: {stage.name} - {e}")

        stage.end_time = time.time()

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        """获取运行实例"""
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self, pipeline_id: Optional[str] = None,
                  status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出运行实例"""
        with self._lock:
            runs = self._runs.values()
            if pipeline_id:
                runs = [r for r in runs if r.pipeline_id == pipeline_id]
            if status:
                runs = [r for r in runs if r.status.value == status]
            return [r.to_dict() for r in runs]

    def cancel_run(self, run_id: str) -> bool:
        """取消运行"""
        with self._lock:
            run = self._runs.get(run_id)
            if not run or run.status != PipelineStatus.RUNNING:
                return False
            run.status = PipelineStatus.CANCELLED
            for stage in run.stages.values():
                if stage.status == StageStatus.RUNNING:
                    stage.status = StageStatus.CANCELLED
            self._logger.info(f"Pipeline cancelled: {run_id}")
            return True

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取历史记录"""
        with self._lock:
            return list(self._history)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._runs)
            success = sum(1 for r in self._runs.values()
                          if r.status == PipelineStatus.SUCCESS)
            failed = sum(1 for r in self._runs.values()
                         if r.status == PipelineStatus.FAILED)
            return {
                "total_pipelines": len(self._pipelines),
                "total_runs": total,
                "success_count": success,
                "failed_count": failed,
                "success_rate": round(success / total * 100, 2) if total else 0.0
            }


# 全局实例
_manager: Optional[CICDPipelineManager] = None


def get_cicd_pipeline_manager() -> CICDPipelineManager:
    """获取全局CI/CD流水线管理器"""
    global _manager
    if _manager is None:
        _manager = CICDPipelineManager()
    return _manager
