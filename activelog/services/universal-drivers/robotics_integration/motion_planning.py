import asyncio
import numpy as np
import math
import random
import time
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import heapq
from collections import deque

class PlannerType(Enum):
    RRT = "rrt"  # Rapidly-exploring Random Tree
    RRT_STAR = "rrt_star"
    A_STAR = "a_star"
    DIJKSTRA = "dijkstra"
    PRM = "prm"  # Probabilistic Roadmap
    RRT_CONNECT = "rrt_connect"
    INFORMED_RRT = "informed_rrt"
    POTENTIAL_FIELD = "potential_field"
    QUINTIC_POLYNOMIAL = "quintic_polynomial"

class ObstacleType(Enum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    POLYGON = "polygon"
    SPHERE = "sphere"
    BOX = "box"
    MESH = "mesh"

@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)
    
    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Point':
        return Point(self.x * scalar, self.y * scalar, self.z * scalar)

@dataclass
class Obstacle:
    obstacle_type: ObstacleType
    position: Point
    dimensions: Dict[str, float]  # radius for circle, width/height for rectangle, etc.
    orientation: float = 0.0  # radians
    
    def contains_point(self, point: Point) -> bool:
        if self.obstacle_type == ObstacleType.CIRCLE:
            return point.distance_to(self.position) <= self.dimensions['radius']
        elif self.obstacle_type == ObstacleType.RECTANGLE:
            # Simplified rectangle collision (axis-aligned)
            dx = abs(point.x - self.position.x)
            dy = abs(point.y - self.position.y)
            return dx <= self.dimensions['width']/2 and dy <= self.dimensions['height']/2
        elif self.obstacle_type == ObstacleType.SPHERE:
            return point.distance_to(self.position) <= self.dimensions['radius']
        elif self.obstacle_type == ObstacleType.BOX:
            dx = abs(point.x - self.position.x)
            dy = abs(point.y - self.position.y)
            dz = abs(point.z - self.position.z)
            return (dx <= self.dimensions['width']/2 and 
                   dy <= self.dimensions['height']/2 and 
                   dz <= self.dimensions['depth']/2)
        return False

@dataclass
class TrajectoryPoint:
    position: Point
    velocity: Point
    acceleration: Point
    timestamp: float
    orientation: float = 0.0

@dataclass
class MotionPlan:
    waypoints: List[Point]
    trajectory: List[TrajectoryPoint]
    total_distance: float
    total_time: float
    planner_used: PlannerType
    planning_time: float
    success: bool
    metadata: Dict[str, Any]

class EnvironmentMap:
    def __init__(self, bounds: Tuple[float, float, float, float], resolution: float = 0.1):
        self.min_x, self.min_y, self.max_x, self.max_y = bounds
        self.resolution = resolution
        self.obstacles = []
        self.width = int((self.max_x - self.min_x) / resolution)
        self.height = int((self.max_y - self.min_y) / resolution)
        self.occupancy_grid = np.zeros((self.height, self.width), dtype=bool)
        
    def add_obstacle(self, obstacle: Obstacle):
        self.obstacles.append(obstacle)
        self._update_occupancy_grid()
    
    def _update_occupancy_grid(self):
        """Update occupancy grid based on obstacles"""
        self.occupancy_grid.fill(False)
        
        for i in range(self.height):
            for j in range(self.width):
                world_x = self.min_x + j * self.resolution
                world_y = self.min_y + i * self.resolution
                point = Point(world_x, world_y)
                
                for obstacle in self.obstacles:
                    if obstacle.contains_point(point):
                        self.occupancy_grid[i, j] = True
                        break
    
    def is_point_valid(self, point: Point) -> bool:
        # Check bounds
        if not (self.min_x <= point.x <= self.max_x and self.min_y <= point.y <= self.max_y):
            return False
        
        # Check occupancy grid
        grid_x = int((point.x - self.min_x) / self.resolution)
        grid_y = int((point.y - self.min_y) / self.resolution)
        
        if 0 <= grid_x < self.width and 0 <= grid_y < self.height:
            return not self.occupancy_grid[grid_y, grid_x]
        
        return False
    
    def is_path_valid(self, start: Point, end: Point, step_size: float = 0.1) -> bool:
        """Check if straight line path between points is valid"""
        distance = start.distance_to(end)
        if distance == 0:
            return True
        
        steps = int(distance / step_size) + 1
        for i in range(steps + 1):
            t = i / steps if steps > 0 else 0
            point = start + (end - start) * t
            if not self.is_point_valid(point):
                return False
        
        return True

