"""
Wiring Diagram Generator
Automatic generation of wiring diagrams for marine engine monitoring systems
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ConnectorType(Enum):
    """Types of electrical connectors"""
    TERMINAL_BLOCK = "terminal_block"
    MOLEX = "molex"
    DEUTSCH = "deutsch"
    AMP_SUPERSEAL = "amp_superseal"
    CIRCULAR_CONNECTOR = "circular_connector"
    PHOENIX = "phoenix"
    WAGO = "wago"
    SCREW_TERMINAL = "screw_terminal"
    PUSH_IN = "push_in"
    RJ45 = "rj45"
    USB = "usb"
    RS232 = "rs232"
    RS485 = "rs485"


class WireType(Enum):
    """Types of wires/cables"""
    SINGLE_CORE = "single_core"
    MULTI_CORE = "multi_core"
    SHIELDED = "shielded"
    TWISTED_PAIR = "twisted_pair"
    COAX = "coax"
    CAN_BUS = "can_bus"
    NMEA_2000 = "nmea_2000"
    ETHERNET = "ethernet"


class ComponentType(Enum):
    """Types of system components"""
    SENSOR = "sensor"
    DISPLAY = "display"
    CONTROLLER = "controller"
    GATEWAY = "gateway"
    POWER_SUPPLY = "power_supply"
    JUNCTION_BOX = "junction_box"
    TERMINATOR = "terminator"
    FUSE = "fuse"
    RELAY = "relay"
    SWITCH = "switch"


@dataclass
class WireSpec:
    """Wire/cable specification"""
    wire_id: str
    wire_type: WireType
    gauge_awg: int
    cores: int = 1
    color: str = "black"
    shielded: bool = False
    length_meters: float = 1.0
    voltage_rating: int = 12
    current_rating: float = 10.0
    temperature_rating: int = 85
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'wire_id': self.wire_id,
            'wire_type': self.wire_type.value,
            'gauge_awg': self.gauge_awg,
            'cores': self.cores,
            'color': self.color,
            'shielded': self.shielded,
            'length_meters': self.length_meters,
            'voltage_rating': self.voltage_rating,
            'current_rating': self.current_rating,
            'temperature_rating': self.temperature_rating,
            'description': self.description
        }


@dataclass
class Connector:
    """Electrical connector specification"""
    connector_id: str
    connector_type: ConnectorType
    pins: int
    pin_assignments: Dict[int, str] = field(default_factory=dict)
    voltage_rating: int = 12
    current_rating: float = 10.0
    ip_rating: str = "IP65"
    material: str = "plastic"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'connector_id': self.connector_id,
            'connector_type': self.connector_type.value,
            'pins': self.pins,
            'pin_assignments': self.pin_assignments,
            'voltage_rating': self.voltage_rating,
            'current_rating': self.current_rating,
            'ip_rating': self.ip_rating,
            'material': self.material,
            'description': self.description
        }


@dataclass
class Component:
    """System component specification"""
    component_id: str
    component_type: ComponentType
    name: str
    model: str = ""
    manufacturer: str = ""
    connectors: List[Connector] = field(default_factory=list)
    power_requirements: Dict[str, Any] = field(default_factory=dict)
    installation_notes: List[str] = field(default_factory=list)
    position: Tuple[float, float] = (0.0, 0.0)  # X, Y coordinates for diagram
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'component_id': self.component_id,
            'component_type': self.component_type.value,
            'name': self.name,
            'model': self.model,
            'manufacturer': self.manufacturer,
            'connectors': [c.to_dict() for c in self.connectors],
            'power_requirements': self.power_requirements,
            'installation_notes': self.installation_notes,
            'position': self.position
        }


@dataclass
class Connection:
    """Wire connection between components"""
    connection_id: str
    from_component: str
    from_connector: str
    from_pin: int
    to_component: str
    to_connector: str
    to_pin: int
    wire_spec: WireSpec
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'from_component': self.from_component,
            'from_connector': self.from_connector,
            'from_pin': self.from_pin,
            'to_component': self.to_component,
            'to_connector': self.to_connector,
            'to_pin': self.to_pin,
            'wire_spec': self.wire_spec.to_dict(),
            'notes': self.notes
        }


@dataclass
class WiringDiagram:
    """Complete wiring diagram"""
    diagram_id: str
    name: str
    description: str
    components: List[Component] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    power_distribution: Dict[str, Any] = field(default_factory=dict)
    ground_points: List[str] = field(default_factory=list)
    fusing: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'diagram_id': self.diagram_id,
            'name': self.name,
            'description': self.description,
            'components': [c.to_dict() for c in self.components],
            'connections': [c.to_dict() for c in self.connections],
            'power_distribution': self.power_distribution,
            'ground_points': self.ground_points,
            'fusing': self.fusing,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }


class WiringDiagramGenerator:
    """Main wiring diagram generator"""
    
    def __init__(self):
        self.component_library: Dict[str, Component] = {}
        self.wire_library: Dict[str, WireSpec] = {}
        self.diagrams: Dict[str, WiringDiagram] = {}
        
        # Initialize component library
        self._initialize_component_library()
        self._initialize_wire_library()
        
        logger.info("WiringDiagramGenerator initialized")
    
    def _initialize_component_library(self):
        """Initialize standard component library"""
        # Engine monitoring components
        components = [
            Component(
                component_id="engine_gateway",
                component_type=ComponentType.GATEWAY,
                name="Engine Gateway",
                model="EG-2000",
                manufacturer="Marine Systems Inc",
                connectors=[
                    Connector("nmea_conn", ConnectorType.CIRCULAR_CONNECTOR, 5, {
                        1: "NMEA_H", 2: "NMEA_L", 3: "SHIELD", 4: "12V", 5: "GND"
                    }),
                    Connector("can_conn", ConnectorType.DEUTSCH, 4, {
                        1: "CAN_H", 2: "CAN_L", 3: "12V", 4: "GND"
                    })
                ],
                power_requirements={"voltage": 12, "current": 0.5, "power": 6},
                position=(100, 100)
            ),
            
            Component(
                component_id="temp_sensor",
                component_type=ComponentType.SENSOR,
                name="Temperature Sensor",
                model="TS-485",
                manufacturer="SensorTech",
                connectors=[
                    Connector("main_conn", ConnectorType.AMP_SUPERSEAL, 3, {
                        1: "SIGNAL+", 2: "SIGNAL-", 3: "SHIELD"
                    })
                ],
                power_requirements={"voltage": 12, "current": 0.02, "power": 0.24},
                position=(300, 200)
            ),
            
            Component(
                component_id="pressure_sensor",
                component_type=ComponentType.SENSOR,
                name="Pressure Sensor",
                model="PS-420MA",
                manufacturer="PressureMax",
                connectors=[
                    Connector("output_conn", ConnectorType.MOLEX, 2, {
                        1: "4-20mA+", 2: "4-20mA-"
                    })
                ],
                power_requirements={"voltage": 24, "current": 0.02, "power": 0.48},
                position=(300, 300)
            ),
            
            Component(
                component_id="display_unit",
                component_type=ComponentType.DISPLAY,
                name="Engine Display",
                model="ED-7000",
                manufacturer="Marine Displays",
                connectors=[
                    Connector("nmea_in", ConnectorType.CIRCULAR_CONNECTOR, 5, {
                        1: "NMEA_H", 2: "NMEA_L", 3: "SHIELD", 4: "12V", 5: "GND"
                    }),
                    Connector("power_conn", ConnectorType.PHOENIX, 2, {
                        1: "12V", 2: "GND"
                    })
                ],
                power_requirements={"voltage": 12, "current": 0.8, "power": 9.6},
                position=(500, 100)
            ),
            
            Component(
                component_id="power_supply",
                component_type=ComponentType.POWER_SUPPLY,
                name="24V Power Supply",
                model="PSU-24-5A",
                manufacturer="PowerTech",
                connectors=[
                    Connector("ac_input", ConnectorType.SCREW_TERMINAL, 3, {
                        1: "AC_L", 2: "AC_N", 3: "AC_PE"
                    }),
                    Connector("dc_output", ConnectorType.SCREW_TERMINAL, 2, {
                        1: "24V+", 2: "24V-"
                    })
                ],
                power_requirements={"input_voltage": 230, "output_voltage": 24, "output_current": 5},
                position=(50, 200)
            )
        ]
        
        for component in components:
            self.component_library[component.component_id] = component
    
    def _initialize_wire_library(self):
        """Initialize standard wire library"""
        wires = [
            WireSpec("nmea_cable", WireType.NMEA_2000, 18, 5, "yellow", True, 10.0),
            WireSpec("can_cable", WireType.CAN_BUS, 18, 2, "blue", True, 5.0),
            WireSpec("power_12v", WireType.SINGLE_CORE, 14, 1, "red", False, 3.0),
            WireSpec("ground", WireType.SINGLE_CORE, 14, 1, "black", False, 3.0),
            WireSpec("analog_signal", WireType.SHIELDED, 20, 2, "gray", True, 5.0),
            WireSpec("digital_io", WireType.MULTI_CORE, 22, 4, "white", False, 2.0),
            WireSpec("rs485_cable", WireType.TWISTED_PAIR, 20, 2, "green", True, 8.0),
            WireSpec("ethernet_cable", WireType.ETHERNET, 24, 8, "blue", True, 15.0)
        ]
        
        for wire in wires:
            self.wire_library[wire.wire_id] = wire
    
    def create_engine_monitoring_diagram(self, engine_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create wiring diagram for engine monitoring system"""
        try:
            diagram_id = f"engine_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            diagram = WiringDiagram(
                diagram_id=diagram_id,
                name="Engine Monitoring System",
                description="Complete wiring diagram for marine engine monitoring"
            )
            
            # Add core components
            components_to_add = ["engine_gateway", "display_unit", "power_supply"]
            
            # Add sensors based on configuration
            sensor_types = engine_config.get('sensors', [])
            for sensor_type in sensor_types:
                if sensor_type == 'temperature':
                    components_to_add.append("temp_sensor")
                elif sensor_type == 'pressure':
                    components_to_add.append("pressure_sensor")
            
            # Add components to diagram
            for comp_id in components_to_add:
                if comp_id in self.component_library:
                    diagram.components.append(self.component_library[comp_id])
            
            # Create connections
            connections = self._generate_connections(diagram.components)
            diagram.connections.extend(connections)
            
            # Add power distribution
            diagram.power_distribution = self._calculate_power_distribution(diagram.components)
            
            # Add fusing recommendations
            diagram.fusing = self._calculate_fusing(diagram.components)
            
            # Add installation notes
            diagram.notes = self._generate_installation_notes(diagram)
            
            # Store diagram
            self.diagrams[diagram_id] = diagram
            
            logger.info(f"Created engine monitoring diagram: {diagram_id}")
            return {
                "success": True,
                "diagram_id": diagram_id,
                "diagram": {
                    "components": [c.component_id for c in diagram.components],
                    "connections": len(diagram.connections),
                    "notes": diagram.notes
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating engine monitoring diagram: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_connections(self, components: List[Component]) -> List[Connection]:
        """Generate connections between components"""
        connections = []
        connection_counter = 1
        
        try:
            # Find components by type
            gateways = [c for c in components if c.component_type == ComponentType.GATEWAY]
            sensors = [c for c in components if c.component_type == ComponentType.SENSOR]
            displays = [c for c in components if c.component_type == ComponentType.DISPLAY]
            power_supplies = [c for c in components if c.component_type == ComponentType.POWER_SUPPLY]
            
            # Connect sensors to gateway
            if gateways and sensors:
                gateway = gateways[0]
                
                for sensor in sensors:
                    if sensor.name == "Temperature Sensor":
                        # RS485 connection
                        conn = Connection(
                            connection_id=f"conn_{connection_counter:03d}",
                            from_component=sensor.component_id,
                            from_connector="main_conn",
                            from_pin=1,
                            to_component=gateway.component_id,
                            to_connector="rs485_conn",
                            to_pin=1,
                            wire_spec=self.wire_library["rs485_cable"]
                        )
                        connections.append(conn)
                        connection_counter += 1
                    
                    elif sensor.name == "Pressure Sensor":
                        # 4-20mA analog connection
                        conn = Connection(
                            connection_id=f"conn_{connection_counter:03d}",
                            from_component=sensor.component_id,
                            from_connector="output_conn",
                            from_pin=1,
                            to_component=gateway.component_id,
                            to_connector="analog_in",
                            to_pin=1,
                            wire_spec=self.wire_library["analog_signal"]
                        )
                        connections.append(conn)
                        connection_counter += 1
            
            # Connect gateway to display via NMEA
            if gateways and displays:
                gateway = gateways[0]
                display = displays[0]
                
                conn = Connection(
                    connection_id=f"conn_{connection_counter:03d}",
                    from_component=gateway.component_id,
                    from_connector="nmea_conn",
                    from_pin=1,
                    to_component=display.component_id,
                    to_connector="nmea_in",
                    to_pin=1,
                    wire_spec=self.wire_library["nmea_cable"]
                )
                connections.append(conn)
                connection_counter += 1
            
            # Add power connections
            if power_supplies:
                power_supply = power_supplies[0]
                
                for component in components:
                    if component.component_type != ComponentType.POWER_SUPPLY:
                        # Power connection
                        conn = Connection(
                            connection_id=f"conn_{connection_counter:03d}",
                            from_component=power_supply.component_id,
                            from_connector="dc_output",
                            from_pin=1,
                            to_component=component.component_id,
                            to_connector="power_in",
                            to_pin=1,
                            wire_spec=self.wire_library["power_12v"]
                        )
                        connections.append(conn)
                        connection_counter += 1
                        
                        # Ground connection
                        conn = Connection(
                            connection_id=f"conn_{connection_counter:03d}",
                            from_component=power_supply.component_id,
                            from_connector="dc_output",
                            from_pin=2,
                            to_component=component.component_id,
                            to_connector="power_in",
                            to_pin=2,
                            wire_spec=self.wire_library["ground"]
                        )
                        connections.append(conn)
                        connection_counter += 1
            
        except Exception as e:
            logger.error(f"Error generating connections: {e}")
        
        return connections
    
    def _calculate_power_distribution(self, components: List[Component]) -> Dict[str, Any]:
        """Calculate power distribution requirements"""
        try:
            total_current_12v = 0.0
            total_current_24v = 0.0
            total_power = 0.0
            
            for component in components:
                power_req = component.power_requirements
                
                if power_req.get('voltage') == 12:
                    total_current_12v += power_req.get('current', 0)
                elif power_req.get('voltage') == 24:
                    total_current_24v += power_req.get('current', 0)
                
                total_power += power_req.get('power', 0)
            
            return {
                '12v_current_total': round(total_current_12v, 2),
                '24v_current_total': round(total_current_24v, 2),
                'total_power_watts': round(total_power, 2),
                'recommended_12v_supply': f"{round(total_current_12v * 1.25, 1)}A",
                'recommended_24v_supply': f"{round(total_current_24v * 1.25, 1)}A"
            }
            
        except Exception as e:
            logger.error(f"Error calculating power distribution: {e}")
            return {}
    
    def _calculate_fusing(self, components: List[Component]) -> Dict[str, float]:
        """Calculate fusing recommendations"""
        try:
            fusing = {}
            
            for component in components:
                power_req = component.power_requirements
                current = power_req.get('current', 0)
                
                if current > 0:
                    # Recommend fuse 25% above rated current
                    recommended_fuse = round(current * 1.25, 1)
                    fusing[component.component_id] = recommended_fuse
            
            return fusing
            
        except Exception as e:
            logger.error(f"Error calculating fusing: {e}")
            return {}
    
    def _generate_installation_notes(self, diagram: WiringDiagram) -> List[str]:
        """Generate installation notes for the diagram"""
        notes = [
            "Installation Notes:",
            "",
            "1. Power System:",
            "   - Install main power switch accessible from engine room",
            "   - Use marine-grade fuses and holders",
            "   - Ensure proper grounding to engine block",
            "",
            "2. Cable Routing:",
            "   - Route cables away from hot engine components",
            "   - Use cable ties every 300mm for support",
            "   - Maintain minimum bend radius per cable specifications",
            "",
            "3. Connections:",
            "   - Apply dielectric grease to all connectors",
            "   - Ensure proper connector orientation and seating",
            "   - Use heat shrink tubing on all splice connections",
            "",
            "4. Testing:",
            "   - Verify continuity of all connections before power-up",
            "   - Test system functionality at 50% and 100% power",
            "   - Document all sensor calibration values"
        ]
        
        # Add component-specific notes
        for component in diagram.components:
            if component.installation_notes:
                notes.extend([f"", f"{component.name} Specific:"])
                notes.extend([f"   - {note}" for note in component.installation_notes])
        
        return notes
    
    def get_diagram(self, diagram_id: str) -> Optional[WiringDiagram]:
        """Get wiring diagram by ID"""
        return self.diagrams.get(diagram_id)
    
    def get_all_diagrams(self) -> Dict[str, WiringDiagram]:
        """Get all wiring diagrams"""
        return self.diagrams.copy()
    
    def export_diagram_json(self, diagram_id: str) -> Optional[str]:
        """Export diagram as JSON"""
        try:
            diagram = self.diagrams.get(diagram_id)
            if diagram:
                return json.dumps(diagram.to_dict(), indent=2)
            return None
            
        except Exception as e:
            logger.error(f"Error exporting diagram {diagram_id}: {e}")
            return None
    
    def generate_parts_list(self, diagram_id: str) -> Dict[str, Any]:
        """Generate parts list for diagram"""
        try:
            diagram = self.diagrams.get(diagram_id)
            if not diagram:
                return {}
            
            parts_list = {
                'components': [],
                'cables': [],
                'connectors': [],
                'hardware': []
            }
            
            # Add components
            for component in diagram.components:
                parts_list['components'].append({
                    'part_number': component.model,
                    'description': component.name,
                    'manufacturer': component.manufacturer,
                    'quantity': 1,
                    'notes': 'Core system component'
                })
            
            # Add cables
            cable_counts = {}
            total_lengths = {}
            
            for connection in diagram.connections:
                wire_id = connection.wire_spec.wire_id
                
                if wire_id not in cable_counts:
                    cable_counts[wire_id] = 0
                    total_lengths[wire_id] = 0.0
                
                cable_counts[wire_id] += 1
                total_lengths[wire_id] += connection.wire_spec.length_meters
            
            for wire_id, count in cable_counts.items():
                wire_spec = self.wire_library.get(wire_id)
                if wire_spec:
                    parts_list['cables'].append({
                        'part_number': f"{wire_spec.wire_type.value.upper()}-{wire_spec.gauge_awg}AWG",
                        'description': f"{wire_spec.description or wire_spec.wire_id}",
                        'total_length_m': round(total_lengths[wire_id] * 1.1, 1),  # 10% extra
                        'connections': count,
                        'specifications': {
                            'gauge': f"{wire_spec.gauge_awg} AWG",
                            'cores': wire_spec.cores,
                            'voltage_rating': f"{wire_spec.voltage_rating}V",
                            'current_rating': f"{wire_spec.current_rating}A"
                        }
                    })
            
            # Add hardware
            parts_list['hardware'].extend([
                {'description': 'Cable ties (300mm spacing)', 'quantity': len(diagram.connections) * 3},
                {'description': 'Heat shrink tubing assortment', 'quantity': 1},
                {'description': 'Dielectric grease', 'quantity': 1},
                {'description': 'Marine fuse holders', 'quantity': len(diagram.fusing)},
                {'description': 'Marine fuses (assorted ratings)', 'quantity': len(diagram.fusing)},
                {'description': 'Ground lugs', 'quantity': len(diagram.components)},
                {'description': 'Mounting brackets', 'quantity': len(diagram.components)}
            ])
            
            return parts_list
            
        except Exception as e:
            logger.error(f"Error generating parts list for {diagram_id}: {e}")
            return {}
    
    def validate_diagram(self, diagram_id: str) -> Dict[str, Any]:
        """Validate wiring diagram for errors"""
        try:
            diagram = self.diagrams.get(diagram_id)
            if not diagram:
                return {'valid': False, 'errors': ['Diagram not found']}
            
            errors = []
            warnings = []
            
            # Check for unconnected components
            connected_components = set()
            for conn in diagram.connections:
                connected_components.add(conn.from_component)
                connected_components.add(conn.to_component)
            
            for component in diagram.components:
                if component.component_id not in connected_components:
                    if component.component_type != ComponentType.POWER_SUPPLY:
                        warnings.append(f"Component {component.name} has no connections")
            
            # Check power requirements
            total_power = sum(comp.power_requirements.get('power', 0) for comp in diagram.components)
            power_supplies = [c for c in diagram.components if c.component_type == ComponentType.POWER_SUPPLY]
            
            if not power_supplies:
                errors.append("No power supply specified")
            elif power_supplies:
                supply_power = sum(ps.power_requirements.get('output_voltage', 0) * 
                                 ps.power_requirements.get('output_current', 0) for ps in power_supplies)
                if supply_power < total_power * 1.25:  # 25% safety margin
                    warnings.append("Power supply may be undersized")
            
            # Check for proper grounding
            ground_connections = [c for c in diagram.connections if 'GND' in str(c.to_pin) or 'ground' in c.wire_spec.wire_id]
            if len(ground_connections) < len(diagram.components) - 1:
                warnings.append("Some components may not be properly grounded")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'component_count': len(diagram.components),
                'connection_count': len(diagram.connections),
                'total_power_watts': total_power
            }
            
        except Exception as e:
            logger.error(f"Error validating diagram {diagram_id}: {e}")
            return {'valid': False, 'errors': [str(e)]}
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a wiring configuration before generating diagram"""
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'recommendations': []
            }
            
            # Check required fields
            required_fields = ['template_id']
            for field in required_fields:
                if field not in config:
                    validation_result['errors'].append(f"Missing required field: {field}")
                    validation_result['valid'] = False
            
            # Validate template ID
            valid_templates = [
                'single_engine_basic', 
                'single_engine_advanced', 
                'twin_engine_basic', 
                'twin_engine_advanced'
            ]
            
            if config.get('template_id') not in valid_templates:
                validation_result['errors'].append(f"Invalid template_id. Must be one of: {', '.join(valid_templates)}")
                validation_result['valid'] = False
            
            # Add recommendations based on configuration
            if config.get('template_id') == 'single_engine_basic':
                validation_result['recommendations'].extend([
                    'Consider upgrading to advanced monitoring for better diagnostics',
                    'Fuel flow sensor recommended for efficiency tracking',
                    'Exhaust temperature monitoring recommended for turbo engines'
                ])
            elif config.get('template_id') == 'twin_engine_advanced':
                validation_result['warnings'].append('Advanced twin engine setup requires skilled installation')
                validation_result['recommendations'].append('Consider professional marine electrician installation')
            
            # Check vessel information
            if not config.get('vessel_name'):
                validation_result['warnings'].append('Vessel name not specified - will use default')
            
            if not config.get('installer_name'):
                validation_result['warnings'].append('Installer name not specified - will use default')
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return {
                'valid': False,
                'errors': [f'Configuration validation error: {str(e)}'],
                'warnings': [],
                'recommendations': []
            }


class InstallationGuide:
    """Installation guidance system"""
    
    def __init__(self, diagram_generator: WiringDiagramGenerator):
        self.diagram_generator = diagram_generator
        
    def generate_installation_guide(self, diagram_id: str) -> Dict[str, Any]:
        """Generate complete installation guide"""
        try:
            diagram = self.diagram_generator.get_diagram(diagram_id)
            if not diagram:
                return {}
            
            guide = {
                'title': f"Installation Guide: {diagram.name}",
                'overview': diagram.description,
                'tools_required': self._get_required_tools(),
                'safety_precautions': self._get_safety_precautions(),
                'preparation_steps': self._get_preparation_steps(),
                'installation_sequence': self._get_installation_sequence(diagram),
                'testing_procedures': self._get_testing_procedures(),
                'troubleshooting': self._get_troubleshooting_guide(),
                'maintenance': self._get_maintenance_schedule()
            }
            
            return guide
            
        except Exception as e:
            logger.error(f"Error generating installation guide: {e}")
            return {}
    
    def _get_required_tools(self) -> List[str]:
        """Get list of required tools"""
        return [
            "Digital multimeter",
            "Crimping tool set",
            "Heat gun",
            "Cable strippers",
            "Screwdriver set",
            "Drill and bits",
            "Cable ties",
            "Label maker",
            "Torque wrench",
            "Marine sealant"
        ]
    
    def _get_safety_precautions(self) -> List[str]:
        """Get safety precautions"""
        return [
            "Disconnect battery power before starting work",
            "Wear safety glasses and gloves",
            "Ensure proper ventilation in engine compartment",
            "Have fire extinguisher readily available",
            "Never work alone in confined spaces",
            "Follow all manufacturer safety guidelines"
        ]
    
    def _get_preparation_steps(self) -> List[str]:
        """Get preparation steps"""
        return [
            "Review complete wiring diagram",
            "Verify all parts and materials are available",
            "Plan cable routing paths",
            "Identify mounting locations for components",
            "Take photos of existing wiring before modifications",
            "Create installation log for documentation"
        ]
    
    def _get_installation_sequence(self, diagram: WiringDiagram) -> List[Dict[str, Any]]:
        """Get installation sequence steps"""
        steps = []
        
        # Step 1: Mount components
        steps.append({
            'step': 1,
            'title': 'Mount Components',
            'description': 'Install all system components in their designated locations',
            'details': [
                'Mount power supply in dry, ventilated area',
                'Install gateway unit away from heat sources',
                'Position display unit for easy viewing',
                'Secure all sensor mounting brackets'
            ],
            'verification': 'All components securely mounted and accessible'
        })
        
        # Step 2: Route cables
        steps.append({
            'step': 2,
            'title': 'Route Cables',
            'description': 'Run all cables according to the routing plan',
            'details': [
                'Route power cables separate from signal cables',
                'Maintain proper bend radius for all cables',
                'Secure cables every 300mm with ties',
                'Label all cables at both ends'
            ],
            'verification': 'All cables properly routed and secured'
        })
        
        # Step 3: Make connections
        steps.append({
            'step': 3,
            'title': 'Make Connections',
            'description': 'Connect all wiring according to diagram',
            'details': [
                'Strip cable ends to proper length',
                'Apply dielectric grease to connectors',
                'Make connections per pin assignments',
                'Apply heat shrink to all splices'
            ],
            'verification': 'All connections made per wiring diagram'
        })
        
        # Step 4: Install fusing
        steps.append({
            'step': 4,
            'title': 'Install Fusing',
            'description': 'Install fuses and protection devices',
            'details': [
                'Install fuses per calculated ratings',
                'Verify fuse holder mounting',
                'Label all fused circuits',
                'Install main system switch'
            ],
            'verification': 'All circuits properly protected'
        })
        
        return steps
    
    def _get_testing_procedures(self) -> List[Dict[str, Any]]:
        """Get testing procedures"""
        return [
            {
                'test': 'Continuity Test',
                'description': 'Verify all connections before power-up',
                'procedure': [
                    'Use multimeter to check continuity',
                    'Verify no short circuits to ground',
                    'Check insulation resistance',
                    'Document all readings'
                ]
            },
            {
                'test': 'Power-Up Test',
                'description': 'Initial system power-up',
                'procedure': [
                    'Apply power with main switch',
                    'Verify voltage at all components',
                    'Check for proper LED indicators',
                    'Monitor current consumption'
                ]
            },
            {
                'test': 'Functional Test',
                'description': 'Verify all system functions',
                'procedure': [
                    'Test all sensor readings',
                    'Verify display operation',
                    'Check alarm functions',
                    'Test communication links'
                ]
            }
        ]
    
    def _get_troubleshooting_guide(self) -> Dict[str, List[str]]:
        """Get troubleshooting guide"""
        return {
            'No Power': [
                'Check main fuse',
                'Verify battery voltage',
                'Check power switch operation',
                'Inspect power connections'
            ],
            'Sensor Not Reading': [
                'Check sensor power supply',
                'Verify signal connections',
                'Test sensor with multimeter',
                'Check configuration settings'
            ],
            'Display Not Working': [
                'Check display power',
                'Verify communication cables',
                'Test display unit separately',
                'Check for error codes'
            ],
            'False Alarms': [
                'Check sensor calibration',
                'Verify alarm thresholds',
                'Inspect for loose connections',
                'Check environmental factors'
            ]
        }
    
    def _get_maintenance_schedule(self) -> List[Dict[str, Any]]:
        """Get maintenance schedule"""
        return [
            {
                'interval': 'Monthly',
                'tasks': [
                    'Visual inspection of all connections',
                    'Check for corrosion or damage',
                    'Test alarm functions',
                    'Clean display screen'
                ]
            },
            {
                'interval': 'Quarterly',
                'tasks': [
                    'Tighten all electrical connections',
                    'Check sensor calibration',
                    'Update system firmware',
                    'Test backup procedures'
                ]
            },
            {
                'interval': 'Annually',
                'tasks': [
                    'Complete system functional test',
                    'Replace backup batteries',
                    'Professional calibration check',
                    'Documentation update'
                ]
            }
        ]