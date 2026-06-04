"""
数据治理平台
提供数据质量规则、数据血缘追踪、数据分类分级、合规性检查功能
"""
import time
import threading
import uuid
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class DataClassification(Enum):
    """数据分类"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataQualityStatus(Enum):
    """数据质量状态"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    UNKNOWN = "unknown"


class RuleType(Enum):
    """规则类型"""
    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"


@dataclass
class DataAsset:
    """数据资产"""
    asset_id: str
    name: str
    source: str
    classification: DataClassification = DataClassification.INTERNAL
    owner: str = ""
    tags: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "source": self.source,
            "classification": self.classification.value,
            "owner": self.owner,
            "tags": list(self.tags)
        }


@dataclass
class DataLineage:
    """数据血缘"""
    lineage_id: str
    source_asset_id: str
    target_asset_id: str
    transformation: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "source_asset_id": self.source_asset_id,
            "target_asset_id": self.target_asset_id,
            "transformation": self.transformation,
            "timestamp": self.timestamp
        }


@dataclass
class QualityRule:
    """质量规则"""
    rule_id: str
    name: str
    rule_type: RuleType
    asset_id: str
    expression: str
    threshold: float = 1.0
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "rule_type": self.rule_type.value,
            "asset_id": self.asset_id,
            "expression": self.expression,
            "threshold": self.threshold,
            "enabled": self.enabled
        }


@dataclass
class QualityReport:
    """质量报告"""
    report_id: str
    asset_id: str
    rule_id: str
    status: DataQualityStatus
    score: float
    details: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "asset_id": self.asset_id,
            "rule_id": self.rule_id,
            "status": self.status.value,
            "score": self.score,
            "details": self.details,
            "timestamp": self.timestamp
        }


@dataclass
class CompliancePolicy:
    """合规策略"""
    policy_id: str
    name: str
    regulation: str
    requirements: List[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "regulation": self.regulation,
            "requirements": self.requirements,
            "enabled": self.enabled
        }


