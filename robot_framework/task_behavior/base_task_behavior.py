#!/usr/bin/env python3
"""
Task Behavior Base Interface
任务行为基础接口，包含任务规划、动作序列和原子动作
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

from ..common.interfaces.base_component import BaseComponent, ComponentType
from ..common.messages.robot_messages import (
    TaskCommand, ManipulationCommand, ManipulationAction, ArmSide, Pose
)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PLANNING = "planning"
    READY = "ready"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionStatus(Enum):
    """动作状态枚举"""
    WAITING = "waiting"
    INITIALIZING = "initializing"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    EMERGENCY = 4


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[timedelta]:
        """任务执行时长"""
        if self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class ActionResult:
    """动作结果"""
    action_id: str
    status: ActionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result_data: Dict[str, Any] = field(default_factory=dict)


class BaseTask(ABC):
    """
    任务基类
    定义了任务的基本接口和生命周期
    """
    
    def __init__(self, task_id: str, task_type: str, priority: TaskPriority = TaskPriority.NORMAL):
        self.task_id = task_id
        self.task_type = task_type
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.parameters: Dict[str, Any] = {}
        self.constraints: Dict[str, Any] = {}
        self.result: Optional[TaskResult] = None
        self.start_time: Optional[datetime] = None
        self.estimated_duration: Optional[timedelta] = None
        self.dependencies: List[str] = []  # 依赖的任务ID列表
        self.callbacks: List[Callable] = []
    
    @abstractmethod
    async def plan(self) -> bool:
        """
        任务规划
        Returns:
            bool: 规划是否成功
        """
        pass
    
    @abstractmethod
    async def execute(self) -> TaskResult:
        """
        执行任务
        Returns:
            TaskResult: 任务执行结果
        """
        pass
    
    @abstractmethod
    async def pause(self) -> bool:
        """
        暂停任务
        Returns:
            bool: 暂停是否成功
        """
        pass
    
    @abstractmethod
    async def resume(self) -> bool:
        """
        恢复任务
        Returns:
            bool: 恢复是否成功
        """
        pass
    
    @abstractmethod
    async def cancel(self) -> bool:
        """
        取消任务
        Returns:
            bool: 取消是否成功
        """
        pass
    
    @abstractmethod
    async def get_progress(self) -> float:
        """
        获取任务进度
        Returns:
            float: 进度百分比 (0.0-1.0)
        """
        pass
    
    def set_parameters(self, parameters: Dict[str, Any]):
        """设置任务参数"""
        self.parameters.update(parameters)
    
    def set_constraints(self, constraints: Dict[str, Any]):
        """设置任务约束"""
        self.constraints.update(constraints)
    
    def add_dependency(self, task_id: str):
        """添加任务依赖"""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
    
    def register_callback(self, callback: Callable):
        """注册状态变化回调"""
        self.callbacks.append(callback)
    
    def set_status(self, status: TaskStatus, error_message: Optional[str] = None):
        """设置任务状态并通知回调"""
        old_status = self.status
        self.status = status
        
        # 更新结果
        if not self.result:
            self.result = TaskResult(
                task_id=self.task_id,
                status=status,
                start_time=self.start_time or datetime.now()
            )
        else:
            self.result.status = status
            if error_message:
                self.result.error_message = error_message
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.result.end_time = datetime.now()
        
        # 通知回调
        for callback in self.callbacks:
            try:
                callback(self, old_status, status)
            except Exception:
                pass  # 忽略回调错误


class BaseAtomicAction(ABC):
    """
    原子动作基类
    定义了不可分割的基本动作
    """
    
    def __init__(self, action_id: str, action_type: str):
        self.action_id = action_id
        self.action_type = action_type
        self.status = ActionStatus.WAITING
        self.parameters: Dict[str, Any] = {}
        self.result: Optional[ActionResult] = None
        self.timeout: Optional[float] = None
        self.retry_count = 0
        self.max_retries = 3
    
    @abstractmethod
    async def execute(self) -> ActionResult:
        """
        执行动作
        Returns:
            ActionResult: 动作执行结果
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        停止动作
        Returns:
            bool: 停止是否成功
        """
        pass
    
    @abstractmethod
    async def is_complete(self) -> bool:
        """
        检查动作是否完成
        Returns:
            bool: 是否完成
        """
        pass
    
    def set_parameters(self, parameters: Dict[str, Any]):
        """设置动作参数"""
        self.parameters.update(parameters)
    
    def set_timeout(self, timeout: float):
        """设置超时时间"""
        self.timeout = timeout
    
    async def execute_with_retry(self) -> ActionResult:
        """带重试的执行"""
        for attempt in range(self.max_retries + 1):
            self.retry_count = attempt
            result = await self.execute()
            
            if result.status == ActionStatus.FINISHED:
                return result
            
            if attempt < self.max_retries:
                await asyncio.sleep(1.0)  # 重试间隔
        
        return result


class ManipulationAction(BaseAtomicAction):
    """操作动作基类"""
    
    def __init__(self, action_id: str, action_type: str, arm_side: ArmSide):
        super().__init__(action_id, action_type)
        self.arm_side = arm_side
        self.target_pose: Optional[Pose] = None
        self.approach_pose: Optional[Pose] = None
        self.retreat_pose: Optional[Pose] = None
        self.force_threshold: float = 10.0
        self.position_tolerance: float = 0.001
        self.orientation_tolerance: float = 0.01


class PickAction(ManipulationAction):
    """抓取动作"""
    
    def __init__(self, action_id: str, arm_side: ArmSide):
        super().__init__(action_id, "pick", arm_side)
        self.object_id: Optional[str] = None
        self.grasp_type: str = "top_grasp"
    
    async def execute(self) -> ActionResult:
        """执行抓取动作"""
        start_time = datetime.now()
        self.status = ActionStatus.RUNNING
        
        try:
            # 1. 移动到接近位置
            if self.approach_pose:
                # TODO: 调用WBC控制器移动到接近位置
                pass
            
            # 2. 移动到目标位置
            if self.target_pose:
                # TODO: 调用WBC控制器移动到目标位置
                pass
            
            # 3. 执行抓取
            # TODO: 调用夹爪/灵巧手执行抓取
            
            # 4. 移动到撤离位置
            if self.retreat_pose:
                # TODO: 调用WBC控制器移动到撤离位置
                pass
            
            self.status = ActionStatus.FINISHED
            return ActionResult(
                action_id=self.action_id,
                status=ActionStatus.FINISHED,
                start_time=start_time,
                end_time=datetime.now()
            )
            
        except Exception as e:
            self.status = ActionStatus.FAILED
            return ActionResult(
                action_id=self.action_id,
                status=ActionStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                error_message=str(e)
            )


class PlaceAction(ManipulationAction):
    """放置动作"""
    
    def __init__(self, action_id: str, arm_side: ArmSide):
        super().__init__(action_id, "place", arm_side)
        self.release_height: float = 0.01  # 释放高度
    
    async def execute(self) -> ActionResult:
        """执行放置动作"""
        start_time = datetime.now()
        self.status = ActionStatus.RUNNING
        
        try:
            # 1. 移动到接近位置
            if self.approach_pose:
                # TODO: 调用WBC控制器移动到接近位置
                pass
            
            # 2. 移动到目标位置
            if self.target_pose:
                # TODO: 调用WBC控制器移动到目标位置
                pass
            
            # 3. 执行放置
            # TODO: 调用夹爪/灵巧手释放物体
            
            # 4. 移动到撤离位置
            if self.retreat_pose:
                # TODO: 调用WBC控制器移动到撤离位置
                pass
            
            self.status = ActionStatus.FINISHED
            return ActionResult(
                action_id=self.action_id,
                status=ActionStatus.FINISHED,
                start_time=start_time,
                end_time=datetime.now()
            )
            
        except Exception as e:
            self.status = ActionStatus.FAILED
            return ActionResult(
                action_id=self.action_id,
                status=ActionStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                error_message=str(e)
            )


class HandoverAction(ManipulationAction):
    """交接动作"""
    
    def __init__(self, action_id: str, from_arm: ArmSide, to_arm: ArmSide):
        super().__init__(action_id, "handover", from_arm)
        self.to_arm = to_arm
        self.handover_pose: Optional[Pose] = None
    
    async def execute(self) -> ActionResult:
        """执行交接动作"""
        start_time = datetime.now()
        self.status = ActionStatus.RUNNING
        
        try:
            # 1. 双臂移动到交接位置
            if self.handover_pose:
                # TODO: 协调双臂移动到交接位置
                pass
            
            # 2. 执行交接
            # TODO: 协调双臂完成物体交接
            
            self.status = ActionStatus.FINISHED
            return ActionResult(
                action_id=self.action_id,
                status=ActionStatus.FINISHED,
                start_time=start_time,
                end_time=datetime.now()
            )
            
        except Exception as e:
            self.status = ActionStatus.FAILED
            return ActionResult(
                action_id=self.action_id,
                status=ActionStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                error_message=str(e)
            )


class ActionSequence:
    """
    动作序列
    管理一系列原子动作的执行
    """
    
    def __init__(self, sequence_id: str):
        self.sequence_id = sequence_id
        self.actions: List[BaseAtomicAction] = []
        self.current_action_index = 0
        self.status = TaskStatus.PENDING
        self.parallel_execution = False
    
    def add_action(self, action: BaseAtomicAction):
        """添加动作到序列"""
        self.actions.append(action)
    
    def insert_action(self, index: int, action: BaseAtomicAction):
        """在指定位置插入动作"""
        self.actions.insert(index, action)
    
    def remove_action(self, action_id: str) -> bool:
        """移除指定动作"""
        for i, action in enumerate(self.actions):
            if action.action_id == action_id:
                self.actions.pop(i)
                return True
        return False
    
    async def execute(self) -> List[ActionResult]:
        """执行动作序列"""
        self.status = TaskStatus.EXECUTING
        results = []
        
        try:
            if self.parallel_execution:
                # 并行执行所有动作
                tasks = [action.execute_with_retry() for action in self.actions]
                results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # 顺序执行动作
                for i, action in enumerate(self.actions):
                    self.current_action_index = i
                    result = await action.execute_with_retry()
                    results.append(result)
                    
                    # 如果动作失败，停止执行
                    if result.status == ActionStatus.FAILED:
                        self.status = TaskStatus.FAILED
                        break
            
            # 检查整体执行结果
            if all(isinstance(r, ActionResult) and r.status == ActionStatus.FINISHED 
                   for r in results):
                self.status = TaskStatus.COMPLETED
            else:
                self.status = TaskStatus.FAILED
                
        except Exception as e:
            self.status = TaskStatus.FAILED
            # 为失败的动作创建结果
            for i in range(len(results), len(self.actions)):
                results.append(ActionResult(
                    action_id=self.actions[i].action_id,
                    status=ActionStatus.FAILED,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(e)
                ))
        
        return results
    
    async def pause(self) -> bool:
        """暂停序列执行"""
        self.status = TaskStatus.PAUSED
        # TODO: 暂停当前执行的动作
        return True
    
    async def resume(self) -> bool:
        """恢复序列执行"""
        self.status = TaskStatus.EXECUTING
        # TODO: 恢复动作执行
        return True
    
    async def cancel(self) -> bool:
        """取消序列执行"""
        self.status = TaskStatus.CANCELLED
        # TODO: 停止所有动作
        for action in self.actions:
            await action.stop()
        return True
    
    def get_progress(self) -> float:
        """获取执行进度"""
        if not self.actions:
            return 1.0
        
        if self.parallel_execution:
            completed = sum(1 for action in self.actions 
                          if action.status in [ActionStatus.FINISHED, ActionStatus.FAILED])
            return completed / len(self.actions)
        else:
            return self.current_action_index / len(self.actions)


class TaskPlanner(BaseComponent):
    """
    任务规划器
    负责将高级任务分解为动作序列
    """
    
    def __init__(self, planner_id: str):
        super().__init__(planner_id, ComponentType.TASK_BEHAVIOR)
        self.task_templates: Dict[str, type] = {}
        self.action_templates: Dict[str, type] = {}
        self.planning_strategies: Dict[str, Callable] = {}
    
    def register_task_template(self, task_type: str, task_class: type):
        """注册任务模板"""
        self.task_templates[task_type] = task_class
    
    def register_action_template(self, action_type: str, action_class: type):
        """注册动作模板"""
        self.action_templates[action_type] = action_class
    
    def register_planning_strategy(self, task_type: str, strategy: Callable):
        """注册规划策略"""
        self.planning_strategies[task_type] = strategy
    
    async def plan_task(self, task_command: TaskCommand) -> Optional[BaseTask]:
        """
        规划任务
        Args:
            task_command: 任务命令
        Returns:
            Optional[BaseTask]: 规划的任务，失败时返回None
        """
        try:
            # 检查是否有对应的任务模板
            if task_command.task_type not in self.task_templates:
                self.logger.error(f"Unknown task type: {task_command.task_type}")
                return None
            
            # 创建任务实例
            task_class = self.task_templates[task_command.task_type]
            task = task_class(
                task_id=task_command.task_id,
                task_type=task_command.task_type,
                priority=TaskPriority(task_command.priority)
            )
            
            # 设置任务参数
            task.set_parameters(task_command.parameters)
            task.set_constraints(task_command.constraints)
            
            # 执行规划
            if task_command.task_type in self.planning_strategies:
                strategy = self.planning_strategies[task_command.task_type]
                success = await strategy(task, task_command)
                if not success:
                    return None
            else:
                # 使用默认规划
                success = await task.plan()
                if not success:
                    return None
            
            return task
            
        except Exception as e:
            self.logger.error(f"Failed to plan task {task_command.task_id}: {e}")
            return None