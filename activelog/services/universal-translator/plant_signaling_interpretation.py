"""
Plant Signaling Interpretation System

This module provides comprehensive analysis and interpretation of plant communication
and signaling systems, including chemical, electrical, hydraulic, and mechanical
signaling pathways.
"""

import asyncio
import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
from datetime import datetime, timedelta
import scipy.signal
import scipy.stats

class PlantSpecies(Enum):
    """Supported plant species for signaling analysis"""
    ARABIDOPSIS = "arabidopsis_thaliana"
    TOMATO = "solanum_lycopersicum"
    TOBACCO = "nicotiana_tabacum"
    MAIZE = "zea_mays"
    WHEAT = "triticum_aestivum"
    RICE = "oryza_sativa"
    SOYBEAN = "glycine_max"
    POPLAR = "populus_trichocarpa"
    EUCALYPTUS = "eucalyptus"
    PINE = "pinus"
    OAK = "quercus"
    WILLOW = "salix"
    BEAN = "phaseolus_vulgaris"
    PEA = "pisum_sativum"
    SUNFLOWER = "helianthus_annuus"
    COTTON = "gossypium"
    POTATO = "solanum_tuberosum"
    CUCUMBER = "cucumis_sativus"
    LETTUCE = "lactuca_sativa"
    SPINACH = "spinacia_oleracea"

class SignalingModality(Enum):
    """Types of plant signaling modalities"""
    CHEMICAL = "chemical"  # VOCs, hormones, metabolites
    ELECTRICAL = "electrical"  # Action potentials, membrane depolarization
    HYDRAULIC = "hydraulic"  # Water pressure, turgor changes
    MECHANICAL = "mechanical"  # Physical movements, vibrations
    OPTICAL = "optical"  # Light reflection, fluorescence
    MYCORRHIZAL = "mycorrhizal"  # Fungal network communication
    ROOT_EXUDATE = "root_exudate"  # Chemical signals through roots
    AIRBORNE = "airborne"  # Volatile organic compounds

class SignalType(Enum):
    """Types of signals plants can send"""
    STRESS_RESPONSE = "stress_response"
    DEFENSE_ACTIVATION = "defense_activation"
    RESOURCE_SHARING = "resource_sharing"
    GROWTH_COORDINATION = "growth_coordination"
    REPRODUCTION_SIGNAL = "reproduction_signal"
    PATHOGEN_ALERT = "pathogen_alert"
    HERBIVORE_WARNING = "herbivore_warning"
    DROUGHT_STRESS = "drought_stress"
    LIGHT_COMPETITION = "light_competition"
    NUTRIENT_AVAILABILITY = "nutrient_availability"
    SEASONAL_CHANGE = "seasonal_change"
    CIRCADIAN_RHYTHM = "circadian_rhythm"
    ALLELOPATHY = "allelopathy"
    SYMBIOSIS_SIGNAL = "symbiosis_signal"
    ROOT_RECOGNITION = "root_recognition"

class EnvironmentalContext(Enum):
    """Environmental contexts affecting plant signaling"""
    NORMAL_CONDITIONS = "normal"
    DROUGHT_STRESS = "drought"
    HEAT_STRESS = "heat"
    COLD_STRESS = "cold"
    PATHOGEN_ATTACK = "pathogen_attack"
    HERBIVORE_DAMAGE = "herbivore_damage"
    NUTRIENT_DEFICIENCY = "nutrient_deficiency"
    LIGHT_LIMITATION = "light_limitation"
    SALT_STRESS = "salt_stress"
    FLOODING = "flooding"
    MECHANICAL_DAMAGE = "mechanical_damage"
    COMPETITION = "competition"
    POLLINATION = "pollination"
    GERMINATION = "germination"
    SENESCENCE = "senescence"

@dataclass
class ChemicalSignal:
    """Represents a chemical signaling compound"""
    compound_name: str
    compound_class: str  # "hormone", "VOC", "metabolite", "phenolic", etc.
    molecular_formula: Optional[str] = None
    concentration: float = 0.0  # µM or ppm
    emission_rate: float = 0.0  # ng/hour or similar
    volatility: str = "unknown"  # "high", "medium", "low"
    biological_activity: List[str] = field(default_factory=list)
    target_tissues: List[str] = field(default_factory=list)
    half_life: Optional[float] = None  # minutes or hours
    transport_method: str = "unknown"  # "xylem", "phloem", "airborne", "soil"

@dataclass
class ElectricalSignal:
    """Represents electrical signaling in plants"""
    signal_type: str  # "action_potential", "variation_potential", "system_potential"
    amplitude: float  # mV
    duration: float  # seconds
    propagation_speed: float  # cm/s
    frequency: Optional[float] = None  # Hz for oscillatory signals
    tissue_origin: str = "unknown"  # "leaf", "stem", "root"
    trigger_stimulus: str = "unknown"
    decay_time: float = 0.0
    membrane_depolarization: float = 0.0

@dataclass
class HydraulicSignal:
    """Represents hydraulic signaling in plants"""
    pressure_change: float  # MPa or bars
    flow_rate_change: float  # percentage change
    tissue_involved: str  # "xylem", "phloem", "root"
    propagation_speed: float  # cm/min
    duration: float  # minutes
    trigger_cause: str = "unknown"
    osmotic_adjustment: float = 0.0
    cavitation_events: int = 0

@dataclass
class MechanicalSignal:
    """Represents mechanical signaling in plants"""
    movement_type: str  # "thigmotropism", "nutation", "leaf_movement"
    displacement: float  # mm or degrees
    velocity: float  # mm/s or degrees/s
    force_generated: float  # mN or similar
    frequency: Optional[float] = None  # Hz for oscillatory movements
    tissue_involved: str = "leaf"
    stimulus_type: str = "touch"
    recovery_time: float = 0.0

