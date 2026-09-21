import asyncio
import json
import time
import threading
import random
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import uuid
import math

class ROSMessageType(Enum):
    GEOMETRY_TWIST = "geometry_msgs/Twist"
    SENSOR_JOINT_STATE = "sensor_msgs/JointState"
    SENSOR_IMAGE = "sensor_msgs/Image"
    SENSOR_LASER_SCAN = "sensor_msgs/LaserScan"
    SENSOR_POINT_CLOUD = "sensor_msgs/PointCloud2"
    NAV_ODOMETRY = "nav_msgs/Odometry"
    NAV_PATH = "nav_msgs/Path"
    STD_STRING = "std_msgs/String"
    TF2_TRANSFORM = "tf2_msgs/TFMessage"
    MOVEIT_TRAJECTORY = "moveit_msgs/RobotTrajectory"
    ACTIONLIB_GOAL = "actionlib_msgs/GoalStatusArray"

class ROSNodeType(Enum):
    PUBLISHER = "publisher"
    SUBSCRIBER = "subscriber"
    SERVICE = "service"
    ACTION_SERVER = "action_server"
    ACTION_CLIENT = "action_client"
    TRANSFORM_BROADCASTER = "tf_broadcaster"

@dataclass
class ROSMessage:
    topic: str
    msg_type: ROSMessageType
    timestamp: datetime
    data: Dict[str, Any]
    frame_id: Optional[str] = None
    sequence: int = 0

@dataclass
class ROSNodeConfig:
    node_name: str
    node_type: ROSNodeType
    topics: List[str]
    message_types: List[ROSMessageType]
    namespace: str = "/"
    rate_hz: float = 10.0
    quality_of_service: Dict[str, Any] = None

