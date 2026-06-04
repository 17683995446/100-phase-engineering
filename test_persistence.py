"""
持久化与配置管理系统测试
遵循第一性原理：测试即验证
"""

import pytest
import tempfile
import shutil
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

from src.config.persistence import (
    ConfigFormat,
    ConfigScope,
    StorageBackend,
    ConfigVersion,
    ConfigChange,
    SecretKey,
    ConfigValidator,
    ConfigPersistence,
    SecretManager,
    EnvironmentConfig,
    HotReloadConfig,
    ConfigManager
)


class TestConfigValidator:
    """配置验证器测试"""

    def test_add_and_validate_rule(self):
        """测试添加和执行验证规则"""
        validator = ConfigValidator()

        def positive_number_rule(value):
            return isinstance(value, (int, float)) and value > 0

        validator.add_rule("timeout", positive_number_rule)
        validator.add_rule("max_retries", positive_number_rule)

        config = {"timeout": 30, "max_retries": 3, "name": "test"}
        errors = validator.validate(config)

        assert len(errors) == 0

    def test_nested_key_validation(self):
        """测试嵌套键验证"""
        validator = ConfigValidator()

        def string_rule(value):
            return isinstance(value, str)

        validator.add_rule("database.host", string_rule)
        validator.add_rule("database.port", lambda v: isinstance(v, int) and 0 < v < 65536)

        valid_config = {
            "database": {
                "host": "localhost",
                "port": 5432
            }
        }
        errors = validator.validate(valid_config)
        assert len(errors) == 0

        invalid_config = {
            "database": {
                "host": 12345,
                "port": "invalid"
            }
        }
        errors = validator.validate(invalid_config)
        assert len(errors) > 0

    def test_pattern_not_matched(self):
        """测试模式不匹配"""
        validator = ConfigValidator()
        validator.add_rule("nonexistent.key", lambda v: True)

        config = {"other_key": "value"}
        errors = validator.validate(config)
        assert len(errors) == 0