@dataclass
class PlantSignalingEvent:
    """Represents a complete plant signaling event"""
    plant_id: str
    species: PlantSpecies
    timestamp: float
    modality: SignalingModality
    signal_type: SignalType
    environmental_context: EnvironmentalContext
    signal_data: Union[ChemicalSignal, ElectricalSignal, HydraulicSignal, MechanicalSignal]
    source_tissue: str = "unknown"
    target_tissues: List[str] = field(default_factory=list)
    confidence: float = 0.0
    measurement_conditions: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlantProfile:
    """Profile of signaling capabilities for a plant species"""
    species: PlantSpecies
    primary_signaling_modes: List[SignalingModality]
    known_compounds: List[str] = field(default_factory=list)
    electrical_properties: Dict[str, float] = field(default_factory=dict)
    hydraulic_characteristics: Dict[str, float] = field(default_factory=dict)
    mechanical_capabilities: List[str] = field(default_factory=list)
    stress_responses: List[str] = field(default_factory=list)
    communication_range: str = "local"  # "local", "regional", "network"
    signaling_complexity: str = "medium"  # "low", "medium", "high"
    symbiotic_relationships: List[str] = field(default_factory=list)
    unique_features: List[str] = field(default_factory=list)

@dataclass
class InterpretationResult:
    """Result of plant signaling interpretation"""
    source_species: PlantSpecies
    analysis_duration: float
    detected_signals: List[PlantSignalingEvent]
    dominant_signal_types: List[SignalType]
    environmental_stressors: List[EnvironmentalContext]
    plant_status: str  # "healthy", "stressed", "responding", "recovering"
    communication_network: str  # "isolated", "connected", "hub"
    interpreted_messages: List[str]
    physiological_state: Dict[str, str]
    processing_time: float
    confidence: float
    interpretation_notes: List[str]
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class PlantDatabase:
    """Database of plant species and their signaling characteristics"""
    
    def __init__(self):
        self.plant_profiles = self._initialize_plant_profiles()
        self.chemical_library = self._initialize_chemical_library()
        
    def _initialize_plant_profiles(self) -> Dict[PlantSpecies, PlantProfile]:
        """Initialize plant signaling profiles"""
        profiles = {
            PlantSpecies.ARABIDOPSIS: PlantProfile(
                species=PlantSpecies.ARABIDOPSIS,
                primary_signaling_modes=[SignalingModality.CHEMICAL, SignalingModality.ELECTRICAL],
                known_compounds=["salicylic_acid", "jasmonic_acid", "ethylene", "abscisic_acid", 
                               "auxin", "cytokinin", "gibberellins"],
                electrical_properties={"resting_potential": -150.0, "threshold": -100.0},
                hydraulic_characteristics={"turgor_pressure": 0.8, "osmotic_potential": -0.5},
                mechanical_capabilities=["leaf_movement", "root_growth_direction"],
                stress_responses=["SAR", "ISR", "osmotic_adjustment", "antioxidant_production"],
                communication_range="local",
                signaling_complexity="high",
                symbiotic_relationships=["mycorrhizae", "rhizobacteria"],
                unique_features=["model_organism", "extensive_gene_networks", "rapid_response"]
            ),
            
            PlantSpecies.TOMATO: PlantProfile(
                species=PlantSpecies.TOMATO,
                primary_signaling_modes=[SignalingModality.CHEMICAL, SignalingModality.AIRBORNE],
                known_compounds=["jasmonic_acid", "salicylic_acid", "ethylene", "hexenol", 
                               "methyl_jasmonate", "green_leaf_volatiles"],
                electrical_properties={"resting_potential": -140.0, "threshold": -90.0},
                stress_responses=["herbivore_defense", "pathogen_resistance", "wound_response"],
                communication_range="regional",
                signaling_complexity="high",
                symbiotic_relationships=["mycorrhizae", "beneficial_bacteria"],
                unique_features=["extensive_VOC_emission", "herbivore_specific_responses", "fruit_signaling"]
            ),
            
            PlantSpecies.MAIZE: PlantProfile(
                species=PlantSpecies.MAIZE,
                primary_signaling_modes=[SignalingModality.CHEMICAL, SignalingModality.HYDRAULIC, 
                                       SignalingModality.ROOT_EXUDATE],
                known_compounds=["benzoxazinoids", "terpenoids", "phenolics", "indole"],
                hydraulic_characteristics={"xylem_pressure": 2.0, "root_pressure": 0.1},
                stress_responses=["drought_tolerance", "herbivore_defense", "allelopathy"],
                communication_range="network",
                signaling_complexity="medium",
                symbiotic_relationships=["mycorrhizae", "rhizosphere_microbes"],
                unique_features=["C4_photosynthesis", "deep_root_system", "allelopathic_compounds"]
            ),
            
            PlantSpecies.WILLOW: PlantProfile(
                species=PlantSpecies.WILLOW,
                primary_signaling_modes=[SignalingModality.CHEMICAL, SignalingModality.ELECTRICAL,
                                       SignalingModality.MECHANICAL],
                known_compounds=["salicin", "salicylic_acid", "catechins", "tannins"],
                electrical_properties={"action_potential_speed": 2.0},  # cm/s
                mechanical_capabilities=["thigmotropism", "gravitropism", "branch_movement"],
                stress_responses=["pathogen_defense", "herbivore_deterrence", "wound_healing"],
                communication_range="regional",
                signaling_complexity="high",
                symbiotic_relationships=["ectomycorrhizae", "endophytes"],
                unique_features=["salicylate_production", "rapid_electrical_signaling", "clonal_growth"]
            ),
            
            PlantSpecies.SOYBEAN: PlantProfile(
                species=PlantSpecies.SOYBEAN,
                primary_signaling_modes=[SignalingModality.CHEMICAL, SignalingModality.ROOT_EXUDATE,
                                       SignalingModality.MYCORRHIZAL],
                known_compounds=["isoflavonoids", "saponins", "genistein", "daidzein"],
                stress_responses=["nitrogen_fixation", "pathogen_resistance", "drought_tolerance"],
                communication_range="network",
                signaling_complexity="high",
                symbiotic_relationships=["rhizobia", "mycorrhizae", "root_microbiome"],
                unique_features=["nodulation_signaling", "isoflavonoid_production", "legume_specific"]
            ),
            
            PlantSpecies.EUCALYPTUS: PlantProfile(
                species=PlantSpecies.EUCALYPTUS,
                primary_signaling_modes=[SignalingModality.CHEMICAL, SignalingModality.AIRBORNE],
                known_compounds=["eucalyptol", "monoterpenes", "sesquiterpenes", "phenolics"],
                stress_responses=["fire_adaptation", "drought_tolerance", "herbivore_deterrence"],
                communication_range="regional",
                signaling_complexity="medium",
                unique_features=["essential_oil_production", "allelopathy", "fire_recovery"]
            )
        }
        
        return profiles
    
    def _initialize_chemical_library(self) -> Dict[str, ChemicalSignal]:
        """Initialize library of plant signaling compounds"""
        library = {
            "salicylic_acid": ChemicalSignal(
                compound_name="Salicylic acid",
                compound_class="phenolic_hormone",
                molecular_formula="C7H6O3",
                concentration=1.0,
                volatility="medium",
                biological_activity=["pathogen_defense", "SAR_induction", "stress_signaling"],
                target_tissues=["leaves", "stems", "roots"],
                half_life=120.0,  # minutes
                transport_method="phloem"
            ),
            
            "jasmonic_acid": ChemicalSignal(
                compound_name="Jasmonic acid",
                compound_class="oxylipin_hormone",
                molecular_formula="C12H18O3",
                concentration=0.5,
                volatility="low",
                biological_activity=["wound_response", "herbivore_defense", "reproduction"],
                target_tissues=["leaves", "flowers", "roots"],
                half_life=60.0,
                transport_method="phloem"
            ),
            
            "methyl_jasmonate": ChemicalSignal(
                compound_name="Methyl jasmonate",
                compound_class="volatile_hormone",
                molecular_formula="C13H20O3",
                concentration=0.1,
                volatility="high",
                biological_activity=["defense_priming", "interplant_signaling", "gene_expression"],
                target_tissues=["leaves", "neighboring_plants"],
                half_life=30.0,
                transport_method="airborne"
            ),
            
            "ethylene": ChemicalSignal(
                compound_name="Ethylene",
                compound_class="gaseous_hormone",
                molecular_formula="C2H4",
                concentration=0.01,
                volatility="high",
                biological_activity=["fruit_ripening", "senescence", "stress_response"],
                target_tissues=["fruits", "leaves", "roots"],
                half_life=10.0,
                transport_method="airborne"
            ),
            
            "abscisic_acid": ChemicalSignal(
                compound_name="Abscisic acid",
                compound_class="terpenoid_hormone",
                molecular_formula="C15H20O4",
                concentration=2.0,
                volatility="low",
                biological_activity=["drought_stress", "stomatal_closure", "dormancy"],
                target_tissues=["leaves", "roots", "seeds"],
                half_life=180.0,
                transport_method="xylem"
            ),
            
            "green_leaf_volatiles": ChemicalSignal(
                compound_name="Green leaf volatiles",
                compound_class="C6_aldehydes_alcohols",
                molecular_formula="C6H12O",
                concentration=0.05,
                volatility="high",
                biological_activity=["herbivore_deterrence", "plant_communication", "antimicrobial"],
                target_tissues=["damaged_leaves", "neighboring_plants"],
                half_life=15.0,
                transport_method="airborne"
            ),
            
            "terpenes": ChemicalSignal(
                compound_name="Terpenes",
                compound_class="volatile_secondary_metabolites",
                molecular_formula="C10H16",
                concentration=0.2,
                volatility="high",
                biological_activity=["herbivore_deterrence", "pathogen_resistance", "pollinator_attraction"],
                target_tissues=["leaves", "flowers", "bark"],
                half_life=45.0,
                transport_method="airborne"
            )
        }
        
        return library

