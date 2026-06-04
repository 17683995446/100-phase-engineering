"""
日志聚合与分析
提供日志收集、聚合、查询和分析功能
"""
import json
import time
import re
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    source: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "metadata": self.metadata
        }


class LogBuffer:
    """日志缓冲区"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._entries: deque = deque(maxlen=max_size)
        self._lock = threading.RLock()
    
    def append(self, entry: LogEntry) -> None:
        """添加日志条目"""
        with self._lock:
            self._entries.append(entry)
    
    def get_entries(self, limit: int = 100, offset: int = 0) -> List[LogEntry]:
        """获取日志条目"""
        with self._lock:
            entries = list(self._entries)
            return entries[offset:offset + limit]
    
    def clear(self) -> None:
        """清空缓冲区"""
        with self._lock:
            self._entries.clear()
    
    def get_size(self) -> int:
        """获取当前大小"""
        with self._lock:
            return len(self._entries)


class LogAggregator:
    """日志聚合器"""
    
    def __init__(self, buffer_size: int = 10000):
        self._buffer = LogBuffer(buffer_size)
        self._lock = threading.RLock()
        self._logger = get_logger("log.aggregator")
        self._sources: set = set()
        self._level_counts: Dict[str, int] = defaultdict(int)
        self._hourly_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._error_patterns: Dict[str, int] = defaultdict(int)
    
    def collect(self, entry: LogEntry) -> None:
        """收集日志"""
        self._buffer.append(entry)
        
        with self._lock:
            self._sources.add(entry.source)
            self._level_counts[entry.level.value] += 1
            
            hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
            self._hourly_counts[hour_key][entry.level.value] += 1
            
            # 记录错误模式
            if entry.level in (LogLevel.ERROR, LogLevel.CRITICAL):
                error_key = entry.message[:100]  # 取前100字符作为模式
                self._error_patterns[error_key] += 1
    
    def collect_from_dict(self, log_dict: Dict[str, Any]) -> None:
        """从字典收集日志"""
        try:
            entry = LogEntry(
                timestamp=datetime.fromisoformat(log_dict.get("timestamp", datetime.now().isoformat())),
                level=LogLevel(log_dict.get("level", "INFO")),
                source=log_dict.get("source", "unknown"),
                message=log_dict.get("message", ""),
                metadata=log_dict.get("metadata", {})
            )
            self.collect(entry)
        except Exception as e:
            self._logger.error(f"Failed to parse log entry: {e}")
    
    def query(self, 
              level: Optional[LogLevel] = None,
              source: Optional[str] = None,
              start_time: Optional[datetime] = None,
              end_time: Optional[datetime] = None,
              message_pattern: Optional[str] = None,
              limit: int = 100) -> List[LogEntry]:
        """查询日志"""
        entries = self._buffer.get_entries(limit=limit * 10)
        results = []
        
        for entry in entries:
            if level and entry.level != level:
                continue
            if source and entry.source != source:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            if message_pattern and not re.search(message_pattern, entry.message, re.IGNORECASE):
                continue
            
            results.append(entry)
            if len(results) >= limit:
                break
        
        return results
    
    def get_level_distribution(self) -> Dict[str, int]:
        """获取日志级别分布"""
        with self._lock:
            return dict(self._level_counts)
    
    def get_source_distribution(self) -> Dict[str, int]:
        """获取来源分布"""
        entries = self._buffer.get_entries(limit=10000)
        source_counts = defaultdict(int)
        for entry in entries:
            source_counts[entry.source] += 1
        return dict(source_counts)
    
    def get_hourly_stats(self, hours: int = 24) -> Dict[str, Dict[str, int]]:
        """获取每小时统计"""
        with self._lock:
            now = datetime.now()
            result = {}
            for i in range(hours):
                hour = now - timedelta(hours=i)
                hour_key = hour.strftime("%Y-%m-%d %H:00")
                if hour_key in self._hourly_counts:
                    result[hour_key] = dict(self._hourly_counts[hour_key])
            return result
    
    def get_top_errors(self, limit: int = 10) -> List[Tuple[str, int]]:
        """获取最常见的错误"""
        with self._lock:
            sorted_errors = sorted(
                self._error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_errors[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_entries": self._buffer.get_size(),
                "sources": len(self._sources),
                "level_distribution": dict(self._level_counts),
                "top_errors": self.get_top_errors(5)
            }
    
    def clear(self) -> None:
        """清空数据"""
        with self._lock:
            self._buffer.clear()
            self._sources.clear()
            self._level_counts.clear()
            self._hourly_counts.clear()
            self._error_patterns.clear()


class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, aggregator: LogAggregator):
        self._aggregator = aggregator
        self._logger = get_logger("log.analyzer")
    
    def analyze_trends(self, hours: int = 24) -> Dict[str, Any]:
        """分析趋势"""
        hourly_stats = self._aggregator.get_hourly_stats(hours)
        
        if not hourly_stats:
            return {"message": "No data available"}
        
        # 计算趋势
        error_trend = []
        for hour_key in sorted(hourly_stats.keys()):
            stats = hourly_stats[hour_key]
            error_count = stats.get("ERROR", 0) + stats.get("CRITICAL", 0)
            error_trend.append({"hour": hour_key, "errors": error_count})
        
        return {
            "error_trend": error_trend,
            "total_hours": len(hourly_stats)
        }
    
    def detect_anomalies(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """检测异常"""
        hourly_stats = self._aggregator.get_hourly_stats(24)
        anomalies = []
        
        error_counts = []
        for hour_key, stats in hourly_stats.items():
            error_count = stats.get("ERROR", 0) + stats.get("CRITICAL", 0)
            error_counts.append(error_count)
        
        if not error_counts:
            return anomalies
        
        avg_errors = sum(error_counts) / len(error_counts)
        
        for hour_key, stats in hourly_stats.items():
            error_count = stats.get("ERROR", 0) + stats.get("CRITICAL", 0)
            if error_count > avg_errors * threshold:
                anomalies.append({
                    "hour": hour_key,
                    "error_count": error_count,
                    "average": avg_errors,
                    "severity": "high" if error_count > avg_errors * 20 else "medium"
                })
        
        return anomalies
    
    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        stats = self._aggregator.get_stats()
        trends = self.analyze_trends()
        anomalies = self.detect_anomalies()
        
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": stats,
            "trends": trends,
            "anomalies": anomalies,
            "recommendations": self._generate_recommendations(stats, anomalies)
        }
    
    def _generate_recommendations(self, stats: Dict[str, Any], 
                                   anomalies: List[Dict[str, Any]]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        level_dist = stats.get("level_distribution", {})
        total = sum(level_dist.values())
        
        if total > 0:
            error_rate = (level_dist.get("ERROR", 0) + level_dist.get("CRITICAL", 0)) / total
            if error_rate > 0.1:
                recommendations.append("错误率过高，建议检查系统稳定性")
            
            warning_rate = level_dist.get("WARNING", 0) / total
            if warning_rate > 0.2:
                recommendations.append("警告数量较多，建议排查潜在问题")
        
        if anomalies:
            recommendations.append(f"检测到 {len(anomalies)} 个异常时段，建议深入分析")
        
        if not recommendations:
            recommendations.append("系统运行正常")
        
        return recommendations


class LogExporter:
    """日志导出器"""
    
    def __init__(self, aggregator: LogAggregator):
        self._aggregator = aggregator
        self._logger = get_logger("log.exporter")
    
    def export_to_json(self, filepath: str, 
                       level: Optional[LogLevel] = None,
                       limit: int = 1000) -> bool:
        """导出为JSON"""
        try:
            entries = self._aggregator.query(level=level, limit=limit)
            data = [entry.to_dict() for entry in entries]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self._logger.info(f"Exported {len(entries)} entries to {filepath}")
            return True
        except Exception as e:
            self._logger.error(f"Export failed: {e}")
            return False
    
    def export_to_csv(self, filepath: str,
                      level: Optional[LogLevel] = None,
                      limit: int = 1000) -> bool:
        """导出为CSV"""
        try:
            entries = self._aggregator.query(level=level, limit=limit)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("timestamp,level,source,message\n")
                for entry in entries:
                    message = entry.message.replace('"', '""').replace('\n', ' ')
                    f.write(f'"{entry.timestamp.isoformat()}","{entry.level.value}",'
                           f'"{entry.source}","{message}"\n')
            
            self._logger.info(f"Exported {len(entries)} entries to {filepath}")
            return True
        except Exception as e:
            self._logger.error(f"Export failed: {e}")
            return False


# 全局实例
_aggregator: Optional[LogAggregator] = None
_analyzer: Optional[LogAnalyzer] = None


def get_log_aggregator(buffer_size: int = 10000) -> LogAggregator:
    """获取日志聚合器"""
    global _aggregator
    if _aggregator is None:
        _aggregator = LogAggregator(buffer_size)
    return _aggregator


def get_log_analyzer(aggregator: Optional[LogAggregator] = None) -> LogAnalyzer:
    """获取日志分析器"""
    global _analyzer
    if _analyzer is None:
        _analyzer = LogAnalyzer(aggregator or get_log_aggregator())
    return _analyzer