class ROSBridge:
    def __init__(self):
        self.nodes = {}
        self.topics = {}
        self.services = {}
        self.parameters = {}
        self.transforms = {}
        self.is_running = False
        self.message_queue = asyncio.Queue()
        self.subscribers = {}
        self.publishers = {}
        
        # ROS Master simulation
        self.master_uri = "http://localhost:11311"
        self.node_counter = 0
        
        # Initialize core ROS components
        self._initialize_core_nodes()
    
    def _initialize_core_nodes(self):
        """Initialize essential ROS nodes"""
        # ROS Master
        self.parameters['/rosversion'] = '1.16.0'
        self.parameters['/rosdistro'] = 'noetic'
        self.parameters['/use_sim_time'] = False
        
        # Core topics
        self.topics['/rosout'] = {
            'type': 'rosgraph_msgs/Log',
            'publishers': [],
            'subscribers': []
        }
        
        self.topics['/tf'] = {
            'type': 'tf2_msgs/TFMessage',
            'publishers': [],
            'subscribers': []
        }
        
        self.topics['/clock'] = {
            'type': 'rosgraph_msgs/Clock',
            'publishers': [],
            'subscribers': []
        }
    
    async def start_bridge(self):
        """Start the ROS bridge"""
        if self.is_running:
            return
        
        self.is_running = True
        print("Starting ROS Bridge...")
        
        # Start message routing task
        asyncio.create_task(self._message_router())
        
        # Start parameter server
        asyncio.create_task(self._parameter_server())
        
        print("ROS Bridge started successfully")
    
    async def stop_bridge(self):
        """Stop the ROS bridge"""
        self.is_running = False
        print("ROS Bridge stopped")
    
    async def _message_router(self):
        """Route messages between publishers and subscribers"""
        while self.is_running:
            try:
                # Process queued messages
                if not self.message_queue.empty():
                    message = await self.message_queue.get()
                    await self._route_message(message)
                
                await asyncio.sleep(0.001)  # 1ms routing cycle
                
            except Exception as e:
                print(f"Message router error: {e}")
                await asyncio.sleep(0.1)
    
    async def _route_message(self, message: ROSMessage):
        """Route message to appropriate subscribers"""
        topic = message.topic
        
        if topic in self.topics:
            # Notify all subscribers
            for subscriber_callback in self.topics[topic].get('subscribers', []):
                try:
                    if asyncio.iscoroutinefunction(subscriber_callback):
                        await subscriber_callback(message)
                    else:
                        subscriber_callback(message)
                except Exception as e:
                    print(f"Subscriber callback error: {e}")
    
    async def _parameter_server(self):
        """Simulate ROS parameter server"""
        while self.is_running:
            # Periodically update dynamic parameters
            self.parameters['/time'] = time.time()
            await asyncio.sleep(1.0)
    
    def create_node(self, config: ROSNodeConfig) -> str:
        """Create a new ROS node"""
        node_id = f"{config.node_name}_{self.node_counter}"
        self.node_counter += 1
        
        self.nodes[node_id] = {
            'config': config,
            'created_at': datetime.now(),
            'active': True,
            'message_count': 0
        }
        
        # Initialize topics for this node
        for topic in config.topics:
            full_topic = f"{config.namespace.rstrip('/')}/{topic.lstrip('/')}"
            
            if full_topic not in self.topics:
                self.topics[full_topic] = {
                    'type': config.message_types[0].value if config.message_types else 'std_msgs/String',
                    'publishers': [],
                    'subscribers': []
                }
            
            if config.node_type == ROSNodeType.PUBLISHER:
                self.topics[full_topic]['publishers'].append(node_id)
            elif config.node_type == ROSNodeType.SUBSCRIBER:
                self.topics[full_topic]['subscribers'].append(node_id)
        
        print(f"Created ROS node: {node_id} ({config.node_type.value})")
        return node_id
    
    async def publish_message(self, node_id: str, topic: str, msg_type: ROSMessageType, data: Dict[str, Any]):
        """Publish a message to a topic"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        message = ROSMessage(
            topic=topic,
            msg_type=msg_type,
            timestamp=datetime.now(),
            data=data,
            sequence=self.nodes[node_id]['message_count']
        )
        
        self.nodes[node_id]['message_count'] += 1
        
        # Queue message for routing
        await self.message_queue.put(message)
        
        return message
    
    def subscribe_to_topic(self, node_id: str, topic: str, callback: Callable):
        """Subscribe to a topic"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        if topic not in self.topics:
            self.topics[topic] = {
                'type': 'std_msgs/String',
                'publishers': [],
                'subscribers': []
            }
        
        if callback not in self.topics[topic]['subscribers']:
            self.topics[topic]['subscribers'].append(callback)
        
        print(f"Node {node_id} subscribed to {topic}")
    
    def get_topics(self) -> Dict[str, Any]:
        """Get list of all topics"""
        return {
            topic: {
                'type': info['type'],
                'publisher_count': len(info['publishers']),
                'subscriber_count': len(info['subscribers'])
            }
            for topic, info in self.topics.items()
        }
    
    def get_nodes(self) -> Dict[str, Any]:
        """Get list of all nodes"""
        return {
            node_id: {
                'name': info['config'].node_name,
                'type': info['config'].node_type.value,
                'active': info['active'],
                'message_count': info['message_count']
            }
            for node_id, info in self.nodes.items()
        }
    
    def set_parameter(self, param_name: str, value: Any):
        """Set a parameter"""
        self.parameters[param_name] = value
        print(f"Parameter set: {param_name} = {value}")
    
    def get_parameter(self, param_name: str, default: Any = None) -> Any:
        """Get a parameter value"""
        return self.parameters.get(param_name, default)
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """Get all parameters"""
        return self.parameters.copy()

