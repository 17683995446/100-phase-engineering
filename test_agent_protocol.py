"""
Agent协作协议和消息路由验证测试
"""

import pytest
from datetime import datetime
from src.agent_layer.protocol import (
    MessageProtocol,
    MessagePriority,
    RoutingStrategy,
    MessageEnvelope,
    RoutingRule,
    MessageFilter,
    PriorityMessageQueue,
    MessageRouter,
    AgentCollaborationProtocol,
    get_collaboration_protocol,
    send_request,
    send_command,
    broadcast_event
)
from src.agent_layer.agent_roles import AgentMessage


class TestMessageProtocol:
    """测试消息协议"""
    
    def test_protocol_values(self):
        """测试协议枚举值"""
        assert MessageProtocol.REQUEST is not None
        assert MessageProtocol.RESPONSE is not None
        assert MessageProtocol.EVENT is not None
        assert MessageProtocol.COMMAND is not None
        assert MessageProtocol.QUERY is not None
        assert MessageProtocol.NOTIFICATION is not None


class TestMessagePriority:
    """测试消息优先级"""
    
    def test_priority_values(self):
        """测试优先级枚举值"""
        assert MessagePriority.CRITICAL.value == 0
        assert MessagePriority.HIGH.value == 1
        assert MessagePriority.NORMAL.value == 2
        assert MessagePriority.LOW.value == 3
        assert MessagePriority.BACKGROUND.value == 4


class TestRoutingStrategy:
    """测试路由策略"""
    
    def test_strategy_values(self):
        """测试策略枚举值"""
        assert RoutingStrategy.DIRECT is not None
        assert RoutingStrategy.BROADCAST is not None
        assert RoutingStrategy.ROUND_ROBIN is not None
        assert RoutingStrategy.LEAST_LOADED is not None
        assert RoutingStrategy.CONTENT_BASED is not None


class TestMessageEnvelope:
    """测试消息信封"""
    
    def test_envelope_creation(self):
        """测试创建信封"""
        envelope = MessageEnvelope(
            envelope_id="env-001",
            protocol=MessageProtocol.REQUEST,
            priority=MessagePriority.NORMAL,
            timestamp=datetime.now()
        )
        
        assert envelope.envelope_id == "env-001"
        assert envelope.protocol == MessageProtocol.REQUEST
        assert envelope.ttl == 300
        assert envelope.retry_count == 0
    
    def test_envelope_to_dict(self):
        """测试信封序列化"""
        envelope = MessageEnvelope(
            envelope_id="env-002",
            protocol=MessageProtocol.EVENT,
            priority=MessagePriority.HIGH,
            timestamp=datetime.now()
        )
        
        result = envelope.to_dict()
        
        assert isinstance(result, dict)
        assert result["envelope_id"] == "env-002"
        assert result["protocol"] == "EVENT"


class TestRoutingRule:
    """测试路由规则"""
    
    def test_rule_creation(self):
        """测试创建规则"""
        rule = RoutingRule(
            rule_id="rule-001",
            name="测试规则",
            source_pattern="agent-a",
            target_pattern="agent-b",
            routing_strategy=RoutingStrategy.DIRECT
        )
        
        assert rule.rule_id == "rule-001"
        assert rule.enabled is True
    
    def test_rule_matches(self):
        """测试规则匹配"""
        rule = RoutingRule(
            rule_id="rule-002",
            name="匹配规则",
            source_pattern="agent-a",
            target_pattern="*",
            routing_strategy=RoutingStrategy.DIRECT
        )
        
        message = AgentMessage(
            message_id="msg-001",
            sender="agent-a",
            receiver="agent-b",
            content="test",
            message_type="request",
            timestamp=datetime.now()
        )
        
        assert rule.matches(message) is True
    
    def test_rule_not_matches(self):
        """测试规则不匹配"""
        rule = RoutingRule(
            rule_id="rule-003",
            name="不匹配规则",
            source_pattern="agent-a",
            target_pattern="*",
            routing_strategy=RoutingStrategy.DIRECT
        )
        
        message = AgentMessage(
            message_id="msg-002",
            sender="agent-b",
            receiver="agent-c",
            content="test",
            message_type="request",
            timestamp=datetime.now()
        )
        
        assert rule.matches(message) is False
    
    def test_wildcard_pattern(self):
        """测试通配符模式"""
        rule = RoutingRule(
            rule_id="rule-004",
            name="通配符规则",
            source_pattern="*",
            target_pattern="*",
            routing_strategy=RoutingStrategy.BROADCAST
        )
        
        message = AgentMessage(
            message_id="msg-003",
            sender="any-agent",
            receiver="any-agent",
            content="test",
            message_type="event",
            timestamp=datetime.now()
        )
        
        assert rule.matches(message) is True


