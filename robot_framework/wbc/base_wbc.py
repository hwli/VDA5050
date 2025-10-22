#!/usr/bin/env python3
"""
Whole Body Control (WBC) Base Interface
全身控制基础接口，协调双臂和底盘的运动
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from enum import Enum
from dataclasses import dataclass

from ..common.interfaces.base_component import BaseComponent, ComponentType
from ..common.messages.robot_messages import (
    Pose, WBCCommand, ArmState, ChassisState, JointState
)


class ControlMode(Enum):
    """控制模式枚举"""
    POSITION = "position"
    VELOCITY = "velocity"
    FORCE = "force"
    IMPEDANCE = "impedance"
    ADMITTANCE = "admittance"


class CoordinationMode(Enum):
    """协调模式枚举"""
    INDEPENDENT = "independent"  # 独立控制
    COORDINATED = "coordinated"  # 协调控制
    COOPERATIVE = "cooperative"  # 合作控制


@dataclass
class ControllerGains:
    """控制器增益参数"""
    kp: np.ndarray  # 比例增益
    kd: np.ndarray  # 微分增益
    ki: np.ndarray  # 积分增益


@dataclass
class ImpedanceParameters:
    """阻抗参数"""
    stiffness: np.ndarray  # 刚度矩阵
    damping: np.ndarray    # 阻尼矩阵
    mass: np.ndarray       # 质量矩阵


@dataclass
class TaskSpaceTarget:
    """任务空间目标"""
    target_pose: Pose
    target_velocity: Optional[np.ndarray] = None
    target_acceleration: Optional[np.ndarray] = None
    target_wrench: Optional[np.ndarray] = None  # 力/力矩


@dataclass
class JointSpaceTarget:
    """关节空间目标"""
    target_positions: np.ndarray
    target_velocities: Optional[np.ndarray] = None
    target_accelerations: Optional[np.ndarray] = None
    target_torques: Optional[np.ndarray] = None


@dataclass
class ConstraintSpecification:
    """约束规范"""
    constraint_type: str  # equality, inequality, contact, collision_avoidance
    constraint_matrix: np.ndarray
    constraint_vector: np.ndarray
    weight: float = 1.0
    active: bool = True


class BaseWBCController(BaseComponent):
    """
    全身控制器基类
    实现双臂+底盘的协调控制
    """
    
    def __init__(self, controller_id: str):
        super().__init__(controller_id, ComponentType.WBC)
        
        # 机器人模型参数
        self.dof_total = 0  # 总自由度
        self.dof_arms = 0   # 双臂自由度
        self.dof_base = 0   # 底盘自由度
        
        # 控制参数
        self.control_mode = ControlMode.POSITION
        self.coordination_mode = CoordinationMode.INDEPENDENT
        self.control_frequency = 1000.0  # Hz
        
        # 状态变量
        self.current_joint_states: Optional[np.ndarray] = None
        self.current_joint_velocities: Optional[np.ndarray] = None
        self.current_joint_torques: Optional[np.ndarray] = None
        
        # 目标变量
        self.task_targets: Dict[str, TaskSpaceTarget] = {}
        self.joint_targets: Optional[JointSpaceTarget] = None
        
        # 约束
        self.constraints: List[ConstraintSpecification] = []
        
        # 控制器参数
        self.controller_gains: Optional[ControllerGains] = None
        self.impedance_params: Optional[ImpedanceParameters] = None
    
    @abstractmethod
    async def initialize_robot_model(self, model_config: Dict[str, Any]) -> bool:
        """
        初始化机器人模型
        Args:
            model_config: 模型配置参数
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    async def update_robot_state(self, 
                               left_arm_state: ArmState,
                               right_arm_state: ArmState,
                               chassis_state: ChassisState) -> bool:
        """
        更新机器人状态
        Args:
            left_arm_state: 左臂状态
            right_arm_state: 右臂状态
            chassis_state: 底盘状态
        Returns:
            bool: 更新是否成功
        """
        pass
    
    @abstractmethod
    async def compute_control_command(self) -> Optional[Dict[str, np.ndarray]]:
        """
        计算控制命令
        Returns:
            Dict[str, np.ndarray]: 控制命令字典
                - "left_arm_torques": 左臂关节力矩
                - "right_arm_torques": 右臂关节力矩
                - "base_velocities": 底盘速度命令
        """
        pass
    
    @abstractmethod
    async def set_task_target(self, task_name: str, target: TaskSpaceTarget) -> bool:
        """
        设置任务空间目标
        Args:
            task_name: 任务名称 (e.g., "left_end_effector", "right_end_effector", "base")
            target: 任务空间目标
        Returns:
            bool: 设置是否成功
        """
        pass
    
    @abstractmethod
    async def set_joint_target(self, target: JointSpaceTarget) -> bool:
        """
        设置关节空间目标
        Args:
            target: 关节空间目标
        Returns:
            bool: 设置是否成功
        """
        pass
    
    @abstractmethod
    async def add_constraint(self, constraint: ConstraintSpecification) -> bool:
        """
        添加约束
        Args:
            constraint: 约束规范
        Returns:
            bool: 添加是否成功
        """
        pass
    
    @abstractmethod
    async def remove_constraint(self, constraint_id: str) -> bool:
        """
        移除约束
        Args:
            constraint_id: 约束ID
        Returns:
            bool: 移除是否成功
        """
        pass
    
    @abstractmethod
    async def forward_kinematics(self, joint_positions: np.ndarray) -> Dict[str, Pose]:
        """
        正向运动学
        Args:
            joint_positions: 关节位置
        Returns:
            Dict[str, Pose]: 各链接的位姿
        """
        pass
    
    @abstractmethod
    async def inverse_kinematics(self, target_poses: Dict[str, Pose]) -> Optional[np.ndarray]:
        """
        逆向运动学
        Args:
            target_poses: 目标位姿字典
        Returns:
            Optional[np.ndarray]: 关节位置解，无解时返回None
        """
        pass
    
    @abstractmethod
    async def jacobian_matrix(self, joint_positions: np.ndarray) -> Dict[str, np.ndarray]:
        """
        计算雅可比矩阵
        Args:
            joint_positions: 关节位置
        Returns:
            Dict[str, np.ndarray]: 各任务的雅可比矩阵
        """
        pass
    
    async def set_control_mode(self, mode: ControlMode) -> bool:
        """设置控制模式"""
        self.control_mode = mode
        self.logger.info(f"Control mode set to: {mode.value}")
        return True
    
    async def set_coordination_mode(self, mode: CoordinationMode) -> bool:
        """设置协调模式"""
        self.coordination_mode = mode
        self.logger.info(f"Coordination mode set to: {mode.value}")
        return True
    
    async def set_controller_gains(self, gains: ControllerGains) -> bool:
        """设置控制器增益"""
        self.controller_gains = gains
        return True
    
    async def set_impedance_parameters(self, params: ImpedanceParameters) -> bool:
        """设置阻抗参数"""
        self.impedance_params = params
        return True
    
    async def process_wbc_command(self, command: WBCCommand) -> bool:
        """
        处理WBC命令
        Args:
            command: WBC命令
        Returns:
            bool: 处理是否成功
        """
        try:
            # 设置任务空间目标
            if command.left_arm_target:
                await self.set_task_target("left_end_effector", 
                    TaskSpaceTarget(target_pose=command.left_arm_target))
            
            if command.right_arm_target:
                await self.set_task_target("right_end_effector",
                    TaskSpaceTarget(target_pose=command.right_arm_target))
            
            if command.base_target:
                await self.set_task_target("base",
                    TaskSpaceTarget(target_pose=command.base_target))
            
            # 设置关节空间目标
            if command.joint_targets:
                positions = np.array(list(command.joint_targets.values()))
                await self.set_joint_target(JointSpaceTarget(target_positions=positions))
            
            # 更新控制参数
            if command.stiffness:
                stiffness = np.diag(list(command.stiffness.values()))
                damping = np.diag(list(command.damping.values())) if command.damping else stiffness * 0.1
                mass = np.eye(len(command.stiffness))
                
                await self.set_impedance_parameters(
                    ImpedanceParameters(stiffness=stiffness, damping=damping, mass=mass)
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing WBC command: {e}")
            return False


class TaskPriorityController(BaseWBCController):
    """
    任务优先级控制器
    基于任务优先级的全身控制实现
    """
    
    def __init__(self, controller_id: str):
        super().__init__(controller_id)
        self.task_priorities: Dict[str, int] = {}
        self.null_space_projectors: Dict[str, np.ndarray] = {}
    
    async def set_task_priority(self, task_name: str, priority: int) -> bool:
        """
        设置任务优先级
        Args:
            task_name: 任务名称
            priority: 优先级（数字越小优先级越高）
        Returns:
            bool: 设置是否成功
        """
        self.task_priorities[task_name] = priority
        return True
    
    async def compute_null_space_projectors(self) -> bool:
        """计算零空间投影矩阵"""
        # 按优先级排序任务
        sorted_tasks = sorted(self.task_priorities.items(), key=lambda x: x[1])
        
        # 计算累积零空间投影矩阵
        accumulated_jacobian = None
        I = np.eye(self.dof_total)
        
        for task_name, _ in sorted_tasks:
            if task_name in self.task_targets:
                # 获取当前任务的雅可比矩阵
                jacobians = await self.jacobian_matrix(self.current_joint_states)
                if task_name in jacobians:
                    J = jacobians[task_name]
                    
                    if accumulated_jacobian is None:
                        # 第一个任务的零空间投影矩阵
                        J_pinv = np.linalg.pinv(J)
                        N = I - J_pinv @ J
                    else:
                        # 在前面任务的零空间中计算当前任务的投影
                        J_aug = J @ accumulated_jacobian
                        J_aug_pinv = np.linalg.pinv(J_aug)
                        N = accumulated_jacobian - J_aug_pinv @ J_aug
                    
                    self.null_space_projectors[task_name] = N
                    accumulated_jacobian = N
        
        return True


class OptimizationBasedController(BaseWBCController):
    """
    基于优化的控制器
    使用二次规划求解全身控制问题
    """
    
    def __init__(self, controller_id: str):
        super().__init__(controller_id)
        self.task_weights: Dict[str, float] = {}
        self.regularization_weight = 1e-6
    
    async def set_task_weight(self, task_name: str, weight: float) -> bool:
        """
        设置任务权重
        Args:
            task_name: 任务名称
            weight: 权重值
        Returns:
            bool: 设置是否成功
        """
        self.task_weights[task_name] = weight
        return True
    
    async def formulate_qp_problem(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        构建二次规划问题
        min 0.5 * x^T * H * x + f^T * x
        s.t. A * x <= b
        
        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]: H, f, A, b矩阵
        """
        # 构建目标函数矩阵H和向量f
        H = np.eye(self.dof_total) * self.regularization_weight
        f = np.zeros(self.dof_total)
        
        # 添加任务目标到目标函数
        for task_name, target in self.task_targets.items():
            if task_name in self.task_weights:
                weight = self.task_weights[task_name]
                
                # 获取雅可比矩阵
                jacobians = await self.jacobian_matrix(self.current_joint_states)
                if task_name in jacobians:
                    J = jacobians[task_name]
                    
                    # 计算任务误差
                    current_poses = await self.forward_kinematics(self.current_joint_states)
                    if task_name in current_poses:
                        # 简化的位置误差计算
                        pos_error = np.array([
                            target.target_pose.position.x - current_poses[task_name].position.x,
                            target.target_pose.position.y - current_poses[task_name].position.y,
                            target.target_pose.position.z - current_poses[task_name].position.z
                        ])
                        
                        # 添加到目标函数
                        H += weight * J.T @ J
                        f += weight * J.T @ pos_error
        
        # 构建约束矩阵A和向量b
        constraint_matrices = []
        constraint_vectors = []
        
        for constraint in self.constraints:
            if constraint.active:
                constraint_matrices.append(constraint.constraint_matrix)
                constraint_vectors.append(constraint.constraint_vector)
        
        if constraint_matrices:
            A = np.vstack(constraint_matrices)
            b = np.hstack(constraint_vectors)
        else:
            A = np.zeros((0, self.dof_total))
            b = np.zeros(0)
        
        return H, f, A, b