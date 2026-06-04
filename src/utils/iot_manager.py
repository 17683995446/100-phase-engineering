"""
物联网设备管理
提供设备注册、状态监控、数据采集和指令下发功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class DeviceStatus(Enum):
    """设备状态"""
    ONLINE = auto()
    OFFLINE = auto()
    SLEEPING = auto()
    ERROR = auto()
    MAINTENANCE = auto()


@dataclass
class Device:
    """设备"""
    device_id: str
    name: str
    device_type: str = ""
    status: DeviceStatus = DeviceStatus.OFFLINE
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_seen: Optional[datetime] = None
    registered_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type,
            "status": self.status.name,
            "metadata": self.metadata,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "registered_at": self.registered_at.isoformat()
        }


@dataclass
class SensorReading:
    """传感器读数"""
    device_id: str
    sensor_type: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "sensor_type": self.sensor_type,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat()
        }


class DeviceManager:
    """设备管理器"""
    
    def __init__(self):
        self._devices: Dict[str, Device] = {}
        self._readings: Dict[str, List[SensorReading]] = {}
        self._callbacks: List[Callable] = []
        self._lock = threading.RLock()
        self._logger = get_logger("device.manager")
    
    def register_device(self, device: Device) -> bool:
        """注册设备"""
        with self._lock:
            self._devices[device.device_id] = device
        
        self._logger.info(f"Device registered: {device.device_id}")
        return True
    
    def unregister_device(self, device_id: str) -> bool:
        """注销设备"""
        with self._lock:
            if device_id in self._devices:
                del self._devices[device_id]
                return True
            return False
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """获取设备"""
        with self._lock:
            return self._devices.get(device_id)
    
    def update_device_status(self, device_id: str, 
                             status: DeviceStatus) -> bool:
        """更新设备状态"""
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return False
            
            device.status = status
            device.last_seen = datetime.now()
        
        self._logger.info(f"Device {device_id} status: {status.name}")
        return True
    
    def get_devices_by_status(self, status: DeviceStatus) -> List[Device]:
        """按状态获取设备"""
        with self._lock:
            return [
                device for device in self._devices.values()
                if device.status == status
            ]
    
    def get_devices_by_type(self, device_type: str) -> List[Device]:
        """按类型获取设备"""
        with self._lock:
            return [
                device for device in self._devices.values()
                if device.device_type == device_type
            ]
    
    def get_all_devices(self) -> List[Device]:
        """获取所有设备"""
        with self._lock:
            return list(self._devices.values())
    
    def add_reading(self, reading: SensorReading) -> bool:
        """添加传感器读数"""
        with self._lock:
            if reading.device_id not in self._readings:
                self._readings[reading.device_id] = []
            
            self._readings[reading.device_id].append(reading)
            
            # 限制历史记录数量
            if len(self._readings[reading.device_id]) > 1000:
                self._readings[reading.device_id] = self._readings[reading.device_id][-1000:]
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(reading)
            except Exception as e:
                self._logger.error(f"Callback error: {e}")
        
        return True
    
    def get_readings(self, device_id: str, 
                     sensor_type: Optional[str] = None,
                     limit: int = 100) -> List[SensorReading]:
        """获取读数"""
        with self._lock:
            readings = self._readings.get(device_id, [])
            
            if sensor_type:
                readings = [
                    r for r in readings
                    if r.sensor_type == sensor_type
                ]
            
            return readings[-limit:]
    
    def get_latest_reading(self, device_id: str,
                           sensor_type: str) -> Optional[SensorReading]:
        """获取最新读数"""
        readings = self.get_readings(device_id, sensor_type, limit=1)
        return readings[0] if readings else None
    
    def add_callback(self, callback: Callable[[SensorReading], None]) -> None:
        """添加读数回调"""
        self._callbacks.append(callback)
    
    def send_command(self, device_id: str, 
                     command: str, 
                     params: Optional[Dict[str, Any]] = None) -> bool:
        """发送命令到设备"""
        device = self.get_device(device_id)
        if not device or device.status != DeviceStatus.ONLINE:
            return False
        
        self._logger.info(f"Command sent to {device_id}: {command}")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._devices)
            online = sum(1 for d in self._devices.values() 
                       if d.status == DeviceStatus.ONLINE)
            
            return {
                "total_devices": total,
                "online": online,
                "offline": total - online,
                "total_readings": sum(len(r) for r in self._readings.values())
            }


# 全局实例
_manager: Optional[DeviceManager] = None


def get_device_manager() -> DeviceManager:
    """获取设备管理器"""
    global _manager
    if _manager is None:
        _manager = DeviceManager()
    return _manager
