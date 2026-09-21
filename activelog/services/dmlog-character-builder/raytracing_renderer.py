"""
World-Class Photorealistic Ray Tracing Renderer
Enterprise-grade ray tracing system for character visualization using
path tracing, global illumination, and physically-based materials
"""

import numpy as np
import json
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import time
from abc import ABC, abstractmethod

class MaterialType(Enum):
    LAMBERT = "lambert"
    METAL = "metal"
    DIELECTRIC = "dielectric"
    EMISSIVE = "emissive"
    SUBSURFACE = "subsurface"
    HAIR = "hair"
    SKIN = "skin"

class LightType(Enum):
    DIRECTIONAL = "directional"
    POINT = "point"
    SPOT = "spot"
    AREA = "area"
    ENVIRONMENT = "environment"
    VOLUMETRIC = "volumetric"

@dataclass
class Vector3:
    x: float
    y: float
    z: float
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def dot(self, other: 'Vector3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3') -> 'Vector3':
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def normalize(self) -> 'Vector3':
        length = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if length > 0:
            return Vector3(self.x / length, self.y / length, self.z / length)
        return Vector3(0, 0, 0)
    
    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

@dataclass
class Ray:
    origin: Vector3
    direction: Vector3
    t_min: float = 0.001
    t_max: float = float('inf')
    depth: int = 0
    
    def at(self, t: float) -> Vector3:
        return self.origin + self.direction * t

@dataclass
class HitRecord:
    point: Vector3
    normal: Vector3
    material_id: int
    t: float
    u: float  # Texture coordinates
    v: float
    front_face: bool = True
    
    def set_face_normal(self, ray: Ray, outward_normal: Vector3):
        self.front_face = ray.direction.dot(outward_normal) < 0
        self.normal = outward_normal if self.front_face else outward_normal * -1

@dataclass
class Material:
    material_type: MaterialType
    albedo: Vector3  # Base color
    metallic: float = 0.0
    roughness: float = 0.5
    ior: float = 1.5  # Index of refraction
    emission: Vector3 = field(default_factory=lambda: Vector3(0, 0, 0))
    subsurface_radius: float = 0.0
    subsurface_color: Vector3 = field(default_factory=lambda: Vector3(1, 1, 1))
    
    # Advanced material properties
    anisotropy: float = 0.0
    sheen: float = 0.0
    clearcoat: float = 0.0
    clearcoat_roughness: float = 0.1
    transmission: float = 0.0
    
    # Texture maps (in production would be actual textures)
    diffuse_map: Optional[str] = None
    normal_map: Optional[str] = None
    roughness_map: Optional[str] = None
    metallic_map: Optional[str] = None
    emission_map: Optional[str] = None

@dataclass
class Light:
    light_type: LightType
    position: Vector3
    direction: Vector3
    color: Vector3
    intensity: float
    radius: float = 0.0  # For area lights
    inner_angle: float = 0.0  # For spot lights
    outer_angle: float = 0.0
    
    # Advanced lighting properties
    temperature: float = 6500.0  # Color temperature in Kelvin
    ies_profile: Optional[str] = None  # IES light profile
    volumetric_density: float = 0.0
    shadow_softness: float = 1.0

class Primitive(ABC):
    """Abstract base class for ray-traceable primitives"""
    
    @abstractmethod
    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        pass
    
    @abstractmethod
    def bounding_box(self) -> Tuple[Vector3, Vector3]:
        pass

class Sphere(Primitive):
    def __init__(self, center: Vector3, radius: float, material_id: int):
        self.center = center
        self.radius = radius
        self.material_id = material_id
    
    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        oc = ray.origin - self.center
        a = ray.direction.dot(ray.direction)
        b = 2.0 * oc.dot(ray.direction)
        c = oc.dot(oc) - self.radius * self.radius
        
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None
        
        sqrt_discriminant = math.sqrt(discriminant)
        root = (-b - sqrt_discriminant) / (2 * a)
        
        if root < t_min or root > t_max:
            root = (-b + sqrt_discriminant) / (2 * a)
            if root < t_min or root > t_max:
                return None
        
        hit_point = ray.at(root)
        outward_normal = (hit_point - self.center) * (1.0 / self.radius)
        
        # Calculate texture coordinates
        theta = math.acos(-outward_normal.y)
        phi = math.atan2(-outward_normal.z, outward_normal.x) + math.pi
        u = phi / (2 * math.pi)
        v = theta / math.pi
        
        hit_record = HitRecord(
            point=hit_point,
            normal=outward_normal,
            material_id=self.material_id,
            t=root,
            u=u,
            v=v
        )
        hit_record.set_face_normal(ray, outward_normal)
        
        return hit_record
    
    def bounding_box(self) -> Tuple[Vector3, Vector3]:
        r = Vector3(self.radius, self.radius, self.radius)
        return (self.center - r, self.center + r)

