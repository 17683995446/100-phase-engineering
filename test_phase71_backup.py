"""
Phase 71 - 数据备份与恢复系统测试
验证备份、恢复、归档和快照功能
"""
import os
import json
import tempfile
import shutil
import unittest
from src.utils.backup import (
    BackupManager,
    SnapshotManager,
    ChecksumCalculator,
    get_backup_manager,
    get_snapshot_manager
)


class TestChecksumCalculator(unittest.TestCase):
    """校验和计算器测试"""

    def test_calculate_string(self):
        """测试字符串校验和"""
        calc = ChecksumCalculator()
        checksum1 = calc.calculate_string("hello")
        checksum2 = calc.calculate_string("hello")
        self.assertEqual(checksum1, checksum2)
        self.assertEqual(len(checksum1), 32)

    def test_calculate_file(self):
        """测试文件校验和"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            calc = ChecksumCalculator()
            checksum = calc.calculate_file(temp_path)
            self.assertEqual(len(checksum), 32)
        finally:
            os.unlink(temp_path)


class TestBackupManager(unittest.TestCase):
    """备份管理器测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.manager = BackupManager(backup_dir=self.backup_dir)

        # 创建测试目录
        self.source_dir = os.path.join(self.temp_dir, "source")
        os.makedirs(self.source_dir)
        with open(os.path.join(self.source_dir, "file1.txt"), "w") as f:
            f.write("content1")
        with open(os.path.join(self.source_dir, "file2.txt"), "w") as f:
            f.write("content2")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_backup_directory(self):
        """测试备份目录"""
        info = self.manager.backup_directory(self.source_dir, backup_id="test1")
        self.assertIsNotNone(info)
        self.assertEqual(info.backup_id, "test1")
        self.assertTrue(os.path.exists(info.backup_path))

    def test_backup_nonexistent(self):
        """测试备份不存在的目录"""
        info = self.manager.backup_directory("/nonexistent/path")
        self.assertIsNone(info)

    def test_restore(self):
        """测试恢复备份"""
        self.manager.backup_directory(self.source_dir, backup_id="test_restore")

        restore_dir = os.path.join(self.temp_dir, "restored")
        result = self.manager.restore("test_restore", restore_dir)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(os.path.join(restore_dir, "source", "file1.txt")))

    def test_verify(self):
        """测试验证备份"""
        self.manager.backup_directory(self.source_dir, backup_id="test_verify")
        self.assertTrue(self.manager.verify("test_verify"))

    def test_delete_backup(self):
        """测试删除备份"""
        info = self.manager.backup_directory(self.source_dir, backup_id="test_delete")
        result = self.manager.delete_backup("test_delete")
        self.assertTrue(result)
        self.assertFalse(os.path.exists(info.backup_path))

    def test_list_backups(self):
        """测试列出备份"""
        self.manager.backup_directory(self.source_dir, backup_id="test_list1")
        self.manager.backup_directory(self.source_dir, backup_id="test_list2")
        backups = self.manager.list_backups()
        self.assertEqual(len(backups), 2)

    def test_get_backup(self):
        """测试获取备份信息"""
        self.manager.backup_directory(self.source_dir, backup_id="test_get")
        info = self.manager.get_backup("test_get")
        self.assertIsNotNone(info)
        self.assertEqual(info.backup_id, "test_get")

    def test_cleanup_old_backups(self):
        """测试清理旧备份"""
        info = self.manager.backup_directory(self.source_dir, backup_id="test_old")
        # 修改创建时间为很久以前
        info.created_at = 0
        removed = self.manager.cleanup_old_backups(max_age_days=1)
        self.assertEqual(removed, 1)

    def test_stats(self):
        """测试统计信息"""
        self.manager.backup_directory(self.source_dir, backup_id="test_stats")
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_backups"], 1)
        self.assertGreater(stats["total_size_bytes"], 0)


class TestSnapshotManager(unittest.TestCase):
    """快照管理器测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.snapshot_dir = os.path.join(self.temp_dir, "snapshots")
        self.manager = SnapshotManager(snapshot_dir=self.snapshot_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_restore_snapshot(self):
        """测试创建和恢复快照"""
        data = {"key": "value", "nested": {"a": 1}}
        snapshot_id = self.manager.create_snapshot(data, snapshot_id="test1")
        self.assertEqual(snapshot_id, "test1")

        restored = self.manager.restore_snapshot("test1")
        self.assertIsNotNone(restored)
        self.assertEqual(restored["key"], "value")
        self.assertEqual(restored["nested"]["a"], 1)

    def test_list_snapshots(self):
        """测试列出快照"""
        self.manager.create_snapshot({"a": 1}, snapshot_id="snap1")
        self.manager.create_snapshot({"b": 2}, snapshot_id="snap2")
        snapshots = self.manager.list_snapshots()
        self.assertEqual(len(snapshots), 2)

    def test_delete_snapshot(self):
        """测试删除快照"""
        self.manager.create_snapshot({"a": 1}, snapshot_id="snap_del")
        result = self.manager.delete_snapshot("snap_del")
        self.assertTrue(result)
        self.assertEqual(len(self.manager.list_snapshots()), 0)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_backup_manager(self):
        """测试获取全局备份管理器"""
        b1 = get_backup_manager()
        b2 = get_backup_manager()
        self.assertIs(b1, b2)

    def test_get_snapshot_manager(self):
        """测试获取全局快照管理器"""
        s1 = get_snapshot_manager()
        s2 = get_snapshot_manager()
        self.assertIs(s1, s2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 71 - 数据备份与恢复系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestChecksumCalculator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBackupManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSnapshotManager))
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
