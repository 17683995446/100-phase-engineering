"""
分布式事务管理器
提供两阶段提交(2PC)、Saga模式和TCC模式支持
"""
import time
import threading
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from src.utils.structured_logging import get_logger


class TransactionStatus(Enum):
    """事务状态"""
    PENDING = "pending"
    PREPARING = "preparing"
    PREPARED = "prepared"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ABORTING = "aborting"
    ABORTED = "aborted"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class ParticipantStatus(Enum):
    """参与者状态"""
    IDLE = "idle"
    PREPARED = "prepared"
    COMMITTED = "committed"
    ABORTED = "aborted"
    COMPENSATED = "compensated"


@dataclass
class TransactionParticipant:
    """事务参与者"""
    participant_id: str
    prepare: Callable[[], bool]
    commit: Callable[[], bool]
    rollback: Callable[[], bool]
    compensate: Optional[Callable[[], bool]] = None
    status: ParticipantStatus = field(default=ParticipantStatus.IDLE)


@dataclass
class TransactionRecord:
    """事务记录"""
    tx_id: str
    status: TransactionStatus
    participants: List[TransactionParticipant]
    created_at: float
    completed_at: Optional[float] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "status": self.status.value,
            "participant_count": len(self.participants),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message
        }


class TwoPhaseCommit:
    """两阶段提交协调器"""

    def __init__(self):
        self._transactions: Dict[str, TransactionRecord] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("tx.2pc")

    def begin_transaction(self, participants: List[TransactionParticipant]) -> str:
        """开始事务"""
        tx_id = str(uuid.uuid4())
        record = TransactionRecord(
            tx_id=tx_id,
            status=TransactionStatus.PENDING,
            participants=participants,
            created_at=time.time()
        )
        with self._lock:
            self._transactions[tx_id] = record
        return tx_id

    def commit(self, tx_id: str) -> bool:
        """提交事务"""
        with self._lock:
            record = self._transactions.get(tx_id)
            if not record:
                return False

        # 阶段1: 准备
        record.status = TransactionStatus.PREPARING
        prepared = []
        for participant in record.participants:
            try:
                if participant.prepare():
                    participant.status = ParticipantStatus.PREPARED
                    prepared.append(participant)
                else:
                    record.error_message = f"Prepare failed for {participant.participant_id}"
                    break
            except Exception as e:
                record.error_message = f"Prepare exception for {participant.participant_id}: {e}"
                break

        # 如果有参与者准备失败，回滚
        if len(prepared) != len(record.participants):
            return self._rollback(record)

        record.status = TransactionStatus.PREPARED

        # 阶段2: 提交
        record.status = TransactionStatus.COMMITTING
        for participant in record.participants:
            try:
                if participant.commit():
                    participant.status = ParticipantStatus.COMMITTED
                else:
                    record.error_message = f"Commit failed for {participant.participant_id}"
                    # 已提交的无法回滚，记录错误
            except Exception as e:
                record.error_message = f"Commit exception for {participant.participant_id}: {e}"

        record.status = TransactionStatus.COMMITTED
        record.completed_at = time.time()
        return True

    def _rollback(self, record: TransactionRecord) -> bool:
        """回滚事务"""
        record.status = TransactionStatus.ABORTING
        for participant in record.participants:
            if participant.status == ParticipantStatus.PREPARED:
                try:
                    participant.rollback()
                    participant.status = ParticipantStatus.ABORTED
                except Exception as e:
                    self._logger.error(f"Rollback failed for {participant.participant_id}: {e}")
            else:
                participant.status = ParticipantStatus.ABORTED

        record.status = TransactionStatus.ABORTED
        record.completed_at = time.time()
        return False

    def get_transaction(self, tx_id: str) -> Optional[TransactionRecord]:
        """获取事务记录"""
        with self._lock:
            return self._transactions.get(tx_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._transactions)
            committed = sum(1 for t in self._transactions.values()
                          if t.status == TransactionStatus.COMMITTED)
            aborted = sum(1 for t in self._transactions.values()
                        if t.status == TransactionStatus.ABORTED)
            return {
                "total_transactions": total,
                "committed": committed,
                "aborted": aborted,
                "pending": total - committed - aborted
            }