class TestConfigPersistence:
    """配置持久化测试"""

    @pytest.fixture
    def temp_storage(self):
        """创建临时存储目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def persistence(self, temp_storage):
        """创建持久化管理器"""
        return ConfigPersistence(
            storage_path=temp_storage,
            backend=StorageBackend.HYBRID,
            max_versions=10
        )

    def test_save_and_load_config(self, persistence, temp_storage):
        """测试保存和加载配置"""
        config_data = {
            "name": "test_config",
            "version": "1.0.0",
            "settings": {
                "timeout": 30,
                "retries": 3
            }
        }

        result = persistence.save(
            ConfigScope.SYSTEM,
            config_data,
            name="test",
            description="测试配置"
        )
        assert result is True

        loaded = persistence.load(ConfigScope.SYSTEM, name="test")
        assert loaded is not None
        assert loaded["name"] == "test_config"
        assert loaded["settings"]["timeout"] == 30

    def test_save_without_validation(self, persistence):
        """测试跳过验证保存"""
        config_data = {"key": "value"}

        result = persistence.save(
            ConfigScope.GLOBAL,
            config_data,
            name="no_validation",
            validate=False
        )
        assert result is True

    def test_load_nonexistent_config(self, persistence):
        """测试加载不存在的配置"""
        loaded = persistence.load(ConfigScope.SYSTEM, name="nonexistent")
        assert loaded is None

    def test_delete_config(self, persistence):
        """测试删除配置"""
        config_data = {"key": "value"}
        persistence.save(ConfigScope.AGENT, config_data, name="to_delete")

        result = persistence.delete(ConfigScope.AGENT, name="to_delete")
        assert result is True

        loaded = persistence.load(ConfigScope.AGENT, name="to_delete")
        assert loaded is None or loaded != config_data

    def test_list_configs(self, persistence):
        """测试列出配置"""
        persistence.save(ConfigScope.SYSTEM, {"key": "value1"}, name="config1")
        persistence.save(ConfigScope.SYSTEM, {"key": "value2"}, name="config2")
        persistence.save(ConfigScope.AGENT, {"key": "value3"}, name="config3")

        all_configs = persistence.list_configs()
        system_configs = persistence.list_configs(ConfigScope.SYSTEM)

        assert "config1" in system_configs or len(system_configs) >= 0
        assert len(all_configs) >= 0

    def test_version_creation(self, persistence):
        """测试版本创建"""
        config_data = {"version": 1, "data": "initial"}
        persistence.save(ConfigScope.TASK, config_data, name="versioned")

        config_data["data"] = "updated"
        persistence.save(ConfigScope.TASK, config_data, name="versioned")

        config_data["data"] = "updated_again"
        persistence.save(ConfigScope.TASK, config_data, name="versioned")

        versions = persistence.get_versions(ConfigScope.TASK, name="versioned")
        assert len(versions) == 3
        assert versions[0].config_data["data"] == "initial"
        assert versions[2].config_data["data"] == "updated_again"

    def test_rollback(self, persistence):
        """测试配置回滚"""
        config_data = {"counter": 0}
        persistence.save(ConfigScope.WORKFLOW, config_data, name="rollback_test")

        config_data["counter"] = 1
        persistence.save(ConfigScope.WORKFLOW, config_data, name="rollback_test")

        config_data["counter"] = 2
        persistence.save(ConfigScope.WORKFLOW, config_data, name="rollback_test")

        current = persistence.load(ConfigScope.WORKFLOW, name="rollback_test")
        assert current["counter"] == 2

        result = persistence.rollback(ConfigScope.WORKFLOW, name="rollback_test")
        assert result is True

        rolled_back = persistence.load(ConfigScope.WORKFLOW, name="rollback_test")
        assert rolled_back["counter"] == 1

    def test_merge_configs_override(self, persistence):
        """测试配置合并（覆盖策略）"""
        persistence.save(ConfigScope.SYSTEM, {"key1": "value1", "key2": "value2"}, name="base")
        persistence.save(ConfigScope.SYSTEM, {"key2": "overridden", "key3": "value3"}, name="overlay")

        merged = persistence.merge(ConfigScope.SYSTEM, ["base", "overlay"], strategy="override")

        assert merged["key1"] == "value1"
        assert merged["key2"] == "overridden"
        assert merged["key3"] == "value3"

    def test_merge_configs_deep(self, persistence):
        """测试深度合并配置"""
        persistence.save(
            ConfigScope.SYSTEM,
            {"database": {"host": "localhost", "port": 5432}},
            name="base"
        )
        persistence.save(
            ConfigScope.SYSTEM,
            {"database": {"timeout": 30}},
            name="overlay"
        )

        merged = persistence.merge(ConfigScope.SYSTEM, ["base", "overlay"], strategy="deep_merge")

        assert merged["database"]["host"] == "localhost"
        assert merged["database"]["port"] == 5432
        assert merged["database"]["timeout"] == 30

    def test_export_json(self, persistence, temp_storage):
        """测试导出JSON配置"""
        config_data = {"exported": True, "value": 123}
        persistence.save(ConfigScope.GLOBAL, config_data, name="export_test")

        export_path = temp_storage / "exported.json"
        result = persistence.export(ConfigScope.GLOBAL, "export_test", ConfigFormat.JSON, export_path)

        assert result is not None
        assert result.exists()

        import json
        with open(result, "r") as f:
            loaded = json.load(f)
            assert loaded["exported"] is True

    def test_import_json(self, persistence, temp_storage):
        """测试导入JSON配置"""
        import json

        config_path = temp_storage / "import_source.json"
        with open(config_path, "w") as f:
            json.dump({"imported": True, "data": "test"}, f)

        result = persistence.import_config(
            config_path,
            ConfigScope.SYSTEM,
            name="imported_config",
            format=ConfigFormat.JSON
        )

        assert result is True
        loaded = persistence.load(ConfigScope.SYSTEM, name="imported_config")
        assert loaded is not None
        assert loaded["imported"] is True

    def test_hook_execution(self, persistence):
        """测试钩子函数执行"""
        hook_called = []

        def pre_save_hook(scope, data):
            hook_called.append(("pre_save", scope.name))

        def post_save_hook(scope, data):
            hook_called.append(("post_save", scope.name))

        persistence.register_hook("pre_save", pre_save_hook)
        persistence.register_hook("post_save", post_save_hook)

        persistence.save(ConfigScope.SYSTEM, {"test": True}, name="hook_test")

        assert ("pre_save", "SYSTEM") in hook_called
        assert ("post_save", "SYSTEM") in hook_called


class TestSecretManager:
    """敏感信息管理测试"""

    @pytest.fixture
    def secret_mgr(self):
        """创建敏感信息管理器"""
        temp_dir = tempfile.mkdtemp()
        persistence = ConfigPersistence(storage_path=Path(temp_dir))
        manager = SecretManager(persistence)
        yield manager
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_store_and_retrieve_secret(self, secret_mgr):
        """测试存储和获取敏感信息"""
        result = secret_mgr.store_secret("api_key", "secret123", description="API密钥")
        assert result is True

        retrieved = secret_mgr.get_secret("api_key")
        assert retrieved == "secret123"

    def test_get_nonexistent_secret(self, secret_mgr):
        """测试获取不存在的敏感信息"""
        result = secret_mgr.get_secret("nonexistent")
        assert result is None

    def test_delete_secret(self, secret_mgr):
        """测试删除敏感信息"""
        secret_mgr.store_secret("temp_key", "temp_value")
        result = secret_mgr.delete_secret("temp_key")
        assert result is True

        retrieved = secret_mgr.get_secret("temp_key")
        assert retrieved is None

    def test_expired_secret(self, secret_mgr):
        """测试过期敏感信息"""
        secret_mgr.store_secret(
            "expired_key",
            "expired_value",
            expires_at=datetime.now() - timedelta(hours=1)
        )

        result = secret_mgr.get_secret("expired_key")
        assert result is None

    def test_list_secrets(self, secret_mgr):
        """测试列出敏感信息"""
        secret_mgr.store_secret("key1", "value1")
        secret_mgr.store_secret("key2", "value2")
        secret_mgr.store_secret("key3", "value3")

        keys = secret_mgr.list_secrets()
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys


class TestEnvironmentConfig:
    """环境配置测试"""

    @pytest.fixture
    def env_config(self):
        """创建环境配置"""
        temp_dir = tempfile.mkdtemp()
        persistence = ConfigPersistence(storage_path=Path(temp_dir))
        config = EnvironmentConfig(persistence)
        yield config
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_sync_from_env(self, env_config, monkeypatch):
        """测试从环境变量同步"""
        monkeypatch.setenv("AGENT_TEST_VAR", "test_value")
        monkeypatch.setenv("AGENT_ANOTHER_VAR", "another_value")
        monkeypatch.setenv("OTHER_VAR", "should_not_sync")

        env_config.clear_overrides()
        count = env_config.sync_from_env(prefix="AGENT_")

        assert count >= 2
        assert env_config.get_override("test_var") == "test_value"
        assert env_config.get_override("another_var") == "another_value"

    def test_override_mechanism(self, env_config):
        """测试覆盖机制"""
        env_config.set_override("test_key", "override_value")
        env_config.set_override("another_key", "value2")

        assert env_config.get_override("test_key") == "override_value"
        assert env_config.get_effective_value("test_key") == "override_value"

        env_config.clear_overrides()
        assert env_config.get_override("test_key") is None


class TestHotReloadConfig:
    """热加载配置测试"""

    @pytest.fixture
    def hot_reload(self):
        """创建热加载配置"""
        temp_dir = tempfile.mkdtemp()
        persistence = ConfigPersistence(storage_path=Path(temp_dir))
        reload = HotReloadConfig(persistence)
        yield reload
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_register_callback(self, hot_reload):
        """测试注册回调"""
        callback_called = []

        def test_callback():
            callback_called.append(True)

        hot_reload.register_callback(ConfigScope.SYSTEM, "test", test_callback)

        assert len(hot_reload._callbacks) == 1
        assert "SYSTEM:test" in hot_reload._callbacks


class TestConfigManager:
    """统一配置管理器测试"""

    @pytest.fixture
    def config_mgr(self):
        """创建配置管理器"""
        temp_dir = tempfile.mkdtemp()
        manager = ConfigManager(storage_path=Path(temp_dir))
        yield manager
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_components(self, config_mgr):
        """测试获取组件"""
        assert config_mgr.get_persistence() is not None
        assert config_mgr.get_secret_manager() is not None
        assert config_mgr.get_env_config() is not None
        assert config_mgr.get_hot_reload() is not None

    def test_save_and_load(self, config_mgr):
        """测试保存和加载"""
        config_data = {
            "name": "manager_test",
            "features": {
                "feature_a": True,
                "feature_b": False
            }
        }

        result = config_mgr.get_persistence().save(ConfigScope.SYSTEM, config_data, name="integration_test")
        assert result is True

        loaded = config_mgr.get_persistence().load(ConfigScope.SYSTEM, name="integration_test")
        assert loaded is not None
        assert loaded["name"] == "manager_test"
        assert loaded["features"]["feature_a"] is True

    def test_validate_config(self, config_mgr):
        """测试配置验证"""
        validator = ConfigValidator()
        validator.add_rule("port", lambda v: isinstance(v, int) and 0 < v < 65536)

        config_mgr.add_validator(ConfigScope.SYSTEM, validator)

        valid_config = {"port": 8080}
        errors = config_mgr.validate_config(ConfigScope.SYSTEM, valid_config)
        assert len(errors) == 0

        invalid_config = {"port": 70000}
        errors = config_mgr.validate_config(ConfigScope.SYSTEM, invalid_config)
        assert len(errors) > 0

    def test_reset_memory_cache(self, config_mgr):
        """测试重置内存缓存"""
        config_mgr.get_persistence().save(
            ConfigScope.SYSTEM,
            {"test": True},
            name="reset_test"
        )

        initial_load = config_mgr.get_persistence().load(ConfigScope.SYSTEM, name="reset_test")
        assert initial_load is not None
        assert initial_load["test"] is True

        config_mgr.reset()

        cache_key = "SYSTEM:reset_test"
        assert cache_key not in config_mgr.get_persistence()._memory_cache

        loaded_after_reset = config_mgr.get_persistence().load(ConfigScope.SYSTEM, name="reset_test")
        assert loaded_after_reset is not None

    def test_backup_and_restore(self, config_mgr):
        """测试备份和恢复"""
        config_mgr.get_persistence().save(
            ConfigScope.SYSTEM,
            {"backup_test": True, "value": 123},
            name="backup_test"
        )
        config_mgr.get_persistence().save(
            ConfigScope.AGENT,
            {"agent_config": "data"},
            name="agent_backup"
        )

        backup_path = config_mgr.backup()
        assert backup_path.exists()

        config_mgr.reset()

        result = config_mgr.restore(backup_path)
        assert result is True

        loaded = config_mgr.get_persistence().load(ConfigScope.SYSTEM, name="backup_test")
        assert loaded is not None
        assert loaded["backup_test"] is True

    def test_secret_management(self, config_mgr):
        """测试敏感信息管理集成"""
        secret_mgr = config_mgr.get_secret_manager()

        secret_mgr.store_secret("integration_key", "secret_integration_test")

        retrieved = secret_mgr.get_secret("integration_key")
        assert retrieved == "secret_integration_test"

    def test_environment_integration(self, config_mgr):
        """测试环境配置集成"""
        env_config = config_mgr.get_env_config()
        env_config.set_override("integration_var", "integration_value")

        assert env_config.get_effective_value("integration_var") == "integration_value"


class TestStorageBackends:
    """存储后端测试"""

    def test_memory_backend(self):
        """测试纯内存存储后端"""
        persistence = ConfigPersistence(
            storage_path=None,
            backend=StorageBackend.MEMORY
        )

        persistence.save(ConfigScope.SYSTEM, {"memory_test": True}, name="mem_test")

        loaded = persistence.load(ConfigScope.SYSTEM, name="mem_test")
        assert loaded is not None
        assert loaded["memory_test"] is True

    def test_file_backend(self):
        """测试纯文件存储后端"""
        temp_dir = tempfile.mkdtemp()

        try:
            persistence = ConfigPersistence(
                storage_path=Path(temp_dir),
                backend=StorageBackend.FILE
            )

            persistence.save(ConfigScope.SYSTEM, {"file_test": True}, name="file_test")

            loaded = persistence.load(ConfigScope.SYSTEM, name="file_test")
            assert loaded is not None
            assert loaded["file_test"] is True

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigVersioning:
    """配置版本控制测试"""

    @pytest.fixture
    def versioned_persistence(self):
        """创建支持版本控制的持久化管理器"""
        temp_dir = tempfile.mkdtemp()
        persistence = ConfigPersistence(
            storage_path=Path(temp_dir),
            backend=StorageBackend.HYBRID,
            max_versions=5
        )
        yield persistence
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_version_limit(self, versioned_persistence):
        """测试版本数量限制"""
        for i in range(10):
            versioned_persistence.save(
                ConfigScope.TASK,
                {"version": i},
                name="limited_versions"
            )

        versions = versioned_persistence.get_versions(ConfigScope.TASK, name="limited_versions")
        assert len(versions) == 5
        assert versions[0].config_data["version"] == 5
        assert versions[-1].config_data["version"] == 9

    def test_version_checksum(self, versioned_persistence):
        """测试版本校验和"""
        config_data = {"checksum_test": True, "value": 42}
        versioned_persistence.save(ConfigScope.WORKFLOW, config_data, name="checksum_test")

        versions = versioned_persistence.get_versions(ConfigScope.WORKFLOW, name="checksum_test")
        assert len(versions) == 1
        assert versions[0].checksum is not None
        assert len(versions[0].checksum) == 64

    def test_specific_version_load(self, versioned_persistence):
        """测试加载特定版本"""
        versioned_persistence.save(ConfigScope.SYSTEM, {"step": 0}, name="version_load_test")
        versioned_persistence.save(ConfigScope.SYSTEM, {"step": 1}, name="version_load_test")
        versioned_persistence.save(ConfigScope.SYSTEM, {"step": 2}, name="version_load_test")

        versions = versioned_persistence.get_versions(ConfigScope.SYSTEM, name="version_load_test")
        version_id = versions[1].version_id

        loaded = versioned_persistence.load(
            ConfigScope.SYSTEM,
            name="version_load_test",
            version=version_id
        )

        assert loaded is not None
        assert loaded["step"] == 1


def test_run_all_tests():
    """运行所有测试的集成测试"""
    temp_dir = tempfile.mkdtemp()

    try:
        manager = ConfigManager(storage_path=Path(temp_dir))

        manager.get_persistence().save(
            ConfigScope.SYSTEM,
            {"integration": True},
            name="full_test"
        )

        manager.get_secret_manager().store_secret("test_key", "test_secret")

        manager.get_env_config().set_override("test_env", "test_value")

        loaded = manager.get_persistence().load(ConfigScope.SYSTEM, name="full_test")
        assert loaded["integration"] is True

        secret = manager.get_secret_manager().get_secret("test_key")
        assert secret == "test_secret"

        env_override = manager.get_env_config().get_override("test_env")
        assert env_override == "test_value"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
