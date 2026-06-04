"""
购物车系统
提供添加商品、修改数量、结算和持久化功能
"""
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class CartStatus(Enum):
    """购物车状态"""
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


@dataclass
class CartItem:
    """购物车项"""
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
class ShoppingCart:
    """购物车"""
    cart_id: str
    user_id: str
    items: List[CartItem] = field(default_factory=list)
    status: CartStatus = CartStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_amount(self) -> float:
        return sum(item.total_price for item in self.items)

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def unique_items(self) -> int:
        return len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cart_id": self.cart_id,
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "status": self.status.value,
            "total_amount": self.total_amount,
            "total_items": self.total_items,
            "unique_items": self.unique_items,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class CartManager:
    """购物车管理器"""

    def __init__(self):
        self._carts: Dict[str, ShoppingCart] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("cart.manager")

    def create_cart(self, cart_id: str, user_id: str,
                    metadata: Optional[Dict[str, Any]] = None) -> ShoppingCart:
        """创建购物车"""
        with self._lock:
            if cart_id in self._carts:
                raise ValueError(f"Cart {cart_id} already exists")

            cart = ShoppingCart(
                cart_id=cart_id,
                user_id=user_id,
                metadata=metadata or {}
            )
            self._carts[cart_id] = cart
            self._logger.info(f"Cart created: {cart_id}")
            return cart

    def get_cart(self, cart_id: str) -> Optional[ShoppingCart]:
        """获取购物车"""
        with self._lock:
            return self._carts.get(cart_id)

    def add_item(self, cart_id: str, item: CartItem) -> bool:
        """添加商品"""
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart or cart.status != CartStatus.ACTIVE:
                return False

            # 检查是否已存在
            for existing in cart.items:
                if existing.item_id == item.item_id:
                    existing.quantity += item.quantity
                    cart.updated_at = time.time()
                    return True

            cart.items.append(item)
            cart.updated_at = time.time()
            return True

    def update_quantity(self, cart_id: str, item_id: str,
                        quantity: int) -> bool:
        """更新商品数量"""
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart or cart.status != CartStatus.ACTIVE:
                return False

            for item in cart.items:
                if item.item_id == item_id:
                    if quantity <= 0:
                        cart.items.remove(item)
                    else:
                        item.quantity = quantity
                    cart.updated_at = time.time()
                    return True
            return False

    def remove_item(self, cart_id: str, item_id: str) -> bool:
        """移除商品"""
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart or cart.status != CartStatus.ACTIVE:
                return False

            for i, item in enumerate(cart.items):
                if item.item_id == item_id:
                    cart.items.pop(i)
                    cart.updated_at = time.time()
                    return True
            return False

    def clear_cart(self, cart_id: str) -> bool:
        """清空购物车"""
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart:
                return False

            cart.items.clear()
            cart.updated_at = time.time()
            return True

    def checkout(self, cart_id: str) -> Optional[ShoppingCart]:
        """结算购物车"""
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart or cart.status != CartStatus.ACTIVE:
                return None

            if not cart.items:
                return None

            cart.status = CartStatus.CHECKED_OUT
            cart.updated_at = time.time()
            self._logger.info(f"Cart checked out: {cart_id}, amount: {cart.total_amount}")
            return cart

    def abandon_cart(self, cart_id: str) -> bool:
        """放弃购物车"""
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart or cart.status != CartStatus.ACTIVE:
                return False

            cart.status = CartStatus.ABANDONED
            cart.updated_at = time.time()
            return True

    def get_user_carts(self, user_id: str,
                       status: Optional[CartStatus] = None) -> List[ShoppingCart]:
        """获取用户的购物车"""
        with self._lock:
            carts = [c for c in self._carts.values() if c.user_id == user_id]
            if status:
                carts = [c for c in carts if c.status == status]
            return carts

    def merge_carts(self, source_cart_id: str,
                    target_cart_id: str) -> bool:
        """合并购物车"""
        with self._lock:
            source = self._carts.get(source_cart_id)
            target = self._carts.get(target_cart_id)

            if not source or not target:
                return False
            if target.status != CartStatus.ACTIVE:
                return False

            for source_item in source.items:
                found = False
                for target_item in target.items:
                    if target_item.item_id == source_item.item_id:
                        target_item.quantity += source_item.quantity
                        found = True
                        break
                if not found:
                    target.items.append(source_item)

            target.updated_at = time.time()
            return True

    def list_carts(self, status: Optional[CartStatus] = None) -> List[ShoppingCart]:
        """列出购物车"""
        with self._lock:
            carts = list(self._carts.values())
            if status:
                carts = [c for c in carts if c.status == status]
            return carts

    def delete_cart(self, cart_id: str) -> bool:
        """删除购物车"""
        with self._lock:
            if cart_id in self._carts:
                del self._carts[cart_id]
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._carts)
            active = sum(1 for c in self._carts.values()
                        if c.status == CartStatus.ACTIVE)
            checked_out = sum(1 for c in self._carts.values()
                             if c.status == CartStatus.CHECKED_OUT)
            abandoned = sum(1 for c in self._carts.values()
                           if c.status == CartStatus.ABANDONED)

            total_value = sum(
                c.total_amount for c in self._carts.values()
                if c.status == CartStatus.ACTIVE
            )

            return {
                "total_carts": total,
                "active": active,
                "checked_out": checked_out,
                "abandoned": abandoned,
                "total_active_value": total_value
            }


# 全局实例
_manager: Optional[CartManager] = None


def get_cart_manager() -> CartManager:
    """获取全局购物车管理器"""
    global _manager
    if _manager is None:
        _manager = CartManager()
    return _manager