class ROSRobotController:
    """ROS-based robot controller"""
    
    def __init__(self, bridge: ROSBridge, robot_name: str):
        self.bridge = bridge
        self.robot_name = robot_name
        self.joint_states = {}
        self.current_pose = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
        self.target_pose = self.current_pose.copy()
        self.is_moving = False
        
        # Create ROS nodes
        self._setup_nodes()
        
        # Start control loop
        asyncio.create_task(self._control_loop())
    
    def _setup_nodes(self):
        """Setup ROS nodes for robot control"""
        # Joint state publisher
        joint_state_config = ROSNodeConfig(
            node_name=f"{self.robot_name}_joint_state_publisher",
            node_type=ROSNodeType.PUBLISHER,
            topics=["joint_states"],
            message_types=[ROSMessageType.SENSOR_JOINT_STATE],
            rate_hz=50.0
        )
        self.joint_state_publisher = self.bridge.create_node(joint_state_config)
        
        # Command velocity subscriber
        cmd_vel_config = ROSNodeConfig(
            node_name=f"{self.robot_name}_cmd_vel_subscriber",
            node_type=ROSNodeType.SUBSCRIBER,
            topics=["cmd_vel"],
            message_types=[ROSMessageType.GEOMETRY_TWIST],
            rate_hz=10.0
        )
        self.cmd_vel_subscriber = self.bridge.create_node(cmd_vel_config)
        
        # Odometry publisher
        odom_config = ROSNodeConfig(
            node_name=f"{self.robot_name}_odometry_publisher",
            node_type=ROSNodeType.PUBLISHER,
            topics=["odom"],
            message_types=[ROSMessageType.NAV_ODOMETRY],
            rate_hz=20.0
        )
        self.odom_publisher = self.bridge.create_node(odom_config)
        
        # Subscribe to command velocity
        self.bridge.subscribe_to_topic(
            self.cmd_vel_subscriber, 
            "cmd_vel", 
            self._cmd_vel_callback
        )
    
    async def _control_loop(self):
        """Main robot control loop"""
        last_time = time.time()
        
        while self.bridge.is_running:
            current_time = time.time()
            dt = current_time - last_time
            
            # Update robot state
            await self._update_robot_state(dt)
            
            # Publish joint states
            await self._publish_joint_states()
            
            # Publish odometry
            await self._publish_odometry()
            
            last_time = current_time
            await asyncio.sleep(0.02)  # 50Hz control loop
    
    def _cmd_vel_callback(self, message: ROSMessage):
        """Handle velocity commands"""
        twist_data = message.data
        
        # Extract linear and angular velocities
        linear_vel = twist_data.get('linear', {})
        angular_vel = twist_data.get('angular', {})
        
        # Update target velocities (simplified)
        self.target_vel = {
            'linear_x': linear_vel.get('x', 0.0),
            'linear_y': linear_vel.get('y', 0.0),
            'linear_z': linear_vel.get('z', 0.0),
            'angular_x': angular_vel.get('x', 0.0),
            'angular_y': angular_vel.get('y', 0.0),
            'angular_z': angular_vel.get('z', 0.0)
        }
        
        self.is_moving = any(abs(v) > 0.01 for v in self.target_vel.values())
        
        print(f"Robot {self.robot_name} received velocity command: "
              f"linear=({linear_vel.get('x', 0):.2f}, {linear_vel.get('y', 0):.2f}, {linear_vel.get('z', 0):.2f}), "
              f"angular=({angular_vel.get('x', 0):.2f}, {angular_vel.get('y', 0):.2f}, {angular_vel.get('z', 0):.2f})")
    
    async def _update_robot_state(self, dt: float):
        """Update robot state based on velocity commands"""
        if not hasattr(self, 'target_vel'):
            return
        
        # Simple kinematic model
        self.current_pose['x'] += self.target_vel['linear_x'] * dt
        self.current_pose['y'] += self.target_vel['linear_y'] * dt
        self.current_pose['z'] += self.target_vel['linear_z'] * dt
        
        self.current_pose['roll'] += self.target_vel['angular_x'] * dt
        self.current_pose['pitch'] += self.target_vel['angular_y'] * dt
        self.current_pose['yaw'] += self.target_vel['angular_z'] * dt
        
        # Normalize angles
        for angle in ['roll', 'pitch', 'yaw']:
            while self.current_pose[angle] > math.pi:
                self.current_pose[angle] -= 2 * math.pi
            while self.current_pose[angle] < -math.pi:
                self.current_pose[angle] += 2 * math.pi
    
    async def _publish_joint_states(self):
        """Publish joint states"""
        joint_data = {
            'header': {
                'stamp': time.time(),
                'frame_id': f"{self.robot_name}_base_link"
            },
            'name': ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6'],
            'position': [random.uniform(-math.pi, math.pi) for _ in range(6)],
            'velocity': [random.uniform(-1.0, 1.0) for _ in range(6)],
            'effort': [random.uniform(-10.0, 10.0) for _ in range(6)]
        }
        
        await self.bridge.publish_message(
            self.joint_state_publisher,
            "joint_states",
            ROSMessageType.SENSOR_JOINT_STATE,
            joint_data
        )
    
    async def _publish_odometry(self):
        """Publish odometry information"""
        odom_data = {
            'header': {
                'stamp': time.time(),
                'frame_id': 'odom'
            },
            'child_frame_id': f"{self.robot_name}_base_link",
            'pose': {
                'pose': {
                    'position': {
                        'x': self.current_pose['x'],
                        'y': self.current_pose['y'],
                        'z': self.current_pose['z']
                    },
                    'orientation': {
                        'x': 0.0,
                        'y': 0.0,
                        'z': math.sin(self.current_pose['yaw'] / 2),
                        'w': math.cos(self.current_pose['yaw'] / 2)
                    }
                }
            },
            'twist': {
                'twist': getattr(self, 'target_vel', {
                    'linear_x': 0, 'linear_y': 0, 'linear_z': 0,
                    'angular_x': 0, 'angular_y': 0, 'angular_z': 0
                })
            }
        }
        
        await self.bridge.publish_message(
            self.odom_publisher,
            "odom",
            ROSMessageType.NAV_ODOMETRY,
            odom_data
        )
    
    async def move_to_pose(self, target_x: float, target_y: float, target_yaw: float):
        """Move robot to target pose"""
        self.target_pose = {'x': target_x, 'y': target_y, 'yaw': target_yaw}
        
        print(f"Robot {self.robot_name} moving to pose: x={target_x:.2f}, y={target_y:.2f}, yaw={target_yaw:.2f}")
        
        # Simple proportional controller
        while True:
            dx = self.target_pose['x'] - self.current_pose['x']
            dy = self.target_pose['y'] - self.current_pose['y']
            dyaw = self.target_pose['yaw'] - self.current_pose['yaw']
            
            # Normalize yaw error
            while dyaw > math.pi:
                dyaw -= 2 * math.pi
            while dyaw < -math.pi:
                dyaw += 2 * math.pi
            
            # Check if reached target
            if abs(dx) < 0.1 and abs(dy) < 0.1 and abs(dyaw) < 0.1:
                break
            
            # Calculate velocities
            linear_vel = min(0.5, math.sqrt(dx**2 + dy**2))
            angular_vel = min(1.0, abs(dyaw)) * (1 if dyaw > 0 else -1)
            
            # Send velocity command
            cmd_vel_data = {
                'linear': {'x': linear_vel * math.cos(math.atan2(dy, dx)), 'y': 0.0, 'z': 0.0},
                'angular': {'x': 0.0, 'y': 0.0, 'z': angular_vel}
            }
            
            # Simulate velocity command
            self._cmd_vel_callback(ROSMessage(
                topic="cmd_vel",
                msg_type=ROSMessageType.GEOMETRY_TWIST,
                timestamp=datetime.now(),
                data=cmd_vel_data
            ))
            
            await asyncio.sleep(0.1)
        
        print(f"Robot {self.robot_name} reached target pose")
    
    def get_current_pose(self) -> Dict[str, float]:
        """Get current robot pose"""
        return self.current_pose.copy()

