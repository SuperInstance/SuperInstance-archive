"""
Virtual Tabletop Service

Provides real-time shared maps, token management, and fog of war functionality
for D&D sessions with WebSocket support for multiplayer interaction.
"""

import asyncio
import json
import math
import uuid
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import websockets
from websockets.exceptions import ConnectionClosed

from ..models.base import BaseSessionModel
from ..models.tabletop import (
    TabletopMap, TabletopToken, Position, LightSource, FogOfWarState,
    TokenMovement, MapAnnotation, TabletopState
)
from ..models.session import SessionSchema
from ..config import TABLETOP_CONFIG


class FogOfWarEngine:
    """Handles fog of war calculations and visibility"""
    
    def __init__(self, map_width: int, map_height: int, grid_size: int = 50):
        self.map_width = map_width
        self.map_height = map_height
        self.grid_size = grid_size
        self.grid_width = math.ceil(map_width / grid_size)
        self.grid_height = math.ceil(map_height / grid_size)
        
        # Fog states: 0=unexplored, 1=explored, 2=visible
        self.fog_grid = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)
        self.visibility_cache = {}
    
    def calculate_line_of_sight(self, start: Position, end: Position, 
                              obstacles: List[Position]) -> bool:
        """Calculate if there's line of sight between two points"""
        x0, y0 = start.x, start.y
        x1, y1 = end.x, end.y
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x, y = x0, y0
        
        while True:
            # Check if current position has obstacle
            for obstacle in obstacles:
                if (abs(x - obstacle.x) < self.grid_size/2 and 
                    abs(y - obstacle.y) < self.grid_size/2):
                    return False
            
            if x == x1 and y == y1:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return True
    
    def update_visibility(self, token: TabletopToken, obstacles: List[Position]):
        """Update fog of war based on token's vision and light sources"""
        token_pos = token.position
        vision_range = token.vision_range or TABLETOP_CONFIG["default_vision_range"]
        
        # Calculate visible grid cells
        start_x = max(0, int((token_pos.x - vision_range) // self.grid_size))
        end_x = min(self.grid_width, int((token_pos.x + vision_range) // self.grid_size) + 1)
        start_y = max(0, int((token_pos.y - vision_range) // self.grid_size))
        end_y = min(self.grid_height, int((token_pos.y + vision_range) // self.grid_size) + 1)
        
        for gx in range(start_x, end_x):
            for gy in range(start_y, end_y):
                cell_x = gx * self.grid_size + self.grid_size // 2
                cell_y = gy * self.grid_size + self.grid_size // 2
                cell_pos = Position(x=cell_x, y=cell_y)
                
                distance = math.sqrt((token_pos.x - cell_x)**2 + (token_pos.y - cell_y)**2)
                
                if distance <= vision_range:
                    if self.calculate_line_of_sight(token_pos, cell_pos, obstacles):
                        self.fog_grid[gy, gx] = 2  # Visible
                    elif self.fog_grid[gy, gx] == 0:
                        self.fog_grid[gy, gx] = 1  # Explored but not visible
        
        # Handle light sources
        for light_source in token.light_sources:
            self._update_light_visibility(light_source, obstacles)
    
    def _update_light_visibility(self, light_source: LightSource, obstacles: List[Position]):
        """Update visibility based on light source"""
        light_pos = light_source.position
        light_range = light_source.range
        
        start_x = max(0, int((light_pos.x - light_range) // self.grid_size))
        end_x = min(self.grid_width, int((light_pos.x + light_range) // self.grid_size) + 1)
        start_y = max(0, int((light_pos.y - light_range) // self.grid_size))
        end_y = min(self.grid_height, int((light_pos.y + light_range) // self.grid_size) + 1)
        
        for gx in range(start_x, end_x):
            for gy in range(start_y, end_y):
                cell_x = gx * self.grid_size + self.grid_size // 2
                cell_y = gy * self.grid_size + self.grid_size // 2
                cell_pos = Position(x=cell_x, y=cell_y)
                
                distance = math.sqrt((light_pos.x - cell_x)**2 + (light_pos.y - cell_y)**2)
                
                if distance <= light_range:
                    if self.calculate_line_of_sight(light_pos, cell_pos, obstacles):
                        self.fog_grid[gy, gx] = 2  # Visible
    
    def get_fog_state(self) -> FogOfWarState:
        """Get current fog of war state"""
        return FogOfWarState(
            grid_width=self.grid_width,
            grid_height=self.grid_height,
            grid_size=self.grid_size,
            fog_data=self.fog_grid.tolist()
        )


class TokenManager:
    """Manages tokens on the tabletop"""
    
    def __init__(self):
        self.tokens: Dict[str, TabletopToken] = {}
        self.token_positions: Dict[str, Position] = {}
        self.movement_history: List[TokenMovement] = []
    
    async def add_token(self, token: TabletopToken) -> str:
        """Add a new token to the tabletop"""
        if not token.id:
            token.id = str(uuid.uuid4())
        
        self.tokens[token.id] = token
        self.token_positions[token.id] = token.position
        return token.id
    
    async def move_token(self, token_id: str, new_position: Position, 
                        user_id: str) -> Optional[TokenMovement]:
        """Move a token to a new position"""
        if token_id not in self.tokens:
            return None
        
        old_position = self.token_positions[token_id]
        movement = TokenMovement(
            token_id=token_id,
            from_position=old_position,
            to_position=new_position,
            moved_by=user_id,
            timestamp=datetime.utcnow()
        )
        
        self.tokens[token_id].position = new_position
        self.token_positions[token_id] = new_position
        self.movement_history.append(movement)
        
        return movement
    
    async def remove_token(self, token_id: str) -> bool:
        """Remove a token from the tabletop"""
        if token_id in self.tokens:
            del self.tokens[token_id]
            del self.token_positions[token_id]
            return True
        return False
    
    async def update_token(self, token_id: str, updates: Dict[str, Any]) -> bool:
        """Update token properties"""
        if token_id not in self.tokens:
            return False
        
        token = self.tokens[token_id]
        for key, value in updates.items():
            if hasattr(token, key):
                setattr(token, key, value)
        
        return True
    
    def get_tokens_in_range(self, center: Position, range_pixels: float) -> List[TabletopToken]:
        """Get all tokens within a certain range of a position"""
        tokens_in_range = []
        
        for token in self.tokens.values():
            distance = math.sqrt(
                (token.position.x - center.x)**2 + (token.position.y - center.y)**2
            )
            if distance <= range_pixels:
                tokens_in_range.append(token)
        
        return tokens_in_range


class MapManager:
    """Manages tabletop maps and annotations"""
    
    def __init__(self):
        self.current_map: Optional[TabletopMap] = None
        self.annotations: List[MapAnnotation] = []
        self.map_cache: Dict[str, TabletopMap] = {}
    
    async def load_map(self, map_data: TabletopMap) -> bool:
        """Load a new map onto the tabletop"""
        try:
            # Validate map image
            if map_data.image_path:
                with Image.open(map_data.image_path) as img:
                    map_data.width = img.width
                    map_data.height = img.height
            
            self.current_map = map_data
            self.map_cache[map_data.id] = map_data
            self.annotations = []  # Clear annotations when loading new map
            
            return True
        except Exception as e:
            print(f"Error loading map: {e}")
            return False
    
    async def add_annotation(self, annotation: MapAnnotation) -> str:
        """Add an annotation to the current map"""
        if not annotation.id:
            annotation.id = str(uuid.uuid4())
        
        self.annotations.append(annotation)
        return annotation.id
    
    async def remove_annotation(self, annotation_id: str) -> bool:
        """Remove an annotation from the map"""
        for i, annotation in enumerate(self.annotations):
            if annotation.id == annotation_id:
                del self.annotations[i]
                return True
        return False
    
    async def update_annotation(self, annotation_id: str, updates: Dict[str, Any]) -> bool:
        """Update an annotation"""
        for annotation in self.annotations:
            if annotation.id == annotation_id:
                for key, value in updates.items():
                    if hasattr(annotation, key):
                        setattr(annotation, key, value)
                return True
        return False


class WebSocketManager:
    """Manages WebSocket connections for real-time tabletop updates"""
    
    def __init__(self):
        self.connections: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.user_sessions: Dict[websockets.WebSocketServerProtocol, str] = {}
    
    async def connect(self, websocket: websockets.WebSocketServerProtocol, 
                     session_id: str, user_id: str):
        """Add a new WebSocket connection"""
        if session_id not in self.connections:
            self.connections[session_id] = set()
        
        self.connections[session_id].add(websocket)
        self.user_sessions[websocket] = user_id
        
        await self.send_to_connection(websocket, {
            "type": "connected",
            "session_id": session_id,
            "user_id": user_id
        })
    
    async def disconnect(self, websocket: websockets.WebSocketServerProtocol):
        """Remove a WebSocket connection"""
        user_id = self.user_sessions.get(websocket)
        
        for session_id, connections in self.connections.items():
            if websocket in connections:
                connections.remove(websocket)
                break
        
        if websocket in self.user_sessions:
            del self.user_sessions[websocket]
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections in a session"""
        if session_id not in self.connections:
            return
        
        disconnected = []
        for websocket in self.connections[session_id]:
            try:
                await websocket.send(json.dumps(message))
            except ConnectionClosed:
                disconnected.append(websocket)
        
        # Remove disconnected websockets
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def send_to_connection(self, websocket: websockets.WebSocketServerProtocol, 
                                message: Dict[str, Any]):
        """Send a message to a specific connection"""
        try:
            await websocket.send(json.dumps(message))
        except ConnectionClosed:
            await self.disconnect(websocket)


class VirtualTabletopService:
    """Main virtual tabletop service"""
    
    def __init__(self):
        self.sessions: Dict[str, TabletopState] = {}
        self.fog_engines: Dict[str, FogOfWarEngine] = {}
        self.token_managers: Dict[str, TokenManager] = {}
        self.map_managers: Dict[str, MapManager] = {}
        self.websocket_manager = WebSocketManager()
    
    async def create_tabletop_session(self, session: SessionSchema) -> TabletopState:
        """Create a new tabletop session"""
        tabletop_state = TabletopState(
            session_id=session.id,
            current_map=None,
            tokens=[],
            annotations=[],
            fog_of_war=None
        )
        
        self.sessions[session.id] = tabletop_state
        self.token_managers[session.id] = TokenManager()
        self.map_managers[session.id] = MapManager()
        
        return tabletop_state
    
    async def load_map(self, session_id: str, map_data: TabletopMap) -> bool:
        """Load a map for a session"""
        if session_id not in self.sessions:
            return False
        
        map_manager = self.map_managers[session_id]
        success = await map_manager.load_map(map_data)
        
        if success:
            # Create fog of war engine for this map
            self.fog_engines[session_id] = FogOfWarEngine(
                map_data.width, map_data.height, map_data.grid_size
            )
            
            # Update session state
            self.sessions[session_id].current_map = map_data
            
            # Broadcast map change to all connected clients
            await self.websocket_manager.broadcast_to_session(session_id, {
                "type": "map_loaded",
                "map": map_data.dict()
            })
        
        return success
    
    async def add_token(self, session_id: str, token: TabletopToken, 
                       user_id: str) -> Optional[str]:
        """Add a token to the tabletop"""
        if session_id not in self.sessions:
            return None
        
        token_manager = self.token_managers[session_id]
        token_id = await token_manager.add_token(token)
        
        # Update session state
        self.sessions[session_id].tokens = list(token_manager.tokens.values())
        
        # Update fog of war if needed
        if token.vision_range and session_id in self.fog_engines:
            fog_engine = self.fog_engines[session_id]
            obstacles = self._get_obstacles(session_id)
            fog_engine.update_visibility(token, obstacles)
            self.sessions[session_id].fog_of_war = fog_engine.get_fog_state()
        
        # Broadcast token addition
        await self.websocket_manager.broadcast_to_session(session_id, {
            "type": "token_added",
            "token": token.dict(),
            "added_by": user_id
        })
        
        return token_id
    
    async def move_token(self, session_id: str, token_id: str, 
                        new_position: Position, user_id: str) -> bool:
        """Move a token on the tabletop"""
        if session_id not in self.sessions:
            return False
        
        token_manager = self.token_managers[session_id]
        movement = await token_manager.move_token(token_id, new_position, user_id)
        
        if movement:
            # Update session state
            self.sessions[session_id].tokens = list(token_manager.tokens.values())
            
            # Update fog of war if token has vision
            token = token_manager.tokens.get(token_id)
            if token and token.vision_range and session_id in self.fog_engines:
                fog_engine = self.fog_engines[session_id]
                obstacles = self._get_obstacles(session_id)
                fog_engine.update_visibility(token, obstacles)
                self.sessions[session_id].fog_of_war = fog_engine.get_fog_state()
            
            # Broadcast movement
            await self.websocket_manager.broadcast_to_session(session_id, {
                "type": "token_moved",
                "movement": movement.dict(),
                "fog_update": self.sessions[session_id].fog_of_war.dict() if self.sessions[session_id].fog_of_war else None
            })
            
            return True
        
        return False
    
    async def add_annotation(self, session_id: str, annotation: MapAnnotation, 
                            user_id: str) -> Optional[str]:
        """Add an annotation to the map"""
        if session_id not in self.sessions:
            return None
        
        map_manager = self.map_managers[session_id]
        annotation_id = await map_manager.add_annotation(annotation)
        
        # Update session state
        self.sessions[session_id].annotations = map_manager.annotations
        
        # Broadcast annotation addition
        await self.websocket_manager.broadcast_to_session(session_id, {
            "type": "annotation_added",
            "annotation": annotation.dict(),
            "added_by": user_id
        })
        
        return annotation_id
    
    async def update_fog_of_war(self, session_id: str):
        """Recalculate fog of war for all tokens with vision"""
        if session_id not in self.fog_engines or session_id not in self.token_managers:
            return
        
        fog_engine = self.fog_engines[session_id]
        token_manager = self.token_managers[session_id]
        obstacles = self._get_obstacles(session_id)
        
        # Reset fog grid to explored state
        fog_engine.fog_grid = np.where(fog_engine.fog_grid > 0, 1, 0)
        
        # Update visibility for all tokens with vision
        for token in token_manager.tokens.values():
            if token.vision_range:
                fog_engine.update_visibility(token, obstacles)
        
        # Update session state
        self.sessions[session_id].fog_of_war = fog_engine.get_fog_state()
        
        # Broadcast fog update
        await self.websocket_manager.broadcast_to_session(session_id, {
            "type": "fog_updated",
            "fog_of_war": self.sessions[session_id].fog_of_war.dict()
        })
    
    def _get_obstacles(self, session_id: str) -> List[Position]:
        """Get obstacle positions for line of sight calculations"""
        obstacles = []
        
        if session_id not in self.sessions:
            return obstacles
        
        current_map = self.sessions[session_id].current_map
        if current_map and current_map.obstacles:
            obstacles.extend(current_map.obstacles)
        
        return obstacles
    
    async def get_session_state(self, session_id: str) -> Optional[TabletopState]:
        """Get the current state of a tabletop session"""
        return self.sessions.get(session_id)
    
    async def handle_websocket_message(self, websocket: websockets.WebSocketServerProtocol, 
                                     message: str, session_id: str, user_id: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "move_token":
                await self.move_token(
                    session_id,
                    data["token_id"],
                    Position(**data["position"]),
                    user_id
                )
            
            elif message_type == "add_annotation":
                annotation = MapAnnotation(**data["annotation"])
                await self.add_annotation(session_id, annotation, user_id)
            
            elif message_type == "update_fog":
                await self.update_fog_of_war(session_id)
            
            elif message_type == "ping":
                await self.websocket_manager.send_to_connection(websocket, {
                    "type": "pong"
                })
        
        except Exception as e:
            await self.websocket_manager.send_to_connection(websocket, {
                "type": "error",
                "message": str(e)
            })