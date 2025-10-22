#!/usr/bin/env python3
"""
Gateway Base Interface
网关基础接口，提供统一的对外交互接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union
import asyncio
import json
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from ..common.interfaces.base_component import BaseComponent, ComponentType
from ..common.messages.robot_messages import (
    MessageType, RobotOrder, DualArmRobotState, MessageFactory
)


class CommunicationProtocol(Enum):
    """通信协议枚举"""
    MQTT = "mqtt"
    HTTP_REST = "http_rest"
    WEBSOCKET = "websocket"
    ROS = "ros"
    GRPC = "grpc"
    TCP = "tcp"
    UDP = "udp"


class MessageDirection(Enum):
    """消息方向枚举"""
    INBOUND = "inbound"   # 接收消息
    OUTBOUND = "outbound" # 发送消息
    BIDIRECTIONAL = "bidirectional"


@dataclass
class EndpointConfig:
    """端点配置"""
    endpoint_id: str
    protocol: CommunicationProtocol
    address: str
    port: int
    topic_prefix: Optional[str] = None
    authentication: Optional[Dict[str, Any]] = None
    ssl_config: Optional[Dict[str, Any]] = None


@dataclass
class MessageRoute:
    """消息路由配置"""
    message_type: MessageType
    direction: MessageDirection
    endpoint_id: str
    topic: str
    qos: int = 0
    retain: bool = False


class BaseGateway(BaseComponent):
    """
    网关基类
    提供统一的消息路由和协议转换功能
    """
    
    def __init__(self, gateway_id: str):
        super().__init__(gateway_id, ComponentType.GATEWAY)
        
        # 端点管理
        self.endpoints: Dict[str, EndpointConfig] = {}
        self.connections: Dict[str, Any] = {}
        
        # 消息路由
        self.message_routes: Dict[MessageType, List[MessageRoute]] = {}
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        
        # 消息队列
        self.inbound_queue = asyncio.Queue()
        self.outbound_queue = asyncio.Queue()
        
        # 统计信息
        self.message_stats = {
            "sent": 0,
            "received": 0,
            "errors": 0
        }
    
    @abstractmethod
    async def create_connection(self, endpoint_config: EndpointConfig) -> bool:
        """
        创建连接
        Args:
            endpoint_config: 端点配置
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    async def close_connection(self, endpoint_id: str) -> bool:
        """
        关闭连接
        Args:
            endpoint_id: 端点ID
        Returns:
            bool: 关闭是否成功
        """
        pass
    
    @abstractmethod
    async def send_message(self, endpoint_id: str, topic: str, 
                          message: Dict[str, Any], **kwargs) -> bool:
        """
        发送消息
        Args:
            endpoint_id: 端点ID
            topic: 主题
            message: 消息内容
            **kwargs: 其他参数
        Returns:
            bool: 发送是否成功
        """
        pass
    
    @abstractmethod
    async def receive_message(self, endpoint_id: str, topic: str, 
                            timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        接收消息
        Args:
            endpoint_id: 端点ID
            topic: 主题
            timeout: 超时时间
        Returns:
            Optional[Dict[str, Any]]: 接收到的消息，超时返回None
        """
        pass
    
    async def register_endpoint(self, endpoint_config: EndpointConfig) -> bool:
        """
        注册端点
        Args:
            endpoint_config: 端点配置
        Returns:
            bool: 注册是否成功
        """
        try:
            self.endpoints[endpoint_config.endpoint_id] = endpoint_config
            success = await self.create_connection(endpoint_config)
            if success:
                self.logger.info(f"Endpoint registered: {endpoint_config.endpoint_id}")
            return success
        except Exception as e:
            self.logger.error(f"Failed to register endpoint {endpoint_config.endpoint_id}: {e}")
            return False
    
    async def unregister_endpoint(self, endpoint_id: str) -> bool:
        """
        取消注册端点
        Args:
            endpoint_id: 端点ID
        Returns:
            bool: 取消注册是否成功
        """
        try:
            if endpoint_id in self.endpoints:
                await self.close_connection(endpoint_id)
                del self.endpoints[endpoint_id]
                if endpoint_id in self.connections:
                    del self.connections[endpoint_id]
                self.logger.info(f"Endpoint unregistered: {endpoint_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to unregister endpoint {endpoint_id}: {e}")
            return False
    
    def add_message_route(self, route: MessageRoute):
        """
        添加消息路由
        Args:
            route: 消息路由配置
        """
        if route.message_type not in self.message_routes:
            self.message_routes[route.message_type] = []
        self.message_routes[route.message_type].append(route)
        self.logger.info(f"Message route added: {route.message_type.value} -> {route.endpoint_id}")
    
    def remove_message_route(self, message_type: MessageType, endpoint_id: str):
        """
        移除消息路由
        Args:
            message_type: 消息类型
            endpoint_id: 端点ID
        """
        if message_type in self.message_routes:
            self.message_routes[message_type] = [
                route for route in self.message_routes[message_type]
                if route.endpoint_id != endpoint_id
            ]
    
    def register_message_handler(self, message_type: MessageType, 
                                handler: Callable[[Dict[str, Any]], None]):
        """
        注册消息处理器
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
    
    def unregister_message_handler(self, message_type: MessageType, 
                                 handler: Callable[[Dict[str, Any]], None]):
        """
        取消注册消息处理器
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        if message_type in self.message_handlers:
            if handler in self.message_handlers[message_type]:
                self.message_handlers[message_type].remove(handler)
    
    async def publish_message(self, message_type: MessageType, 
                            message_data: Dict[str, Any]) -> bool:
        """
        发布消息到所有相关端点
        Args:
            message_type: 消息类型
            message_data: 消息数据
        Returns:
            bool: 发布是否成功
        """
        success = True
        
        if message_type in self.message_routes:
            for route in self.message_routes[message_type]:
                if route.direction in [MessageDirection.OUTBOUND, MessageDirection.BIDIRECTIONAL]:
                    try:
                        await self.send_message(
                            route.endpoint_id, 
                            route.topic, 
                            message_data,
                            qos=route.qos,
                            retain=route.retain
                        )
                        self.message_stats["sent"] += 1
                    except Exception as e:
                        self.logger.error(f"Failed to send message to {route.endpoint_id}: {e}")
                        self.message_stats["errors"] += 1
                        success = False
        
        return success
    
    async def handle_received_message(self, message_type: MessageType, 
                                    message_data: Dict[str, Any]):
        """
        处理接收到的消息
        Args:
            message_type: 消息类型
            message_data: 消息数据
        """
        self.message_stats["received"] += 1
        
        # 调用注册的处理器
        if message_type in self.message_handlers:
            for handler in self.message_handlers[message_type]:
                try:
                    handler(message_data)
                except Exception as e:
                    self.logger.error(f"Error in message handler: {e}")
        
        # 将消息放入入站队列
        await self.inbound_queue.put((message_type, message_data))
    
    async def get_received_message(self, timeout: float = 1.0) -> Optional[tuple]:
        """
        获取接收到的消息
        Args:
            timeout: 超时时间
        Returns:
            Optional[tuple]: (message_type, message_data)
        """
        try:
            return await asyncio.wait_for(self.inbound_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    async def publish_robot_state(self, robot_state: DualArmRobotState) -> bool:
        """
        发布机器人状态
        Args:
            robot_state: 机器人状态
        Returns:
            bool: 发布是否成功
        """
        message = MessageFactory.create_dual_arm_state(robot_state)
        return await self.publish_message(MessageType.DUAL_ARM_STATE, message)
    
    async def publish_order_response(self, order_id: str, success: bool, 
                                   error_message: Optional[str] = None) -> bool:
        """
        发布订单响应
        Args:
            order_id: 订单ID
            success: 是否成功
            error_message: 错误消息
        Returns:
            bool: 发布是否成功
        """
        response = {
            "messageType": "order_response",
            "orderId": order_id,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "errorMessage": error_message
        }
        return await self.publish_message(MessageType.ORDER, response)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "endpoints": len(self.endpoints),
            "active_connections": len(self.connections),
            "message_routes": sum(len(routes) for routes in self.message_routes.values()),
            "message_handlers": sum(len(handlers) for handlers in self.message_handlers.values()),
            "messages_sent": self.message_stats["sent"],
            "messages_received": self.message_stats["received"],
            "errors": self.message_stats["errors"]
        }
    
    async def start(self) -> bool:
        """启动网关"""
        try:
            self.set_state(ComponentState.RUNNING)
            
            # 启动消息处理循环
            asyncio.create_task(self._message_processing_loop())
            
            self.logger.info("Gateway started successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start gateway: {e}")
            self.set_state(ComponentState.ERROR, str(e))
            return False
    
    async def stop(self) -> bool:
        """停止网关"""
        try:
            self.request_stop()
            self.set_state(ComponentState.STOPPING)
            
            # 关闭所有连接
            for endpoint_id in list(self.endpoints.keys()):
                await self.unregister_endpoint(endpoint_id)
            
            self.set_state(ComponentState.STOPPED)
            self.logger.info("Gateway stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop gateway: {e}")
            self.set_state(ComponentState.ERROR, str(e))
            return False
    
    async def _message_processing_loop(self):
        """消息处理循环"""
        while not self.should_stop():
            try:
                # 处理出站消息队列
                try:
                    message_type, message_data = await asyncio.wait_for(
                        self.outbound_queue.get(), timeout=0.1
                    )
                    await self.publish_message(message_type, message_data)
                except asyncio.TimeoutError:
                    pass
                
                # 检查连接状态
                await self._check_connections()
                
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _check_connections(self):
        """检查连接状态"""
        for endpoint_id, endpoint_config in self.endpoints.items():
            if endpoint_id not in self.connections:
                # 尝试重新连接
                self.logger.warning(f"Reconnecting to endpoint: {endpoint_id}")
                await self.create_connection(endpoint_config)