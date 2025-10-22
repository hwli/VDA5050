#!/usr/bin/env python3
"""
Base Component Interface for Robot Framework
基础组件接口，所有模块的基类
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
import threading
import time
import logging
from dataclasses import dataclass
from datetime import datetime


class ComponentState(Enum):
    """组件状态枚举"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ComponentType(Enum):
    """组件类型枚举"""
    DRIVER = "driver"
    WBC = "wbc"
    GATEWAY = "gateway"
    TASK_BEHAVIOR = "task_behavior"
    TOOL = "tool"


@dataclass
class ComponentStatus:
    """组件状态信息"""
    component_id: str
    component_type: ComponentType
    state: ComponentState
    timestamp: datetime
    error_message: Optional[str] = None
    health_score: float = 1.0  # 0.0-1.0, 1.0表示完全健康
    metrics: Dict[str, Any] = None


class BaseComponent(ABC):
    """
    所有组件的基类
    定义了组件的基本生命周期和接口
    """
    
    def __init__(self, component_id: str, component_type: ComponentType):
        self.component_id = component_id
        self.component_type = component_type
        self.state = ComponentState.UNINITIALIZED
        self.logger = logging.getLogger(f"{component_type.value}.{component_id}")
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._status_callbacks = []
        
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化组件
        Args:
            config: 配置参数
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """
        启动组件
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        停止组件
        Returns:
            bool: 停止是否成功
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> ComponentStatus:
        """
        健康检查
        Returns:
            ComponentStatus: 组件状态信息
        """
        pass
    
    def get_state(self) -> ComponentState:
        """获取当前状态"""
        with self._lock:
            return self.state
    
    def set_state(self, new_state: ComponentState, error_message: Optional[str] = None):
        """设置状态并通知回调"""
        with self._lock:
            old_state = self.state
            self.state = new_state
            
            # 创建状态信息
            status = ComponentStatus(
                component_id=self.component_id,
                component_type=self.component_type,
                state=new_state,
                timestamp=datetime.now(),
                error_message=error_message
            )
            
            # 通知状态变化回调
            for callback in self._status_callbacks:
                try:
                    callback(status)
                except Exception as e:
                    self.logger.error(f"Error in status callback: {e}")
            
            self.logger.info(f"State changed: {old_state.value} -> {new_state.value}")
    
    def register_status_callback(self, callback):
        """注册状态变化回调"""
        self._status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback):
        """取消注册状态变化回调"""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def is_running(self) -> bool:
        """检查组件是否正在运行"""
        return self.state == ComponentState.RUNNING
    
    def is_ready(self) -> bool:
        """检查组件是否就绪"""
        return self.state in [ComponentState.READY, ComponentState.RUNNING]
    
    def request_stop(self):
        """请求停止组件"""
        self._stop_event.set()
    
    def should_stop(self) -> bool:
        """检查是否应该停止"""
        return self._stop_event.is_set()


class ComponentManager:
    """
    组件管理器
    负责管理所有组件的生命周期
    """
    
    def __init__(self):
        self.components: Dict[str, BaseComponent] = {}
        self.logger = logging.getLogger("ComponentManager")
        self._lock = threading.RLock()
    
    def register_component(self, component: BaseComponent):
        """注册组件"""
        with self._lock:
            self.components[component.component_id] = component
            self.logger.info(f"Registered component: {component.component_id}")
    
    def unregister_component(self, component_id: str):
        """取消注册组件"""
        with self._lock:
            if component_id in self.components:
                del self.components[component_id]
                self.logger.info(f"Unregistered component: {component_id}")
    
    def get_component(self, component_id: str) -> Optional[BaseComponent]:
        """获取组件"""
        with self._lock:
            return self.components.get(component_id)
    
    def get_components_by_type(self, component_type: ComponentType) -> List[BaseComponent]:
        """根据类型获取组件列表"""
        with self._lock:
            return [comp for comp in self.components.values() 
                   if comp.component_type == component_type]
    
    async def initialize_all(self, configs: Dict[str, Dict[str, Any]]) -> bool:
        """初始化所有组件"""
        success = True
        for component_id, component in self.components.items():
            try:
                config = configs.get(component_id, {})
                if not await component.initialize(config):
                    self.logger.error(f"Failed to initialize component: {component_id}")
                    success = False
            except Exception as e:
                self.logger.error(f"Exception during initialization of {component_id}: {e}")
                success = False
        return success
    
    async def start_all(self) -> bool:
        """启动所有组件"""
        success = True
        for component_id, component in self.components.items():
            try:
                if not await component.start():
                    self.logger.error(f"Failed to start component: {component_id}")
                    success = False
            except Exception as e:
                self.logger.error(f"Exception during start of {component_id}: {e}")
                success = False
        return success
    
    async def stop_all(self) -> bool:
        """停止所有组件"""
        success = True
        for component_id, component in self.components.items():
            try:
                if not await component.stop():
                    self.logger.error(f"Failed to stop component: {component_id}")
                    success = False
            except Exception as e:
                self.logger.error(f"Exception during stop of {component_id}: {e}")
                success = False
        return success
    
    async def health_check_all(self) -> Dict[str, ComponentStatus]:
        """对所有组件进行健康检查"""
        results = {}
        for component_id, component in self.components.items():
            try:
                results[component_id] = await component.health_check()
            except Exception as e:
                self.logger.error(f"Health check failed for {component_id}: {e}")
                results[component_id] = ComponentStatus(
                    component_id=component_id,
                    component_type=component.component_type,
                    state=ComponentState.ERROR,
                    timestamp=datetime.now(),
                    error_message=str(e),
                    health_score=0.0
                )
        return results


# 全局组件管理器实例
component_manager = ComponentManager()