#!/usr/bin/env python3
"""
Tools Base Interface
工具基础接口，包含监控、诊断、校准、维护等工具
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union
import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging

from ..common.interfaces.base_component import BaseComponent, ComponentType, ComponentStatus
from ..common.messages.robot_messages import DualArmRobotState


class ToolType(Enum):
    """工具类型枚举"""
    MONITORING = "monitoring"
    DIAGNOSTICS = "diagnostics"
    CALIBRATION = "calibration"
    MAINTENANCE = "maintenance"
    LOGGING = "logging"
    VISUALIZATION = "visualization"


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MaintenanceType(Enum):
    """维护类型枚举"""
    PREVENTIVE = "preventive"      # 预防性维护
    CORRECTIVE = "corrective"      # 纠正性维护
    PREDICTIVE = "predictive"      # 预测性维护
    EMERGENCY = "emergency"        # 紧急维护


@dataclass
class Alert:
    """告警信息"""
    alert_id: str
    component_id: str
    alert_level: AlertLevel
    message: str
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricData:
    """指标数据"""
    metric_name: str
    value: Union[float, int, str, bool]
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class DiagnosticResult:
    """诊断结果"""
    test_name: str
    component_id: str
    status: str  # "pass", "fail", "warning", "unknown"
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class CalibrationResult:
    """校准结果"""
    calibration_type: str
    component_id: str
    success: bool
    timestamp: datetime
    parameters_before: Dict[str, Any]
    parameters_after: Dict[str, Any]
    accuracy_improvement: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class MaintenanceTask:
    """维护任务"""
    task_id: str
    task_type: MaintenanceType
    component_id: str
    description: str
    scheduled_time: datetime
    estimated_duration: timedelta
    priority: int = 1
    status: str = "pending"  # pending, in_progress, completed, failed, cancelled
    assigned_to: Optional[str] = None
    completion_time: Optional[datetime] = None
    notes: str = ""


class BaseTool(BaseComponent):
    """
    工具基类
    定义了所有运维工具的通用接口
    """
    
    def __init__(self, tool_id: str, tool_type: ToolType):
        super().__init__(tool_id, ComponentType.TOOL)
        self.tool_type = tool_type
        self.is_active = False
        self.configuration: Dict[str, Any] = {}
        self.data_storage: Dict[str, Any] = {}
        
    @abstractmethod
    async def run_tool(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行工具
        Args:
            parameters: 工具参数
        Returns:
            Dict[str, Any]: 工具运行结果
        """
        pass
    
    @abstractmethod
    async def get_tool_status(self) -> Dict[str, Any]:
        """
        获取工具状态
        Returns:
            Dict[str, Any]: 工具状态信息
        """
        pass
    
    def configure(self, config: Dict[str, Any]):
        """配置工具"""
        self.configuration.update(config)
    
    def get_configuration(self) -> Dict[str, Any]:
        """获取工具配置"""
        return self.configuration.copy()
    
    async def activate(self) -> bool:
        """激活工具"""
        self.is_active = True
        self.logger.info(f"Tool {self.component_id} activated")
        return True
    
    async def deactivate(self) -> bool:
        """停用工具"""
        self.is_active = False
        self.logger.info(f"Tool {self.component_id} deactivated")
        return True


class MonitoringTool(BaseTool):
    """
    监控工具基类
    用于监控系统状态和性能指标
    """
    
    def __init__(self, tool_id: str):
        super().__init__(tool_id, ToolType.MONITORING)
        self.metrics: Dict[str, List[MetricData]] = {}
        self.alerts: List[Alert] = []
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self.monitoring_interval = 1.0  # 秒
        self._monitoring_task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def collect_metrics(self) -> List[MetricData]:
        """
        收集指标数据
        Returns:
            List[MetricData]: 指标数据列表
        """
        pass
    
    @abstractmethod
    async def check_thresholds(self, metrics: List[MetricData]) -> List[Alert]:
        """
        检查阈值并生成告警
        Args:
            metrics: 指标数据
        Returns:
            List[Alert]: 告警列表
        """
        pass
    
    def set_threshold(self, metric_name: str, warning: float, critical: float):
        """设置指标阈值"""
        self.thresholds[metric_name] = {
            "warning": warning,
            "critical": critical
        }
    
    def add_metric(self, metric: MetricData):
        """添加指标数据"""
        if metric.metric_name not in self.metrics:
            self.metrics[metric.metric_name] = []
        
        self.metrics[metric.metric_name].append(metric)
        
        # 保持最近1000个数据点
        if len(self.metrics[metric.metric_name]) > 1000:
            self.metrics[metric.metric_name] = self.metrics[metric.metric_name][-1000:]
    
    def add_alert(self, alert: Alert):
        """添加告警"""
        self.alerts.append(alert)
        self.logger.warning(f"Alert generated: {alert.message}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def get_metrics_history(self, metric_name: str, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[MetricData]:
        """获取指标历史数据"""
        if metric_name not in self.metrics:
            return []
        
        metrics = self.metrics[metric_name]
        
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        return metrics
    
    async def start_monitoring(self):
        """开始监控"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """停止监控"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_active and not self.should_stop():
            try:
                # 收集指标
                metrics = await self.collect_metrics()
                for metric in metrics:
                    self.add_metric(metric)
                
                # 检查阈值
                alerts = await self.check_thresholds(metrics)
                for alert in alerts:
                    self.add_alert(alert)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1.0)


