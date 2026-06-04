"""
模板引擎
提供模板解析、变量替换和条件渲染功能
"""
import re
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class TemplateEngine:
    """模板引擎"""
    
    def __init__(self):
        self._templates: Dict[str, str] = {}
        self._filters: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("template.engine")
        self._register_default_filters()
    
    def _register_default_filters(self) -> None:
        """注册默认过滤器"""
        self._filters["upper"] = str.upper
        self._filters["lower"] = str.lower
        self._filters["title"] = str.title
        self._filters["trim"] = str.strip
        self._filters["length"] = len
        self._filters["default"] = lambda value, default="": value if value else default
    
    def register_template(self, name: str, template: str) -> None:
        """注册模板"""
        with self._lock:
            self._templates[name] = template
    
    def register_filter(self, name: str, func: Callable) -> None:
        """注册过滤器"""
        with self._lock:
            self._filters[name] = func
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """渲染模板"""
        with self._lock:
            template = self._templates.get(template_name)
        
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        return self._render_string(template, context)
    
    def render_string(self, template: str, context: Dict[str, Any]) -> str:
        """渲染字符串"""
        return self._render_string(template, context)
    
    def _render_string(self, template: str, context: Dict[str, Any]) -> str:
        """渲染字符串实现"""
        result = template
        
        # 处理条件语句
        result = self._process_conditionals(result, context)
        
        # 处理循环
        result = self._process_loops(result, context)
        
        # 处理变量
        result = self._process_variables(result, context)
        
        return result
    
    def _process_variables(self, template: str, context: Dict[str, Any]) -> str:
        """处理变量"""
        def replace_var(match):
            var_expr = match.group(1).strip()
            return self._resolve_variable(var_expr, context)
        
        return re.sub(r'\{\{\s*(.+?)\s*\}\}', replace_var, template)
    
    def _resolve_variable(self, expr: str, context: Dict[str, Any]) -> str:
        """解析变量表达式"""
        parts = expr.split('|')
        var_name = parts[0].strip()
        
        # 获取值
        value = self._get_value(var_name, context)
        
        # 应用过滤器
        for filter_expr in parts[1:]:
            filter_expr = filter_expr.strip()
            filter_name = filter_expr.split(':')[0].strip()
            filter_args = filter_expr.split(':')[1:] if ':' in filter_expr else []
            
            filter_func = self._filters.get(filter_name)
            if filter_func:
                try:
                    if filter_args:
                        value = filter_func(value, *filter_args)
                    else:
                        value = filter_func(value)
                except Exception:
                    pass
        
        return str(value) if value is not None else ""
    
    def _get_value(self, var_name: str, context: Dict[str, Any]) -> Any:
        """获取变量值"""
        parts = var_name.split('.')
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    def _process_conditionals(self, template: str, context: Dict[str, Any]) -> str:
        """处理条件语句"""
        pattern = r'\{%\s*if\s+(.+?)\s*%\}(.*?)\{%\s*endif\s*%\}'
        
        def replace_cond(match):
            condition = match.group(1).strip()
            content = match.group(2)
            
            if self._evaluate_condition(condition, context):
                return content
            return ""
        
        return re.sub(pattern, replace_cond, template, flags=re.DOTALL)
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件"""
        # 简单条件：变量存在且为真
        value = self._get_value(condition, context)
        return bool(value)
    
    def _process_loops(self, template: str, context: Dict[str, Any]) -> str:
        """处理循环"""
        pattern = r'\{%\s*for\s+(\w+)\s+in\s+(.+?)\s*%\}(.*?)\{%\s*endfor\s*%\}'
        
        def replace_loop(match):
            var_name = match.group(1)
            collection_expr = match.group(2).strip()
            content = match.group(3)
            
            collection = self._get_value(collection_expr, context)
            if not collection:
                return ""
            
            results = []
            for item in collection:
                loop_context = dict(context)
                loop_context[var_name] = item
                results.append(self._render_string(content, loop_context))
            
            return "".join(results)
        
        return re.sub(pattern, replace_loop, template, flags=re.DOTALL)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "templates": len(self._templates),
                "filters": len(self._filters)
            }


# 全局实例
_engine: Optional[TemplateEngine] = None


def get_template_engine() -> TemplateEngine:
    """获取模板引擎"""
    global _engine
    if _engine is None:
        _engine = TemplateEngine()
    return _engine
