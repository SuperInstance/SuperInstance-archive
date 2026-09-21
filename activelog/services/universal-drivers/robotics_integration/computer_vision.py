import asyncio
import numpy as np
import random
import time
import math
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import json

class VisionAlgorithm(Enum):
    EDGE_DETECTION = "edge_detection"
    CORNER_DETECTION = "corner_detection"
    BLOB_DETECTION = "blob_detection"
    TEMPLATE_MATCHING = "template_matching"
    OPTICAL_FLOW = "optical_flow"
    STEREO_VISION = "stereo_vision"
    OBJECT_DETECTION = "object_detection"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    DEPTH_ESTIMATION = "depth_estimation"
    SLAM = "slam"

class ObjectClass(Enum):
    PERSON = "person"
    CAR = "car"
    BICYCLE = "bicycle"
    TRUCK = "truck"
    BUS = "bus"
    TRAFFIC_SIGN = "traffic_sign"
    TRAFFIC_LIGHT = "traffic_light"
    OBSTACLE = "obstacle"
    LANDMARK = "landmark"
    UNKNOWN = "unknown"

@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int
    confidence: float
    
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def area(self) -> int:
        return self.width * self.height

@dataclass
class DetectedObject:
    object_class: ObjectClass
    bounding_box: BoundingBox
    confidence: float
    attributes: Dict[str, Any]
    tracking_id: Optional[int] = None

@dataclass
class Keypoint:
    x: int
    y: int
    strength: float

@dataclass
class VisionFrame:
    timestamp: datetime
    frame_id: int
    width: int
    height: int
    channels: int
    data: np.ndarray
    metadata: Dict[str, Any]

@dataclass
class VisionResult:
    algorithm: VisionAlgorithm
    timestamp: datetime
    frame_id: int
    processing_time: float
    results: Dict[str, Any]
    confidence: float