class Triangle(Primitive):
    def __init__(self, v0: Vector3, v1: Vector3, v2: Vector3, material_id: int,
                 n0: Vector3 = None, n1: Vector3 = None, n2: Vector3 = None,
                 uv0: Tuple[float, float] = (0, 0), 
                 uv1: Tuple[float, float] = (1, 0),
                 uv2: Tuple[float, float] = (0, 1)):
        self.v0, self.v1, self.v2 = v0, v1, v2
        self.material_id = material_id
        
        # Vertex normals for smooth shading
        self.n0 = n0 if n0 else self._calculate_face_normal()
        self.n1 = n1 if n1 else self.n0
        self.n2 = n2 if n2 else self.n0
        
        # Texture coordinates
        self.uv0, self.uv1, self.uv2 = uv0, uv1, uv2
        
        # Precompute edge vectors
        self.edge1 = v1 - v0
        self.edge2 = v2 - v0
    
    def _calculate_face_normal(self) -> Vector3:
        return self.edge1.cross(self.edge2).normalize()
    
    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        # Möller-Trumbore intersection algorithm
        h = ray.direction.cross(self.edge2)
        a = self.edge1.dot(h)
        
        if abs(a) < 1e-8:  # Ray is parallel to triangle
            return None
        
        f = 1.0 / a
        s = ray.origin - self.v0
        u = f * s.dot(h)
        
        if u < 0.0 or u > 1.0:
            return None
        
        q = s.cross(self.edge1)
        v = f * ray.direction.dot(q)
        
        if v < 0.0 or u + v > 1.0:
            return None
        
        t = f * self.edge2.dot(q)
        
        if t < t_min or t > t_max:
            return None
        
        # Interpolate normal and texture coordinates
        w = 1.0 - u - v
        normal = (self.n0 * w + self.n1 * u + self.n2 * v).normalize()
        
        tex_u = w * self.uv0[0] + u * self.uv1[0] + v * self.uv2[0]
        tex_v = w * self.uv0[1] + u * self.uv1[1] + v * self.uv2[1]
        
        hit_point = ray.at(t)
        
        hit_record = HitRecord(
            point=hit_point,
            normal=normal,
            material_id=self.material_id,
            t=t,
            u=tex_u,
            v=tex_v
        )
        hit_record.set_face_normal(ray, normal)
        
        return hit_record
    
    def bounding_box(self) -> Tuple[Vector3, Vector3]:
        min_x = min(self.v0.x, self.v1.x, self.v2.x)
        max_x = max(self.v0.x, self.v1.x, self.v2.x)
        min_y = min(self.v0.y, self.v1.y, self.v2.y)
        max_y = max(self.v0.y, self.v1.y, self.v2.y)
        min_z = min(self.v0.z, self.v1.z, self.v2.z)
        max_z = max(self.v0.z, self.v1.z, self.v2.z)
        
        return (Vector3(min_x, min_y, min_z), Vector3(max_x, max_y, max_z))

class BVHNode:
    """Bounding Volume Hierarchy node for acceleration"""
    
    def __init__(self, primitives: List[Primitive]):
        self.primitives = primitives
        self.left: Optional['BVHNode'] = None
        self.right: Optional['BVHNode'] = None
        self.bbox_min, self.bbox_max = self._calculate_bounding_box()
        
        # Recursively build BVH
        if len(primitives) > 1:
            self._split()
    
    def _calculate_bounding_box(self) -> Tuple[Vector3, Vector3]:
        if not self.primitives:
            return Vector3(0, 0, 0), Vector3(0, 0, 0)
        
        min_bbox, max_bbox = self.primitives[0].bounding_box()
        
        for primitive in self.primitives[1:]:
            prim_min, prim_max = primitive.bounding_box()
            
            min_bbox = Vector3(
                min(min_bbox.x, prim_min.x),
                min(min_bbox.y, prim_min.y),
                min(min_bbox.z, prim_min.z)
            )
            max_bbox = Vector3(
                max(max_bbox.x, prim_max.x),
                max(max_bbox.y, prim_max.y),
                max(max_bbox.z, prim_max.z)
            )
        
        return min_bbox, max_bbox
    
    def _split(self):
        # Choose split axis (longest axis)
        extent = self.bbox_max - self.bbox_min
        split_axis = 0 if extent.x > extent.y and extent.x > extent.z else (1 if extent.y > extent.z else 2)
        
        # Sort primitives by centroid along split axis
        def get_centroid_component(primitive: Primitive) -> float:
            min_bbox, max_bbox = primitive.bounding_box()
            centroid = (min_bbox + max_bbox) * 0.5
            return centroid.x if split_axis == 0 else (centroid.y if split_axis == 1 else centroid.z)
        
        self.primitives.sort(key=get_centroid_component)
        
        # Split primitives
        mid = len(self.primitives) // 2
        left_primitives = self.primitives[:mid]
        right_primitives = self.primitives[mid:]
        
        self.left = BVHNode(left_primitives)
        self.right = BVHNode(right_primitives)
        
        # Clear primitives list for internal nodes
        self.primitives = []
    
    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[HitRecord]:
        # Ray-box intersection test
        if not self._ray_box_intersection(ray, t_min, t_max):
            return None
        
        # Leaf node - test primitives
        if self.primitives:
            closest_hit = None
            closest_t = t_max
            
            for primitive in self.primitives:
                hit_record = primitive.hit(ray, t_min, closest_t)
                if hit_record and hit_record.t < closest_t:
                    closest_hit = hit_record
                    closest_t = hit_record.t
            
            return closest_hit
        
        # Internal node - test children
        left_hit = self.left.hit(ray, t_min, t_max) if self.left else None
        right_hit = self.right.hit(ray, t_min, t_max) if self.right else None
        
        if left_hit and right_hit:
            return left_hit if left_hit.t < right_hit.t else right_hit
        elif left_hit:
            return left_hit
        else:
            return right_hit
    
    def _ray_box_intersection(self, ray: Ray, t_min: float, t_max: float) -> bool:
        # Optimized ray-box intersection
        inv_dir = Vector3(
            1.0 / ray.direction.x if ray.direction.x != 0 else float('inf'),
            1.0 / ray.direction.y if ray.direction.y != 0 else float('inf'),
            1.0 / ray.direction.z if ray.direction.z != 0 else float('inf')
        )
        
        t1 = (self.bbox_min.x - ray.origin.x) * inv_dir.x
        t2 = (self.bbox_max.x - ray.origin.x) * inv_dir.x
        if t1 > t2:
            t1, t2 = t2, t1
        
        t_near = max(t1, t_min)
        t_far = min(t2, t_max)
        
        t1 = (self.bbox_min.y - ray.origin.y) * inv_dir.y
        t2 = (self.bbox_max.y - ray.origin.y) * inv_dir.y
        if t1 > t2:
            t1, t2 = t2, t1
        
        t_near = max(t1, t_near)
        t_far = min(t2, t_far)
        
        t1 = (self.bbox_min.z - ray.origin.z) * inv_dir.z
        t2 = (self.bbox_max.z - ray.origin.z) * inv_dir.z
        if t1 > t2:
            t1, t2 = t2, t1
        
        t_near = max(t1, t_near)
        t_far = min(t2, t_far)
        
        return t_near <= t_far

