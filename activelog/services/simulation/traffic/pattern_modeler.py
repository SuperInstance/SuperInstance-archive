"""
ActiveLog Simulation Engine - Traffic Pattern Modeling

This module provides comprehensive traffic pattern simulation and modeling including:
- Real-time traffic flow analysis and prediction
- Route optimization and congestion modeling
- Multi-modal transportation simulation
- Incident impact assessment and response planning
- Urban traffic planning and infrastructure optimization
- Emergency vehicle routing and priority systems
- Parking availability and demand forecasting
- Public transit integration and optimization
"""

import asyncio
import json
import logging
import math
import random
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import numpy as np
from scipy.spatial.distance import euclidean
from sklearn.cluster import DBSCAN
from sklearn.linear_model import LinearRegression
import networkx as nx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VehicleType(Enum):
    """Types of vehicles in traffic simulation"""
    CAR = "car"
    TRUCK = "truck"
    BUS = "bus"
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    PEDESTRIAN = "pedestrian"
    EMERGENCY = "emergency"
    PUBLIC_TRANSIT = "public_transit"


class RoadType(Enum):
    """Types of roads and transportation infrastructure"""
    HIGHWAY = "highway"
    ARTERIAL = "arterial"
    COLLECTOR = "collector"
    LOCAL = "local"
    RESIDENTIAL = "residential"
    PARKING = "parking"
    BUS_LANE = "bus_lane"
    BIKE_LANE = "bike_lane"
    SIDEWALK = "sidewalk"


class TrafficCondition(Enum):
    """Traffic flow conditions"""
    FREE_FLOW = "free_flow"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    CONGESTED = "congested"
    GRIDLOCK = "gridlock"


class IncidentType(Enum):
    """Types of traffic incidents"""
    ACCIDENT = "accident"
    BREAKDOWN = "breakdown"
    CONSTRUCTION = "construction"
    WEATHER = "weather"
    EVENT = "event"
    ROAD_CLOSURE = "road_closure"
    SIGNAL_OUTAGE = "signal_outage"


class WeatherCondition(Enum):
    """Weather conditions affecting traffic"""
    CLEAR = "clear"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"
    ICE = "ice"
    WIND = "wind"
    STORM = "storm"


@dataclass
class Coordinate:
    """Geographic coordinate"""
    lat: float
    lon: float
    
    def distance_to(self, other: 'Coordinate') -> float:
        """Calculate distance in meters"""
        # Haversine formula for great circle distance
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(self.lat)
        lat2_rad = math.radians(other.lat)
        delta_lat = math.radians(other.lat - self.lat)
        delta_lon = math.radians(other.lon - self.lon)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


@dataclass
class RoadSegment:
    """Represents a segment of road infrastructure"""
    segment_id: str
    name: str
    road_type: RoadType
    start_coord: Coordinate
    end_coord: Coordinate
    length: float  # meters
    lanes: int
    speed_limit: float  # km/h
    capacity: int  # vehicles per hour per lane
    current_volume: int = 0
    current_speed: float = 0.0
    incidents: List[str] = field(default_factory=list)  # incident IDs
    traffic_lights: int = 0
    construction_zones: List[Tuple[float, float]] = field(default_factory=list)  # (start_km, end_km)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Vehicle:
    """Represents a vehicle in the traffic simulation"""
    vehicle_id: str
    vehicle_type: VehicleType
    current_position: Coordinate
    destination: Coordinate
    current_segment: Optional[str] = None
    current_speed: float = 0.0
    desired_speed: float = 50.0  # km/h
    route: List[str] = field(default_factory=list)  # segment IDs
    travel_time_start: datetime = field(default_factory=datetime.now)
    total_distance: float = 0.0
    fuel_consumption: float = 0.0
    emissions: float = 0.0
    priority: int = 1  # 1-5, where 5 is highest (emergency vehicles)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrafficIncident:
    """Represents a traffic incident"""
    incident_id: str
    incident_type: IncidentType
    location: Coordinate
    affected_segments: List[str]
    severity: int  # 1-5
    start_time: datetime
    estimated_duration: float  # minutes
    capacity_reduction: float  # 0-1 (percentage reduction)
    speed_reduction: float  # 0-1 (percentage reduction)
    description: str
    response_units: List[str] = field(default_factory=list)
    cleared: bool = False
    cleared_time: Optional[datetime] = None


@dataclass
class TrafficSignal:
    """Traffic signal/intersection control"""
    signal_id: str
    location: Coordinate
    controlled_segments: List[str]
    cycle_time: float  # seconds
    green_times: Dict[str, float]  # segment_id -> green time
    current_phase: int = 0
    last_change: datetime = field(default_factory=datetime.now)
    adaptive: bool = False
    queue_sensors: Dict[str, int] = field(default_factory=dict)  # segment_id -> queue length


@dataclass
class ParkingArea:
    """Parking facility or area"""
    parking_id: str
    name: str
    location: Coordinate
    total_spaces: int
    occupied_spaces: int = 0
    hourly_rate: float = 0.0
    vehicle_types: Set[VehicleType] = field(default_factory=lambda: {VehicleType.CAR})
    access_segments: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PublicTransitRoute:
    """Public transportation route"""
    route_id: str
    name: str
    vehicle_type: VehicleType
    stops: List[Coordinate]
    schedule: List[datetime]  # departure times
    capacity: int
    current_vehicles: List[str] = field(default_factory=list)  # vehicle IDs
    frequency: float = 30.0  # minutes between vehicles
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrafficPattern:
    """Traffic flow pattern analysis"""
    pattern_id: str
    area_bounds: Tuple[Coordinate, Coordinate]  # (southwest, northeast)
    time_period: str  # "morning_rush", "evening_rush", "midday", etc.
    day_type: str  # "weekday", "weekend", "holiday"
    average_volume: Dict[str, float]  # segment_id -> vehicles per hour
    average_speed: Dict[str, float]  # segment_id -> km/h
    congestion_hotspots: List[Tuple[str, float]]  # (segment_id, congestion_level)
    travel_times: Dict[Tuple[str, str], float]  # (origin, destination) -> minutes
    route_preferences: Dict[str, List[str]]  # destination -> preferred route segments
    seasonal_factors: Dict[str, float] = field(default_factory=dict)  # month -> multiplier
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class TrafficSimulationState:
    """Current state of traffic simulation"""
    simulation_id: str
    current_time: datetime
    vehicles: Dict[str, Vehicle]
    segments: Dict[str, RoadSegment]
    incidents: Dict[str, TrafficIncident]
    signals: Dict[str, TrafficSignal]
    parking_areas: Dict[str, ParkingArea]
    transit_routes: Dict[str, PublicTransitRoute]
    weather_condition: WeatherCondition = WeatherCondition.CLEAR
    visibility: float = 100.0  # percentage
    temperature: float = 20.0  # Celsius
    precipitation: float = 0.0  # mm/h
    total_vehicles: int = 0
    average_speed: float = 0.0
    total_travel_time: float = 0.0
    emissions_total: float = 0.0


@dataclass
class TrafficAnalytics:
    """Traffic analytics and metrics"""
    analytics_id: str
    simulation_id: str
    time_range: Tuple[datetime, datetime]
    total_vehicles: int
    completed_trips: int
    average_travel_time: float
    average_speed: float
    fuel_consumption: float
    emissions: float
    incident_count: int
    congestion_index: float  # 0-1
    level_of_service: Dict[str, str]  # segment_id -> A/B/C/D/E/F
    bottleneck_segments: List[Tuple[str, float]]  # (segment_id, severity)
    efficiency_metrics: Dict[str, float]
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


class TrafficSimulator(ABC):
    """Abstract base for traffic simulation engines"""
    
    @abstractmethod
    async def simulate_step(self, state: TrafficSimulationState, time_step: float) -> TrafficSimulationState:
        """Simulate one time step"""
        pass
    
    @abstractmethod
    async def route_vehicle(self, vehicle: Vehicle, segments: Dict[str, RoadSegment]) -> List[str]:
        """Calculate optimal route for vehicle"""
        pass


