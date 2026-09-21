"""
Shared Navigation View System
Real-time navigation display shared across all crew stations
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
import websockets
import threading
from pathlib import Path

from ..crew.crew_management import CrewRole
from ..roles.permissions import Permission, PermissionScope, AccessLevel, PermissionManager

logger = logging.getLogger(__name__)

class NavigationDataType(Enum):
    POSITION = "position"
    HEADING = "heading"
    SPEED = "speed"
    DEPTH = "depth"
    WIND = "wind"
    WAYPOINT = "waypoint"
    ROUTE = "route"
    AIS_TARGET = "ais_target"
    FISH_MARK = "fish_mark"
    ALERT = "alert"
    CHART_UPDATE = "chart_update"

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class DisplayMode(Enum):
    FULL = "full"           # Full navigation display
    SIMPLIFIED = "simplified"  # Basic info only
    WATCH = "watch"         # Watch-specific display
    RESTRICTED = "restricted"  # Limited view

@dataclass
class NavigationData:
    data_id: str
    data_type: NavigationDataType
    timestamp: datetime
    data: Dict[str, Any]
    source_station: str
    requires_permission: Optional[Permission] = None
    alert_level: Optional[AlertLevel] = None
    
    def __post_init__(self):
        if not self.data_id:
            self.data_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['data_type'] = self.data_type.value
        result['timestamp'] = self.timestamp.isoformat()
        if result.get('requires_permission'):
            result['requires_permission'] = result['requires_permission'].value
        if result.get('alert_level'):
            result['alert_level'] = result['alert_level'].value
        return result

@dataclass
class CrewStation:
    station_id: str
    member_id: str
    role: CrewRole
    display_mode: DisplayMode = DisplayMode.FULL
    active: bool = True
    last_activity: Optional[datetime] = None
    subscribed_data_types: Optional[Set[NavigationDataType]] = None
    position: Optional[Dict[str, int]] = None  # Screen position/size
    
    def __post_init__(self):
        if self.subscribed_data_types is None:
            self.subscribed_data_types = set()
        if self.last_activity is None:
            self.last_activity = datetime.now(timezone.utc)
        if self.position is None:
            self.position = {'x': 0, 'y': 0, 'width': 1920, 'height': 1080}
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['role'] = self.role.value
        result['display_mode'] = self.display_mode.value
        result['subscribed_data_types'] = [dt.value for dt in self.subscribed_data_types]
        if result.get('last_activity'):
            result['last_activity'] = result['last_activity'].isoformat()
        return result

@dataclass
class FishCount:
    count_id: str
    species: str
    count: int
    weight: Optional[float] = None  # kg
    location: Optional[Dict[str, float]] = None  # lat, lon
    logged_by: Optional[str] = None  # member_id
    timestamp: Optional[datetime] = None
    trip_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.count_id:
            self.count_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if result.get('timestamp'):
            result['timestamp'] = result['timestamp'].isoformat()
        return result

class SharedNavigationManager:
    """Manages shared navigation data across crew stations"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.permission_manager = PermissionManager()
        
        # Active crew stations
        self.stations: Dict[str, CrewStation] = {}
        
        # Current navigation data
        self.navigation_data: Dict[NavigationDataType, NavigationData] = {}
        
        # WebSocket connections
        self.websocket_connections: Dict[str, Any] = {}
        
        # Data subscription management
        self.data_subscriptions: Dict[NavigationDataType, Set[str]] = {}
        
        # Fish count tracking
        self.fish_counts: Dict[str, List[FishCount]] = {}  # trip_id -> counts
        
        # Initialize data subscriptions
        for data_type in NavigationDataType:
            self.data_subscriptions[data_type] = set()
    
    def register_station(self, member_id: str, role: CrewRole, 
                        display_mode: DisplayMode = DisplayMode.FULL) -> CrewStation:
        """Register crew station for shared navigation"""
        station_id = f"station_{member_id}_{uuid.uuid4().hex[:8]}"
        
        station = CrewStation(
            station_id=station_id,
            member_id=member_id,
            role=role,
            display_mode=display_mode
        )
        
        # Set default subscriptions based on role and permissions
        self._setup_default_subscriptions(station)
        
        self.stations[station_id] = station
        logger.info(f"Registered navigation station: {station_id} for {role.value}")
        
        return station
    
    def unregister_station(self, station_id: str) -> bool:
        """Unregister crew station"""
        if station_id not in self.stations:
            return False
        
        station = self.stations[station_id]
        
        # Remove from all subscriptions
        for data_type, subscribers in self.data_subscriptions.items():
            subscribers.discard(station_id)
        
        # Close WebSocket connection if exists
        if station_id in self.websocket_connections:
            del self.websocket_connections[station_id]
        
        del self.stations[station_id]
        logger.info(f"Unregistered navigation station: {station_id}")
        
        return True
    
    def _setup_default_subscriptions(self, station: CrewStation):
        """Setup default data subscriptions based on role"""
        role = station.role
        
        # Basic navigation data for all roles
        basic_data = {
            NavigationDataType.POSITION,
            NavigationDataType.HEADING,
            NavigationDataType.SPEED,
            NavigationDataType.DEPTH
        }
        
        station.subscribed_data_types.update(basic_data)
        
        # Role-specific subscriptions
        if role in [CrewRole.CAPTAIN, CrewRole.FIRST_MATE, CrewRole.MATE]:
            # Officers get full navigation data
            officer_data = {
                NavigationDataType.WIND,
                NavigationDataType.WAYPOINT,
                NavigationDataType.ROUTE,
                NavigationDataType.AIS_TARGET,
                NavigationDataType.ALERT
            }
            station.subscribed_data_types.update(officer_data)
        
        if role in [CrewRole.CAPTAIN, CrewRole.FIRST_MATE, CrewRole.MATE, CrewRole.DECKHAND]:
            # Fishing crew gets fish-related data
            station.subscribed_data_types.add(NavigationDataType.FISH_MARK)
        
        if role == CrewRole.ENGINEER:
            # Engineer gets system alerts
            station.subscribed_data_types.add(NavigationDataType.ALERT)
        
        # Add station to subscriptions
        for data_type in station.subscribed_data_types:
            self.data_subscriptions[data_type].add(station.station_id)
    
    def update_navigation_data(self, data_type: NavigationDataType, data: Dict[str, Any],
                             source_station: str, alert_level: Optional[AlertLevel] = None) -> bool:
        """Update navigation data and broadcast to subscribed stations"""
        
        # Check if source station has permission to update this data type
        source_station_obj = self.stations.get(source_station)
        if not source_station_obj:
            logger.warning(f"Unknown source station: {source_station}")
            return False
        
        required_permission = self._get_required_permission(data_type)
        if required_permission:
            has_permission = self.permission_manager.has_permission(
                source_station_obj.role, required_permission, 
                PermissionScope.VESSEL, AccessLevel.WRITE
            )
            
            if not has_permission:
                logger.warning(f"Station {source_station} lacks permission for {data_type.value}")
                return False
        
        # Create navigation data object
        nav_data = NavigationData(
            data_id=str(uuid.uuid4()),
            data_type=data_type,
            timestamp=datetime.now(timezone.utc),
            data=data,
            source_station=source_station,
            requires_permission=self._get_view_permission(data_type),
            alert_level=alert_level
        )
        
        # Store current data
        self.navigation_data[data_type] = nav_data
        
        # Broadcast to subscribed stations
        self._broadcast_to_subscribers(data_type, nav_data)
        
        logger.info(f"Updated navigation data: {data_type.value} from {source_station}")
        return True
    
    def _get_required_permission(self, data_type: NavigationDataType) -> Optional[Permission]:
        """Get required permission to update data type"""
        permission_map = {
            NavigationDataType.WAYPOINT: Permission.SET_COURSE,
            NavigationDataType.ROUTE: Permission.SET_COURSE,
            NavigationDataType.FISH_MARK: Permission.LOG_CATCHES,
            NavigationDataType.ALERT: Permission.SEND_BROADCASTS
        }
        
        return permission_map.get(data_type)
    
    def _get_view_permission(self, data_type: NavigationDataType) -> Optional[Permission]:
        """Get required permission to view data type"""
        permission_map = {
            NavigationDataType.POSITION: Permission.VIEW_NAVIGATION,
            NavigationDataType.HEADING: Permission.VIEW_NAVIGATION,
            NavigationDataType.SPEED: Permission.VIEW_NAVIGATION,
            NavigationDataType.DEPTH: Permission.VIEW_NAVIGATION,
            NavigationDataType.WIND: Permission.VIEW_NAVIGATION,
            NavigationDataType.WAYPOINT: Permission.VIEW_NAVIGATION,
            NavigationDataType.ROUTE: Permission.VIEW_NAVIGATION,
            NavigationDataType.AIS_TARGET: Permission.VIEW_NAVIGATION,
            NavigationDataType.FISH_MARK: Permission.VIEW_CATCH_DATA
        }
        
        return permission_map.get(data_type)
    
    def _broadcast_to_subscribers(self, data_type: NavigationDataType, nav_data: NavigationData):
        """Broadcast data to subscribed stations"""
        subscribers = self.data_subscriptions.get(data_type, set())
        
        for station_id in subscribers:
            station = self.stations.get(station_id)
            if not station or not station.active:
                continue
            
            # Check if station has permission to view this data
            if nav_data.requires_permission:
                has_permission = self.permission_manager.has_permission(
                    station.role, nav_data.requires_permission,
                    PermissionScope.VESSEL, AccessLevel.READ
                )
                
                if not has_permission:
                    continue
            
            # Filter data based on station display mode
            filtered_data = self._filter_data_for_station(nav_data, station)
            
            # Send to WebSocket if connected
            if station_id in self.websocket_connections:
                self._send_websocket_data(station_id, filtered_data)
    
    def _filter_data_for_station(self, nav_data: NavigationData, station: CrewStation) -> NavigationData:
        """Filter navigation data based on station display mode and permissions"""
        if station.display_mode == DisplayMode.FULL:
            return nav_data
        
        # Create filtered copy
        filtered_data = nav_data.data.copy()
        
        if station.display_mode == DisplayMode.SIMPLIFIED:
            # Keep only essential fields
            if nav_data.data_type == NavigationDataType.POSITION:
                filtered_data = {
                    'latitude': nav_data.data.get('latitude'),
                    'longitude': nav_data.data.get('longitude')
                }
            elif nav_data.data_type == NavigationDataType.AIS_TARGET:
                # Limit number of targets
                if 'targets' in filtered_data:
                    filtered_data['targets'] = filtered_data['targets'][:5]
        
        elif station.display_mode == DisplayMode.WATCH:
            # Watch-specific filtering
            if nav_data.data_type == NavigationDataType.ALERT:
                # Only show watch-relevant alerts
                if nav_data.alert_level not in [AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                    filtered_data = {}
        
        elif station.display_mode == DisplayMode.RESTRICTED:
            # Very limited data for restricted access
            if nav_data.data_type in [NavigationDataType.WAYPOINT, NavigationDataType.ROUTE]:
                filtered_data = {}
        
        return NavigationData(
            data_id=nav_data.data_id,
            data_type=nav_data.data_type,
            timestamp=nav_data.timestamp,
            data=filtered_data,
            source_station=nav_data.source_station,
            requires_permission=nav_data.requires_permission,
            alert_level=nav_data.alert_level
        )
    
    def _send_websocket_data(self, station_id: str, nav_data: NavigationData):
        """Send data to WebSocket connection"""
        connection = self.websocket_connections.get(station_id)
        if not connection:
            return
        
        try:
            message = {
                'type': 'navigation_update',
                'data': nav_data.to_dict()
            }
            
            # Send asynchronously
            asyncio.create_task(connection.send(json.dumps(message)))
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket data to {station_id}: {e}")
            # Remove failed connection
            if station_id in self.websocket_connections:
                del self.websocket_connections[station_id]
    
    def add_fish_count(self, trip_id: str, species: str, count: int, 
                      weight: Optional[float] = None, logged_by: Optional[str] = None,
                      location: Optional[Dict[str, float]] = None) -> FishCount:
        """Add fish count entry"""
        fish_count = FishCount(
            count_id=str(uuid.uuid4()),
            species=species,
            count=count,
            weight=weight,
            location=location,
            logged_by=logged_by,
            trip_id=trip_id
        )
        
        if trip_id not in self.fish_counts:
            self.fish_counts[trip_id] = []
        
        self.fish_counts[trip_id].append(fish_count)
        
        # Broadcast fish count update
        fish_data = {
            'trip_id': trip_id,
            'species': species,
            'count': count,
            'weight': weight,
            'total_count': self.get_total_fish_count(trip_id),
            'species_breakdown': self.get_species_breakdown(trip_id)
        }
        
        self.update_navigation_data(
            NavigationDataType.FISH_MARK,
            fish_data,
            f"system_{logged_by}" if logged_by else "system"
        )
        
        logger.info(f"Added fish count: {count} {species} for trip {trip_id}")
        return fish_count
    
    def get_total_fish_count(self, trip_id: str) -> int:
        """Get total fish count for trip"""
        if trip_id not in self.fish_counts:
            return 0
        
        return sum(fc.count for fc in self.fish_counts[trip_id])
    
    def get_species_breakdown(self, trip_id: str) -> Dict[str, int]:
        """Get fish count by species for trip"""
        if trip_id not in self.fish_counts:
            return {}
        
        breakdown = {}
        for fish_count in self.fish_counts[trip_id]:
            species = fish_count.species
            breakdown[species] = breakdown.get(species, 0) + fish_count.count
        
        return breakdown
    
    def get_fish_count_display_data(self, trip_id: str) -> Dict[str, Any]:
        """Get formatted fish count data for display"""
        if trip_id not in self.fish_counts:
            return {
                'trip_id': trip_id,
                'total_count': 0,
                'species_breakdown': {},
                'recent_entries': []
            }
        
        counts = self.fish_counts[trip_id]
        recent_entries = sorted(counts, key=lambda x: x.timestamp, reverse=True)[:10]
        
        return {
            'trip_id': trip_id,
            'total_count': self.get_total_fish_count(trip_id),
            'species_breakdown': self.get_species_breakdown(trip_id),
            'recent_entries': [entry.to_dict() for entry in recent_entries],
            'last_updated': recent_entries[0].timestamp.isoformat() if recent_entries else None
        }
    
    def subscribe_station_to_data(self, station_id: str, data_types: List[NavigationDataType]) -> bool:
        """Subscribe station to additional data types"""
        if station_id not in self.stations:
            return False
        
        station = self.stations[station_id]
        
        # Check permissions for each data type
        for data_type in data_types:
            required_permission = self._get_view_permission(data_type)
            if required_permission:
                has_permission = self.permission_manager.has_permission(
                    station.role, required_permission,
                    PermissionScope.VESSEL, AccessLevel.READ
                )
                
                if not has_permission:
                    logger.warning(f"Station {station_id} lacks permission for {data_type.value}")
                    continue
            
            # Add to subscriptions
            station.subscribed_data_types.add(data_type)
            self.data_subscriptions[data_type].add(station_id)
        
        logger.info(f"Updated subscriptions for station {station_id}")
        return True
    
    def get_station_data(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Get current navigation data for station"""
        if station_id not in self.stations:
            return None
        
        station = self.stations[station_id]
        station.update_activity()
        
        # Collect data for subscribed types
        station_data = {
            'station_info': station.to_dict(),
            'navigation_data': {},
            'fish_count_data': {}
        }
        
        # Get navigation data
        for data_type in station.subscribed_data_types:
            if data_type in self.navigation_data:
                nav_data = self.navigation_data[data_type]
                
                # Check permissions
                if nav_data.requires_permission:
                    has_permission = self.permission_manager.has_permission(
                        station.role, nav_data.requires_permission,
                        PermissionScope.VESSEL, AccessLevel.READ
                    )
                    
                    if not has_permission:
                        continue
                
                # Filter and add data
                filtered_data = self._filter_data_for_station(nav_data, station)
                station_data['navigation_data'][data_type.value] = filtered_data.to_dict()
        
        return station_data
    
    def get_active_stations(self) -> List[Dict[str, Any]]:
        """Get list of active navigation stations"""
        active_stations = []
        
        for station in self.stations.values():
            if station.active:
                # Check if station is still active (within last 5 minutes)
                if station.last_activity:
                    time_since_activity = datetime.now(timezone.utc) - station.last_activity
                    if time_since_activity > timedelta(minutes=5):
                        station.active = False
                        continue
                
                active_stations.append(station.to_dict())
        
        return active_stations
    
    def set_station_display_mode(self, station_id: str, display_mode: DisplayMode) -> bool:
        """Set display mode for station"""
        if station_id not in self.stations:
            return False
        
        self.stations[station_id].display_mode = display_mode
        self.stations[station_id].update_activity()
        
        logger.info(f"Set display mode for station {station_id}: {display_mode.value}")
        return True
    
    def broadcast_alert(self, alert_message: str, alert_level: AlertLevel, 
                       source_station: str, alert_data: Optional[Dict[str, Any]] = None) -> bool:
        """Broadcast alert to all stations"""
        alert_data = alert_data or {}
        alert_data.update({
            'message': alert_message,
            'level': alert_level.value,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        return self.update_navigation_data(
            NavigationDataType.ALERT,
            alert_data,
            source_station,
            alert_level
        )

async def main():
    """Example usage of shared navigation system"""
    
    # Initialize shared navigation manager
    nav_manager = SharedNavigationManager()
    
    print("=== Shared Navigation System Demo ===")
    
    # Register crew stations
    captain_station = nav_manager.register_station("capt_001", CrewRole.CAPTAIN)
    mate_station = nav_manager.register_station("mate_001", CrewRole.FIRST_MATE, DisplayMode.FULL)
    deckhand_station = nav_manager.register_station("deck_001", CrewRole.DECKHAND, DisplayMode.SIMPLIFIED)
    
    print(f"Registered stations:")
    print(f"- Captain: {captain_station.station_id}")
    print(f"- Mate: {mate_station.station_id}")
    print(f"- Deckhand: {deckhand_station.station_id}")
    
    # Update navigation data
    position_data = {
        'latitude': 40.7128,
        'longitude': -74.0060,
        'accuracy': 5.0,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    nav_manager.update_navigation_data(
        NavigationDataType.POSITION,
        position_data,
        captain_station.station_id
    )
    
    # Update fish count
    trip_id = "trip_2024_001"
    nav_manager.add_fish_count(trip_id, "Striped Bass", 5, 12.5, "deck_001")
    nav_manager.add_fish_count(trip_id, "Bluefish", 3, 8.2, "deck_001")
    nav_manager.add_fish_count(trip_id, "Striped Bass", 2, 9.1, "mate_001")
    
    # Get fish count display data
    fish_data = nav_manager.get_fish_count_display_data(trip_id)
    print(f"\nFish Count Data:")
    print(f"- Total fish: {fish_data['total_count']}")
    print(f"- Species breakdown: {fish_data['species_breakdown']}")
    print(f"- Recent entries: {len(fish_data['recent_entries'])}")
    
    # Broadcast alert
    nav_manager.broadcast_alert(
        "Shallow water detected - 8 feet depth",
        AlertLevel.WARNING,
        captain_station.station_id,
        {'depth': 8.0, 'location': position_data}
    )
    
    # Get station data
    captain_data = nav_manager.get_station_data(captain_station.station_id)
    if captain_data:
        print(f"\nCaptain station data:")
        print(f"- Navigation data types: {len(captain_data['navigation_data'])}")
        print(f"- Subscribed to: {captain_data['station_info']['subscribed_data_types']}")
    
    # Get active stations
    active_stations = nav_manager.get_active_stations()
    print(f"\nActive stations: {len(active_stations)}")
    for station in active_stations:
        print(f"- {station['role']}: {station['display_mode']} mode")
    
    # Test permission-based filtering
    guest_station = nav_manager.register_station("guest_001", CrewRole.GUEST, DisplayMode.RESTRICTED)
    guest_data = nav_manager.get_station_data(guest_station.station_id)
    
    if guest_data:
        print(f"\nGuest station (restricted access):")
        print(f"- Navigation data types: {len(guest_data['navigation_data'])}")
        print(f"- Subscribed to: {guest_data['station_info']['subscribed_data_types']}")

if __name__ == "__main__":
    asyncio.run(main())