class ComputerVisionProcessor:
    def __init__(self, algorithms: List[VisionAlgorithm] = None):
        self.algorithms = algorithms or [VisionAlgorithm.OBJECT_DETECTION]
        self.frame_buffer = []
        self.max_buffer_size = 100
        self.processing_stats = {alg: {'count': 0, 'avg_time': 0.0} for alg in self.algorithms}
        
        # Object tracking
        self.tracked_objects = {}
        self.next_tracking_id = 1
        
        # SLAM state
        self.slam_map = []
        self.robot_pose = {'x': 0.0, 'y': 0.0, 'theta': 0.0}
        
        # Calibration parameters (simulated camera)
        self.camera_matrix = np.array([[800, 0, 320], [0, 800, 240], [0, 0, 1]])
        self.distortion_coeffs = np.array([0.1, -0.2, 0, 0, 0])
        
    async def process_frame(self, frame: VisionFrame) -> List[VisionResult]:
        """Process a single frame with all configured algorithms"""
        results = []
        
        # Store frame in buffer
        self.frame_buffer.append(frame)
        if len(self.frame_buffer) > self.max_buffer_size:
            self.frame_buffer.pop(0)
        
        # Process with each algorithm
        for algorithm in self.algorithms:
            start_time = time.time()
            
            try:
                result = await self._process_algorithm(frame, algorithm)
                processing_time = time.time() - start_time
                
                vision_result = VisionResult(
                    algorithm=algorithm,
                    timestamp=datetime.now(),
                    frame_id=frame.frame_id,
                    processing_time=processing_time,
                    results=result,
                    confidence=result.get('confidence', 0.8)
                )
                
                results.append(vision_result)
                
                # Update statistics
                stats = self.processing_stats[algorithm]
                stats['count'] += 1
                stats['avg_time'] = (stats['avg_time'] * (stats['count'] - 1) + processing_time) / stats['count']
                
            except Exception as e:
                print(f"Error processing {algorithm.value}: {e}")
        
        return results
    
    async def _process_algorithm(self, frame: VisionFrame, algorithm: VisionAlgorithm) -> Dict[str, Any]:
        """Process frame with specific algorithm"""
        if algorithm == VisionAlgorithm.EDGE_DETECTION:
            return await self._edge_detection(frame)
        elif algorithm == VisionAlgorithm.CORNER_DETECTION:
            return await self._corner_detection(frame)
        elif algorithm == VisionAlgorithm.BLOB_DETECTION:
            return await self._blob_detection(frame)
        elif algorithm == VisionAlgorithm.TEMPLATE_MATCHING:
            return await self._template_matching(frame)
        elif algorithm == VisionAlgorithm.OPTICAL_FLOW:
            return await self._optical_flow(frame)
        elif algorithm == VisionAlgorithm.OBJECT_DETECTION:
            return await self._object_detection(frame)
        elif algorithm == VisionAlgorithm.SEMANTIC_SEGMENTATION:
            return await self._semantic_segmentation(frame)
        elif algorithm == VisionAlgorithm.DEPTH_ESTIMATION:
            return await self._depth_estimation(frame)
        elif algorithm == VisionAlgorithm.SLAM:
            return await self._slam_processing(frame)
        else:
            return {'error': f'Unknown algorithm: {algorithm}'}
    
    async def _edge_detection(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate edge detection (Canny-style)"""
        # Simulate edge detection processing
        await asyncio.sleep(0.01)  # Simulate processing time
        
        # Generate synthetic edge map
        height, width = frame.height, frame.width
        edge_strength = np.random.random((height // 10, width // 10))
        
        # Simulate edge locations
        edges = []
        for y in range(0, height, 10):
            for x in range(0, width, 10):
                if edge_strength[y // 10, x // 10] > 0.7:
                    edges.append({'x': x, 'y': y, 'strength': edge_strength[y // 10, x // 10]})
        
        return {
            'edges': edges,
            'edge_count': len(edges),
            'confidence': 0.85
        }
    
    async def _corner_detection(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate corner detection (Harris corners)"""
        await asyncio.sleep(0.015)
        
        # Generate synthetic corners
        corner_count = random.randint(20, 80)
        corners = []
        
        for _ in range(corner_count):
            corner = Keypoint(
                x=random.randint(0, frame.width - 1),
                y=random.randint(0, frame.height - 1),
                strength=random.uniform(0.5, 1.0)
            )
            corners.append(asdict(corner))
        
        return {
            'corners': corners,
            'corner_count': len(corners),
            'confidence': 0.8
        }
    
    async def _blob_detection(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate blob detection"""
        await asyncio.sleep(0.02)
        
        # Generate synthetic blobs
        blob_count = random.randint(5, 20)
        blobs = []
        
        for _ in range(blob_count):
            blob = {
                'center_x': random.randint(0, frame.width - 1),
                'center_y': random.randint(0, frame.height - 1),
                'radius': random.uniform(10, 50),
                'strength': random.uniform(0.6, 1.0)
            }
            blobs.append(blob)
        
        return {
            'blobs': blobs,
            'blob_count': len(blobs),
            'confidence': 0.75
        }
    
    async def _template_matching(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate template matching"""
        await asyncio.sleep(0.03)
        
        # Simulate finding template matches
        matches = []
        template_count = random.randint(0, 5)
        
        for _ in range(template_count):
            match = {
                'x': random.randint(0, frame.width - 100),
                'y': random.randint(0, frame.height - 100),
                'width': random.randint(50, 100),
                'height': random.randint(50, 100),
                'correlation': random.uniform(0.7, 0.95),
                'template_id': random.randint(1, 10)
            }
            matches.append(match)
        
        return {
            'matches': matches,
            'match_count': len(matches),
            'confidence': 0.82
        }
    
    async def _optical_flow(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate optical flow calculation"""
        await asyncio.sleep(0.025)
        
        if len(self.frame_buffer) < 2:
            return {'flow_vectors': [], 'confidence': 0.0}
        
        # Simulate flow vectors
        flow_vectors = []
        vector_count = random.randint(50, 200)
        
        for _ in range(vector_count):
            vector = {
                'x': random.randint(0, frame.width - 1),
                'y': random.randint(0, frame.height - 1),
                'dx': random.uniform(-5, 5),
                'dy': random.uniform(-5, 5),
                'magnitude': 0.0
            }
            vector['magnitude'] = math.sqrt(vector['dx']**2 + vector['dy']**2)
            flow_vectors.append(vector)
        
        avg_flow = np.mean([v['magnitude'] for v in flow_vectors]) if flow_vectors else 0
        
        return {
            'flow_vectors': flow_vectors,
            'vector_count': len(flow_vectors),
            'average_flow': avg_flow,
            'confidence': 0.78
        }
    
    async def _object_detection(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate object detection (YOLO-style)"""
        await asyncio.sleep(0.05)  # More processing time for object detection
        
        # Generate synthetic detections
        object_classes = list(ObjectClass)
        detection_count = random.randint(1, 8)
        detections = []
        
        for _ in range(detection_count):
            obj_class = random.choice(object_classes)
            
            # Create bounding box
            x = random.randint(0, frame.width - 100)
            y = random.randint(0, frame.height - 100)
            w = random.randint(50, min(200, frame.width - x))
            h = random.randint(50, min(200, frame.height - y))
            
            bbox = BoundingBox(x, y, w, h, random.uniform(0.6, 0.95))
            
            # Assign or update tracking ID
            center = bbox.center()
            tracking_id = self._assign_tracking_id(center, obj_class)
            
            detection = DetectedObject(
                object_class=obj_class,
                bounding_box=bbox,
                confidence=bbox.confidence,
                attributes={
                    'distance': random.uniform(1.0, 20.0),
                    'velocity': random.uniform(0.0, 10.0),
                    'color': random.choice(['red', 'blue', 'green', 'yellow', 'black', 'white'])
                },
                tracking_id=tracking_id
            )
            
            detections.append(asdict(detection))
        
        return {
            'detections': detections,
            'detection_count': len(detections),
            'confidence': 0.87
        }
    
    def _assign_tracking_id(self, center: Tuple[int, int], obj_class: ObjectClass) -> int:
        """Assign tracking ID to detected object"""
        # Simple tracking based on proximity
        threshold = 50  # pixels
        
        for tracking_id, tracked_obj in self.tracked_objects.items():
            last_center = tracked_obj['center']
            distance = math.sqrt((center[0] - last_center[0])**2 + (center[1] - last_center[1])**2)
            
            if distance < threshold and tracked_obj['class'] == obj_class:
                # Update tracked object
                self.tracked_objects[tracking_id] = {
                    'center': center,
                    'class': obj_class,
                    'last_seen': datetime.now()
                }
                return tracking_id
        
        # New object - assign new ID
        new_id = self.next_tracking_id
        self.next_tracking_id += 1
        
        self.tracked_objects[new_id] = {
            'center': center,
            'class': obj_class,
            'last_seen': datetime.now()
        }
        
        return new_id
    
    async def _semantic_segmentation(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate semantic segmentation"""
        await asyncio.sleep(0.08)  # High processing time
        
        # Simulate segmentation mask
        height, width = frame.height // 8, frame.width // 8  # Reduced resolution
        
        classes = ['background', 'road', 'building', 'vehicle', 'person', 'vegetation']
        segmentation_map = np.random.choice(len(classes), size=(height, width))
        
        # Calculate class statistics
        class_pixels = {}
        total_pixels = height * width
        
        for i, class_name in enumerate(classes):
            pixel_count = np.sum(segmentation_map == i)
            class_pixels[class_name] = {
                'pixel_count': int(pixel_count),
                'percentage': float(pixel_count / total_pixels * 100)
            }
        
        return {
            'segmentation_map': segmentation_map.tolist(),
            'classes': classes,
            'class_statistics': class_pixels,
            'resolution': (height, width),
            'confidence': 0.83
        }
    
    async def _depth_estimation(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate depth estimation"""
        await asyncio.sleep(0.04)
        
        # Generate synthetic depth map
        height, width = frame.height // 4, frame.width // 4
        
        # Simulate depth values (in meters)
        depth_map = np.random.uniform(0.5, 20.0, size=(height, width))
        
        # Add some structure (closer objects in center, farther on edges)
        y_center, x_center = height // 2, width // 2
        for y in range(height):
            for x in range(width):
                distance_from_center = math.sqrt((x - x_center)**2 + (y - y_center)**2)
                depth_map[y, x] = 2.0 + distance_from_center * 0.1 + random.uniform(-0.5, 0.5)
        
        # Calculate statistics
        avg_depth = float(np.mean(depth_map))
        min_depth = float(np.min(depth_map))
        max_depth = float(np.max(depth_map))
        
        return {
            'depth_map': depth_map.tolist(),
            'resolution': (height, width),
            'depth_statistics': {
                'average': avg_depth,
                'minimum': min_depth,
                'maximum': max_depth
            },
            'confidence': 0.79
        }
    
    async def _slam_processing(self, frame: VisionFrame) -> Dict[str, Any]:
        """Simulate SLAM (Simultaneous Localization and Mapping)"""
        await asyncio.sleep(0.06)
        
        # Update robot pose (random walk for simulation)
        self.robot_pose['x'] += random.uniform(-0.1, 0.1)
        self.robot_pose['y'] += random.uniform(-0.1, 0.1)
        self.robot_pose['theta'] += random.uniform(-0.05, 0.05)
        
        # Add landmarks to map
        if random.random() < 0.3:  # 30% chance of detecting new landmark
            landmark = {
                'id': len(self.slam_map) + 1,
                'x': self.robot_pose['x'] + random.uniform(-5, 5),
                'y': self.robot_pose['y'] + random.uniform(-5, 5),
                'type': random.choice(['corner', 'pole', 'tree', 'sign']),
                'confidence': random.uniform(0.7, 0.95)
            }
            self.slam_map.append(landmark)
        
        # Estimate uncertainty
        pose_uncertainty = {
            'x_std': random.uniform(0.05, 0.2),
            'y_std': random.uniform(0.05, 0.2),
            'theta_std': random.uniform(0.02, 0.1)
        }
        
        return {
            'robot_pose': self.robot_pose.copy(),
            'pose_uncertainty': pose_uncertainty,
            'landmarks': self.slam_map[-10:],  # Last 10 landmarks
            'total_landmarks': len(self.slam_map),
            'confidence': 0.85
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing performance statistics"""
        return {
            'algorithms': [alg.value for alg in self.algorithms],
            'statistics': {alg.value: stats for alg, stats in self.processing_stats.items()},
            'buffer_size': len(self.frame_buffer),
            'tracked_objects': len(self.tracked_objects),
            'slam_landmarks': len(self.slam_map)
        }
    
    def cleanup_tracking(self, max_age_seconds: float = 2.0):
        """Clean up old tracked objects"""
        current_time = datetime.now()
        expired_ids = []
        
        for tracking_id, tracked_obj in self.tracked_objects.items():
            age = (current_time - tracked_obj['last_seen']).total_seconds()
            if age > max_age_seconds:
                expired_ids.append(tracking_id)
        
        for tracking_id in expired_ids:
            del self.tracked_objects[tracking_id]

class CameraSimulator:
    """Simulate camera input for vision processing"""
    
    def __init__(self, width: int = 640, height: int = 480, fps: float = 30.0):
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_id = 0
        self.is_running = False
        
    async def start_capture(self, callback: Callable[[VisionFrame], None]):
        """Start capturing frames"""
        self.is_running = True
        
        while self.is_running:
            # Generate synthetic frame
            frame = self._generate_frame()
            
            # Call processing callback
            if callback:
                try:
                    await callback(frame)
                except Exception as e:
                    print(f"Frame processing error: {e}")
            
            # Wait for next frame
            await asyncio.sleep(1.0 / self.fps)
    
    def stop_capture(self):
        """Stop capturing frames"""
        self.is_running = False
    
    def _generate_frame(self) -> VisionFrame:
        """Generate synthetic camera frame"""
        # Create random RGB image data
        data = np.random.randint(0, 256, size=(self.height, self.width, 3), dtype=np.uint8)
        
        # Add some structure to make it more realistic
        # Add horizontal gradient
        for y in range(self.height):
            data[y, :, :] = data[y, :, :] * (0.5 + 0.5 * y / self.height)
        
        # Add some "objects" (rectangles)
        for _ in range(random.randint(2, 6)):
            x = random.randint(0, self.width - 50)
            y = random.randint(0, self.height - 50)
            w = random.randint(20, 100)
            h = random.randint(20, 100)
            
            color = [random.randint(0, 255) for _ in range(3)]
            data[y:y+h, x:x+w] = color
        
        frame = VisionFrame(
            timestamp=datetime.now(),
            frame_id=self.frame_id,
            width=self.width,
            height=self.height,
            channels=3,
            data=data,
            metadata={
                'camera_id': 'sim_camera_0',
                'exposure_time': 0.033,
                'gain': 1.0
            }
        )
        
        self.frame_id += 1
        return frame

if __name__ == "__main__":
    print("Computer Vision Pipeline Simulation")
    print("=" * 50)
    
    async def demo():
        # Create vision processor with multiple algorithms
        algorithms = [
            VisionAlgorithm.OBJECT_DETECTION,
            VisionAlgorithm.EDGE_DETECTION,
            VisionAlgorithm.OPTICAL_FLOW,
            VisionAlgorithm.DEPTH_ESTIMATION,
            VisionAlgorithm.SLAM
        ]
        
        processor = ComputerVisionProcessor(algorithms)
        
        # Create camera simulator
        camera = CameraSimulator(width=640, height=480, fps=10.0)  # Lower FPS for demo
        
        # Frame processing callback
        async def process_frame(frame: VisionFrame):
            print(f"\nProcessing frame {frame.frame_id} ({frame.width}x{frame.height})")
            
            results = await processor.process_frame(frame)
            
            for result in results:
                print(f"  {result.algorithm.value}: {result.processing_time:.3f}s")
                
                # Show interesting results
                if result.algorithm == VisionAlgorithm.OBJECT_DETECTION:
                    detections = result.results.get('detections', [])
                    print(f"    Detected {len(detections)} objects:")
                    for det in detections[:3]:  # Show first 3
                        print(f"      {det['object_class']} (conf: {det['confidence']:.2f})")
                
                elif result.algorithm == VisionAlgorithm.SLAM:
                    pose = result.results.get('robot_pose', {})
                    landmarks = result.results.get('total_landmarks', 0)
                    print(f"    Robot pose: ({pose.get('x', 0):.2f}, {pose.get('y', 0):.2f})")
                    print(f"    Total landmarks: {landmarks}")
                
                elif result.algorithm == VisionAlgorithm.DEPTH_ESTIMATION:
                    stats = result.results.get('depth_statistics', {})
                    avg_depth = stats.get('average', 0)
                    print(f"    Average depth: {avg_depth:.2f}m")
        
        # Start camera and run for 10 frames
        print("Starting computer vision demo...")
        
        camera_task = asyncio.create_task(camera.start_capture(process_frame))
        
        # Run for 10 seconds
        await asyncio.sleep(10)
        
        # Stop camera
        camera.stop_capture()
        await camera_task
        
        # Show final statistics
        print("\nFinal Statistics:")
        stats = processor.get_processing_stats()
        for alg_name, alg_stats in stats['statistics'].items():
            print(f"  {alg_name}: {alg_stats['count']} frames, avg {alg_stats['avg_time']:.3f}s")
        
        print(f"  Tracked objects: {stats['tracked_objects']}")
        print(f"  SLAM landmarks: {stats['slam_landmarks']}")
        
        print("Computer vision demo completed")
    
    asyncio.run(demo())