class TrafficAnalyzer(ABC):
    """Abstract traffic analysis interface"""
    
    @abstractmethod
    async def analyze_patterns(self, historical_data: List[TrafficSimulationState]) -> TrafficPattern:
        """Analyze traffic patterns from historical data"""
        pass
    
    @abstractmethod
    async def predict_congestion(self, current_state: TrafficSimulationState, 
                               forecast_hours: int) -> Dict[str, List[float]]:
        """Predict congestion levels"""
        pass


class IncidentManager(ABC):
    """Abstract incident management interface"""
    
    @abstractmethod
    async def detect_incident(self, state: TrafficSimulationState) -> Optional[TrafficIncident]:
        """Detect potential incidents from traffic data"""
        pass
    
    @abstractmethod
    async def plan_response(self, incident: TrafficIncident, state: TrafficSimulationState) -> Dict[str, Any]:
        """Plan response to traffic incident"""
        pass


class MicroscopicTrafficSimulator(TrafficSimulator):
    """Microscopic traffic simulation (individual vehicle behavior)"""
    
    def __init__(self):
        self.following_distance = 2.0  # seconds
        self.reaction_time = 1.5  # seconds
        self.comfort_deceleration = 2.0  # m/s²
        self.max_acceleration = 3.0  # m/s²
        
    async def simulate_step(self, state: TrafficSimulationState, time_step: float) -> TrafficSimulationState:
        """Simulate one time step using microscopic model"""
        try:
            # Update vehicle positions and speeds
            for vehicle in state.vehicles.values():
                await self._update_vehicle(vehicle, state, time_step)
            
            # Update traffic signals
            for signal in state.signals.values():
                await self._update_signal(signal, state, time_step)
            
            # Process incidents
            await self._process_incidents(state, time_step)
            
            # Update segment conditions
            await self._update_segment_conditions(state)
            
            # Generate new vehicles if needed
            await self._generate_vehicles(state, time_step)
            
            # Remove completed vehicles
            await self._remove_completed_vehicles(state)
            
            # Update simulation statistics
            state.current_time += timedelta(seconds=time_step)
            await self._update_statistics(state)
            
            return state
            
        except Exception as e:
            logger.error(f"Error in traffic simulation step: {e}")
            return state
    
    async def route_vehicle(self, vehicle: Vehicle, segments: Dict[str, RoadSegment]) -> List[str]:
        """Calculate optimal route using A* algorithm"""
        try:
            # Build graph from segments
            graph = nx.DiGraph()
            
            for segment in segments.values():
                # Add edge with travel time as weight
                travel_time = await self._calculate_travel_time(segment)
                graph.add_edge(
                    f"{segment.start_coord.lat},{segment.start_coord.lon}",
                    f"{segment.end_coord.lat},{segment.end_coord.lon}",
                    weight=travel_time,
                    segment_id=segment.segment_id
                )
            
            # Find closest segments to current position and destination
            start_node = await self._find_closest_node(vehicle.current_position, segments)
            end_node = await self._find_closest_node(vehicle.destination, segments)
            
            if start_node and end_node and nx.has_path(graph, start_node, end_node):
                # Calculate shortest path
                path_nodes = nx.shortest_path(graph, start_node, end_node, weight='weight')
                
                # Extract segment IDs
                route = []
                for i in range(len(path_nodes) - 1):
                    edge_data = graph[path_nodes[i]][path_nodes[i + 1]]
                    route.append(edge_data['segment_id'])
                
                return route
            
            return []
            
        except Exception as e:
            logger.error(f"Error calculating route: {e}")
            return []
    
    async def _update_vehicle(self, vehicle: Vehicle, state: TrafficSimulationState, time_step: float):
        """Update individual vehicle state"""
        try:
            if not vehicle.route:
                # Calculate new route if needed
                vehicle.route = await self.route_vehicle(vehicle, state.segments)
            
            if vehicle.route and vehicle.current_segment:
                current_segment = state.segments.get(vehicle.current_segment)
                if current_segment:
                    # Car following model (Intelligent Driver Model)
                    await self._apply_car_following(vehicle, current_segment, state, time_step)
                    
                    # Lane changing model
                    await self._apply_lane_changing(vehicle, current_segment, state, time_step)
                    
                    # Move vehicle
                    await self._move_vehicle(vehicle, current_segment, state, time_step)
                    
                    # Check if reached end of segment
                    if await self._reached_segment_end(vehicle, current_segment):
                        await self._advance_to_next_segment(vehicle, state)
                    
        except Exception as e:
            logger.error(f"Error updating vehicle {vehicle.vehicle_id}: {e}")
    
    async def _apply_car_following(self, vehicle: Vehicle, segment: RoadSegment, 
                                 state: TrafficSimulationState, time_step: float):
        """Apply car following behavior (IDM)"""
        try:
            # Find leading vehicle
            leading_vehicle = await self._find_leading_vehicle(vehicle, segment, state)
            
            if leading_vehicle:
                # Calculate desired spacing
                gap = await self._calculate_gap(vehicle, leading_vehicle)
                desired_spacing = (self.following_distance * vehicle.current_speed / 3.6 + 
                                 vehicle.current_speed**2 / (2 * math.sqrt(self.max_acceleration * self.comfort_deceleration)))
                
                # IDM acceleration
                speed_factor = (vehicle.current_speed / vehicle.desired_speed)**4
                spacing_factor = (desired_spacing / max(gap, 1.0))**2
                
                acceleration = self.max_acceleration * (1 - speed_factor - spacing_factor)
            else:
                # Free driving
                speed_difference = vehicle.desired_speed - vehicle.current_speed
                acceleration = self.max_acceleration * (speed_difference / vehicle.desired_speed)
            
            # Apply acceleration limits
            acceleration = max(-self.comfort_deceleration, min(self.max_acceleration, acceleration))
            
            # Update speed
            new_speed = max(0, vehicle.current_speed + acceleration * time_step / 3.6)
            vehicle.current_speed = min(new_speed, segment.speed_limit * 0.9)  # Respect speed limit
            
        except Exception as e:
            logger.error(f"Error in car following model: {e}")
    
    async def _apply_lane_changing(self, vehicle: Vehicle, segment: RoadSegment, 
                                 state: TrafficSimulationState, time_step: float):
        """Apply lane changing logic"""
        try:
            if segment.lanes <= 1:
                return
            
            # Simple lane changing: change if significantly faster lane available
            current_speed = vehicle.current_speed
            
            # Check adjacent lanes (simplified)
            if current_speed < vehicle.desired_speed * 0.7:
                # Consider lane change if going slow
                if random.random() < 0.1:  # 10% chance per time step
                    # Simplified lane change
                    logger.debug(f"Vehicle {vehicle.vehicle_id} considering lane change")
            
        except Exception as e:
            logger.error(f"Error in lane changing model: {e}")
    
    async def _move_vehicle(self, vehicle: Vehicle, segment: RoadSegment, 
                          state: TrafficSimulationState, time_step: float):
        """Move vehicle along segment"""
        try:
            # Calculate distance traveled
            distance_m = vehicle.current_speed / 3.6 * time_step
            vehicle.total_distance += distance_m
            
            # Update fuel consumption and emissions (simplified)
            fuel_rate = 0.1 + (vehicle.current_speed / 100)**2  # L/km
            vehicle.fuel_consumption += (distance_m / 1000) * fuel_rate
            vehicle.emissions += (distance_m / 1000) * fuel_rate * 2.3  # kg CO2
            
            # Update position along segment (simplified)
            # In a full implementation, would interpolate along segment geometry
            
        except Exception as e:
            logger.error(f"Error moving vehicle: {e}")
    
    async def _find_leading_vehicle(self, vehicle: Vehicle, segment: RoadSegment, 
                                  state: TrafficSimulationState) -> Optional[Vehicle]:
        """Find the vehicle immediately ahead"""
        try:
            # Simplified: find vehicles on same segment ahead of current vehicle
            candidates = []
            
            for other_vehicle in state.vehicles.values():
                if (other_vehicle.vehicle_id != vehicle.vehicle_id and 
                    other_vehicle.current_segment == vehicle.current_segment):
                    # In real implementation, would check actual positions along segment
                    candidates.append(other_vehicle)
            
            # Return closest vehicle ahead (simplified)
            return candidates[0] if candidates else None
            
        except Exception as e:
            logger.error(f"Error finding leading vehicle: {e}")
            return None
    
    async def _calculate_gap(self, vehicle: Vehicle, leading_vehicle: Vehicle) -> float:
        """Calculate gap to leading vehicle"""
        try:
            # Simplified gap calculation
            # In real implementation, would use actual positions
            base_gap = 20.0  # meters
            speed_factor = vehicle.current_speed / 3.6 * self.following_distance
            return base_gap + speed_factor
            
        except Exception as e:
            logger.error(f"Error calculating gap: {e}")
            return 50.0
    
    async def _update_signal(self, signal: TrafficSignal, state: TrafficSimulationState, time_step: float):
        """Update traffic signal state"""
        try:
            time_since_change = (datetime.now() - signal.last_change).total_seconds()
            
            if signal.adaptive:
                # Adaptive signal control
                await self._adaptive_signal_control(signal, state)
            else:
                # Fixed-time control
                if time_since_change >= signal.cycle_time:
                    signal.current_phase = (signal.current_phase + 1) % len(signal.controlled_segments)
                    signal.last_change = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating signal: {e}")
    
    async def _adaptive_signal_control(self, signal: TrafficSignal, state: TrafficSimulationState):
        """Implement adaptive signal control"""
        try:
            # Count vehicles waiting at each approach
            approach_counts = {}
            
            for segment_id in signal.controlled_segments:
                segment = state.segments.get(segment_id)
                if segment:
                    # Count vehicles on approach
                    waiting_vehicles = len([v for v in state.vehicles.values() 
                                          if v.current_segment == segment_id and v.current_speed < 5.0])
                    approach_counts[segment_id] = waiting_vehicles
            
            # Adjust green times based on demand
            if approach_counts:
                max_count_segment = max(approach_counts.items(), key=lambda x: x[1])
                if max_count_segment[1] > 5:  # If more than 5 vehicles waiting
                    # Give more green time to this approach
                    signal.green_times[max_count_segment[0]] = min(60.0, signal.green_times.get(max_count_segment[0], 30.0) + 10.0)
            
        except Exception as e:
            logger.error(f"Error in adaptive signal control: {e}")
    
    async def _process_incidents(self, state: TrafficSimulationState, time_step: float):
        """Process active incidents and their effects"""
        try:
            current_time = datetime.now()
            
            for incident in list(state.incidents.values()):
                if not incident.cleared:
                    # Check if incident should be cleared
                    elapsed_time = (current_time - incident.start_time).total_seconds() / 60
                    
                    if elapsed_time >= incident.estimated_duration:
                        incident.cleared = True
                        incident.cleared_time = current_time
                        
                        # Restore segment capacity
                        for segment_id in incident.affected_segments:
                            segment = state.segments.get(segment_id)
                            if segment:
                                segment.incidents.remove(incident.incident_id)
                    
                    else:
                        # Apply incident effects
                        await self._apply_incident_effects(incident, state)
                
        except Exception as e:
            logger.error(f"Error processing incidents: {e}")
    
    async def _apply_incident_effects(self, incident: TrafficIncident, state: TrafficSimulationState):
        """Apply effects of incident on traffic"""
        try:
            for segment_id in incident.affected_segments:
                segment = state.segments.get(segment_id)
                if segment:
                    # Reduce effective capacity and speed
                    effective_capacity = segment.capacity * segment.lanes * (1 - incident.capacity_reduction)
                    effective_speed = segment.speed_limit * (1 - incident.speed_reduction)
                    
                    # Update segment attributes
                    segment.attributes['effective_capacity'] = effective_capacity
                    segment.attributes['effective_speed'] = effective_speed
                    
        except Exception as e:
            logger.error(f"Error applying incident effects: {e}")
    
    async def _update_segment_conditions(self, state: TrafficSimulationState):
        """Update traffic conditions for all segments"""
        try:
            for segment in state.segments.values():
                # Count vehicles on segment
                vehicles_on_segment = len([v for v in state.vehicles.values() 
                                         if v.current_segment == segment.segment_id])
                
                segment.current_volume = vehicles_on_segment
                
                # Calculate average speed on segment
                speeds = [v.current_speed for v in state.vehicles.values() 
                         if v.current_segment == segment.segment_id]
                segment.current_speed = statistics.mean(speeds) if speeds else segment.speed_limit
                
                # Determine traffic condition
                density = vehicles_on_segment / max(segment.length / 1000, 0.1)  # vehicles per km
                
                if density < 10:
                    condition = TrafficCondition.FREE_FLOW
                elif density < 20:
                    condition = TrafficCondition.LIGHT
                elif density < 40:
                    condition = TrafficCondition.MODERATE
                elif density < 60:
                    condition = TrafficCondition.HEAVY
                else:
                    condition = TrafficCondition.CONGESTED
                
                segment.attributes['traffic_condition'] = condition
                
        except Exception as e:
            logger.error(f"Error updating segment conditions: {e}")
    
    async def _generate_vehicles(self, state: TrafficSimulationState, time_step: float):
        """Generate new vehicles entering the network"""
        try:
            # Simple vehicle generation based on demand patterns
            generation_rate = await self._get_vehicle_generation_rate(state)
            
            if random.random() < generation_rate * time_step / 3600:  # Convert hourly rate to probability
                # Find entry points (segments with no incoming connections)
                entry_segments = await self._find_entry_segments(state.segments)
                
                if entry_segments:
                    entry_segment = random.choice(entry_segments)
                    destination = await self._generate_destination(state)
                    
                    # Create new vehicle
                    new_vehicle = Vehicle(
                        vehicle_id=str(uuid4()),
                        vehicle_type=random.choice(list(VehicleType)),
                        current_position=entry_segment.start_coord,
                        destination=destination,
                        current_segment=entry_segment.segment_id,
                        desired_speed=random.uniform(0.8, 1.2) * entry_segment.speed_limit
                    )
                    
                    state.vehicles[new_vehicle.vehicle_id] = new_vehicle
                    state.total_vehicles += 1
            
        except Exception as e:
            logger.error(f"Error generating vehicles: {e}")
    
    async def _remove_completed_vehicles(self, state: TrafficSimulationState):
        """Remove vehicles that have reached their destinations"""
        try:
            completed_vehicles = []
            
            for vehicle in state.vehicles.values():
                # Check if vehicle has reached destination
                if (vehicle.current_position.distance_to(vehicle.destination) < 100):  # Within 100m
                    completed_vehicles.append(vehicle.vehicle_id)
            
            # Remove completed vehicles
            for vehicle_id in completed_vehicles:
                del state.vehicles[vehicle_id]
                
        except Exception as e:
            logger.error(f"Error removing completed vehicles: {e}")
    
    async def _update_statistics(self, state: TrafficSimulationState):
        """Update simulation statistics"""
        try:
            if state.vehicles:
                # Average speed across all vehicles
                speeds = [v.current_speed for v in state.vehicles.values()]
                state.average_speed = statistics.mean(speeds)
                
                # Total travel time
                travel_times = [(datetime.now() - v.travel_time_start).total_seconds() / 3600 
                               for v in state.vehicles.values()]
                state.total_travel_time = sum(travel_times)
                
                # Total emissions
                state.emissions_total = sum(v.emissions for v in state.vehicles.values())
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    # Helper methods
    
    async def _calculate_travel_time(self, segment: RoadSegment) -> float:
        """Calculate travel time for segment in minutes"""
        try:
            # Base travel time at speed limit
            base_time = (segment.length / 1000) / segment.speed_limit * 60
            
            # Apply congestion factor
            congestion_factor = segment.attributes.get('congestion_factor', 1.0)
            
            # Apply incident effects
            incident_factor = 1.0
            if segment.incidents:
                incident_factor = 2.0  # Double travel time if incident
            
            return base_time * congestion_factor * incident_factor
            
        except Exception as e:
            logger.error(f"Error calculating travel time: {e}")
            return 60.0  # Default 1 hour
    
    async def _find_closest_node(self, position: Coordinate, segments: Dict[str, RoadSegment]) -> Optional[str]:
        """Find closest network node to position"""
        try:
            closest_distance = float('inf')
            closest_node = None
            
            for segment in segments.values():
                # Check distance to start and end coordinates
                start_distance = position.distance_to(segment.start_coord)
                end_distance = position.distance_to(segment.end_coord)
                
                if start_distance < closest_distance:
                    closest_distance = start_distance
                    closest_node = f"{segment.start_coord.lat},{segment.start_coord.lon}"
                
                if end_distance < closest_distance:
                    closest_distance = end_distance
                    closest_node = f"{segment.end_coord.lat},{segment.end_coord.lon}"
            
            return closest_node
            
        except Exception as e:
            logger.error(f"Error finding closest node: {e}")
            return None
    
    async def _get_vehicle_generation_rate(self, state: TrafficSimulationState) -> float:
        """Get vehicle generation rate based on time and conditions"""
        try:
            current_hour = state.current_time.hour
            
            # Basic demand pattern
            if 7 <= current_hour <= 9:  # Morning rush
                return 500.0  # vehicles per hour
            elif 17 <= current_hour <= 19:  # Evening rush
                return 450.0
            elif 10 <= current_hour <= 16:  # Midday
                return 200.0
            elif 20 <= current_hour <= 23:  # Evening
                return 150.0
            else:  # Night
                return 50.0
                
        except Exception as e:
            logger.error(f"Error getting generation rate: {e}")
            return 100.0
    
    async def _find_entry_segments(self, segments: Dict[str, RoadSegment]) -> List[RoadSegment]:
        """Find segments that serve as entry points to the network"""
        try:
            # Simplified: return highway segments as entry points
            entry_segments = [s for s in segments.values() if s.road_type == RoadType.HIGHWAY]
            return entry_segments
            
        except Exception as e:
            logger.error(f"Error finding entry segments: {e}")
            return []
    
    async def _generate_destination(self, state: TrafficSimulationState) -> Coordinate:
        """Generate random destination coordinate"""
        try:
            # Generate destination within simulation area
            # Simplified: random coordinate near existing segments
            segments = list(state.segments.values())
            if segments:
                random_segment = random.choice(segments)
                # Add some randomness around segment end
                lat_offset = random.uniform(-0.01, 0.01)
                lon_offset = random.uniform(-0.01, 0.01)
                return Coordinate(
                    random_segment.end_coord.lat + lat_offset,
                    random_segment.end_coord.lon + lon_offset
                )
            
            return Coordinate(0.0, 0.0)  # Default
            
        except Exception as e:
            logger.error(f"Error generating destination: {e}")
            return Coordinate(0.0, 0.0)
    
    async def _reached_segment_end(self, vehicle: Vehicle, segment: RoadSegment) -> bool:
        """Check if vehicle has reached end of current segment"""
        # Simplified: random chance of reaching end
        return random.random() < 0.1
    
    async def _advance_to_next_segment(self, vehicle: Vehicle, state: TrafficSimulationState):
        """Advance vehicle to next segment in route"""
        try:
            if vehicle.route:
                current_index = vehicle.route.index(vehicle.current_segment) if vehicle.current_segment in vehicle.route else -1
                
                if current_index >= 0 and current_index < len(vehicle.route) - 1:
                    # Move to next segment
                    vehicle.current_segment = vehicle.route[current_index + 1]
                    next_segment = state.segments.get(vehicle.current_segment)
                    if next_segment:
                        vehicle.current_position = next_segment.start_coord
                else:
                    # Remove from route if at end
                    vehicle.route = []
                    vehicle.current_segment = None
                    
        except Exception as e:
            logger.error(f"Error advancing to next segment: {e}")