class DiagnosticTool(BaseTool):
    """
    诊断工具基类
    用于系统健康检查和故障诊断
    """
    
    def __init__(self, tool_id: str):
        super().__init__(tool_id, ToolType.DIAGNOSTICS)
        self.diagnostic_tests: Dict[str, Callable] = {}
        self.test_results: List[DiagnosticResult] = []
    
    def register_test(self, test_name: str, test_function: Callable):
        """注册诊断测试"""
        self.diagnostic_tests[test_name] = test_function
    
    async def run_test(self, test_name: str, component_id: str, 
                      parameters: Dict[str, Any] = None) -> DiagnosticResult:
        """
        运行单个诊断测试
        Args:
            test_name: 测试名称
            component_id: 组件ID
            parameters: 测试参数
        Returns:
            DiagnosticResult: 诊断结果
        """
        if test_name not in self.diagnostic_tests:
            return DiagnosticResult(
                test_name=test_name,
                component_id=component_id,
                status="unknown",
                message=f"Test {test_name} not found",
                timestamp=datetime.now()
            )
        
        try:
            test_function = self.diagnostic_tests[test_name]
            result = await test_function(component_id, parameters or {})
            result.timestamp = datetime.now()
            self.test_results.append(result)
            return result
            
        except Exception as e:
            result = DiagnosticResult(
                test_name=test_name,
                component_id=component_id,
                status="fail",
                message=f"Test failed with exception: {str(e)}",
                timestamp=datetime.now()
            )
            self.test_results.append(result)
            return result
    
    async def run_all_tests(self, component_id: str) -> List[DiagnosticResult]:
        """运行所有诊断测试"""
        results = []
        for test_name in self.diagnostic_tests:
            result = await self.run_test(test_name, component_id)
            results.append(result)
        return results
    
    async def run_health_check(self, components: List[str]) -> Dict[str, List[DiagnosticResult]]:
        """运行健康检查"""
        health_results = {}
        for component_id in components:
            health_results[component_id] = await self.run_all_tests(component_id)
        return health_results
    
    def get_test_history(self, test_name: str, component_id: str) -> List[DiagnosticResult]:
        """获取测试历史"""
        return [result for result in self.test_results 
                if result.test_name == test_name and result.component_id == component_id]


class CalibrationTool(BaseTool):
    """
    校准工具基类
    用于设备校准和参数调优
    """
    
    def __init__(self, tool_id: str):
        super().__init__(tool_id, ToolType.CALIBRATION)
        self.calibration_procedures: Dict[str, Callable] = {}
        self.calibration_results: List[CalibrationResult] = {}
    
    def register_calibration_procedure(self, calibration_type: str, procedure: Callable):
        """注册校准程序"""
        self.calibration_procedures[calibration_type] = procedure
    
    async def calibrate(self, calibration_type: str, component_id: str,
                       parameters: Dict[str, Any] = None) -> CalibrationResult:
        """
        执行校准
        Args:
            calibration_type: 校准类型
            component_id: 组件ID
            parameters: 校准参数
        Returns:
            CalibrationResult: 校准结果
        """
        if calibration_type not in self.calibration_procedures:
            return CalibrationResult(
                calibration_type=calibration_type,
                component_id=component_id,
                success=False,
                timestamp=datetime.now(),
                parameters_before={},
                parameters_after={},
                error_message=f"Calibration procedure {calibration_type} not found"
            )
        
        try:
            procedure = self.calibration_procedures[calibration_type]
            result = await procedure(component_id, parameters or {})
            result.timestamp = datetime.now()
            self.calibration_results.append(result)
            return result
            
        except Exception as e:
            result = CalibrationResult(
                calibration_type=calibration_type,
                component_id=component_id,
                success=False,
                timestamp=datetime.now(),
                parameters_before={},
                parameters_after={},
                error_message=str(e)
            )
            self.calibration_results.append(result)
            return result
    
    def get_calibration_history(self, component_id: str) -> List[CalibrationResult]:
        """获取校准历史"""
        return [result for result in self.calibration_results 
                if result.component_id == component_id]


