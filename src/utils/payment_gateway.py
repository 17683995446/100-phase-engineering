"""
支付网关系统
提供支付处理、退款、对账和支付渠道管理功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class PaymentStatus(Enum):
    """支付状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"


class PaymentMethod(Enum):
    """支付方式"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"


@dataclass
class PaymentRequest:
    """支付请求"""
    order_id: str
    amount: float
    currency: str
    method: PaymentMethod
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "amount": self.amount,
            "currency": self.currency,
            "method": self.method.value,
            "description": self.description,
            "metadata": self.metadata
        }


@dataclass
class PaymentResult:
    """支付结果"""
    transaction_id: str
    order_id: str
    status: PaymentStatus
    amount: float
    currency: str
    method: PaymentMethod
    timestamp: float
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "order_id": self.order_id,
            "status": self.status.value,
            "amount": self.amount,
            "currency": self.currency,
            "method": self.method.value,
            "timestamp": self.timestamp,
            "message": self.message,
            "metadata": self.metadata
        }


@dataclass
class RefundRequest:
    """退款请求"""
    transaction_id: str
    amount: float
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "amount": self.amount,
            "reason": self.reason
        }


class PaymentProcessor:
    """支付处理器"""

    def __init__(self, name: str):
        self._name = name
        self._logger = get_logger(f"payment.processor.{name}")

    def process(self, request: PaymentRequest) -> PaymentResult:
        """处理支付"""
        raise NotImplementedError

    def refund(self, transaction_id: str, amount: float) -> PaymentResult:
        """处理退款"""
        raise NotImplementedError

    def query(self, transaction_id: str) -> Optional[PaymentResult]:
        """查询支付状态"""
        raise NotImplementedError


class MockPaymentProcessor(PaymentProcessor):
    """模拟支付处理器"""

    def __init__(self, name: str, success_rate: float = 1.0):
        super().__init__(name)
        self._success_rate = success_rate
        self._transactions: Dict[str, PaymentResult] = {}
        self._lock = threading.RLock()
        self._counter = 0

    def _generate_id(self) -> str:
        """生成交易ID"""
        with self._lock:
            self._counter += 1
            return f"TXN_{self._name}_{int(time.time())}_{self._counter}"

    def process(self, request: PaymentRequest) -> PaymentResult:
        """处理支付"""
        import random
        transaction_id = self._generate_id()

        if random.random() <= self._success_rate:
            status = PaymentStatus.SUCCESS
            message = "Payment successful"
        else:
            status = PaymentStatus.FAILED
            message = "Payment failed"

        result = PaymentResult(
            transaction_id=transaction_id,
            order_id=request.order_id,
            status=status,
            amount=request.amount,
            currency=request.currency,
            method=request.method,
            timestamp=time.time(),
            message=message
        )

        with self._lock:
            self._transactions[transaction_id] = result

        self._logger.info(f"Payment {transaction_id}: {status.value}")
        return result

    def refund(self, transaction_id: str, amount: float) -> PaymentResult:
        """处理退款"""
        with self._lock:
            original = self._transactions.get(transaction_id)
            if not original:
                return PaymentResult(
                    transaction_id=transaction_id,
                    order_id="",
                    status=PaymentStatus.FAILED,
                    amount=amount,
                    currency="",
                    method=PaymentMethod.CREDIT_CARD,
                    timestamp=time.time(),
                    message="Transaction not found"
                )

            if amount > original.amount:
                return PaymentResult(
                    transaction_id=transaction_id,
                    order_id=original.order_id,
                    status=PaymentStatus.FAILED,
                    amount=amount,
                    currency=original.currency,
                    method=original.method,
                    timestamp=time.time(),
                    message="Refund amount exceeds original"
                )

            refund_id = self._generate_id()
            result = PaymentResult(
                transaction_id=refund_id,
                order_id=original.order_id,
                status=PaymentStatus.REFUNDED,
                amount=amount,
                currency=original.currency,
                method=original.method,
                timestamp=time.time(),
                message="Refund successful"
            )
            self._transactions[refund_id] = result

            # 更新原交易状态
            if amount == original.amount:
                original.status = PaymentStatus.REFUNDED
            else:
                original.status = PaymentStatus.PARTIALLY_REFUNDED

            return result

    def query(self, transaction_id: str) -> Optional[PaymentResult]:
        """查询支付状态"""
        with self._lock:
            return self._transactions.get(transaction_id)

    def get_transactions(self) -> List[PaymentResult]:
        """获取所有交易"""
        with self._lock:
            return list(self._transactions.values())


class PaymentGateway:
    """支付网关"""

    def __init__(self):
        self._processors: Dict[PaymentMethod, PaymentProcessor] = {}
        self._transactions: Dict[str, PaymentResult] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("payment.gateway")

    def register_processor(self, method: PaymentMethod,
                           processor: PaymentProcessor) -> None:
        """注册支付处理器"""
        with self._lock:
            self._processors[method] = processor

    def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """处理支付"""
        with self._lock:
            processor = self._processors.get(request.method)
            if not processor:
                return PaymentResult(
                    transaction_id="",
                    order_id=request.order_id,
                    status=PaymentStatus.FAILED,
                    amount=request.amount,
                    currency=request.currency,
                    method=request.method,
                    timestamp=time.time(),
                    message=f"No processor for method: {request.method.value}"
                )

        result = processor.process(request)

        with self._lock:
            self._transactions[result.transaction_id] = result

        return result

    def refund(self, transaction_id: str, amount: float,
               reason: str = "") -> PaymentResult:
        """处理退款"""
        with self._lock:
            original = self._transactions.get(transaction_id)
            if not original:
                return PaymentResult(
                    transaction_id=transaction_id,
                    order_id="",
                    status=PaymentStatus.FAILED,
                    amount=amount,
                    currency="",
                    method=PaymentMethod.CREDIT_CARD,
                    timestamp=time.time(),
                    message="Transaction not found"
                )

            processor = self._processors.get(original.method)
            if not processor:
                return PaymentResult(
                    transaction_id=transaction_id,
                    order_id=original.order_id,
                    status=PaymentStatus.FAILED,
                    amount=amount,
                    currency=original.currency,
                    method=original.method,
                    timestamp=time.time(),
                    message="Processor not available"
                )

        return processor.refund(transaction_id, amount)

    def query_transaction(self, transaction_id: str) -> Optional[PaymentResult]:
        """查询交易"""
        with self._lock:
            return self._transactions.get(transaction_id)

    def get_transactions_by_order(self, order_id: str) -> List[PaymentResult]:
        """获取订单的所有交易"""
        with self._lock:
            return [
                t for t in self._transactions.values()
                if t.order_id == order_id
            ]

    def reconcile(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """对账"""
        with self._lock:
            transactions = [
                t for t in self._transactions.values()
                if start_time <= t.timestamp <= end_time
            ]

            total_amount = sum(t.amount for t in transactions
                              if t.status == PaymentStatus.SUCCESS)
            refund_amount = sum(t.amount for t in transactions
                               if t.status == PaymentStatus.REFUNDED)
            success_count = sum(1 for t in transactions
                               if t.status == PaymentStatus.SUCCESS)
            failed_count = sum(1 for t in transactions
                              if t.status == PaymentStatus.FAILED)

            return {
                "period": f"{start_time} - {end_time}",
                "total_transactions": len(transactions),
                "success_count": success_count,
                "failed_count": failed_count,
                "total_amount": total_amount,
                "refund_amount": refund_amount,
                "net_amount": total_amount - refund_amount
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "registered_processors": len(self._processors),
                "total_transactions": len(self._transactions)
            }


# 全局实例
_gateway: Optional[PaymentGateway] = None


def get_payment_gateway() -> PaymentGateway:
    """获取全局支付网关"""
    global _gateway
    if _gateway is None:
        _gateway = PaymentGateway()
    return _gateway
