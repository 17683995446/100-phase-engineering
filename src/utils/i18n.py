"""
国际化与本地化系统
提供多语言支持、翻译管理、区域格式化和文化适配功能
"""
import re
import json
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.structured_logging import get_logger


@dataclass
class LocaleConfig:
    """区域配置"""
    locale: str
    language: str
    territory: str = ""
    currency: str = "USD"
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    number_format: str = ",."
    translations: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "locale": self.locale,
            "language": self.language,
            "territory": self.territory,
            "currency": self.currency,
            "date_format": self.date_format,
            "time_format": self.time_format,
            "datetime_format": self.datetime_format
        }


class Translator:
    """翻译器"""

    def __init__(self):
        self._translations: Dict[str, Dict[str, str]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("i18n.translator")

    def load_translations(self, locale: str,
                          translations: Dict[str, str]) -> None:
        """加载翻译"""
        with self._lock:
            if locale not in self._translations:
                self._translations[locale] = {}
            self._translations[locale].update(translations)

    def translate(self, key: str, locale: str,
                  **kwargs) -> str:
        """翻译键值"""
        with self._lock:
            translations = self._translations.get(locale, {})
            text = translations.get(key, key)

        # 替换占位符
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass

        return text

    def has_translation(self, key: str, locale: str) -> bool:
        """检查是否有翻译"""
        with self._lock:
            return key in self._translations.get(locale, {})

    def get_available_locales(self) -> List[str]:
        """获取可用区域"""
        with self._lock:
            return list(self._translations.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "locales": len(self._translations),
                "total_keys": sum(len(t) for t in self._translations.values())
            }


class LocaleFormatter:
    """区域格式化器"""

    def __init__(self):
        self._locales: Dict[str, LocaleConfig] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("i18n.formatter")

    def register_locale(self, config: LocaleConfig) -> None:
        """注册区域配置"""
        with self._lock:
            self._locales[config.locale] = config

    def format_date(self, date: datetime, locale: str) -> str:
        """格式化日期"""
        with self._lock:
            config = self._locales.get(locale)
            if not config:
                return date.strftime("%Y-%m-%d")
            return date.strftime(config.date_format)

    def format_time(self, time: datetime, locale: str) -> str:
        """格式化时间"""
        with self._lock:
            config = self._locales.get(locale)
            if not config:
                return time.strftime("%H:%M:%S")
            return time.strftime(config.time_format)

    def format_datetime(self, dt: datetime, locale: str) -> str:
        """格式化日期时间"""
        with self._lock:
            config = self._locales.get(locale)
            if not config:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return dt.strftime(config.datetime_format)

    def format_number(self, number: float, locale: str,
                      decimals: int = 2) -> str:
        """格式化数字"""
        with self._lock:
            config = self._locales.get(locale)
            if not config:
                return f"{number:,.{decimals}f}"

            fmt = f"{{:,.{decimals}f}}"
            result = fmt.format(number)

            # 根据区域配置替换分隔符
            if config.number_format:
                thousand_sep = config.number_format[0]
                decimal_sep = config.number_format[1] if len(config.number_format) > 1 else "."
                # 先替换小数点，再替换千位分隔符，避免冲突
                result = result.replace(".", "|DECIMAL|")
                result = result.replace(",", thousand_sep)
                result = result.replace("|DECIMAL|", decimal_sep)

            return result

    def format_currency(self, amount: float, locale: str) -> str:
        """格式化货币"""
        with self._lock:
            config = self._locales.get(locale)
            currency = config.currency if config else "USD"
            formatted = self.format_number(amount, locale, 2)
            return f"{currency} {formatted}"

    def get_locale(self, locale: str) -> Optional[LocaleConfig]:
        """获取区域配置"""
        with self._lock:
            return self._locales.get(locale)

    def list_locales(self) -> List[str]:
        """列出所有区域"""
        with self._lock:
            return list(self._locales.keys())


class I18nManager:
    """国际化管理器"""

    def __init__(self, default_locale: str = "en"):
        self._default_locale = default_locale
        self._current_locale = default_locale
        self._translator = Translator()
        self._formatter = LocaleFormatter()
        self._lock = threading.RLock()
        self._logger = get_logger("i18n.manager")

    def set_locale(self, locale: str) -> None:
        """设置当前区域"""
        with self._lock:
            self._current_locale = locale

    def get_locale(self) -> str:
        """获取当前区域"""
        with self._lock:
            return self._current_locale

    def t(self, key: str, **kwargs) -> str:
        """翻译（使用当前区域）"""
        return self._translator.translate(key, self._current_locale, **kwargs)

    def translate(self, key: str, locale: Optional[str] = None,
                  **kwargs) -> str:
        """翻译"""
        loc = locale or self._current_locale
        return self._translator.translate(key, loc, **kwargs)

    def load_translations(self, locale: str,
                          translations: Dict[str, str]) -> None:
        """加载翻译"""
        self._translator.load_translations(locale, translations)

    def register_locale(self, config: LocaleConfig) -> None:
        """注册区域配置"""
        self._formatter.register_locale(config)

    def format_date(self, date: datetime, locale: Optional[str] = None) -> str:
        """格式化日期"""
        loc = locale or self._current_locale
        return self._formatter.format_date(date, loc)

    def format_time(self, time: datetime, locale: Optional[str] = None) -> str:
        """格式化时间"""
        loc = locale or self._current_locale
        return self._formatter.format_time(time, loc)

    def format_datetime(self, dt: datetime,
                        locale: Optional[str] = None) -> str:
        """格式化日期时间"""
        loc = locale or self._current_locale
        return self._formatter.format_datetime(dt, loc)

    def format_number(self, number: float, locale: Optional[str] = None,
                      decimals: int = 2) -> str:
        """格式化数字"""
        loc = locale or self._current_locale
        return self._formatter.format_number(number, loc, decimals)

    def format_currency(self, amount: float,
                        locale: Optional[str] = None) -> str:
        """格式化货币"""
        loc = locale or self._current_locale
        return self._formatter.format_currency(amount, loc)

    def get_available_locales(self) -> List[str]:
        """获取可用区域"""
        return self._translator.get_available_locales()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "current_locale": self._current_locale,
            "default_locale": self._default_locale,
            "translator": self._translator.get_stats(),
            "formatter_locales": len(self._formatter.list_locales())
        }


# 全局实例
_i18n: Optional[I18nManager] = None


def get_i18n_manager() -> I18nManager:
    """获取全局国际化管理器"""
    global _i18n
    if _i18n is None:
        _i18n = I18nManager()
    return _i18n