class IntelligentTrafficAnalyzer(TrafficAnalyzer):
    """Advanced traffic analysis using machine learning and statistics"""
    
    def __init__(self):
        self.pattern_models = {}
        self.congestion_predictors = {}
        
    async def analyze_patterns(self, historical_data: List[TrafficSimulationState]) -> TrafficPattern:
        """Analyze traffic patterns from historical data"""
        try:
            if not historical_data:
                return TrafficPattern(
                    pattern_id=str(uuid4()),
                    area_bounds=(Coordinate(0, 0), Coordinate(0, 0)),
                    time_period="unknown",
                    day_type="unknown",
                    average_volume={},
                    average_speed={},
                    congestion_hotspots=[],
                    travel_times={},
                    route_preferences={}
                )
            
            # Determine time period and day type
            first_state = historical_data[0]
            time_period = await self._classify_time_period(first_state.current_time)
            day_type = await self._classify_day_type(first_state.current_time)
            
            # Calculate average volumes and speeds by segment
            segment_volumes = {}
            segment_speeds = {}
            
            for state in historical_data:
                for segment_id, segment in state.segments.items():
                    if segment_id not in segment_volumes:
                        segment_volumes[segment_id] = []
                        segment_speeds[segment_id] = []
                    
                    segment_volumes[segment_id].append(segment.current_volume)
                    segment_speeds[segment_id].append(segment.current_speed)
            
            # Calculate averages
            avg_volumes = {sid: statistics.mean(volumes) for sid, volumes in segment_volumes.items()}
            avg_speeds = {sid: statistics.mean(speeds) for sid, speeds in segment_speeds.items()}
            
            # Identify congestion hotspots
            hotspots = []
            for segment_id, speeds in segment_speeds.items():
                avg_speed = statistics.mean(speeds)
                segment = first_state.segments.get(segment_id)
                if segment and avg_speed < segment.speed_limit * 0.5:  # Less than 50% of speed limit
                    congestion_level = 1.0 - (avg_speed / segment.speed_limit)
                    hotspots.append((segment_id, congestion_level))
            
            # Sort hotspots by congestion level
            hotspots.sort(key=lambda x: x[1], reverse=True)
            
            # Calculate area bounds
            all_segments = list(first_state.segments.values())
            if all_segments:
                lats = [s.start_coord.lat for s in all_segments] + [s.end_coord.lat for s in all_segments]
                lons = [s.start_coord.lon for s in all_segments] + [s.end_coord.lon for s in all_segments]
                
                area_bounds = (
                    Coordinate(min(lats), min(lons)),
                    Coordinate(max(lats), max(lons))
                )
            else:
                area_bounds = (Coordinate(0, 0), Coordinate(0, 0))
            
            return TrafficPattern(
                pattern_id=str(uuid4()),
                area_bounds=area_bounds,
                time_period=time_period,
                day_type=day_type,
                average_volume=avg_volumes,
                average_speed=avg_speeds,
                congestion_hotspots=hotspots,
                travel_times={},  # Would calculate from vehicle data
                route_preferences={}  # Would analyze from vehicle routes
            )
            
        except Exception as e:
            logger.error(f"Error analyzing traffic patterns: {e}")
            return TrafficPattern(
                pattern_id=str(uuid4()),
                area_bounds=(Coordinate(0, 0), Coordinate(0, 0)),
                time_period="unknown",
                day_type="unknown",
                average_volume={},
                average_speed={},
                congestion_hotspots=[],
                travel_times={},
                route_preferences={}
            )
    
    async def predict_congestion(self, current_state: TrafficSimulationState, 
                               forecast_hours: int) -> Dict[str, List[float]]:
        """Predict congestion levels for next few hours"""
        try:
            predictions = {}
            
            for segment_id, segment in current_state.segments.items():
                # Simple prediction based on current conditions and time patterns
                hourly_predictions = []
                
                current_hour = current_state.current_time.hour
                current_congestion = await self._calculate_congestion_level(segment)
                
                for hour_offset in range(forecast_hours):
                    future_hour = (current_hour + hour_offset) % 24
                    
                    # Apply time-based patterns
                    time_factor = await self._get_time_congestion_factor(future_hour)
                    
                    # Apply trend (simplified)
                    trend_factor = 1.0 + (hour_offset * 0.05)  # Slight increase over time
                    
                    predicted_congestion = min(1.0, current_congestion * time_factor * trend_factor)
                    hourly_predictions.append(predicted_congestion)
                
                predictions[segment_id] = hourly_predictions
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting congestion: {e}")
            return {}
    
    async def _classify_time_period(self, timestamp: datetime) -> str:
        """Classify time period"""
        hour = timestamp.hour
        
        if 6 <= hour < 10:
            return "morning_rush"
        elif 10 <= hour < 16:
            return "midday"
        elif 16 <= hour < 20:
            return "evening_rush"
        elif 20 <= hour < 24:
            return "evening"
        else:
            return "night"
    
    async def _classify_day_type(self, timestamp: datetime) -> str:
        """Classify day type"""
        weekday = timestamp.weekday()
        
        if weekday < 5:
            return "weekday"
        elif weekday == 5:
            return "saturday"
        else:
            return "sunday"
    
    async def _calculate_congestion_level(self, segment: RoadSegment) -> float:
        """Calculate congestion level for segment (0-1)"""
        try:
            # Based on speed reduction
            if segment.speed_limit > 0:
                speed_ratio = segment.current_speed / segment.speed_limit
                congestion_level = 1.0 - min(1.0, speed_ratio)
                return max(0.0, congestion_level)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating congestion level: {e}")
            return 0.0
    
    async def _get_time_congestion_factor(self, hour: int) -> float:
        """Get congestion factor based on time of day"""
        # Peak hours have higher congestion
        if hour in [7, 8, 17, 18]:
            return 1.5
        elif hour in [9, 16, 19]:
            return 1.2
        elif 10 <= hour <= 15:
            return 0.8
        elif 20 <= hour <= 6:
            return 0.4
        else:
            return 1.0


