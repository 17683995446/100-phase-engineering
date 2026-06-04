"""
简单Agent实现
复用AutoGen的会话机制，但不依赖LLM，避免API key问题
"""

from typing import Dict, Any, List
from src.agent_layer.base import BaseAgent
from src.config.constants import AgentRole
from src.utils.logger import logger


class SimpleAgent(BaseAgent):
    """
    简单Agent实现
    不依赖LLM，用于演示基础通信机制
    """
    
    def __init__(self, role: AgentRole, name: str | None = None):
        super().__init__(role, name)
        self.message_history: List[Dict[str, Any]] = []
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        简单处理逻辑
        
        Args:
            input_data: 输入数据
            
        Returns:
            处理结果
        """
        logger.info(f"{self.name} 处理输入: {input_data.get('message', '')[:50]}...")
        
        # 记录消息
        self.message_history.append({
            "role": "user",
            "content": input_data.get("message", "")
        })
        
        # 简单的响应逻辑
        response = self._generate_simple_response(input_data)
        
        self.message_history.append({
            "role": "assistant",
            "content": response
        })
        
        return {
            "agent": self.name,
            "role": self.role,
            "response": response,
            "success": True
        }
    
    def _generate_simple_response(self, input_data: Dict[str, Any]) -> str:
        """
        生成简单响应
        
        Args:
            input_data: 输入数据
            
        Returns:
            响应文本
        """
        message = input_data.get("message", "")
        
        # 根据角色生成不同响应
        if self.role == AgentRole.ORCHESTRATOR:
            return f"[协调器] 已接收任务: {message[:30]}..."
        elif self.role == AgentRole.ANALYZER:
            return f"[分析师] 分析完成: {message[:30]}..."
        elif self.role == AgentRole.ARCHITECT:
            return f"[架构师] 设计完成: {message[:30]}..."
        elif self.role == AgentRole.DEVELOPER:
            return f"[开发者] 编码完成: {message[:30]}..."
        elif self.role == AgentRole.REVIEWER:
            return f"[评审] 审查通过: {message[:30]}..."
        elif self.role == AgentRole.TESTER:
            return f"[测试] 测试完成: {message[:30]}..."
        elif self.role == AgentRole.DOCUMENTER:
            return f"[文档] 文档完成: {message[:30]}..."
        else:
            return f"[{self.name}] 已处理: {message[:30]}..."


class SimpleTeam:
    """
    简单Agent团队
    实现基本的多Agent协作
    """
    
    def __init__(self):
        self.agents: Dict[AgentRole, SimpleAgent] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        logger.info("初始化简单Agent团队")
    
    def add_agent(self, agent: SimpleAgent) -> "SimpleTeam":
        """
        添加Agent到团队
        
        Args:
            agent: Agent实例
            
        Returns:
            self，支持链式调用
        """
        self.agents[agent.role] = agent
        logger.info(f"团队添加Agent: {agent.name}")
        return self
    
    def send_message(
        self,
        from_role: AgentRole,
        to_role: AgentRole,
        message: str
    ) -> Dict[str, Any]:
        """
        从一个Agent向另一个Agent发送消息
        
        Args:
            from_role: 发送者角色
            to_role: 接收者角色
            message: 消息内容
            
        Returns:
            响应结果
        """
        if to_role not in self.agents:
            raise ValueError(f"目标Agent不存在: {to_role}")
        
        sender = self.agents.get(from_role, None)
        sender_name = sender.name if sender else "system"
        
        logger.info(f"{sender_name} -> {self.agents[to_role].name}: {message[:50]}...")
        
        # 记录对话
        self.conversation_history.append({
            "from": sender_name,
            "to": self.agents[to_role].name,
            "message": message
        })
        
        # 目标Agent处理
        result = self.agents[to_role].process({
            "message": message,
            "from": sender_name
        })
        
        self.conversation_history.append({
            "from": self.agents[to_role].name,
            "to": sender_name,
            "message": result["response"]
        })
        
        return result
    
    def get_conversation_summary(self) -> List[Dict[str, Any]]:
        """
        获取对话摘要
        
        Returns:
            对话历史
        """
        return self.conversation_history
