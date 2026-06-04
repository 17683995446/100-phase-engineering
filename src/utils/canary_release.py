"""
灰度发布系统
提供流量分配、版本切换、回滚和渐进式发布功能
"""
import time
import threading
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class ReleaseStrategy(Enum):
    """发布策略"""
    RANDOM = "random"
    HASH = "hash"
    WEIGHT = "weight"
    USER_ID = "user_id"
    REGION = "region"


class ReleaseStatus(Enum):
    """发布状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"


@dataclass
class ReleaseVersion:
    """发布版本"""
    version_id: str
    weight: float = 0.0  # 0.0 - 1.0
    status: ReleaseStatus = ReleaseStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "weight": self.weight,
            "status": self.status.value,
            "metadata": self.metadata
        }


@dataclass
class ReleasePlan:
    """发布计划"""
    plan_id: str
    name: str
    versions: List[ReleaseVersion]
    strategy: ReleaseStrategy
    status: ReleaseStatus
    created_at: float
    updated_at: float
    current_step: int = 0
    steps: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "versions": [v.to_dict() for v in self.versions],
            "strategy": self.strategy.value,
            "status": self.status.value,
            "current_step": self.current_step,
            "steps": self.steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class TrafficRouter:
    """流量路由器"""

    def __init__(self):
        self._logger = get_logger("canary.router")

    def route(self, key: str, versions: List[ReleaseVersion],
              strategy: ReleaseStrategy) -> Optional[str]:
        """根据策略路由到版本"""
        if not versions:
            return None

        # 过滤掉未激活的版本
        active = [v for v in versions if v.status in (ReleaseStatus.RUNNING, ReleaseStatus.PENDING)]
        if not active:
            return None

        if strategy == ReleaseStrategy.RANDOM:
            return self._route_random(active)
        elif strategy == ReleaseStrategy.HASH:
            return self._route_hash(key, active)
        elif strategy == ReleaseStrategy.WEIGHT:
            return self._route_weight(active)
        elif strategy == ReleaseStrategy.USER_ID:
            return self._route_user_id(key, active)
        else:
            return self._route_weight(active)

    def _route_random(self, versions: List[ReleaseVersion]) -> str:
        """随机路由"""
        import random
        weights = [v.weight for v in versions]
        return random.choices(versions, weights=weights)[0].version_id

    def _route_hash(self, key: str, versions: List[ReleaseVersion]) -> str:
        """哈希路由"""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        total_weight = sum(v.weight for v in versions)
        if total_weight == 0:
            return versions[0].version_id

        normalized = (hash_value % 10000) / 10000.0 * total_weight
        cumulative = 0
        for version in versions:
            cumulative += version.weight
            if normalized <= cumulative:
                return version.version_id
        return versions[-1].version_id

    def _route_weight(self, versions: List[ReleaseVersion]) -> str:
        """权重路由"""
        return self._route_hash(str(time.time()), versions)

    def _route_user_id(self, user_id: str, versions: List[ReleaseVersion]) -> str:
        """用户ID路由"""
        return self._route_hash(user_id, versions)


class CanaryReleaseManager:
    """灰度发布管理器"""

    def __init__(self):
        self._plans: Dict[str, ReleasePlan] = {}
        self._router = TrafficRouter()
        self._lock = threading.RLock()
        self._logger = get_logger("canary.manager")

    def create_plan(self, name: str, versions: List[str],
                    strategy: ReleaseStrategy = ReleaseStrategy.WEIGHT,
                    steps: Optional[List[float]] = None) -> ReleasePlan:
        """创建发布计划"""
        import uuid
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        version_objs = []
        for i, vid in enumerate(versions):
            weight = 1.0 / len(versions) if i == 0 else 0.0
            version_objs.append(ReleaseVersion(version_id=vid, weight=weight))

        plan = ReleasePlan(
            plan_id=plan_id,
            name=name,
            versions=version_objs,
            strategy=strategy,
            status=ReleaseStatus.PENDING,
            created_at=time.time(),
            updated_at=time.time(),
            steps=steps or [0.1, 0.25, 0.5, 0.75, 1.0]
        )

        with self._lock:
            self._plans[plan_id] = plan

        self._logger.info(f"Created release plan: {plan_id}")
        return plan

    def start_plan(self, plan_id: str) -> bool:
        """开始发布计划"""
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan or plan.status != ReleaseStatus.PENDING:
                return False

            plan.status = ReleaseStatus.RUNNING
            for v in plan.versions:
                v.status = ReleaseStatus.RUNNING
            plan.updated_at = time.time()

        self._logger.info(f"Started release plan: {plan_id}")
        return True

    def advance_step(self, plan_id: str) -> bool:
        """推进到下一步"""
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan or plan.status != ReleaseStatus.RUNNING:
                return False

            if plan.current_step >= len(plan.steps):
                plan.status = ReleaseStatus.COMPLETED
                return True

            target_weight = plan.steps[plan.current_step]
            plan.current_step += 1

            # 更新版本权重
            if len(plan.versions) >= 2:
                plan.versions[0].weight = 1.0 - target_weight
                plan.versions[1].weight = target_weight

            plan.updated_at = time.time()

        self._logger.info(f"Advanced plan {plan_id} to step {plan.current_step}, weight: {target_weight}")
        return True

    def rollback(self, plan_id: str) -> bool:
        """回滚发布计划"""
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan:
                return False

            plan.status = ReleaseStatus.ROLLED_BACK
            for v in plan.versions:
                v.status = ReleaseStatus.ROLLED_BACK

            # 回滚到第一个版本
            if plan.versions:
                plan.versions[0].weight = 1.0
                for v in plan.versions[1:]:
                    v.weight = 0.0

            plan.updated_at = time.time()

        self._logger.info(f"Rolled back release plan: {plan_id}")
        return True

    def route(self, plan_id: str, key: str = "") -> Optional[str]:
        """路由请求到版本"""
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan or plan.status != ReleaseStatus.RUNNING:
                return None

            return self._router.route(key, plan.versions, plan.strategy)

    def get_plan(self, plan_id: str) -> Optional[ReleasePlan]:
        """获取发布计划"""
        with self._lock:
            return self._plans.get(plan_id)

    def list_plans(self) -> List[ReleasePlan]:
        """列出所有发布计划"""
        with self._lock:
            return list(self._plans.values())

    def delete_plan(self, plan_id: str) -> bool:
        """删除发布计划"""
        with self._lock:
            if plan_id in self._plans:
                del self._plans[plan_id]
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_plans": len(self._plans),
                "running": sum(1 for p in self._plans.values()
                               if p.status == ReleaseStatus.RUNNING),
                "completed": sum(1 for p in self._plans.values()
                                if p.status == ReleaseStatus.COMPLETED),
                "rolled_back": sum(1 for p in self._plans.values()
                                  if p.status == ReleaseStatus.ROLLED_BACK)
            }


# 全局实例
_manager: Optional[CanaryReleaseManager] = None


def get_canary_manager() -> CanaryReleaseManager:
    """获取全局灰度发布管理器"""
    global _manager
    if _manager is None:
        _manager = CanaryReleaseManager()
    return _manager