class SmartIncidentManager(IncidentManager):
    """Smart incident detection and response management"""
    
    def __init__(self):
        self.incident_threshold = 0.3  # Speed reduction threshold for detection
        self.response_teams = {}
        
    async def detect_incident(self, state: TrafficSimulationState) -> Optional[TrafficIncident]:
        """Detect potential incidents from traffic anomalies"""
        try:
            # Look for sudden speed drops or volume spikes
            for segment_id, segment in state.segments.items():
                # Check for significant speed reduction
                speed_reduction = 1.0 - (segment.current_speed / segment.speed_limit)
                
                if speed_reduction > self.incident_threshold:
                    # Potential incident detected
                    severity = min(5, int(speed_reduction * 5) + 1)
                    
                    # Create incident
                    incident = TrafficIncident(
                        incident_id=str(uuid4()),
                        incident_type=IncidentType.ACCIDENT,  # Default type
                        location=segment.start_coord,
                        affected_segments=[segment_id],
                        severity=severity,
                        start_time=datetime.now(),
                        estimated_duration=severity * 30.0,  # 30 minutes per severity level
                        capacity_reduction=speed_reduction * 0.5,
                        speed_reduction=speed_reduction,
                        description=f"Detected incident on {segment.name}"
                    )
                    
                    logger.warning(f"Incident detected: {incident.description}")
                    return incident
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting incident: {e}")
            return None
    
    async def plan_response(self, incident: TrafficIncident, state: TrafficSimulationState) -> Dict[str, Any]:
        """Plan response to traffic incident"""
        try:
            response_plan = {
                'incident_id': incident.incident_id,
                'response_time': datetime.now(),
                'actions': [],
                'resource_allocation': {},
                'traffic_management': {},
                'estimated_clearance': incident.start_time + timedelta(minutes=incident.estimated_duration)
            }
            
            # Determine required response units
            if incident.incident_type == IncidentType.ACCIDENT:
                response_plan['actions'].extend([
                    'Dispatch emergency medical services',
                    'Send traffic control officers',
                    'Deploy tow trucks if needed',
                    'Set up traffic diversion'
                ])
                
                response_plan['resource_allocation'] = {
                    'ambulance': 1 if incident.severity >= 3 else 0,
                    'police': 1,
                    'tow_truck': 1 if incident.severity >= 2 else 0,
                    'traffic_control': 2
                }
            
            elif incident.incident_type == IncidentType.BREAKDOWN:
                response_plan['actions'].extend([
                    'Deploy assistance vehicle',
                    'Provide traffic warning signs',
                    'Monitor traffic flow'
                ])
                
                response_plan['resource_allocation'] = {
                    'assistance_vehicle': 1,
                    'warning_signs': 4
                }
            
            # Plan traffic management
            affected_segments = incident.affected_segments
            
            for segment_id in affected_segments:
                segment = state.segments.get(segment_id)
                if segment:
                    # Suggest traffic diversions
                    response_plan['traffic_management'][segment_id] = {
                        'lane_closures': min(segment.lanes - 1, incident.severity - 1),
                        'speed_reduction': incident.speed_reduction,
                        'alternative_routes': await self._find_alternative_routes(segment, state),
                        'signal_adjustments': 'extend_green_time_for_diversions'
                    }
            
            # Calculate response priority
            priority = min(5, incident.severity + (len(affected_segments) - 1))
            response_plan['priority'] = priority
            
            return response_plan
            
        except Exception as e:
            logger.error(f"Error planning incident response: {e}")
            return {}
    
    async def _find_alternative_routes(self, affected_segment: RoadSegment, 
                                     state: TrafficSimulationState) -> List[str]:
        """Find alternative routes around incident"""
        try:
            # Simplified alternative route finding
            alternatives = []
            
            # Look for parallel segments
            for segment_id, segment in state.segments.items():
                if segment_id != affected_segment.segment_id:
                    # Check if segments are roughly parallel
                    start_distance = affected_segment.start_coord.distance_to(segment.start_coord)
                    end_distance = affected_segment.end_coord.distance_to(segment.end_coord)
                    
                    if start_distance < 2000 and end_distance < 2000:  # Within 2km
                        alternatives.append(segment_id)
            
            return alternatives[:3]  # Return up to 3 alternatives
            
        except Exception as e:
            logger.error(f"Error finding alternative routes: {e}")
            return []


