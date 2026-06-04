"""
订单管理系统
提供订单创建、状态流转、取消和查询功能
"""
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class OrderStatus(Enum):
    """订单状态"""
    CREATED = "created"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class OrderItem:
    """订单项"""
    item_id: str
    name: str
    quantity: int
    unit_price: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "metadata": self.metadata
        }


@dataclass
class Order:
    """订单"""
    order_id: str
    user_id: str
    items: List[OrderItem]
    status: OrderStatus
    total_amount: float
    currency: str
    created_at: float
    updated_at: float
    shipping_address: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "status": self.status.value,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "shipping_address": self.shipping_address,
            "metadata": self.metadata
        }


class OrderManager:
    """订单管理器"""

    def __init__(self):
        self._orders: Dict[str, Order] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("order.manager")

    def create_order(self, order_id: str, user_id: str,
                     items: List[OrderItem], currency: str = "USD",
                     shipping_address: Optional[Dict[str, Any]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Order:
        """创建订单"""
        with self._lock:
            if order_id in self._orders:
                raise ValueError(f"Order {order_id} already exists")

            total = sum(item.total_price for item in items)
            now = time.time()

            order = Order(
                order_id=order_id,
                user_id=user_id,
                items=items,
                status=OrderStatus.CREATED,
                total_amount=total,
                currency=currency,
                created_at=now,
                updated_at=now,
                shipping_address=shipping_address or {},
                metadata=metadata or {}
            )

            self._orders[order_id] = order
            self._logger.info(f"Order created: {order_id}, amount: {total}")
            return order

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        with self._lock:
            return self._orders.get(order_id)

    def update_status(self, order_id: str, status: OrderStatus) -> bool:
        """更新订单状态"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                return False

            order.status = status
            order.updated_at = time.time()
            self._logger.info(f"Order {order_id} status updated to {status.value}")
            return True

    def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """取消订单"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                return False

            if order.status in (OrderStatus.COMPLETED, OrderStatus.REFUNDED):
                return False

            order.status = OrderStatus.CANCELLED
            order.updated_at = time.time()
            order.metadata["cancel_reason"] = reason
            self._logger.info(f"Order {order_id} cancelled: {reason}")
            return True

    def add_item(self, order_id: str, item: OrderItem) -> bool:
        """添加订单项"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order or order.status != OrderStatus.CREATED:
                return False

            order.items.append(item)
            order.total_amount += item.total_price
            order.updated_at = time.time()
            return True

    def remove_item(self, order_id: str, item_id: str) -> bool:
        """移除订单项"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order or order.status != OrderStatus.CREATED:
                return False

            for i, item in enumerate(order.items):
                if item.item_id == item_id:
                    order.total_amount -= item.total_price
                    order.items.pop(i)
                    order.updated_at = time.time()
                    return True
            return False

    def list_orders(self, user_id: Optional[str] = None,
                    status: Optional[OrderStatus] = None) -> List[Order]:
        """列出订单"""
        with self._lock:
            orders = list(self._orders.values())
            if user_id:
                orders = [o for o in orders if o.user_id == user_id]
            if status:
                orders = [o for o in orders if o.status == status]
            return orders

    def get_user_orders(self, user_id: str) -> List[Order]:
        """获取用户的所有订单"""
        return self.list_orders(user_id=user_id)

    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """获取订单历史（简化版）"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                return []
            return [{
                "status": order.status.value,
                "timestamp": order.updated_at
            }]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._orders)
            by_status = {}
            for order in self._orders.values():
                status = order.status.value
                by_status[status] = by_status.get(status, 0) + 1

            total_revenue = sum(
                o.total_amount for o in self._orders.values()
                if o.status in (OrderStatus.PAID, OrderStatus.COMPLETED)
            )

            return {
                "total_orders": total,
                "by_status": by_status,
                "total_revenue": total_revenue
            }


# 全局实例
_manager: Optional[OrderManager] = None


def get_order_manager() -> OrderManager:
    """获取全局订单管理器"""
    global _manager
    if _manager is None:
        _manager = OrderManager()
    return _manager