class MaintenanceTool(BaseTool):
    """
    维护工具基类
    用于设备维护管理
    """
    
    def __init__(self, tool_id: str):
        super().__init__(tool_id, ToolType.MAINTENANCE)
        self.maintenance_tasks: List[MaintenanceTask] = []
        self.maintenance_procedures: Dict[str, Callable] = {}
        self.maintenance_schedules: Dict[str, Dict[str, Any]] = {}
    
    def register_maintenance_procedure(self, procedure_name: str, procedure: Callable):
        """注册维护程序"""
        self.maintenance_procedures[procedure_name] = procedure
    
    def schedule_maintenance(self, task: MaintenanceTask):
        """安排维护任务"""
        self.maintenance_tasks.append(task)
        self.logger.info(f"Maintenance task scheduled: {task.task_id}")
    
    def get_pending_tasks(self) -> List[MaintenanceTask]:
        """获取待执行的维护任务"""
        return [task for task in self.maintenance_tasks if task.status == "pending"]
    
    def get_overdue_tasks(self) -> List[MaintenanceTask]:
        """获取过期的维护任务"""
        now = datetime.now()
        return [task for task in self.maintenance_tasks 
                if task.status == "pending" and task.scheduled_time < now]
    
    async def execute_maintenance_task(self, task_id: str) -> bool:
        """执行维护任务"""
        task = next((t for t in self.maintenance_tasks if t.task_id == task_id), None)
        if not task:
            return False
        
        try:
            task.status = "in_progress"
            
            # 执行维护程序
            if task.description in self.maintenance_procedures:
                procedure = self.maintenance_procedures[task.description]
                await procedure(task.component_id, {})
            
            task.status = "completed"
            task.completion_time = datetime.now()
            self.logger.info(f"Maintenance task completed: {task_id}")
            return True
            
        except Exception as e:
            task.status = "failed"
            task.notes = str(e)
            self.logger.error(f"Maintenance task failed: {task_id}, error: {e}")
            return False
    
    def update_maintenance_schedule(self, component_id: str, schedule: Dict[str, Any]):
        """更新维护计划"""
        self.maintenance_schedules[component_id] = schedule
    
    async def generate_maintenance_plan(self, time_horizon: timedelta) -> List[MaintenanceTask]:
        """生成维护计划"""
        plan = []
        end_time = datetime.now() + time_horizon
        
        for component_id, schedule in self.maintenance_schedules.items():
            # 根据计划生成维护任务
            # 这里可以实现更复杂的计划逻辑
            pass
        
        return plan


class ToolManager(BaseComponent):
    """
    工具管理器
    统一管理所有运维工具
    """
    
    def __init__(self):
        super().__init__("tool_manager", ComponentType.TOOL)
        self.tools: Dict[str, BaseTool] = {}
        self.tool_registry: Dict[ToolType, List[str]] = {}
    
    def register_tool(self, tool: BaseTool):
        """注册工具"""
        self.tools[tool.component_id] = tool
        
        if tool.tool_type not in self.tool_registry:
            self.tool_registry[tool.tool_type] = []
        self.tool_registry[tool.tool_type].append(tool.component_id)
        
        self.logger.info(f"Tool registered: {tool.component_id}")
    
    def unregister_tool(self, tool_id: str):
        """取消注册工具"""
        if tool_id in self.tools:
            tool = self.tools[tool_id]
            del self.tools[tool_id]
            
            if tool.tool_type in self.tool_registry:
                if tool_id in self.tool_registry[tool.tool_type]:
                    self.tool_registry[tool.tool_type].remove(tool_id)
            
            self.logger.info(f"Tool unregistered: {tool_id}")
    
    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        """获取工具"""
        return self.tools.get(tool_id)
    
    def get_tools_by_type(self, tool_type: ToolType) -> List[BaseTool]:
        """根据类型获取工具"""
        if tool_type not in self.tool_registry:
            return []
        
        return [self.tools[tool_id] for tool_id in self.tool_registry[tool_type]
                if tool_id in self.tools]
    
    async def run_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """运行工具"""
        tool = self.get_tool(tool_id)
        if not tool:
            return None
        
        try:
            return await tool.run_tool(parameters)
        except Exception as e:
            self.logger.error(f"Error running tool {tool_id}: {e}")
            return None
    
    async def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
            "alerts": [],
            "metrics": {}
        }
        
        # 收集监控工具的数据
        monitoring_tools = self.get_tools_by_type(ToolType.MONITORING)
        for tool in monitoring_tools:
            if isinstance(tool, MonitoringTool):
                active_alerts = tool.get_active_alerts()
                health_data["alerts"].extend([
                    {
                        "alert_id": alert.alert_id,
                        "component_id": alert.component_id,
                        "level": alert.alert_level.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat()
                    } for alert in active_alerts
                ])
        
        # 收集诊断工具的数据
        diagnostic_tools = self.get_tools_by_type(ToolType.DIAGNOSTICS)
        for tool in diagnostic_tools:
            if isinstance(tool, DiagnosticTool):
                # 获取最近的测试结果
                recent_results = tool.test_results[-10:] if tool.test_results else []
                for result in recent_results:
                    if result.component_id not in health_data["components"]:
                        health_data["components"][result.component_id] = []
                    
                    health_data["components"][result.component_id].append({
                        "test_name": result.test_name,
                        "status": result.status,
                        "message": result.message,
                        "timestamp": result.timestamp.isoformat()
                    })
        
        # 确定整体状态
        if any(alert["level"] in ["error", "critical"] for alert in health_data["alerts"]):
            health_data["overall_status"] = "critical"
        elif any(alert["level"] == "warning" for alert in health_data["alerts"]):
            health_data["overall_status"] = "warning"
        
        return health_data