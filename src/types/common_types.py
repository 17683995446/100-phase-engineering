"""
通用类型定义
提供精确的类型别名和 TypedDict，减少 Any 的使用
"""
from typing import Union, Dict, List, Optional, TypedDict

# 配置值类型
ConfigValue = Union[str, int, float, bool, List[str], Dict[str, str]]

# 指标值类型
MetricValue = Union[int, float]

# 时间戳类型
Timestamp = float

# 标签类型
Labels = Dict[str, str]


class CoverageReportDict(TypedDict, total=False):
    """覆盖率报告字典"""
    report_id: str
    timestamp: float
    overall_coverage: float
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    threshold: float
    passed: bool


class PipelineRunDict(TypedDict, total=False):
    """流水线运行字典"""
    run_id: str
    pipeline_id: str
    trigger: str
    status: str
    duration: float
    stages: Dict[str, Dict[str, Any]]
    variables: Dict[str, str]
    artifacts: List[str]


class ServiceInstanceDict(TypedDict, total=False):
    """服务实例字典"""
    service_id: str
    status: str
    target_replicas: int
    current_replicas: int
    containers: List[Dict[str, Any]]


class SecretInfoDict(TypedDict, total=False):
    """密钥信息字典"""
    secret_id: str
    name: str
    secret_type: str
    status: str
    created_at: float
    expires_at: Optional[float]
    access_count: int
    allowed_services: Optional[List[str]]


class AlertDict(TypedDict, total=False):
    """告警字典"""
    alert_id: str
    rule_id: str
    name: str
    severity: str
    status: str
    value: float
    threshold: float
    fired_at: float
    resolved_at: Optional[float]
    message: str


class ConfigItemDict(TypedDict, total=False):
    """配置项字典"""
    key: str
    value: ConfigValue
    config_type: str
    description: str
    status: str
    version: int
    env: str
    tags: List[str]
    updated_at: float


class DataAssetDict(TypedDict, total=False):
    """数据资产字典"""
    asset_id: str
    name: str
    source: str
    classification: str
    owner: str
    tags: List[str]


class QualityReportDict(TypedDict, total=False):
    """质量报告字典"""
    report_id: str
    asset_id: str
    rule_id: str
    status: str
    score: float
    details: str
    timestamp: float


class StatsDict(TypedDict, total=False):
    """通用统计字典"""
    total: int
    active: int
    failed: int
    success: int
    pending: int