@dataclass
class Camera:
    position: Vector3
    target: Vector3
    up: Vector3
    fov: float  # Field of view in degrees
    aspect_ratio: float
    aperture: float = 0.0  # For depth of field
    focus_distance: float = 10.0
    
    def __post_init__(self):
        # Calculate camera basis vectors
        self.forward = (self.target - self.position).normalize()
        self.right = self.forward.cross(self.up).normalize()
        self.camera_up = self.right.cross(self.forward)
        
        # Calculate image plane dimensions
        theta = math.radians(self.fov)
        half_height = math.tan(theta / 2) * self.focus_distance
        half_width = half_height * self.aspect_ratio
        
        # Calculate image plane corners
        self.lower_left = (self.position + 
                          self.forward * self.focus_distance - 
                          self.right * half_width - 
                          self.camera_up * half_height)
        self.horizontal = self.right * (2 * half_width)
        self.vertical = self.camera_up * (2 * half_height)
        
        # Lens radius for depth of field
        self.lens_radius = self.aperture / 2
    
    def get_ray(self, u: float, v: float) -> Ray:
        """Generate camera ray for given UV coordinates"""
        # Depth of field offset
        rd = self._random_in_unit_disk() * self.lens_radius
        offset = self.right * rd.x + self.camera_up * rd.y
        
        ray_origin = self.position + offset
        ray_target = self.lower_left + self.horizontal * u + self.vertical * v
        ray_direction = (ray_target - ray_origin).normalize()
        
        return Ray(ray_origin, ray_direction)
    
    def _random_in_unit_disk(self) -> Vector3:
        """Generate random point in unit disk for depth of field"""
        while True:
            p = Vector3(
                np.random.uniform(-1, 1),
                np.random.uniform(-1, 1),
                0
            )
            if p.dot(p) < 1:
                return p

