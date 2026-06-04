"""
Phase 41 - 安全认证与授权系统测试
验证认证系统是否正常工作
"""
import unittest
from src.utils.security import (
    AuthManager,
    Permission,
    get_auth_manager
)
from src.utils.auth_middleware_simple import (
    PermissionChecker,
    get_permission_checker
)


class TestAuthManager(unittest.TestCase):
    """认证管理器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.auth_manager = AuthManager()
    
    def test_generate_api_key(self):
        """测试生成API密钥"""
        key, key_id = self.auth_manager.generate_api_key(
            name="test_key",
            permissions={Permission.READ, Permission.WRITE},
            description="Test API key"
        )
        
        self.assertIsNotNone(key)
        self.assertIsNotNone(key_id)
        self.assertGreater(len(key), 20)
    
    def test_validate_api_key(self):
        """测试验证API密钥"""
        key, key_id = self.auth_manager.generate_api_key(
            name="validate_test",
            permissions={Permission.READ}
        )
        
        # 验证正确密钥
        api_key = self.auth_manager.validate_api_key(key)
        self.assertIsNotNone(api_key)
        self.assertEqual(api_key.key_id, key_id)
        
        # 验证错误密钥
        invalid_key = self.auth_manager.validate_api_key("invalid_key")
        self.assertIsNone(invalid_key)
    
    def test_revoke_api_key(self):
        """测试撤销API密钥"""
        key, key_id = self.auth_manager.generate_api_key(
            name="revoke_test",
            permissions={Permission.READ}
        )
        
        # 撤销密钥
        result = self.auth_manager.revoke_api_key(key_id)
        self.assertTrue(result)
        
        # 验证密钥已失效
        api_key = self.auth_manager.validate_api_key(key)
        self.assertIsNone(api_key)
    
    def test_has_permission(self):
        """测试权限检查"""
        key, key_id = self.auth_manager.generate_api_key(
            name="permission_test",
            permissions={Permission.READ, Permission.WRITE}
        )
        
        # 验证有权限
        self.assertTrue(self.auth_manager.has_permission(key_id, Permission.READ))
        self.assertTrue(self.auth_manager.has_permission(key_id, Permission.WRITE))
        
        # 验证无权限
        self.assertFalse(self.auth_manager.has_permission(key_id, Permission.DELETE))
    
    def test_rate_limit(self):
        """测试速率限制"""
        key, key_id = self.auth_manager.generate_api_key(
            name="rate_limit_test",
            permissions={Permission.READ},
            rate_limit=5
        )
        
        # 前5次应该通过
        for i in range(5):
            self.assertTrue(self.auth_manager.check_rate_limit(key_id, 5))
        
        # 第6次应该失败
        self.assertFalse(self.auth_manager.check_rate_limit(key_id, 5))
    
    def test_audit_logs(self):
        """测试审计日志"""
        key, key_id = self.auth_manager.generate_api_key(
            name="audit_test",
            permissions={Permission.READ}
        )
        
        # 记录一些日志
        self.auth_manager.log_request(key_id, "/test", "GET", "success")
        self.auth_manager.log_request(key_id, "/test", "POST", "failure")
        
        # 获取日志
        logs = self.auth_manager.get_audit_logs(key_id)
        self.assertGreaterEqual(len(logs), 2)


class TestPermissionChecker(unittest.TestCase):
    """权限检查器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.auth_manager = AuthManager()
        self.checker = PermissionChecker(self.auth_manager)
    
    def test_check_read(self):
        """测试读权限检查"""
        key, key_id = self.auth_manager.generate_api_key(
            name="read_test",
            permissions={Permission.READ}
        )
        
        self.assertTrue(self.checker.check_read(key_id))
        self.assertFalse(self.checker.check_write(key_id))
    
    def test_check_all(self):
        """测试检查所有权限"""
        key, key_id = self.auth_manager.generate_api_key(
            name="all_test",
            permissions={Permission.READ, Permission.WRITE, Permission.DELETE}
        )
        
        self.assertTrue(
            self.checker.check_all(key_id, Permission.READ, Permission.WRITE)
        )
        self.assertFalse(
            self.checker.check_all(key_id, Permission.READ, Permission.ADMIN)
        )
    
    def test_check_any(self):
        """测试检查任意权限"""
        key, key_id = self.auth_manager.generate_api_key(
            name="any_test",
            permissions={Permission.READ}
        )
        
        self.assertTrue(
            self.checker.check_any(key_id, Permission.READ, Permission.WRITE)
        )
        self.assertFalse(
            self.checker.check_any(key_id, Permission.WRITE, Permission.DELETE)
        )


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 41 - 安全认证与授权系统测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAuthManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPermissionChecker))
    
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