class ChemicalSignalAnalyzer:
    """Analyzes chemical signaling in plants"""
    
    def __init__(self):
        self.plant_db = PlantDatabase()
        
    async def analyze_chemical_signals(self, compound_data: Dict[str, float],
                                     species: PlantSpecies,
                                     environmental_context: EnvironmentalContext) -> List[ChemicalSignal]:
        """Analyze detected chemical compounds for signaling activity"""
        detected_signals = []
        
        for compound_name, concentration in compound_data.items():
            if compound_name in self.plant_db.chemical_library:
                base_signal = self.plant_db.chemical_library[compound_name]
                
                # Create signal instance with measured concentration
                signal = ChemicalSignal(
                    compound_name=base_signal.compound_name,
                    compound_class=base_signal.compound_class,
                    molecular_formula=base_signal.molecular_formula,
                    concentration=concentration,
                    emission_rate=await self._estimate_emission_rate(concentration, base_signal),
                    volatility=base_signal.volatility,
                    biological_activity=base_signal.biological_activity,
                    target_tissues=base_signal.target_tissues,
                    half_life=base_signal.half_life,
                    transport_method=base_signal.transport_method
                )
                
                # Adjust activity based on concentration and context
                signal.biological_activity = await self._adjust_activity_for_context(
                    signal, environmental_context
                )
                
                detected_signals.append(signal)
            else:
                # Unknown compound - create basic signal
                signal = ChemicalSignal(
                    compound_name=compound_name,
                    compound_class="unknown",
                    concentration=concentration,
                    volatility="unknown",
                    biological_activity=["unknown_function"],
                    target_tissues=["unknown"]
                )
                detected_signals.append(signal)
        
        return detected_signals
    
    async def _estimate_emission_rate(self, concentration: float, base_signal: ChemicalSignal) -> float:
        """Estimate emission rate based on concentration and compound properties"""
        # Simple model: emission rate proportional to concentration and volatility
        volatility_factors = {"high": 10.0, "medium": 3.0, "low": 1.0, "unknown": 1.0}
        volatility_factor = volatility_factors.get(base_signal.volatility, 1.0)
        
        return concentration * volatility_factor * 0.1  # ng/hour (simplified)
    
    async def _adjust_activity_for_context(self, signal: ChemicalSignal, 
                                         context: EnvironmentalContext) -> List[str]:
        """Adjust biological activity based on environmental context"""
        context_adjustments = {
            EnvironmentalContext.PATHOGEN_ATTACK: ["pathogen_defense", "SAR_induction"],
            EnvironmentalContext.HERBIVORE_DAMAGE: ["herbivore_defense", "wound_response"],
            EnvironmentalContext.DROUGHT_STRESS: ["osmotic_adjustment", "stomatal_regulation"],
            EnvironmentalContext.HEAT_STRESS: ["heat_shock_response", "protein_protection"],
            EnvironmentalContext.NUTRIENT_DEFICIENCY: ["nutrient_mobilization", "root_signaling"],
            EnvironmentalContext.COMPETITION: ["allelopathy", "competitive_response"]
        }
        
        base_activities = signal.biological_activity.copy()
        context_specific = context_adjustments.get(context, [])
        
        # Combine base activities with context-specific ones
        enhanced_activities = list(set(base_activities + context_specific))
        
        return enhanced_activities

