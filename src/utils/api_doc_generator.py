"""
API文档生成器
提供API解析、文档生成、OpenAPI导出和版本管理功能
"""
import json
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class HttpMethod(Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIParameter:
    """API参数"""
    name: str
    param_type: str
    required: bool = False
    description: str = ""
    default: Any = None
    location: str = "query"  # query, path, body, header

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.param_type,
            "required": self.required,
            "description": self.description,
            "default": self.default,
            "in": self.location
        }


@dataclass
class APIEndpoint:
    """API端点"""
    path: str
    method: HttpMethod
    summary: str = ""
    description: str = ""
    parameters: List[APIParameter] = field(default_factory=list)
    responses: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method.value,
            "summary": self.summary,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "responses": self.responses,
            "tags": self.tags,
            "deprecated": self.deprecated
        }


@dataclass
class APIDocument:
    """API文档"""
    title: str
    version: str
    description: str = ""
    endpoints: List[APIEndpoint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "metadata": self.metadata
        }


class APIDocGenerator:
    """API文档生成器"""

    def __init__(self):
        self._documents: Dict[str, APIDocument] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("api.doc")

    def create_document(self, doc_id: str, title: str, version: str,
                        description: str = "") -> APIDocument:
        """创建文档"""
        with self._lock:
            if doc_id in self._documents:
                raise ValueError(f"Document {doc_id} already exists")

            doc = APIDocument(
                title=title,
                version=version,
                description=description
            )
            self._documents[doc_id] = doc
            return doc

    def get_document(self, doc_id: str) -> Optional[APIDocument]:
        """获取文档"""
        with self._lock:
            return self._documents.get(doc_id)

    def add_endpoint(self, doc_id: str, endpoint: APIEndpoint) -> bool:
        """添加端点"""
        with self._lock:
            doc = self._documents.get(doc_id)
            if not doc:
                return False

            doc.endpoints.append(endpoint)
            return True

    def remove_endpoint(self, doc_id: str, path: str,
                        method: HttpMethod) -> bool:
        """移除端点"""
        with self._lock:
            doc = self._documents.get(doc_id)
            if not doc:
                return False

            for i, ep in enumerate(doc.endpoints):
                if ep.path == path and ep.method == method:
                    doc.endpoints.pop(i)
                    return True
            return False

    def export_openapi(self, doc_id: str) -> Optional[str]:
        """导出OpenAPI格式"""
        with self._lock:
            doc = self._documents.get(doc_id)
            if not doc:
                return None

            openapi = {
                "openapi": "3.0.0",
                "info": {
                    "title": doc.title,
                    "version": doc.version,
                    "description": doc.description
                },
                "paths": {}
            }

            for endpoint in doc.endpoints:
                if endpoint.path not in openapi["paths"]:
                    openapi["paths"][endpoint.path] = {}

                openapi["paths"][endpoint.path][endpoint.method.value.lower()] = {
                    "summary": endpoint.summary,
                    "description": endpoint.description,
                    "parameters": [p.to_dict() for p in endpoint.parameters],
                    "responses": endpoint.responses,
                    "tags": endpoint.tags,
                    "deprecated": endpoint.deprecated
                }

            return json.dumps(openapi, indent=2, ensure_ascii=False)

    def export_markdown(self, doc_id: str) -> Optional[str]:
        """导出Markdown格式"""
        with self._lock:
            doc = self._documents.get(doc_id)
            if not doc:
                return None

            lines = [
                f"# {doc.title}",
                f"",
                f"Version: {doc.version}",
                f"",
                f"{doc.description}",
                f"",
                f"## Endpoints",
                f""
            ]

            for endpoint in doc.endpoints:
                lines.append(f"### {endpoint.method.value} {endpoint.path}")
                lines.append(f"")
                lines.append(f"{endpoint.summary}")
                if endpoint.description:
                    lines.append(f"")
                    lines.append(f"{endpoint.description}")
                lines.append(f"")

                if endpoint.parameters:
                    lines.append(f"**Parameters:**")
                    lines.append(f"")
                    lines.append(f"| Name | Type | Required | Location | Description |")
                    lines.append(f"|------|------|----------|----------|-------------|")
                    for param in endpoint.parameters:
                        lines.append(
                            f"| {param.name} | {param.param_type} | "
                            f"{'Yes' if param.required else 'No'} | "
                            f"{param.location} | {param.description} |"
                        )
                    lines.append(f"")

                if endpoint.responses:
                    lines.append(f"**Responses:**")
                    for code, response in endpoint.responses.items():
                        lines.append(f"- {code}: {response}")
                    lines.append(f"")

                if endpoint.deprecated:
                    lines.append(f"> **Deprecated**")
                    lines.append(f"")

            return "\n".join(lines)

    def list_documents(self) -> List[APIDocument]:
        """列出文档"""
        with self._lock:
            return list(self._documents.values())

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        with self._lock:
            if doc_id in self._documents:
                del self._documents[doc_id]
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_endpoints = sum(len(d.endpoints) for d in self._documents.values())
            return {
                "total_documents": len(self._documents),
                "total_endpoints": total_endpoints
            }


# 全局实例
_generator: Optional[APIDocGenerator] = None


def get_api_doc_generator() -> APIDocGenerator:
    """获取全局API文档生成器"""
    global _generator
    if _generator is None:
        _generator = APIDocGenerator()
    return _generator