class TrafficPatternModelingService:
    """Main traffic pattern modeling service"""
    
    def __init__(self,
                 simulator: TrafficSimulator,
                 analyzer: TrafficAnalyzer,
                 incident_manager: IncidentManager):
        self.simulator = simulator
        self.analyzer = analyzer
        self.incident_manager = incident_manager
        
        # Storage
        self.simulation_states: Dict[str, TrafficSimulationState] = {}
        self.patterns: Dict[str, TrafficPattern] = {}
        self.analytics: Dict[str, TrafficAnalytics] = {}
        self.road_network: Dict[str, RoadSegment] = {}
        
        # Simulation control
        self.active_simulations: Dict[str, bool] = {}
        self.simulation_tasks: Dict[str, asyncio.Task] = {}
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def start(self):
        """Start the traffic modeling service"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting Traffic Pattern Modeling Service")
        
        # Start background tasks
        self._background_tasks = [
            asyncio.create_task(self._monitor_real_time_traffic()),
            asyncio.create_task(self._update_traffic_patterns()),
            asyncio.create_task(self._generate_predictions())
        ]
    
    async def stop(self):
        """Stop the traffic modeling service"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping Traffic Pattern Modeling Service")
        
        # Stop active simulations
        for sim_id in list(self.active_simulations.keys()):
            await self.stop_simulation(sim_id)
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
    
    async def create_road_network(self, segments: List[RoadSegment]) -> bool:
        """Create road network from segments"""
        try:
            for segment in segments:
                self.road_network[segment.segment_id] = segment
            
            logger.info(f"Created road network with {len(segments)} segments")
            return True
            
        except Exception as e:
            logger.error(f"Error creating road network: {e}")
            return False
    
    async def start_simulation(self, simulation_id: str, initial_conditions: Dict[str, Any]) -> bool:
        """Start a traffic simulation"""
        try:
            if simulation_id in self.active_simulations:
                logger.warning(f"Simulation {simulation_id} already running")
                return False
            
            # Create initial simulation state
            initial_state = TrafficSimulationState(
                simulation_id=simulation_id,
                current_time=datetime.now(),
                vehicles={},
                segments=dict(self.road_network),
                incidents={},
                signals={},
                parking_areas={},
                transit_routes={},
                weather_condition=initial_conditions.get('weather', WeatherCondition.CLEAR),
                visibility=initial_conditions.get('visibility', 100.0),
                temperature=initial_conditions.get('temperature', 20.0)
            )
            
            # Apply initial conditions
            await self._apply_initial_conditions(initial_state, initial_conditions)
            
            self.simulation_states[simulation_id] = initial_state
            self.active_simulations[simulation_id] = True
            
            # Start simulation task
            task = asyncio.create_task(self._run_simulation(simulation_id))
            self.simulation_tasks[simulation_id] = task
            
            logger.info(f"Started traffic simulation: {simulation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting simulation: {e}")
            return False
    
    async def stop_simulation(self, simulation_id: str) -> bool:
        """Stop a running simulation"""
        try:
            if simulation_id not in self.active_simulations:
                return False
            
            self.active_simulations[simulation_id] = False
            
            # Cancel simulation task
            if simulation_id in self.simulation_tasks:
                task = self.simulation_tasks[simulation_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.simulation_tasks[simulation_id]
            
            logger.info(f"Stopped traffic simulation: {simulation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping simulation: {e}")
            return False
    
    async def get_simulation_state(self, simulation_id: str) -> Optional[TrafficSimulationState]:
        """Get current state of simulation"""
        return self.simulation_states.get(simulation_id)
    
    async def analyze_traffic_patterns(self, area_bounds: Tuple[Coordinate, Coordinate],
                                     time_range: Tuple[datetime, datetime]) -> Optional[TrafficPattern]:
        """Analyze traffic patterns for specified area and time"""
        try:
            # Find relevant historical data
            historical_data = []
            
            for state in self.simulation_states.values():
                if time_range[0] <= state.current_time <= time_range[1]:
                    # Check if state overlaps with area bounds
                    historical_data.append(state)
            
            if not historical_data:
                logger.warning("No historical data found for analysis")
                return None
            
            # Analyze patterns
            pattern = await self.analyzer.analyze_patterns(historical_data)
            
            # Store pattern
            self.patterns[pattern.pattern_id] = pattern
            
            logger.info(f"Analyzed traffic pattern: {pattern.pattern_id}")
            return pattern
            
        except Exception as e:
            logger.error(f"Error analyzing traffic patterns: {e}")
            return None
    
    async def predict_traffic_conditions(self, simulation_id: str, forecast_hours: int = 4) -> Optional[Dict[str, Any]]:
        """Predict future traffic conditions"""
        try:
            state = self.simulation_states.get(simulation_id)
            if not state:
                return None
            
            # Get congestion predictions
            congestion_predictions = await self.analyzer.predict_congestion(state, forecast_hours)
            
            # Generate overall predictions
            predictions = {
                'simulation_id': simulation_id,
                'forecast_start': state.current_time.isoformat(),
                'forecast_hours': forecast_hours,
                'segment_predictions': congestion_predictions,
                'overall_trends': await self._calculate_overall_trends(congestion_predictions),
                'recommendations': await self._generate_traffic_recommendations(state, congestion_predictions)
            }
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting traffic conditions: {e}")
            return None
    
    async def optimize_traffic_signals(self, simulation_id: str) -> Dict[str, Any]:
        """Optimize traffic signal timing"""
        try:
            state = self.simulation_states.get(simulation_id)
            if not state:
                return {}
            
            optimizations = {}
            
            for signal_id, signal in state.signals.items():
                # Analyze current performance
                current_delays = await self._calculate_signal_delays(signal, state)
                
                # Suggest optimizations
                suggested_timings = await self._optimize_signal_timing(signal, state)
                
                optimizations[signal_id] = {
                    'current_delays': current_delays,
                    'suggested_green_times': suggested_timings,
                    'expected_improvement': await self._estimate_signal_improvement(signal, suggested_timings, state)
                }
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Error optimizing traffic signals: {e}")
            return {}
    
    async def simulate_incident_impact(self, simulation_id: str, incident: TrafficIncident) -> Dict[str, Any]:
        """Simulate impact of traffic incident"""
        try:
            state = self.simulation_states.get(simulation_id)
            if not state:
                return {}
            
            # Store original state
            original_conditions = {}
            for segment_id in incident.affected_segments:
                segment = state.segments.get(segment_id)
                if segment:
                    original_conditions[segment_id] = {
                        'speed': segment.current_speed,
                        'volume': segment.current_volume
                    }
            
            # Apply incident
            state.incidents[incident.incident_id] = incident
            
            # Simulate for short period to assess impact
            impact_duration = 30  # minutes
            for _ in range(impact_duration):
                await self.simulator.simulate_step(state, 60.0)  # 1-minute steps
            
            # Analyze impact
            impact_analysis = {
                'incident_id': incident.incident_id,
                'affected_segments': incident.affected_segments,
                'impact_metrics': {},
                'response_plan': await self.incident_manager.plan_response(incident, state)
            }
            
            for segment_id in incident.affected_segments:
                segment = state.segments.get(segment_id)
                if segment and segment_id in original_conditions:
                    original = original_conditions[segment_id]
                    impact_analysis['impact_metrics'][segment_id] = {
                        'speed_reduction': (original['speed'] - segment.current_speed) / original['speed'],
                        'volume_change': segment.current_volume - original['volume'],
                        'delay_increase': await self._calculate_delay_increase(segment, original)
                    }
            
            return impact_analysis
            
        except Exception as e:
            logger.error(f"Error simulating incident impact: {e}")
            return {}
    
    async def get_traffic_analytics(self, simulation_id: str) -> Optional[TrafficAnalytics]:
        """Generate comprehensive traffic analytics"""
        try:
            state = self.simulation_states.get(simulation_id)
            if not state:
                return None
            
            # Calculate metrics
            total_vehicles = len(state.vehicles)
            completed_trips = 0  # Would track from vehicle completion
            
            travel_times = []
            speeds = []
            fuel_consumption = 0.0
            emissions = 0.0
            
            for vehicle in state.vehicles.values():
                travel_time = (datetime.now() - vehicle.travel_time_start).total_seconds() / 3600
                travel_times.append(travel_time)
                speeds.append(vehicle.current_speed)
                fuel_consumption += vehicle.fuel_consumption
                emissions += vehicle.emissions
            
            avg_travel_time = statistics.mean(travel_times) if travel_times else 0.0
            avg_speed = statistics.mean(speeds) if speeds else 0.0
            
            # Calculate congestion index
            congestion_levels = []
            for segment in state.segments.values():
                congestion = 1.0 - (segment.current_speed / segment.speed_limit) if segment.speed_limit > 0 else 0
                congestion_levels.append(max(0, congestion))
            
            congestion_index = statistics.mean(congestion_levels) if congestion_levels else 0.0
            
            # Identify bottlenecks
            bottlenecks = []
            for segment_id, segment in state.segments.items():
                if segment.speed_limit > 0:
                    speed_ratio = segment.current_speed / segment.speed_limit
                    if speed_ratio < 0.5:  # Less than 50% of speed limit
                        severity = 1.0 - speed_ratio
                        bottlenecks.append((segment_id, severity))
            
            bottlenecks.sort(key=lambda x: x[1], reverse=True)
            
            # Level of service calculation
            level_of_service = {}
            for segment_id, segment in state.segments.items():
                if segment.speed_limit > 0:
                    speed_ratio = segment.current_speed / segment.speed_limit
                    if speed_ratio >= 0.9:
                        los = 'A'
                    elif speed_ratio >= 0.7:
                        los = 'B'
                    elif speed_ratio >= 0.5:
                        los = 'C'
                    elif speed_ratio >= 0.3:
                        los = 'D'
                    elif speed_ratio >= 0.15:
                        los = 'E'
                    else:
                        los = 'F'
                    
                    level_of_service[segment_id] = los
            
            analytics = TrafficAnalytics(
                analytics_id=str(uuid4()),
                simulation_id=simulation_id,
                time_range=(state.current_time - timedelta(hours=1), state.current_time),
                total_vehicles=total_vehicles,
                completed_trips=completed_trips,
                average_travel_time=avg_travel_time,
                average_speed=avg_speed,
                fuel_consumption=fuel_consumption,
                emissions=emissions,
                incident_count=len(state.incidents),
                congestion_index=congestion_index,
                level_of_service=level_of_service,
                bottleneck_segments=bottlenecks[:10],  # Top 10 bottlenecks
                efficiency_metrics={
                    'network_efficiency': 1.0 - congestion_index,
                    'throughput_efficiency': avg_speed / 50.0 if avg_speed > 0 else 0,  # Normalized to 50 km/h
                    'environmental_efficiency': 1.0 / (emissions + 1.0)  # Inverse of emissions
                }
            )
            
            # Store analytics
            self.analytics[analytics.analytics_id] = analytics
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error generating traffic analytics: {e}")
            return None
    
    # Background tasks and helper methods
    
    async def _run_simulation(self, simulation_id: str):
        """Main simulation loop"""
        try:
            time_step = 1.0  # 1 second per step
            
            while self.active_simulations.get(simulation_id, False):
                state = self.simulation_states.get(simulation_id)
                if state:
                    # Run simulation step
                    updated_state = await self.simulator.simulate_step(state, time_step)
                    self.simulation_states[simulation_id] = updated_state
                    
                    # Check for incidents
                    detected_incident = await self.incident_manager.detect_incident(updated_state)
                    if detected_incident:
                        updated_state.incidents[detected_incident.incident_id] = detected_incident
                
                await asyncio.sleep(0.1)  # Run at 10x real-time
                
        except asyncio.CancelledError:
            logger.info(f"Simulation {simulation_id} cancelled")
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}")
    
    async def _apply_initial_conditions(self, state: TrafficSimulationState, conditions: Dict[str, Any]):
        """Apply initial conditions to simulation"""
        try:
            # Add initial vehicles if specified
            initial_vehicles = conditions.get('initial_vehicles', [])
            for vehicle_data in initial_vehicles:
                vehicle = Vehicle(**vehicle_data)
                state.vehicles[vehicle.vehicle_id] = vehicle
            
            # Add traffic signals if specified
            signals = conditions.get('signals', [])
            for signal_data in signals:
                signal = TrafficSignal(**signal_data)
                state.signals[signal.signal_id] = signal
            
            # Add incidents if specified
            incidents = conditions.get('incidents', [])
            for incident_data in incidents:
                incident = TrafficIncident(**incident_data)
                state.incidents[incident.incident_id] = incident
                
        except Exception as e:
            logger.error(f"Error applying initial conditions: {e}")
    
    async def _monitor_real_time_traffic(self):
        """Monitor real-time traffic conditions"""
        while self._running:
            try:
                # In real implementation, would connect to traffic sensors, cameras, etc.
                # For simulation, we'll just log current state
                
                active_count = len([s for s in self.active_simulations.values() if s])
                if active_count > 0:
                    logger.info(f"Monitoring {active_count} active traffic simulations")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in real-time monitoring: {e}")
                await asyncio.sleep(300)
    
    async def _update_traffic_patterns(self):
        """Update traffic patterns from recent data"""
        while self._running:
            try:
                # Analyze patterns from recent simulation data
                current_time = datetime.now()
                
                for state in self.simulation_states.values():
                    if (current_time - state.current_time).total_seconds() < 3600:  # Within last hour
                        # Update patterns (simplified)
                        pass
                
                logger.info("Updated traffic patterns")
                
                # Update every hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating traffic patterns: {e}")
                await asyncio.sleep(3600)
    
    async def _generate_predictions(self):
        """Generate traffic predictions"""
        while self._running:
            try:
                # Generate predictions for all active simulations
                for sim_id in self.active_simulations:
                    if self.active_simulations[sim_id]:
                        predictions = await self.predict_traffic_conditions(sim_id)
                        if predictions:
                            logger.info(f"Generated predictions for simulation {sim_id}")
                
                # Generate every 15 minutes
                await asyncio.sleep(900)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error generating predictions: {e}")
                await asyncio.sleep(900)
    
    async def _calculate_overall_trends(self, segment_predictions: Dict[str, List[float]]) -> Dict[str, str]:
        """Calculate overall traffic trends"""
        try:
            trends = {}
            
            for segment_id, predictions in segment_predictions.items():
                if len(predictions) >= 2:
                    # Simple trend calculation
                    initial = predictions[0]
                    final = predictions[-1]
                    
                    if final > initial * 1.1:
                        trends[segment_id] = "increasing_congestion"
                    elif final < initial * 0.9:
                        trends[segment_id] = "decreasing_congestion"
                    else:
                        trends[segment_id] = "stable"
            
            return trends
            
        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            return {}
    
    async def _generate_traffic_recommendations(self, state: TrafficSimulationState, 
                                              predictions: Dict[str, List[float]]) -> List[str]:
        """Generate traffic management recommendations"""
        recommendations = []
        
        try:
            # Analyze predictions for problematic segments
            for segment_id, prediction_series in predictions.items():
                if prediction_series and max(prediction_series) > 0.8:  # High congestion predicted
                    recommendations.append(f"Consider rerouting traffic from segment {segment_id}")
            
            # Check for signal optimization opportunities
            if len(state.signals) > 0:
                recommendations.append("Review traffic signal timing for potential optimization")
            
            # Check incident response
            if len(state.incidents) > 0:
                recommendations.append("Monitor active incidents and ensure appropriate response resources")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _calculate_signal_delays(self, signal: TrafficSignal, state: TrafficSimulationState) -> Dict[str, float]:
        """Calculate current delays at traffic signal"""
        delays = {}
        
        try:
            for segment_id in signal.controlled_segments:
                # Count waiting vehicles
                waiting_vehicles = len([v for v in state.vehicles.values() 
                                      if v.current_segment == segment_id and v.current_speed < 5.0])
                
                # Estimate delay (simplified)
                estimated_delay = waiting_vehicles * 30.0  # 30 seconds per waiting vehicle
                delays[segment_id] = estimated_delay
            
            return delays
            
        except Exception as e:
            logger.error(f"Error calculating signal delays: {e}")
            return {}
    
    async def _optimize_signal_timing(self, signal: TrafficSignal, state: TrafficSimulationState) -> Dict[str, float]:
        """Optimize signal timing based on current conditions"""
        optimized_timings = {}
        
        try:
            # Count demand on each approach
            approach_demands = {}
            
            for segment_id in signal.controlled_segments:
                vehicle_count = len([v for v in state.vehicles.values() 
                                   if v.current_segment == segment_id])
                approach_demands[segment_id] = vehicle_count
            
            # Allocate green time proportional to demand
            total_demand = sum(approach_demands.values())
            
            if total_demand > 0:
                for segment_id, demand in approach_demands.items():
                    proportion = demand / total_demand
                    optimized_green_time = signal.cycle_time * proportion * 0.8  # 80% of cycle for green
                    optimized_timings[segment_id] = max(10.0, optimized_green_time)  # Minimum 10 seconds
            
            return optimized_timings
            
        except Exception as e:
            logger.error(f"Error optimizing signal timing: {e}")
            return {}
    
    async def _estimate_signal_improvement(self, signal: TrafficSignal, new_timings: Dict[str, float], 
                                         state: TrafficSimulationState) -> float:
        """Estimate improvement from signal timing changes"""
        try:
            # Simple improvement estimation
            current_delays = await self._calculate_signal_delays(signal, state)
            total_current_delay = sum(current_delays.values())
            
            # Estimate new delays (simplified)
            improvement_factor = 0.8  # Assume 20% improvement
            estimated_new_delay = total_current_delay * improvement_factor
            
            improvement = (total_current_delay - estimated_new_delay) / max(total_current_delay, 1.0)
            
            return improvement
            
        except Exception as e:
            logger.error(f"Error estimating signal improvement: {e}")
            return 0.0
    
    async def _calculate_delay_increase(self, segment: RoadSegment, original_conditions: Dict[str, Any]) -> float:
        """Calculate delay increase due to incident"""
        try:
            # Simple delay calculation based on speed reduction
            original_speed = original_conditions['speed']
            current_speed = segment.current_speed
            
            if original_speed > 0 and current_speed > 0:
                original_travel_time = segment.length / (original_speed / 3.6)  # Convert km/h to m/s
                current_travel_time = segment.length / (current_speed / 3.6)
                
                delay_increase = current_travel_time - original_travel_time
                return max(0, delay_increase)  # Seconds
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating delay increase: {e}")
            return 0.0