class MotionPlanner:
    def __init__(self, environment: EnvironmentMap, planner_type: PlannerType = PlannerType.RRT):
        self.environment = environment
        self.planner_type = planner_type
        self.max_iterations = 5000
        self.step_size = 0.2
        self.goal_tolerance = 0.1
        
    async def plan_path(self, start: Point, goal: Point) -> MotionPlan:
        """Plan a path from start to goal"""
        planning_start_time = time.time()
        
        # Validate start and goal
        if not self.environment.is_point_valid(start):
            return MotionPlan([], [], 0, 0, self.planner_type, 0, False, {'error': 'Invalid start point'})
        
        if not self.environment.is_point_valid(goal):
            return MotionPlan([], [], 0, 0, self.planner_type, 0, False, {'error': 'Invalid goal point'})
        
        # Plan based on algorithm type
        if self.planner_type == PlannerType.RRT:
            waypoints = await self._plan_rrt(start, goal)
        elif self.planner_type == PlannerType.RRT_STAR:
            waypoints = await self._plan_rrt_star(start, goal)
        elif self.planner_type == PlannerType.A_STAR:
            waypoints = await self._plan_a_star(start, goal)
        elif self.planner_type == PlannerType.PRM:
            waypoints = await self._plan_prm(start, goal)
        else:
            waypoints = await self._plan_rrt(start, goal)  # Default to RRT
        
        planning_time = time.time() - planning_start_time
        
        if not waypoints:
            return MotionPlan([], [], 0, 0, self.planner_type, planning_time, False, {'error': 'No path found'})
        
        # Generate smooth trajectory
        trajectory = await self._generate_trajectory(waypoints)
        
        # Calculate path metrics
        total_distance = sum(waypoints[i].distance_to(waypoints[i+1]) for i in range(len(waypoints)-1))
        total_time = trajectory[-1].timestamp if trajectory else 0
        
        return MotionPlan(
            waypoints=waypoints,
            trajectory=trajectory,
            total_distance=total_distance,
            total_time=total_time,
            planner_used=self.planner_type,
            planning_time=planning_time,
            success=True,
            metadata={'iterations': getattr(self, '_last_iterations', 0)}
        )
    
    async def _plan_rrt(self, start: Point, goal: Point) -> List[Point]:
        """RRT (Rapidly-exploring Random Tree) planning"""
        class TreeNode:
            def __init__(self, point: Point, parent=None):
                self.point = point
                self.parent = parent
                self.children = []
        
        tree = [TreeNode(start)]
        self._last_iterations = 0
        
        for iteration in range(self.max_iterations):
            self._last_iterations = iteration + 1
            
            # Sample random point
            if random.random() < 0.1:  # 10% chance to sample goal
                rand_point = goal
            else:
                rand_point = Point(
                    random.uniform(self.environment.min_x, self.environment.max_x),
                    random.uniform(self.environment.min_y, self.environment.max_y)
                )
            
            # Find nearest node
            nearest_node = min(tree, key=lambda n: n.point.distance_to(rand_point))
            
            # Extend towards random point
            direction = rand_point - nearest_node.point
            distance = nearest_node.point.distance_to(rand_point)
            
            if distance > self.step_size:
                direction = direction * (self.step_size / distance)
            
            new_point = nearest_node.point + direction
            
            # Check if new point is valid and path is collision-free
            if (self.environment.is_point_valid(new_point) and 
                self.environment.is_path_valid(nearest_node.point, new_point)):
                
                new_node = TreeNode(new_point, nearest_node)
                nearest_node.children.append(new_node)
                tree.append(new_node)
                
                # Check if goal is reached
                if new_point.distance_to(goal) <= self.goal_tolerance:
                    # Construct path
                    path = []
                    current = new_node
                    while current:
                        path.append(current.point)
                        current = current.parent
                    path.reverse()
                    return path
            
            # Yield control periodically
            if iteration % 100 == 0:
                await asyncio.sleep(0.001)
        
        return []  # No path found
    
    async def _plan_rrt_star(self, start: Point, goal: Point) -> List[Point]:
        """RRT* (optimal RRT) planning"""
        class TreeNode:
            def __init__(self, point: Point, parent=None, cost=0):
                self.point = point
                self.parent = parent
                self.children = []
                self.cost = cost
        
        tree = [TreeNode(start, cost=0)]
        search_radius = 1.0
        self._last_iterations = 0
        
        for iteration in range(self.max_iterations):
            self._last_iterations = iteration + 1
            
            # Sample random point
            if random.random() < 0.1:
                rand_point = goal
            else:
                rand_point = Point(
                    random.uniform(self.environment.min_x, self.environment.max_x),
                    random.uniform(self.environment.min_y, self.environment.max_y)
                )
            
            # Find nearest node
            nearest_node = min(tree, key=lambda n: n.point.distance_to(rand_point))
            
            # Extend towards random point
            direction = rand_point - nearest_node.point
            distance = nearest_node.point.distance_to(rand_point)
            
            if distance > self.step_size:
                direction = direction * (self.step_size / distance)
            
            new_point = nearest_node.point + direction
            
            if (self.environment.is_point_valid(new_point) and 
                self.environment.is_path_valid(nearest_node.point, new_point)):
                
                # Find nearby nodes for rewiring
                nearby_nodes = [n for n in tree 
                              if n.point.distance_to(new_point) <= search_radius]
                
                # Choose parent with minimum cost
                best_parent = nearest_node
                min_cost = nearest_node.cost + nearest_node.point.distance_to(new_point)
                
                for node in nearby_nodes:
                    cost = node.cost + node.point.distance_to(new_point)
                    if (cost < min_cost and 
                        self.environment.is_path_valid(node.point, new_point)):
                        best_parent = node
                        min_cost = cost
                
                new_node = TreeNode(new_point, best_parent, min_cost)
                best_parent.children.append(new_node)
                tree.append(new_node)
                
                # Rewire nearby nodes
                for node in nearby_nodes:
                    if node != best_parent:
                        new_cost = new_node.cost + new_node.point.distance_to(node.point)
                        if (new_cost < node.cost and 
                            self.environment.is_path_valid(new_node.point, node.point)):
                            # Rewire
                            if node.parent:
                                node.parent.children.remove(node)
                            node.parent = new_node
                            node.cost = new_cost
                            new_node.children.append(node)
                
                # Check if goal is reached
                if new_point.distance_to(goal) <= self.goal_tolerance:
                    path = []
                    current = new_node
                    while current:
                        path.append(current.point)
                        current = current.parent
                    path.reverse()
                    return path
            
            if iteration % 100 == 0:
                await asyncio.sleep(0.001)
        
        return []
    
    async def _plan_a_star(self, start: Point, goal: Point) -> List[Point]:
        """A* grid-based planning"""
        # Convert to grid coordinates
        def world_to_grid(point: Point) -> Tuple[int, int]:
            x = int((point.x - self.environment.min_x) / self.environment.resolution)
            y = int((point.y - self.environment.min_y) / self.environment.resolution)
            return (x, y)
        
        def grid_to_world(grid_x: int, grid_y: int) -> Point:
            x = self.environment.min_x + grid_x * self.environment.resolution
            y = self.environment.min_y + grid_y * self.environment.resolution
            return Point(x, y)
        
        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
            return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)
        
        start_grid = world_to_grid(start)
        goal_grid = world_to_grid(goal)
        
        # A* algorithm
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: heuristic(start_grid, goal_grid)}
        
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        
        iteration = 0
        while open_set and iteration < self.max_iterations:
            iteration += 1
            
            current = heapq.heappop(open_set)[1]
            
            if current == goal_grid:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(grid_to_world(*current))
                    current = came_from[current]
                path.append(start)
                path.reverse()
                return path
            
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Check bounds and obstacles
                if (0 <= neighbor[0] < self.environment.width and 
                    0 <= neighbor[1] < self.environment.height and
                    not self.environment.occupancy_grid[neighbor[1], neighbor[0]]):
                    
                    tentative_g = g_score[current] + math.sqrt(dx**2 + dy**2)
                    
                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score[neighbor] = tentative_g + heuristic(neighbor, goal_grid)
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
            
            if iteration % 100 == 0:
                await asyncio.sleep(0.001)
        
        return []
    
    async def _plan_prm(self, start: Point, goal: Point) -> List[Point]:
        """Probabilistic Roadmap (PRM) planning"""
        # Generate random samples
        samples = [start, goal]
        sample_count = 500
        
        for _ in range(sample_count):
            point = Point(
                random.uniform(self.environment.min_x, self.environment.max_x),
                random.uniform(self.environment.min_y, self.environment.max_y)
            )
            if self.environment.is_point_valid(point):
                samples.append(point)
        
        # Build roadmap
        roadmap = {i: [] for i in range(len(samples))}
        connection_radius = 1.0
        
        for i, sample1 in enumerate(samples):
            for j, sample2 in enumerate(samples[i+1:], i+1):
                if (sample1.distance_to(sample2) <= connection_radius and
                    self.environment.is_path_valid(sample1, sample2)):
                    roadmap[i].append(j)
                    roadmap[j].append(i)
        
        # Find shortest path using Dijkstra
        start_idx = 0
        goal_idx = 1
        
        distances = {i: float('inf') for i in range(len(samples))}
        distances[start_idx] = 0
        previous = {}
        unvisited = set(range(len(samples)))
        
        while unvisited:
            current = min(unvisited, key=lambda x: distances[x])
            unvisited.remove(current)
            
            if current == goal_idx:
                break
            
            for neighbor in roadmap[current]:
                if neighbor in unvisited:
                    distance = distances[current] + samples[current].distance_to(samples[neighbor])
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        previous[neighbor] = current
        
        # Reconstruct path
        if goal_idx not in previous and goal_idx != start_idx:
            return []
        
        path = []
        current = goal_idx
        while current in previous:
            path.append(samples[current])
            current = previous[current]
        path.append(start)
        path.reverse()
        
        return path
    
    async def _generate_trajectory(self, waypoints: List[Point], max_velocity: float = 1.0, max_acceleration: float = 2.0) -> List[TrajectoryPoint]:
        """Generate smooth trajectory from waypoints"""
        if len(waypoints) < 2:
            return []
        
        trajectory = []
        current_time = 0.0
        current_velocity = Point(0, 0, 0)
        
        for i in range(len(waypoints)):
            point = waypoints[i]
            
            if i == 0:
                # Start point
                trajectory.append(TrajectoryPoint(
                    position=point,
                    velocity=Point(0, 0, 0),
                    acceleration=Point(0, 0, 0),
                    timestamp=current_time
                ))
            else:
                # Calculate desired velocity direction
                direction = waypoints[i] - waypoints[i-1]
                distance = waypoints[i-1].distance_to(waypoints[i])
                
                if distance > 0:
                    direction = direction * (1.0 / distance)
                    
                    # Simple velocity profile (trapezoidal)
                    desired_velocity = direction * max_velocity
                    
                    # Time to reach this waypoint (simplified)
                    segment_time = distance / max_velocity
                    current_time += segment_time
                    
                    trajectory.append(TrajectoryPoint(
                        position=point,
                        velocity=desired_velocity,
                        acceleration=Point(0, 0, 0),  # Simplified
                        timestamp=current_time
                    ))
        
        # Set final velocity to zero
        if trajectory:
            trajectory[-1].velocity = Point(0, 0, 0)
        
        return trajectory