class ROSSensorSimulator:
    """ROS sensor data simulator"""
    
    def __init__(self, bridge: ROSBridge, sensor_name: str):
        self.bridge = bridge
        self.sensor_name = sensor_name
        
        # Setup sensor nodes
        self._setup_sensor_nodes()
        
        # Start sensor publishing
        asyncio.create_task(self._sensor_loop())
    
    def _setup_sensor_nodes(self):
        """Setup sensor publisher nodes"""
        # Laser scan publisher
        laser_config = ROSNodeConfig(
            node_name=f"{self.sensor_name}_laser_publisher",
            node_type=ROSNodeType.PUBLISHER,
            topics=["scan"],
            message_types=[ROSMessageType.SENSOR_LASER_SCAN],
            rate_hz=10.0
        )
        self.laser_publisher = self.bridge.create_node(laser_config)
        
        # Camera publisher
        camera_config = ROSNodeConfig(
            node_name=f"{self.sensor_name}_camera_publisher",
            node_type=ROSNodeType.PUBLISHER,
            topics=["camera/image_raw"],
            message_types=[ROSMessageType.SENSOR_IMAGE],
            rate_hz=30.0
        )
        self.camera_publisher = self.bridge.create_node(camera_config)
    
    async def _sensor_loop(self):
        """Main sensor data publishing loop"""
        while self.bridge.is_running:
            # Publish laser scan
            await self._publish_laser_scan()
            
            # Publish camera image (less frequently)
            if random.random() < 0.1:  # 10% chance
                await self._publish_camera_image()
            
            await asyncio.sleep(0.1)  # 10Hz
    
    async def _publish_laser_scan(self):
        """Publish simulated laser scan data"""
        ranges = []
        angle_min = -math.pi
        angle_max = math.pi
        angle_increment = 0.01  # ~1 degree
        
        angle = angle_min
        while angle <= angle_max:
            # Simulate distance measurements
            base_range = 5.0 + 2.0 * math.sin(angle * 3)  # Simulated environment
            noise = random.uniform(-0.1, 0.1)
            range_val = max(0.1, base_range + noise)
            ranges.append(range_val)
            angle += angle_increment
        
        laser_data = {
            'header': {
                'stamp': time.time(),
                'frame_id': f"{self.sensor_name}_laser_link"
            },
            'angle_min': angle_min,
            'angle_max': angle_max,
            'angle_increment': angle_increment,
            'time_increment': 0.0,
            'scan_time': 0.1,
            'range_min': 0.1,
            'range_max': 10.0,
            'ranges': ranges,
            'intensities': [random.uniform(0, 100) for _ in ranges]
        }
        
        await self.bridge.publish_message(
            self.laser_publisher,
            "scan",
            ROSMessageType.SENSOR_LASER_SCAN,
            laser_data
        )
    
    async def _publish_camera_image(self):
        """Publish simulated camera image"""
        image_data = {
            'header': {
                'stamp': time.time(),
                'frame_id': f"{self.sensor_name}_camera_link"
            },
            'height': 480,
            'width': 640,
            'encoding': 'rgb8',
            'is_bigendian': 0,
            'step': 640 * 3,
            'data': [random.randint(0, 255) for _ in range(640 * 480 * 3)]  # Random RGB data
        }
        
        await self.bridge.publish_message(
            self.camera_publisher,
            "camera/image_raw",
            ROSMessageType.SENSOR_IMAGE,
            image_data
        )

