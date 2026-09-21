import asyncio
import asyncpg
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from datetime import datetime
import math


class PartCategory(Enum):
    FASTENERS = "fasteners"
    GEARS = "gears"
    ELECTRONICS = "electronics"
    STRUCTURAL = "structural"
    TOOLS = "tools"
    SENSORS = "sensors"
    ACTUATORS = "actuators"
    DECORATIVE = "decorative"
    RAW_MATERIALS = "raw_materials"
    CUSTOM = "custom"


class PartSize(Enum):
    MICRO = "micro"      # < 1mm
    TINY = "tiny"        # 1-5mm
    SMALL = "small"      # 5-25mm
    MEDIUM = "medium"    # 25-100mm
    LARGE = "large"      # 100-500mm
    HUGE = "huge"        # > 500mm


class MaterialType(Enum):
    METAL_STEEL = "steel"
    METAL_ALUMINUM = "aluminum"
    METAL_COPPER = "copper"
    METAL_BRASS = "brass"
    PLASTIC_ABS = "abs_plastic"
    PLASTIC_PLA = "pla_plastic"
    PLASTIC_NYLON = "nylon"
    WOOD_PINE = "pine"
    WOOD_OAK = "oak"
    WOOD_PLYWOOD = "plywood"
    RUBBER = "rubber"
    CERAMIC = "ceramic"
    GLASS = "glass"
    FABRIC = "fabric"
    PAPER = "paper"


@dataclass
class PartSpecification:
    part_id: str
    name: str
    description: str
    category: PartCategory
    size_category: PartSize
    material: MaterialType
    dimensions: Tuple[float, float, float]  # length, width, height in meters
    mass: float  # in kg
    color: str
    mesh_file: str
    texture_file: Optional[str]
    icon_file: str
    educational_info: Dict[str, Any]
    properties: Dict[str, Any]  # Specific properties like thread pitch, resistance, etc.
    compatibility: List[str]    # Compatible part IDs
    tags: List[str]
    cost_virtual: int          # Virtual currency cost
    rarity: int               # 1-5, 5 being rarest
    unlock_level: int         # Required user level
    is_tool: bool = False
    is_consumable: bool = False


@dataclass
class PartInstance:
    instance_id: str
    part_id: str
    owner_user_id: str
    quantity: int
    condition: float  # 0.0 to 1.0, 1.0 being perfect
    location: str     # "inventory", "project_<id>", "workspace"
    position: Optional[Tuple[float, float, float]] = None
    rotation: Optional[Tuple[float, float, float, float]] = None  # Quaternion
    last_used: Optional[datetime] = None
    custom_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PartsCollection:
    collection_id: str
    name: str
    description: str
    part_instances: List[PartInstance]
    tags: List[str]
    is_public: bool
    created_by: str
    created_at: datetime


