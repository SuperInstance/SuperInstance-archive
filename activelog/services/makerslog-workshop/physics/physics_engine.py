import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from datetime import datetime


class ForceType(Enum):
    GRAVITY = "gravity"
    FRICTION = "friction"
    NORMAL = "normal"
    APPLIED = "applied"
    SPRING = "spring"
    DAMPING = "damping"
    MAGNETIC = "magnetic"


class MaterialProperty(Enum):
    DENSITY = "density"
    ELASTICITY = "elasticity"
    FRICTION_STATIC = "friction_static"
    FRICTION_KINETIC = "friction_kinetic"
    HARDNESS = "hardness"
    THERMAL_CONDUCTIVITY = "thermal_conductivity"
    ELECTRICAL_CONDUCTIVITY = "electrical_conductivity"


@dataclass
class Vector3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3D':
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3D':
        mag = self.magnitude()
        if mag == 0:
            return Vector3D(0, 0, 0)
        return Vector3D(self.x / mag, self.y / mag, self.z / mag)
    
    def dot(self, other: 'Vector3D') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )


@dataclass
class RigidBody:
    body_id: str
    position: Vector3D = field(default_factory=Vector3D)
    velocity: Vector3D = field(default_factory=Vector3D)
    acceleration: Vector3D = field(default_factory=Vector3D)
    rotation: Vector3D = field(default_factory=Vector3D)  # Euler angles
    angular_velocity: Vector3D = field(default_factory=Vector3D)
    angular_acceleration: Vector3D = field(default_factory=Vector3D)
    mass: float = 1.0
    moment_of_inertia: Vector3D = field(default_factory=lambda: Vector3D(1, 1, 1))
    forces: List[Tuple[ForceType, Vector3D]] = field(default_factory=list)
    torques: List[Vector3D] = field(default_factory=list)
    is_kinematic: bool = False  # Kinematic bodies are not affected by physics
    is_static: bool = False     # Static bodies don't move
    material_properties: Dict[MaterialProperty, float] = field(default_factory=dict)
    bounding_box: Tuple[Vector3D, Vector3D] = field(default_factory=lambda: (Vector3D(-0.5, -0.5, -0.5), Vector3D(0.5, 0.5, 0.5)))


@dataclass
class Joint:
    joint_id: str
    body_a_id: str
    body_b_id: str
    joint_type: str  # "fixed", "hinge", "ball", "slider"
    anchor_point_a: Vector3D
    anchor_point_b: Vector3D
    axis: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    limits: Optional[Tuple[float, float]] = None
    spring_constant: float = 0.0
    damping_constant: float = 0.0
    is_broken: bool = False


@dataclass
class Collision:
    body_a_id: str
    body_b_id: str
    contact_point: Vector3D
    contact_normal: Vector3D
    penetration_depth: float
    relative_velocity: Vector3D


