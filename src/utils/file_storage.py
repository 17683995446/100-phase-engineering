"""
文件存储系统
提供文件上传、下载、分片、元数据管理和存储策略功能
"""
import os
import hashlib
import shutil
import mimetypes
from typing import Dict, Any, List, Optional, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.utils.structured_logging import get_logger


@dataclass
class FileMetadata:
    """文件元数据"""
    file_id: str
    filename: str
    size: int
    content_type: str
    checksum: str
    storage_path: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "size": self.size,
            "content_type": self.content_type,
            "checksum": self.checksum,
            "storage_path": self.storage_path,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


class FileStorage:
    """文件存储"""

    def __init__(self, base_path: str = "storage"):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._files: Dict[str, FileMetadata] = {}
        self._logger = get_logger("file.storage")

    def _generate_id(self, filename: str) -> str:
        """生成文件ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_input = f"{filename}_{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"{timestamp}_{hash_value}"

    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def upload(self, filename: str, content: bytes,
               metadata: Optional[Dict[str, Any]] = None) -> FileMetadata:
        """上传文件"""
        file_id = self._generate_id(filename)
        storage_dir = self._base_path / file_id[:8]
        storage_dir.mkdir(exist_ok=True)
        storage_path = storage_dir / file_id

        with open(storage_path, "wb") as f:
            f.write(content)

        checksum = self._calculate_checksum(str(storage_path))
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        file_meta = FileMetadata(
            file_id=file_id,
            filename=filename,
            size=len(content),
            content_type=content_type,
            checksum=checksum,
            storage_path=str(storage_path),
            created_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        self._files[file_id] = file_meta
        self._logger.info(f"File uploaded: {file_id}, size: {len(content)} bytes")
        return file_meta

    def download(self, file_id: str) -> Optional[bytes]:
        """下载文件"""
        file_meta = self._files.get(file_id)
        if not file_meta:
            return None

        file_path = Path(file_meta.storage_path)
        if not file_path.exists():
            return None

        with open(file_path, "rb") as f:
            return f.read()

    def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """获取文件元数据"""
        return self._files.get(file_id)

    def delete(self, file_id: str) -> bool:
        """删除文件"""
        file_meta = self._files.get(file_id)
        if not file_meta:
            return False

        file_path = Path(file_meta.storage_path)
        if file_path.exists():
            file_path.unlink()

        del self._files[file_id]
        self._logger.info(f"File deleted: {file_id}")
        return True

    def list_files(self) -> List[FileMetadata]:
        """列出所有文件"""
        return list(self._files.values())

    def verify_checksum(self, file_id: str) -> bool:
        """验证文件校验和"""
        file_meta = self._files.get(file_id)
        if not file_meta:
            return False

        current_checksum = self._calculate_checksum(file_meta.storage_path)
        return current_checksum == file_meta.checksum

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_size = sum(f.size for f in self._files.values())
        return {
            "total_files": len(self._files),
            "total_size": total_size,
            "base_path": str(self._base_path)
        }


class ChunkedUploader:
    """分片上传器"""

    def __init__(self, storage: FileStorage):
        self._storage = storage
        self._chunks: Dict[str, List[bytes]] = {}
        self._logger = get_logger("file.chunked")

    def upload_chunk(self, upload_id: str, chunk_index: int,
                     chunk_data: bytes) -> bool:
        """上传分片"""
        if upload_id not in self._chunks:
            self._chunks[upload_id] = []

        # 确保列表足够长
        while len(self._chunks[upload_id]) <= chunk_index:
            self._chunks[upload_id].append(b"")

        self._chunks[upload_id][chunk_index] = chunk_data
        return True

    def complete_upload(self, upload_id: str, filename: str,
                        metadata: Optional[Dict[str, Any]] = None) -> Optional[FileMetadata]:
        """完成分片上传"""
        chunks = self._chunks.get(upload_id)
        if not chunks:
            return None

        content = b"".join(chunks)
        result = self._storage.upload(filename, content, metadata)

        del self._chunks[upload_id]
        self._logger.info(f"Chunked upload completed: {result.file_id}")
        return result

    def get_uploaded_chunks(self, upload_id: str) -> int:
        """获取已上传的分片数"""
        chunks = self._chunks.get(upload_id, [])
        return sum(1 for c in chunks if c)


# 全局实例
_storage: Optional[FileStorage] = None


def get_file_storage() -> FileStorage:
    """获取全局文件存储"""
    global _storage
    if _storage is None:
        _storage = FileStorage()
    return _storage