class VirtualPartsManager:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.part_catalog: Dict[str, PartSpecification] = {}
        self.user_inventories: Dict[str, List[PartInstance]] = {}
        self.part_search_index: Dict[str, Set[str]] = {}
        
    async def initialize_tables(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS part_specifications (
                    id SERIAL PRIMARY KEY,
                    part_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    category VARCHAR(50) NOT NULL,
                    size_category VARCHAR(20) NOT NULL,
                    material VARCHAR(50) NOT NULL,
                    dimensions JSONB NOT NULL,
                    mass FLOAT NOT NULL,
                    color VARCHAR(50) NOT NULL,
                    mesh_file VARCHAR(200) NOT NULL,
                    texture_file VARCHAR(200),
                    icon_file VARCHAR(200) NOT NULL,
                    educational_info JSONB DEFAULT '{}',
                    properties JSONB DEFAULT '{}',
                    compatibility JSONB DEFAULT '[]',
                    tags JSONB DEFAULT '[]',
                    cost_virtual INTEGER DEFAULT 10,
                    rarity INTEGER DEFAULT 1,
                    unlock_level INTEGER DEFAULT 1,
                    is_tool BOOLEAN DEFAULT FALSE,
                    is_consumable BOOLEAN DEFAULT FALSE,
                    is_available BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_part_inventory (
                    id SERIAL PRIMARY KEY,
                    instance_id VARCHAR(50) UNIQUE NOT NULL,
                    part_id VARCHAR(50) NOT NULL,
                    owner_user_id VARCHAR(50) NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    condition FLOAT DEFAULT 1.0,
                    location VARCHAR(100) DEFAULT 'inventory',
                    position JSONB,
                    rotation JSONB,
                    last_used TIMESTAMP,
                    custom_properties JSONB DEFAULT '{}',
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS parts_collections (
                    id SERIAL PRIMARY KEY,
                    collection_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    part_instances JSONB NOT NULL,
                    tags JSONB DEFAULT '[]',
                    is_public BOOLEAN DEFAULT FALSE,
                    created_by VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS part_usage_history (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    part_id VARCHAR(50) NOT NULL,
                    project_id VARCHAR(50),
                    usage_type VARCHAR(50) NOT NULL,
                    usage_duration INTEGER,
                    learned_something BOOLEAN DEFAULT FALSE,
                    notes TEXT,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        # Initialize default parts catalog
        await self.initialize_default_parts()
        await self.build_search_index()

    async def initialize_default_parts(self):
        """Initialize the default parts catalog with common components"""
        default_parts = [
            # Fasteners
            PartSpecification(
                part_id="screw_m3_10mm",
                name="M3x10mm Machine Screw",
                description="Standard metric machine screw with Phillips head",
                category=PartCategory.FASTENERS,
                size_category=PartSize.TINY,
                material=MaterialType.METAL_STEEL,
                dimensions=(0.01, 0.003, 0.003),
                mass=0.001,
                color="silver",
                mesh_file="meshes/fasteners/screw_m3_10mm.obj",
                texture_file="textures/steel_brushed.jpg",
                icon_file="icons/screw.svg",
                educational_info={
                    "purpose": "Joins parts together with threaded connection",
                    "how_to_use": "Turn clockwise to tighten, counterclockwise to loosen",
                    "thread_pitch": "0.5mm",
                    "material_strength": "High tensile strength steel",
                    "applications": ["Electronics enclosures", "Mechanical assemblies", "Furniture"]
                },
                properties={
                    "thread_pitch": 0.0005,
                    "head_type": "phillips",
                    "tensile_strength": 400,  # MPa
                    "hardness": "HRC 25-35"
                },
                compatibility=["nut_m3", "washer_m3", "threaded_hole_m3"],
                tags=["fastener", "screw", "metric", "steel", "phillips"],
                cost_virtual=2,
                rarity=1,
                unlock_level=1,
                is_consumable=True
            ),
            
            PartSpecification(
                part_id="nut_m3_hex",
                name="M3 Hex Nut",
                description="Hexagonal nut for M3 screws",
                category=PartCategory.FASTENERS,
                size_category=PartSize.TINY,
                material=MaterialType.METAL_STEEL,
                dimensions=(0.0055, 0.0055, 0.0024),
                mass=0.0003,
                color="silver",
                mesh_file="meshes/fasteners/nut_m3_hex.obj",
                texture_file="textures/steel_brushed.jpg",
                icon_file="icons/nut.svg",
                educational_info={
                    "purpose": "Provides threaded hole to receive screws",
                    "how_to_use": "Thread onto screw and tighten with wrench",
                    "why_hexagonal": "Six sides provide good grip for tools and distribute stress evenly",
                    "material_properties": "Same material as screw for compatibility"
                },
                properties={
                    "thread_pitch": 0.0005,
                    "across_flats": 0.0055,
                    "thickness": 0.0024
                },
                compatibility=["screw_m3_10mm", "screw_m3_16mm", "washer_m3"],
                tags=["fastener", "nut", "metric", "hexagonal"],
                cost_virtual=1,
                rarity=1,
                unlock_level=1
            ),
            
            # Gears
            PartSpecification(
                part_id="gear_spur_20t_mod1",
                name="20-Tooth Spur Gear (Module 1)",
                description="Plastic spur gear with 20 teeth, module 1 for basic gear trains",
                category=PartCategory.GEARS,
                size_category=PartSize.SMALL,
                material=MaterialType.PLASTIC_ABS,
                dimensions=(0.022, 0.022, 0.005),
                mass=0.003,
                color="white",
                mesh_file="meshes/gears/spur_20t_mod1.obj",
                texture_file="textures/plastic_white.jpg",
                icon_file="icons/gear.svg",
                educational_info={
                    "purpose": "Transmits rotational motion and changes speed/torque",
                    "gear_ratio": "Speed ratio inversely proportional to tooth count ratio",
                    "module_explained": "Module = pitch diameter / number of teeth",
                    "why_involute_teeth": "Involute gear teeth provide smooth, efficient power transmission",
                    "applications": ["Clockwork", "Car transmissions", "Mechanical calculators"]
                },
                properties={
                    "teeth_count": 20,
                    "module": 1.0,
                    "pressure_angle": 20,  # degrees
                    "pitch_diameter": 20,   # mm
                    "face_width": 5,        # mm
                    "bore_diameter": 6      # mm
                },
                compatibility=["gear_spur_40t_mod1", "axle_6mm", "gear_rack_mod1"],
                tags=["gear", "spur", "transmission", "mechanical", "plastic"],
                cost_virtual=8,
                rarity=2,
                unlock_level=2
            ),
            
            # Electronics
            PartSpecification(
                part_id="resistor_1k_1_4w",
                name="1kΩ Resistor (1/4W)",
                description="Carbon film resistor, 1000 ohms, 1/4 watt power rating",
                category=PartCategory.ELECTRONICS,
                size_category=PartSize.TINY,
                material=MaterialType.CERAMIC,
                dimensions=(0.0065, 0.002, 0.002),
                mass=0.0001,
                color="beige",
                mesh_file="meshes/electronics/resistor_1_4w.obj",
                texture_file="textures/resistor_1k.jpg",
                icon_file="icons/resistor.svg",
                educational_info={
                    "purpose": "Limits electrical current flow according to Ohm's Law (V = I × R)",
                    "color_code": "Brown-Black-Red = 1000 ohms",
                    "ohms_law": "Voltage = Current × Resistance",
                    "power_dissipation": "Power = Voltage² / Resistance",
                    "why_needed": "Protects sensitive components from excessive current",
                    "applications": ["LED current limiting", "Voltage dividers", "Pull-up/pull-down"]
                },
                properties={
                    "resistance": 1000,     # ohms
                    "tolerance": 0.05,      # 5%
                    "power_rating": 0.25,   # watts
                    "voltage_rating": 250,  # volts
                    "temperature_coefficient": 100  # ppm/°C
                },
                compatibility=["led_red_5mm", "breadboard_mini", "wire_22awg"],
                tags=["resistor", "electronics", "passive", "current_limiting"],
                cost_virtual=1,
                rarity=1,
                unlock_level=1,
                is_consumable=True
            ),
            
            PartSpecification(
                part_id="led_red_5mm",
                name="5mm Red LED",
                description="High-brightness red light-emitting diode",
                category=PartCategory.ELECTRONICS,
                size_category=PartSize.TINY,
                material=MaterialType.PLASTIC_ABS,
                dimensions=(0.005, 0.005, 0.008),
                mass=0.0001,
                color="red",
                mesh_file="meshes/electronics/led_5mm.obj",
                texture_file="textures/led_red.jpg",
                icon_file="icons/led.svg",
                educational_info={
                    "purpose": "Converts electrical energy into light energy",
                    "how_it_works": "Electrons recombine with holes, releasing photons",
                    "polarity": "Current flows from anode (long leg) to cathode (short leg)",
                    "forward_voltage": "Typically 1.8-2.2V for red LEDs",
                    "why_current_limiting": "LEDs can burn out without current limiting resistor",
                    "efficiency": "Much more efficient than incandescent bulbs"
                },
                properties={
                    "forward_voltage": 2.0,     # volts
                    "max_current": 0.02,        # amperes
                    "luminous_intensity": 1000, # mcd
                    "wavelength": 660,          # nanometers
                    "viewing_angle": 60         # degrees
                },
                compatibility=["resistor_1k_1_4w", "resistor_330_1_4w", "breadboard_mini", "wire_22awg"],
                tags=["led", "electronics", "light", "diode", "indicator"],
                cost_virtual=3,
                rarity=1,
                unlock_level=1
            ),
            
            # Tools
            PartSpecification(
                part_id="screwdriver_phillips_1",
                name="Phillips Head Screwdriver (#1)",
                description="Small Phillips head screwdriver for electronics work",
                category=PartCategory.TOOLS,
                size_category=PartSize.MEDIUM,
                material=MaterialType.METAL_STEEL,
                dimensions=(0.15, 0.01, 0.01),
                mass=0.05,
                color="red_black",
                mesh_file="meshes/tools/screwdriver_phillips_1.obj",
                texture_file="textures/tool_handle_red.jpg",
                icon_file="icons/screwdriver.svg",
                educational_info={
                    "purpose": "Drives screws with Phillips (cross) heads",
                    "why_phillips": "Self-centering design prevents slipping",
                    "proper_technique": "Apply downward pressure while turning",
                    "size_matching": "Use correct size to avoid stripping screw heads",
                    "magnetized_tip": "Helps hold screws during installation"
                },
                properties={
                    "tip_size": "#1",
                    "shaft_length": 0.08,      # meters
                    "handle_material": "rubberized_plastic",
                    "tip_material": "hardened_steel",
                    "magnetized": True
                },
                compatibility=["screw_m3_10mm", "screw_m4_16mm"],
                tags=["tool", "screwdriver", "phillips", "electronics"],
                cost_virtual=15,
                rarity=2,
                unlock_level=1,
                is_tool=True
            ),
            
            # Structural Components
            PartSpecification(
                part_id="beam_aluminum_20x20x200",
                name="Aluminum T-Slot Beam (20x20x200mm)",
                description="Extruded aluminum beam with T-slot for modular construction",
                category=PartCategory.STRUCTURAL,
                size_category=PartSize.LARGE,
                material=MaterialType.METAL_ALUMINUM,
                dimensions=(0.2, 0.02, 0.02),
                mass=0.087,
                color="silver",
                mesh_file="meshes/structural/beam_tslot_20x20_200.obj",
                texture_file="textures/aluminum_anodized.jpg",
                icon_file="icons/beam.svg",
                educational_info={
                    "purpose": "Provides structural framework for mechanical assemblies",
                    "t_slot_advantage": "Allows nuts and bolts to slide in for flexible connections",
                    "aluminum_properties": "Lightweight, corrosion-resistant, good strength-to-weight ratio",
                    "modular_design": "Standard sizes allow interchangeable construction",
                    "applications": ["3D printer frames", "Workbenches", "Automation equipment"]
                },
                properties={
                    "cross_section": "20x20",   # mm
                    "length": 200,             # mm
                    "slot_width": 6,           # mm
                    "wall_thickness": 1.5,     # mm
                    "moment_of_inertia": 0.7   # cm⁴
                },
                compatibility=["bracket_corner_20", "bolt_m5_16mm", "nut_tslot_m5"],
                tags=["structural", "aluminum", "tslot", "extrusion", "framework"],
                cost_virtual=25,
                rarity=3,
                unlock_level=3
            ),
            
            # Sensors
            PartSpecification(
                part_id="sensor_ultrasonic_hc_sr04",
                name="HC-SR04 Ultrasonic Distance Sensor",
                description="Ultrasonic ranging module with 2-400cm measurement range",
                category=PartCategory.SENSORS,
                size_category=PartSize.SMALL,
                material=MaterialType.PLASTIC_ABS,
                dimensions=(0.045, 0.02, 0.015),
                mass=0.008,
                color="blue",
                mesh_file="meshes/sensors/hc_sr04.obj",
                texture_file="textures/pcb_blue.jpg",
                icon_file="icons/sensor_ultrasonic.svg",
                educational_info={
                    "purpose": "Measures distance using ultrasonic sound waves",
                    "how_it_works": "Sends ultrasonic pulse, measures time for echo return",
                    "speed_of_sound": "343 m/s in air at room temperature",
                    "distance_calculation": "Distance = (Time × Speed_of_Sound) / 2",
                    "limitations": "Affected by temperature, humidity, and surface materials",
                    "applications": ["Robotics navigation", "Parking sensors", "Liquid level monitoring"]
                },
                properties={
                    "operating_voltage": 5.0,   # volts
                    "operating_current": 0.015, # amperes
                    "frequency": 40000,         # Hz
                    "range_min": 0.02,          # meters
                    "range_max": 4.0,           # meters
                    "accuracy": 0.003           # meters
                },
                compatibility=["microcontroller_arduino", "wire_jumper_male_female", "resistor_1k_1_4w"],
                tags=["sensor", "ultrasonic", "distance", "arduino", "robotics"],
                cost_virtual=12,
                rarity=3,
                unlock_level=4
            ),
            
            # Raw Materials
            PartSpecification(
                part_id="sheet_acrylic_3mm_100x100",
                name="Acrylic Sheet (3mm, 100x100mm)",
                description="Clear acrylic plastic sheet for cutting and shaping",
                category=PartCategory.RAW_MATERIALS,
                size_category=PartSize.MEDIUM,
                material=MaterialType.PLASTIC_ABS,
                dimensions=(0.1, 0.1, 0.003),
                mass=0.012,
                color="clear",
                mesh_file="meshes/materials/sheet_acrylic_100x100x3.obj",
                texture_file="textures/acrylic_clear.jpg",
                icon_file="icons/sheet_material.svg",
                educational_info={
                    "purpose": "Raw material for custom parts and enclosures",
                    "cutting_methods": "Laser cutting, saw cutting, scoring and snapping",
                    "shaping": "Can be heated and formed into curves",
                    "joining": "Solvent welding, mechanical fasteners, adhesives",
                    "properties": "Optically clear, weather resistant, impact resistant",
                    "applications": ["Windows", "Signs", "Light guides", "Protective covers"]
                },
                properties={
                    "thickness": 0.003,         # meters
                    "transparency": 0.92,       # 92% light transmission
                    "impact_strength": 17,      # kJ/m²
                    "service_temperature": 80,  # °C
                    "density": 1200            # kg/m³
                },
                compatibility=["laser_cutter", "drill_bits", "saw_blade_fine"],
                tags=["material", "plastic", "acrylic", "clear", "sheet"],
                cost_virtual=18,
                rarity=2,
                unlock_level=3,
                is_consumable=True
            )
        ]
        
        # Add all default parts to the catalog
        for part_spec in default_parts:
            await self.add_part_to_catalog(part_spec)

    async def add_part_to_catalog(self, part_spec: PartSpecification):
        """Add a part specification to the catalog"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO part_specifications (
                    part_id, name, description, category, size_category, material,
                    dimensions, mass, color, mesh_file, texture_file, icon_file,
                    educational_info, properties, compatibility, tags,
                    cost_virtual, rarity, unlock_level, is_tool, is_consumable
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                ON CONFLICT (part_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    educational_info = EXCLUDED.educational_info,
                    properties = EXCLUDED.properties,
                    compatibility = EXCLUDED.compatibility,
                    tags = EXCLUDED.tags
            """,
                part_spec.part_id, part_spec.name, part_spec.description,
                part_spec.category.value, part_spec.size_category.value, part_spec.material.value,
                json.dumps(part_spec.dimensions), part_spec.mass, part_spec.color,
                part_spec.mesh_file, part_spec.texture_file, part_spec.icon_file,
                json.dumps(part_spec.educational_info), json.dumps(part_spec.properties),
                json.dumps(part_spec.compatibility), json.dumps(part_spec.tags),
                part_spec.cost_virtual, part_spec.rarity, part_spec.unlock_level,
                part_spec.is_tool, part_spec.is_consumable
            )
        
        # Cache the part
        self.part_catalog[part_spec.part_id] = part_spec

    async def search_parts(self, query: str, filters: Optional[Dict] = None, 
                          user_level: int = 1) -> List[Dict]:
        """Search for parts in the catalog"""
        search_terms = query.lower().split() if query else []
        
        async with self.db_pool.acquire() as conn:
            # Build the search query
            base_query = """
                SELECT * FROM part_specifications 
                WHERE is_available = TRUE AND unlock_level <= $1
            """
            params = [user_level]
            param_count = 1
            
            # Add text search
            if search_terms:
                text_conditions = []
                for term in search_terms:
                    param_count += 1
                    text_conditions.append(f"""
                        (LOWER(name) LIKE ${param_count} OR 
                         LOWER(description) LIKE ${param_count} OR
                         LOWER(tags::text) LIKE ${param_count})
                    """)
                    params.append(f"%{term}%")
                
                base_query += " AND (" + " AND ".join(text_conditions) + ")"
            
            # Add filters
            if filters:
                if "category" in filters:
                    param_count += 1
                    base_query += f" AND category = ${param_count}"
                    params.append(filters["category"])
                
                if "material" in filters:
                    param_count += 1
                    base_query += f" AND material = ${param_count}"
                    params.append(filters["material"])
                
                if "size" in filters:
                    param_count += 1
                    base_query += f" AND size_category = ${param_count}"
                    params.append(filters["size"])
                
                if "max_cost" in filters:
                    param_count += 1
                    base_query += f" AND cost_virtual <= ${param_count}"
                    params.append(filters["max_cost"])
            
            base_query += " ORDER BY rarity ASC, cost_virtual ASC, name ASC LIMIT 50"
            
            parts = await conn.fetch(base_query, *params)
        
        # Format results
        results = []
        for part in parts:
            results.append({
                "part_id": part["part_id"],
                "name": part["name"],
                "description": part["description"],
                "category": part["category"],
                "material": part["material"],
                "size": part["size_category"],
                "cost": part["cost_virtual"],
                "rarity": part["rarity"],
                "icon": part["icon_file"],
                "tags": json.loads(part["tags"]),
                "educational_preview": self._get_educational_preview(json.loads(part["educational_info"])),
                "compatibility_count": len(json.loads(part["compatibility"]))
            })
        
        return results

    def _get_educational_preview(self, educational_info: Dict) -> str:
        """Get a short educational preview for search results"""
        if "purpose" in educational_info:
            return educational_info["purpose"]
        elif "how_it_works" in educational_info:
            return educational_info["how_it_works"]
        else:
            return "Educational information available"

    async def get_part_details(self, part_id: str, user_level: int = 1) -> Optional[Dict]:
        """Get detailed information about a specific part"""
        async with self.db_pool.acquire() as conn:
            part = await conn.fetchrow("""
                SELECT * FROM part_specifications 
                WHERE part_id = $1 AND is_available = TRUE AND unlock_level <= $2
            """, part_id, user_level)
            
            if not part:
                return None
            
            # Get compatibility parts
            compatible_parts = []
            compatibility_ids = json.loads(part["compatibility"])
            if compatibility_ids:
                compatible_parts = await conn.fetch("""
                    SELECT part_id, name, icon_file FROM part_specifications
                    WHERE part_id = ANY($1) AND is_available = TRUE AND unlock_level <= $2
                """, compatibility_ids, user_level)
        
        return {
            "part_id": part["part_id"],
            "name": part["name"],
            "description": part["description"],
            "category": part["category"],
            "size_category": part["size_category"],
            "material": part["material"],
            "dimensions": json.loads(part["dimensions"]),
            "mass": part["mass"],
            "color": part["color"],
            "mesh_file": part["mesh_file"],
            "texture_file": part["texture_file"],
            "icon_file": part["icon_file"],
            "educational_info": json.loads(part["educational_info"]),
            "properties": json.loads(part["properties"]),
            "tags": json.loads(part["tags"]),
            "cost_virtual": part["cost_virtual"],
            "rarity": part["rarity"],
            "unlock_level": part["unlock_level"],
            "is_tool": part["is_tool"],
            "is_consumable": part["is_consumable"],
            "compatible_parts": [
                {
                    "part_id": cp["part_id"],
                    "name": cp["name"],
                    "icon": cp["icon_file"]
                } for cp in compatible_parts
            ],
            "usage_examples": await self._generate_usage_examples(part_id),
            "learning_objectives": self._extract_learning_objectives(json.loads(part["educational_info"]))
        }

    async def _generate_usage_examples(self, part_id: str) -> List[Dict]:
        """Generate usage examples for a part"""
        # This would be more sophisticated in a real implementation
        examples = {
            "screw_m3_10mm": [
                {"project": "LED Circuit Box", "role": "Securing the enclosure lid"},
                {"project": "Mini Robot", "role": "Attaching servo motors to chassis"}
            ],
            "gear_spur_20t_mod1": [
                {"project": "Gear Train Demo", "role": "Input gear for speed reduction"},
                {"project": "Mechanical Clock", "role": "Hour hand drive mechanism"}
            ],
            "resistor_1k_1_4w": [
                {"project": "LED Blinker", "role": "Current limiting for LED protection"},
                {"project": "Sensor Interface", "role": "Pull-up resistor for digital input"}
            ]
        }
        
        return examples.get(part_id, [
            {"project": "Custom Build", "role": "Component integration"}
        ])

    def _extract_learning_objectives(self, educational_info: Dict) -> List[str]:
        """Extract learning objectives from educational information"""
        objectives = []
        
        if "purpose" in educational_info:
            objectives.append(f"Understand the purpose: {educational_info['purpose']}")
        
        if "how_it_works" in educational_info:
            objectives.append(f"Learn the mechanism: {educational_info['how_it_works']}")
        
        if "applications" in educational_info:
            objectives.append("Identify real-world applications")
        
        return objectives

    async def add_part_to_inventory(self, user_id: str, part_id: str, quantity: int = 1, 
                                   location: str = "inventory") -> Dict:
        """Add a part instance to user's inventory"""
        # Check if part exists and user can access it
        user_level = await self.get_user_level(user_id)
        part_details = await self.get_part_details(part_id, user_level)
        
        if not part_details:
            return {"success": False, "error": "Part not available or locked"}
        
        instance_id = str(uuid.uuid4())
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_part_inventory (
                    instance_id, part_id, owner_user_id, quantity, location
                ) VALUES ($1, $2, $3, $4, $5)
            """, instance_id, part_id, user_id, quantity, location)
        
        return {
            "success": True,
            "instance_id": instance_id,
            "part_name": part_details["name"],
            "quantity_added": quantity,
            "total_cost": part_details["cost_virtual"] * quantity
        }

    async def get_user_inventory(self, user_id: str, location_filter: str = None) -> Dict:
        """Get user's part inventory"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT upi.*, ps.name, ps.icon_file, ps.category, ps.rarity
                FROM user_part_inventory upi
                JOIN part_specifications ps ON upi.part_id = ps.part_id
                WHERE upi.owner_user_id = $1
            """
            params = [user_id]
            
            if location_filter:
                query += " AND upi.location = $2"
                params.append(location_filter)
            
            query += " ORDER BY ps.category, ps.name"
            
            inventory_items = await conn.fetch(query, *params)
        
        # Group by category
        inventory_by_category = {}
        total_items = 0
        total_value = 0
        
        for item in inventory_items:
            category = item["category"]
            if category not in inventory_by_category:
                inventory_by_category[category] = []
            
            inventory_by_category[category].append({
                "instance_id": item["instance_id"],
                "part_id": item["part_id"],
                "name": item["name"],
                "quantity": item["quantity"],
                "condition": item["condition"],
                "location": item["location"],
                "icon": item["icon_file"],
                "rarity": item["rarity"],
                "last_used": item["last_used"].isoformat() if item["last_used"] else None
            })
            
            total_items += item["quantity"]
            # Would calculate actual value from part specifications
        
        return {
            "total_items": total_items,
            "total_categories": len(inventory_by_category),
            "inventory_by_category": inventory_by_category,
            "storage_locations": await self._get_storage_locations(user_id),
            "recent_acquisitions": await self._get_recent_acquisitions(user_id, 5)
        }

    async def use_part(self, user_id: str, instance_id: str, project_id: str = None, 
                      usage_type: str = "assembly") -> Dict:
        """Use a part from inventory"""
        async with self.db_pool.acquire() as conn:
            # Get part instance
            instance = await conn.fetchrow("""
                SELECT upi.*, ps.name, ps.is_consumable
                FROM user_part_inventory upi
                JOIN part_specifications ps ON upi.part_id = ps.part_id
                WHERE upi.instance_id = $1 AND upi.owner_user_id = $2
            """, instance_id, user_id)
            
            if not instance:
                return {"success": False, "error": "Part not found in inventory"}
            
            if instance["quantity"] <= 0:
                return {"success": False, "error": "Part out of stock"}
            
            # Update usage
            new_quantity = instance["quantity"]
            if instance["is_consumable"] and usage_type in ["consume", "assembly"]:
                new_quantity -= 1
            
            await conn.execute("""
                UPDATE user_part_inventory 
                SET quantity = $1, last_used = CURRENT_TIMESTAMP,
                    location = $2
                WHERE instance_id = $3
            """, new_quantity, f"project_{project_id}" if project_id else "workspace", instance_id)
            
            # Log usage
            await conn.execute("""
                INSERT INTO part_usage_history (
                    user_id, part_id, project_id, usage_type
                ) VALUES ($1, $2, $3, $4)
            """, user_id, instance["part_id"], project_id, usage_type)
        
        return {
            "success": True,
            "part_name": instance["name"],
            "remaining_quantity": new_quantity,
            "usage_type": usage_type,
            "consumed": instance["is_consumable"] and usage_type in ["consume", "assembly"]
        }

    async def get_parts_for_project_type(self, project_type: str, difficulty_level: int = 1,
                                        user_level: int = 1) -> Dict:
        """Get recommended parts for a specific project type"""
        project_part_recommendations = {
            "simple_circuit": {
                "required": ["resistor_1k_1_4w", "led_red_5mm", "wire_22awg"],
                "optional": ["breadboard_mini", "battery_9v"],
                "tools": ["screwdriver_phillips_1"]
            },
            "mechanical_assembly": {
                "required": ["screw_m3_10mm", "nut_m3_hex", "beam_aluminum_20x20x200"],
                "optional": ["washer_m3", "bracket_corner_20"],
                "tools": ["screwdriver_phillips_1", "wrench_hex_3mm"]
            },
            "gear_train": {
                "required": ["gear_spur_20t_mod1", "gear_spur_40t_mod1", "axle_6mm"],
                "optional": ["bearing_6mm", "gear_rack_mod1"],
                "tools": ["caliper_digital"]
            }
        }
        
        recommendations = project_part_recommendations.get(project_type, {
            "required": [],
            "optional": [],
            "tools": []
        })
        
        # Get detailed information for each part
        all_part_ids = recommendations["required"] + recommendations["optional"] + recommendations["tools"]
        part_details = {}
        
        for part_id in all_part_ids:
            details = await self.get_part_details(part_id, user_level)
            if details:
                part_details[part_id] = details
        
        return {
            "project_type": project_type,
            "difficulty_level": difficulty_level,
            "required_parts": [part_details.get(pid, {"part_id": pid, "name": "Unknown"}) 
                              for pid in recommendations["required"]],
            "optional_parts": [part_details.get(pid, {"part_id": pid, "name": "Unknown"}) 
                              for pid in recommendations["optional"]],
            "recommended_tools": [part_details.get(pid, {"part_id": pid, "name": "Unknown"}) 
                                 for pid in recommendations["tools"]],
            "total_cost_estimate": sum(part_details.get(pid, {}).get("cost_virtual", 0) 
                                     for pid in all_part_ids),
            "learning_objectives": self._get_project_learning_objectives(project_type)
        }

    def _get_project_learning_objectives(self, project_type: str) -> List[str]:
        """Get learning objectives for project types"""
        objectives = {
            "simple_circuit": [
                "Understand basic electrical circuits",
                "Learn about current, voltage, and resistance",
                "Practice component identification",
                "Apply Ohm's Law"
            ],
            "mechanical_assembly": [
                "Learn about fasteners and joints",
                "Understand structural stability",
                "Practice assembly techniques",
                "Explore mechanical properties"
            ],
            "gear_train": [
                "Understand gear ratios and mechanical advantage",
                "Learn about rotational motion transmission",
                "Calculate speed and torque relationships",
                "Explore mechanical systems"
            ]
        }
        
        return objectives.get(project_type, ["General making and problem-solving skills"])

    async def create_parts_collection(self, user_id: str, name: str, description: str,
                                    part_instances: List[str], is_public: bool = False) -> Dict:
        """Create a collection of parts for sharing or organization"""
        collection_id = str(uuid.uuid4())
        
        # Verify all parts belong to user
        async with self.db_pool.acquire() as conn:
            valid_instances = await conn.fetch("""
                SELECT instance_id, part_id, quantity FROM user_part_inventory
                WHERE instance_id = ANY($1) AND owner_user_id = $2
            """, part_instances, user_id)
            
            if len(valid_instances) != len(part_instances):
                return {"success": False, "error": "Some parts not found in your inventory"}
            
            # Create collection
            await conn.execute("""
                INSERT INTO parts_collections (
                    collection_id, name, description, part_instances, is_public, created_by
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, collection_id, name, description, json.dumps(part_instances), is_public, user_id)
        
        return {
            "success": True,
            "collection_id": collection_id,
            "name": name,
            "part_count": len(part_instances),
            "is_public": is_public
        }

    async def browse_parts_by_category(self, category: PartCategory, user_level: int = 1) -> Dict:
        """Browse parts organized by category"""
        async with self.db_pool.acquire() as conn:
            parts = await conn.fetch("""
                SELECT * FROM part_specifications
                WHERE category = $1 AND is_available = TRUE AND unlock_level <= $2
                ORDER BY rarity ASC, cost_virtual ASC, name ASC
            """, category.value, user_level)
        
        # Group by subcategories or material
        subcategories = {}
        for part in parts:
            material = part["material"]
            if material not in subcategories:
                subcategories[material] = []
            
            subcategories[material].append({
                "part_id": part["part_id"],
                "name": part["name"],
                "description": part["description"],
                "cost": part["cost_virtual"],
                "rarity": part["rarity"],
                "icon": part["icon_file"],
                "tags": json.loads(part["tags"])
            })
        
        return {
            "category": category.value,
            "total_parts": len(parts),
            "subcategories": subcategories,
            "category_info": self._get_category_info(category),
            "learning_focus": self._get_category_learning_focus(category)
        }

    def _get_category_info(self, category: PartCategory) -> Dict:
        """Get educational information about a part category"""
        category_info = {
            PartCategory.FASTENERS: {
                "description": "Components used to join or secure parts together",
                "key_concepts": ["Threaded connections", "Mechanical advantage", "Material stress"],
                "real_world": "Found in everything from furniture to spacecraft"
            },
            PartCategory.ELECTRONICS: {
                "description": "Components that control or use electrical current",
                "key_concepts": ["Current flow", "Voltage", "Resistance", "Digital signals"],
                "real_world": "The building blocks of all electronic devices"
            },
            PartCategory.GEARS: {
                "description": "Mechanical components that transmit rotational motion",
                "key_concepts": ["Gear ratios", "Mechanical advantage", "Torque", "Speed"],
                "real_world": "Used in cars, clocks, and industrial machinery"
            },
            PartCategory.SENSORS: {
                "description": "Components that detect and measure physical phenomena",
                "key_concepts": ["Signal conversion", "Calibration", "Accuracy", "Response time"],
                "real_world": "Enable automation and smart systems everywhere"
            }
        }
        
        return category_info.get(category, {
            "description": "Important components for building and learning",
            "key_concepts": ["Design", "Function", "Application"],
            "real_world": "Used in many engineering applications"
        })

    def _get_category_learning_focus(self, category: PartCategory) -> List[str]:
        """Get learning focus areas for a category"""
        focus_areas = {
            PartCategory.FASTENERS: [
                "Mechanical engineering principles",
                "Material properties and selection",
                "Assembly techniques"
            ],
            PartCategory.ELECTRONICS: [
                "Circuit analysis and design", 
                "Electrical safety",
                "Component specification and selection"
            ],
            PartCategory.GEARS: [
                "Mechanical systems design",
                "Power transmission",
                "Precision manufacturing"
            ]
        }
        
        return focus_areas.get(category, ["General engineering and design principles"])

    async def get_part_compatibility_web(self, part_id: str, depth: int = 2) -> Dict:
        """Get a web of part compatibilities for exploration"""
        compatibility_web = {}
        visited = set()
        
        async def explore_compatibility(current_part_id: str, current_depth: int):
            if current_depth <= 0 or current_part_id in visited:
                return
            
            visited.add(current_part_id)
            part_details = await self.get_part_details(current_part_id)
            
            if part_details:
                compatibility_web[current_part_id] = {
                    "name": part_details["name"],
                    "category": part_details["category"],
                    "icon": part_details["icon_file"],
                    "compatible_with": []
                }
                
                for compatible_part in part_details["compatible_parts"]:
                    compatible_id = compatible_part["part_id"]
                    compatibility_web[current_part_id]["compatible_with"].append({
                        "part_id": compatible_id,
                        "name": compatible_part["name"],
                        "icon": compatible_part["icon"]
                    })
                    
                    # Recursively explore
                    await explore_compatibility(compatible_id, current_depth - 1)
        
        await explore_compatibility(part_id, depth)
        
        return {
            "root_part_id": part_id,
            "compatibility_web": compatibility_web,
            "total_parts": len(compatibility_web),
            "exploration_depth": depth
        }

    async def get_user_level(self, user_id: str) -> int:
        """Get user's current level (would integrate with user system)"""
        # This would integrate with the user progression system
        return 3  # Default level

    async def _get_storage_locations(self, user_id: str) -> List[Dict]:
        """Get user's storage locations"""
        async with self.db_pool.acquire() as conn:
            locations = await conn.fetch("""
                SELECT location, COUNT(*) as item_count
                FROM user_part_inventory
                WHERE owner_user_id = $1
                GROUP BY location
                ORDER BY location
            """, user_id)
        
        return [{"location": loc["location"], "item_count": loc["item_count"]} for loc in locations]

    async def _get_recent_acquisitions(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get user's recent part acquisitions"""
        async with self.db_pool.acquire() as conn:
            recent = await conn.fetch("""
                SELECT upi.part_id, ps.name, ps.icon_file, upi.quantity, upi.acquired_at
                FROM user_part_inventory upi
                JOIN part_specifications ps ON upi.part_id = ps.part_id
                WHERE upi.owner_user_id = $1
                ORDER BY upi.acquired_at DESC
                LIMIT $2
            """, user_id, limit)
        
        return [
            {
                "part_id": item["part_id"],
                "name": item["name"],
                "icon": item["icon_file"],
                "quantity": item["quantity"],
                "acquired_at": item["acquired_at"].isoformat()
            } for item in recent
        ]

    async def build_search_index(self):
        """Build search index for fast part lookup"""
        async with self.db_pool.acquire() as conn:
            all_parts = await conn.fetch("""
                SELECT part_id, name, description, tags
                FROM part_specifications
                WHERE is_available = TRUE
            """)
        
        # Build keyword index
        for part in all_parts:
            keywords = set()
            
            # Add name words
            keywords.update(part["name"].lower().split())
            
            # Add description words
            if part["description"]:
                keywords.update(part["description"].lower().split())
            
            # Add tags
            tags = json.loads(part["tags"])
            keywords.update(tag.lower() for tag in tags)
            
            # Index each keyword
            for keyword in keywords:
                if keyword not in self.part_search_index:
                    self.part_search_index[keyword] = set()
                self.part_search_index[keyword].add(part["part_id"])

    async def get_parts_usage_analytics(self, user_id: str) -> Dict:
        """Get analytics about user's parts usage"""
        async with self.db_pool.acquire() as conn:
            # Most used parts
            most_used = await conn.fetch("""
                SELECT puh.part_id, ps.name, COUNT(*) as usage_count
                FROM part_usage_history puh
                JOIN part_specifications ps ON puh.part_id = ps.part_id
                WHERE puh.user_id = $1
                GROUP BY puh.part_id, ps.name
                ORDER BY usage_count DESC
                LIMIT 5
            """, user_id)
            
            # Usage by category
            category_usage = await conn.fetch("""
                SELECT ps.category, COUNT(*) as usage_count
                FROM part_usage_history puh
                JOIN part_specifications ps ON puh.part_id = ps.part_id
                WHERE puh.user_id = $1
                GROUP BY ps.category
                ORDER BY usage_count DESC
            """, user_id)
        
        return {
            "most_used_parts": [
                {"part_id": p["part_id"], "name": p["name"], "usage_count": p["usage_count"]}
                for p in most_used
            ],
            "usage_by_category": [
                {"category": c["category"], "usage_count": c["usage_count"]}
                for c in category_usage
            ],
            "learning_progression": await self._analyze_learning_progression(user_id)
        }

    async def _analyze_learning_progression(self, user_id: str) -> Dict:
        """Analyze user's learning progression through parts usage"""
        # This would analyze the complexity and variety of parts used over time
        return {
            "complexity_trend": "increasing",
            "categories_explored": 4,
            "skill_level": "intermediate",
            "next_suggested_category": "sensors"
        }