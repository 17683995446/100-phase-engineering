# 项目架构说明

## 第一性原理

### 六大公理

1. **任务可分性公理** - 复杂任务可拆解至不可再分原子动作
2. **依赖单向性公理** - 整体架构与代码结构保持有向无环DAG，规避循环依赖
3. **信息最小熵公理** - 消除隐式状态、隐式逻辑，信息全显式可追溯
4. **职责正交公理** - Agent职责无重叠、无空缺，分工互补无冲突
5. **状态分离公理** - 业务、任务、系统三层状态隔离管控
6. **成本最小公理** - 按需选用组件，剔除冗余能力，精简整体架构

## 四层单向依赖架构

```
src/
├── input_layer/          # Layer 1 - 输入收敛层
│   └── (统一接收任务、类型判定、基础预处理
│
├── scheduling_layer/     # Layer 2 - 调度中枢层
│   └── (流程流转、状态管控、分支回退、全局调度
│
├── agent_layer/         # Layer 3 - 智能协作层
│   └── (多角色Agent交互、任务分发、协商会诊
│
├── execution_layer/     # Layer 4 - 原子执行层
    └── (代码解析、重构修改、规范校验、测试生成
```

### 依赖方向

```
input_layer → scheduling_layer → agent_layer → execution_layer
     ↓              ↓               ↓               ↓
  (无依赖      依赖下层    依赖下层    依赖下层
```

**严格单向依赖，下层不能依赖上层

## 目录结构详解

### 核心代码

```
multi-agent-engineering-system/
├── src/
│   ├── __init__.py
│   ├── input_layer/          # Layer 1
│   ├── scheduling_layer/     # Layer 2
│   ├── agent_layer/         # Layer 3
│   ├── execution_layer/     # Layer 4
│   ├── config/             # 配置模块
│   └── utils/              # 工具模块
├── tests/                  # 测试
├── docs/                   # 文档
├── logs/                   # 日志
├── pyproject.toml
├── requirements.txt
├── requirements.lock.txt
└── .python-version
```

## Agent角色体系（正交职责）

| 角色 | 职责 | 层级 |
|------|------|
| ORCHESTRATOR | 总控调度、收口验收 | agent_layer |
| ANALYZER | 需求拆解、影响分析 | agent_layer |
| ARCHITECT | 架构设计、边界划分 | agent_layer |
| DEVELOPER | 代码实现、重构修改 | agent_layer |
| DEBUGGER | 缺陷排查、根因定位 | agent_layer |
| REVIEWER | 代码审查、规范校验 | agent_layer |
| TESTER | 测试生成、回归验证 | agent_layer |
| DOCUMENTER | 文档生成、变更归档 | agent_layer |