class ElectricalSignalAnalyzer:
    """Analyzes electrical signaling in plants"""
    
    def __init__(self):
        self.plant_db = PlantDatabase()
        
    async def analyze_electrical_signals(self, voltage_data: np.ndarray, 
                                       sample_rate: float,
                                       species: PlantSpecies,
                                       stimulus_type: str = "unknown") -> List[ElectricalSignal]:
        """Analyze electrical signal data from plant measurements"""
        signals = []
        
        # Preprocessing - remove noise and drift
        filtered_data = await self._preprocess_electrical_data(voltage_data, sample_rate)
        
        # Detect signal events (action potentials, variation potentials)
        events = await self._detect_electrical_events(filtered_data, sample_rate)
        
        # Analyze each detected event
        for event_start, event_end in events:
            signal_segment = filtered_data[event_start:event_end]
            
            signal = await self._analyze_electrical_event(
                signal_segment, sample_rate, species, stimulus_type
            )
            
            if signal:
                signals.append(signal)
        
        return signals
    
    async def _preprocess_electrical_data(self, voltage_data: np.ndarray, 
                                        sample_rate: float) -> np.ndarray:
        """Preprocess electrical data to remove noise and artifacts"""
        # Remove DC component
        detrended = scipy.signal.detrend(voltage_data)
        
        # Apply low-pass filter to remove high-frequency noise
        # Plants typically have slow electrical responses (0.1-10 Hz)
        nyquist = sample_rate / 2
        cutoff = min(10.0, nyquist * 0.8)
        sos = scipy.signal.butter(4, cutoff/nyquist, output='sos')
        filtered = scipy.signal.sosfilt(sos, detrended)
        
        return filtered
    
    async def _detect_electrical_events(self, voltage_data: np.ndarray, 
                                      sample_rate: float) -> List[Tuple[int, int]]:
        """Detect electrical signaling events in voltage data"""
        # Calculate derivative to find rapid changes
        derivative = np.gradient(voltage_data)
        
        # Find threshold for significant events
        threshold = np.std(derivative) * 3
        
        # Find events that exceed threshold
        significant_changes = np.abs(derivative) > threshold
        
        # Group consecutive significant points into events
        events = []
        in_event = False
        event_start = 0
        min_event_duration = int(sample_rate * 0.5)  # Minimum 0.5 seconds
        
        for i, is_significant in enumerate(significant_changes):
            if is_significant and not in_event:
                event_start = max(0, i - int(sample_rate * 0.1))  # Include some pre-event data
                in_event = True
            elif not is_significant and in_event:
                event_end = min(len(voltage_data), i + int(sample_rate * 0.1))
                if event_end - event_start >= min_event_duration:
                    events.append((event_start, event_end))
                in_event = False
        
        # Handle case where event continues to end of data
        if in_event:
            events.append((event_start, len(voltage_data)))
        
        return events
    
    async def _analyze_electrical_event(self, signal_data: np.ndarray, 
                                      sample_rate: float,
                                      species: PlantSpecies,
                                      stimulus_type: str) -> Optional[ElectricalSignal]:
        """Analyze individual electrical event"""
        if len(signal_data) < 10:
            return None
        
        # Calculate signal characteristics
        amplitude = np.max(signal_data) - np.min(signal_data)
        duration = len(signal_data) / sample_rate
        
        # Determine signal type based on characteristics
        signal_type = await self._classify_electrical_signal(signal_data, amplitude, duration)
        
        # Estimate propagation speed (requires spatial information - simplified)
        propagation_speed = await self._estimate_propagation_speed(species, signal_type)
        
        # Calculate frequency if oscillatory
        frequency = None
        if signal_type == "system_potential":
            freqs, psd = scipy.signal.welch(signal_data, sample_rate, nperseg=min(256, len(signal_data)))
            peak_freq_idx = np.argmax(psd)
            frequency = freqs[peak_freq_idx]
        
        # Calculate decay time
        decay_time = await self._calculate_decay_time(signal_data, sample_rate)
        
        return ElectricalSignal(
            signal_type=signal_type,
            amplitude=amplitude,
            duration=duration,
            propagation_speed=propagation_speed,
            frequency=frequency,
            tissue_origin="leaf",  # Default - would need measurement setup info
            trigger_stimulus=stimulus_type,
            decay_time=decay_time,
            membrane_depolarization=max(0, amplitude)
        )
    
    async def _classify_electrical_signal(self, signal_data: np.ndarray, 
                                        amplitude: float, duration: float) -> str:
        """Classify type of electrical signal"""
        if amplitude > 100 and duration < 5.0:  # mV, seconds
            return "action_potential"
        elif amplitude > 20 and duration > 10.0:
            return "variation_potential"
        elif duration > 60.0:
            return "system_potential"
        else:
            return "local_potential"
    
    async def _estimate_propagation_speed(self, species: PlantSpecies, signal_type: str) -> float:
        """Estimate signal propagation speed based on species and signal type"""
        # Default speeds based on literature (cm/s)
        speed_ranges = {
            "action_potential": (1.0, 5.0),
            "variation_potential": (0.1, 1.0),
            "system_potential": (0.01, 0.1),
            "local_potential": (0.001, 0.01)
        }
        
        speed_range = speed_ranges.get(signal_type, (0.1, 1.0))
        
        # Species-specific adjustments
        species_factors = {
            PlantSpecies.ARABIDOPSIS: 0.8,  # Small plant, slower speeds
            PlantSpecies.WILLOW: 1.5,      # Fast electrical signaling
            PlantSpecies.TOMATO: 1.2,      # Moderate speed
        }
        
        factor = species_factors.get(species, 1.0)
        base_speed = (speed_range[0] + speed_range[1]) / 2
        
        return base_speed * factor
    
    async def _calculate_decay_time(self, signal_data: np.ndarray, sample_rate: float) -> float:
        """Calculate signal decay time constant"""
        # Find peak
        peak_idx = np.argmax(np.abs(signal_data))
        
        if peak_idx >= len(signal_data) - 10:
            return 0.0
        
        # Analyze decay after peak
        decay_portion = signal_data[peak_idx:]
        peak_value = signal_data[peak_idx]
        
        # Find where signal decays to 37% of peak (1/e)
        target_value = peak_value * 0.37
        
        for i, value in enumerate(decay_portion):
            if abs(value) <= abs(target_value):
                return i / sample_rate
        
        return len(decay_portion) / sample_rate

