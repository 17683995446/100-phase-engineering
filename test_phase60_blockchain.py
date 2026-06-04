"""
Phase 60 - 区块链基础组件测试
验证区块、链、哈希和基本共识功能是否正常工作
"""
import unittest
from src.utils.blockchain import (
    Blockchain,
    Block,
    Transaction,
    get_blockchain
)


class TestTransaction(unittest.TestCase):
    """交易测试"""

    def test_transaction_creation(self):
        """测试交易创建"""
        tx = Transaction("tx1", "addr1", "addr2", 10.0)
        self.assertEqual(tx.tx_id, "tx1")
        self.assertEqual(tx.from_addr, "addr1")
        self.assertEqual(tx.to_addr, "addr2")
        self.assertEqual(tx.amount, 10.0)

    def test_transaction_hash(self):
        """测试交易哈希"""
        tx = Transaction("tx1", "addr1", "addr2", 10.0)
        hash1 = tx.hash()
        hash2 = tx.hash()
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)


class TestBlock(unittest.TestCase):
    """区块测试"""

    def test_block_creation(self):
        """测试区块创建"""
        block = Block(0, 1234567890, [], "0")
        self.assertEqual(block.index, 0)
        self.assertEqual(block.previous_hash, "0")

    def test_block_hash(self):
        """测试区块哈希"""
        block = Block(1, 1234567890, [], "prev_hash")
        block.hash = block.calculate_hash()
        self.assertEqual(len(block.hash), 64)

    def test_mine(self):
        """测试挖矿"""
        block = Block(1, 1234567890, [], "prev_hash")
        block.mine(difficulty=2)
        self.assertTrue(block.hash.startswith("00"))


class TestBlockchain(unittest.TestCase):
    """区块链测试"""

    def setUp(self):
        """测试前设置"""
        self.blockchain = Blockchain(difficulty=1)

    def test_genesis_block(self):
        """测试创世区块"""
        self.assertEqual(len(self.blockchain.chain), 1)
        self.assertEqual(self.blockchain.chain[0].index, 0)
        self.assertEqual(self.blockchain.chain[0].previous_hash, "0")

    def test_add_transaction(self):
        """测试添加交易"""
        tx = Transaction("tx1", "addr1", "addr2", 5.0)
        result = self.blockchain.add_transaction(tx)
        self.assertTrue(result)
        self.assertEqual(len(self.blockchain.pending_transactions), 1)

    def test_mine_block(self):
        """测试挖矿"""
        tx = Transaction("tx1", "addr1", "addr2", 5.0)
        self.blockchain.add_transaction(tx)
        block = self.blockchain.mine_pending_transactions("miner1")

        self.assertEqual(block.index, 1)
        self.assertEqual(len(self.blockchain.chain), 2)
        self.assertEqual(len(self.blockchain.pending_transactions), 0)

    def test_chain_validity(self):
        """测试链有效性"""
        self.assertTrue(self.blockchain.is_chain_valid())

    def test_chain_validity_after_mine(self):
        """测试挖矿后链有效性"""
        tx = Transaction("tx1", "addr1", "addr2", 5.0)
        self.blockchain.add_transaction(tx)
        self.blockchain.mine_pending_transactions("miner1")

        self.assertTrue(self.blockchain.is_chain_valid())

    def test_balance(self):
        """测试余额"""
        # 初始余额为0
        self.assertEqual(self.blockchain.get_balance("addr2"), 0.0)

        tx = Transaction("tx1", "addr1", "addr2", 5.0)
        self.blockchain.add_transaction(tx)
        self.blockchain.mine_pending_transactions("miner1")

        # addr2 收到 5.0，miner1 收到 1.0 奖励
        self.assertEqual(self.blockchain.get_balance("addr2"), 5.0)

    def test_get_block(self):
        """测试获取区块"""
        block = self.blockchain.get_block(0)
        self.assertIsNotNone(block)
        self.assertEqual(block.index, 0)

        nonexistent = self.blockchain.get_block(999)
        self.assertIsNone(nonexistent)

    def test_get_transaction(self):
        """测试获取交易"""
        tx = Transaction("tx1", "addr1", "addr2", 5.0)
        self.blockchain.add_transaction(tx)
        self.blockchain.mine_pending_transactions("miner1")

        found = self.blockchain.get_transaction("tx1")
        self.assertIsNotNone(found)
        self.assertEqual(found.amount, 5.0)

    def test_get_latest_block(self):
        """测试获取最新区块"""
        latest = self.blockchain.get_latest_block()
        self.assertEqual(latest.index, 0)

    def test_stats(self):
        """测试统计"""
        stats = self.blockchain.get_stats()
        self.assertEqual(stats["blocks"], 1)
        self.assertEqual(stats["difficulty"], 1)
        self.assertTrue(stats["is_valid"])


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_blockchain(self):
        """测试获取全局区块链"""
        b1 = get_blockchain()
        b2 = get_blockchain()
        self.assertIs(b1, b2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 60 - 区块链基础组件测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTransaction))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBlock))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBlockchain))
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
