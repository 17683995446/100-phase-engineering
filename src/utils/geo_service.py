"""
地理位置服务
提供坐标计算、距离测量、地理围栏和位置查询功能
"""
import math
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.structured_logging import get_logger


class DistanceUnit(Enum):
    """距离单位"""
    KILOMETERS = "km"
    MILES = "mi"
    METERS = "m"
    NAUTICAL_MILES = "nm"


@dataclass
class GeoPoint:
    """地理坐标点"""
    latitude: float
    longitude: float
    altitude: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        self._validate()

    def _validate(self) -> None:
        """验证坐标有效性"""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "metadata": self.metadata
        }


@dataclass
class GeoFence:
    """地理围栏"""
    fence_id: str
    center: GeoPoint
    radius_meters: float
    name: str = ""

    def contains(self, point: GeoPoint) -> bool:
        """检查点是否在围栏内"""
        distance = GeoCalculator.haversine_distance(self.center, point)
        return distance <= self.radius_meters

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fence_id": self.fence_id,
            "name": self.name,
            "center": self.center.to_dict(),
            "radius_meters": self.radius_meters
        }


class GeoCalculator:
    """地理计算器"""

    EARTH_RADIUS_KM = 6371.0
    EARTH_RADIUS_MILES = 3959.0
    EARTH_RADIUS_METERS = 6371000.0

    @classmethod
    def haversine_distance(cls, point1: GeoPoint, point2: GeoPoint,
                           unit: DistanceUnit = DistanceUnit.KILOMETERS) -> float:
        """计算两点间的哈弗辛距离"""
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        if unit == DistanceUnit.KILOMETERS:
            radius = cls.EARTH_RADIUS_KM
        elif unit == DistanceUnit.MILES:
            radius = cls.EARTH_RADIUS_MILES
        elif unit == DistanceUnit.METERS:
            radius = cls.EARTH_RADIUS_METERS
        elif unit == DistanceUnit.NAUTICAL_MILES:
            radius = cls.EARTH_RADIUS_KM / 1.852
        else:
            radius = cls.EARTH_RADIUS_KM

        return radius * c

    @classmethod
    def bearing(cls, point1: GeoPoint, point2: GeoPoint) -> float:
        """计算从点1到点2的方位角（度）"""
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)

        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        return (bearing + 360) % 360

    @classmethod
    def destination_point(cls, start: GeoPoint, bearing: float,
                          distance_km: float) -> GeoPoint:
        """计算从起点沿方位角移动一定距离后的终点"""
        lat1, lon1 = math.radians(start.latitude), math.radians(start.longitude)
        bearing_rad = math.radians(bearing)

        angular_distance = distance_km / cls.EARTH_RADIUS_KM

        lat2 = math.asin(
            math.sin(lat1) * math.cos(angular_distance) +
            math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing_rad)
        )

        lon2 = lon1 + math.atan2(
            math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat1),
            math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2)
        )

        return GeoPoint(
            latitude=math.degrees(lat2),
            longitude=math.degrees(lon2)
        )

    @classmethod
    def midpoint(cls, point1: GeoPoint, point2: GeoPoint) -> GeoPoint:
        """计算两点间的中点"""
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)

        dlon = lon2 - lon1
        bx = math.cos(lat2) * math.cos(dlon)
        by = math.cos(lat2) * math.sin(dlon)

        lat3 = math.atan2(
            math.sin(lat1) + math.sin(lat2),
            math.sqrt((math.cos(lat1) + bx) ** 2 + by ** 2)
        )
        lon3 = lon1 + math.atan2(by, math.cos(lat1) + bx)

        return GeoPoint(
            latitude=math.degrees(lat3),
            longitude=math.degrees(lon3)
        )


class GeoFenceManager:
    """地理围栏管理器"""

    def __init__(self):
        self._fences: Dict[str, GeoFence] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("geo.fence")

    def create_fence(self, fence_id: str, center: GeoPoint,
                     radius_meters: float, name: str = "") -> GeoFence:
        """创建地理围栏"""
        with self._lock:
            fence = GeoFence(
                fence_id=fence_id,
                center=center,
                radius_meters=radius_meters,
                name=name
            )
            self._fences[fence_id] = fence
            self._logger.info(f"Created geo-fence: {fence_id}")
            return fence

    def get_fence(self, fence_id: str) -> Optional[GeoFence]:
        """获取地理围栏"""
        with self._lock:
            return self._fences.get(fence_id)

    def delete_fence(self, fence_id: str) -> bool:
        """删除地理围栏"""
        with self._lock:
            if fence_id in self._fences:
                del self._fences[fence_id]
                return True
            return False

    def check_point(self, point: GeoPoint) -> List[str]:
        """检查点位于哪些围栏内"""
        with self._lock:
            return [
                fence_id for fence_id, fence in self._fences.items()
                if fence.contains(point)
            ]

    def list_fences(self) -> List[GeoFence]:
        """列出所有围栏"""
        with self._lock:
            return list(self._fences.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_fences": len(self._fences)
            }


class GeoSpatialIndex:
    """简单地理空间索引"""

    def __init__(self):
        self._points: Dict[str, GeoPoint] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("geo.index")

    def add_point(self, point_id: str, point: GeoPoint) -> None:
        """添加点"""
        with self._lock:
            self._points[point_id] = point

    def remove_point(self, point_id: str) -> bool:
        """移除点"""
        with self._lock:
            if point_id in self._points:
                del self._points[point_id]
                return True
            return False

    def find_nearby(self, center: GeoPoint, radius_meters: float) -> List[Tuple[str, float]]:
        """查找附近的点"""
        with self._lock:
            results = []
            for point_id, point in self._points.items():
                distance = GeoCalculator.haversine_distance(
                    center, point, DistanceUnit.METERS
                )
                if distance <= radius_meters:
                    results.append((point_id, distance))
            return sorted(results, key=lambda x: x[1])

    def find_nearest(self, center: GeoPoint, limit: int = 10) -> List[Tuple[str, float]]:
        """查找最近的点"""
        with self._lock:
            results = []
            for point_id, point in self._points.items():
                distance = GeoCalculator.haversine_distance(
                    center, point, DistanceUnit.METERS
                )
                results.append((point_id, distance))
            return sorted(results, key=lambda x: x[1])[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_points": len(self._points)
            }


# 全局实例
_fence_manager: Optional[GeoFenceManager] = None
_spatial_index: Optional[GeoSpatialIndex] = None


def get_geo_fence_manager() -> GeoFenceManager:
    """获取全局地理围栏管理器"""
    global _fence_manager
    if _fence_manager is None:
        _fence_manager = GeoFenceManager()
    return _fence_manager


def get_spatial_index() -> GeoSpatialIndex:
    """获取全局空间索引"""
    global _spatial_index
    if _spatial_index is None:
        _spatial_index = GeoSpatialIndex()
    return _spatial_index
