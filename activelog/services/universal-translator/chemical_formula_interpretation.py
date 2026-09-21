"""
Chemical Formula Interpretation System

This module provides comprehensive interpretation and translation capabilities for
chemical formulas, reactions, and molecular structures across different notation
systems and languages.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
from datetime import datetime
import numpy as np

class ChemicalNotation(Enum):
    """Supported chemical notation systems"""
    MOLECULAR_FORMULA = "molecular_formula"
    STRUCTURAL_FORMULA = "structural_formula"
    SMILES = "smiles"
    IUPAC_NAME = "iupac_name"
    COMMON_NAME = "common_name"
    CAS_NUMBER = "cas_number"
    INCHI = "inchi"
    REACTION_EQUATION = "reaction_equation"
    LEWIS_STRUCTURE = "lewis_structure"
    EMPIRICAL_FORMULA = "empirical_formula"

class ChemicalCategory(Enum):
    """Chemical compound categories"""
    ORGANIC = "organic"
    INORGANIC = "inorganic"
    BIOCHEMICAL = "biochemical"
    POLYMER = "polymer"
    ORGANOMETALLIC = "organometallic"
    IONIC = "ionic"
    COVALENT = "covalent"
    ACID = "acid"
    BASE = "base"
    SALT = "salt"

class ReactionType(Enum):
    """Types of chemical reactions"""
    SYNTHESIS = "synthesis"
    DECOMPOSITION = "decomposition"
    SINGLE_REPLACEMENT = "single_replacement"
    DOUBLE_REPLACEMENT = "double_replacement"
    COMBUSTION = "combustion"
    ACID_BASE = "acid_base"
    REDOX = "redox"
    PRECIPITATION = "precipitation"
    COMPLEXATION = "complexation"
    ENZYMATIC = "enzymatic"

@dataclass
class Element:
    """Represents a chemical element"""
    symbol: str
    name: str
    atomic_number: int
    atomic_mass: float
    group: int
    period: int
    electron_configuration: str
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Compound:
    """Represents a chemical compound"""
    formula: str
    name: str
    molecular_weight: float
    elements: Dict[str, int]  # element symbol -> count
    category: ChemicalCategory
    properties: Dict[str, Any] = field(default_factory=dict)
    synonyms: List[str] = field(default_factory=list)
    cas_number: Optional[str] = None
    smiles: Optional[str] = None
    iupac_name: Optional[str] = None

@dataclass
class ChemicalReaction:
    """Represents a chemical reaction"""
    equation: str
    reactants: List[Compound]
    products: List[Compound]
    reaction_type: ReactionType
    balanced: bool
    conditions: Dict[str, Any] = field(default_factory=dict)
    mechanism: Optional[str] = None
    enthalpy: Optional[float] = None
    entropy: Optional[float] = None

@dataclass
class InterpretationResult:
    """Result of chemical formula interpretation"""
    original_notation: ChemicalNotation
    target_notation: ChemicalNotation
    original_formula: str
    interpreted_result: str
    confidence: float
    processing_time: float
    compound_info: Optional[Compound] = None
    reaction_info: Optional[ChemicalReaction] = None
    interpretation_notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ElementDatabase:
    """Database of chemical elements and their properties"""
    
    def __init__(self):
        self.elements = self._initialize_periodic_table()
        self.element_by_symbol = {e.symbol: e for e in self.elements}
        self.element_by_name = {e.name.lower(): e for e in self.elements}
    
    def _initialize_periodic_table(self) -> List[Element]:
        """Initialize periodic table data"""
        elements = [
            Element("H", "Hydrogen", 1, 1.008, 1, 1, "1s1", {
                "electronegativity": 2.20, "ionization_energy": 13.60, "atomic_radius": 0.37,
                "state_at_stp": "gas", "color": "colorless"
            }),
            Element("He", "Helium", 2, 4.003, 18, 1, "1s2", {
                "electronegativity": None, "ionization_energy": 24.59, "atomic_radius": 0.32,
                "state_at_stp": "gas", "color": "colorless"
            }),
            Element("Li", "Lithium", 3, 6.941, 1, 2, "[He] 2s1", {
                "electronegativity": 0.98, "ionization_energy": 5.39, "atomic_radius": 1.34,
                "state_at_stp": "solid", "color": "silver"
            }),
            Element("Be", "Beryllium", 4, 9.012, 2, 2, "[He] 2s2", {
                "electronegativity": 1.57, "ionization_energy": 9.32, "atomic_radius": 0.90,
                "state_at_stp": "solid", "color": "gray"
            }),
            Element("B", "Boron", 5, 10.811, 13, 2, "[He] 2s2 2p1", {
                "electronegativity": 2.04, "ionization_energy": 8.30, "atomic_radius": 0.82,
                "state_at_stp": "solid", "color": "black"
            }),
            Element("C", "Carbon", 6, 12.011, 14, 2, "[He] 2s2 2p2", {
                "electronegativity": 2.55, "ionization_energy": 11.26, "atomic_radius": 0.77,
                "state_at_stp": "solid", "color": "black"
            }),
            Element("N", "Nitrogen", 7, 14.007, 15, 2, "[He] 2s2 2p3", {
                "electronegativity": 3.04, "ionization_energy": 14.53, "atomic_radius": 0.75,
                "state_at_stp": "gas", "color": "colorless"
            }),
            Element("O", "Oxygen", 8, 15.999, 16, 2, "[He] 2s2 2p4", {
                "electronegativity": 3.44, "ionization_energy": 13.62, "atomic_radius": 0.73,
                "state_at_stp": "gas", "color": "colorless"
            }),
            Element("F", "Fluorine", 9, 18.998, 17, 2, "[He] 2s2 2p5", {
                "electronegativity": 3.98, "ionization_energy": 17.42, "atomic_radius": 0.71,
                "state_at_stp": "gas", "color": "pale yellow"
            }),
            Element("Ne", "Neon", 10, 20.180, 18, 2, "[He] 2s2 2p6", {
                "electronegativity": None, "ionization_energy": 21.56, "atomic_radius": 0.69,
                "state_at_stp": "gas", "color": "colorless"
            }),
            Element("Na", "Sodium", 11, 22.990, 1, 3, "[Ne] 3s1", {
                "electronegativity": 0.93, "ionization_energy": 5.14, "atomic_radius": 1.54,
                "state_at_stp": "solid", "color": "silver"
            }),
            Element("Mg", "Magnesium", 12, 24.305, 2, 3, "[Ne] 3s2", {
                "electronegativity": 1.31, "ionization_energy": 7.65, "atomic_radius": 1.30,
                "state_at_stp": "solid", "color": "silver"
            }),
            Element("Al", "Aluminum", 13, 26.982, 13, 3, "[Ne] 3s2 3p1", {
                "electronegativity": 1.61, "ionization_energy": 5.99, "atomic_radius": 1.18,
                "state_at_stp": "solid", "color": "silver"
            }),
            Element("Si", "Silicon", 14, 28.086, 14, 3, "[Ne] 3s2 3p2", {
                "electronegativity": 1.90, "ionization_energy": 8.15, "atomic_radius": 1.11,
                "state_at_stp": "solid", "color": "gray"
            }),
            Element("P", "Phosphorus", 15, 30.974, 15, 3, "[Ne] 3s2 3p3", {
                "electronegativity": 2.19, "ionization_energy": 10.49, "atomic_radius": 1.06,
                "state_at_stp": "solid", "color": "white/red"
            }),
            Element("S", "Sulfur", 16, 32.065, 16, 3, "[Ne] 3s2 3p4", {
                "electronegativity": 2.58, "ionization_energy": 10.36, "atomic_radius": 1.02,
                "state_at_stp": "solid", "color": "yellow"
            }),
            Element("Cl", "Chlorine", 17, 35.453, 17, 3, "[Ne] 3s2 3p5", {
                "electronegativity": 3.16, "ionization_energy": 12.97, "atomic_radius": 0.99,
                "state_at_stp": "gas", "color": "green"
            }),
            Element("Ar", "Argon", 18, 39.948, 18, 3, "[Ne] 3s2 3p6", {
                "electronegativity": None, "ionization_energy": 15.76, "atomic_radius": 0.97,
                "state_at_stp": "gas", "color": "colorless"
            }),
            Element("K", "Potassium", 19, 39.098, 1, 4, "[Ar] 4s1", {
                "electronegativity": 0.82, "ionization_energy": 4.34, "atomic_radius": 1.96,
                "state_at_stp": "solid", "color": "silver"
            }),
            Element("Ca", "Calcium", 20, 40.078, 2, 4, "[Ar] 4s2", {
                "electronegativity": 1.00, "ionization_energy": 6.11, "atomic_radius": 1.74,
                "state_at_stp": "solid", "color": "silver"
            }),
            Element("Fe", "Iron", 26, 55.845, 8, 4, "[Ar] 3d6 4s2", {
                "electronegativity": 1.83, "ionization_energy": 7.90, "atomic_radius": 1.17,
                "state_at_stp": "solid", "color": "metallic gray"
            }),
            Element("Cu", "Copper", 29, 63.546, 11, 4, "[Ar] 3d10 4s1", {
                "electronegativity": 1.90, "ionization_energy": 7.73, "atomic_radius": 1.17,
                "state_at_stp": "solid", "color": "copper"
            }),
            Element("Zn", "Zinc", 30, 65.38, 12, 4, "[Ar] 3d10 4s2", {
                "electronegativity": 1.65, "ionization_energy": 9.39, "atomic_radius": 1.25,
                "state_at_stp": "solid", "color": "bluish gray"
            }),
            Element("Br", "Bromine", 35, 79.904, 17, 4, "[Ar] 3d10 4s2 4p5", {
                "electronegativity": 2.96, "ionization_energy": 11.81, "atomic_radius": 1.14,
                "state_at_stp": "liquid", "color": "red-brown"
            }),
            Element("I", "Iodine", 53, 126.90, 17, 5, "[Kr] 4d10 5s2 5p5", {
                "electronegativity": 2.66, "ionization_energy": 10.45, "atomic_radius": 1.33,
                "state_at_stp": "solid", "color": "violet"
            }),
            Element("Au", "Gold", 79, 196.97, 11, 6, "[Xe] 4f14 5d10 6s1", {
                "electronegativity": 2.54, "ionization_energy": 9.23, "atomic_radius": 1.35,
                "state_at_stp": "solid", "color": "gold"
            }),
            Element("Ag", "Silver", 47, 107.87, 11, 5, "[Kr] 4d10 5s1", {
                "electronegativity": 1.93, "ionization_energy": 7.58, "atomic_radius": 1.34,
                "state_at_stp": "solid", "color": "silver"
            })
        ]
        
        return elements
    
    def get_element(self, identifier: str) -> Optional[Element]:
        """Get element by symbol or name"""
        if identifier in self.element_by_symbol:
            return self.element_by_symbol[identifier]
        elif identifier.lower() in self.element_by_name:
            return self.element_by_name[identifier.lower()]
        return None

class FormulaParser:
    """Parses chemical formulas into structured components"""
    
    def __init__(self):
        self.element_db = ElementDatabase()
        
    async def parse_molecular_formula(self, formula: str) -> Dict[str, int]:
        """Parse molecular formula into element counts"""
        # Handle parentheses first
        formula = await self._expand_parentheses(formula)
        
        # Extract element-count pairs
        pattern = r'([A-Z][a-z]?)(\d*)'
        matches = re.findall(pattern, formula)
        
        element_counts = {}
        
        for element_symbol, count_str in matches:
            count = int(count_str) if count_str else 1
            
            if element_symbol in element_counts:
                element_counts[element_symbol] += count
            else:
                element_counts[element_symbol] = count
        
        return element_counts
    
    async def _expand_parentheses(self, formula: str) -> str:
        """Expand parentheses in chemical formulas"""
        # Find innermost parentheses
        while '(' in formula:
            # Find the last opening parenthesis
            start = formula.rfind('(')
            if start == -1:
                break
            
            # Find corresponding closing parenthesis
            end = formula.find(')', start)
            if end == -1:
                break
            
            # Extract content and multiplier
            content = formula[start+1:end]
            
            # Find multiplier after closing parenthesis
            multiplier_match = re.match(r'(\d+)', formula[end+1:])
            multiplier = int(multiplier_match.group(1)) if multiplier_match else 1
            
            # Expand the parenthetical content
            expanded = await self._multiply_formula_part(content, multiplier)
            
            # Replace in original formula
            replacement_end = end + 1 + (len(multiplier_match.group(1)) if multiplier_match else 0)
            formula = formula[:start] + expanded + formula[replacement_end:]
        
        return formula
    
    async def _multiply_formula_part(self, formula_part: str, multiplier: int) -> str:
        """Multiply a formula part by a given factor"""
        if multiplier == 1:
            return formula_part
        
        pattern = r'([A-Z][a-z]?)(\d*)'
        matches = re.findall(pattern, formula_part)
        
        expanded = ""
        for element_symbol, count_str in matches:
            count = int(count_str) if count_str else 1
            new_count = count * multiplier
            
            expanded += element_symbol
            if new_count > 1:
                expanded += str(new_count)
        
        return expanded
    
    async def calculate_molecular_weight(self, element_counts: Dict[str, int]) -> float:
        """Calculate molecular weight from element counts"""
        total_weight = 0.0
        
        for element_symbol, count in element_counts.items():
            element = self.element_db.get_element(element_symbol)
            if element:
                total_weight += element.atomic_mass * count
            else:
                # Unknown element, use average atomic mass
                total_weight += 12.0 * count
        
        return total_weight
    
    async def determine_compound_category(self, element_counts: Dict[str, int]) -> ChemicalCategory:
        """Determine compound category based on composition"""
        elements = set(element_counts.keys())
        
        # Check for carbon (organic)
        if 'C' in elements:
            if 'H' in elements:
                return ChemicalCategory.ORGANIC
            else:
                return ChemicalCategory.ORGANOMETALLIC
        
        # Check for metals
        metals = {'Li', 'Na', 'K', 'Mg', 'Ca', 'Al', 'Fe', 'Cu', 'Zn', 'Ag', 'Au'}
        has_metal = bool(elements & metals)
        
        # Check for nonmetals
        nonmetals = {'H', 'C', 'N', 'O', 'F', 'P', 'S', 'Cl', 'Br', 'I'}
        has_nonmetal = bool(elements & nonmetals)
        
        if has_metal and has_nonmetal:
            return ChemicalCategory.IONIC
        elif has_metal:
            return ChemicalCategory.INORGANIC
        else:
            return ChemicalCategory.COVALENT

class CompoundDatabase:
    """Database of known chemical compounds"""
    
    def __init__(self):
        self.compounds = self._initialize_compound_database()
        self.formula_to_compound = {c.formula: c for c in self.compounds}
        self.name_to_compound = {c.name.lower(): c for c in self.compounds}
        
        # Add synonyms to lookup
        for compound in self.compounds:
            for synonym in compound.synonyms:
                self.name_to_compound[synonym.lower()] = compound
    
    def _initialize_compound_database(self) -> List[Compound]:
        """Initialize database of common compounds"""
        compounds = [
            Compound(
                formula="H2O",
                name="Water",
                molecular_weight=18.015,
                elements={"H": 2, "O": 1},
                category=ChemicalCategory.COVALENT,
                properties={
                    "boiling_point": 100.0,
                    "melting_point": 0.0,
                    "density": 1.0,
                    "ph": 7.0,
                    "solubility": "infinite"
                },
                synonyms=["dihydrogen monoxide", "H2O"],
                cas_number="7732-18-5",
                smiles="O",
                iupac_name="oxidane"
            ),
            Compound(
                formula="CO2",
                name="Carbon Dioxide",
                molecular_weight=44.010,
                elements={"C": 1, "O": 2},
                category=ChemicalCategory.COVALENT,
                properties={
                    "boiling_point": -78.5,
                    "melting_point": -56.6,
                    "density": 1.98,
                    "state_at_stp": "gas"
                },
                synonyms=["carbon(IV) oxide", "CO2"],
                cas_number="124-38-9",
                smiles="C(=O)=O",
                iupac_name="carbon dioxide"
            ),
            Compound(
                formula="NaCl",
                name="Sodium Chloride",
                molecular_weight=58.443,
                elements={"Na": 1, "Cl": 1},
                category=ChemicalCategory.IONIC,
                properties={
                    "boiling_point": 1465.0,
                    "melting_point": 801.0,
                    "density": 2.16,
                    "solubility": 36.0
                },
                synonyms=["table salt", "salt", "halite"],
                cas_number="7647-14-5",
                smiles="[Na+].[Cl-]",
                iupac_name="sodium chloride"
            ),
            Compound(
                formula="C6H12O6",
                name="Glucose",
                molecular_weight=180.156,
                elements={"C": 6, "H": 12, "O": 6},
                category=ChemicalCategory.ORGANIC,
                properties={
                    "boiling_point": 146.0,
                    "melting_point": 146.0,
                    "density": 1.54,
                    "solubility": 91.0
                },
                synonyms=["dextrose", "blood sugar", "grape sugar"],
                cas_number="50-99-7",
                smiles="C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)O)O)O)O)O",
                iupac_name="(2R,3S,4R,5R)-2,3,4,5,6-pentahydroxyhexanal"
            ),
            Compound(
                formula="CH4",
                name="Methane",
                molecular_weight=16.043,
                elements={"C": 1, "H": 4},
                category=ChemicalCategory.ORGANIC,
                properties={
                    "boiling_point": -161.5,
                    "melting_point": -182.5,
                    "density": 0.656,
                    "state_at_stp": "gas"
                },
                synonyms=["natural gas", "marsh gas"],
                cas_number="74-82-8",
                smiles="C",
                iupac_name="methane"
            ),
            Compound(
                formula="H2SO4",
                name="Sulfuric Acid",
                molecular_weight=98.079,
                elements={"H": 2, "S": 1, "O": 4},
                category=ChemicalCategory.ACID,
                properties={
                    "boiling_point": 337.0,
                    "melting_point": 10.0,
                    "density": 1.84,
                    "ph": -3.0
                },
                synonyms=["oil of vitriol", "battery acid"],
                cas_number="7664-93-9",
                smiles="OS(=O)(=O)O",
                iupac_name="sulfuric acid"
            ),
            Compound(
                formula="NH3",
                name="Ammonia",
                molecular_weight=17.031,
                elements={"N": 1, "H": 3},
                category=ChemicalCategory.BASE,
                properties={
                    "boiling_point": -33.3,
                    "melting_point": -77.7,
                    "density": 0.73,
                    "ph": 11.6
                },
                synonyms=["azane"],
                cas_number="7664-41-7",
                smiles="N",
                iupac_name="ammonia"
            ),
            Compound(
                formula="C2H5OH",
                name="Ethanol",
                molecular_weight=46.068,
                elements={"C": 2, "H": 6, "O": 1},
                category=ChemicalCategory.ORGANIC,
                properties={
                    "boiling_point": 78.4,
                    "melting_point": -114.1,
                    "density": 0.79,
                    "solubility": "infinite"
                },
                synonyms=["ethyl alcohol", "grain alcohol", "alcohol"],
                cas_number="64-17-5",
                smiles="CCO",
                iupac_name="ethanol"
            ),
            Compound(
                formula="CaCO3",
                name="Calcium Carbonate",
                molecular_weight=100.087,
                elements={"Ca": 1, "C": 1, "O": 3},
                category=ChemicalCategory.IONIC,
                properties={
                    "melting_point": 1339.0,
                    "density": 2.71,
                    "solubility": 0.0015
                },
                synonyms=["limestone", "chalk", "marble"],
                cas_number="471-34-1",
                smiles="C(=O)([O-])[O-].[Ca+2]",
                iupac_name="calcium carbonate"
            ),
            Compound(
                formula="C8H18",
                name="Octane",
                molecular_weight=114.229,
                elements={"C": 8, "H": 18},
                category=ChemicalCategory.ORGANIC,
                properties={
                    "boiling_point": 125.7,
                    "melting_point": -56.8,
                    "density": 0.70,
                    "state_at_stp": "liquid"
                },
                synonyms=["n-octane"],
                cas_number="111-65-9",
                smiles="CCCCCCCC",
                iupac_name="octane"
            )
        ]
        
        return compounds
    
    def find_compound(self, identifier: str) -> Optional[Compound]:
        """Find compound by formula, name, or synonym"""
        # Try exact formula match
        if identifier in self.formula_to_compound:
            return self.formula_to_compound[identifier]
        
        # Try name/synonym match
        if identifier.lower() in self.name_to_compound:
            return self.name_to_compound[identifier.lower()]
        
        return None

class ReactionParser:
    """Parses chemical reaction equations"""
    
    def __init__(self):
        self.formula_parser = FormulaParser()
        self.compound_db = CompoundDatabase()
    
    async def parse_reaction_equation(self, equation: str) -> ChemicalReaction:
        """Parse chemical reaction equation"""
        # Split by arrow
        arrow_patterns = [' -> ', ' → ', ' ⇌ ', ' <-> ', '->']
        
        reactants_str = None
        products_str = None
        
        for pattern in arrow_patterns:
            if pattern in equation:
                parts = equation.split(pattern, 1)
                reactants_str = parts[0].strip()
                products_str = parts[1].strip()
                break
        
        if reactants_str is None or products_str is None:
            raise ValueError("Invalid reaction equation format")
        
        # Parse reactants and products
        reactants = await self._parse_compound_list(reactants_str)
        products = await self._parse_compound_list(products_str)
        
        # Determine reaction type
        reaction_type = await self._determine_reaction_type(reactants, products)
        
        # Check if balanced
        balanced = await self._check_balance(reactants, products)
        
        return ChemicalReaction(
            equation=equation,
            reactants=reactants,
            products=products,
            reaction_type=reaction_type,
            balanced=balanced
        )
    
    async def _parse_compound_list(self, compound_list_str: str) -> List[Compound]:
        """Parse list of compounds (e.g., '2H2 + O2')"""
        compounds = []
        
        # Split by +
        compound_strings = compound_list_str.split('+')
        
        for compound_str in compound_strings:
            compound_str = compound_str.strip()
            
            # Extract coefficient
            coeff_match = re.match(r'^(\d+)\s*(.+)$', compound_str)
            if coeff_match:
                coefficient = int(coeff_match.group(1))
                formula = coeff_match.group(2)
            else:
                coefficient = 1
                formula = compound_str
            
            # Look up compound
            compound = self.compound_db.find_compound(formula)
            
            if not compound:
                # Create basic compound info
                element_counts = await self.formula_parser.parse_molecular_formula(formula)
                molecular_weight = await self.formula_parser.calculate_molecular_weight(element_counts)
                category = await self.formula_parser.determine_compound_category(element_counts)
                
                compound = Compound(
                    formula=formula,
                    name=f"Unknown compound ({formula})",
                    molecular_weight=molecular_weight,
                    elements=element_counts,
                    category=category
                )
            
            # Add coefficient to properties
            compound.properties["coefficient"] = coefficient
            compounds.append(compound)
        
        return compounds
    
    async def _determine_reaction_type(self, reactants: List[Compound], 
                                     products: List[Compound]) -> ReactionType:
        """Determine type of chemical reaction"""
        num_reactants = len(reactants)
        num_products = len(products)
        
        # Synthesis: A + B -> AB
        if num_reactants > 1 and num_products == 1:
            return ReactionType.SYNTHESIS
        
        # Decomposition: AB -> A + B
        if num_reactants == 1 and num_products > 1:
            return ReactionType.DECOMPOSITION
        
        # Check for combustion (contains O2 reactant and CO2/H2O products)
        reactant_formulas = [r.formula for r in reactants]
        product_formulas = [p.formula for p in products]
        
        if "O2" in reactant_formulas:
            if "CO2" in product_formulas or "H2O" in product_formulas:
                return ReactionType.COMBUSTION
        
        # Check for acid-base reaction
        acid_indicators = ["H+", "H3O+", "HCl", "H2SO4", "HNO3"]
        base_indicators = ["OH-", "NH3", "NaOH", "KOH"]
        
        has_acid = any(any(indicator in compound.formula for indicator in acid_indicators) 
                      for compound in reactants)
        has_base = any(any(indicator in compound.formula for indicator in base_indicators) 
                      for compound in reactants)
        
        if has_acid and has_base:
            return ReactionType.ACID_BASE
        
        # Default to single or double replacement
        if num_reactants == 2 and num_products == 2:
            return ReactionType.DOUBLE_REPLACEMENT
        else:
            return ReactionType.SINGLE_REPLACEMENT
    
    async def _check_balance(self, reactants: List[Compound], products: List[Compound]) -> bool:
        """Check if reaction equation is balanced"""
        # Count atoms on both sides
        reactant_atoms = {}
        product_atoms = {}
        
        for compound in reactants:
            coefficient = compound.properties.get("coefficient", 1)
            for element, count in compound.elements.items():
                reactant_atoms[element] = reactant_atoms.get(element, 0) + (count * coefficient)
        
        for compound in products:
            coefficient = compound.properties.get("coefficient", 1)
            for element, count in compound.elements.items():
                product_atoms[element] = product_atoms.get(element, 0) + (count * coefficient)
        
        # Compare atom counts
        all_elements = set(reactant_atoms.keys()) | set(product_atoms.keys())
        
        for element in all_elements:
            reactant_count = reactant_atoms.get(element, 0)
            product_count = product_atoms.get(element, 0)
            
            if reactant_count != product_count:
                return False
        
        return True

class ChemicalTranslator:
    """Translates between different chemical notation systems"""
    
    def __init__(self):
        self.formula_parser = FormulaParser()
        self.compound_db = CompoundDatabase()
        self.reaction_parser = ReactionParser()
    
    async def translate_notation(self, input_text: str, 
                               source_notation: ChemicalNotation,
                               target_notation: ChemicalNotation) -> str:
        """Translate between chemical notation systems"""
        
        if source_notation == ChemicalNotation.MOLECULAR_FORMULA:
            return await self._translate_from_molecular_formula(input_text, target_notation)
        elif source_notation == ChemicalNotation.COMMON_NAME:
            return await self._translate_from_common_name(input_text, target_notation)
        elif source_notation == ChemicalNotation.REACTION_EQUATION:
            return await self._translate_reaction_equation(input_text, target_notation)
        elif source_notation == ChemicalNotation.SMILES:
            return await self._translate_from_smiles(input_text, target_notation)
        else:
            return f"Translation from {source_notation.value} not yet implemented"
    
    async def _translate_from_molecular_formula(self, formula: str, 
                                              target_notation: ChemicalNotation) -> str:
        """Translate from molecular formula"""
        compound = self.compound_db.find_compound(formula)
        
        if target_notation == ChemicalNotation.COMMON_NAME:
            return compound.name if compound else f"Unknown compound ({formula})"
        
        elif target_notation == ChemicalNotation.IUPAC_NAME:
            return compound.iupac_name if compound and compound.iupac_name else f"IUPAC name not available for {formula}"
        
        elif target_notation == ChemicalNotation.SMILES:
            return compound.smiles if compound and compound.smiles else f"SMILES not available for {formula}"
        
        elif target_notation == ChemicalNotation.EMPIRICAL_FORMULA:
            element_counts = await self.formula_parser.parse_molecular_formula(formula)
            return await self._calculate_empirical_formula(element_counts)
        
        else:
            return f"Translation to {target_notation.value} not implemented"
    
    async def _translate_from_common_name(self, name: str, 
                                        target_notation: ChemicalNotation) -> str:
        """Translate from common name"""
        compound = self.compound_db.find_compound(name)
        
        if not compound:
            return f"Unknown compound: {name}"
        
        if target_notation == ChemicalNotation.MOLECULAR_FORMULA:
            return compound.formula
        
        elif target_notation == ChemicalNotation.IUPAC_NAME:
            return compound.iupac_name if compound.iupac_name else f"IUPAC name not available"
        
        elif target_notation == ChemicalNotation.SMILES:
            return compound.smiles if compound.smiles else f"SMILES not available"
        
        elif target_notation == ChemicalNotation.CAS_NUMBER:
            return compound.cas_number if compound.cas_number else f"CAS number not available"
        
        else:
            return f"Translation to {target_notation.value} not implemented"
    
    async def _translate_reaction_equation(self, equation: str, 
                                         target_notation: ChemicalNotation) -> str:
        """Translate reaction equation to different format"""
        reaction = await self.reaction_parser.parse_reaction_equation(equation)
        
        if target_notation == ChemicalNotation.COMMON_NAME:
            # Convert to common names
            reactant_names = [r.name for r in reaction.reactants]
            product_names = [p.name for p in reaction.products]
            
            return f"{' + '.join(reactant_names)} → {' + '.join(product_names)}"
        
        else:
            return f"Reaction translation to {target_notation.value} not implemented"
    
    async def _translate_from_smiles(self, smiles: str, target_notation: ChemicalNotation) -> str:
        """Translate from SMILES notation"""
        # Find compound with matching SMILES
        for compound in self.compound_db.compounds:
            if compound.smiles == smiles:
                if target_notation == ChemicalNotation.MOLECULAR_FORMULA:
                    return compound.formula
                elif target_notation == ChemicalNotation.COMMON_NAME:
                    return compound.name
                elif target_notation == ChemicalNotation.IUPAC_NAME:
                    return compound.iupac_name if compound.iupac_name else "IUPAC name not available"
        
        return f"Unknown SMILES: {smiles}"
    
    async def _calculate_empirical_formula(self, element_counts: Dict[str, int]) -> str:
        """Calculate empirical formula from element counts"""
        if not element_counts:
            return ""
        
        # Find GCD of all counts
        counts = list(element_counts.values())
        gcd = counts[0]
        for count in counts[1:]:
            gcd = np.gcd(gcd, count)
        
        # Divide by GCD to get empirical formula
        empirical_formula = ""
        for element in sorted(element_counts.keys()):
            count = element_counts[element] // gcd
            empirical_formula += element
            if count > 1:
                empirical_formula += str(count)
        
        return empirical_formula

class ChemicalFormulaInterpretationSystem:
    """Main system for chemical formula interpretation"""
    
    def __init__(self):
        self.translator = ChemicalTranslator()
        self.formula_parser = FormulaParser()
        self.compound_db = CompoundDatabase()
        self.element_db = ElementDatabase()
        self.reaction_parser = ReactionParser()
    
    async def interpret_chemical_formula(self, input_formula: str,
                                       source_notation: ChemicalNotation,
                                       target_notation: ChemicalNotation = ChemicalNotation.COMMON_NAME) -> InterpretationResult:
        """Interpret and translate chemical formula"""
        start_time = datetime.now()
        
        try:
            # Translate notation
            interpreted_result = await self.translator.translate_notation(
                input_formula, source_notation, target_notation
            )
            
            # Get detailed compound information
            compound_info = None
            reaction_info = None
            
            if source_notation == ChemicalNotation.MOLECULAR_FORMULA:
                compound_info = await self._analyze_compound(input_formula)
            elif source_notation == ChemicalNotation.REACTION_EQUATION:
                reaction_info = await self.reaction_parser.parse_reaction_equation(input_formula)
            
            # Calculate confidence
            confidence = await self._calculate_confidence(
                source_notation, target_notation, input_formula, interpreted_result
            )
            
            # Generate notes and warnings
            notes = await self._generate_interpretation_notes(
                source_notation, target_notation, compound_info, reaction_info
            )
            warnings = await self._generate_warnings(input_formula, compound_info, reaction_info)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return InterpretationResult(
                original_notation=source_notation,
                target_notation=target_notation,
                original_formula=input_formula,
                interpreted_result=interpreted_result,
                confidence=confidence,
                processing_time=processing_time,
                compound_info=compound_info,
                reaction_info=reaction_info,
                interpretation_notes=notes,
                warnings=warnings,
                metadata={
                    "element_count": len(compound_info.elements) if compound_info else 0,
                    "molecular_weight": compound_info.molecular_weight if compound_info else 0,
                    "compound_category": compound_info.category.value if compound_info else None
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return InterpretationResult(
                original_notation=source_notation,
                target_notation=target_notation,
                original_formula=input_formula,
                interpreted_result=f"Interpretation error: {str(e)}",
                confidence=0.0,
                processing_time=processing_time,
                interpretation_notes=[f"Error: {str(e)}"],
                warnings=["Failed to interpret chemical formula"]
            )
    
    async def _analyze_compound(self, formula: str) -> Compound:
        """Analyze compound from molecular formula"""
        # Check if compound is in database
        compound = self.compound_db.find_compound(formula)
        
        if compound:
            return compound
        
        # Create compound analysis
        element_counts = await self.formula_parser.parse_molecular_formula(formula)
        molecular_weight = await self.formula_parser.calculate_molecular_weight(element_counts)
        category = await self.formula_parser.determine_compound_category(element_counts)
        
        # Generate basic properties
        properties = {
            "state_prediction": await self._predict_state(element_counts),
            "polarity": await self._predict_polarity(element_counts),
            "ionic_character": await self._predict_ionic_character(element_counts)
        }
        
        return Compound(
            formula=formula,
            name=f"Unknown compound ({formula})",
            molecular_weight=molecular_weight,
            elements=element_counts,
            category=category,
            properties=properties
        )
    
    async def _predict_state(self, element_counts: Dict[str, int]) -> str:
        """Predict physical state at STP"""
        elements = set(element_counts.keys())
        
        # Simple heuristics
        if elements == {"H", "O"} and element_counts.get("H", 0) == 2:
            return "liquid"  # Water
        elif "C" in elements and "H" in elements:
            carbon_count = element_counts.get("C", 0)
            if carbon_count <= 4:
                return "gas"
            elif carbon_count <= 16:
                return "liquid"
            else:
                return "solid"
        elif len(elements) == 1:
            element = list(elements)[0]
            element_obj = self.element_db.get_element(element)
            if element_obj:
                return element_obj.properties.get("state_at_stp", "solid")
        
        return "solid"  # Default prediction
    
    async def _predict_polarity(self, element_counts: Dict[str, int]) -> str:
        """Predict molecular polarity"""
        elements = set(element_counts.keys())
        
        # Symmetric molecules tend to be nonpolar
        if len(elements) == 1:
            return "nonpolar"
        
        # Check for highly electronegative atoms
        electronegative = {"F", "O", "N", "Cl", "Br"}
        if elements & electronegative:
            return "polar"
        
        return "slightly polar"
    
    async def _predict_ionic_character(self, element_counts: Dict[str, int]) -> float:
        """Predict ionic character (0-1 scale)"""
        elements = set(element_counts.keys())
        
        metals = {"Li", "Na", "K", "Mg", "Ca", "Al", "Fe", "Cu", "Zn"}
        nonmetals = {"F", "Cl", "Br", "I", "O", "S", "N", "P"}
        
        has_metal = bool(elements & metals)
        has_nonmetal = bool(elements & nonmetals)
        
        if has_metal and has_nonmetal:
            return 0.8  # High ionic character
        elif "C" in elements and "H" in elements:
            return 0.1  # Low ionic character (organic)
        else:
            return 0.4  # Moderate
    
    async def _calculate_confidence(self, source_notation: ChemicalNotation,
                                  target_notation: ChemicalNotation,
                                  input_formula: str, result: str) -> float:
        """Calculate interpretation confidence"""
        base_confidence = 0.8
        
        # Higher confidence for known compounds
        if self.compound_db.find_compound(input_formula):
            base_confidence = 0.95
        
        # Adjust based on notation types
        if source_notation == ChemicalNotation.MOLECULAR_FORMULA:
            if target_notation == ChemicalNotation.COMMON_NAME:
                base_confidence *= 0.9
        elif source_notation == ChemicalNotation.COMMON_NAME:
            if target_notation == ChemicalNotation.MOLECULAR_FORMULA:
                base_confidence *= 0.95
        
        # Check if result indicates error or unknown
        if "unknown" in result.lower() or "error" in result.lower():
            base_confidence *= 0.3
        
        return min(base_confidence, 1.0)
    
    async def _generate_interpretation_notes(self, source_notation: ChemicalNotation,
                                           target_notation: ChemicalNotation,
                                           compound_info: Optional[Compound],
                                           reaction_info: Optional[ChemicalReaction]) -> List[str]:
        """Generate interpretation notes"""
        notes = []
        
        if compound_info:
            notes.append(f"Molecular weight: {compound_info.molecular_weight:.3f} g/mol")
            notes.append(f"Compound category: {compound_info.category.value}")
            
            if compound_info.properties:
                state = compound_info.properties.get("state_prediction")
                if state:
                    notes.append(f"Predicted state at STP: {state}")
        
        if reaction_info:
            notes.append(f"Reaction type: {reaction_info.reaction_type.value}")
            notes.append(f"Equation balanced: {'Yes' if reaction_info.balanced else 'No'}")
            notes.append(f"Reactants: {len(reaction_info.reactants)}, Products: {len(reaction_info.products)}")
        
        # Notation-specific notes
        if target_notation == ChemicalNotation.EMPIRICAL_FORMULA:
            notes.append("Empirical formula shows simplest whole number ratio")
        elif target_notation == ChemicalNotation.SMILES:
            notes.append("SMILES notation represents molecular structure")
        
        return notes
    
    async def _generate_warnings(self, input_formula: str,
                               compound_info: Optional[Compound],
                               reaction_info: Optional[ChemicalReaction]) -> List[str]:
        """Generate warnings about interpretation"""
        warnings = []
        
        # Check for unusual formulas
        if re.search(r'\d{3,}', input_formula):
            warnings.append("Large subscripts detected - verify formula accuracy")
        
        if compound_info and not self.compound_db.find_compound(compound_info.formula):
            warnings.append("Compound not found in database - properties are predicted")
        
        if reaction_info and not reaction_info.balanced:
            warnings.append("Chemical equation is not balanced")
        
        # Check for potentially hazardous compounds
        hazardous_elements = {"F", "Cl", "Br", "I", "Hg", "Pb", "As"}
        if compound_info:
            elements = set(compound_info.elements.keys())
            if elements & hazardous_elements:
                warnings.append("Compound may contain hazardous elements")
        
        return warnings
    
    async def batch_interpret_formulas(self, formulas: List[Tuple[str, ChemicalNotation]], 
                                     target_notation: ChemicalNotation = ChemicalNotation.COMMON_NAME) -> List[InterpretationResult]:
        """Interpret multiple chemical formulas in batch"""
        tasks = [
            self.interpret_chemical_formula(formula, source_notation, target_notation)
            for formula, source_notation in formulas
        ]
        
        return await asyncio.gather(*tasks)

# Example usage
async def main():
    """Example usage of chemical formula interpretation system"""
    
    # Initialize the system
    interpreter = ChemicalFormulaInterpretationSystem()
    
    print("Chemical Formula Interpretation System Demo")
    print("=" * 50)
    
    # Example 1: Molecular formula to common name
    print("Example 1: Molecular formula interpretation")
    result1 = await interpreter.interpret_chemical_formula(
        input_formula="C6H12O6",
        source_notation=ChemicalNotation.MOLECULAR_FORMULA,
        target_notation=ChemicalNotation.COMMON_NAME
    )
    
    print(f"Formula: {result1.original_formula}")
    print(f"Common name: {result1.interpreted_result}")
    print(f"Molecular weight: {result1.compound_info.molecular_weight:.3f} g/mol")
    print(f"Category: {result1.compound_info.category.value}")
    print(f"Confidence: {result1.confidence:.3f}")
    
    # Example 2: Common name to molecular formula
    print("\n" + "=" * 30)
    print("Example 2: Common name to formula")
    result2 = await interpreter.interpret_chemical_formula(
        input_formula="water",
        source_notation=ChemicalNotation.COMMON_NAME,
        target_notation=ChemicalNotation.MOLECULAR_FORMULA
    )
    
    print(f"Common name: {result2.original_formula}")
    print(f"Molecular formula: {result2.interpreted_result}")
    print(f"SMILES: {result2.compound_info.smiles}")
    
    # Example 3: Reaction equation analysis
    print("\n" + "=" * 30)
    print("Example 3: Chemical reaction analysis")
    result3 = await interpreter.interpret_chemical_formula(
        input_formula="2H2 + O2 -> 2H2O",
        source_notation=ChemicalNotation.REACTION_EQUATION,
        target_notation=ChemicalNotation.COMMON_NAME
    )
    
    print(f"Reaction: {result3.original_formula}")
    print(f"In common names: {result3.interpreted_result}")
    print(f"Reaction type: {result3.reaction_info.reaction_type.value}")
    print(f"Balanced: {result3.reaction_info.balanced}")
    
    # Example 4: Complex organic molecule
    print("\n" + "=" * 30)
    print("Example 4: Complex molecule analysis")
    result4 = await interpreter.interpret_chemical_formula(
        input_formula="C8H18",
        source_notation=ChemicalNotation.MOLECULAR_FORMULA,
        target_notation=ChemicalNotation.EMPIRICAL_FORMULA
    )
    
    print(f"Molecular formula: {result4.original_formula}")
    print(f"Empirical formula: {result4.interpreted_result}")
    
    # Show interpretation notes
    if result4.interpretation_notes:
        print("Notes:")
        for note in result4.interpretation_notes:
            print(f"  📝 {note}")
    
    if result4.warnings:
        print("Warnings:")
        for warning in result4.warnings:
            print(f"  ⚠️  {warning}")

if __name__ == "__main__":
    asyncio.run(main())