class PlantSignalingInterpreter:
    """Interprets plant signaling events into biological meanings"""
    
    def __init__(self):
        self.plant_db = PlantDatabase()
        
    async def interpret_signaling_events(self, events: List[PlantSignalingEvent],
                                       species: PlantSpecies) -> List[str]:
        """Interpret biological meaning of signaling events"""
        interpretations = []
        
        for event in events:
            interpretation = await self._interpret_single_event(event, species)
            interpretations.append(interpretation)
        
        # Look for patterns across events
        pattern_interpretation = await self._interpret_event_patterns(events, species)
        if pattern_interpretation:
            interpretations.append(f"Pattern analysis: {pattern_interpretation}")
        
        return interpretations
    
    async def _interpret_single_event(self, event: PlantSignalingEvent, 
                                    species: PlantSpecies) -> str:
        """Interpret a single signaling event"""
        modality = event.modality
        signal_type = event.signal_type
        context = event.environmental_context
        
        interpretations = []
        
        # Modality-specific interpretations
        if modality == SignalingModality.CHEMICAL:
            if isinstance(event.signal_data, ChemicalSignal):
                compound = event.signal_data.compound_name
                concentration = event.signal_data.concentration
                
                if "defense" in event.signal_data.biological_activity:
                    interpretations.append(f"Defense response via {compound} (conc: {concentration:.2f})")
                if "stress" in event.signal_data.biological_activity:
                    interpretations.append(f"Stress signaling with {compound}")
                
        elif modality == SignalingModality.ELECTRICAL:
            if isinstance(event.signal_data, ElectricalSignal):
                signal_type_desc = event.signal_data.signal_type
                amplitude = event.signal_data.amplitude
                
                if signal_type_desc == "action_potential":
                    interpretations.append(f"Rapid electrical response (amplitude: {amplitude:.1f}mV)")
                elif signal_type_desc == "variation_potential":
                    interpretations.append(f"Slow electrical signaling indicating stress response")
        
        # Context-based interpretations
        if context == EnvironmentalContext.PATHOGEN_ATTACK:
            interpretations.append("Pathogen defense activation")
        elif context == EnvironmentalContext.HERBIVORE_DAMAGE:
            interpretations.append("Herbivore damage response")
        elif context == EnvironmentalContext.DROUGHT_STRESS:
            interpretations.append("Water stress adaptation")
        elif context == EnvironmentalContext.NUTRIENT_DEFICIENCY:
            interpretations.append("Nutrient stress response")
        
        # Signal type interpretations
        if signal_type == SignalType.DEFENSE_ACTIVATION:
            interpretations.append("Activating plant defense systems")
        elif signal_type == SignalType.RESOURCE_SHARING:
            interpretations.append("Coordinating resource allocation")
        elif signal_type == SignalType.STRESS_RESPONSE:
            interpretations.append("General stress response activation")
        
        if not interpretations:
            interpretations.append(f"{modality.value} signaling event")
        
        return "; ".join(interpretations)
    
    async def _interpret_event_patterns(self, events: List[PlantSignalingEvent],
                                      species: PlantSpecies) -> Optional[str]:
        """Interpret patterns across multiple signaling events"""
        if len(events) < 2:
            return None
        
        # Analyze temporal patterns
        timestamps = [event.timestamp for event in events]
        time_intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        
        # Check for coordinated responses
        chemical_events = [e for e in events if e.modality == SignalingModality.CHEMICAL]
        electrical_events = [e for e in events if e.modality == SignalingModality.ELECTRICAL]
        
        patterns = []
        
        if chemical_events and electrical_events:
            patterns.append("Coordinated chemical-electrical signaling")
        
        # Check for escalating response
        signal_strengths = []
        for event in events:
            if isinstance(event.signal_data, ChemicalSignal):
                signal_strengths.append(event.signal_data.concentration)
            elif isinstance(event.signal_data, ElectricalSignal):
                signal_strengths.append(event.signal_data.amplitude)
        
        if len(signal_strengths) > 2 and all(signal_strengths[i] <= signal_strengths[i+1] for i in range(len(signal_strengths)-1)):
            patterns.append("Escalating response intensity")
        
        # Check for rhythmic patterns
        if len(time_intervals) > 3:
            interval_cv = np.std(time_intervals) / np.mean(time_intervals)
            if interval_cv < 0.3:  # Low coefficient of variation
                patterns.append("Rhythmic signaling pattern")
        
        return "; ".join(patterns) if patterns else None