class TestMessageFilter:
    """测试消息过滤器"""
    
    def test_filter_creation(self):
        """测试创建过滤器"""
        filter_def = MessageFilter(
            filter_id="filter-001",
            name="测试过滤器",
            filter_type="content",
            condition=lambda m: len(m.content) > 0
        )
        
        assert filter_def.filter_id == "filter-001"
        assert filter_def.priority == 0
    
    def test_filter_apply(self):
        """测试过滤器应用"""
        filter_def = MessageFilter(
            filter_id="filter-002",
            name="长度过滤",
            filter_type="length",
            condition=lambda m: len(m.content) >= 5
        )
        
        message = AgentMessage(
            message_id="msg-004",
            sender="agent-a",
            receiver="agent-b",
            content="hello world",
            message_type="request",
            timestamp=datetime.now()
        )
        
        assert filter_def.apply(message) is True


class TestPriorityMessageQueue:
    """测试优先级消息队列"""
    
    def test_queue_creation(self):
        """测试创建队列"""
        queue = PriorityMessageQueue(max_size=100)
        
        assert queue.size() == 0
        assert queue.max_size == 100
    
    def test_enqueue(self):
        """测试入队"""
        queue = PriorityMessageQueue()
        
        message = AgentMessage(
            message_id="msg-005",
            sender="agent-a",
            receiver="agent-b",
            content="test",
            message_type="request",
            timestamp=datetime.now()
        )
        
        result = queue.enqueue(message, MessagePriority.HIGH)
        
        assert result is True
        assert queue.size() == 1
    
    def test_dequeue(self):
        """测试出队"""
        queue = PriorityMessageQueue()
        
        message1 = AgentMessage(
            message_id="msg-006",
            sender="agent-a",
            receiver="agent-b",
            content="low priority",
            message_type="request",
            timestamp=datetime.now()
        )
        
        message2 = AgentMessage(
            message_id="msg-007",
            sender="agent-a",
            receiver="agent-b",
            content="high priority",
            message_type="request",
            timestamp=datetime.now()
        )
        
        queue.enqueue(message1, MessagePriority.LOW)
        queue.enqueue(message2, MessagePriority.HIGH)
        
        dequeued = queue.dequeue()
        
        assert dequeued is not None
        assert dequeued.message_id == "msg-007"
    
    def test_priority_ordering(self):
        """测试优先级排序"""
        queue = PriorityMessageQueue()
        
        for i in range(5):
            message = AgentMessage(
                message_id=f"msg-{i}",
                sender="agent-a",
                receiver="agent-b",
                content=f"message {i}",
                message_type="request",
                timestamp=datetime.now()
            )
            queue.enqueue(message, MessagePriority.NORMAL)
        
        queue.enqueue(AgentMessage(
            message_id="msg-critical",
            sender="agent-a",
            receiver="agent-b",
            content="critical",
            message_type="request",
            timestamp=datetime.now()
        ), MessagePriority.CRITICAL)
        
        first = queue.dequeue()
        assert first.message_id == "msg-critical"


class TestMessageRouter:
    """测试消息路由器"""
    
    def test_router_creation(self):
        """测试创建路由器"""
        router = MessageRouter()
        
        assert len(router.rules) == 0
        assert len(router.filters) == 0
    
    def test_add_rule(self):
        """测试添加规则"""
        router = MessageRouter()
        
        rule = RoutingRule(
            rule_id="rule-005",
            name="测试规则",
            source_pattern="*",
            target_pattern="*",
            routing_strategy=RoutingStrategy.DIRECT
        )
        
        router.add_rule(rule)
        
        assert len(router.rules) == 1
    
    def test_route_message(self):
        """测试路由消息"""
        router = MessageRouter()
        
        message = AgentMessage(
            message_id="msg-008",
            sender="agent-a",
            receiver="agent-b",
            content="test",
            message_type="request",
            timestamp=datetime.now()
        )
        
        targets = router.route_message(message, ["agent-b", "agent-c"])
        
        assert "agent-b" in targets