class SagaOrchestrator:
    """Saga编排器"""

    def __init__(self):
        self._transactions: Dict[str, TransactionRecord] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("tx.saga")

    def execute(self, steps: List[TransactionParticipant]) -> str:
        """执行Saga事务"""
        tx_id = str(uuid.uuid4())
        record = TransactionRecord(
            tx_id=tx_id,
            status=TransactionStatus.PENDING,
            participants=steps,
            created_at=time.time()
        )
        with self._lock:
            self._transactions[tx_id] = record

        completed_steps = []

        # 顺序执行每个步骤
        for step in steps:
            try:
                if step.prepare():
                    step.status = ParticipantStatus.COMMITTED
                    completed_steps.append(step)
                else:
                    record.error_message = f"Step failed: {step.participant_id}"
                    break
            except Exception as e:
                record.error_message = f"Step exception: {step.participant_id}: {e}"
                break

        # 如果有步骤失败，执行补偿
        if len(completed_steps) != len(steps):
            record.status = TransactionStatus.COMPENSATING
            for step in reversed(completed_steps):
                if step.compensate:
                    try:
                        step.compensate()
                        step.status = ParticipantStatus.COMPENSATED
                    except Exception as e:
                        self._logger.error(f"Compensation failed for {step.participant_id}: {e}")
            record.status = TransactionStatus.COMPENSATED
            record.completed_at = time.time()
            return tx_id

        record.status = TransactionStatus.COMMITTED
        record.completed_at = time.time()
        return tx_id

    def get_transaction(self, tx_id: str) -> Optional[TransactionRecord]:
        """获取事务记录"""
        with self._lock:
            return self._transactions.get(tx_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._transactions)
            committed = sum(1 for t in self._transactions.values()
                          if t.status == TransactionStatus.COMMITTED)
            compensated = sum(1 for t in self._transactions.values()
                            if t.status == TransactionStatus.COMPENSATED)
            return {
                "total_transactions": total,
                "committed": committed,
                "compensated": compensated
            }


class TCCManager:
    """TCC (Try-Confirm-Cancel) 管理器"""

    def __init__(self):
        self._transactions: Dict[str, TransactionRecord] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("tx.tcc")

    def execute(self, participants: List[TransactionParticipant]) -> str:
        """执行TCC事务"""
        tx_id = str(uuid.uuid4())
        record = TransactionRecord(
            tx_id=tx_id,
            status=TransactionStatus.PENDING,
            participants=participants,
            created_at=time.time()
        )
        with self._lock:
            self._transactions[tx_id] = record

        # Try 阶段
        tried = []
        for participant in participants:
            try:
                if participant.prepare():  # Try
                    tried.append(participant)
                else:
                    record.error_message = f"Try failed: {participant.participant_id}"
                    break
            except Exception as e:
                record.error_message = f"Try exception: {participant.participant_id}: {e}"
                break

        # 如果有Try失败，执行Cancel
        if len(tried) != len(participants):
            record.status = TransactionStatus.ABORTING
            for participant in tried:
                try:
                    participant.rollback()  # Cancel
                    participant.status = ParticipantStatus.ABORTED
                except Exception as e:
                    self._logger.error(f"Cancel failed: {e}")
            record.status = TransactionStatus.ABORTED
            record.completed_at = time.time()
            return tx_id

        # Confirm 阶段
        record.status = TransactionStatus.COMMITTING
        for participant in participants:
            try:
                participant.commit()  # Confirm
                participant.status = ParticipantStatus.COMMITTED
            except Exception as e:
                self._logger.error(f"Confirm failed: {e}")

        record.status = TransactionStatus.COMMITTED
        record.completed_at = time.time()
        return tx_id

    def get_transaction(self, tx_id: str) -> Optional[TransactionRecord]:
        """获取事务记录"""
        with self._lock:
            return self._transactions.get(tx_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._transactions)
            committed = sum(1 for t in self._transactions.values()
                          if t.status == TransactionStatus.COMMITTED)
            aborted = sum(1 for t in self._transactions.values()
                        if t.status == TransactionStatus.ABORTED)
            return {
                "total_transactions": total,
                "committed": committed,
                "aborted": aborted
            }


# 全局实例
_2pc: Optional[TwoPhaseCommit] = None
_saga: Optional[SagaOrchestrator] = None
_tcc: Optional[TCCManager] = None


def get_two_phase_commit() -> TwoPhaseCommit:
    """获取全局2PC协调器"""
    global _2pc
    if _2pc is None:
        _2pc = TwoPhaseCommit()
    return _2pc


def get_saga_orchestrator() -> SagaOrchestrator:
    """获取全局Saga编排器"""
    global _saga
    if _saga is None:
        _saga = SagaOrchestrator()
    return _saga


def get_tcc_manager() -> TCCManager:
    """获取全局TCC管理器"""
    global _tcc
    if _tcc is None:
        _tcc = TCCManager()
    return _tcc
