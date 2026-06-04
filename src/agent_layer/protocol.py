"""
Agent协作协议和消息路由系统
信息最小熵公理：消息路由高效、协议标准化
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from src.agent_layer.agent_roles import AgentMessage
from src.utils.logger import logger


class MessageProtocol(Enum):
    """消息协议类型"""
    REQUEST = auto()
    RESPONSE = auto()
    EVENT = auto()
    COMMAND = auto()
    QUERY = auto()
    NOTIFICATION = auto()


class MessagePriority(Enum):
    """消息优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class RoutingStrategy(Enum):
    """路由策略"""
    DIRECT = auto()
    BROADCAST = auto()
    ROUND_ROBIN = auto()
    LEAST_LOADED = auto()
    CONTENT_BASED = auto()


@dataclass
class MessageEnvelope:
    """消息信封 - 包装原始消息"""
    envelope_id: str
    protocol: MessageProtocol
    priority: MessagePriority
    timestamp: datetime
    ttl: int = 300
    retry_count: int = 0
    max_retries: int = 3
    headers: dict[str, str] = field(default_factory=dict)
    raw_message: AgentMessage | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "protocol": self.protocol.name,
            "priority": self.priority.name,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "headers": self.headers,
            "raw_message": self.raw_message.to_dict() if self.raw_message else None
        }


@dataclass
class RoutingRule:
    """路由规则"""
    rule_id: str
    name: str
    source_pattern: str
    target_pattern: str
    routing_strategy: RoutingStrategy
    filter_conditions: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True

    def matches(self, message: AgentMessage) -> bool:
        """检查消息是否匹配规则"""
        if not self.enabled:
            return False

        if self.source_pattern != "*" and message.sender != self.source_pattern:
            return False

        if self.source_pattern.startswith("role:"):
            role_pattern = self.source_pattern[5:]
            if not re.match(role_pattern, message.sender):
                return False

        return True

    def get_target(self, message: AgentMessage, available_agents: list[str]) -> list[str]:
        """获取目标Agent列表"""
        if self.routing_strategy == RoutingStrategy.DIRECT:
            return [message.receiver] if message.receiver in available_agents else []

        elif self.routing_strategy == RoutingStrategy.BROADCAST:
            return [a for a in available_agents if a != message.sender]

        elif self.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            return [available_agents[0]] if available_agents else []

        elif self.routing_strategy == RoutingStrategy.LEAST_LOADED:
            return [available_agents[0]] if available_agents else []

        return []


@dataclass
class MessageFilter:
    """消息过滤器"""
    filter_id: str
    name: str
    filter_type: str
    condition: Callable[[AgentMessage], bool]
    action: str = "pass"
    priority: int = 0

    def apply(self, message: AgentMessage) -> bool:
        """应用过滤器"""
        try:
            return self.condition(message)
        except Exception:
            return True