if __name__ == "__main__":
    print("ROS Bridge Simulation")
    print("=" * 50)
    
    async def demo():
        # Create ROS bridge
        bridge = ROSBridge()
        await bridge.start_bridge()
        
        # Create robot controller
        robot = ROSRobotController(bridge, "demo_robot")
        
        # Create sensor simulator
        sensors = ROSSensorSimulator(bridge, "demo_sensors")
        
        # Wait for initialization
        await asyncio.sleep(1)
        
        print("ROS system initialized")
        print(f"Topics: {list(bridge.get_topics().keys())}")
        print(f"Nodes: {list(bridge.get_nodes().keys())}")
        
        # Demonstrate robot movement
        print("\nDemonstrating robot movement...")
        
        # Move to different poses
        poses = [
            (1.0, 0.0, 0.0),
            (1.0, 1.0, math.pi/2),
            (0.0, 1.0, math.pi),
            (0.0, 0.0, -math.pi/2)
        ]
        
        for x, y, yaw in poses:
            print(f"Moving to: ({x:.1f}, {y:.1f}, {yaw:.2f})")
            await robot.move_to_pose(x, y, yaw)
            
            current_pose = robot.get_current_pose()
            print(f"Current pose: ({current_pose['x']:.2f}, {current_pose['y']:.2f}, {current_pose['yaw']:.2f})")
            
            await asyncio.sleep(1)
        
        # Monitor system for a while
        print("\nMonitoring system...")
        for i in range(10):
            await asyncio.sleep(1)
            if i % 3 == 0:
                topics = bridge.get_topics()
                print(f"Active topics: {len(topics)}")
        
        await bridge.stop_bridge()
        print("Demo completed")
    
    asyncio.run(demo())