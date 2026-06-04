"""
核心架构协调器
四层架构整合和工作流驱动
"""

from typing import Dict, Any, Optional
from datetime import datetime

from src.input_layer import TaskInputHandler
from src.scheduling_layer import WorkflowEngine
from src.agent_layer import SimpleAgent, SimpleTeam
from src.execution_layer import CodeAnalyzer, CodeChecker, TestRunner
from src.config.constants import TaskType, AgentRole
from src.utils.logger import logger


class FourLayerOrchestrator:
    """
    四层架构协调器
    将输入层-调度层-Agent层-执行层整合起来
    """
    
    def __init__(self):
        logger.info("初始化四层架构协调器")
        
        # 初始化各层组件
        self.input_handler = TaskInputHandler()
        self.workflow_engine = WorkflowEngine()
        self.agent_team = SimpleTeam()
        self.code_analyzer = CodeAnalyzer()
        self.code_checker = CodeChecker()
        self.test_runner = TestRunner()
        
        # 注册Agent
        self._init_agent_team()
        
        logger.info("四层架构协调器初始化完成")
    
    def _init_agent_team(self):
        """初始化Agent团队"""
        self.agent_team.add_agent(SimpleAgent(AgentRole.ORCHESTRATOR, "总控协调Agent"))
        self.agent_team.add_agent(SimpleAgent(AgentRole.ANALYZER, "需求分析Agent"))
        self.agent_team.add_agent(SimpleAgent(AgentRole.ARCHITECT, "架构设计Agent"))
        self.agent_team.add_agent(SimpleAgent(AgentRole.DEVELOPER, "开发编码Agent"))
        self.agent_team.add_agent(SimpleAgent(AgentRole.REVIEWER, "代码评审Agent"))
        self.agent_team.add_agent(SimpleAgent(AgentRole.TESTER, "测试验证Agent"))
        self.agent_team.add_agent(SimpleAgent(AgentRole.DOCUMENTER, "文档归档Agent"))
        logger.info("Agent团队初始化完成")
    
    def execute_task(
        self,
        task_description: str,
        task_type: TaskType = TaskType.REQUIREMENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行完整任务流程
        
        Args:
            task_description: 任务描述
            task_type: 任务类型
            metadata: 元数据
            
        Returns:
            完整的执行结果
        """
        start_time = datetime.now()
        task_id = None
        
        try:
            logger.info("=" * 60)
            logger.info("开始执行新任务")
            logger.info("=" * 60)
            
            # 第1层: 输入层 - 任务接收和预处理
            logger.info("--- Layer 1: 输入层 ---")
            processed_task = self.input_handler.receive_task(
                task_description=task_description,
                task_type=task_type,
                metadata=metadata
            )
            task_id = processed_task["task_id"]
            
            # 第2层: 调度层 - 工作流调度
            logger.info("--- Layer 2: 调度层 ---")
            workflow_result = self.workflow_engine.execute(
                task_id=task_id,
                initial_state={"task": processed_task}
            )
            
            # 第3层: Agent层 - 智能协作（简化版流程）
            logger.info("--- Layer 3: Agent层 ---")
            agent_result = self._execute_agent_collaboration(processed_task)
            
            # 第4层: 执行层 - 代码处理（如果有代码）
            logger.info("--- Layer 4: 执行层 ---")
            execution_result = self._execute_code_operations(processed_task, metadata)
            
            # 整合结果
            final_result = {
                "success": True,
                "task_id": task_id,
                "start_time": start_time,
                "end_time": datetime.now(),
                "input_layer": processed_task,
                "scheduling_layer": workflow_result,
                "agent_layer": agent_result,
                "execution_layer": execution_result,
            }
            
            logger.info("=" * 60)
            logger.info("任务执行完成")
            logger.info("=" * 60)
            
            return final_result
            
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "task_id": task_id,
                "start_time": start_time,
                "end_time": datetime.now(),
                "error": str(e),
            }
    
    def _execute_agent_collaboration(self, processed_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Agent协作流程
        
        Args:
            processed_task: 处理后的任务
            
        Returns:
            Agent协作结果
        """
        result = {
            "agents_used": [],
            "conversation_count": 0,
            "steps": []
        }
        
        # 简单的协作流程
        task_description = processed_task["description"]
        
        # 总控协调
        coord_result = self.agent_team.send_message(
            AgentRole.ORCHESTRATOR,
            AgentRole.ANALYZER,
            f"请分析以下任务: {task_description}"
        )
        result["agents_used"].append("ORCHESTRATOR")
        result["agents_used"].append("ANALYZER")
        result["steps"].append("协调→分析")
        result["conversation_count"] += 1
        
        # 分析后传递给开发者
        dev_result = self.agent_team.send_message(
            AgentRole.ANALYZER,
            AgentRole.DEVELOPER,
            f"基于分析结果，请实现功能: {task_description}"
        )
        result["agents_used"].append("DEVELOPER")
        result["steps"].append("分析→开发")
        result["conversation_count"] += 1
        
        # 开发者传递给评审
        rev_result = self.agent_team.send_message(
            AgentRole.DEVELOPER,
            AgentRole.REVIEWER,
            "请评审代码质量"
        )
        result["agents_used"].append("REVIEWER")
        result["steps"].append("开发→评审")
        result["conversation_count"] += 1
        
        # 最终结果
        result["agent_messages"] = [
            coord_result.get("response", ""),
            dev_result.get("response", ""),
            rev_result.get("response", ""),
        ]
        
        return result
    
    def _execute_code_operations(
        self,
        processed_task: Dict[str, Any],
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行代码操作
        
        Args:
            processed_task: 处理后的任务
            metadata: 元数据
            
        Returns:
            执行结果
        """
        result = {
            "code_analyzed": False,
            "code_checked": False,
            "tests_run": False,
            "details": {}
        }
        
        # 如果元数据中包含代码，则执行操作
        if metadata and "code" in metadata:
            code = metadata["code"]
            
            # 代码分析
            analysis = self.code_analyzer.analyze_python_file(code)
            result["code_analyzed"] = True
            result["details"]["analysis"] = analysis
            
            # 代码检查
            check = self.code_checker.check_atomic_compliance(code)
            result["code_checked"] = True
            result["details"]["check"] = check
            
            # 如果有测试代码，运行测试
            if "test_code" in metadata:
                test_result = self.test_runner.run_tests_from_code(
                    code,
                    metadata["test_code"]
                )
                result["tests_run"] = True
                result["details"]["tests"] = test_result
        
        return result