class PlantSignalingInterpretationSystem:
    """Main system for interpreting plant signaling and communication"""
    
    def __init__(self):
        self.plant_db = PlantDatabase()
        self.chemical_analyzer = ChemicalSignalAnalyzer()
        self.electrical_analyzer = ElectricalSignalAnalyzer()
        self.interpreter = PlantSignalingInterpreter()
        
    async def interpret_plant_signals(self, 
                                    chemical_data: Optional[Dict[str, float]] = None,
                                    electrical_data: Optional[Tuple[np.ndarray, float]] = None,
                                    hydraulic_data: Optional[Dict[str, float]] = None,
                                    mechanical_data: Optional[Dict[str, float]] = None,
                                    species: PlantSpecies = PlantSpecies.ARABIDOPSIS,
                                    environmental_context: EnvironmentalContext = EnvironmentalContext.NORMAL_CONDITIONS,
                                    measurement_duration: float = 3600.0) -> InterpretationResult:
        """Interpret plant signaling across multiple modalities"""
        start_time = datetime.now()
        
        detected_signals = []
        
        try:
            # Analyze chemical signals
            if chemical_data:
                chemical_signals = await self.chemical_analyzer.analyze_chemical_signals(
                    chemical_data, species, environmental_context
                )
                
                for signal in chemical_signals:
                    event = PlantSignalingEvent(
                        plant_id="plant_001",
                        species=species,
                        timestamp=0.0,
                        modality=SignalingModality.CHEMICAL,
                        signal_type=await self._infer_signal_type_from_chemical(signal, environmental_context),
                        environmental_context=environmental_context,
                        signal_data=signal,
                        confidence=0.8
                    )
                    detected_signals.append(event)
            
            # Analyze electrical signals
            if electrical_data:
                voltage_data, sample_rate = electrical_data
                electrical_signals = await self.electrical_analyzer.analyze_electrical_signals(
                    voltage_data, sample_rate, species
                )
                
                for signal in electrical_signals:
                    event = PlantSignalingEvent(
                        plant_id="plant_001",
                        species=species,
                        timestamp=0.0,
                        modality=SignalingModality.ELECTRICAL,
                        signal_type=await self._infer_signal_type_from_electrical(signal, environmental_context),
                        environmental_context=environmental_context,
                        signal_data=signal,
                        confidence=0.75
                    )
                    detected_signals.append(event)
            
            # Analyze hydraulic signals (simplified)
            if hydraulic_data:
                hydraulic_event = await self._analyze_hydraulic_data(
                    hydraulic_data, species, environmental_context
                )
                if hydraulic_event:
                    detected_signals.append(hydraulic_event)
            
            # Analyze mechanical signals (simplified)
            if mechanical_data:
                mechanical_event = await self._analyze_mechanical_data(
                    mechanical_data, species, environmental_context
                )
                if mechanical_event:
                    detected_signals.append(mechanical_event)
            
            # Interpret all detected signals
            interpreted_messages = await self.interpreter.interpret_signaling_events(
                detected_signals, species
            )
            
            # Determine dominant signal types
            signal_types = [event.signal_type for event in detected_signals]
            dominant_signal_types = list(set(signal_types))
            
            # Assess plant status
            plant_status = await self._assess_plant_status(detected_signals, environmental_context)
            
            # Determine physiological state
            physiological_state = await self._determine_physiological_state(
                detected_signals, species
            )
            
            # Assess communication network status
            communication_network = await self._assess_communication_network(detected_signals)
            
            # Calculate confidence
            confidence = await self._calculate_interpretation_confidence(detected_signals)
            
            # Generate interpretation notes
            interpretation_notes = await self._generate_interpretation_notes(
                species, detected_signals, environmental_context
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return InterpretationResult(
                source_species=species,
                analysis_duration=measurement_duration,
                detected_signals=detected_signals,
                dominant_signal_types=dominant_signal_types,
                environmental_stressors=[environmental_context] if environmental_context != EnvironmentalContext.NORMAL_CONDITIONS else [],
                plant_status=plant_status,
                communication_network=communication_network,
                interpreted_messages=interpreted_messages,
                physiological_state=physiological_state,
                processing_time=processing_time,
                confidence=confidence,
                interpretation_notes=interpretation_notes,
                metadata={
                    "total_signals": len(detected_signals),
                    "chemical_signals": len([s for s in detected_signals if s.modality == SignalingModality.CHEMICAL]),
                    "electrical_signals": len([s for s in detected_signals if s.modality == SignalingModality.ELECTRICAL]),
                    "measurement_conditions": {"context": environmental_context.value, "duration": measurement_duration}
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return InterpretationResult(
                source_species=species,
                analysis_duration=measurement_duration,
                detected_signals=[],
                dominant_signal_types=[],
                environmental_stressors=[],
                plant_status="unknown",
                communication_network="unknown",
                interpreted_messages=[f"Analysis error: {str(e)}"],
                physiological_state={"status": "error"},
                processing_time=processing_time,
                confidence=0.0,
                interpretation_notes=[f"Error: {str(e)}"],
                warnings=["Analysis failed due to processing error"]
            )
    
    async def _infer_signal_type_from_chemical(self, signal: ChemicalSignal, 
                                             context: EnvironmentalContext) -> SignalType:
        """Infer signal type from chemical signal characteristics"""
        activities = signal.biological_activity
        
        if "pathogen_defense" in activities or "SAR_induction" in activities:
            return SignalType.PATHOGEN_ALERT
        elif "herbivore_defense" in activities or "wound_response" in activities:
            return SignalType.HERBIVORE_WARNING
        elif "stress_signaling" in activities or "osmotic_adjustment" in activities:
            return SignalType.STRESS_RESPONSE
        elif "growth_regulation" in activities:
            return SignalType.GROWTH_COORDINATION
        elif "reproduction" in activities:
            return SignalType.REPRODUCTION_SIGNAL
        else:
            return SignalType.STRESS_RESPONSE  # Default
    
    async def _infer_signal_type_from_electrical(self, signal: ElectricalSignal,
                                               context: EnvironmentalContext) -> SignalType:
        """Infer signal type from electrical signal characteristics"""
        if signal.signal_type == "action_potential":
            if context in [EnvironmentalContext.HERBIVORE_DAMAGE, EnvironmentalContext.MECHANICAL_DAMAGE]:
                return SignalType.HERBIVORE_WARNING
            else:
                return SignalType.STRESS_RESPONSE
        elif signal.signal_type == "variation_potential":
            return SignalType.STRESS_RESPONSE
        else:
            return SignalType.GROWTH_COORDINATION
    
    async def _analyze_hydraulic_data(self, hydraulic_data: Dict[str, float],
                                    species: PlantSpecies, 
                                    context: EnvironmentalContext) -> Optional[PlantSignalingEvent]:
        """Analyze hydraulic signaling data"""
        pressure_change = hydraulic_data.get("pressure_change", 0.0)
        
        if abs(pressure_change) > 0.1:  # Significant pressure change
            hydraulic_signal = HydraulicSignal(
                pressure_change=pressure_change,
                flow_rate_change=hydraulic_data.get("flow_rate_change", 0.0),
                tissue_involved="xylem",
                propagation_speed=1.0,  # cm/min
                duration=hydraulic_data.get("duration", 60.0),
                trigger_cause=context.value
            )
            
            event = PlantSignalingEvent(
                plant_id="plant_001",
                species=species,
                timestamp=0.0,
                modality=SignalingModality.HYDRAULIC,
                signal_type=SignalType.STRESS_RESPONSE if pressure_change < 0 else SignalType.RESOURCE_SHARING,
                environmental_context=context,
                signal_data=hydraulic_signal,
                confidence=0.7
            )
            
            return event
        
        return None
    
    async def _analyze_mechanical_data(self, mechanical_data: Dict[str, float],
                                     species: PlantSpecies,
                                     context: EnvironmentalContext) -> Optional[PlantSignalingEvent]:
        """Analyze mechanical signaling data"""
        displacement = mechanical_data.get("displacement", 0.0)
        
        if abs(displacement) > 1.0:  # Significant movement
            mechanical_signal = MechanicalSignal(
                movement_type="thigmotropism",
                displacement=displacement,
                velocity=mechanical_data.get("velocity", 0.1),
                force_generated=mechanical_data.get("force", 0.0),
                tissue_involved="leaf",
                stimulus_type=context.value
            )
            
            event = PlantSignalingEvent(
                plant_id="plant_001",
                species=species,
                timestamp=0.0,
                modality=SignalingModality.MECHANICAL,
                signal_type=SignalType.STRESS_RESPONSE,
                environmental_context=context,
                signal_data=mechanical_signal,
                confidence=0.6
            )
            
            return event
        
        return None
    
    async def _assess_plant_status(self, signals: List[PlantSignalingEvent],
                                 context: EnvironmentalContext) -> str:
        """Assess overall plant health status from signals"""
        if not signals:
            return "healthy"
        
        stress_signals = len([s for s in signals if s.signal_type == SignalType.STRESS_RESPONSE])
        defense_signals = len([s for s in signals if s.signal_type in [SignalType.PATHOGEN_ALERT, SignalType.HERBIVORE_WARNING]])
        
        total_signals = len(signals)
        stress_ratio = stress_signals / total_signals
        defense_ratio = defense_signals / total_signals
        
        if defense_ratio > 0.5:
            return "under_attack"
        elif stress_ratio > 0.6:
            return "stressed"
        elif stress_ratio > 0.3:
            return "responding"
        elif context != EnvironmentalContext.NORMAL_CONDITIONS:
            return "adapting"
        else:
            return "healthy"
    
    async def _determine_physiological_state(self, signals: List[PlantSignalingEvent],
                                           species: PlantSpecies) -> Dict[str, str]:
        """Determine physiological state from signaling patterns"""
        state = {
            "metabolism": "normal",
            "growth": "normal", 
            "defense": "baseline",
            "stress_response": "inactive",
            "communication": "local"
        }
        
        for signal in signals:
            if signal.signal_type == SignalType.STRESS_RESPONSE:
                state["stress_response"] = "active"
                state["metabolism"] = "altered"
            elif signal.signal_type in [SignalType.PATHOGEN_ALERT, SignalType.HERBIVORE_WARNING]:
                state["defense"] = "activated"
            elif signal.signal_type == SignalType.GROWTH_COORDINATION:
                state["growth"] = "coordinated"
            
            if signal.modality == SignalingModality.AIRBORNE:
                state["communication"] = "regional"
        
        return state
    
    async def _assess_communication_network(self, signals: List[PlantSignalingEvent]) -> str:
        """Assess plant's role in communication network"""
        airborne_signals = len([s for s in signals if s.modality == SignalingModality.AIRBORNE])
        chemical_signals = len([s for s in signals if s.modality == SignalingModality.CHEMICAL])
        
        if airborne_signals > 2:
            return "network_hub"
        elif airborne_signals > 0 or chemical_signals > 3:
            return "connected"
        else:
            return "isolated"
    
    async def _calculate_interpretation_confidence(self, signals: List[PlantSignalingEvent]) -> float:
        """Calculate confidence in interpretation"""
        if not signals:
            return 0.0
        
        confidences = [signal.confidence for signal in signals if signal.confidence > 0]
        
        if not confidences:
            return 0.3
        
        avg_confidence = np.mean(confidences)
        
        # Bonus for multiple modalities
        modalities = set(signal.modality for signal in signals)
        modality_bonus = min(len(modalities) * 0.05, 0.2)
        
        # Bonus for signal count
        count_bonus = min(len(signals) * 0.02, 0.1)
        
        return min(avg_confidence + modality_bonus + count_bonus, 1.0)
    
    async def _generate_interpretation_notes(self, species: PlantSpecies,
                                           signals: List[PlantSignalingEvent],
                                           context: EnvironmentalContext) -> List[str]:
        """Generate notes about the interpretation"""
        notes = []
        
        # Species information
        profile = self.plant_db.plant_profiles.get(species)
        if profile:
            notes.append(f"Species: {species.value.replace('_', ' ').title()}")
            notes.append(f"Signaling complexity: {profile.signaling_complexity}")
            notes.append(f"Primary modalities: {[m.value for m in profile.primary_signaling_modes]}")
        
        # Signal analysis
        if signals:
            modalities = set(signal.modality for signal in signals)
            notes.append(f"Active signaling modalities: {[m.value for m in modalities]}")
            
            signal_types = set(signal.signal_type for signal in signals)
            notes.append(f"Signal types detected: {[st.value for st in signal_types]}")
        
        # Context information
        notes.append(f"Environmental context: {context.value.replace('_', ' ')}")
        
        # Specific observations
        chemical_signals = [s for s in signals if s.modality == SignalingModality.CHEMICAL]
        if chemical_signals:
            compounds = []
            for signal in chemical_signals:
                if isinstance(signal.signal_data, ChemicalSignal):
                    compounds.append(signal.signal_data.compound_name)
            if compounds:
                notes.append(f"Chemical compounds detected: {', '.join(compounds[:3])}")
        
        electrical_signals = [s for s in signals if s.modality == SignalingModality.ELECTRICAL]
        if electrical_signals:
            notes.append(f"Electrical activity detected: {len(electrical_signals)} events")
        
        return notes

# Example usage
async def main():
    """Example usage of plant signaling interpretation system"""
    
    # Initialize the system
    interpreter = PlantSignalingInterpretationSystem()
    
    print("Plant Signaling Interpretation System Demo")
    print("=" * 50)
    
    # Example 1: Chemical signaling analysis
    print("Example 1: Chemical Defense Response")
    chemical_data = {
        "salicylic_acid": 5.2,  # elevated levels indicate pathogen response
        "jasmonic_acid": 2.1,   # herbivore defense
        "ethylene": 0.08,       # stress hormone
        "methyl_jasmonate": 0.15 # volatile signal
    }
    
    result1 = await interpreter.interpret_plant_signals(
        chemical_data=chemical_data,
        species=PlantSpecies.TOMATO,
        environmental_context=EnvironmentalContext.PATHOGEN_ATTACK,
        measurement_duration=7200.0  # 2 hours
    )
    
    print(f"Plant status: {result1.plant_status}")
    print(f"Dominant signal types: {[st.value for st in result1.dominant_signal_types]}")
    print(f"Confidence: {result1.confidence:.3f}")
    print(f"Communication network role: {result1.communication_network}")
    
    print("\nInterpreted messages:")
    for message in result1.interpreted_messages:
        print(f"  📡 {message}")
    
    # Example 2: Electrical signaling analysis
    print("\n" + "=" * 30)
    print("Example 2: Electrical Signaling Response")
    
    # Simulate electrical data (action potential)
    sample_rate = 10.0  # Hz
    duration = 300.0    # 5 minutes
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Simulate action potential at t=60s
    voltage_data = np.zeros_like(t)
    ap_start = int(60 * sample_rate)
    ap_duration = int(2 * sample_rate)  # 2 second action potential
    
    if ap_start + ap_duration < len(voltage_data):
        voltage_data[ap_start:ap_start + ap_duration] = 50 * np.exp(-np.linspace(0, 3, ap_duration))
    
    # Add some noise
    voltage_data += np.random.normal(0, 2, len(voltage_data))
    
    electrical_data = (voltage_data, sample_rate)
    
    result2 = await interpreter.interpret_plant_signals(
        electrical_data=electrical_data,
        species=PlantSpecies.ARABIDOPSIS,
        environmental_context=EnvironmentalContext.MECHANICAL_DAMAGE,
        measurement_duration=duration
    )
    
    print(f"Plant status: {result2.plant_status}")
    print(f"Processing time: {result2.processing_time:.2f}s")
    
    print("\nPhysiological state:")
    for state, value in result2.physiological_state.items():
        print(f"  {state}: {value}")
    
    # Example 3: Multi-modal signaling
    print("\n" + "=" * 30)
    print("Example 3: Multi-modal Stress Response")
    
    # Combined chemical and hydraulic response to drought
    drought_chemicals = {
        "abscisic_acid": 8.5,    # drought stress hormone
        "proline": 12.3,         # osmolyte accumulation
        "trehalose": 3.2         # protective sugar
    }
    
    hydraulic_data = {
        "pressure_change": -0.3,  # pressure drop (MPa)
        "flow_rate_change": -25,  # 25% reduction in flow
        "duration": 1800         # 30 minutes
    }
    
    result3 = await interpreter.interpret_plant_signals(
        chemical_data=drought_chemicals,
        hydraulic_data=hydraulic_data,
        species=PlantSpecies.MAIZE,
        environmental_context=EnvironmentalContext.DROUGHT_STRESS,
        measurement_duration=3600.0
    )
    
    print(f"Environmental stressors: {[es.value for es in result3.environmental_stressors]}")
    print(f"Total signals detected: {len(result3.detected_signals)}")
    
    print("\nDetailed interpretation notes:")
    for note in result3.interpretation_notes:
        print(f"  📝 {note}")
    
    if result3.warnings:
        print("\nWarnings:")
        for warning in result3.warnings:
            print(f"  ⚠️  {warning}")
    
    print(f"\nSystem metadata:")
    for key, value in result3.metadata.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())