#!/usr/bin/env python3
"""
Base Driver Interface
驱动层基础接口，所有硬件驱动的基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
import asyncio
import threading
from enum import Enum

from ..common.interfaces.base_component import BaseComponent, ComponentType, ComponentState
from ..common.messages.robot_messages import SensorData


class DriverType(Enum):
    """驱动类型枚举"""
    CAMERA = "camera"
    LIDAR = "lidar"
    ARM = "arm"
    GRIPPER = "gripper"
    DEXTEROUS_HAND = "dexterous_hand"
    CHASSIS = "chassis"


class ConnectionType(Enum):
    """连接类型枚举"""
    USB = "usb"
    ETHERNET = "ethernet"
    CAN = "can"
    SERIAL = "serial"
    WIRELESS = "wireless"


class BaseDriver(BaseComponent):
    """
    硬件驱动基类
    定义了所有硬件驱动的通用接口
    """
    
    def __init__(self, driver_id: str, driver_type: DriverType):
        super().__init__(driver_id, ComponentType.DRIVER)
        self.driver_type = driver_type
        self.connection_type: Optional[ConnectionType] = None
        self.device_info: Dict[str, Any] = {}
        self.is_connected = False
        self._data_callbacks: List[Callable] = []
        self._command_queue = asyncio.Queue()
        
    @abstractmethod
    async def connect(self, connection_params: Dict[str, Any]) -> bool:
        """
        连接到硬件设备
        Args:
            connection_params: 连接参数
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        断开硬件连接
        Returns:
            bool: 断开是否成功
        """
        pass
    
    @abstractmethod
    async def read_data(self) -> Optional[Any]:
        """
        读取硬件数据
        Returns:
            Any: 读取的数据，失败时返回None
        """
        pass
    
    @abstractmethod
    async def write_command(self, command: Dict[str, Any]) -> bool:
        """
        向硬件发送命令
        Args:
            command: 命令数据
        Returns:
            bool: 发送是否成功
        """
        pass
    
    @abstractmethod
    async def get_device_info(self) -> Dict[str, Any]:
        """
        获取设备信息
        Returns:
            Dict[str, Any]: 设备信息
        """
        pass
    
    @abstractmethod
    async def calibrate(self, calibration_params: Dict[str, Any]) -> bool:
        """
        校准设备
        Args:
            calibration_params: 校准参数
        Returns:
            bool: 校准是否成功
        """
        pass
    
    @abstractmethod
    async def reset(self) -> bool:
        """
        重置设备
        Returns:
            bool: 重置是否成功
        """
        pass
    
    def register_data_callback(self, callback: Callable[[Any], None]):
        """注册数据回调函数"""
        self._data_callbacks.append(callback)
    
    def unregister_data_callback(self, callback: Callable[[Any], None]):
        """取消注册数据回调函数"""
        if callback in self._data_callbacks:
            self._data_callbacks.remove(callback)
    
    def notify_data_callbacks(self, data: Any):
        """通知所有数据回调"""
        for callback in self._data_callbacks:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Error in data callback: {e}")
    
    async def send_command_async(self, command: Dict[str, Any]) -> bool:
        """异步发送命令"""
        await self._command_queue.put(command)
        return True
    
    async def _command_processor(self):
        """命令处理器协程"""
        while not self.should_stop():
            try:
                # 等待命令，超时1秒
                command = await asyncio.wait_for(
                    self._command_queue.get(), timeout=1.0
                )
                await self.write_command(command)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing command: {e}")
    
    async def start(self) -> bool:
        """启动驱动"""
        if self.state != ComponentState.READY:
            self.logger.error("Driver not ready for start")
            return False
        
        try:
            self.set_state(ComponentState.RUNNING)
            # 启动命令处理器
            asyncio.create_task(self._command_processor())
            return True
        except Exception as e:
            self.logger.error(f"Failed to start driver: {e}")
            self.set_state(ComponentState.ERROR, str(e))
            return False
    
    async def stop(self) -> bool:
        """停止驱动"""
        try:
            self.request_stop()
            self.set_state(ComponentState.STOPPING)
            
            # 断开连接
            if self.is_connected:
                await self.disconnect()
            
            self.set_state(ComponentState.STOPPED)
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop driver: {e}")
            self.set_state(ComponentState.ERROR, str(e))
            return False


class SensorDriver(BaseDriver):
    """
    传感器驱动基类
    用于相机、激光雷达等传感器
    """
    
    def __init__(self, driver_id: str, driver_type: DriverType):
        super().__init__(driver_id, driver_type)
        self.sampling_rate = 30.0  # Hz
        self.is_streaming = False
        self._stream_task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def start_streaming(self) -> bool:
        """开始数据流"""
        pass
    
    @abstractmethod
    async def stop_streaming(self) -> bool:
        """停止数据流"""
        pass
    
    @abstractmethod
    async def capture_single(self) -> Optional[SensorData]:
        """单次数据采集"""
        pass
    
    async def set_sampling_rate(self, rate: float) -> bool:
        """设置采样率"""
        if rate <= 0:
            return False
        self.sampling_rate = rate
        return True
    
    async def _streaming_loop(self):
        """数据流循环"""
        interval = 1.0 / self.sampling_rate
        
        while self.is_streaming and not self.should_stop():
            try:
                start_time = asyncio.get_event_loop().time()
                
                # 读取数据
                data = await self.read_data()
                if data is not None:
                    self.notify_data_callbacks(data)
                
                # 控制采样率
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except Exception as e:
                self.logger.error(f"Error in streaming loop: {e}")
                await asyncio.sleep(0.1)  # 避免快速重试


class ActuatorDriver(BaseDriver):
    """
    执行器驱动基类
    用于机械臂、夹爪、底盘等执行器
    """
    
    def __init__(self, driver_id: str, driver_type: DriverType):
        super().__init__(driver_id, driver_type)
        self.is_moving = False
        self.current_position: Optional[Any] = None
        self.target_position: Optional[Any] = None
        self.position_tolerance = 0.01
    
    @abstractmethod
    async def move_to_position(self, position: Any, speed: float = 1.0) -> bool:
        """移动到指定位置"""
        pass
    
    @abstractmethod
    async def stop_motion(self) -> bool:
        """停止运动"""
        pass
    
    @abstractmethod
    async def get_current_position(self) -> Optional[Any]:
        """获取当前位置"""
        pass
    
    @abstractmethod
    async def is_motion_complete(self) -> bool:
        """检查运动是否完成"""
        pass
    
    @abstractmethod
    async def emergency_stop(self) -> bool:
        """紧急停止"""
        pass
    
    async def wait_for_motion_complete(self, timeout: float = 30.0) -> bool:
        """等待运动完成"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if await self.is_motion_complete():
                return True
            await asyncio.sleep(0.1)
        
        return False


class DriverFactory:
    """驱动工厂类"""
    
    _driver_classes: Dict[DriverType, type] = {}
    
    @classmethod
    def register_driver(cls, driver_type: DriverType, driver_class: type):
        """注册驱动类"""
        cls._driver_classes[driver_type] = driver_class
    
    @classmethod
    def create_driver(cls, driver_type: DriverType, driver_id: str, 
                     config: Dict[str, Any]) -> Optional[BaseDriver]:
        """创建驱动实例"""
        if driver_type not in cls._driver_classes:
            return None
        
        driver_class = cls._driver_classes[driver_type]
        return driver_class(driver_id, **config)
    
    @classmethod
    def get_available_drivers(cls) -> List[DriverType]:
        """获取可用的驱动类型"""
        return list(cls._driver_classes.keys())