class PriorityMessageQueue:
    """优先级消息队列"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queue: list[tuple[int, AgentMessage]] = []
        self._current_index = 0

    def enqueue(self, message: AgentMessage, priority: MessagePriority = MessagePriority.NORMAL) -> bool:
        """入队"""
        if len(self._queue) >= self.max_size:
            logger.warning(f"消息队列已满: {len(self._queue)}")
            return False

        item = (priority.value, self._current_index, message)
        self._current_index += 1
        self._queue.append(item)
        self._queue.sort(key=lambda x: (x[0], x[1]))
        return True

    def dequeue(self) -> AgentMessage | None:
        """出队"""
        if not self._queue:
            return None

        _, _, message = self._queue.pop(0)
        return message

    def peek(self) -> AgentMessage | None:
        """查看队首"""
        if not self._queue:
            return None
        return self._queue[0][2]

    def size(self) -> int:
        """队列大小"""
        return len(self._queue)

    def clear(self):
        """清空队列"""
        self._queue.clear()
        self._current_index = 0


class MessageRouter:
    """消息路由器"""

    def __init__(self):
        self.rules: dict[str, RoutingRule] = {}
        self.filters: list[MessageFilter] = []
        self.route_cache: dict[str, list[str]] = {}
        self.route_count: dict[str, int] = {}
        logger.info("初始化消息路由器")

    def add_rule(self, rule: RoutingRule):
        """添加路由规则"""
        self.rules[rule.rule_id] = rule
        logger.debug(f"添加路由规则: {rule.name}")

    def remove_rule(self, rule_id: str):
        """移除路由规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.debug(f"移除路由规则: {rule_id}")

    def add_filter(self, filter_def: MessageFilter):
        """添加过滤器"""
        self.filters.append(filter_def)
        self.filters.sort(key=lambda x: x.priority)
        logger.debug(f"添加过滤器: {filter_def.name}")

    def apply_filters(self, message: AgentMessage) -> bool:
        """应用过滤器"""
        for msg_filter in self.filters:
            result = msg_filter.apply(message)
            if not result:
                logger.debug(f"消息被过滤器拦截: {msg_filter.name}")
                return False
        return True

    def find_matching_rule(self, message: AgentMessage) -> RoutingRule | None:
        """查找匹配的路由规则"""
        for rule in sorted(self.rules.values(), key=lambda x: x.priority, reverse=True):
            if rule.matches(message):
                return rule
        return None

    def route_message(self, message: AgentMessage, available_agents: list[str]) -> list[str]:
        """路由消息"""
        if not self.apply_filters(message):
            return []

        matching_rule = self.find_matching_rule(message)

        if matching_rule:
            targets = matching_rule.get_target(message, available_agents)
            logger.debug(f"规则路由: {matching_rule.name} -> {targets}")
            return targets

        if message.receiver and message.receiver in available_agents:
            return [message.receiver]

        return []

    def clear_cache(self):
        """清空路由缓存"""
        self.route_cache.clear()
        self.route_count.clear()