class PhotorealisticRaytracer:
    """World-class ray tracing renderer with advanced features"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._load_default_config()
        self.materials: List[Material] = []
        self.lights: List[Light] = []
        self.primitives: List[Primitive] = []
        self.bvh: Optional[BVHNode] = None
        self.environment_map: Optional[str] = None
        
        # Advanced features
        self.denoiser_enabled = True
        self.motion_blur_enabled = False
        self.volumetric_rendering = True
        self.subsurface_scattering = True
        
        # Performance tracking
        self.render_stats = {
            "rays_cast": 0,
            "triangles_tested": 0,
            "bvh_traversals": 0,
            "material_evaluations": 0
        }
        
        logger = logging.getLogger(__name__)
        logger.info("Photorealistic ray tracer initialized")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load world-class ray tracing configuration"""
        return {
            "rendering": {
                "width": 1920,
                "height": 1080,
                "samples_per_pixel": 1024,
                "max_ray_depth": 16,
                "russian_roulette_threshold": 0.1,
                "tile_size": 64
            },
            "lighting": {
                "global_illumination": True,
                "caustics": True,
                "volumetric_lighting": True,
                "shadow_rays": 4,
                "environment_sampling": True
            },
            "materials": {
                "subsurface_scattering": True,
                "spectral_rendering": False,
                "microfacet_models": True,
                "layered_materials": True
            },
            "acceleration": {
                "bvh_enabled": True,
                "bvh_max_leaf_size": 4,
                "spatial_splits": True,
                "traversal_optimization": True
            },
            "post_processing": {
                "tone_mapping": "aces",
                "gamma_correction": 2.2,
                "bloom": True,
                "chromatic_aberration": False,
                "vignette": False,
                "denoising": "optix"  # In production would use OptiX denoiser
            }
        }
    
    def add_material(self, material: Material) -> int:
        """Add material and return its ID"""
        self.materials.append(material)
        return len(self.materials) - 1
    
    def add_light(self, light: Light):
        """Add light to the scene"""
        self.lights.append(light)
    
    def add_primitive(self, primitive: Primitive):
        """Add primitive to the scene"""
        self.primitives.append(primitive)
    
    def build_acceleration_structure(self):
        """Build BVH acceleration structure"""
        if self.primitives:
            self.bvh = BVHNode(self.primitives)
            logger = logging.getLogger(__name__)
            logger.info(f"Built BVH with {len(self.primitives)} primitives")
    
    def render_character(self, camera: Camera, character_model: Dict[str, Any]) -> np.ndarray:
        """Render character with photorealistic quality"""
        
        # Setup character geometry and materials
        self._setup_character_geometry(character_model)
        self._setup_character_materials(character_model)
        self._setup_lighting_environment(character_model.get("lighting", {}))
        
        # Build acceleration structure
        self.build_acceleration_structure()
        
        # Render with path tracing
        image = self._path_trace_render(camera)
        
        # Post-processing
        image = self._apply_post_processing(image)
        
        return image
    
    def _setup_character_geometry(self, character_model: Dict[str, Any]):
        """Setup character geometry from model data"""
        
        # Create basic character geometry (simplified for demo)
        # In production, would load from detailed 3D mesh
        
        # Head
        head_material = self._create_skin_material(character_model.get("skin_tone", "fair"))
        head = Sphere(Vector3(0, 1.7, 0), 0.12, head_material)
        self.add_primitive(head)
        
        # Body
        body_material = self._create_clothing_material(character_model.get("clothing", {}))
        body = Sphere(Vector3(0, 1.3, 0), 0.2, body_material)
        self.add_primitive(body)
        
        # Hair (if present)
        if character_model.get("hair_style") != "bald":
            hair_material = self._create_hair_material(character_model.get("hair_color", "brown"))
            hair = Sphere(Vector3(0, 1.75, -0.05), 0.15, hair_material)
            self.add_primitive(hair)
        
        # Equipment
        equipment = character_model.get("equipment", {})
        if "weapon" in equipment:
            weapon_material = self._create_metal_material()
            weapon = Sphere(Vector3(0.3, 1.2, 0), 0.05, weapon_material)
            self.add_primitive(weapon)
    
    def _create_skin_material(self, skin_tone: str) -> int:
        """Create realistic skin material"""
        
        skin_colors = {
            "fair": Vector3(0.92, 0.84, 0.76),
            "tan": Vector3(0.85, 0.72, 0.58),
            "olive": Vector3(0.78, 0.71, 0.51),
            "brown": Vector3(0.65, 0.48, 0.36),
            "dark": Vector3(0.45, 0.32, 0.24)
        }
        
        albedo = skin_colors.get(skin_tone, skin_colors["fair"])
        
        skin_material = Material(
            material_type=MaterialType.SKIN,
            albedo=albedo,
            roughness=0.4,
            subsurface_radius=0.02,
            subsurface_color=Vector3(0.8, 0.4, 0.3),  # Blood color
            metallic=0.0,
            ior=1.4  # Skin IOR
        )
        
        return self.add_material(skin_material)
    
    def _create_hair_material(self, hair_color: str) -> int:
        """Create realistic hair material"""
        
        hair_colors = {
            "black": Vector3(0.05, 0.05, 0.05),
            "brown": Vector3(0.2, 0.12, 0.08),
            "blonde": Vector3(0.6, 0.5, 0.3),
            "red": Vector3(0.4, 0.1, 0.05),
            "white": Vector3(0.9, 0.9, 0.9),
            "gray": Vector3(0.5, 0.5, 0.5)
        }
        
        albedo = hair_colors.get(hair_color, hair_colors["brown"])
        
        hair_material = Material(
            material_type=MaterialType.HAIR,
            albedo=albedo,
            roughness=0.8,
            anisotropy=0.9,  # Hair is highly anisotropic
            metallic=0.0
        )
        
        return self.add_material(hair_material)
    
    def _create_clothing_material(self, clothing_data: Dict[str, Any]) -> int:
        """Create clothing material"""
        
        material_type = clothing_data.get("material", "fabric")
        color = clothing_data.get("color", [0.3, 0.3, 0.6])
        
        if material_type == "leather":
            material = Material(
                material_type=MaterialType.LAMBERT,
                albedo=Vector3(0.4, 0.2, 0.1),
                roughness=0.7,
                metallic=0.0
            )
        elif material_type == "metal":
            material = Material(
                material_type=MaterialType.METAL,
                albedo=Vector3(0.7, 0.7, 0.7),
                roughness=0.1,
                metallic=1.0
            )
        else:  # fabric
            material = Material(
                material_type=MaterialType.LAMBERT,
                albedo=Vector3(*color),
                roughness=0.9,
                metallic=0.0
            )
        
        return self.add_material(material)
    
    def _create_metal_material(self) -> int:
        """Create metal material for weapons/armor"""
        metal_material = Material(
            material_type=MaterialType.METAL,
            albedo=Vector3(0.8, 0.8, 0.9),
            roughness=0.05,
            metallic=1.0,
            ior=2.5
        )
        
        return self.add_material(metal_material)
    
    def _setup_character_materials(self, character_model: Dict[str, Any]):
        """Setup advanced material properties"""
        
        # Eye materials
        eye_material = Material(
            material_type=MaterialType.DIELECTRIC,
            albedo=Vector3(0.1, 0.3, 0.6),  # Eye color
            roughness=0.0,
            ior=1.376,  # Eye fluid IOR
            transmission=0.9
        )
        self.add_material(eye_material)
        
        # Teeth material
        teeth_material = Material(
            material_type=MaterialType.SUBSURFACE,
            albedo=Vector3(0.95, 0.93, 0.88),
            roughness=0.1,
            subsurface_radius=0.005,
            subsurface_color=Vector3(0.9, 0.8, 0.7)
        )
        self.add_material(teeth_material)
    
    def _setup_lighting_environment(self, lighting_config: Dict[str, Any]):
        """Setup advanced lighting environment"""
        
        lighting_type = lighting_config.get("type", "studio")
        
        if lighting_type == "studio":
            self._setup_studio_lighting()
        elif lighting_type == "outdoor":
            self._setup_outdoor_lighting()
        elif lighting_type == "dramatic":
            self._setup_dramatic_lighting()
        else:
            self._setup_default_lighting()
    
    def _setup_studio_lighting(self):
        """Setup professional studio lighting"""
        
        # Key light - main illumination
        key_light = Light(
            light_type=LightType.AREA,
            position=Vector3(2, 3, 2),
            direction=Vector3(-0.5, -0.7, -0.5),
            color=Vector3(1.0, 0.95, 0.9),
            intensity=800,
            radius=0.5,
            temperature=5600
        )
        self.add_light(key_light)
        
        # Fill light - soften shadows
        fill_light = Light(
            light_type=LightType.AREA,
            position=Vector3(-1.5, 2, 1.5),
            direction=Vector3(0.4, -0.5, -0.3),
            color=Vector3(0.8, 0.9, 1.0),
            intensity=300,
            radius=0.8,
            temperature=6500
        )
        self.add_light(fill_light)
        
        # Rim light - edge definition
        rim_light = Light(
            light_type=LightType.POINT,
            position=Vector3(-2, 2, -2),
            direction=Vector3(0, 0, 0),
            color=Vector3(1.0, 0.9, 0.8),
            intensity=400,
            temperature=3200
        )
        self.add_light(rim_light)
        
        # Environment light
        env_light = Light(
            light_type=LightType.ENVIRONMENT,
            position=Vector3(0, 0, 0),
            direction=Vector3(0, 1, 0),
            color=Vector3(0.2, 0.2, 0.25),
            intensity=100
        )
        self.add_light(env_light)
    
    def _setup_outdoor_lighting(self):
        """Setup natural outdoor lighting"""
        
        # Sun light
        sun = Light(
            light_type=LightType.DIRECTIONAL,
            position=Vector3(0, 0, 0),
            direction=Vector3(0.3, -0.8, 0.5),
            color=Vector3(1.0, 0.95, 0.8),
            intensity=1000,
            temperature=5778
        )
        self.add_light(sun)
        
        # Sky light (ambient)
        sky = Light(
            light_type=LightType.ENVIRONMENT,
            position=Vector3(0, 0, 0),
            direction=Vector3(0, 1, 0),
            color=Vector3(0.4, 0.6, 1.0),
            intensity=200
        )
        self.add_light(sky)
    
    def _setup_dramatic_lighting(self):
        """Setup dramatic cinematic lighting"""
        
        # Strong key light
        key = Light(
            light_type=LightType.SPOT,
            position=Vector3(3, 4, 1),
            direction=Vector3(-0.8, -0.9, -0.2),
            color=Vector3(1.0, 0.8, 0.6),
            intensity=1200,
            inner_angle=math.radians(15),
            outer_angle=math.radians(30),
            temperature=3200
        )
        self.add_light(key)
        
        # Colored accent light
        accent = Light(
            light_type=LightType.POINT,
            position=Vector3(-2, 1, -1),
            direction=Vector3(0, 0, 0),
            color=Vector3(0.2, 0.4, 1.0),
            intensity=300
        )
        self.add_light(accent)
    
    def _setup_default_lighting(self):
        """Setup default balanced lighting"""
        
        # Main light
        main = Light(
            light_type=LightType.POINT,
            position=Vector3(2, 2, 2),
            direction=Vector3(0, 0, 0),
            color=Vector3(1.0, 1.0, 1.0),
            intensity=500
        )
        self.add_light(main)
        
        # Ambient
        ambient = Light(
            light_type=LightType.ENVIRONMENT,
            position=Vector3(0, 0, 0),
            direction=Vector3(0, 1, 0),
            color=Vector3(0.3, 0.3, 0.3),
            intensity=150
        )
        self.add_light(ambient)
    
    def _path_trace_render(self, camera: Camera) -> np.ndarray:
        """Main path tracing rendering loop"""
        
        config = self.config["rendering"]
        width = config["width"]
        height = config["height"]
        samples = config["samples_per_pixel"]
        
        # Initialize image buffer
        image = np.zeros((height, width, 3), dtype=np.float32)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Starting path tracing render: {width}x{height}, {samples} SPP")
        
        # Tile-based rendering for memory efficiency
        tile_size = config["tile_size"]
        
        for tile_y in range(0, height, tile_size):
            for tile_x in range(0, width, tile_size):
                self._render_tile(image, camera, tile_x, tile_y, tile_size, samples)
                
                # Progress update
                progress = ((tile_y * width + tile_x * tile_size) / (width * height)) * 100
                if int(progress) % 10 == 0:
                    logger.info(f"Rendering progress: {progress:.1f}%")
        
        return image
    
    def _render_tile(self, image: np.ndarray, camera: Camera, 
                    start_x: int, start_y: int, tile_size: int, samples: int):
        """Render a single tile with path tracing"""
        
        height, width = image.shape[:2]
        end_x = min(start_x + tile_size, width)
        end_y = min(start_y + tile_size, height)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                
                # Accumulate samples
                pixel_color = Vector3(0, 0, 0)
                
                for sample in range(samples):
                    # Jittered sampling for antialiasing
                    u = (x + np.random.random()) / width
                    v = (y + np.random.random()) / height
                    
                    # Generate camera ray
                    ray = camera.get_ray(u, v)
                    
                    # Path trace the ray
                    sample_color = self._trace_path(ray, 0)
                    pixel_color = pixel_color + sample_color
                    
                    self.render_stats["rays_cast"] += 1
                
                # Average samples and store in image
                pixel_color = pixel_color * (1.0 / samples)
                image[y, x] = [pixel_color.x, pixel_color.y, pixel_color.z]
    
    def _trace_path(self, ray: Ray, depth: int) -> Vector3:
        """Trace a single path with global illumination"""
        
        max_depth = self.config["rendering"]["max_ray_depth"]
        russian_roulette = self.config["rendering"]["russian_roulette_threshold"]
        
        # Russian roulette for path termination
        if depth > 3:
            probability = max(russian_roulette, min(0.95, self._luminance(Vector3(1, 1, 1))))
            if np.random.random() > probability:
                return Vector3(0, 0, 0)
            else:
                # Continue path with increased weight
                pass
        
        # Hard depth limit
        if depth >= max_depth:
            return Vector3(0, 0, 0)
        
        # Intersect ray with scene
        hit_record = self._intersect_scene(ray)
        
        if not hit_record:
            # No intersection - return environment color
            return self._sample_environment(ray)
        
        # Get material
        material = self.materials[hit_record.material_id]
        
        # Evaluate material and lighting
        return self._evaluate_material(ray, hit_record, material, depth)
    
    def _intersect_scene(self, ray: Ray) -> Optional[HitRecord]:
        """Intersect ray with scene geometry"""
        
        if self.bvh:
            # Use BVH acceleration
            self.render_stats["bvh_traversals"] += 1
            return self.bvh.hit(ray, ray.t_min, ray.t_max)
        else:
            # Brute force intersection
            closest_hit = None
            closest_t = ray.t_max
            
            for primitive in self.primitives:
                hit_record = primitive.hit(ray, ray.t_min, closest_t)
                if hit_record and hit_record.t < closest_t:
                    closest_hit = hit_record
                    closest_t = hit_record.t
                    self.render_stats["triangles_tested"] += 1
            
            return closest_hit
    
    def _sample_environment(self, ray: Ray) -> Vector3:
        """Sample environment lighting"""
        
        # Simple gradient sky for demo
        t = (ray.direction.y + 1.0) * 0.5  # Map Y from [-1,1] to [0,1]
        
        # Interpolate between horizon and zenith
        horizon_color = Vector3(0.7, 0.8, 1.0)
        zenith_color = Vector3(0.3, 0.5, 1.0)
        
        return horizon_color * (1.0 - t) + zenith_color * t
    
    def _evaluate_material(self, ray: Ray, hit_record: HitRecord, 
                          material: Material, depth: int) -> Vector3:
        """Evaluate material BRDF and lighting"""
        
        self.render_stats["material_evaluations"] += 1
        
        # Direct lighting contribution
        direct_lighting = self._compute_direct_lighting(hit_record, material)
        
        # Indirect lighting (global illumination)
        indirect_lighting = Vector3(0, 0, 0)
        
        if self.config["lighting"]["global_illumination"]:
            indirect_lighting = self._compute_indirect_lighting(ray, hit_record, material, depth)
        
        # Material emission
        emission = material.emission
        
        # Combine lighting contributions
        total_lighting = direct_lighting + indirect_lighting + emission
        
        # Apply material properties
        final_color = self._apply_material_properties(total_lighting, material, hit_record)
        
        return final_color
    
    def _compute_direct_lighting(self, hit_record: HitRecord, material: Material) -> Vector3:
        """Compute direct lighting from all light sources"""
        
        direct_color = Vector3(0, 0, 0)
        
        for light in self.lights:
            # Sample light
            light_samples = self._sample_light(light, hit_record)
            
            for light_sample in light_samples:
                # Shadow ray test
                shadow_ray = Ray(
                    hit_record.point,
                    light_sample["direction"],
                    0.001,
                    light_sample["distance"] - 0.001
                )
                
                # Check for occlusion
                if not self._is_occluded(shadow_ray):
                    # Evaluate BRDF
                    brdf_value = self._evaluate_brdf(
                        -light_sample["direction"],  # Light direction
                        -hit_record.normal,          # View direction
                        hit_record.normal,           # Surface normal
                        material
                    )
                    
                    # Lambert's cosine law
                    cos_theta = max(0, hit_record.normal.dot(light_sample["direction"]))
                    
                    # Add contribution
                    contribution = (brdf_value * 
                                  light_sample["radiance"] * 
                                  cos_theta * 
                                  light_sample["pdf"])
                    
                    direct_color = direct_color + contribution
        
        return direct_color
    
    def _compute_indirect_lighting(self, incident_ray: Ray, hit_record: HitRecord, 
                                 material: Material, depth: int) -> Vector3:
        """Compute indirect lighting via Monte Carlo integration"""
        
        # Sample hemisphere for indirect lighting
        sample_direction = self._sample_hemisphere(hit_record.normal)
        
        # Create indirect ray
        indirect_ray = Ray(hit_record.point, sample_direction, depth=depth + 1)
        
        # Recursively trace indirect ray
        indirect_radiance = self._trace_path(indirect_ray, depth + 1)
        
        # Evaluate BRDF for indirect contribution
        brdf_value = self._evaluate_brdf(
            sample_direction,
            incident_ray.direction * -1,
            hit_record.normal,
            material
        )
        
        # Monte Carlo estimator
        cos_theta = max(0, hit_record.normal.dot(sample_direction))
        pdf = cos_theta / math.pi  # Cosine-weighted hemisphere sampling
        
        if pdf > 0:
            return brdf_value * indirect_radiance * cos_theta / pdf
        else:
            return Vector3(0, 0, 0)
    
    def _sample_light(self, light: Light, hit_record: HitRecord) -> List[Dict[str, Any]]:
        """Sample light source for direct lighting"""
        
        samples = []
        
        if light.light_type == LightType.POINT:
            # Point light sampling
            light_dir = (light.position - hit_record.point).normalize()
            distance = (light.position - hit_record.point).length()
            
            # Inverse square law attenuation
            attenuation = 1.0 / (distance * distance)
            radiance = light.color * light.intensity * attenuation
            
            samples.append({
                "direction": light_dir,
                "distance": distance,
                "radiance": radiance,
                "pdf": 1.0
            })
        
        elif light.light_type == LightType.DIRECTIONAL:
            # Directional light sampling
            samples.append({
                "direction": light.direction * -1,
                "distance": float('inf'),
                "radiance": light.color * light.intensity,
                "pdf": 1.0
            })
        
        elif light.light_type == LightType.AREA:
            # Area light sampling (simplified as multiple point samples)
            num_samples = self.config["lighting"]["shadow_rays"]
            
            for _ in range(num_samples):
                # Random point on light surface
                offset = self._random_in_unit_disk() * light.radius
                sample_point = light.position + offset
                
                light_dir = (sample_point - hit_record.point).normalize()
                distance = (sample_point - hit_record.point).length()
                
                attenuation = 1.0 / (distance * distance)
                radiance = light.color * light.intensity * attenuation / num_samples
                
                samples.append({
                    "direction": light_dir,
                    "distance": distance,
                    "radiance": radiance,
                    "pdf": 1.0 / num_samples
                })
        
        return samples
    
    def _is_occluded(self, shadow_ray: Ray) -> bool:
        """Test if shadow ray is occluded"""
        
        hit_record = self._intersect_scene(shadow_ray)
        return hit_record is not None
    
    def _evaluate_brdf(self, light_dir: Vector3, view_dir: Vector3, 
                      normal: Vector3, material: Material) -> Vector3:
        """Evaluate bidirectional reflectance distribution function"""
        
        if material.material_type == MaterialType.LAMBERT:
            # Lambertian BRDF
            return material.albedo * (1.0 / math.pi)
        
        elif material.material_type == MaterialType.METAL:
            # Cook-Torrance microfacet BRDF
            return self._cook_torrance_brdf(light_dir, view_dir, normal, material)
        
        elif material.material_type == MaterialType.SKIN:
            # Subsurface scattering approximation
            return self._subsurface_brdf(light_dir, view_dir, normal, material)
        
        elif material.material_type == MaterialType.HAIR:
            # Kajiya-Kay hair BRDF
            return self._hair_brdf(light_dir, view_dir, normal, material)
        
        else:
            # Default Lambertian
            return material.albedo * (1.0 / math.pi)
    
    def _cook_torrance_brdf(self, light_dir: Vector3, view_dir: Vector3,
                           normal: Vector3, material: Material) -> Vector3:
        """Cook-Torrance microfacet BRDF for metals and dielectrics"""
        
        # Half vector
        half_vec = (light_dir + view_dir).normalize()
        
        # Dot products
        n_dot_l = max(0.001, normal.dot(light_dir))
        n_dot_v = max(0.001, normal.dot(view_dir))
        n_dot_h = max(0.001, normal.dot(half_vec))
        v_dot_h = max(0.001, view_dir.dot(half_vec))
        
        # Fresnel term
        f0 = material.albedo if material.metallic > 0.5 else Vector3(0.04, 0.04, 0.04)
        fresnel = self._fresnel_schlick(v_dot_h, f0)
        
        # Distribution term (GGX/Trowbridge-Reitz)
        alpha = material.roughness * material.roughness
        alpha2 = alpha * alpha
        denom = n_dot_h * n_dot_h * (alpha2 - 1.0) + 1.0
        distribution = alpha2 / (math.pi * denom * denom)
        
        # Geometry term (Smith model)
        geometry = self._geometry_smith(n_dot_l, n_dot_v, material.roughness)
        
        # Cook-Torrance BRDF
        numerator = distribution * geometry * fresnel
        denominator = 4.0 * n_dot_l * n_dot_v
        
        specular = numerator * (1.0 / max(denominator, 0.001))
        
        # Diffuse component (for dielectrics)
        diffuse = material.albedo * (1.0 / math.pi) * (1.0 - material.metallic)
        
        return diffuse + specular
    
    def _fresnel_schlick(self, cos_theta: float, f0: Vector3) -> Vector3:
        """Fresnel-Schlick approximation"""
        one_minus_cos = 1.0 - cos_theta
        return f0 + (Vector3(1, 1, 1) - f0) * (one_minus_cos ** 5)
    
    def _geometry_smith(self, n_dot_l: float, n_dot_v: float, roughness: float) -> float:
        """Smith geometry function"""
        
        def geometry_schlick_ggx(n_dot: float, k: float) -> float:
            return n_dot / (n_dot * (1.0 - k) + k)
        
        k = (roughness + 1.0) * (roughness + 1.0) / 8.0
        ggx1 = geometry_schlick_ggx(n_dot_v, k)
        ggx2 = geometry_schlick_ggx(n_dot_l, k)
        
        return ggx1 * ggx2
    
    def _subsurface_brdf(self, light_dir: Vector3, view_dir: Vector3,
                        normal: Vector3, material: Material) -> Vector3:
        """Subsurface scattering BRDF approximation"""
        
        # Simple subsurface approximation using wrapped lighting
        n_dot_l = normal.dot(light_dir)
        wrapped_diffuse = max(0, (n_dot_l + material.subsurface_radius) / (1.0 + material.subsurface_radius))
        
        # Combine surface and subsurface scattering
        surface_contrib = material.albedo * wrapped_diffuse
        subsurface_contrib = material.subsurface_color * wrapped_diffuse * material.subsurface_radius
        
        return (surface_contrib + subsurface_contrib) * (1.0 / math.pi)
    
    def _hair_brdf(self, light_dir: Vector3, view_dir: Vector3,
                  normal: Vector3, material: Material) -> Vector3:
        """Hair BRDF using Kajiya-Kay model"""
        
        # Tangent vector (hair direction)
        tangent = Vector3(0, 1, 0)  # Simplified - hair grows upward
        
        # Primary reflection lobe
        sin_theta_i = math.sqrt(max(0, 1 - (tangent.dot(light_dir))**2))
        sin_theta_r = math.sqrt(max(0, 1 - (tangent.dot(view_dir))**2))
        
        cos_phi = light_dir.dot(view_dir) - tangent.dot(light_dir) * tangent.dot(view_dir)
        cos_phi = cos_phi / (sin_theta_i * sin_theta_r + 0.001)
        
        # Specular term
        specular_power = 1.0 / (material.roughness + 0.001)
        specular = pow(max(0, cos_phi), specular_power)
        
        # Diffuse term
        diffuse = sin_theta_i
        
        return material.albedo * (diffuse + specular * 0.3) * (1.0 / math.pi)
    
    def _sample_hemisphere(self, normal: Vector3) -> Vector3:
        """Sample random direction in hemisphere around normal"""
        
        # Create coordinate system
        if abs(normal.x) > 0.9:
            tangent = Vector3(0, 1, 0)
        else:
            tangent = Vector3(1, 0, 0)
        
        tangent = (tangent - normal * tangent.dot(normal)).normalize()
        bitangent = normal.cross(tangent)
        
        # Cosine-weighted hemisphere sampling
        r1 = np.random.random()
        r2 = np.random.random()
        
        cos_theta = math.sqrt(r1)
        sin_theta = math.sqrt(1 - r1)
        phi = 2 * math.pi * r2
        
        x = sin_theta * math.cos(phi)
        y = sin_theta * math.sin(phi)
        z = cos_theta
        
        # Transform to world space
        world_direction = (tangent * x + bitangent * y + normal * z).normalize()
        return world_direction
    
    def _random_in_unit_disk(self) -> Vector3:
        """Generate random point in unit disk"""
        while True:
            p = Vector3(np.random.uniform(-1, 1), np.random.uniform(-1, 1), 0)
            if p.dot(p) < 1:
                return p
    
    def _apply_material_properties(self, radiance: Vector3, material: Material,
                                 hit_record: HitRecord) -> Vector3:
        """Apply material-specific properties to final color"""
        
        # Texture sampling (simplified - would use actual texture coordinates)
        if material.diffuse_map:
            # Sample diffuse texture
            texture_color = self._sample_texture(material.diffuse_map, hit_record.u, hit_record.v)
            radiance = Vector3(
                radiance.x * texture_color.x,
                radiance.y * texture_color.y,
                radiance.z * texture_color.z
            )
        
        # Normal mapping
        if material.normal_map:
            # Apply normal map (would modify surface normal)
            pass
        
        # Roughness mapping
        if material.roughness_map:
            # Modify material roughness based on texture
            pass
        
        return radiance
    
    def _sample_texture(self, texture_path: str, u: float, v: float) -> Vector3:
        """Sample texture at UV coordinates"""
        # Simplified texture sampling - in production would load actual textures
        return Vector3(0.5, 0.5, 0.5)  # Neutral gray
    
    def _luminance(self, color: Vector3) -> float:
        """Calculate luminance of color"""
        return 0.299 * color.x + 0.587 * color.y + 0.114 * color.z
    
    def _apply_post_processing(self, image: np.ndarray) -> np.ndarray:
        """Apply advanced post-processing effects"""
        
        config = self.config["post_processing"]
        
        # Tone mapping
        if config["tone_mapping"] == "aces":
            image = self._aces_tone_mapping(image)
        elif config["tone_mapping"] == "reinhard":
            image = self._reinhard_tone_mapping(image)
        
        # Gamma correction
        gamma = config["gamma_correction"]
        if gamma != 1.0:
            image = np.power(image, 1.0 / gamma)
        
        # Bloom effect
        if config["bloom"]:
            image = self._apply_bloom(image)
        
        # Denoising (simplified - in production would use advanced denoisers)
        if config["denoising"] and self.denoiser_enabled:
            image = self._apply_denoising(image)
        
        # Clamp to [0, 1] range
        image = np.clip(image, 0.0, 1.0)
        
        return image
    
    def _aces_tone_mapping(self, image: np.ndarray) -> np.ndarray:
        """ACES tone mapping for cinematic look"""
        
        # ACES tone mapping curve
        def aces_tonemap(x):
            a = 2.51
            b = 0.03
            c = 2.43
            d = 0.59
            e = 0.14
            return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
        
        return aces_tonemap(image)
    
    def _reinhard_tone_mapping(self, image: np.ndarray) -> np.ndarray:
        """Reinhard tone mapping"""
        return image / (1.0 + image)
    
    def _apply_bloom(self, image: np.ndarray) -> np.ndarray:
        """Apply bloom post-processing effect"""
        
        # Extract bright areas
        threshold = 1.0
        bright_mask = np.sum(image, axis=2, keepdims=True) > threshold * 3
        bright_areas = image * bright_mask
        
        # Gaussian blur (simplified)
        from scipy import ndimage
        if 'ndimage' in globals():
            blurred = ndimage.gaussian_filter(bright_areas, sigma=5)
            
            # Combine with original
            bloom_strength = 0.1
            return image + blurred * bloom_strength
        
        return image
    
    def _apply_denoising(self, image: np.ndarray) -> np.ndarray:
        """Apply denoising filter"""
        
        # Simple bilateral filter approximation
        # In production would use OptiX or similar advanced denoiser
        
        try:
            from scipy import ndimage
            # Simple noise reduction
            denoised = ndimage.gaussian_filter(image, sigma=0.5)
            
            # Blend with original to preserve detail
            blend_factor = 0.7
            return image * (1 - blend_factor) + denoised * blend_factor
        except:
            return image
    
    def get_render_statistics(self) -> Dict[str, Any]:
        """Get rendering performance statistics"""
        
        return {
            "render_stats": self.render_stats.copy(),
            "memory_usage": self._estimate_memory_usage(),
            "acceleration_structure": {
                "bvh_enabled": self.bvh is not None,
                "primitive_count": len(self.primitives),
                "material_count": len(self.materials),
                "light_count": len(self.lights)
            },
            "quality_settings": {
                "samples_per_pixel": self.config["rendering"]["samples_per_pixel"],
                "max_ray_depth": self.config["rendering"]["max_ray_depth"],
                "resolution": f"{self.config['rendering']['width']}x{self.config['rendering']['height']}"
            }
        }
    
    def _estimate_memory_usage(self) -> Dict[str, float]:
        """Estimate memory usage in MB"""
        
        primitive_memory = len(self.primitives) * 0.1  # Rough estimate
        material_memory = len(self.materials) * 0.05
        light_memory = len(self.lights) * 0.01
        
        bvh_memory = 0
        if self.bvh:
            bvh_memory = len(self.primitives) * 0.2  # BVH overhead
        
        image_memory = (self.config["rendering"]["width"] * 
                       self.config["rendering"]["height"] * 
                       3 * 4) / (1024 * 1024)  # RGB float32
        
        return {
            "primitives": primitive_memory,
            "materials": material_memory,
            "lights": light_memory,
            "bvh": bvh_memory,
            "image_buffer": image_memory,
            "total": primitive_memory + material_memory + light_memory + bvh_memory + image_memory
        }

# Export main renderer
__all__ = ["PhotorealisticRaytracer", "Camera", "Material", "Light", "MaterialType", "LightType"]