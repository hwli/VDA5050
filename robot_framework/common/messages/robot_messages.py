#!/usr/bin/env python3
"""
Robot Framework Message Definitions
机器人框架消息定义，扩展VDA5050协议以支持双臂机器人
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
import numpy as np


class MessageType(Enum):
    """消息类型枚举"""
    # VDA5050 基础消息
    CONNECTION = "connection"
    STATE = "state"
    ORDER = "order"
    INSTANT_ACTION = "instantAction"
    FACTSHEET = "factsheet"
    VISUALIZATION = "visualization"
    
    # 扩展消息类型
    DUAL_ARM_STATE = "dual_arm_state"
    MANIPULATION_ORDER = "manipulation_order"
    WBC_COMMAND = "wbc_command"
    SENSOR_DATA = "sensor_data"
    TOOL_STATUS = "tool_status"


class ArmSide(Enum):
    """机械臂侧别"""
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


class ManipulationAction(Enum):
    """操作动作类型"""
    PICK = "pick"
    PLACE = "place"
    MOVE = "move"
    GRASP = "grasp"
    RELEASE = "release"
    APPROACH = "approach"
    RETREAT = "retreat"
    HANDOVER = "handover"


@dataclass
class Position3D:
    """3D位置"""
    x: float
    y: float
    z: float


@dataclass
class Orientation:
    """方向（四元数）"""
    x: float
    y: float
    z: float
    w: float


@dataclass
class Pose:
    """位姿（位置+方向）"""
    position: Position3D
    orientation: Orientation


@dataclass
class JointState:
    """关节状态"""
    name: str
    position: float
    velocity: float = 0.0
    effort: float = 0.0
    temperature: float = 0.0


@dataclass
class ArmState:
    """机械臂状态"""
    arm_id: str
    side: ArmSide
    joint_states: List[JointState]
    end_effector_pose: Pose
    is_moving: bool = False
    is_collision: bool = False
    payload_mass: float = 0.0
    error_code: int = 0
    error_message: str = ""


@dataclass
class GripperState:
    """夹爪状态"""
    gripper_id: str
    arm_side: ArmSide
    position: float  # 0.0-1.0, 0表示完全闭合，1表示完全张开
    force: float
    is_grasping: bool = False
    object_detected: bool = False


@dataclass
class DexterousHandState:
    """灵巧手状态"""
    hand_id: str
    arm_side: ArmSide
    finger_positions: List[float]  # 每个手指的位置
    finger_forces: List[float]     # 每个手指的力
    tactile_data: Optional[np.ndarray] = None  # 触觉数据
    is_grasping: bool = False


@dataclass
class ChassisState:
    """底盘状态"""
    linear_velocity: Position3D
    angular_velocity: Position3D
    wheel_speeds: List[float]
    wheel_positions: List[float]
    is_moving: bool = False
    odometry: Pose
    battery_level: float


@dataclass
class SensorData:
    """传感器数据"""
    sensor_id: str
    sensor_type: str
    timestamp: datetime
    data: Dict[str, Any]


@dataclass
class CameraData(SensorData):
    """相机数据"""
    image_data: Optional[np.ndarray] = None
    depth_data: Optional[np.ndarray] = None
    point_cloud: Optional[np.ndarray] = None
    detections: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LidarData(SensorData):
    """激光雷达数据"""
    ranges: np.ndarray
    angles: np.ndarray
    intensities: Optional[np.ndarray] = None
    point_cloud: Optional[np.ndarray] = None


@dataclass
class DualArmRobotState:
    """双臂机器人完整状态"""
    # VDA5050 基础字段
    header_id: int
    timestamp: datetime
    version: str
    manufacturer: str
    serial_number: str
    order_id: str
    order_update_id: int
    
    # 机器人特定状态
    left_arm: ArmState
    right_arm: ArmState
    left_gripper: Optional[GripperState] = None
    right_gripper: Optional[GripperState] = None
    left_hand: Optional[DexterousHandState] = None
    right_hand: Optional[DexterousHandState] = None
    chassis: ChassisState
    
    # 传感器数据
    cameras: List[CameraData] = field(default_factory=list)
    lidars: List[LidarData] = field(default_factory=list)
    
    # 系统状态
    operating_mode: str = "AUTOMATIC"
    safety_state: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ManipulationTarget:
    """操作目标"""
    target_id: str
    target_pose: Pose
    approach_pose: Optional[Pose] = None
    retreat_pose: Optional[Pose] = None
    grasp_config: Optional[Dict[str, Any]] = None


@dataclass
class ManipulationCommand:
    """操作命令"""
    command_id: str
    action: ManipulationAction
    arm_side: ArmSide
    target: ManipulationTarget
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass
class WBCCommand:
    """全身控制命令"""
    command_id: str
    timestamp: datetime
    
    # 任务空间目标
    left_arm_target: Optional[Pose] = None
    right_arm_target: Optional[Pose] = None
    base_target: Optional[Pose] = None
    
    # 关节空间目标
    joint_targets: Optional[Dict[str, float]] = None
    
    # 约束条件
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    # 控制参数
    stiffness: Dict[str, float] = field(default_factory=dict)
    damping: Dict[str, float] = field(default_factory=dict)


@dataclass
class TaskCommand:
    """任务命令"""
    task_id: str
    task_type: str
    priority: int
    parameters: Dict[str, Any]
    manipulation_commands: List[ManipulationCommand] = field(default_factory=list)
    wbc_commands: List[WBCCommand] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RobotOrder:
    """机器人订单（扩展VDA5050 Order）"""
    # VDA5050 基础字段
    header_id: int
    timestamp: datetime
    version: str
    manufacturer: str
    serial_number: str
    order_id: str
    order_update_id: int
    
    # 导航相关（继承VDA5050）
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    
    # 双臂机器人扩展
    task_commands: List[TaskCommand] = field(default_factory=list)
    coordination_mode: str = "independent"  # independent, coordinated, cooperative
    
    # 安全和约束
    safety_constraints: Dict[str, Any] = field(default_factory=dict)
    performance_requirements: Dict[str, Any] = field(default_factory=dict)


class MessageFactory:
    """消息工厂类"""
    
    @staticmethod
    def create_dual_arm_state(robot_state: DualArmRobotState) -> Dict[str, Any]:
        """创建双臂机器人状态消息"""
        return {
            "messageType": MessageType.DUAL_ARM_STATE.value,
            "headerId": robot_state.header_id,
            "timestamp": robot_state.timestamp.isoformat(),
            "version": robot_state.version,
            "manufacturer": robot_state.manufacturer,
            "serialNumber": robot_state.serial_number,
            "orderId": robot_state.order_id,
            "orderUpdateId": robot_state.order_update_id,
            "leftArm": MessageFactory._arm_state_to_dict(robot_state.left_arm),
            "rightArm": MessageFactory._arm_state_to_dict(robot_state.right_arm),
            "chassis": MessageFactory._chassis_state_to_dict(robot_state.chassis),
            "operatingMode": robot_state.operating_mode,
            "safetyState": robot_state.safety_state,
            "errors": robot_state.errors
        }
    
    @staticmethod
    def create_manipulation_order(order: RobotOrder) -> Dict[str, Any]:
        """创建操作订单消息"""
        return {
            "messageType": MessageType.MANIPULATION_ORDER.value,
            "headerId": order.header_id,
            "timestamp": order.timestamp.isoformat(),
            "version": order.version,
            "manufacturer": order.manufacturer,
            "serialNumber": order.serial_number,
            "orderId": order.order_id,
            "orderUpdateId": order.order_update_id,
            "nodes": order.nodes,
            "edges": order.edges,
            "taskCommands": [MessageFactory._task_command_to_dict(cmd) 
                           for cmd in order.task_commands],
            "coordinationMode": order.coordination_mode,
            "safetyConstraints": order.safety_constraints,
            "performanceRequirements": order.performance_requirements
        }
    
    @staticmethod
    def _arm_state_to_dict(arm_state: ArmState) -> Dict[str, Any]:
        """将机械臂状态转换为字典"""
        return {
            "armId": arm_state.arm_id,
            "side": arm_state.side.value,
            "jointStates": [
                {
                    "name": js.name,
                    "position": js.position,
                    "velocity": js.velocity,
                    "effort": js.effort,
                    "temperature": js.temperature
                } for js in arm_state.joint_states
            ],
            "endEffectorPose": MessageFactory._pose_to_dict(arm_state.end_effector_pose),
            "isMoving": arm_state.is_moving,
            "isCollision": arm_state.is_collision,
            "payloadMass": arm_state.payload_mass,
            "errorCode": arm_state.error_code,
            "errorMessage": arm_state.error_message
        }
    
    @staticmethod
    def _chassis_state_to_dict(chassis_state: ChassisState) -> Dict[str, Any]:
        """将底盘状态转换为字典"""
        return {
            "linearVelocity": {
                "x": chassis_state.linear_velocity.x,
                "y": chassis_state.linear_velocity.y,
                "z": chassis_state.linear_velocity.z
            },
            "angularVelocity": {
                "x": chassis_state.angular_velocity.x,
                "y": chassis_state.angular_velocity.y,
                "z": chassis_state.angular_velocity.z
            },
            "wheelSpeeds": chassis_state.wheel_speeds,
            "wheelPositions": chassis_state.wheel_positions,
            "isMoving": chassis_state.is_moving,
            "odometry": MessageFactory._pose_to_dict(chassis_state.odometry),
            "batteryLevel": chassis_state.battery_level
        }
    
    @staticmethod
    def _pose_to_dict(pose: Pose) -> Dict[str, Any]:
        """将位姿转换为字典"""
        return {
            "position": {
                "x": pose.position.x,
                "y": pose.position.y,
                "z": pose.position.z
            },
            "orientation": {
                "x": pose.orientation.x,
                "y": pose.orientation.y,
                "z": pose.orientation.z,
                "w": pose.orientation.w
            }
        }
    
    @staticmethod
    def _task_command_to_dict(task_command: TaskCommand) -> Dict[str, Any]:
        """将任务命令转换为字典"""
        return {
            "taskId": task_command.task_id,
            "taskType": task_command.task_type,
            "priority": task_command.priority,
            "parameters": task_command.parameters,
            "manipulationCommands": [
                MessageFactory._manipulation_command_to_dict(cmd)
                for cmd in task_command.manipulation_commands
            ],
            "constraints": task_command.constraints
        }
    
    @staticmethod
    def _manipulation_command_to_dict(cmd: ManipulationCommand) -> Dict[str, Any]:
        """将操作命令转换为字典"""
        return {
            "commandId": cmd.command_id,
            "action": cmd.action.value,
            "armSide": cmd.arm_side.value,
            "target": {
                "targetId": cmd.target.target_id,
                "targetPose": MessageFactory._pose_to_dict(cmd.target.target_pose),
                "approachPose": MessageFactory._pose_to_dict(cmd.target.approach_pose) 
                              if cmd.target.approach_pose else None,
                "retreatPose": MessageFactory._pose_to_dict(cmd.target.retreat_pose)
                             if cmd.target.retreat_pose else None,
                "graspConfig": cmd.target.grasp_config
            },
            "parameters": cmd.parameters,
            "constraints": cmd.constraints,
            "priority": cmd.priority
        }