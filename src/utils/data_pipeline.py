"""
数据管道与ETL
提供数据提取、转换、加载和管道编排功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Iterator, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class PipelineStatus(Enum):
    """管道状态"""
    IDLE = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    PAUSED = auto()


@dataclass
class DataRecord:
    """数据记录"""
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取字段值"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置字段值"""
        self.data[key] = value


class DataSource:
    """数据源基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._logger = get_logger(f"source.{name}")
    
    def extract(self) -> Iterator[DataRecord]:
        """提取数据"""
        raise NotImplementedError
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {"name": self.name, "type": self.__class__.__name__}


class DataTransformer:
    """数据转换器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._logger = get_logger(f"transformer.{name}")
    
    def transform(self, record: DataRecord) -> Optional[DataRecord]:
        """转换数据"""
        raise NotImplementedError
    
    def transform_batch(self, records: List[DataRecord]) -> List[DataRecord]:
        """批量转换"""
        return [r for r in (self.transform(record) for record in records) if r is not None]


class DataSink:
    """数据目标基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._records_loaded = 0
        self._lock = threading.Lock()
        self._logger = get_logger(f"sink.{name}")
    
    def load(self, record: DataRecord) -> bool:
        """加载数据"""
        raise NotImplementedError
    
    def load_batch(self, records: List[DataRecord]) -> int:
        """批量加载"""
        count = 0
        for record in records:
            if self.load(record):
                count += 1
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {"name": self.name, "records_loaded": self._records_loaded}


class MemorySource(DataSource):
    """内存数据源"""
    
    def __init__(self, name: str, data: List[Dict[str, Any]]):
        super().__init__(name)
        self._data = data
    
    def extract(self) -> Iterator[DataRecord]:
        """从内存提取"""
        for item in self._data:
            yield DataRecord(data=item, source=self.name)


class MemorySink(DataSink):
    """内存数据目标"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._records: List[DataRecord] = []
        self._storage_lock = threading.Lock()
    
    def load(self, record: DataRecord) -> bool:
        """加载到内存"""
        with self._storage_lock:
            self._records.append(record)
        with self._lock:
            self._records_loaded += 1
        return True
    
    def get_records(self) -> List[DataRecord]:
        """获取所有记录"""
        with self._storage_lock:
            return list(self._records)
    
    def clear(self) -> None:
        """清空数据"""
        with self._storage_lock:
            self._records.clear()


class FilterTransformer(DataTransformer):
    """过滤转换器"""
    
    def __init__(self, name: str, condition: Callable[[DataRecord], bool]):
        super().__init__(name)
        self.condition = condition
    
    def transform(self, record: DataRecord) -> Optional[DataRecord]:
        """过滤数据"""
        if self.condition(record):
            return record
        return None


class MapTransformer(DataTransformer):
    """映射转换器"""
    
    def __init__(self, name: str, mapper: Callable[[DataRecord], DataRecord]):
        super().__init__(name)
        self.mapper = mapper
    
    def transform(self, record: DataRecord) -> Optional[DataRecord]:
        """映射数据"""
        return self.mapper(record)


class Pipeline:
    """数据管道"""
    
    def __init__(self, name: str):
        self.name = name
        self._source: Optional[DataSource] = None
        self._transformers: List[DataTransformer] = []
        self._sink: Optional[DataSink] = None
        self._status = PipelineStatus.IDLE
        self._lock = threading.Lock()
        self._logger = get_logger(f"pipeline.{name}")
        self._records_processed = 0
        self._records_filtered = 0
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
    
    def set_source(self, source: DataSource) -> "Pipeline":
        """设置数据源"""
        self._source = source
        return self
    
    def add_transformer(self, transformer: DataTransformer) -> "Pipeline":
        """添加转换器"""
        self._transformers.append(transformer)
        return self
    
    def set_sink(self, sink: DataSink) -> "Pipeline":
        """设置数据目标"""
        self._sink = sink
        return self
    
    def run(self, batch_size: int = 100) -> Dict[str, Any]:
        """运行管道"""
        if not self._source or not self._sink:
            raise ValueError("Source and sink must be set")
        
        with self._lock:
            self._status = PipelineStatus.RUNNING
            self._start_time = datetime.now()
            self._records_processed = 0
            self._records_filtered = 0
        
        try:
            batch = []
            for record in self._source.extract():
                processed = self._process_record(record)
                if processed:
                    batch.append(processed)
                    
                    if len(batch) >= batch_size:
                        self._load_batch(batch)
                        batch = []
                else:
                    self._records_filtered += 1
                
                self._records_processed += 1
            
            if batch:
                self._load_batch(batch)
            
            with self._lock:
                self._status = PipelineStatus.COMPLETED
                self._end_time = datetime.now()
            
            self._logger.info(f"Pipeline {self.name} completed")
            
        except Exception as e:
            with self._lock:
                self._status = PipelineStatus.FAILED
                self._end_time = datetime.now()
            self._logger.error(f"Pipeline {self.name} failed: {e}")
            raise
        
        return self.get_stats()
    
    def _process_record(self, record: DataRecord) -> Optional[DataRecord]:
        """处理单条记录"""
        current = record
        for transformer in self._transformers:
            if current is None:
                break
            current = transformer.transform(current)
        return current
    
    def _load_batch(self, batch: List[DataRecord]) -> None:
        """加载批次"""
        self._sink.load_batch(batch)
    
    def get_status(self) -> PipelineStatus:
        """获取状态"""
        with self._lock:
            return self._status
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            duration = None
            if self._start_time and self._end_time:
                duration = (self._end_time - self._start_time).total_seconds()
            elif self._start_time:
                duration = (datetime.now() - self._start_time).total_seconds()
            
            return {
                "name": self.name,
                "status": self._status.name,
                "records_processed": self._records_processed,
                "records_filtered": self._records_filtered,
                "records_loaded": self._sink.get_stats().get("records_loaded", 0) if self._sink else 0,
                "duration_seconds": duration,
                "transformers": len(self._transformers)
            }


class PipelineManager:
    """管道管理器"""
    
    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._lock = threading.Lock()
        self._logger = get_logger("pipeline.manager")
    
    def register_pipeline(self, pipeline: Pipeline) -> None:
        """注册管道"""
        with self._lock:
            self._pipelines[pipeline.name] = pipeline
        self._logger.info(f"Registered pipeline: {pipeline.name}")
    
    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """获取管道"""
        with self._lock:
            return self._pipelines.get(name)
    
    def run_pipeline(self, name: str) -> Optional[Dict[str, Any]]:
        """运行管道"""
        pipeline = self.get_pipeline(name)
        if pipeline:
            return pipeline.run()
        return None
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有统计"""
        with self._lock:
            return {
                name: pipeline.get_stats()
                for name, pipeline in self._pipelines.items()
            }


# 全局实例
_manager: Optional[PipelineManager] = None


def get_pipeline_manager() -> PipelineManager:
    """获取管道管理器"""
    global _manager
    if _manager is None:
        _manager = PipelineManager()
    return _manager
