# Phase 25: 缓存管理系统

## 阶段概述

**阶段名称**: 缓存管理系统
**完成状态**: ✅ 已完成
**测试结果**: 37个测试用例全部通过
**系统总测试**: 408个测试全部通过（37+371）

## 核心设计原则

遵循 **成本最小公理**: 通过缓存计算结果，降低重复计算成本，提升系统性能。

## 核心架构

### 缓存策略枚举

```python
class CacheStrategy(Enum):
    LRU = auto()       # 最近最少使用
    LFU = auto()       # 最不经常使用
    FIFO = auto()      # 先进先出
    MRU = auto()       # 最近使用
    RANDOM = auto()    # 随机淘汰
```

### 缓存层级枚举

```python
class CacheLevel(Enum):
    L1 = auto()        # 一级缓存（内存）
    L2 = auto()        # 二级缓存
    L3 = auto()        # 三级缓存
```

## 主要组件

### 数据结构

#### CacheEntry
缓存条目数据结构，包含：
- 键值对
- 创建时间
- 过期时间（可选）
- 访问次数
- 最后访问时间

#### CacheStats
缓存统计结构，包含：
- 命中数
- 未命中数
- 淘汰数
- 设置数
- 删除数
- 命中率
- 当前和最大大小

### 缓存实现

#### BaseCache (基类)
所有缓存策略的基类，提供：
- 基本的 set/get/delete 操作
- TTL 过期管理
- 线程安全锁
- 统计跟踪

#### LRUCache (Least Recently Used)
- 最近最少使用策略
- 使用 OrderedDict 实现访问顺序
- 访问数据时移至末尾
- 淘汰头部（最久未使用）数据

#### LFUCache (Least Frequently Used)
- 最不经常使用策略
- 跟踪每个键的访问频率
- 淘汰访问频率最低的数据
- 相同频率时随机淘汰

#### FIFOCache (First In First Out)
- 先进先出策略
- 简单的队列结构
- 最早插入的数据最先淘汰

#### MRUCache (Most Recently Used)
- 最近使用策略
- 与 LRU 相反
- 淘汰最近访问的数据

#### RandomCache
- 随机淘汰策略
- 适合无特定模式的数据

### 工厂函数

```python
def create_cache(
    strategy: CacheStrategy,
    max_size: int = 1000,
    default_ttl: Optional[int] = None
) -> BaseCache:
    """创建指定策略的缓存实例"""
```

### CacheManager (缓存管理器)

统一管理多个缓存：
- 注册/注销缓存
- 获取或创建缓存
- 多级缓存（L1/L2/L3）管理
- 获取所有缓存统计
- 批量失效

### 装饰器支持

#### @cached
便捷装饰器，自动缓存函数结果：
```python
@cached(name="my_cache", strategy=CacheStrategy.LRU, max_size=1000, ttl=3600)
def expensive_calculation(x):
    return x * 2
```

#### @cache_result
基于指定缓存的装饰器，更灵活：
```python
cache = LRUCache(max_size=100)
@cache_result(cache=cache, ttl=3600, key_prefix="calc_")
def calc(x):
    return x * x
```

### 缓存失效工具

```python
invalidate_cache("cache_name")  # 失效指定缓存
invalidate_pattern("user_")     # 按模式批量失效
```

## 功能特性

### 1. TTL 过期
- 支持键级 TTL
- 支持默认 TTL
- 过期自动清理

### 2. 线程安全
- RLock 互斥锁
- 多线程安全读写

### 3. 统计监控
- 实时命中率统计
- 访问计数跟踪
- 性能监控

### 4. 多级缓存
- L1/L2/L3 分层管理
- 灵活配置各级策略

### 5. 失效策略
- 单个缓存失效
- 模式匹配批量失效
- 手动清空

## 使用示例

### 基本使用
```python
from src.utils.cache import LRUCache

cache = LRUCache(max_size=1000, default_ttl=3600)
cache.set("key", "value")
value = cache.get("key")
```

### 使用装饰器
```python
from src.utils.cache import cached

@cached(name="fib_cache", max_size=100)
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

### 缓存管理
```python
from src.utils.cache import CacheManager, CacheStrategy

manager = CacheManager()
cache = manager.register_cache("api_results", CacheStrategy.LFU, max_size=500)
stats = manager.get_all_stats()
```

## 测试覆盖

| 测试类别 | 用例数 | 状态 |
|---------|--------|------|
| 数据结构 | 5 | ✅ |
| LRU缓存 | 9 | ✅ |
| LFU缓存 | 3 | ✅ |
| FIFO缓存 | 2 | ✅ |
| MRU缓存 | 2 | ✅ |
| Random缓存 | 2 | ✅ |
| 工厂函数 | 1 | ✅ |
| 管理器 | 6 | ✅ |
| 装饰器 | 2 | ✅ |
| 失效工具 | 2 | ✅ |
| 默认管理器 | 1 | ✅ |
| 集成测试 | 3 | ✅ |
| 线程安全 | 1 | ✅ |
| **总计** | **37** | **✅** |

## 系统集成

### 与现有模块结合
- [src/utils/logger](file:///workspace/src/utils/logger.py): 日志记录缓存命中/未命中
- [src/config/persistence](file:///workspace/src/config/persistence.py): 可结合持久化配置
- 所有层模块：均可通过装饰器使用缓存

### 推荐应用场景
- 重复计算的函数结果
- 频繁访问的配置
- 代理响应缓存
- 数据库查询结果
- 渲染模板

## 性能优化建议

1. **选择合适策略**:
   - 有热点数据 → LRU
   - 访问频率有差异 → LFU
   - 简单队列 → FIFO

2. **合理设置大小**:
   - 过小 → 频繁淘汰
   - 过大 → 内存浪费

3. **使用 TTL**:
   - 避免脏数据
   - 自动清理陈旧数据

4. **监控命中率**:
   - 优化策略选择
   - 调整缓存大小

## 文件清单

| 文件路径 | 描述 |
|---------|------|
| [src/utils/cache.py](file:///workspace/src/utils/cache.py) | 缓存管理系统核心实现 |
| [test_cache.py](file:///workspace/test_cache.py) | 37个测试用例 |
| [src/utils/__init__.py](file:///workspace/src/utils/__init__.py) | 模块导出更新 |
| [PHASE_25_SUMMARY.md](file:///workspace/PHASE_25_SUMMARY.md) | 本阶段总结 |

## 下一阶段 (Phase 26)

可选方向：
- 日志系统增强（结构化日志）
- 指标收集系统（Prometheus格式）
- 分布式追踪集成（OpenTelemetry）
- API接口层（REST/GraphQL）
