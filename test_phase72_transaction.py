"""
Phase 72 - 分布式事务管理器测试
验证两阶段提交(2PC)、Saga模式和TCC模式
"""
import unittest
from src.utils.distributed_transaction import (
    TwoPhaseCommit,
    SagaOrchestrator,
    TCCManager,
    TransactionParticipant,
    TransactionStatus,
    ParticipantStatus,
    get_two_phase_commit,
    get_saga_orchestrator,
    get_tcc_manager
)


class TestTwoPhaseCommit(unittest.TestCase):
    """两阶段提交测试"""

    def setUp(self):
        self.tx = TwoPhaseCommit()

    def test_commit_success(self):
        """测试成功提交"""
        participants = [
            TransactionParticipant("p1", lambda: True, lambda: True, lambda: True),
            TransactionParticipant("p2", lambda: True, lambda: True, lambda: True)
        ]
        tx_id = self.tx.begin_transaction(participants)
        result = self.tx.commit(tx_id)
        self.assertTrue(result)

        record = self.tx.get_transaction(tx_id)
        self.assertEqual(record.status, TransactionStatus.COMMITTED)

    def test_commit_prepare_failure(self):
        """测试准备阶段失败"""
        participants = [
            TransactionParticipant("p1", lambda: True, lambda: True, lambda: True),
            TransactionParticipant("p2", lambda: False, lambda: True, lambda: True)
        ]
        tx_id = self.tx.begin_transaction(participants)
        result = self.tx.commit(tx_id)
        self.assertFalse(result)

        record = self.tx.get_transaction(tx_id)
        self.assertEqual(record.status, TransactionStatus.ABORTED)

    def test_stats(self):
        """测试统计信息"""
        participants = [
            TransactionParticipant("p1", lambda: True, lambda: True, lambda: True)
        ]
        tx_id = self.tx.begin_transaction(participants)
        self.tx.commit(tx_id)

        stats = self.tx.get_stats()
        self.assertEqual(stats["committed"], 1)


class TestSagaOrchestrator(unittest.TestCase):
    """Saga编排器测试"""

    def setUp(self):
        self.saga = SagaOrchestrator()

    def test_saga_success(self):
        """测试Saga成功执行"""
        steps = [
            TransactionParticipant("s1", lambda: True, lambda: True, lambda: True),
            TransactionParticipant("s2", lambda: True, lambda: True, lambda: True)
        ]
        tx_id = self.saga.execute(steps)
        record = self.saga.get_transaction(tx_id)
        self.assertEqual(record.status, TransactionStatus.COMMITTED)

    def test_saga_compensation(self):
        """测试Saga补偿"""
        compensated = []
        steps = [
            TransactionParticipant(
                "s1", lambda: True, lambda: True, lambda: True,
                compensate=lambda: compensated.append("s1") or True
            ),
            TransactionParticipant(
                "s2", lambda: True, lambda: True, lambda: True,
                compensate=lambda: compensated.append("s2") or True
            ),
            TransactionParticipant("s3", lambda: False, lambda: True, lambda: True)
        ]
        tx_id = self.saga.execute(steps)
        record = self.saga.get_transaction(tx_id)
        self.assertEqual(record.status, TransactionStatus.COMPENSATED)
        self.assertEqual(len(compensated), 2)

    def test_stats(self):
        """测试统计信息"""
        steps = [TransactionParticipant("s1", lambda: True, lambda: True, lambda: True)]
        self.saga.execute(steps)
        stats = self.saga.get_stats()
        self.assertEqual(stats["committed"], 1)


class TestTCCManager(unittest.TestCase):
    """TCC管理器测试"""

    def setUp(self):
        self.tcc = TCCManager()

    def test_tcc_success(self):
        """测试TCC成功"""
        participants = [
            TransactionParticipant("p1", lambda: True, lambda: True, lambda: True),
            TransactionParticipant("p2", lambda: True, lambda: True, lambda: True)
        ]
        tx_id = self.tcc.execute(participants)
        record = self.tcc.get_transaction(tx_id)
        self.assertEqual(record.status, TransactionStatus.COMMITTED)

    def test_tcc_try_failure(self):
        """测试Try阶段失败"""
        participants = [
            TransactionParticipant("p1", lambda: True, lambda: True, lambda: True),
            TransactionParticipant("p2", lambda: False, lambda: True, lambda: True)
        ]
        tx_id = self.tcc.execute(participants)
        record = self.tcc.get_transaction(tx_id)
        self.assertEqual(record.status, TransactionStatus.ABORTED)

    def test_stats(self):
        """测试统计信息"""
        participants = [TransactionParticipant("p1", lambda: True, lambda: True, lambda: True)]
        self.tcc.execute(participants)
        stats = self.tcc.get_stats()
        self.assertEqual(stats["committed"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_two_phase_commit(self):
        """测试获取全局2PC"""
        t1 = get_two_phase_commit()
        t2 = get_two_phase_commit()
        self.assertIs(t1, t2)

    def test_get_saga_orchestrator(self):
        """测试获取全局Saga"""
        s1 = get_saga_orchestrator()
        s2 = get_saga_orchestrator()
        self.assertIs(s1, s2)

    def test_get_tcc_manager(self):
        """测试获取全局TCC"""
        t1 = get_tcc_manager()
        t2 = get_tcc_manager()
        self.assertIs(t1, t2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 72 - 分布式事务管理器测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTwoPhaseCommit))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSagaOrchestrator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTCCManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalInstance))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run_tests()