class DataGovernancePlatform:
    """数据治理平台"""

    def __init__(self):
        self._assets: Dict[str, DataAsset] = {}
        self._lineage: Dict[str, DataLineage] = {}
        self._rules: Dict[str, QualityRule] = {}
        self._reports: List[QualityReport] = []
        self._policies: Dict[str, CompliancePolicy] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("data.governance")
        self._rule_handlers: Dict[RuleType, Callable[[Any, QualityRule], tuple[DataQualityStatus, float, str]]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """注册默认规则处理器"""
        self._rule_handlers[RuleType.COMPLETENESS] = self._check_completeness
        self._rule_handlers[RuleType.UNIQUENESS] = self._check_uniqueness
        self._rule_handlers[RuleType.VALIDITY] = self._check_validity

    def _check_completeness(self, data: Any, rule: QualityRule) -> tuple[DataQualityStatus, float, str]:
        """检查完整性"""
        if isinstance(data, (list, dict)):
            if len(data) == 0:
                return DataQualityStatus.FAIL, 0.0, "Empty data"
            return DataQualityStatus.PASS, 1.0, f"Data size: {len(data)}"
        if data is None:
            return DataQualityStatus.FAIL, 0.0, "Null value"
        return DataQualityStatus.PASS, 1.0, "Value present"

    def _check_uniqueness(self, data: Any, rule: QualityRule) -> tuple[DataQualityStatus, float, str]:
        """检查唯一性"""
        if isinstance(data, list):
            unique = len(set(str(x) for x in data))
            total = len(data)
            if total == 0:
                return DataQualityStatus.PASS, 1.0, "Empty list"
            ratio = unique / total
            if ratio >= rule.threshold:
                return DataQualityStatus.PASS, ratio, f"{unique}/{total} unique"
            return DataQualityStatus.FAIL, ratio, f"Duplicates found: {total - unique}"
        return DataQualityStatus.PASS, 1.0, "Single value"

    def _check_validity(self, data: Any, rule: QualityRule) -> tuple[DataQualityStatus, float, str]:
        """检查有效性"""
        expr = rule.expression
        if expr == "not_null":
            if data is None:
                return DataQualityStatus.FAIL, 0.0, "Null value"
            return DataQualityStatus.PASS, 1.0, "Not null"
        if expr == "positive":
            try:
                if float(data) > 0:
                    return DataQualityStatus.PASS, 1.0, "Positive value"
                return DataQualityStatus.FAIL, 0.0, "Non-positive value"
            except (ValueError, TypeError):
                return DataQualityStatus.FAIL, 0.0, "Not a number"
        return DataQualityStatus.UNKNOWN, 0.0, "Unknown expression"

    def register_asset(self, asset_id: str, name: str, source: str,
                       classification: DataClassification = DataClassification.INTERNAL,
                       owner: str = "",
                       tags: Optional[List[str]] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> DataAsset:
        """注册数据资产"""
        with self._lock:
            if asset_id in self._assets:
                raise ValueError(f"Asset already exists: {asset_id}")
            asset = DataAsset(
                asset_id=asset_id,
                name=name,
                source=source,
                classification=classification,
                owner=owner,
                tags=set(tags or []),
                metadata=metadata or {}
            )
            self._assets[asset_id] = asset
            self._logger.info(f"Asset registered: {asset_id}")
            return asset

    def get_asset(self, asset_id: str) -> Optional[DataAsset]:
        """获取数据资产"""
        with self._lock:
            return self._assets.get(asset_id)

    def list_assets(self, classification: Optional[str] = None,
                    tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出数据资产"""
        with self._lock:
            assets = self._assets.values()
            if classification:
                assets = [a for a in assets if a.classification.value == classification]
            if tag:
                assets = [a for a in assets if tag in a.tags]
            return [a.to_dict() for a in assets]

    def delete_asset(self, asset_id: str) -> bool:
        """删除数据资产"""
        with self._lock:
            if asset_id in self._assets:
                del self._assets[asset_id]
                self._logger.info(f"Asset deleted: {asset_id}")
                return True
            return False

    def add_lineage(self, source_asset_id: str, target_asset_id: str,
                    transformation: str = "") -> DataLineage:
        """添加数据血缘"""
        with self._lock:
            lineage_id = f"lin_{uuid.uuid4().hex[:8]}"
            lineage = DataLineage(
                lineage_id=lineage_id,
                source_asset_id=source_asset_id,
                target_asset_id=target_asset_id,
                transformation=transformation
            )
            self._lineage[lineage_id] = lineage
            self._logger.info(f"Lineage added: {source_asset_id} -> {target_asset_id}")
            return lineage

    def get_lineage(self, asset_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """获取数据血缘"""
        with self._lock:
            upstream = [l.to_dict() for l in self._lineage.values()
                        if l.target_asset_id == asset_id]
            downstream = [l.to_dict() for l in self._lineage.values()
                          if l.source_asset_id == asset_id]
            return {"upstream": upstream, "downstream": downstream}

    def create_rule(self, rule_id: str, name: str, rule_type: RuleType,
                    asset_id: str, expression: str,
                    threshold: float = 1.0) -> QualityRule:
        """创建质量规则"""
        with self._lock:
            if rule_id in self._rules:
                raise ValueError(f"Rule already exists: {rule_id}")
            rule = QualityRule(
                rule_id=rule_id,
                name=name,
                rule_type=rule_type,
                asset_id=asset_id,
                expression=expression,
                threshold=threshold
            )
            self._rules[rule_id] = rule
            self._logger.info(f"Quality rule created: {rule_id}")
            return rule

    def get_rule(self, rule_id: str) -> Optional[QualityRule]:
        """获取质量规则"""
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(self, asset_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出质量规则"""
        with self._lock:
            rules = self._rules.values()
            if asset_id:
                rules = [r for r in rules if r.asset_id == asset_id]
            return [r.to_dict() for r in rules]

    def delete_rule(self, rule_id: str) -> bool:
        """删除质量规则"""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                return True
            return False

    def evaluate_rule(self, rule_id: str, data: Any) -> Optional[QualityReport]:
        """评估质量规则"""
        with self._lock:
            rule = self._rules.get(rule_id)
            if not rule or not rule.enabled:
                return None

            handler = self._rule_handlers.get(rule.rule_type)
            if not handler:
                return None

            status, score, details = handler(data, rule)
            report = QualityReport(
                report_id=f"rep_{uuid.uuid4().hex[:8]}",
                asset_id=rule.asset_id,
                rule_id=rule_id,
                status=status,
                score=score,
                details=details
            )
            self._reports.append(report)
            self._logger.info(f"Rule evaluated: {rule_id} status={status.value} score={score}")
            return report

    def evaluate_asset(self, asset_id: str, data: Any) -> List[QualityReport]:
        """评估资产的所有规则"""
        with self._lock:
            reports = []
            for rule in self._rules.values():
                if rule.asset_id == asset_id and rule.enabled:
                    report = self.evaluate_rule(rule.rule_id, data)
                    if report:
                        reports.append(report)
            return reports

    def get_reports(self, asset_id: Optional[str] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """获取质量报告"""
        with self._lock:
            reports = self._reports
            if asset_id:
                reports = [r for r in reports if r.asset_id == asset_id]
            return [r.to_dict() for r in reports[-limit:]]

    def create_policy(self, policy_id: str, name: str, regulation: str,
                      requirements: Optional[List[str]] = None) -> CompliancePolicy:
        """创建合规策略"""
        with self._lock:
            if policy_id in self._policies:
                raise ValueError(f"Policy already exists: {policy_id}")
            policy = CompliancePolicy(
                policy_id=policy_id,
                name=name,
                regulation=regulation,
                requirements=requirements or []
            )
            self._policies[policy_id] = policy
            self._logger.info(f"Policy created: {policy_id}")
            return policy

    def get_policy(self, policy_id: str) -> Optional[CompliancePolicy]:
        """获取合规策略"""
        with self._lock:
            return self._policies.get(policy_id)

    def list_policies(self) -> List[Dict[str, Any]]:
        """列出合规策略"""
        with self._lock:
            return [p.to_dict() for p in self._policies.values()]

    def check_compliance(self, asset_id: str) -> Dict[str, Any]:
        """检查资产合规性"""
        with self._lock:
            asset = self._assets.get(asset_id)
            if not asset:
                return {"compliant": False, "reason": "Asset not found"}

            issues = []
            if asset.classification in (DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED):
                if not asset.owner:
                    issues.append("High classification asset must have an owner")

            reports = [r for r in self._reports if r.asset_id == asset_id]
            failed_rules = [r for r in reports if r.status == DataQualityStatus.FAIL]
            if failed_rules:
                issues.append(f"{len(failed_rules)} quality rules failed")

            return {
                "asset_id": asset_id,
                "compliant": len(issues) == 0,
                "issues": issues,
                "classification": asset.classification.value
            }

    def classify_data(self, asset_id: str,
                      classification: DataClassification) -> bool:
        """分类数据资产"""
        with self._lock:
            asset = self._assets.get(asset_id)
            if not asset:
                return False
            asset.classification = classification
            self._logger.info(f"Asset classified: {asset_id} -> {classification.value}")
            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_assets": len(self._assets),
                "total_lineage": len(self._lineage),
                "total_rules": len(self._rules),
                "total_reports": len(self._reports),
                "total_policies": len(self._policies)
            }


# 全局实例
_platform: Optional[DataGovernancePlatform] = None


def get_data_governance_platform() -> DataGovernancePlatform:
    """获取全局数据治理平台"""
    global _platform
    if _platform is None:
        _platform = DataGovernancePlatform()
    return _platform