# Singleton instance
_traffic_pattern_modeling_service: Optional[TrafficPatternModelingService] = None


def get_traffic_pattern_modeling_service() -> TrafficPatternModelingService:
    """Get the singleton traffic pattern modeling service instance"""
    global _traffic_pattern_modeling_service
    
    if _traffic_pattern_modeling_service is None:
        # Initialize with default implementations
        simulator = MicroscopicTrafficSimulator()
        analyzer = IntelligentTrafficAnalyzer()
        incident_manager = SmartIncidentManager()
        
        _traffic_pattern_modeling_service = TrafficPatternModelingService(
            simulator=simulator,
            analyzer=analyzer,
            incident_manager=incident_manager
        )
    
    return _traffic_pattern_modeling_service


async def main():
    """Example usage of the traffic pattern modeling service"""
    service = get_traffic_pattern_modeling_service()
    
    try:
        await service.start()
        
        # Example 1: Create road network
        print("=== Creating Road Network ===")
        
        segments = [
            RoadSegment(
                segment_id="highway_1",
                name="Highway 1 - North",
                road_type=RoadType.HIGHWAY,
                start_coord=Coordinate(40.7128, -74.0060),  # NYC
                end_coord=Coordinate(40.7589, -73.9851),    # Central Park
                length=5000,  # 5km
                lanes=3,
                speed_limit=80,
                capacity=2000
            ),
            RoadSegment(
                segment_id="arterial_1",
                name="Broadway",
                road_type=RoadType.ARTERIAL,
                start_coord=Coordinate(40.7589, -73.9851),
                end_coord=Coordinate(40.7831, -73.9712),
                length=3000,
                lanes=2,
                speed_limit=50,
                capacity=1200
            ),
            RoadSegment(
                segment_id="local_1",
                name="5th Avenue",
                road_type=RoadType.LOCAL,
                start_coord=Coordinate(40.7831, -73.9712),
                end_coord=Coordinate(40.7505, -73.9934),
                length=2500,
                lanes=2,
                speed_limit=40,
                capacity=800
            )
        ]
        
        success = await service.create_road_network(segments)
        print(f"Created road network: {success}")
        
        # Example 2: Start traffic simulation
        print("=== Starting Traffic Simulation ===")
        
        initial_conditions = {
            'weather': WeatherCondition.CLEAR,
            'visibility': 100.0,
            'temperature': 22.0,
            'initial_vehicles': [
                {
                    'vehicle_id': 'vehicle_001',
                    'vehicle_type': VehicleType.CAR,
                    'current_position': Coordinate(40.7128, -74.0060),
                    'destination': Coordinate(40.7505, -73.9934),
                    'current_segment': 'highway_1',
                    'desired_speed': 70.0
                }
            ],
            'signals': [
                {
                    'signal_id': 'signal_001',
                    'location': Coordinate(40.7589, -73.9851),
                    'controlled_segments': ['highway_1', 'arterial_1'],
                    'cycle_time': 120.0,
                    'green_times': {'highway_1': 60.0, 'arterial_1': 45.0},
                    'adaptive': True
                }
            ]
        }
        
        sim_started = await service.start_simulation("nyc_traffic_sim", initial_conditions)
        print(f"Started simulation: {sim_started}")
        
        # Let simulation run for a bit
        await asyncio.sleep(5)
        
        # Example 3: Get simulation state
        print("=== Current Simulation State ===")
        
        state = await service.get_simulation_state("nyc_traffic_sim")
        if state:
            print(f"Current time: {state.current_time}")
            print(f"Active vehicles: {len(state.vehicles)}")
            print(f"Road segments: {len(state.segments)}")
            print(f"Traffic signals: {len(state.signals)}")
            print(f"Active incidents: {len(state.incidents)}")
            print(f"Weather: {state.weather_condition.value}")
            print(f"Average speed: {state.average_speed:.2f} km/h")
        
        # Example 4: Traffic analytics
        print("\n=== Traffic Analytics ===")
        
        analytics = await service.get_traffic_analytics("nyc_traffic_sim")
        if analytics:
            print(f"Total vehicles: {analytics.total_vehicles}")
            print(f"Average travel time: {analytics.average_travel_time:.2f} hours")
            print(f"Average speed: {analytics.average_speed:.2f} km/h")
            print(f"Congestion index: {analytics.congestion_index:.2f}")
            print(f"Fuel consumption: {analytics.fuel_consumption:.2f} L")
            print(f"Emissions: {analytics.emissions:.2f} kg CO2")
            
            if analytics.bottleneck_segments:
                print(f"\nTop bottlenecks:")
                for segment_id, severity in analytics.bottleneck_segments[:3]:
                    print(f"  - {segment_id}: severity {severity:.2f}")
            
            print(f"\nEfficiency metrics:")
            for metric, value in analytics.efficiency_metrics.items():
                print(f"  - {metric}: {value:.2f}")
        
        # Example 5: Traffic predictions
        print("\n=== Traffic Predictions ===")
        
        predictions = await service.predict_traffic_conditions("nyc_traffic_sim", forecast_hours=2)
        if predictions:
            print(f"Forecast for next {predictions['forecast_hours']} hours:")
            
            for segment_id, prediction_series in predictions['segment_predictions'].items():
                if prediction_series:
                    avg_congestion = sum(prediction_series) / len(prediction_series)
                    print(f"  - {segment_id}: avg congestion {avg_congestion:.2f}")
            
            if predictions['recommendations']:
                print(f"\nRecommendations:")
                for rec in predictions['recommendations']:
                    print(f"  - {rec}")
        
        # Example 6: Simulate traffic incident
        print("\n=== Simulating Traffic Incident ===")
        
        test_incident = TrafficIncident(
            incident_id="incident_001",
            incident_type=IncidentType.ACCIDENT,
            location=Coordinate(40.7589, -73.9851),
            affected_segments=["arterial_1"],
            severity=3,
            start_time=datetime.now(),
            estimated_duration=45.0,
            capacity_reduction=0.5,
            speed_reduction=0.6,
            description="Multi-vehicle accident on Broadway"
        )
        
        incident_impact = await service.simulate_incident_impact("nyc_traffic_sim", test_incident)
        if incident_impact:
            print(f"Incident impact analysis:")
            print(f"  Affected segments: {incident_impact['affected_segments']}")
            
            for segment_id, metrics in incident_impact['impact_metrics'].items():
                print(f"  {segment_id}:")
                print(f"    Speed reduction: {metrics['speed_reduction']:.1%}")
                print(f"    Volume change: {metrics['volume_change']:.0f} vehicles")
                print(f"    Delay increase: {metrics['delay_increase']:.0f} seconds")
            
            response_plan = incident_impact.get('response_plan', {})
            if response_plan:
                print(f"\n  Response plan:")
                print(f"    Priority: {response_plan.get('priority', 'N/A')}")
                if 'actions' in response_plan:
                    for action in response_plan['actions'][:3]:
                        print(f"    - {action}")
        
        # Example 7: Signal optimization
        print("\n=== Traffic Signal Optimization ===")
        
        signal_optimizations = await service.optimize_traffic_signals("nyc_traffic_sim")
        if signal_optimizations:
            for signal_id, optimization in signal_optimizations.items():
                print(f"Signal {signal_id}:")
                print(f"  Current delays: {optimization['current_delays']}")
                print(f"  Suggested green times: {optimization['suggested_green_times']}")
                print(f"  Expected improvement: {optimization['expected_improvement']:.1%}")
        
        # Let simulation run a bit more
        await asyncio.sleep(5)
        
        # Stop simulation
        await service.stop_simulation("nyc_traffic_sim")
        print("\nStopped traffic simulation")
        
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())