class CollisionChecker:
    """Advanced collision detection for robot motion planning"""
    
    def __init__(self, robot_radius: float = 0.3):
        self.robot_radius = robot_radius
    
    def check_robot_collision(self, robot_pose: Point, obstacles: List[Obstacle]) -> bool:
        """Check if robot collides with obstacles"""
        for obstacle in obstacles:
            if self._robot_obstacle_collision(robot_pose, obstacle):
                return True
        return False
    
    def _robot_obstacle_collision(self, robot_pose: Point, obstacle: Obstacle) -> bool:
        """Check collision between circular robot and obstacle"""
        if obstacle.obstacle_type == ObstacleType.CIRCLE:
            distance = robot_pose.distance_to(obstacle.position)
            return distance <= (self.robot_radius + obstacle.dimensions['radius'])
        
        elif obstacle.obstacle_type == ObstacleType.RECTANGLE:
            # Distance from point to rectangle
            dx = max(0, abs(robot_pose.x - obstacle.position.x) - obstacle.dimensions['width']/2)
            dy = max(0, abs(robot_pose.y - obstacle.position.y) - obstacle.dimensions['height']/2)
            distance = math.sqrt(dx**2 + dy**2)
            return distance <= self.robot_radius
        
        return False

if __name__ == "__main__":
    print("Motion Planning Simulation")
    print("=" * 50)
    
    async def demo():
        # Create environment
        env = EnvironmentMap((-5, -5, 5, 5), resolution=0.1)
        
        # Add obstacles
        obstacles = [
            Obstacle(ObstacleType.CIRCLE, Point(0, 0), {'radius': 0.8}),
            Obstacle(ObstacleType.RECTANGLE, Point(2, 2), {'width': 1.0, 'height': 1.5}),
            Obstacle(ObstacleType.CIRCLE, Point(-2, 1), {'radius': 0.6}),
            Obstacle(ObstacleType.RECTANGLE, Point(1, -2), {'width': 0.8, 'height': 1.2})
        ]
        
        for obstacle in obstacles:
            env.add_obstacle(obstacle)
        
        print(f"Environment created with {len(obstacles)} obstacles")
        
        # Test different planners
        planners = [
            PlannerType.RRT,
            PlannerType.RRT_STAR,
            PlannerType.A_STAR,
            PlannerType.PRM
        ]
        
        start = Point(-4, -4)
        goal = Point(4, 4)
        
        print(f"Planning from {start.x:.1f}, {start.y:.1f} to {goal.x:.1f}, {goal.y:.1f}")
        
        for planner_type in planners:
            planner = MotionPlanner(env, planner_type)
            
            print(f"\n--- {planner_type.value.upper()} Planner ---")
            
            plan = await planner.plan_path(start, goal)
            
            if plan.success:
                print(f"✓ Path found!")
                print(f"  Waypoints: {len(plan.waypoints)}")
                print(f"  Distance: {plan.total_distance:.2f}")
                print(f"  Time: {plan.total_time:.2f}s")
                print(f"  Planning time: {plan.planning_time:.3f}s")
                print(f"  Trajectory points: {len(plan.trajectory)}")
                
                # Show some waypoints
                print("  Key waypoints:")
                step = max(1, len(plan.waypoints) // 5)
                for i in range(0, len(plan.waypoints), step):
                    wp = plan.waypoints[i]
                    print(f"    [{i}] ({wp.x:.2f}, {wp.y:.2f})")
            else:
                print(f"✗ Planning failed: {plan.metadata.get('error', 'Unknown error')}")
        
        print("\nMotion planning demo completed")
    
    asyncio.run(demo())