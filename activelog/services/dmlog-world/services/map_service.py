"""
Map generation service for dungeons, towns, regions, and worlds.
"""

import random
import math
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from sqlalchemy.orm import Session
import logging
import numpy as np
from noise import pnoise2
import cv2
from PIL import Image, ImageDraw, ImageFont

from ..models.maps import (
    MapType, TileType, RoomType, ConnectionType, BiomeType, SettlementType,
    MapSchema, DungeonMap, SettlementMap, RegionMap, WorldMap,
    DungeonGenerationRequest, SettlementGenerationRequest,
    RegionGenerationRequest, WorldGenerationRequest,
    MapGenerationResponse, Room, DungeonLevel, Tile, Coordinate,
    MapAnalysis, PathfindingRequest, PathfindingResponse
)
from ..config import Config

logger = logging.getLogger(__name__)

class MapService:
    def __init__(self):
        self.config = Config()
        self.tile_colors = self._initialize_tile_colors()
        self.biome_colors = self._initialize_biome_colors()
        
    def _initialize_tile_colors(self) -> Dict[TileType, Tuple[int, int, int]]:
        """Initialize color mapping for different tile types."""
        return {
            TileType.VOID: (0, 0, 0),
            TileType.FLOOR: (200, 180, 140),
            TileType.WALL: (100, 100, 100),
            TileType.DOOR: (139, 69, 19),
            TileType.WATER: (30, 144, 255),
            TileType.ROAD: (105, 105, 105),
            TileType.GRASS: (34, 139, 34),
            TileType.FOREST: (0, 100, 0),
            TileType.MOUNTAIN: (139, 137, 137),
            TileType.DESERT: (238, 203, 173),
            TileType.SWAMP: (107, 142, 35),
            TileType.BUILDING: (160, 82, 45),
            TileType.ENTRANCE: (255, 215, 0),
            TileType.STAIRS_UP: (255, 255, 0),
            TileType.STAIRS_DOWN: (255, 140, 0),
            TileType.TREASURE: (255, 215, 0),
            TileType.TRAP: (220, 20, 60)
        }
    
    def _initialize_biome_colors(self) -> Dict[BiomeType, Tuple[int, int, int]]:
        """Initialize color mapping for different biomes."""
        return {
            BiomeType.ARCTIC: (240, 248, 255),
            BiomeType.TEMPERATE_FOREST: (34, 139, 34),
            BiomeType.TROPICAL_FOREST: (0, 100, 0),
            BiomeType.GRASSLAND: (124, 252, 0),
            BiomeType.DESERT: (238, 203, 173),
            BiomeType.SWAMP: (107, 142, 35),
            BiomeType.MOUNTAINS: (139, 137, 137),
            BiomeType.HILLS: (189, 183, 107),
            BiomeType.COAST: (255, 248, 220),
            BiomeType.OCEAN: (30, 144, 255),
            BiomeType.LAKE: (135, 206, 235),
            BiomeType.RIVER: (100, 149, 237),
            BiomeType.TUNDRA: (176, 196, 222),
            BiomeType.VOLCANIC: (178, 34, 34)
        }

    async def generate_dungeon(
        self,
        request: DungeonGenerationRequest,
        db_session: Optional[Session] = None
    ) -> MapGenerationResponse:
        """Generate a dungeon map with multiple levels."""
        
        start_time = datetime.utcnow()
        
        try:
            # Set random seed if provided
            if request.seed:
                random.seed(request.seed)
                np.random.seed(hash(request.seed) % 2**32)
            
            # Determine map dimensions
            width = request.width or 50
            height = request.height or 50
            
            # Generate dungeon levels
            levels = []
            for level_num in range(1, request.levels + 1):
                level = await self._generate_dungeon_level(
                    level_num, width, height, request
                )
                levels.append(level)
            
            # Create base tile grid
            tiles = [[Tile(tile_type=TileType.WALL) for _ in range(width)] for _ in range(height)]
            
            # Apply first level to main tile grid
            if levels:
                first_level = levels[0]
                for room in first_level.rooms:
                    for coord in room.coordinates:
                        if 0 <= coord.x < width and 0 <= coord.y < height:
                            tiles[coord.y][coord.x] = Tile(tile_type=TileType.FLOOR)
                
                # Add corridors
                for corridor in first_level.corridors:
                    for coord in corridor:
                        if 0 <= coord.x < width and 0 <= coord.y < height:
                            tiles[coord.y][coord.x] = Tile(tile_type=TileType.FLOOR)
            
            # Create dungeon map
            dungeon_map = DungeonMap(
                name=request.name or f"Generated Dungeon",
                map_type=MapType.DUNGEON,
                width=width,
                height=height,
                depth=request.levels,
                tiles=tiles,
                levels=levels,
                max_depth=request.levels,
                theme=request.theme,
                generation_seed=request.seed,
                generation_params=request.parameters
            )
            
            # Generate preview image
            preview_url = await self._generate_map_image(dungeon_map)
            
            # Calculate generation time
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            return MapGenerationResponse(
                success=True,
                map_data=dungeon_map,
                preview_url=preview_url,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error generating dungeon: {e}")
            return MapGenerationResponse(
                success=False,
                message=f"Failed to generate dungeon: {str(e)}",
                errors=[str(e)]
            )

    async def generate_settlement(
        self,
        request: SettlementGenerationRequest,
        db_session: Optional[Session] = None
    ) -> MapGenerationResponse:
        """Generate a settlement map (town/city)."""
        
        start_time = datetime.utcnow()
        
        try:
            # Set random seed
            if request.seed:
                random.seed(request.seed)
                np.random.seed(hash(request.seed) % 2**32)
            
            # Determine dimensions based on settlement type
            size_map = {
                SettlementType.HAMLET: (20, 20),
                SettlementType.VILLAGE: (30, 30),
                SettlementType.TOWN: (50, 50),
                SettlementType.CITY: (80, 80),
                SettlementType.METROPOLIS: (120, 120)
            }
            
            default_width, default_height = size_map.get(request.settlement_type, (50, 50))
            width = request.width or default_width
            height = request.height or default_height
            
            # Determine population
            population_map = {
                SettlementType.HAMLET: (20, 100),
                SettlementType.VILLAGE: (100, 1000),
                SettlementType.TOWN: (1000, 5000),
                SettlementType.CITY: (5000, 25000),
                SettlementType.METROPOLIS: (25000, 100000)
            }
            
            min_pop, max_pop = population_map.get(request.settlement_type, (1000, 5000))
            population = request.population or random.randint(min_pop, max_pop)
            
            # Initialize tile grid
            tiles = [[Tile(tile_type=TileType.GRASS) for _ in range(width)] for _ in range(height)]
            
            # Generate settlement layout
            districts = await self._generate_districts(width, height, request.settlement_type, request.districts)
            roads = await self._generate_road_network(width, height, request.road_layout, districts)
            buildings = await self._generate_buildings(width, height, districts, population, request.special_buildings)
            
            # Apply to tile grid
            # Roads first
            for road in roads:
                for coord in road:
                    if 0 <= coord.x < width and 0 <= coord.y < height:
                        tiles[coord.y][coord.x] = Tile(tile_type=TileType.ROAD)
            
            # Then buildings
            for building in buildings:
                for coord in building.get("coordinates", []):
                    if 0 <= coord.x < width and 0 <= coord.y < height:
                        tiles[coord.y][coord.x] = Tile(tile_type=TileType.BUILDING)
            
            # Add walls if requested
            gates = []
            if request.has_walls:
                gates = await self._generate_walls_and_gates(width, height, tiles)
            
            # Create settlement map
            settlement_map = SettlementMap(
                name=request.name or f"Generated {request.settlement_type.value.title()}",
                map_type=MapType.TOWN,
                settlement_type=request.settlement_type,
                width=width,
                height=height,
                tiles=tiles,
                population=population,
                districts=districts,
                buildings=buildings,
                roads=roads,
                walls=request.has_walls,
                gates=gates,
                generation_seed=request.seed
            )
            
            # Generate preview
            preview_url = await self._generate_map_image(settlement_map)
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            return MapGenerationResponse(
                success=True,
                map_data=settlement_map,
                preview_url=preview_url,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error generating settlement: {e}")
            return MapGenerationResponse(
                success=False,
                message=f"Failed to generate settlement: {str(e)}",
                errors=[str(e)]
            )

    async def generate_region(
        self,
        request: RegionGenerationRequest,
        db_session: Optional[Session] = None
    ) -> MapGenerationResponse:
        """Generate a region map with biomes and settlements."""
        
        start_time = datetime.utcnow()
        
        try:
            if request.seed:
                random.seed(request.seed)
                np.random.seed(hash(request.seed) % 2**32)
            
            width = request.width or 100
            height = request.height or 100
            
            # Generate terrain using Perlin noise
            tiles = await self._generate_terrain(width, height, request.primary_biome, request.secondary_biomes)
            
            # Generate settlements
            settlements = await self._generate_region_settlements(
                width, height, request.settlement_density, tiles
            )
            
            # Generate trade routes
            trade_routes = await self._generate_trade_routes(settlements)
            
            # Generate points of interest
            poi_list = await self._generate_points_of_interest(
                width, height, request.points_of_interest, tiles
            )
            
            # Create biome distribution
            biome_distribution = await self._analyze_biome_distribution(tiles)
            
            region_map = RegionMap(
                name=request.name or "Generated Region",
                map_type=MapType.REGION,
                width=width,
                height=height,
                tiles=tiles,
                biome_distribution=biome_distribution,
                settlements=settlements,
                trade_routes=trade_routes,
                points_of_interest=poi_list,
                generation_seed=request.seed
            )
            
            preview_url = await self._generate_map_image(region_map)
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            return MapGenerationResponse(
                success=True,
                map_data=region_map,
                preview_url=preview_url,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error generating region: {e}")
            return MapGenerationResponse(
                success=False,
                message=f"Failed to generate region: {str(e)}",
                errors=[str(e)]
            )

    async def generate_world(
        self,
        request: WorldGenerationRequest,
        db_session: Optional[Session] = None
    ) -> MapGenerationResponse:
        """Generate a world map with continents and oceans."""
        
        start_time = datetime.utcnow()
        
        try:
            if request.seed:
                random.seed(request.seed)
                np.random.seed(hash(request.seed) % 2**32)
            
            width = request.width or 512
            height = request.height or 512
            
            # Generate base heightmap
            heightmap = await self._generate_heightmap(width, height)
            
            # Generate continents and islands
            continents, landmask = await self._generate_continents(
                width, height, heightmap, request.continent_count, request.landmass_ratio
            )
            
            # Generate climate zones
            climate_zones = await self._generate_climate_zones(
                width, height, landmask, request.climate_variation
            )
            
            # Generate biomes based on climate
            tiles = await self._generate_world_biomes(width, height, landmask, climate_zones)
            
            # Generate major regions
            major_regions = await self._identify_major_regions(tiles, continents)
            
            # Generate sea routes
            sea_routes = await self._generate_sea_routes(width, height, landmask, continents)
            
            world_map = WorldMap(
                name=request.name or "Generated World",
                map_type=MapType.WORLD,
                width=width,
                height=height,
                tiles=tiles,
                continents=continents,
                climate_zones=climate_zones,
                major_regions=major_regions,
                sea_routes=sea_routes,
                generation_seed=request.seed
            )
            
            preview_url = await self._generate_map_image(world_map)
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            return MapGenerationResponse(
                success=True,
                map_data=world_map,
                preview_url=preview_url,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error generating world: {e}")
            return MapGenerationResponse(
                success=False,
                message=f"Failed to generate world: {str(e)}",
                errors=[str(e)]
            )

    async def analyze_map(self, map_data: MapSchema) -> MapAnalysis:
        """Analyze map properties and generate metrics."""
        
        connectivity_score = await self._calculate_connectivity(map_data)
        balance_score = await self._calculate_balance(map_data)
        complexity_score = await self._calculate_complexity(map_data)
        
        # Find bottlenecks and dead ends
        bottlenecks = await self._find_bottlenecks(map_data)
        dead_ends = await self._find_dead_ends(map_data)
        
        # Analyze area coverage
        area_coverage = await self._calculate_area_coverage(map_data)
        
        return MapAnalysis(
            map_id=map_data.id or "unknown",
            connectivity_score=connectivity_score,
            balance_score=balance_score,
            complexity_score=complexity_score,
            bottlenecks=bottlenecks,
            dead_ends=dead_ends,
            area_coverage=area_coverage
        )

    async def find_path(self, request: PathfindingRequest) -> PathfindingResponse:
        """Find path between two points on a map."""
        
        start_time = datetime.utcnow()
        
        # In a real implementation, would load map from database
        # For now, return mock pathfinding result
        
        path = [request.start, request.end]  # Simple direct path
        distance = math.sqrt(
            (request.end.x - request.start.x)**2 + 
            (request.end.y - request.start.y)**2
        )
        
        computation_time = (datetime.utcnow() - start_time).total_seconds()
        
        return PathfindingResponse(
            path=path,
            distance=distance,
            cost=distance,
            found=True,
            algorithm_used=request.algorithm,
            computation_time=computation_time
        )

    # Helper methods for dungeon generation
    async def _generate_dungeon_level(
        self,
        level: int,
        width: int,
        height: int,
        request: DungeonGenerationRequest
    ) -> DungeonLevel:
        """Generate a single dungeon level."""
        
        room_count = request.room_count or random.randint(5, 12)
        rooms = []
        
        # Generate rooms
        for i in range(room_count):
            room = await self._generate_room(i, width, height, request)
            if room:
                rooms.append(room)
        
        # Generate corridors connecting rooms
        corridors = await self._generate_corridors(rooms, width, height)
        
        # Add special features
        special_features = {}
        if request.include_boss_room and level == request.levels:
            special_features["boss_room"] = rooms[-1].id if rooms else None
        
        return DungeonLevel(
            level=level,
            rooms=rooms,
            corridors=corridors,
            special_features=special_features,
            theme=request.theme,
            difficulty=request.difficulty
        )

    async def _generate_room(
        self,
        room_id: int,
        map_width: int,
        map_height: int,
        request: DungeonGenerationRequest
    ) -> Optional[Room]:
        """Generate a single room."""
        
        max_attempts = 50
        
        for _ in range(max_attempts):
            # Random room size
            width = random.randint(3, 8)
            height = random.randint(3, 8)
            
            # Random position
            x = random.randint(1, map_width - width - 1)
            y = random.randint(1, map_height - height - 1)
            
            # Create room coordinates
            coordinates = []
            for rx in range(x, x + width):
                for ry in range(y, y + height):
                    coordinates.append(Coordinate(x=rx, y=ry))
            
            center = Coordinate(x=x + width // 2, y=y + height // 2)
            
            # Determine room type
            room_type = self._determine_room_type(room_id, request)
            
            return Room(
                id=f"room_{room_id}",
                room_type=room_type,
                coordinates=coordinates,
                center=center,
                width=width,
                height=height
            )
        
        return None

    def _determine_room_type(self, room_id: int, request: DungeonGenerationRequest) -> RoomType:
        """Determine the type of room to generate."""
        
        if room_id == 0:
            return RoomType.ENTRANCE
        
        # Random room type based on theme and preferences
        room_types = [RoomType.CHAMBER, RoomType.CHAMBER, RoomType.CHAMBER]  # Chambers are common
        
        if request.include_treasure_rooms and random.random() < 0.2:
            room_types.append(RoomType.TREASURE_ROOM)
        
        if random.random() < request.secret_room_chance:
            room_types.append(RoomType.SECRET_ROOM)
        
        return random.choice(room_types)

    async def _generate_corridors(
        self,
        rooms: List[Room],
        width: int,
        height: int
    ) -> List[List[Coordinate]]:
        """Generate corridors connecting rooms."""
        
        corridors = []
        
        if len(rooms) < 2:
            return corridors
        
        # Connect each room to at least one other room
        for i, room in enumerate(rooms):
            if i == 0:
                continue  # Skip first room
            
            # Connect to previous room
            prev_room = rooms[i - 1]
            corridor = await self._create_corridor(room.center, prev_room.center)
            if corridor:
                corridors.append(corridor)
        
        return corridors

    async def _create_corridor(self, start: Coordinate, end: Coordinate) -> List[Coordinate]:
        """Create a corridor between two points."""
        
        corridor = []
        
        # L-shaped corridor
        # First go horizontally
        current_x = start.x
        while current_x != end.x:
            corridor.append(Coordinate(x=current_x, y=start.y))
            current_x += 1 if end.x > start.x else -1
        
        # Then go vertically
        current_y = start.y
        while current_y != end.y:
            corridor.append(Coordinate(x=end.x, y=current_y))
            current_y += 1 if end.y > start.y else -1
        
        return corridor

    # Helper methods for settlement generation
    async def _generate_districts(
        self,
        width: int,
        height: int,
        settlement_type: SettlementType,
        requested_districts: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate districts for a settlement."""
        
        districts = []
        district_types = requested_districts or ["residential", "commercial"]
        
        if settlement_type in [SettlementType.CITY, SettlementType.METROPOLIS]:
            district_types.extend(["noble", "temple"])
        
        # Simple district generation - divide map into quadrants
        district_size_x = width // 2
        district_size_y = height // 2
        
        for i, district_type in enumerate(district_types[:4]):  # Max 4 districts for simplicity
            x_offset = (i % 2) * district_size_x
            y_offset = (i // 2) * district_size_y
            
            districts.append({
                "name": f"{district_type.title()} District",
                "type": district_type,
                "bounds": {
                    "x": x_offset,
                    "y": y_offset,
                    "width": district_size_x,
                    "height": district_size_y
                }
            })
        
        return districts

    async def _generate_road_network(
        self,
        width: int,
        height: int,
        layout: str,
        districts: List[Dict[str, Any]]
    ) -> List[List[Coordinate]]:
        """Generate road network for settlement."""
        
        roads = []
        
        if layout == "grid":
            # Grid layout - horizontal and vertical roads
            for x in range(0, width, 10):
                road = [Coordinate(x=x, y=y) for y in range(height)]
                roads.append(road)
            
            for y in range(0, height, 10):
                road = [Coordinate(x=x, y=y) for x in range(width)]
                roads.append(road)
        
        else:  # organic layout
            # Main roads connecting districts
            center_x, center_y = width // 2, height // 2
            
            # Roads to each district
            for district in districts:
                bounds = district["bounds"]
                district_center_x = bounds["x"] + bounds["width"] // 2
                district_center_y = bounds["y"] + bounds["height"] // 2
                
                # Simple path from center to district
                road = await self._create_corridor(
                    Coordinate(x=center_x, y=center_y),
                    Coordinate(x=district_center_x, y=district_center_y)
                )
                if road:
                    roads.append(road)
        
        return roads

    async def _generate_buildings(
        self,
        width: int,
        height: int,
        districts: List[Dict[str, Any]],
        population: int,
        special_buildings: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate buildings for settlement."""
        
        buildings = []
        building_count = max(10, population // 50)  # Rough estimate
        
        for district in districts:
            district_type = district["type"]
            bounds = district["bounds"]
            
            # Generate buildings in this district
            district_building_count = building_count // len(districts)
            
            for _ in range(district_building_count):
                # Random position within district
                x = random.randint(bounds["x"], bounds["x"] + bounds["width"] - 3)
                y = random.randint(bounds["y"], bounds["y"] + bounds["height"] - 3)
                
                # Small building size
                bwidth = random.randint(2, 4)
                bheight = random.randint(2, 4)
                
                coordinates = []
                for bx in range(x, x + bwidth):
                    for by in range(y, y + bheight):
                        if bx < width and by < height:
                            coordinates.append(Coordinate(x=bx, y=by))
                
                building_type = self._determine_building_type(district_type)
                
                buildings.append({
                    "type": building_type,
                    "coordinates": coordinates,
                    "district": district["name"],
                    "size": {"width": bwidth, "height": bheight}
                })
        
        return buildings

    def _determine_building_type(self, district_type: str) -> str:
        """Determine building type based on district."""
        
        building_types = {
            "residential": ["house", "apartment", "cottage"],
            "commercial": ["shop", "market", "warehouse"],
            "noble": ["mansion", "estate", "manor"],
            "temple": ["temple", "shrine", "monastery"],
            "industrial": ["forge", "mill", "workshop"]
        }
        
        return random.choice(building_types.get(district_type, ["building"]))

    async def _generate_walls_and_gates(
        self,
        width: int,
        height: int,
        tiles: List[List[Tile]]
    ) -> List[Coordinate]:
        """Generate walls around settlement and return gate positions."""
        
        gates = []
        
        # Simple rectangular wall
        wall_margin = 2
        
        # Top and bottom walls
        for x in range(wall_margin, width - wall_margin):
            tiles[wall_margin][x] = Tile(tile_type=TileType.WALL)
            tiles[height - wall_margin - 1][x] = Tile(tile_type=TileType.WALL)
        
        # Left and right walls
        for y in range(wall_margin, height - wall_margin):
            tiles[y][wall_margin] = Tile(tile_type=TileType.WALL)
            tiles[y][width - wall_margin - 1] = Tile(tile_type=TileType.WALL)
        
        # Add gates
        gate_positions = [
            (width // 2, wall_margin),  # North gate
            (width // 2, height - wall_margin - 1),  # South gate
            (wall_margin, height // 2),  # West gate
            (width - wall_margin - 1, height // 2)  # East gate
        ]
        
        for gate_x, gate_y in gate_positions:
            if 0 <= gate_x < width and 0 <= gate_y < height:
                tiles[gate_y][gate_x] = Tile(tile_type=TileType.DOOR)
                gates.append(Coordinate(x=gate_x, y=gate_y))
        
        return gates

    # Helper methods for terrain generation
    async def _generate_terrain(
        self,
        width: int,
        height: int,
        primary_biome: BiomeType,
        secondary_biomes: List[BiomeType]
    ) -> List[List[Tile]]:
        """Generate terrain using Perlin noise."""
        
        tiles = []
        scale = 0.1
        
        for y in range(height):
            row = []
            for x in range(width):
                # Generate base noise
                noise_val = pnoise2(x * scale, y * scale, octaves=4)
                
                # Determine biome based on noise value
                if noise_val > 0.3:
                    biome = BiomeType.MOUNTAINS
                elif noise_val > 0.1:
                    biome = primary_biome
                elif noise_val > -0.1:
                    biome = secondary_biomes[0] if secondary_biomes else primary_biome
                else:
                    biome = BiomeType.WATER
                
                # Convert biome to tile type
                tile_type = self._biome_to_tile_type(biome)
                row.append(Tile(tile_type=tile_type))
            
            tiles.append(row)
        
        return tiles

    def _biome_to_tile_type(self, biome: BiomeType) -> TileType:
        """Convert biome to tile type."""
        
        biome_mapping = {
            BiomeType.TEMPERATE_FOREST: TileType.FOREST,
            BiomeType.TROPICAL_FOREST: TileType.FOREST,
            BiomeType.GRASSLAND: TileType.GRASS,
            BiomeType.DESERT: TileType.DESERT,
            BiomeType.SWAMP: TileType.SWAMP,
            BiomeType.MOUNTAINS: TileType.MOUNTAIN,
            BiomeType.HILLS: TileType.GRASS,
            BiomeType.OCEAN: TileType.WATER,
            BiomeType.LAKE: TileType.WATER,
            BiomeType.RIVER: TileType.WATER
        }
        
        return biome_mapping.get(biome, TileType.GRASS)

    async def _generate_region_settlements(
        self,
        width: int,
        height: int,
        density: float,
        tiles: List[List[Tile]]
    ) -> List[Dict[str, Any]]:
        """Generate settlements for a region."""
        
        settlements = []
        settlement_count = int(width * height * density / 1000)  # Rough calculation
        
        for _ in range(settlement_count):
            # Find suitable location (not water or mountain)
            attempts = 0
            while attempts < 50:
                x = random.randint(0, width - 1)
                y = random.randint(0, height - 1)
                
                tile = tiles[y][x]
                if tile.tile_type not in [TileType.WATER, TileType.MOUNTAIN]:
                    settlement_type = random.choice(list(SettlementType))
                    
                    settlements.append({
                        "name": f"Settlement {len(settlements) + 1}",
                        "type": settlement_type.value,
                        "position": {"x": x, "y": y},
                        "population": random.randint(50, 5000)
                    })
                    break
                
                attempts += 1
        
        return settlements

    async def _generate_trade_routes(
        self,
        settlements: List[Dict[str, Any]]
    ) -> List[List[Coordinate]]:
        """Generate trade routes between settlements."""
        
        routes = []
        
        # Connect each settlement to nearest neighbor
        for i, settlement in enumerate(settlements):
            if i == 0:
                continue
            
            start_pos = settlement["position"]
            end_pos = settlements[i - 1]["position"]
            
            route = await self._create_corridor(
                Coordinate(x=start_pos["x"], y=start_pos["y"]),
                Coordinate(x=end_pos["x"], y=end_pos["y"])
            )
            
            if route:
                routes.append(route)
        
        return routes

    async def _generate_points_of_interest(
        self,
        width: int,
        height: int,
        count: int,
        tiles: List[List[Tile]]
    ) -> List[Dict[str, Any]]:
        """Generate points of interest for a region."""
        
        poi_types = [
            "Ancient Ruins", "Dragon Lair", "Haunted Forest", "Magic Spring",
            "Bandit Camp", "Hidden Temple", "Mysterious Cave", "Old Battlefield"
        ]
        
        points = []
        
        for _ in range(count):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            
            poi_type = random.choice(poi_types)
            
            points.append({
                "name": f"{poi_type} #{len(points) + 1}",
                "type": poi_type,
                "position": {"x": x, "y": y},
                "discovered": False
            })
        
        return points

    async def _analyze_biome_distribution(
        self,
        tiles: List[List[Tile]]
    ) -> Dict[BiomeType, float]:
        """Analyze the distribution of biomes in the map."""
        
        biome_counts = {}
        total_tiles = 0
        
        for row in tiles:
            for tile in row:
                biome = self._tile_type_to_biome(tile.tile_type)
                biome_counts[biome] = biome_counts.get(biome, 0) + 1
                total_tiles += 1
        
        # Convert to percentages
        distribution = {}
        for biome, count in biome_counts.items():
            distribution[biome] = count / total_tiles if total_tiles > 0 else 0
        
        return distribution

    def _tile_type_to_biome(self, tile_type: TileType) -> BiomeType:
        """Convert tile type back to biome."""
        
        tile_to_biome = {
            TileType.FOREST: BiomeType.TEMPERATE_FOREST,
            TileType.GRASS: BiomeType.GRASSLAND,
            TileType.DESERT: BiomeType.DESERT,
            TileType.SWAMP: BiomeType.SWAMP,
            TileType.MOUNTAIN: BiomeType.MOUNTAINS,
            TileType.WATER: BiomeType.OCEAN
        }
        
        return tile_to_biome.get(tile_type, BiomeType.GRASSLAND)

    # World generation helpers
    async def _generate_heightmap(self, width: int, height: int) -> np.ndarray:
        """Generate heightmap for world generation."""
        
        heightmap = np.zeros((height, width))
        
        for y in range(height):
            for x in range(width):
                # Multiple octaves of noise for realistic terrain
                height_val = (
                    pnoise2(x * 0.01, y * 0.01, octaves=1) * 0.5 +
                    pnoise2(x * 0.02, y * 0.02, octaves=2) * 0.25 +
                    pnoise2(x * 0.04, y * 0.04, octaves=4) * 0.125
                )
                heightmap[y, x] = height_val
        
        return heightmap

    async def _generate_continents(
        self,
        width: int,
        height: int,
        heightmap: np.ndarray,
        continent_count: int,
        landmass_ratio: float
    ) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """Generate continents and return landmask."""
        
        # Threshold heightmap to create land/sea
        sea_level = np.percentile(heightmap, (1 - landmass_ratio) * 100)
        landmask = heightmap > sea_level
        
        # Identify continent regions (simplified)
        continents = []
        for i in range(continent_count):
            # Find a random land point for continent center
            land_points = np.where(landmask)
            if len(land_points[0]) > 0:
                idx = random.randint(0, len(land_points[0]) - 1)
                center_y, center_x = land_points[0][idx], land_points[1][idx]
                
                continents.append({
                    "id": f"continent_{i + 1}",
                    "name": f"Continent {i + 1}",
                    "center": {"x": int(center_x), "y": int(center_y)},
                    "area": random.randint(1000, 10000)  # Mock area
                })
        
        return continents, landmask

    async def _generate_climate_zones(
        self,
        width: int,
        height: int,
        landmask: np.ndarray,
        climate_variation: float
    ) -> List[Dict[str, Any]]:
        """Generate climate zones based on latitude and other factors."""
        
        zones = []
        
        # Simple latitude-based climate zones
        zone_height = height // 5
        
        climate_types = ["arctic", "temperate", "subtropical", "tropical", "desert"]
        
        for i, climate in enumerate(climate_types):
            y_start = i * zone_height
            y_end = min((i + 1) * zone_height, height)
            
            zones.append({
                "climate": climate,
                "bounds": {
                    "y_start": y_start,
                    "y_end": y_end,
                    "x_start": 0,
                    "x_end": width
                },
                "temperature_range": self._get_climate_temperature_range(climate)
            })
        
        return zones

    def _get_climate_temperature_range(self, climate: str) -> Tuple[int, int]:
        """Get temperature range for climate type."""
        
        ranges = {
            "arctic": (-30, 10),
            "temperate": (-10, 30),
            "subtropical": (10, 35),
            "tropical": (20, 40),
            "desert": (0, 50)
        }
        
        return ranges.get(climate, (0, 25))

    async def _generate_world_biomes(
        self,
        width: int,
        height: int,
        landmask: np.ndarray,
        climate_zones: List[Dict[str, Any]]
    ) -> List[List[Tile]]:
        """Generate biomes for world map based on climate and terrain."""
        
        tiles = []
        
        for y in range(height):
            row = []
            for x in range(width):
                if not landmask[y, x]:
                    # Water tile
                    row.append(Tile(tile_type=TileType.WATER))
                else:
                    # Determine climate zone
                    climate = self._get_climate_at_position(y, climate_zones)
                    
                    # Generate biome based on climate and local factors
                    biome = self._generate_biome_for_climate(climate, x, y)
                    tile_type = self._biome_to_tile_type(biome)
                    
                    row.append(Tile(tile_type=tile_type))
            
            tiles.append(row)
        
        return tiles

    def _get_climate_at_position(self, y: int, climate_zones: List[Dict[str, Any]]) -> str:
        """Get climate type at given y position."""
        
        for zone in climate_zones:
            bounds = zone["bounds"]
            if bounds["y_start"] <= y < bounds["y_end"]:
                return zone["climate"]
        
        return "temperate"  # Default

    def _generate_biome_for_climate(self, climate: str, x: int, y: int) -> BiomeType:
        """Generate appropriate biome for climate zone."""
        
        climate_biomes = {
            "arctic": [BiomeType.ARCTIC, BiomeType.TUNDRA],
            "temperate": [BiomeType.TEMPERATE_FOREST, BiomeType.GRASSLAND, BiomeType.HILLS],
            "subtropical": [BiomeType.TEMPERATE_FOREST, BiomeType.GRASSLAND],
            "tropical": [BiomeType.TROPICAL_FOREST, BiomeType.GRASSLAND],
            "desert": [BiomeType.DESERT]
        }
        
        possible_biomes = climate_biomes.get(climate, [BiomeType.GRASSLAND])
        return random.choice(possible_biomes)

    async def _identify_major_regions(
        self,
        tiles: List[List[Tile]],
        continents: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify major geographic regions."""
        
        regions = []
        
        for continent in continents:
            continent_name = continent["name"]
            
            # Generate region names for each continent
            region_types = ["Northern", "Southern", "Eastern", "Western", "Central"]
            
            for region_type in region_types[:3]:  # Max 3 regions per continent
                regions.append(f"{region_type} {continent_name}")
        
        return regions

    async def _generate_sea_routes(
        self,
        width: int,
        height: int,
        landmask: np.ndarray,
        continents: List[Dict[str, Any]]
    ) -> List[List[Coordinate]]:
        """Generate sea trade routes between continents."""
        
        routes = []
        
        # Connect continents with sea routes
        for i in range(len(continents) - 1):
            start_continent = continents[i]
            end_continent = continents[i + 1]
            
            start_pos = start_continent["center"]
            end_pos = end_continent["center"]
            
            # Simple route (should check for water tiles in real implementation)
            route = await self._create_corridor(
                Coordinate(x=start_pos["x"], y=start_pos["y"]),
                Coordinate(x=end_pos["x"], y=end_pos["y"])
            )
            
            if route:
                routes.append(route)
        
        return routes

    # Analysis helper methods
    async def _calculate_connectivity(self, map_data: MapSchema) -> float:
        """Calculate connectivity score for the map."""
        # Simplified connectivity calculation
        return 0.75  # Mock score

    async def _calculate_balance(self, map_data: MapSchema) -> float:
        """Calculate balance score for the map."""
        return 0.80  # Mock score

    async def _calculate_complexity(self, map_data: MapSchema) -> float:
        """Calculate complexity score for the map."""
        return 0.65  # Mock score

    async def _find_bottlenecks(self, map_data: MapSchema) -> List[Coordinate]:
        """Find bottleneck points in the map."""
        return []  # Mock result

    async def _find_dead_ends(self, map_data: MapSchema) -> List[Coordinate]:
        """Find dead end points in the map."""
        return []  # Mock result

    async def _calculate_area_coverage(self, map_data: MapSchema) -> Dict[TileType, float]:
        """Calculate area coverage by tile type."""
        
        coverage = {}
        total_tiles = 0
        
        for row in map_data.tiles:
            for tile in row:
                if isinstance(tile, str):
                    tile_type = TileType(tile)
                else:
                    tile_type = tile.tile_type
                
                coverage[tile_type] = coverage.get(tile_type, 0) + 1
                total_tiles += 1
        
        # Convert to percentages
        for tile_type in coverage:
            coverage[tile_type] /= total_tiles
        
        return coverage

    # Image generation
    async def _generate_map_image(self, map_data: MapSchema) -> Optional[str]:
        """Generate a preview image for the map."""
        
        try:
            width, height = map_data.width, map_data.height
            
            # Create image
            img = Image.new('RGB', (width * 4, height * 4), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw tiles
            for y, row in enumerate(map_data.tiles):
                for x, tile in enumerate(row):
                    if isinstance(tile, str):
                        tile_type = TileType(tile)
                    else:
                        tile_type = tile.tile_type
                    
                    color = self.tile_colors.get(tile_type, (128, 128, 128))
                    
                    # Draw 4x4 pixel tile
                    draw.rectangle([x*4, y*4, x*4+3, y*4+3], fill=color)
            
            # Save to temporary location (in real implementation, save to proper storage)
            image_path = f"/tmp/map_{map_data.id or 'temp'}_{datetime.now().timestamp()}.png"
            img.save(image_path)
            
            return image_path
            
        except Exception as e:
            logger.error(f"Error generating map image: {e}")
            return None