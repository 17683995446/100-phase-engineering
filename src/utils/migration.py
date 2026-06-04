"""
数据迁移与版本控制
提供数据库迁移管理和版本控制功能
"""
import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class MigrationStatus(Enum):
    """迁移状态"""
    PENDING = auto()
    APPLIED = auto()
    FAILED = auto()
    ROLLED_BACK = auto()


@dataclass
class Migration:
    """迁移记录"""
    version: str
    name: str
    description: str
    applied_at: Optional[datetime] = None
    status: MigrationStatus = MigrationStatus.PENDING
    checksum: str = ""
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "status": self.status.name,
            "checksum": self.checksum,
            "execution_time_ms": self.execution_time_ms
        }


class MigrationManager:
    """迁移管理器"""
    
    def __init__(self, migrations_dir: str = "migrations"):
        self.migrations_dir = migrations_dir
        self._migrations: Dict[str, Migration] = {}
        self._handlers: Dict[str, Callable] = {}
        self._logger = get_logger("migration.manager")
        self._history_file = os.path.join(migrations_dir, "history.json")
        
        # 确保目录存在
        os.makedirs(migrations_dir, exist_ok=True)
        
        # 加载历史记录
        self._load_history()
    
    def register_migration(
        self,
        version: str,
        name: str,
        description: str,
        handler: Callable,
        checksum: str = ""
    ) -> None:
        """注册迁移"""
        migration = Migration(
            version=version,
            name=name,
            description=description,
            checksum=checksum
        )
        
        self._migrations[version] = migration
        self._handlers[version] = handler
        
        self._logger.info(f"Registered migration: {version} - {name}")
    
    def apply_migration(self, version: str) -> bool:
        """应用迁移"""
        migration = self._migrations.get(version)
        if not migration:
            self._logger.error(f"Migration not found: {version}")
            return False
        
        if migration.status == MigrationStatus.APPLIED:
            self._logger.info(f"Migration already applied: {version}")
            return True
        
        handler = self._handlers.get(version)
        if not handler:
            self._logger.error(f"Migration handler not found: {version}")
            return False
        
        try:
            self._logger.info(f"Applying migration: {version}")
            start_time = time.time()
            
            handler()
            
            execution_time = (time.time() - start_time) * 1000
            
            migration.status = MigrationStatus.APPLIED
            migration.applied_at = datetime.now()
            migration.execution_time_ms = execution_time
            
            self._save_history()
            
            self._logger.info(f"Migration applied: {version} ({execution_time:.2f}ms)")
            return True
        except Exception as e:
            migration.status = MigrationStatus.FAILED
            self._save_history()
            
            self._logger.error(f"Migration failed: {version} - {e}", exc_info=True)
            return False
    
    def apply_all(self) -> Dict[str, bool]:
        """应用所有待处理的迁移"""
        results = {}
        
        # 按版本排序
        versions = sorted(self._migrations.keys())
        
        for version in versions:
            migration = self._migrations[version]
            if migration.status == MigrationStatus.PENDING:
                results[version] = self.apply_migration(version)
        
        return results
    
    def rollback_migration(self, version: str) -> bool:
        """回滚迁移"""
        migration = self._migrations.get(version)
        if not migration:
            self._logger.error(f"Migration not found: {version}")
            return False
        
        if migration.status != MigrationStatus.APPLIED:
            self._logger.warning(f"Migration not applied: {version}")
            return False
        
        # 标记为已回滚
        migration.status = MigrationStatus.ROLLED_BACK
        migration.applied_at = None
        
        self._save_history()
        
        self._logger.info(f"Migration rolled back: {version}")
        return True
    
    def get_migration_status(self, version: str) -> Optional[MigrationStatus]:
        """获取迁移状态"""
        migration = self._migrations.get(version)
        return migration.status if migration else None
    
    def get_all_migrations(self) -> List[Dict[str, Any]]:
        """获取所有迁移"""
        return [
            migration.to_dict()
            for migration in sorted(
                self._migrations.values(),
                key=lambda m: m.version
            )
        ]
    
    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """获取待处理的迁移"""
        return [
            migration.to_dict()
            for migration in self._migrations.values()
            if migration.status == MigrationStatus.PENDING
        ]
    
    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """获取已应用的迁移"""
        return [
            migration.to_dict()
            for migration in self._migrations.values()
            if migration.status == MigrationStatus.APPLIED
        ]
    
    def _load_history(self) -> None:
        """加载历史记录"""
        if os.path.exists(self._history_file):
            try:
                with open(self._history_file, 'r') as f:
                    data = json.load(f)
                
                for version, migration_data in data.get("migrations", {}).items():
                    migration = Migration(
                        version=version,
                        name=migration_data.get("name", ""),
                        description=migration_data.get("description", ""),
                        applied_at=datetime.fromisoformat(migration_data["applied_at"]) if migration_data.get("applied_at") else None,
                        status=MigrationStatus[migration_data.get("status", "PENDING")],
                        checksum=migration_data.get("checksum", ""),
                        execution_time_ms=migration_data.get("execution_time_ms", 0.0)
                    )
                    self._migrations[version] = migration
                
                self._logger.info(f"Loaded migration history: {len(self._migrations)} migrations")
            except Exception as e:
                self._logger.error(f"Failed to load migration history: {e}")
    
    def _save_history(self) -> None:
        """保存历史记录"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "migrations": {
                    version: migration.to_dict()
                    for version, migration in self._migrations.items()
                }
            }
            
            with open(self._history_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self._logger.debug("Migration history saved")
        except Exception as e:
            self._logger.error(f"Failed to save migration history: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        total = len(self._migrations)
        applied = sum(1 for m in self._migrations.values() if m.status == MigrationStatus.APPLIED)
        pending = sum(1 for m in self._migrations.values() if m.status == MigrationStatus.PENDING)
        failed = sum(1 for m in self._migrations.values() if m.status == MigrationStatus.FAILED)
        
        return {
            "total": total,
            "applied": applied,
            "pending": pending,
            "failed": failed,
            "migrations_dir": self.migrations_dir
        }


class VersionControl:
    """版本控制"""
    
    def __init__(self, version_file: str = "version.json"):
        self.version_file = version_file
        self._logger = get_logger("version.control")
        self._current_version = "0.0.0"
        self._load_version()
    
    def _load_version(self) -> None:
        """加载版本"""
        if os.path.exists(self.version_file):
            try:
                with open(self.version_file, 'r') as f:
                    data = json.load(f)
                self._current_version = data.get("version", "0.0.0")
            except Exception as e:
                self._logger.error(f"Failed to load version: {e}")
    
    def _save_version(self) -> None:
        """保存版本"""
        try:
            data = {
                "version": self._current_version,
                "updated_at": datetime.now().isoformat()
            }
            with open(self.version_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self._logger.error(f"Failed to save version: {e}")
    
    def get_version(self) -> str:
        """获取当前版本"""
        return self._current_version
    
    def set_version(self, version: str) -> None:
        """设置版本"""
        self._current_version = version
        self._save_version()
        self._logger.info(f"Version updated: {version}")
    
    def bump_major(self) -> str:
        """升级主版本"""
        parts = self._current_version.split(".")
        major = int(parts[0]) + 1
        self._current_version = f"{major}.0.0"
        self._save_version()
        return self._current_version
    
    def bump_minor(self) -> str:
        """升级次版本"""
        parts = self._current_version.split(".")
        major = int(parts[0])
        minor = int(parts[1]) + 1
        self._current_version = f"{major}.{minor}.0"
        self._save_version()
        return self._current_version
    
    def bump_patch(self) -> str:
        """升级补丁版本"""
        parts = self._current_version.split(".")
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) + 1
        self._current_version = f"{major}.{minor}.{patch}"
        self._save_version()
        return self._current_version
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """比较版本"""
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            p1 = v1_parts[i] if i < len(v1_parts) else 0
            p2 = v2_parts[i] if i < len(v2_parts) else 0
            
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        
        return 0


# 全局实例
_migration_manager: Optional[MigrationManager] = None
_version_control: Optional[VersionControl] = None


def get_migration_manager(migrations_dir: str = "migrations") -> MigrationManager:
    """获取迁移管理器"""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager(migrations_dir)
    return _migration_manager


def get_version_control(version_file: str = "version.json") -> VersionControl:
    """获取版本控制"""
    global _version_control
    if _version_control is None:
        _version_control = VersionControl(version_file)
    return _version_control