class PhysicsEngine:
    def __init__(self):
        self.rigid_bodies: Dict[str, RigidBody] = {}
        self.joints: Dict[str, Joint] = {}
        self.gravity = Vector3D(0, 0, -9.81)  # Standard gravity
        self.time_step = 1.0 / 60.0  # 60 FPS
        self.simulation_running = False
        self.educational_mode = True
        self.slow_motion_factor = 1.0
        self.collision_pairs: List[Collision] = []
        
        # Material property defaults
        self.material_defaults = {
            MaterialProperty.DENSITY: {
                "metal": 7800.0,    # kg/m³
                "plastic": 950.0,
                "wood": 600.0,
                "rubber": 1200.0,
                "glass": 2500.0
            },
            MaterialProperty.FRICTION_STATIC: {
                "metal": 0.7,
                "plastic": 0.4,
                "wood": 0.6,
                "rubber": 1.0,
                "glass": 0.9
            },
            MaterialProperty.FRICTION_KINETIC: {
                "metal": 0.5,
                "plastic": 0.3,
                "wood": 0.4,
                "rubber": 0.8,
                "glass": 0.6
            },
            MaterialProperty.ELASTICITY: {
                "metal": 0.2,
                "plastic": 0.8,
                "wood": 0.3,
                "rubber": 0.9,
                "glass": 0.1
            }
        }

    def add_rigid_body(self, body: RigidBody):
        """Add a rigid body to the physics simulation"""
        # Set default material properties if not specified
        if not body.material_properties:
            body.material_properties = self._get_default_material_properties("plastic")
        
        self.rigid_bodies[body.body_id] = body
        
        return {
            "success": True,
            "body_id": body.body_id,
            "physics_enabled": not (body.is_kinematic or body.is_static)
        }

    def remove_rigid_body(self, body_id: str):
        """Remove a rigid body from simulation"""
        if body_id in self.rigid_bodies:
            del self.rigid_bodies[body_id]
            
            # Remove any joints connected to this body
            joints_to_remove = [joint_id for joint_id, joint in self.joints.items()
                              if joint.body_a_id == body_id or joint.body_b_id == body_id]
            
            for joint_id in joints_to_remove:
                del self.joints[joint_id]
            
            return {"success": True}
        
        return {"success": False, "error": "Body not found"}

    def add_joint(self, joint: Joint):
        """Add a joint constraint between two bodies"""
        if joint.body_a_id not in self.rigid_bodies or joint.body_b_id not in self.rigid_bodies:
            return {"success": False, "error": "One or both bodies not found"}
        
        self.joints[joint.joint_id] = joint
        
        return {
            "success": True,
            "joint_id": joint.joint_id,
            "joint_type": joint.joint_type,
            "educational_info": self._get_joint_educational_info(joint)
        }

    def apply_force(self, body_id: str, force: Vector3D, force_type: ForceType = ForceType.APPLIED,
                   point_of_application: Optional[Vector3D] = None):
        """Apply a force to a rigid body"""
        if body_id not in self.rigid_bodies:
            return {"success": False, "error": "Body not found"}
        
        body = self.rigid_bodies[body_id]
        
        if body.is_static or body.is_kinematic:
            return {"success": False, "error": "Cannot apply force to static or kinematic body"}
        
        body.forces.append((force_type, force))
        
        # Calculate torque if force is applied at a point
        if point_of_application:
            relative_pos = point_of_application - body.position
            torque = relative_pos.cross(force)
            body.torques.append(torque)
        
        return {
            "success": True,
            "force_applied": {"x": force.x, "y": force.y, "z": force.z},
            "force_type": force_type.value,
            "educational_explanation": self._explain_force_effect(force_type, force, body.mass)
        }

    def step_simulation(self, delta_time: Optional[float] = None):
        """Advance the physics simulation by one time step"""
        if not self.simulation_running:
            return
        
        dt = delta_time or (self.time_step * self.slow_motion_factor)
        
        # Clear collision list
        self.collision_pairs.clear()
        
        # Detect collisions
        self._detect_collisions()
        
        # Apply forces and integrate motion
        for body in self.rigid_bodies.values():
            if not body.is_static and not body.is_kinematic:
                self._integrate_forces(body, dt)
                self._integrate_motion(body, dt)
        
        # Resolve collisions
        self._resolve_collisions()
        
        # Apply joint constraints
        self._apply_joint_constraints(dt)
        
        return {
            "collision_count": len(self.collision_pairs),
            "active_bodies": len([b for b in self.rigid_bodies.values() if not b.is_static]),
            "total_kinetic_energy": self._calculate_total_kinetic_energy(),
            "educational_observations": self._generate_educational_observations()
        }

    def _integrate_forces(self, body: RigidBody, dt: float):
        """Integrate forces to calculate acceleration"""
        # Sum all forces
        net_force = Vector3D()
        for force_type, force in body.forces:
            net_force = net_force + force
        
        # Add gravity
        gravity_force = self.gravity * body.mass
        net_force = net_force + gravity_force
        
        # Calculate acceleration (F = ma)
        body.acceleration = net_force * (1.0 / body.mass)
        
        # Sum all torques
        net_torque = Vector3D()
        for torque in body.torques:
            net_torque = net_torque + torque
        
        # Calculate angular acceleration (τ = Iα)
        body.angular_acceleration = Vector3D(
            net_torque.x / body.moment_of_inertia.x,
            net_torque.y / body.moment_of_inertia.y,
            net_torque.z / body.moment_of_inertia.z
        )
        
        # Clear forces and torques for next frame
        body.forces.clear()
        body.torques.clear()

    def _integrate_motion(self, body: RigidBody, dt: float):
        """Integrate motion using Verlet integration"""
        # Update velocity
        body.velocity = body.velocity + body.acceleration * dt
        body.angular_velocity = body.angular_velocity + body.angular_acceleration * dt
        
        # Apply damping
        damping_factor = 0.99
        body.velocity = body.velocity * damping_factor
        body.angular_velocity = body.angular_velocity * damping_factor
        
        # Update position
        body.position = body.position + body.velocity * dt
        body.rotation = body.rotation + body.angular_velocity * dt
        
        # Keep rotation angles in reasonable range
        body.rotation.x = body.rotation.x % (2 * math.pi)
        body.rotation.y = body.rotation.y % (2 * math.pi)
        body.rotation.z = body.rotation.z % (2 * math.pi)

    def _detect_collisions(self):
        """Detect collisions between all rigid bodies"""
        bodies = list(self.rigid_bodies.values())
        
        for i, body_a in enumerate(bodies):
            for body_b in bodies[i + 1:]:
                # Skip collision detection for static-static pairs
                if body_a.is_static and body_b.is_static:
                    continue
                
                collision = self._check_aabb_collision(body_a, body_b)
                if collision:
                    self.collision_pairs.append(collision)

    def _check_aabb_collision(self, body_a: RigidBody, body_b: RigidBody) -> Optional[Collision]:
        """Check collision using Axis-Aligned Bounding Box (AABB)"""
        # Transform bounding boxes to world space
        min_a = body_a.position + body_a.bounding_box[0]
        max_a = body_a.position + body_a.bounding_box[1]
        min_b = body_b.position + body_b.bounding_box[0]
        max_b = body_b.position + body_b.bounding_box[1]
        
        # Check for overlap
        overlap_x = max(0, min(max_a.x, max_b.x) - max(min_a.x, min_b.x))
        overlap_y = max(0, min(max_a.y, max_b.y) - max(min_a.y, min_b.y))
        overlap_z = max(0, min(max_a.z, max_b.z) - max(min_a.z, min_b.z))
        
        if overlap_x > 0 and overlap_y > 0 and overlap_z > 0:
            # Calculate contact point and normal
            contact_point = Vector3D(
                (body_a.position.x + body_b.position.x) / 2,
                (body_a.position.y + body_b.position.y) / 2,
                (body_a.position.z + body_b.position.z) / 2
            )
            
            # Simple normal calculation (towards body_a)
            direction = body_a.position - body_b.position
            contact_normal = direction.normalize()
            
            # Penetration depth (minimum overlap)
            penetration_depth = min(overlap_x, overlap_y, overlap_z)
            
            # Relative velocity
            relative_velocity = body_a.velocity - body_b.velocity
            
            return Collision(
                body_a_id=body_a.body_id,
                body_b_id=body_b.body_id,
                contact_point=contact_point,
                contact_normal=contact_normal,
                penetration_depth=penetration_depth,
                relative_velocity=relative_velocity
            )
        
        return None

    def _resolve_collisions(self):
        """Resolve all detected collisions"""
        for collision in self.collision_pairs:
            body_a = self.rigid_bodies[collision.body_a_id]
            body_b = self.rigid_bodies[collision.body_b_id]
            
            # Skip if both bodies are static
            if body_a.is_static and body_b.is_static:
                continue
            
            # Calculate masses for impulse resolution
            mass_a = body_a.mass if not body_a.is_static else float('inf')
            mass_b = body_b.mass if not body_b.is_static else float('inf')
            
            # Calculate restitution (bounciness)
            restitution = self._calculate_restitution(body_a, body_b)
            
            # Relative velocity in collision normal direction
            relative_velocity_normal = collision.relative_velocity.dot(collision.contact_normal)
            
            # Don't resolve if velocities are separating
            if relative_velocity_normal > 0:
                continue
            
            # Calculate collision impulse
            impulse_magnitude = -(1 + restitution) * relative_velocity_normal
            impulse_magnitude /= (1/mass_a + 1/mass_b)
            
            impulse = collision.contact_normal * impulse_magnitude
            
            # Apply impulse to bodies
            if not body_a.is_static:
                body_a.velocity = body_a.velocity + impulse * (1/mass_a)
            
            if not body_b.is_static:
                body_b.velocity = body_b.velocity - impulse * (1/mass_b)
            
            # Position correction to prevent sinking
            percent = 0.2  # Usually 20% to 80%
            slop = 0.01    # Usually 0.01 to 0.1
            
            correction_magnitude = max(collision.penetration_depth - slop, 0) / (1/mass_a + 1/mass_b) * percent
            correction = collision.contact_normal * correction_magnitude
            
            if not body_a.is_static:
                body_a.position = body_a.position + correction * (1/mass_a)
            
            if not body_b.is_static:
                body_b.position = body_b.position - correction * (1/mass_b)

    def _calculate_restitution(self, body_a: RigidBody, body_b: RigidBody) -> float:
        """Calculate coefficient of restitution between two materials"""
        elasticity_a = body_a.material_properties.get(MaterialProperty.ELASTICITY, 0.5)
        elasticity_b = body_b.material_properties.get(MaterialProperty.ELASTICITY, 0.5)
        
        # Combine elasticities (geometric mean)
        return math.sqrt(elasticity_a * elasticity_b)

    def _apply_joint_constraints(self, dt: float):
        """Apply joint constraints between connected bodies"""
        for joint in self.joints.values():
            if joint.is_broken:
                continue
            
            body_a = self.rigid_bodies[joint.body_a_id]
            body_b = self.rigid_bodies[joint.body_b_id]
            
            if joint.joint_type == "fixed":
                self._apply_fixed_joint(joint, body_a, body_b, dt)
            elif joint.joint_type == "hinge":
                self._apply_hinge_joint(joint, body_a, body_b, dt)
            elif joint.joint_type == "ball":
                self._apply_ball_joint(joint, body_a, body_b, dt)
            elif joint.joint_type == "slider":
                self._apply_slider_joint(joint, body_a, body_b, dt)

    def _apply_fixed_joint(self, joint: Joint, body_a: RigidBody, body_b: RigidBody, dt: float):
        """Apply fixed joint constraint (no relative motion allowed)"""
        # Calculate desired positions
        world_anchor_a = body_a.position + joint.anchor_point_a
        world_anchor_b = body_b.position + joint.anchor_point_b
        
        # Position error
        position_error = world_anchor_b - world_anchor_a
        
        # Apply corrective forces
        if position_error.magnitude() > 0.001:  # Small threshold
            correction_force = position_error * joint.spring_constant * 1000  # Strong constraint
            
            if not body_a.is_static:
                self.apply_force(body_a.body_id, correction_force, ForceType.SPRING)
            
            if not body_b.is_static:
                self.apply_force(body_b.body_id, correction_force * -1, ForceType.SPRING)

    def _apply_hinge_joint(self, joint: Joint, body_a: RigidBody, body_b: RigidBody, dt: float):
        """Apply hinge joint constraint (rotation around one axis)"""
        # Position constraint (bodies stay connected)
        world_anchor_a = body_a.position + joint.anchor_point_a
        world_anchor_b = body_b.position + joint.anchor_point_b
        
        position_error = world_anchor_b - world_anchor_a
        
        if position_error.magnitude() > 0.001:
            correction_force = position_error * joint.spring_constant * 500
            
            if not body_a.is_static:
                self.apply_force(body_a.body_id, correction_force, ForceType.SPRING)
            
            if not body_b.is_static:
                self.apply_force(body_b.body_id, correction_force * -1, ForceType.SPRING)

    def _apply_ball_joint(self, joint: Joint, body_a: RigidBody, body_b: RigidBody, dt: float):
        """Apply ball joint constraint (no translation, free rotation)"""
        # Only position constraint
        self._apply_fixed_joint(joint, body_a, body_b, dt)

    def _apply_slider_joint(self, joint: Joint, body_a: RigidBody, body_b: RigidBody, dt: float):
        """Apply slider joint constraint (translation along one axis only)"""
        # More complex constraint - would need full implementation
        pass

    def _calculate_total_kinetic_energy(self) -> float:
        """Calculate total kinetic energy in the system"""
        total_ke = 0.0
        
        for body in self.rigid_bodies.values():
            if not body.is_static:
                # Translational kinetic energy
                linear_ke = 0.5 * body.mass * (body.velocity.magnitude() ** 2)
                
                # Rotational kinetic energy
                angular_ke = 0.5 * (
                    body.moment_of_inertia.x * (body.angular_velocity.x ** 2) +
                    body.moment_of_inertia.y * (body.angular_velocity.y ** 2) +
                    body.moment_of_inertia.z * (body.angular_velocity.z ** 2)
                )
                
                total_ke += linear_ke + angular_ke
        
        return total_ke

    def _generate_educational_observations(self) -> List[Dict]:
        """Generate educational observations about the current physics state"""
        observations = []
        
        # Energy conservation
        total_ke = self._calculate_total_kinetic_energy()
        if total_ke > 0.1:
            observations.append({
                "type": "energy",
                "title": "Kinetic Energy",
                "description": f"The system has {total_ke:.2f} J of kinetic energy",
                "educational_note": "Kinetic energy is the energy of motion"
            })
        
        # Collision observations
        if self.collision_pairs:
            observations.append({
                "type": "collision",
                "title": "Collision Detected",
                "description": f"{len(self.collision_pairs)} collision(s) occurring",
                "educational_note": "Collisions demonstrate conservation of momentum"
            })
        
        # Force observations
        for body in self.rigid_bodies.values():
            if len(body.forces) > 0:
                observations.append({
                    "type": "force",
                    "title": "Forces Acting",
                    "description": f"{len(body.forces)} forces acting on {body.body_id}",
                    "educational_note": "Forces cause acceleration (F = ma)"
                })
                break  # Just show one example
        
        return observations

    def _explain_force_effect(self, force_type: ForceType, force: Vector3D, mass: float) -> str:
        """Generate educational explanation of force effects"""
        force_magnitude = force.magnitude()
        acceleration = force_magnitude / mass
        
        explanations = {
            ForceType.GRAVITY: f"Gravity pulls objects downward with {force_magnitude:.2f}N force",
            ForceType.APPLIED: f"Applied force of {force_magnitude:.2f}N causes {acceleration:.2f} m/s² acceleration",
            ForceType.FRICTION: f"Friction opposes motion with {force_magnitude:.2f}N force",
            ForceType.SPRING: f"Spring force of {force_magnitude:.2f}N tries to restore position"
        }
        
        return explanations.get(force_type, f"Force of {force_magnitude:.2f}N applied")

    def _get_joint_educational_info(self, joint: Joint) -> Dict:
        """Get educational information about joint types"""
        joint_info = {
            "fixed": {
                "description": "Fixed joints prevent all relative motion",
                "examples": "Welded connections, glued parts",
                "degrees_of_freedom": 0
            },
            "hinge": {
                "description": "Hinge joints allow rotation around one axis",
                "examples": "Door hinges, elbow joints",
                "degrees_of_freedom": 1
            },
            "ball": {
                "description": "Ball joints allow rotation in all directions",
                "examples": "Shoulder joints, car steering",
                "degrees_of_freedom": 3
            },
            "slider": {
                "description": "Slider joints allow translation along one axis",
                "examples": "Drawer slides, hydraulic pistons",
                "degrees_of_freedom": 1
            }
        }
        
        return joint_info.get(joint.joint_type, {"description": "Unknown joint type"})

    def _get_default_material_properties(self, material_name: str) -> Dict[MaterialProperty, float]:
        """Get default material properties for a given material"""
        properties = {}
        
        for prop in MaterialProperty:
            if prop in self.material_defaults:
                properties[prop] = self.material_defaults[prop].get(material_name, 1.0)
        
        return properties

    def start_simulation(self):
        """Start the physics simulation"""
        self.simulation_running = True
        return {"success": True, "message": "Physics simulation started"}

    def stop_simulation(self):
        """Stop the physics simulation"""
        self.simulation_running = False
        return {"success": True, "message": "Physics simulation stopped"}

    def reset_simulation(self):
        """Reset all bodies to their initial state"""
        for body in self.rigid_bodies.values():
            body.velocity = Vector3D()
            body.angular_velocity = Vector3D()
            body.acceleration = Vector3D()
            body.angular_acceleration = Vector3D()
            body.forces.clear()
            body.torques.clear()
        
        self.collision_pairs.clear()
        
        return {"success": True, "message": "Physics simulation reset"}

    def set_gravity(self, gravity_vector: Vector3D):
        """Set gravity direction and magnitude"""
        self.gravity = gravity_vector
        
        return {
            "success": True,
            "gravity": {"x": gravity_vector.x, "y": gravity_vector.y, "z": gravity_vector.z},
            "educational_note": "Gravity affects all objects with mass equally"
        }

    def set_slow_motion(self, factor: float):
        """Set slow motion factor for educational purposes"""
        self.slow_motion_factor = max(0.1, min(factor, 2.0))  # Clamp between 0.1x and 2x
        
        return {
            "success": True,
            "slow_motion_factor": self.slow_motion_factor,
            "educational_note": f"Time is running at {self.slow_motion_factor}x normal speed"
        }

    def get_body_state(self, body_id: str) -> Optional[Dict]:
        """Get current state of a rigid body"""
        if body_id not in self.rigid_bodies:
            return None
        
        body = self.rigid_bodies[body_id]
        
        return {
            "body_id": body_id,
            "position": {"x": body.position.x, "y": body.position.y, "z": body.position.z},
            "velocity": {"x": body.velocity.x, "y": body.velocity.y, "z": body.velocity.z},
            "rotation": {"x": body.rotation.x, "y": body.rotation.y, "z": body.rotation.z},
            "angular_velocity": {"x": body.angular_velocity.x, "y": body.angular_velocity.y, "z": body.angular_velocity.z},
            "mass": body.mass,
            "kinetic_energy": 0.5 * body.mass * (body.velocity.magnitude() ** 2),
            "is_moving": body.velocity.magnitude() > 0.01,
            "forces_applied": len(body.forces)
        }

    def get_simulation_state(self) -> Dict:
        """Get overall simulation state"""
        return {
            "running": self.simulation_running,
            "time_step": self.time_step,
            "slow_motion_factor": self.slow_motion_factor,
            "gravity": {"x": self.gravity.x, "y": self.gravity.y, "z": self.gravity.z},
            "total_bodies": len(self.rigid_bodies),
            "active_bodies": len([b for b in self.rigid_bodies.values() if not b.is_static]),
            "total_joints": len(self.joints),
            "active_collisions": len(self.collision_pairs),
            "total_kinetic_energy": self._calculate_total_kinetic_energy(),
            "educational_mode": self.educational_mode
        }

    def demonstrate_physics_concept(self, concept: str, bodies: List[str]) -> Dict:
        """Demonstrate a specific physics concept with selected bodies"""
        demonstrations = {
            "gravity": self._demonstrate_gravity,
            "friction": self._demonstrate_friction,
            "momentum": self._demonstrate_momentum,
            "energy_conservation": self._demonstrate_energy_conservation,
            "springs": self._demonstrate_springs,
            "pendulum": self._demonstrate_pendulum
        }
        
        if concept in demonstrations:
            return demonstrations[concept](bodies)
        else:
            return {"success": False, "error": "Unknown physics concept"}

    def _demonstrate_gravity(self, bodies: List[str]) -> Dict:
        """Demonstrate gravity by dropping objects"""
        for body_id in bodies:
            if body_id in self.rigid_bodies:
                body = self.rigid_bodies[body_id]
                # Lift the body up
                body.position.z += 2.0
                body.velocity = Vector3D()  # Stop any existing motion
        
        return {
            "success": True,
            "concept": "gravity",
            "explanation": "All objects fall at the same rate regardless of their mass",
            "observation": "Watch how different objects fall at the same speed",
            "physics_law": "F = mg (gravitational force equals mass times gravitational acceleration)"
        }

    def _demonstrate_friction(self, bodies: List[str]) -> Dict:
        """Demonstrate friction by applying horizontal forces"""
        for body_id in bodies:
            if body_id in self.rigid_bodies:
                # Apply horizontal force
                force = Vector3D(10.0, 0, 0)
                self.apply_force(body_id, force, ForceType.APPLIED)
        
        return {
            "success": True,
            "concept": "friction",
            "explanation": "Friction opposes motion between surfaces in contact",
            "observation": "Notice how objects with different surface materials move differently",
            "physics_law": "F_friction = μ × N (friction force equals coefficient times normal force)"
        }

    def _demonstrate_momentum(self, bodies: List[str]) -> Dict:
        """Demonstrate momentum conservation with collisions"""
        if len(bodies) >= 2:
            # Set up collision scenario
            body_a = self.rigid_bodies[bodies[0]]
            body_b = self.rigid_bodies[bodies[1]]
            
            # Position bodies for collision
            body_a.position = Vector3D(-2, 0, 0)
            body_b.position = Vector3D(2, 0, 0)
            
            # Give initial velocities
            body_a.velocity = Vector3D(3, 0, 0)
            body_b.velocity = Vector3D(-1, 0, 0)
        
        return {
            "success": True,
            "concept": "momentum_conservation",
            "explanation": "In collisions, total momentum is conserved",
            "observation": "Watch how momentum transfers between colliding objects",
            "physics_law": "p = mv (momentum equals mass times velocity)"
        }

    def _demonstrate_energy_conservation(self, bodies: List[str]) -> Dict:
        """Demonstrate energy conservation with a pendulum-like motion"""
        for body_id in bodies:
            if body_id in self.rigid_bodies:
                body = self.rigid_bodies[body_id]
                # Set up for energy demonstration
                body.position = Vector3D(0, 0, 3)  # High potential energy
                body.velocity = Vector3D()  # Zero kinetic energy
        
        return {
            "success": True,
            "concept": "energy_conservation",
            "explanation": "Energy converts between kinetic and potential forms",
            "observation": "Watch potential energy convert to kinetic energy as objects fall",
            "physics_law": "E_total = KE + PE (total energy is kinetic plus potential energy)"
        }

    def _demonstrate_springs(self, bodies: List[str]) -> Dict:
        """Demonstrate spring forces"""
        return {
            "success": True,
            "concept": "springs",
            "explanation": "Springs exert forces proportional to displacement",
            "physics_law": "F = -kx (Hooke's Law)"
        }

    def _demonstrate_pendulum(self, bodies: List[str]) -> Dict:
        """Demonstrate pendulum motion"""
        return {
            "success": True,
            "concept": "pendulum",
            "explanation": "Pendulums demonstrate periodic motion and energy exchange",
            "physics_law": "T = 2π√(L/g) (period depends on length and gravity)"
        }

    def break_joint(self, joint_id: str, reason: str = "excessive_force") -> Dict:
        """Break a joint due to excessive force or other reasons"""
        if joint_id not in self.joints:
            return {"success": False, "error": "Joint not found"}
        
        joint = self.joints[joint_id]
        joint.is_broken = True
        
        return {
            "success": True,
            "joint_id": joint_id,
            "reason": reason,
            "educational_note": "Joints can break when forces exceed their strength limits",
            "repair_suggestion": "Consider using stronger materials or better joint design"
        }

    def repair_joint(self, joint_id: str) -> Dict:
        """Repair a broken joint"""
        if joint_id not in self.joints:
            return {"success": False, "error": "Joint not found"}
        
        joint = self.joints[joint_id]
        joint.is_broken = False
        
        return {
            "success": True,
            "joint_id": joint_id,
            "educational_note": "Joint has been repaired and constraints are active again"
        }