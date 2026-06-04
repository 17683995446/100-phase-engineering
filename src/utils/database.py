"""
数据库连接池与ORM集成
提供连接池管理、基础ORM和CRUD操作功能
"""
import sqlite3
import threading
import queue
import time
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, get_type_hints
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager
from abc import ABC, abstractmethod

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


T = TypeVar('T', bound='Model')


@dataclass
class ConnectionPoolConfig:
    """连接池配置"""
    max_connections: int = 10
    min_connections: int = 2
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0
    max_retries: int = 3
    retry_delay: float = 1.0


class ConnectionPool:
    """数据库连接池"""
    
    def __init__(self, database_path: str, config: Optional[ConnectionPoolConfig] = None):
        self.database_path = database_path
        self.config = config or ConnectionPoolConfig()
        self._pool: queue.Queue = queue.Queue(maxsize=self.config.max_connections)
        self._active_connections: int = 0
        self._lock = threading.Lock()
        self._logger = get_logger("database.pool")
        self._closed = False
        
        # 初始化最小连接数
        self._initialize_pool()
    
    def _create_connection(self) -> sqlite3.Connection:
        """创建新连接"""
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _initialize_pool(self) -> None:
        """初始化连接池"""
        for _ in range(self.config.min_connections):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
                self._active_connections += 1
            except Exception as e:
                self._logger.error(f"Failed to create initial connection: {e}")
    
    @contextmanager
    def get_connection(self):
        """获取连接（上下文管理器）"""
        conn = None
        try:
            conn = self._acquire_connection()
            yield conn
        finally:
            if conn:
                self._release_connection(conn)
    
    def _acquire_connection(self) -> sqlite3.Connection:
        """获取连接"""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        # 尝试从池中获取
        try:
            conn = self._pool.get(timeout=self.config.connection_timeout)
            # 验证连接是否有效
            try:
                conn.execute("SELECT 1")
                return conn
            except Exception:
                conn.close()
                self._active_connections -= 1
        except queue.Empty:
            pass
        
        # 创建新连接
        with self._lock:
            if self._active_connections < self.config.max_connections:
                for attempt in range(self.config.max_retries):
                    try:
                        conn = self._create_connection()
                        self._active_connections += 1
                        return conn
                    except Exception as e:
                        self._logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                        if attempt < self.config.max_retries - 1:
                            time.sleep(self.config.retry_delay)
                
                raise RuntimeError("Failed to create database connection after retries")
            else:
                raise RuntimeError("Connection pool exhausted")
    
    def _release_connection(self, conn: sqlite3.Connection) -> None:
        """释放连接"""
        if self._closed:
            conn.close()
            return
        
        try:
            # 尝试放回池中
            self._pool.put_nowait(conn)
        except queue.Full:
            # 池已满，关闭连接
            conn.close()
            with self._lock:
                self._active_connections -= 1
    
    def close(self) -> None:
        """关闭连接池"""
        self._closed = True
        
        # 关闭所有连接
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except queue.Empty:
                break
        
        self._logger.info("Connection pool closed")
    
    def execute(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行查询"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            conn.commit()
            return [dict(row) for row in rows]
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行"""
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        return {
            "database_path": self.database_path,
            "max_connections": self.config.max_connections,
            "min_connections": self.config.min_connections,
            "active_connections": self._active_connections,
            "available_connections": self._pool.qsize(),
            "closed": self._closed
        }


class Model(ABC):
    """ORM基础模型"""
    
    _table_name: str = ""
    _primary_key: str = "id"
    _pool: Optional[ConnectionPool] = None
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def set_pool(cls, pool: ConnectionPool) -> None:
        """设置连接池"""
        cls._pool = pool
    
    @classmethod
    def get_pool(cls) -> ConnectionPool:
        """获取连接池"""
        if cls._pool is None:
            raise RuntimeError("Connection pool not set")
        return cls._pool
    
    @classmethod
    def _get_fields(cls) -> Dict[str, type]:
        """获取字段类型"""
        return get_type_hints(cls)
    
    @classmethod
    def _get_create_table_sql(cls) -> str:
        """生成建表SQL"""
        fields = cls._get_fields()
        columns = []
        
        for field_name, field_type in fields.items():
            if field_name.startswith('_'):
                continue
            
            sql_type = cls._python_type_to_sql(field_type)
            nullable = "NOT NULL" if field_name == cls._primary_key else ""
            
            if field_name == cls._primary_key:
                columns.append(f"{field_name} {sql_type} PRIMARY KEY AUTOINCREMENT")
            else:
                columns.append(f"{field_name} {sql_type} {nullable}")
        
        return f"CREATE TABLE IF NOT EXISTS {cls._table_name} ({', '.join(columns)})"
    
    @classmethod
    def _python_type_to_sql(cls, python_type: type) -> str:
        """Python类型转SQL类型"""
        type_mapping = {
            int: "INTEGER",
            str: "TEXT",
            float: "REAL",
            bool: "INTEGER",
            datetime: "TEXT",
            Optional[int]: "INTEGER",
            Optional[str]: "TEXT",
            Optional[float]: "REAL",
        }
        return type_mapping.get(python_type, "TEXT")
    
    @classmethod
    def create_table(cls) -> None:
        """创建表"""
        sql = cls._get_create_table_sql()
        cls.get_pool().execute(sql)
    
    @classmethod
    def drop_table(cls) -> None:
        """删除表"""
        sql = f"DROP TABLE IF EXISTS {cls._table_name}"
        cls.get_pool().execute(sql)
    
    def save(self) -> 'Model':
        """保存记录"""
        fields = self._get_fields()
        field_names = [f for f in fields.keys() if not f.startswith('_') and f != self._primary_key]
        
        values = []
        for field_name in field_names:
            value = getattr(self, field_name, None)
            if isinstance(value, datetime):
                value = value.isoformat()
            values.append(value)
        
        placeholders = ', '.join(['?' for _ in field_names])
        columns = ', '.join(field_names)
        
        sql = f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})"
        
        pool = self.get_pool()
        with pool.get_connection() as conn:
            cursor = conn.execute(sql, tuple(values))
            conn.commit()
            
            # 获取自增ID
            if hasattr(self, self._primary_key) and getattr(self, self._primary_key) is None:
                setattr(self, self._primary_key, cursor.lastrowid)
        
        return self
    
    @classmethod
    def find_by_id(cls: Type[T], id: int) -> Optional[T]:
        """根据ID查找"""
        sql = f"SELECT * FROM {cls._table_name} WHERE {cls._primary_key} = ?"
        results = cls.get_pool().execute(sql, (id,))
        
        if results:
            return cls(**results[0])
        return None
    
    @classmethod
    def find_all(cls: Type[T], limit: int = 100, offset: int = 0) -> List[T]:
        """查找所有记录"""
        sql = f"SELECT * FROM {cls._table_name} LIMIT ? OFFSET ?"
        results = cls.get_pool().execute(sql, (limit, offset))
        return [cls(**row) for row in results]
    
    @classmethod
    def find_by(cls: Type[T], **kwargs) -> List[T]:
        """根据条件查找"""
        conditions = []
        values = []
        
        for key, value in kwargs.items():
            conditions.append(f"{key} = ?")
            values.append(value)
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {cls._table_name} WHERE {where_clause}"
        
        results = cls.get_pool().execute(sql, tuple(values))
        return [cls(**row) for row in results]
    
    def update(self) -> 'Model':
        """更新记录"""
        fields = self._get_fields()
        field_names = [f for f in fields.keys() if not f.startswith('_') and f != self._primary_key]
        
        set_clauses = []
        values = []
        
        for field_name in field_names:
            value = getattr(self, field_name, None)
            if isinstance(value, datetime):
                value = value.isoformat()
            set_clauses.append(f"{field_name} = ?")
            values.append(value)
        
        # 添加主键值
        primary_key_value = getattr(self, self._primary_key)
        values.append(primary_key_value)
        
        set_clause = ', '.join(set_clauses)
        sql = f"UPDATE {self._table_name} SET {set_clause} WHERE {self._primary_key} = ?"
        
        self.get_pool().execute(sql, tuple(values))
        return self
    
    def delete(self) -> bool:
        """删除记录"""
        primary_key_value = getattr(self, self._primary_key)
        sql = f"DELETE FROM {self._table_name} WHERE {self._primary_key} = ?"
        
        result = self.get_pool().execute(sql, (primary_key_value,))
        return True
    
    @classmethod
    def delete_by_id(cls, id: int) -> bool:
        """根据ID删除"""
        sql = f"DELETE FROM {cls._table_name} WHERE {cls._primary_key} = ?"
        cls.get_pool().execute(sql, (id,))
        return True
    
    @classmethod
    def count(cls) -> int:
        """获取记录数"""
        sql = f"SELECT COUNT(*) as count FROM {cls._table_name}"
        result = cls.get_pool().execute(sql)
        return result[0]['count'] if result else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        fields = self._get_fields()
        result = {}
        for field_name in fields.keys():
            if not field_name.startswith('_'):
                value = getattr(self, field_name, None)
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[field_name] = value
        return result


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_path: str = "app.db"):
        self.database_path = database_path
        self.pool = ConnectionPool(database_path)
        self._models: List[Type[Model]] = []
        self._logger = get_logger("database.manager")
    
    def register_model(self, model_class: Type[Model]) -> None:
        """注册模型"""
        model_class.set_pool(self.pool)
        self._models.append(model_class)
        self._logger.info(f"Registered model: {model_class.__name__}")
    
    def create_all_tables(self) -> None:
        """创建所有表"""
        for model in self._models:
            model.create_table()
            self._logger.info(f"Created table: {model._table_name}")
    
    def drop_all_tables(self) -> None:
        """删除所有表"""
        for model in self._models:
            model.drop_table()
            self._logger.info(f"Dropped table: {model._table_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计"""
        return {
            "database_path": self.database_path,
            "registered_models": len(self._models),
            "model_names": [m.__name__ for m in self._models],
            "pool_stats": self.pool.get_stats()
        }
    
    def close(self) -> None:
        """关闭数据库"""
        self.pool.close()
        self._logger.info("Database manager closed")


# 全局实例
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(database_path: str = "app.db") -> DatabaseManager:
    """获取数据库管理器"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_path)
    return _db_manager
