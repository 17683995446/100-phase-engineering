"""
Phase 78 - 文件存储系统测试
验证文件上传、下载、分片、元数据管理和存储策略功能
"""
import os
import tempfile
import shutil
import unittest
from src.utils.file_storage import (
    FileStorage,
    ChunkedUploader,
    get_file_storage
)


class TestFileStorage(unittest.TestCase):
    """文件存储测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileStorage(base_path=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_upload(self):
        """测试上传"""
        content = b"Hello, World!"
        meta = self.storage.upload("test.txt", content)
        self.assertIsNotNone(meta.file_id)
        self.assertEqual(meta.filename, "test.txt")
        self.assertEqual(meta.size, len(content))
        self.assertEqual(meta.content_type, "text/plain")

    def test_upload_with_metadata(self):
        """测试带元数据上传"""
        meta = self.storage.upload("test.txt", b"content",
                                    metadata={"author": "test"})
        self.assertEqual(meta.metadata["author"], "test")

    def test_download(self):
        """测试下载"""
        content = b"Hello, World!"
        meta = self.storage.upload("test.txt", content)
        downloaded = self.storage.download(meta.file_id)
        self.assertEqual(downloaded, content)

    def test_download_not_found(self):
        """测试下载不存在的文件"""
        result = self.storage.download("nonexistent")
        self.assertIsNone(result)

    def test_get_metadata(self):
        """测试获取元数据"""
        meta = self.storage.upload("test.txt", b"content")
        retrieved = self.storage.get_metadata(meta.file_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.filename, "test.txt")

    def test_delete(self):
        """测试删除"""
        meta = self.storage.upload("test.txt", b"content")
        result = self.storage.delete(meta.file_id)
        self.assertTrue(result)
        self.assertIsNone(self.storage.get_metadata(meta.file_id))

    def test_delete_not_found(self):
        """测试删除不存在的文件"""
        result = self.storage.delete("nonexistent")
        self.assertFalse(result)

    def test_list_files(self):
        """测试列出文件"""
        self.storage.upload("file1.txt", b"content1")
        self.storage.upload("file2.txt", b"content2")
        files = self.storage.list_files()
        self.assertEqual(len(files), 2)

    def test_verify_checksum(self):
        """测试校验和验证"""
        meta = self.storage.upload("test.txt", b"content")
        self.assertTrue(self.storage.verify_checksum(meta.file_id))

    def test_verify_checksum_not_found(self):
        """测试验证不存在的文件"""
        self.assertFalse(self.storage.verify_checksum("nonexistent"))

    def test_stats(self):
        """测试统计信息"""
        self.storage.upload("test.txt", b"content")
        stats = self.storage.get_stats()
        self.assertEqual(stats["total_files"], 1)
        self.assertEqual(stats["total_size"], 7)


class TestChunkedUploader(unittest.TestCase):
    """分片上传器测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileStorage(base_path=self.temp_dir)
        self.uploader = ChunkedUploader(self.storage)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_upload_chunks(self):
        """测试分片上传"""
        self.uploader.upload_chunk("upload1", 0, b"Hello, ")
        self.uploader.upload_chunk("upload1", 1, b"World!")

        meta = self.uploader.complete_upload("upload1", "test.txt")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.size, 13)

        downloaded = self.storage.download(meta.file_id)
        self.assertEqual(downloaded, b"Hello, World!")

    def test_get_uploaded_chunks(self):
        """测试获取已上传分片数"""
        self.uploader.upload_chunk("upload1", 0, b"chunk1")
        self.uploader.upload_chunk("upload1", 1, b"chunk2")
        self.assertEqual(self.uploader.get_uploaded_chunks("upload1"), 2)

    def test_complete_not_found(self):
        """测试完成不存在的上传"""
        result = self.uploader.complete_upload("nonexistent", "test.txt")
        self.assertIsNone(result)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_file_storage(self):
        """测试获取全局文件存储"""
        s1 = get_file_storage()
        s2 = get_file_storage()
        self.assertIs(s1, s2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 78 - 文件存储系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFileStorage))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestChunkedUploader))
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
