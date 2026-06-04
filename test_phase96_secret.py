"""
Phase 96 - 密钥管理系统测试
"""
import unittest
import time
from src.utils.secret_manager import (
    SecretManager, SecretType, SecretStatus,
    get_secret_manager
)


class TestSecretManager(unittest.TestCase):
    """密钥管理器测试"""

    def setUp(self):
        self.manager = SecretManager()

    def test_create_secret(self):
        """测试创建密钥"""
        secret = self.manager.create_secret(
            "db_password", SecretType.PASSWORD, "mysecret123"
        )
        self.assertEqual(secret.name, "db_password")
        self.assertEqual(secret.secret_type, SecretType.PASSWORD)
        self.assertEqual(secret.status, SecretStatus.ACTIVE)

    def test_generate_api_key(self):
        """测试生成API密钥"""
        secret, value = self.manager.generate_api_key("service_key")
        self.assertEqual(secret.secret_type, SecretType.API_KEY)
        self.assertTrue(value.startswith("ak_"))
        self.assertTrue(self.manager.verify_secret(secret.secret_id, value))

    def test_generate_password(self):
        """测试生成密码"""
        secret, value = self.manager.generate_password("db_pass", length=16)
        self.assertEqual(secret.secret_type, SecretType.PASSWORD)
        self.assertTrue(self.manager.verify_secret(secret.secret_id, value))

    def test_get_secret_value(self):
        """测试获取密钥值"""
        secret = self.manager.create_secret(
            "api_key", SecretType.API_KEY, "secret_value",
            allowed_services=["service_a"]
        )
        value = self.manager.get_secret_value(secret.secret_id, "service_a")
        self.assertEqual(value, "secret_value")
        self.assertEqual(secret.access_count, 1)

    def test_get_secret_value_unauthorized(self):
        """测试未授权服务获取密钥"""
        secret = self.manager.create_secret(
            "api_key", SecretType.API_KEY, "secret_value",
            allowed_services=["service_a"]
        )
        value = self.manager.get_secret_value(secret.secret_id, "service_b")
        self.assertIsNone(value)

    def test_get_secret_value_expired(self):
        """测试过期密钥"""
        secret = self.manager.create_secret(
            "temp", SecretType.TOKEN, "temp_value",
            expires_in_seconds=1
        )
        time.sleep(1.1)
        value = self.manager.get_secret_value(secret.secret_id, "any")
        self.assertIsNone(value)
        self.assertEqual(secret.status, SecretStatus.EXPIRED)

    def test_get_secret_value_revoked(self):
        """测试撤销后获取密钥"""
        secret = self.manager.create_secret(
            "api_key", SecretType.API_KEY, "secret_value"
        )
        self.manager.revoke_secret(secret.secret_id)
        value = self.manager.get_secret_value(secret.secret_id, "any")
        self.assertIsNone(value)

    def test_verify_secret(self):
        """测试验证密钥"""
        secret = self.manager.create_secret(
            "api_key", SecretType.API_KEY, "correct_value"
        )
        self.assertTrue(self.manager.verify_secret(secret.secret_id, "correct_value"))
        self.assertFalse(self.manager.verify_secret(secret.secret_id, "wrong_value"))

    def test_rotate_secret(self):
        """测试轮换密钥"""
        secret = self.manager.create_secret(
            "api_key", SecretType.API_KEY, "old_value"
        )
        old_hash = secret.value_hash
        rotated = self.manager.rotate_secret(secret.secret_id, "new_value")
        self.assertIsNotNone(rotated)
        self.assertNotEqual(rotated.value_hash, old_hash)
        self.assertTrue(self.manager.verify_secret(secret.secret_id, "new_value"))

    def test_rotate_secret_auto_generate(self):
        """测试自动轮换密钥"""
        secret, old_value = self.manager.generate_api_key("auto_key")
        rotated = self.manager.rotate_secret(secret.secret_id)
        self.assertIsNotNone(rotated)
        self.assertFalse(self.manager.verify_secret(secret.secret_id, old_value))

    def test_revoke_secret(self):
        """测试撤销密钥"""
        secret = self.manager.create_secret("temp", SecretType.TOKEN, "value")
        self.assertTrue(self.manager.revoke_secret(secret.secret_id))
        self.assertEqual(secret.status, SecretStatus.REVOKED)

    def test_delete_secret(self):
        """测试删除密钥"""
        secret = self.manager.create_secret("temp", SecretType.TOKEN, "value")
        self.assertTrue(self.manager.delete_secret(secret.secret_id))
        self.assertIsNone(self.manager.get_secret(secret.secret_id))

    def test_get_secret(self):
        """测试获取密钥信息"""
        secret = self.manager.create_secret("db", SecretType.PASSWORD, "pass")
        fetched = self.manager.get_secret(secret.secret_id)
        self.assertEqual(fetched.name, "db")

    def test_list_secrets(self):
        """测试列出密钥"""
        self.manager.create_secret("k1", SecretType.API_KEY, "v1")
        self.manager.create_secret("k2", SecretType.PASSWORD, "v2")
        all_secrets = self.manager.list_secrets()
        self.assertEqual(len(all_secrets), 2)
        api_keys = self.manager.list_secrets(secret_type=SecretType.API_KEY)
        self.assertEqual(len(api_keys), 1)

    def test_access_logs(self):
        """测试访问日志"""
        secret = self.manager.create_secret(
            "api_key", SecretType.API_KEY, "value",
            allowed_services=["svc"]
        )
        self.manager.get_secret_value(secret.secret_id, "svc")
        self.manager.get_secret_value(secret.secret_id, "other")
        logs = self.manager.get_access_logs(secret.secret_id)
        self.assertEqual(len(logs), 2)
        self.assertTrue(logs[0]["success"])
        self.assertFalse(logs[1]["success"])

    def test_grant_revoke_access(self):
        """测试授予和撤销访问权限"""
        secret = self.manager.create_secret(
            "api_key", SecretType.API_KEY, "value"
        )
        self.manager.grant_access(secret.secret_id, "service_a")
        value = self.manager.get_secret_value(secret.secret_id, "service_a")
        self.assertEqual(value, "value")

        self.manager.revoke_access(secret.secret_id, "service_a")
        value = self.manager.get_secret_value(secret.secret_id, "service_a")
        self.assertIsNone(value)

    def test_stats(self):
        """测试统计信息"""
        self.manager.create_secret("k1", SecretType.API_KEY, "v1")
        self.manager.create_secret("k2", SecretType.PASSWORD, "v2")
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_secrets"], 2)
        self.assertEqual(stats["active"], 2)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_secret_manager(self):
        """测试获取全局密钥管理器"""
        m1 = get_secret_manager()
        m2 = get_secret_manager()
        self.assertIs(m1, m2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 96 - 密钥管理系统测试")
    print("=" * 60)
    unittest.main(verbosity=2)
