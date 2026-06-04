"""
库存管理系统
提供库存跟踪、预警、调拨和盘点功能
"""
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class StockStatus(Enum):
    """库存状态"""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    RESERVED = "reserved"


@dataclass
class StockItem:
    """库存项"""
    sku: str
    name: str
    quantity: int
    reserved: int = 0
    reorder_level: int = 10
    reorder_quantity: int = 100
    location: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def available(self) -> int:
        return max(0, self.quantity - self.reserved)

    @property
    def status(self) -> StockStatus:
        if self.quantity <= 0:
            return StockStatus.OUT_OF_STOCK
        elif self.quantity <= self.reorder_level:
            return StockStatus.LOW_STOCK
        return StockStatus.IN_STOCK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sku": self.sku,
            "name": self.name,
            "quantity": self.quantity,
            "reserved": self.reserved,
            "available": self.available,
            "status": self.status.value,
            "reorder_level": self.reorder_level,
            "location": self.location
        }


class InventoryManager:
    """库存管理器"""

    def __init__(self):
        self._items: Dict[str, StockItem] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("inventory.manager")

    def add_item(self, sku: str, name: str, quantity: int,
                 reorder_level: int = 10, location: str = "default",
                 metadata: Optional[Dict[str, Any]] = None) -> StockItem:
        """添加库存项"""
        with self._lock:
            if sku in self._items:
                raise ValueError(f"SKU {sku} already exists")

            item = StockItem(
                sku=sku,
                name=name,
                quantity=quantity,
                reorder_level=reorder_level,
                location=location,
                metadata=metadata or {}
            )
            self._items[sku] = item
            self._logger.info(f"Stock item added: {sku}, quantity: {quantity}")
            return item

    def get_item(self, sku: str) -> Optional[StockItem]:
        """获取库存项"""
        with self._lock:
            return self._items.get(sku)

    def update_quantity(self, sku: str, quantity: int) -> bool:
        """更新库存数量"""
        with self._lock:
            item = self._items.get(sku)
            if not item:
                return False

            item.quantity = quantity
            self._logger.info(f"Stock updated: {sku}, quantity: {quantity}")
            return True

    def increase_stock(self, sku: str, amount: int) -> bool:
        """增加库存"""
        with self._lock:
            item = self._items.get(sku)
            if not item:
                return False

            item.quantity += amount
            self._logger.info(f"Stock increased: {sku}, +{amount}")
            return True

    def decrease_stock(self, sku: str, amount: int) -> bool:
        """减少库存"""
        with self._lock:
            item = self._items.get(sku)
            if not item:
                return False

            if item.available < amount:
                return False

            item.quantity -= amount
            self._logger.info(f"Stock decreased: {sku}, -{amount}")
            return True

    def reserve_stock(self, sku: str, amount: int) -> bool:
        """预留库存"""
        with self._lock:
            item = self._items.get(sku)
            if not item:
                return False

            if item.available < amount:
                return False

            item.reserved += amount
            return True

    def release_reservation(self, sku: str, amount: int) -> bool:
        """释放预留"""
        with self._lock:
            item = self._items.get(sku)
            if not item:
                return False

            item.reserved = max(0, item.reserved - amount)
            return True

    def transfer_stock(self, sku: str, from_location: str,
                       to_location: str, amount: int) -> bool:
        """调拨库存"""
        with self._lock:
            item = self._items.get(sku)
            if not item or item.location != from_location:
                return False

            if item.quantity < amount:
                return False

            item.quantity -= amount

            # 创建或更新目标位置的库存
            target_sku = f"{sku}@{to_location}"
            if target_sku in self._items:
                self._items[target_sku].quantity += amount
            else:
                new_item = StockItem(
                    sku=target_sku,
                    name=item.name,
                    quantity=amount,
                    reorder_level=item.reorder_level,
                    location=to_location
                )
                self._items[target_sku] = new_item

            self._logger.info(f"Stock transferred: {sku} from {from_location} to {to_location}")
            return True

    def check_stock(self, sku: str) -> Optional[Dict[str, Any]]:
        """检查库存状态"""
        with self._lock:
            item = self._items.get(sku)
            if not item:
                return None
            return item.to_dict()

    def get_low_stock_items(self) -> List[StockItem]:
        """获取低库存项"""
        with self._lock:
            return [
                item for item in self._items.values()
                if item.status == StockStatus.LOW_STOCK
            ]

    def get_out_of_stock_items(self) -> List[StockItem]:
        """获取缺货项"""
        with self._lock:
            return [
                item for item in self._items.values()
                if item.status == StockStatus.OUT_OF_STOCK
            ]

    def list_items(self, location: Optional[str] = None) -> List[StockItem]:
        """列出库存项"""
        with self._lock:
            items = list(self._items.values())
            if location:
                items = [i for i in items if i.location == location]
            return items

    def delete_item(self, sku: str) -> bool:
        """删除库存项"""
        with self._lock:
            if sku in self._items:
                del self._items[sku]
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_items = len(self._items)
            total_quantity = sum(i.quantity for i in self._items.values())
            total_reserved = sum(i.reserved for i in self._items.values())
            low_stock = len(self.get_low_stock_items())
            out_of_stock = len(self.get_out_of_stock_items())

            return {
                "total_items": total_items,
                "total_quantity": total_quantity,
                "total_reserved": total_reserved,
                "low_stock_count": low_stock,
                "out_of_stock_count": out_of_stock
            }


# 全局实例
_manager: Optional[InventoryManager] = None


def get_inventory_manager() -> InventoryManager:
    """获取全局库存管理器"""
    global _manager
    if _manager is None:
        _manager = InventoryManager()
    return _manager
