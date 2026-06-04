"""
数据备份与恢复系统
提供数据备份、恢复、归档和快照功能
"""
import os
import json
import shutil
import tarfile
import gzip
import hashlib
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.utils.structured_logging import get_logger


@dataclass
class BackupInfo:
    """备份信息"""
    backup_id: str
    source_path: str
    backup_path: str
    size_bytes: int
    checksum: str
    created_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "source_path": self.source_path,
            "backup_path": self.backup_path,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


class ChecksumCalculator:
    """校验和计算器"""

    def calculate_file(self, file_path: str) -> str:
        """计算文件MD5校验和"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def calculate_string(self, content: str) -> str:
        """计算字符串MD5校验和"""
        return hashlib.md5(content.encode("utf-8")).hexdigest()


class BackupManager:
    """备份管理器"""

    def __init__(self, backup_dir: str = "backups"):
        self._backup_dir = Path(backup_dir)
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._backups: Dict[str, BackupInfo] = {}
        self._lock = threading.RLock()
        self._checksum = ChecksumCalculator()
        self._logger = get_logger("backup.manager")
        self._load_index()

    def _load_index(self) -> None:
        """加载备份索引"""
        index_file = self._backup_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for bid, info in data.items():
                        self._backups[bid] = BackupInfo(**info)
            except Exception as e:
                self._logger.warning(f"Failed to load backup index: {e}")

    def _save_index(self) -> None:
        """保存备份索引"""
        index_file = self._backup_dir / "index.json"
        with self._lock:
            data = {bid: info.to_dict() for bid, info in self._backups.items()}
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def backup_directory(self, source_path: str,
                         backup_id: Optional[str] = None,
                         compress: bool = True) -> Optional[BackupInfo]:
        """备份目录"""
        source = Path(source_path)
        if not source.exists():
            self._logger.error(f"Source path does not exist: {source_path}")
            return None

        backup_id = backup_id or f"backup_{int(time.time())}"
        ext = "tar.gz" if compress else "tar"
        backup_filename = f"{backup_id}.{ext}"
        backup_path = self._backup_dir / backup_filename

        try:
            # 创建归档
            mode = "w:gz" if compress else "w"
            with tarfile.open(backup_path, mode) as tar:
                tar.add(source, arcname=source.name)

            size_bytes = backup_path.stat().st_size
            checksum = self._checksum.calculate_file(str(backup_path))

            info = BackupInfo(
                backup_id=backup_id,
                source_path=str(source.absolute()),
                backup_path=str(backup_path.absolute()),
                size_bytes=size_bytes,
                checksum=checksum,
                created_at=time.time()
            )

            with self._lock:
                self._backups[backup_id] = info
                self._save_index()

            self._logger.info(f"Backup created: {backup_id}, size: {size_bytes} bytes")
            return info

        except Exception as e:
            self._logger.error(f"Backup failed: {e}")
            return None

    def backup_files(self, file_paths: List[str],
                     backup_id: Optional[str] = None,
                     compress: bool = True) -> Optional[BackupInfo]:
        """备份多个文件"""
        backup_id = backup_id or f"backup_{int(time.time())}"
        ext = "tar.gz" if compress else "tar"
        backup_filename = f"{backup_id}.{ext}"
        backup_path = self._backup_dir / backup_filename

        try:
            mode = "w:gz" if compress else "w"
            with tarfile.open(backup_path, mode) as tar:
                for file_path in file_paths:
                    fp = Path(file_path)
                    if fp.exists():
                        tar.add(fp, arcname=fp.name)

            size_bytes = backup_path.stat().st_size
            checksum = self._checksum.calculate_file(str(backup_path))

            info = BackupInfo(
                backup_id=backup_id,
                source_path=",".join(file_paths),
                backup_path=str(backup_path.absolute()),
                size_bytes=size_bytes,
                checksum=checksum,
                created_at=time.time()
            )

            with self._lock:
                self._backups[backup_id] = info
                self._save_index()

            return info

        except Exception as e:
            self._logger.error(f"Backup files failed: {e}")
            return None

    def restore(self, backup_id: str, target_path: str) -> bool:
        """恢复备份"""
        with self._lock:
            info = self._backups.get(backup_id)
            if not info:
                self._logger.error(f"Backup not found: {backup_id}")
                return False

        backup_path = Path(info.backup_path)
        if not backup_path.exists():
            self._logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            target = Path(target_path)
            target.mkdir(parents=True, exist_ok=True)

            with tarfile.open(backup_path, "r:gz" if backup_path.suffix == ".gz" else "r") as tar:
                tar.extractall(target)

            self._logger.info(f"Backup restored: {backup_id} to {target_path}")
            return True

        except Exception as e:
            self._logger.error(f"Restore failed: {e}")
            return False

    def verify(self, backup_id: str) -> bool:
        """验证备份完整性"""
        with self._lock:
            info = self._backups.get(backup_id)
            if not info:
                return False

        backup_path = Path(info.backup_path)
        if not backup_path.exists():
            return False

        current_checksum = self._checksum.calculate_file(str(backup_path))
        return current_checksum == info.checksum

    def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        with self._lock:
            info = self._backups.get(backup_id)
            if not info:
                return False

            backup_path = Path(info.backup_path)
            if backup_path.exists():
                backup_path.unlink()

            del self._backups[backup_id]
            self._save_index()
            return True

    def list_backups(self) -> List[BackupInfo]:
        """列出所有备份"""
        with self._lock:
            return list(self._backups.values())

    def get_backup(self, backup_id: str) -> Optional[BackupInfo]:
        """获取备份信息"""
        with self._lock:
            return self._backups.get(backup_id)

    def cleanup_old_backups(self, max_age_days: int) -> int:
        """清理旧备份"""
        cutoff = time.time() - (max_age_days * 86400)
        removed = 0

        with self._lock:
            for bid in list(self._backups.keys()):
                info = self._backups[bid]
                if info.created_at < cutoff:
                    self.delete_backup(bid)
                    removed += 1

        return removed

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_size = sum(b.size_bytes for b in self._backups.values())
            return {
                "total_backups": len(self._backups),
                "total_size_bytes": total_size,
                "backup_dir": str(self._backup_dir)
            }


class SnapshotManager:
    """快照管理器"""

    def __init__(self, snapshot_dir: str = "snapshots"):
        self._snapshot_dir = Path(snapshot_dir)
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._logger = get_logger("snapshot.manager")

    def create_snapshot(self, data: Dict[str, Any],
                        snapshot_id: Optional[str] = None) -> str:
        """创建数据快照"""
        snapshot_id = snapshot_id or f"snapshot_{int(time.time())}"
        snapshot_path = self._snapshot_dir / f"{snapshot_id}.json.gz"

        with self._lock:
            with gzip.open(snapshot_path, "wt", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        self._logger.info(f"Snapshot created: {snapshot_id}")
        return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """恢复快照"""
        snapshot_path = self._snapshot_dir / f"{snapshot_id}.json.gz"
        if not snapshot_path.exists():
            return None

        with self._lock:
            with gzip.open(snapshot_path, "rt", encoding="utf-8") as f:
                return json.load(f)

    def list_snapshots(self) -> List[str]:
        """列出所有快照"""
        with self._lock:
            return [p.stem for p in self._snapshot_dir.glob("*.json.gz")]

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        snapshot_path = self._snapshot_dir / f"{snapshot_id}.json.gz"
        with self._lock:
            if snapshot_path.exists():
                snapshot_path.unlink()
                return True
            return False


# 全局实例
_backup_manager: Optional[BackupManager] = None
_snapshot_manager: Optional[SnapshotManager] = None


def get_backup_manager() -> BackupManager:
    """获取全局备份管理器"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager


def get_snapshot_manager() -> SnapshotManager:
    """获取全局快照管理器"""
    global _snapshot_manager
    if _snapshot_manager is None:
        _snapshot_manager = SnapshotManager()
    return _snapshot_manager