class TestAgentCollaborationProtocol:
    """测试Agent协作协议"""
    
    def test_protocol_creation(self):
        """测试创建协议"""
        protocol = AgentCollaborationProtocol()
        
        assert protocol is not None
        assert len(protocol.router.rules) > 0
    
    def test_create_envelope(self):
        """测试创建信封"""
        protocol = AgentCollaborationProtocol()
        
        message = AgentMessage(
            message_id="msg-009",
            sender="agent-a",
            receiver="agent-b",
            content="test",
            message_type="request",
            timestamp=datetime.now()
        )
        
        envelope = protocol.create_envelope(
            message=message,
            protocol=MessageProtocol.REQUEST
        )
        
        assert envelope.protocol == MessageProtocol.REQUEST
        assert envelope.raw_message is not None
    
    def test_send_with_protocol(self):
        """测试使用协议发送"""
        protocol = AgentCollaborationProtocol()
        
        message = protocol.send_with_protocol(
            sender="agent-a",
            receiver="agent-b",
            content="Hello",
            protocol=MessageProtocol.REQUEST
        )
        
        assert message.sender == "agent-a"
        assert message.receiver == "agent-b"
        assert message.message_type == "request"
    
    def test_enqueue_dequeue(self):
        """测试入队出队"""
        protocol = AgentCollaborationProtocol()
        
        message = AgentMessage(
            message_id="msg-010",
            sender="agent-a",
            receiver="agent-b",
            content="test",
            message_type="request",
            timestamp=datetime.now()
        )
        
        protocol.enqueue_message("agent-b", message, MessagePriority.NORMAL)
        
        dequeued = protocol.dequeue_message("agent-b")
        
        assert dequeued is not None
        assert dequeued.message_id == "msg-010"
    
    def test_mark_delivered(self):
        """测试标记已送达"""
        protocol = AgentCollaborationProtocol()
        
        protocol.mark_delivered("msg-011")
        
        assert protocol.is_delivered("msg-011") is True
        assert protocol.is_delivered("msg-012") is False
    
    def test_create_response(self):
        """测试创建响应"""
        protocol = AgentCollaborationProtocol()
        
        original = AgentMessage(
            message_id="msg-original",
            sender="agent-a",
            receiver="agent-b",
            content="Request",
            message_type="request",
            timestamp=datetime.now()
        )
        
        response = protocol.create_response(original, "Response content")
        
        assert response.sender == "agent-b"
        assert response.receiver == "agent-a"
        assert response.reply_to == "msg-original"
    
    def test_get_statistics(self):
        """测试获取统计"""
        protocol = AgentCollaborationProtocol()
        
        stats = protocol.get_statistics()
        
        assert "total_queues" in stats
        assert "total_rules" in stats
        assert "total_filters" in stats


def test_send_request():
    """测试发送请求"""
    message = send_request(
        sender="agent-orchestrator",
        receiver="agent-analyzer",
        content="Analyze this"
    )
    
    assert message.sender == "agent-orchestrator"
    assert message.receiver == "agent-analyzer"


def test_send_command():
    """测试发送命令"""
    message = send_command(
        sender="agent-orchestrator",
        receiver="agent-developer",
        content="Start coding"
    )
    
    assert message.sender == "agent-orchestrator"
    assert message.message_type == "command"


def test_broadcast_event():
    """测试广播事件"""
    messages = broadcast_event(
        sender="agent-orchestrator",
        content="Task completed",
        receivers=["agent-a", "agent-b"]
    )
    
    assert len(messages) == 2


def test_get_global_protocol():
    """测试获取全局协议"""
    protocol1 = get_collaboration_protocol()
    protocol2 = get_collaboration_protocol()
    
    assert protocol1 is protocol2