class AgentCollaborationProtocol:
    """Agent协作协议"""

    def __init__(self):
        self.router = MessageRouter()
        self.message_queues: dict[str, PriorityMessageQueue] = {}
        self.delivered_messages: set[str] = set()
        self.protocol_handlers: dict[MessageProtocol, Callable] = {}
        self._setup_default_rules()
        self._setup_default_filters()
        logger.info("初始化Agent协作协议")

    def _setup_default_rules(self):
        """设置默认路由规则"""
        self.router.add_rule(RoutingRule(
            rule_id="rule_coordinator",
            name="协调器广播",
            source_pattern="agent-orchestrator",
            target_pattern="*",
            routing_strategy=RoutingStrategy.BROADCAST,
            priority=100
        ))

        self.router.add_rule(RoutingRule(
            rule_id="rule_analyzer_to_architect",
            name="分析师到架构师",
            source_pattern="role:analyzer",
            target_pattern="role:architect",
            routing_strategy=RoutingStrategy.DIRECT,
            priority=50
        ))

        self.router.add_rule(RoutingRule(
            rule_id="rule_developer_to_reviewer",
            name="开发者到评审员",
            source_pattern="role:developer",
            target_pattern="role:reviewer",
            routing_strategy=RoutingStrategy.DIRECT,
            priority=50
        ))

        self.router.add_rule(RoutingRule(
            rule_id="rule_reviewer_to_tester",
            name="评审员到测试员",
            source_pattern="role:reviewer",
            target_pattern="role:tester",
            routing_strategy=RoutingStrategy.DIRECT,
            priority=50
        ))

    def _setup_default_filters(self):
        """设置默认过滤器"""
        self.router.add_filter(MessageFilter(
            filter_id="filter_empty_content",
            name="空内容过滤",
            filter_type="content",
            condition=lambda m: bool(m.content.strip()),
            priority=100
        ))

        self.router.add_filter(MessageFilter(
            filter_id="filter_size_limit",
            name="消息大小限制",
            filter_type="size",
            condition=lambda m: len(m.content) < 50000,
            priority=90
        ))

    def register_handler(self, protocol: MessageProtocol, handler: Callable):
        """注册协议处理器"""
        self.protocol_handlers[protocol] = handler
        logger.debug(f"注册协议处理器: {protocol.name}")

    def create_envelope(
        self,
        message: AgentMessage,
        protocol: MessageProtocol,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl: int = 300
    ) -> MessageEnvelope:
        """创建消息信封"""
        envelope = MessageEnvelope(
            envelope_id=str(uuid.uuid4()),
            protocol=protocol,
            priority=priority,
            timestamp=datetime.now(),
            ttl=ttl,
            raw_message=message
        )
        return envelope

    def send_with_protocol(
        self,
        sender: str,
        receiver: str,
        content: str,
        protocol: MessageProtocol,
        priority: MessagePriority = MessagePriority.NORMAL,
        chain_id: str | None = None,
        task_id: str | None = None
    ) -> AgentMessage:
        """使用协议发送消息"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=protocol.name.lower(),
            timestamp=datetime.now(),
            chain_id=chain_id,
            task_id=task_id
        )

        handler = self.protocol_handlers.get(protocol)
        if handler:
            handler(message)

        return message

    def route(self, message: AgentMessage, available_agents: list[str]) -> list[str]:
        """路由消息"""
        return self.router.route_message(message, available_agents)

    def get_queue(self, agent_id: str) -> PriorityMessageQueue:
        """获取Agent的消息队列"""
        if agent_id not in self.message_queues:
            self.message_queues[agent_id] = PriorityMessageQueue()
        return self.message_queues[agent_id]

    def enqueue_message(
        self,
        agent_id: str,
        message: AgentMessage,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> bool:
        """入队消息"""
        queue = self.get_queue(agent_id)
        return queue.enqueue(message, priority)

    def dequeue_message(self, agent_id: str) -> AgentMessage | None:
        """出队消息"""
        queue = self.get_queue(agent_id)
        return queue.dequeue()

    def mark_delivered(self, message_id: str):
        """标记消息已送达"""
        self.delivered_messages.add(message_id)

    def is_delivered(self, message_id: str) -> bool:
        """检查消息是否已送达"""
        return message_id in self.delivered_messages

    def create_response(
        self,
        original_message: AgentMessage,
        content: str,
        status: str = "success"
    ) -> AgentMessage:
        """创建响应消息"""
        response = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=original_message.receiver,
            receiver=original_message.sender,
            content=content,
            message_type="response",
            timestamp=datetime.now(),
            chain_id=original_message.chain_id,
            task_id=original_message.task_id,
            reply_to=original_message.message_id,
            metadata={"original_message_id": original_message.message_id, "status": status}
        )
        return response

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total_queued = sum(q.size() for q in self.message_queues.values())
        return {
            "total_queues": len(self.message_queues),
            "total_queued_messages": total_queued,
            "total_rules": len(self.router.rules),
            "total_filters": len(self.router.filters),
            "delivered_messages": len(self.delivered_messages)
        }


_global_protocol: AgentCollaborationProtocol | None = None


def get_collaboration_protocol() -> AgentCollaborationProtocol:
    """获取全局协作协议"""
    global _global_protocol
    if _global_protocol is None:
        _global_protocol = AgentCollaborationProtocol()
    return _global_protocol


def send_request(
    sender: str,
    receiver: str,
    content: str,
    chain_id: str | None = None,
    task_id: str | None = None
) -> AgentMessage:
    """发送请求消息"""
    protocol = get_collaboration_protocol()
    return protocol.send_with_protocol(
        sender=sender,
        receiver=receiver,
        content=content,
        protocol=MessageProtocol.REQUEST,
        priority=MessagePriority.NORMAL,
        chain_id=chain_id,
        task_id=task_id
    )


def send_command(
    sender: str,
    receiver: str,
    content: str,
    chain_id: str | None = None,
    task_id: str | None = None
) -> AgentMessage:
    """发送命令消息"""
    protocol = get_collaboration_protocol()
    return protocol.send_with_protocol(
        sender=sender,
        receiver=receiver,
        content=content,
        protocol=MessageProtocol.COMMAND,
        priority=MessagePriority.HIGH,
        chain_id=chain_id,
        task_id=task_id
    )


def broadcast_event(
    sender: str,
    content: str,
    receivers: list[str],
    chain_id: str | None = None,
    task_id: str | None = None
) -> list[AgentMessage]:
    """广播事件"""
    protocol = get_collaboration_protocol()
    messages = []
    for receiver in receivers:
        msg = protocol.send_with_protocol(
            sender=sender,
            receiver=receiver,
            content=content,
            protocol=MessageProtocol.EVENT,
            priority=MessagePriority.NORMAL,
            chain_id=chain_id,
            task_id=task_id
        )
        messages.append(msg)
    return messages
