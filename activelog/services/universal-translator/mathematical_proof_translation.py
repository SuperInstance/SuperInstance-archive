"""
Mathematical Proof Translation System

This module provides comprehensive translation and interpretation capabilities for
mathematical proofs, theorems, and formal mathematical expressions across different
notation systems and languages.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
from datetime import datetime
import sympy as sp
import numpy as np

class MathNotation(Enum):
    """Supported mathematical notation systems"""
    LATEX = "latex"
    MATHML = "mathml"
    ASCII_MATH = "ascii_math"
    UNICODE_MATH = "unicode_math"
    NATURAL_LANGUAGE = "natural_language"
    FORMAL_LOGIC = "formal_logic"
    LEAN_THEOREM_PROVER = "lean"
    COQQ_THEOREM_PROVER = "coq"
    ISABELLE = "isabelle"
    SET_THEORY = "set_theory"
    CATEGORY_THEORY = "category_theory"

class MathField(Enum):
    """Mathematical fields and areas"""
    ALGEBRA = "algebra"
    CALCULUS = "calculus"
    GEOMETRY = "geometry"
    NUMBER_THEORY = "number_theory"
    TOPOLOGY = "topology"
    ANALYSIS = "analysis"
    LOGIC = "logic"
    PROBABILITY = "probability"
    STATISTICS = "statistics"
    DISCRETE_MATH = "discrete_mathematics"
    LINEAR_ALGEBRA = "linear_algebra"
    DIFFERENTIAL_EQUATIONS = "differential_equations"

class ProofTechnique(Enum):
    """Mathematical proof techniques"""
    DIRECT_PROOF = "direct"
    PROOF_BY_CONTRADICTION = "contradiction"
    PROOF_BY_INDUCTION = "induction"
    PROOF_BY_CONTRAPOSITIVE = "contrapositive"
    PROOF_BY_CASES = "cases"
    PROOF_BY_CONSTRUCTION = "construction"
    PROOF_BY_EXHAUSTION = "exhaustion"
    PROOF_BY_INFINITE_DESCENT = "infinite_descent"
    PROBABILISTIC_PROOF = "probabilistic"

@dataclass
class MathSymbol:
    """Represents a mathematical symbol"""
    latex: str
    unicode: str
    ascii: str
    meaning: str
    category: str
    context: List[str] = field(default_factory=list)

@dataclass
class MathExpression:
    """Represents a mathematical expression"""
    expression: str
    notation: MathNotation
    field: Optional[MathField] = None
    variables: Set[str] = field(default_factory=set)
    constants: Set[str] = field(default_factory=set)
    operators: Set[str] = field(default_factory=set)
    functions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProofStep:
    """Represents a step in a mathematical proof"""
    step_number: int
    statement: str
    justification: str
    technique: Optional[ProofTechnique] = None
    references: List[int] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    conclusions: List[str] = field(default_factory=list)

@dataclass
class MathematicalProof:
    """Represents a complete mathematical proof"""
    theorem_statement: str
    assumptions: List[str]
    steps: List[ProofStep]
    conclusion: str
    field: MathField
    techniques_used: Set[ProofTechnique]
    difficulty: str  # beginner, intermediate, advanced, expert
    completeness: float  # 0-1 score
    rigor: float  # 0-1 score
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TranslationResult:
    """Result of mathematical proof translation"""
    source_notation: MathNotation
    target_notation: MathNotation
    original_proof: str
    translated_proof: str
    confidence: float
    processing_time: float
    proof_structure: Optional[MathematicalProof] = None
    translation_notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class MathSymbolDatabase:
    """Database of mathematical symbols and their representations"""
    
    def __init__(self):
        self.symbols = self._initialize_symbol_database()
        self.latex_to_symbol = {s.latex: s for s in self.symbols}
        self.unicode_to_symbol = {s.unicode: s for s in self.symbols}
        self.ascii_to_symbol = {s.ascii: s for s in self.symbols}
    
    def _initialize_symbol_database(self) -> List[MathSymbol]:
        """Initialize database of mathematical symbols"""
        symbols = [
            # Greek letters
            MathSymbol(r"\alpha", "α", "alpha", "angle, coefficient", "greek_letter", ["geometry", "physics"]),
            MathSymbol(r"\beta", "β", "beta", "angle, coefficient", "greek_letter", ["geometry", "statistics"]),
            MathSymbol(r"\gamma", "γ", "gamma", "angle, function", "greek_letter", ["geometry", "analysis"]),
            MathSymbol(r"\delta", "δ", "delta", "small change, limit", "greek_letter", ["calculus", "analysis"]),
            MathSymbol(r"\epsilon", "ε", "epsilon", "small positive number", "greek_letter", ["analysis", "topology"]),
            MathSymbol(r"\theta", "θ", "theta", "angle", "greek_letter", ["geometry", "trigonometry"]),
            MathSymbol(r"\lambda", "λ", "lambda", "eigenvalue, parameter", "greek_letter", ["linear_algebra", "analysis"]),
            MathSymbol(r"\mu", "μ", "mu", "mean, measure", "greek_letter", ["statistics", "measure_theory"]),
            MathSymbol(r"\pi", "π", "pi", "circle constant", "greek_letter", ["geometry", "analysis"]),
            MathSymbol(r"\sigma", "σ", "sigma", "standard deviation, sum", "greek_letter", ["statistics", "analysis"]),
            MathSymbol(r"\phi", "φ", "phi", "golden ratio, angle", "greek_letter", ["geometry", "number_theory"]),
            MathSymbol(r"\psi", "ψ", "psi", "wave function, angle", "greek_letter", ["physics", "geometry"]),
            MathSymbol(r"\omega", "ω", "omega", "angular frequency", "greek_letter", ["physics", "analysis"]),
            
            # Operators
            MathSymbol(r"\in", "∈", "in", "element of", "set_operator", ["set_theory", "logic"]),
            MathSymbol(r"\notin", "∉", "notin", "not element of", "set_operator", ["set_theory", "logic"]),
            MathSymbol(r"\subset", "⊂", "subset", "proper subset", "set_operator", ["set_theory"]),
            MathSymbol(r"\subseteq", "⊆", "subseteq", "subset or equal", "set_operator", ["set_theory"]),
            MathSymbol(r"\supset", "⊃", "supset", "proper superset", "set_operator", ["set_theory"]),
            MathSymbol(r"\supseteq", "⊇", "supseteq", "superset or equal", "set_operator", ["set_theory"]),
            MathSymbol(r"\cup", "∪", "union", "set union", "set_operator", ["set_theory"]),
            MathSymbol(r"\cap", "∩", "intersection", "set intersection", "set_operator", ["set_theory"]),
            MathSymbol(r"\emptyset", "∅", "emptyset", "empty set", "set_operator", ["set_theory"]),
            
            # Logic
            MathSymbol(r"\land", "∧", "and", "logical and", "logic_operator", ["logic", "set_theory"]),
            MathSymbol(r"\lor", "∨", "or", "logical or", "logic_operator", ["logic", "set_theory"]),
            MathSymbol(r"\neg", "¬", "not", "logical not", "logic_operator", ["logic"]),
            MathSymbol(r"\implies", "⟹", "implies", "logical implication", "logic_operator", ["logic"]),
            MathSymbol(r"\iff", "⟺", "iff", "if and only if", "logic_operator", ["logic"]),
            MathSymbol(r"\forall", "∀", "forall", "for all", "quantifier", ["logic", "analysis"]),
            MathSymbol(r"\exists", "∃", "exists", "there exists", "quantifier", ["logic", "analysis"]),
            MathSymbol(r"\nexists", "∄", "nexists", "does not exist", "quantifier", ["logic"]),
            
            # Calculus
            MathSymbol(r"\int", "∫", "int", "integral", "calculus_operator", ["calculus", "analysis"]),
            MathSymbol(r"\sum", "∑", "sum", "summation", "calculus_operator", ["calculus", "discrete"]),
            MathSymbol(r"\prod", "∏", "prod", "product", "calculus_operator", ["calculus", "discrete"]),
            MathSymbol(r"\partial", "∂", "partial", "partial derivative", "calculus_operator", ["calculus"]),
            MathSymbol(r"\nabla", "∇", "nabla", "gradient operator", "calculus_operator", ["vector_calculus"]),
            MathSymbol(r"\lim", "lim", "lim", "limit", "calculus_operator", ["calculus", "analysis"]),
            
            # Comparison
            MathSymbol(r"\leq", "≤", "<=", "less than or equal", "comparison", ["algebra", "analysis"]),
            MathSymbol(r"\geq", "≥", ">=", "greater than or equal", "comparison", ["algebra", "analysis"]),
            MathSymbol(r"\neq", "≠", "!=", "not equal", "comparison", ["algebra"]),
            MathSymbol(r"\approx", "≈", "approx", "approximately equal", "comparison", ["analysis"]),
            MathSymbol(r"\equiv", "≡", "equiv", "equivalent", "comparison", ["algebra", "logic"]),
            
            # Special functions
            MathSymbol(r"\sin", "sin", "sin", "sine function", "function", ["trigonometry", "analysis"]),
            MathSymbol(r"\cos", "cos", "cos", "cosine function", "function", ["trigonometry", "analysis"]),
            MathSymbol(r"\tan", "tan", "tan", "tangent function", "function", ["trigonometry", "analysis"]),
            MathSymbol(r"\log", "log", "log", "logarithm", "function", ["algebra", "analysis"]),
            MathSymbol(r"\ln", "ln", "ln", "natural logarithm", "function", ["analysis"]),
            MathSymbol(r"\exp", "exp", "exp", "exponential function", "function", ["analysis"]),
            
            # Number sets
            MathSymbol(r"\mathbb{N}", "ℕ", "N", "natural numbers", "number_set", ["number_theory"]),
            MathSymbol(r"\mathbb{Z}", "ℤ", "Z", "integers", "number_set", ["number_theory"]),
            MathSymbol(r"\mathbb{Q}", "ℚ", "Q", "rational numbers", "number_set", ["number_theory"]),
            MathSymbol(r"\mathbb{R}", "ℝ", "R", "real numbers", "number_set", ["analysis"]),
            MathSymbol(r"\mathbb{C}", "ℂ", "C", "complex numbers", "number_set", ["complex_analysis"]),
            
            # Infinity
            MathSymbol(r"\infty", "∞", "infinity", "infinity", "special", ["analysis", "set_theory"])
        ]
        
        return symbols
    
    def find_symbol(self, representation: str, notation_type: str = "latex") -> Optional[MathSymbol]:
        """Find symbol by representation"""
        if notation_type == "latex":
            return self.latex_to_symbol.get(representation)
        elif notation_type == "unicode":
            return self.unicode_to_symbol.get(representation)
        elif notation_type == "ascii":
            return self.ascii_to_symbol.get(representation)
        return None

class MathExpressionParser:
    """Parses mathematical expressions into structured components"""
    
    def __init__(self):
        self.symbol_db = MathSymbolDatabase()
        
    async def parse_expression(self, expression: str, notation: MathNotation) -> MathExpression:
        """Parse mathematical expression"""
        if notation == MathNotation.LATEX:
            return await self._parse_latex(expression)
        elif notation == MathNotation.NATURAL_LANGUAGE:
            return await self._parse_natural_language(expression)
        elif notation == MathNotation.ASCII_MATH:
            return await self._parse_ascii_math(expression)
        else:
            return await self._parse_generic(expression, notation)
    
    async def _parse_latex(self, latex_expr: str) -> MathExpression:
        """Parse LaTeX mathematical expression"""
        variables = set()
        constants = set()
        operators = set()
        functions = set()
        
        # Extract LaTeX commands
        latex_commands = re.findall(r'\\[a-zA-Z]+', latex_expr)
        for cmd in latex_commands:
            symbol = self.symbol_db.find_symbol(cmd, "latex")
            if symbol:
                if symbol.category == "function":
                    functions.add(symbol.meaning)
                elif symbol.category in ["logic_operator", "set_operator", "calculus_operator"]:
                    operators.add(symbol.meaning)
                elif symbol.category == "greek_letter":
                    variables.add(symbol.unicode)
        
        # Extract single letter variables (common in math)
        single_letters = re.findall(r'(?<!\\)[a-zA-Z]', latex_expr)
        for letter in single_letters:
            if letter not in ['e', 'i']:  # Exclude common constants
                variables.add(letter)
            else:
                constants.add(letter)
        
        # Extract numbers
        numbers = re.findall(r'\d+', latex_expr)
        constants.update(numbers)
        
        # Determine field based on symbols used
        field = await self._determine_math_field(latex_commands + list(operators))
        
        return MathExpression(
            expression=latex_expr,
            notation=MathNotation.LATEX,
            field=field,
            variables=variables,
            constants=constants,
            operators=operators,
            functions=functions
        )
    
    async def _parse_natural_language(self, text: str) -> MathExpression:
        """Parse natural language mathematical statement"""
        variables = set()
        constants = set()
        operators = set()
        functions = set()
        
        # Common mathematical phrases
        math_phrases = {
            "for all": "∀",
            "there exists": "∃",
            "such that": "|",
            "implies": "⟹",
            "if and only if": "⟺",
            "greater than": ">",
            "less than": "<",
            "equal to": "=",
            "not equal": "≠",
            "integral": "∫",
            "derivative": "d/dx",
            "limit": "lim",
            "sum": "∑",
            "product": "∏"
        }
        
        text_lower = text.lower()
        for phrase, symbol in math_phrases.items():
            if phrase in text_lower:
                operators.add(phrase)
        
        # Extract potential variables (single letters mentioned)
        potential_vars = re.findall(r'\b[a-zA-Z]\b', text)
        variables.update(potential_vars)
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', text)
        constants.update(numbers)
        
        field = await self._determine_field_from_text(text)
        
        return MathExpression(
            expression=text,
            notation=MathNotation.NATURAL_LANGUAGE,
            field=field,
            variables=variables,
            constants=constants,
            operators=operators,
            functions=functions
        )
    
    async def _parse_ascii_math(self, ascii_expr: str) -> MathExpression:
        """Parse ASCII mathematical expression"""
        variables = set()
        constants = set()
        operators = set()
        functions = set()
        
        # Common ASCII operators
        ascii_operators = {
            ">=": "greater than or equal",
            "<=": "less than or equal",
            "!=": "not equal",
            "->": "implies",
            "&&": "and",
            "||": "or",
            "!": "not",
            "sum": "summation",
            "int": "integral",
            "lim": "limit"
        }
        
        for op, meaning in ascii_operators.items():
            if op in ascii_expr:
                operators.add(meaning)
        
        # Extract variables and numbers
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+', ascii_expr)
        for token in tokens:
            if token.isdigit():
                constants.add(token)
            elif token in ["sin", "cos", "tan", "log", "exp", "sqrt"]:
                functions.add(token)
            else:
                variables.add(token)
        
        return MathExpression(
            expression=ascii_expr,
            notation=MathNotation.ASCII_MATH,
            variables=variables,
            constants=constants,
            operators=operators,
            functions=functions
        )
    
    async def _parse_generic(self, expression: str, notation: MathNotation) -> MathExpression:
        """Generic parser for other notations"""
        return MathExpression(
            expression=expression,
            notation=notation,
            variables=set(),
            constants=set(),
            operators=set(),
            functions=set()
        )
    
    async def _determine_math_field(self, symbols: List[str]) -> Optional[MathField]:
        """Determine mathematical field based on symbols used"""
        field_indicators = {
            MathField.CALCULUS: ["\\int", "\\partial", "\\lim", "\\sum", "\\nabla"],
            MathField.ALGEBRA: ["\\neq", "\\equiv", "\\leq", "\\geq"],
            MathField.SET_THEORY: ["\\in", "\\subset", "\\cup", "\\cap", "\\emptyset"],
            MathField.LOGIC: ["\\land", "\\lor", "\\neg", "\\implies", "\\forall", "\\exists"],
            MathField.GEOMETRY: ["\\angle", "\\theta", "\\sin", "\\cos"],
            MathField.NUMBER_THEORY: ["\\mathbb{N}", "\\mathbb{Z}", "\\mathbb{Q}"],
            MathField.ANALYSIS: ["\\mathbb{R}", "\\epsilon", "\\delta", "\\lim"]
        }
        
        for field, indicators in field_indicators.items():
            if any(indicator in symbols for indicator in indicators):
                return field
        
        return None
    
    async def _determine_field_from_text(self, text: str) -> Optional[MathField]:
        """Determine mathematical field from natural language text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["integral", "derivative", "limit", "continuous"]):
            return MathField.CALCULUS
        elif any(word in text_lower for word in ["set", "element", "union", "intersection"]):
            return MathField.SET_THEORY
        elif any(word in text_lower for word in ["and", "or", "not", "implies", "for all", "exists"]):
            return MathField.LOGIC
        elif any(word in text_lower for word in ["angle", "triangle", "circle", "geometry"]):
            return MathField.GEOMETRY
        elif any(word in text_lower for word in ["prime", "integer", "divisible", "congruent"]):
            return MathField.NUMBER_THEORY
        else:
            return MathField.ALGEBRA

class ProofParser:
    """Parses mathematical proofs into structured components"""
    
    def __init__(self):
        self.expression_parser = MathExpressionParser()
        
    async def parse_proof(self, proof_text: str, notation: MathNotation) -> MathematicalProof:
        """Parse mathematical proof into structured format"""
        lines = proof_text.strip().split('\n')
        
        theorem_statement = ""
        assumptions = []
        steps = []
        conclusion = ""
        techniques_used = set()
        
        current_step = 0
        in_proof = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Identify theorem statement
            if any(keyword in line.lower() for keyword in ["theorem", "proposition", "lemma", "corollary"]):
                theorem_statement = line
                
            # Identify assumptions
            elif any(keyword in line.lower() for keyword in ["assume", "given", "let", "suppose"]):
                assumptions.append(line)
                
            # Identify proof start
            elif "proof" in line.lower() and not in_proof:
                in_proof = True
                
            # Identify conclusion
            elif any(keyword in line.lower() for keyword in ["therefore", "thus", "hence", "qed", "∎"]):
                conclusion = line
                
            # Parse proof steps
            elif in_proof and not conclusion:
                current_step += 1
                technique = await self._identify_proof_technique(line)
                if technique:
                    techniques_used.add(technique)
                
                step = ProofStep(
                    step_number=current_step,
                    statement=line,
                    justification=await self._extract_justification(line),
                    technique=technique,
                    references=[],
                    assumptions=[],
                    conclusions=[]
                )
                steps.append(step)
        
        # Determine field and difficulty
        field = await self._determine_proof_field(theorem_statement + " " + proof_text)
        difficulty = await self._assess_difficulty(steps, techniques_used)
        completeness = await self._assess_completeness(steps)
        rigor = await self._assess_rigor(steps, techniques_used)
        
        return MathematicalProof(
            theorem_statement=theorem_statement,
            assumptions=assumptions,
            steps=steps,
            conclusion=conclusion,
            field=field,
            techniques_used=techniques_used,
            difficulty=difficulty,
            completeness=completeness,
            rigor=rigor
        )
    
    async def _identify_proof_technique(self, line: str) -> Optional[ProofTechnique]:
        """Identify proof technique used in a line"""
        line_lower = line.lower()
        
        if any(phrase in line_lower for phrase in ["contradiction", "assume not", "suppose not"]):
            return ProofTechnique.PROOF_BY_CONTRADICTION
        elif any(phrase in line_lower for phrase in ["induction", "base case", "inductive step"]):
            return ProofTechnique.PROOF_BY_INDUCTION
        elif any(phrase in line_lower for phrase in ["contrapositive", "assume not"]):
            return ProofTechnique.PROOF_BY_CONTRAPOSITIVE
        elif any(phrase in line_lower for phrase in ["case", "consider"]):
            return ProofTechnique.PROOF_BY_CASES
        elif any(phrase in line_lower for phrase in ["construct", "define", "let"]):
            return ProofTechnique.PROOF_BY_CONSTRUCTION
        else:
            return ProofTechnique.DIRECT_PROOF
    
    async def _extract_justification(self, line: str) -> str:
        """Extract justification from proof line"""
        # Look for common justification patterns
        justifications = [
            "by definition", "by assumption", "by theorem", "by lemma",
            "by induction hypothesis", "by contradiction", "since", "because"
        ]
        
        line_lower = line.lower()
        for just in justifications:
            if just in line_lower:
                return just
        
        return "direct reasoning"
    
    async def _determine_proof_field(self, proof_text: str) -> MathField:
        """Determine mathematical field of the proof"""
        text_lower = proof_text.lower()
        
        field_keywords = {
            MathField.CALCULUS: ["integral", "derivative", "limit", "continuous", "differentiable"],
            MathField.ALGEBRA: ["polynomial", "equation", "solution", "root", "coefficient"],
            MathField.NUMBER_THEORY: ["prime", "divisible", "congruent", "integer", "modulo"],
            MathField.GEOMETRY: ["triangle", "angle", "circle", "polygon", "euclidean"],
            MathField.SET_THEORY: ["set", "element", "union", "intersection", "subset"],
            MathField.LOGIC: ["proposition", "predicate", "formula", "satisfiable"],
            MathField.TOPOLOGY: ["open", "closed", "compact", "connected", "continuous"],
            MathField.ANALYSIS: ["sequence", "series", "convergent", "bounded", "metric"]
        }
        
        for field, keywords in field_keywords.items():
            if sum(1 for keyword in keywords if keyword in text_lower) >= 2:
                return field
        
        return MathField.ALGEBRA  # Default
    
    async def _assess_difficulty(self, steps: List[ProofStep], techniques: Set[ProofTechnique]) -> str:
        """Assess difficulty level of the proof"""
        num_steps = len(steps)
        num_techniques = len(techniques)
        
        # Simple heuristic based on length and technique complexity
        advanced_techniques = {
            ProofTechnique.PROOF_BY_CONTRADICTION,
            ProofTechnique.PROOF_BY_INDUCTION,
            ProofTechnique.PROOF_BY_INFINITE_DESCENT
        }
        
        has_advanced = bool(techniques & advanced_techniques)
        
        if num_steps <= 3 and not has_advanced:
            return "beginner"
        elif num_steps <= 8 and num_techniques <= 2:
            return "intermediate"
        elif num_steps <= 15 or has_advanced:
            return "advanced"
        else:
            return "expert"
    
    async def _assess_completeness(self, steps: List[ProofStep]) -> float:
        """Assess completeness of the proof (0-1 scale)"""
        if not steps:
            return 0.0
        
        # Simple heuristic: more steps with justifications = more complete
        justified_steps = sum(1 for step in steps if step.justification != "direct reasoning")
        completeness_score = min(justified_steps / len(steps), 1.0)
        
        # Bonus for having clear structure
        if len(steps) >= 3:
            completeness_score += 0.1
        
        return min(completeness_score, 1.0)
    
    async def _assess_rigor(self, steps: List[ProofStep], techniques: Set[ProofTechnique]) -> float:
        """Assess rigor of the proof (0-1 scale)"""
        base_rigor = 0.6
        
        # Bonus for using formal techniques
        formal_techniques = {
            ProofTechnique.PROOF_BY_CONTRADICTION,
            ProofTechnique.PROOF_BY_INDUCTION,
            ProofTechnique.PROOF_BY_CONTRAPOSITIVE
        }
        
        if techniques & formal_techniques:
            base_rigor += 0.2
        
        # Bonus for detailed justifications
        detailed_steps = sum(1 for step in steps 
                           if len(step.justification) > 10 and "direct reasoning" not in step.justification)
        if detailed_steps > len(steps) * 0.5:
            base_rigor += 0.1
        
        return min(base_rigor, 1.0)

class MathNotationTranslator:
    """Translates between different mathematical notation systems"""
    
    def __init__(self):
        self.symbol_db = MathSymbolDatabase()
        
    async def translate_notation(self, expression: str, 
                               source_notation: MathNotation,
                               target_notation: MathNotation) -> str:
        """Translate between mathematical notations"""
        
        if source_notation == target_notation:
            return expression
        
        if source_notation == MathNotation.LATEX and target_notation == MathNotation.UNICODE_MATH:
            return await self._latex_to_unicode(expression)
        elif source_notation == MathNotation.LATEX and target_notation == MathNotation.NATURAL_LANGUAGE:
            return await self._latex_to_natural_language(expression)
        elif source_notation == MathNotation.NATURAL_LANGUAGE and target_notation == MathNotation.LATEX:
            return await self._natural_language_to_latex(expression)
        elif source_notation == MathNotation.ASCII_MATH and target_notation == MathNotation.LATEX:
            return await self._ascii_to_latex(expression)
        elif source_notation == MathNotation.LATEX and target_notation == MathNotation.ASCII_MATH:
            return await self._latex_to_ascii(expression)
        else:
            return f"Translation from {source_notation.value} to {target_notation.value} not yet implemented"
    
    async def _latex_to_unicode(self, latex_expr: str) -> str:
        """Convert LaTeX to Unicode mathematical notation"""
        result = latex_expr
        
        # Replace LaTeX commands with Unicode symbols
        for symbol in self.symbol_db.symbols:
            result = result.replace(symbol.latex, symbol.unicode)
        
        # Clean up remaining LaTeX syntax
        result = re.sub(r'\\[a-zA-Z]+', '', result)  # Remove unknown commands
        result = re.sub(r'[{}]', '', result)  # Remove braces
        result = re.sub(r'\s+', ' ', result).strip()  # Normalize whitespace
        
        return result
    
    async def _latex_to_natural_language(self, latex_expr: str) -> str:
        """Convert LaTeX to natural language description"""
        result = latex_expr
        
        # Common LaTeX to English translations
        translations = {
            r"\\forall": "for all",
            r"\\exists": "there exists", 
            r"\\in": "is an element of",
            r"\\subset": "is a subset of",
            r"\\implies": "implies",
            r"\\iff": "if and only if",
            r"\\leq": "is less than or equal to",
            r"\\geq": "is greater than or equal to",
            r"\\neq": "is not equal to",
            r"\\approx": "is approximately equal to",
            r"\\int": "the integral of",
            r"\\sum": "the sum of",
            r"\\lim": "the limit of",
            r"\\frac\{([^}]+)\}\{([^}]+)\}": r"\1 divided by \2",
            r"\^2": " squared",
            r"\^3": " cubed",
            r"\^n": " to the power of n",
            r"\\sqrt\{([^}]+)\}": r"the square root of \1"
        }
        
        for latex_pattern, english in translations.items():
            result = re.sub(latex_pattern, english, result)
        
        # Clean up remaining LaTeX syntax
        result = re.sub(r'\\[a-zA-Z]+', '', result)
        result = re.sub(r'[{}$]', '', result)
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    async def _natural_language_to_latex(self, text: str) -> str:
        """Convert natural language to LaTeX notation"""
        result = text.lower()
        
        # English to LaTeX translations
        translations = {
            "for all": r"\\forall",
            "there exists": r"\\exists",
            "is an element of": r"\\in",
            "is a subset of": r"\\subset", 
            "implies": r"\\implies",
            "if and only if": r"\\iff",
            "is less than or equal to": r"\\leq",
            "is greater than or equal to": r"\\geq",
            "is not equal to": r"\\neq",
            "is approximately equal to": r"\\approx",
            "the integral of": r"\\int",
            "the sum of": r"\\sum",
            "the limit of": r"\\lim",
            " squared": "^2",
            " cubed": "^3",
            "the square root of": r"\\sqrt",
            " divided by ": r"\\frac{"
        }
        
        for english, latex in translations.items():
            result = result.replace(english, latex)
        
        return result
    
    async def _ascii_to_latex(self, ascii_expr: str) -> str:
        """Convert ASCII math to LaTeX"""
        result = ascii_expr
        
        ascii_to_latex = {
            ">=": r"\\geq",
            "<=": r"\\leq", 
            "!=": r"\\neq",
            "->": r"\\rightarrow",
            "<->": r"\\leftrightarrow",
            "alpha": r"\\alpha",
            "beta": r"\\beta",
            "gamma": r"\\gamma",
            "delta": r"\\delta",
            "epsilon": r"\\epsilon",
            "pi": r"\\pi",
            "sigma": r"\\sigma",
            "theta": r"\\theta",
            "infinity": r"\\infty",
            "sum": r"\\sum",
            "int": r"\\int",
            "lim": r"\\lim"
        }
        
        for ascii_sym, latex_sym in ascii_to_latex.items():
            result = result.replace(ascii_sym, latex_sym)
        
        return result
    
    async def _latex_to_ascii(self, latex_expr: str) -> str:
        """Convert LaTeX to ASCII math"""
        result = latex_expr
        
        latex_to_ascii = {
            r"\\geq": ">=",
            r"\\leq": "<=",
            r"\\neq": "!=",
            r"\\rightarrow": "->",
            r"\\leftrightarrow": "<->",
            r"\\alpha": "alpha",
            r"\\beta": "beta", 
            r"\\gamma": "gamma",
            r"\\delta": "delta",
            r"\\epsilon": "epsilon",
            r"\\pi": "pi",
            r"\\sigma": "sigma",
            r"\\theta": "theta",
            r"\\infty": "infinity",
            r"\\sum": "sum",
            r"\\int": "int",
            r"\\lim": "lim"
        }
        
        for latex_sym, ascii_sym in latex_to_ascii.items():
            result = result.replace(latex_sym, ascii_sym)
        
        # Clean up remaining LaTeX syntax
        result = re.sub(r'\\[a-zA-Z]+', '', result)
        result = re.sub(r'[{}$]', '', result)
        
        return result

class MathematicalProofTranslationSystem:
    """Main system for mathematical proof translation"""
    
    def __init__(self):
        self.expression_parser = MathExpressionParser()
        self.proof_parser = ProofParser()
        self.notation_translator = MathNotationTranslator()
        
    async def translate_mathematical_proof(self, proof_text: str,
                                         source_notation: MathNotation,
                                         target_notation: MathNotation) -> TranslationResult:
        """Translate mathematical proof between notation systems"""
        start_time = datetime.now()
        
        try:
            # Parse the original proof
            proof_structure = await self.proof_parser.parse_proof(proof_text, source_notation)
            
            # Translate the proof text
            translated_proof = await self._translate_proof_text(
                proof_text, source_notation, target_notation
            )
            
            # Calculate confidence
            confidence = await self._calculate_translation_confidence(
                source_notation, target_notation, proof_structure
            )
            
            # Generate notes and warnings
            translation_notes = await self._generate_translation_notes(
                source_notation, target_notation, proof_structure
            )
            warnings = await self._generate_warnings(proof_structure, target_notation)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return TranslationResult(
                source_notation=source_notation,
                target_notation=target_notation,
                original_proof=proof_text,
                translated_proof=translated_proof,
                confidence=confidence,
                processing_time=processing_time,
                proof_structure=proof_structure,
                translation_notes=translation_notes,
                warnings=warnings,
                metadata={
                    "theorem_field": proof_structure.field.value,
                    "proof_techniques": [t.value for t in proof_structure.techniques_used],
                    "difficulty_level": proof_structure.difficulty,
                    "proof_steps": len(proof_structure.steps),
                    "completeness_score": proof_structure.completeness,
                    "rigor_score": proof_structure.rigor
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return TranslationResult(
                source_notation=source_notation,
                target_notation=target_notation,
                original_proof=proof_text,
                translated_proof=f"Translation error: {str(e)}",
                confidence=0.0,
                processing_time=processing_time,
                translation_notes=[f"Error: {str(e)}"],
                warnings=["Failed to translate mathematical proof"]
            )
    
    async def _translate_proof_text(self, proof_text: str,
                                  source_notation: MathNotation,
                                  target_notation: MathNotation) -> str:
        """Translate the proof text between notations"""
        lines = proof_text.split('\n')
        translated_lines = []
        
        for line in lines:
            if line.strip():
                # Translate mathematical expressions in the line
                translated_line = await self.notation_translator.translate_notation(
                    line, source_notation, target_notation
                )
                translated_lines.append(translated_line)
            else:
                translated_lines.append(line)
        
        return '\n'.join(translated_lines)
    
    async def _calculate_translation_confidence(self, source_notation: MathNotation,
                                              target_notation: MathNotation,
                                              proof_structure: MathematicalProof) -> float:
        """Calculate confidence in the translation"""
        base_confidence = 0.8
        
        # Adjust based on notation compatibility
        compatibility_matrix = {
            (MathNotation.LATEX, MathNotation.UNICODE_MATH): 0.95,
            (MathNotation.LATEX, MathNotation.NATURAL_LANGUAGE): 0.85,
            (MathNotation.ASCII_MATH, MathNotation.LATEX): 0.9,
            (MathNotation.NATURAL_LANGUAGE, MathNotation.LATEX): 0.7
        }
        
        notation_pair = (source_notation, target_notation)
        if notation_pair in compatibility_matrix:
            base_confidence = compatibility_matrix[notation_pair]
        
        # Adjust based on proof complexity
        complexity_factor = {
            "beginner": 1.0,
            "intermediate": 0.95,
            "advanced": 0.9,
            "expert": 0.8
        }
        
        difficulty_adjustment = complexity_factor.get(proof_structure.difficulty, 0.8)
        
        # Adjust based on proof structure completeness
        structure_adjustment = proof_structure.completeness * 0.1
        
        final_confidence = base_confidence * difficulty_adjustment + structure_adjustment
        
        return min(final_confidence, 1.0)
    
    async def _generate_translation_notes(self, source_notation: MathNotation,
                                        target_notation: MathNotation,
                                        proof_structure: MathematicalProof) -> List[str]:
        """Generate notes about the translation"""
        notes = []
        
        # Proof structure information
        notes.append(f"Proof contains {len(proof_structure.steps)} steps")
        notes.append(f"Mathematical field: {proof_structure.field.value}")
        notes.append(f"Difficulty level: {proof_structure.difficulty}")
        notes.append(f"Completeness score: {proof_structure.completeness:.2f}")
        
        # Techniques used
        if proof_structure.techniques_used:
            techniques = [t.value for t in proof_structure.techniques_used]
            notes.append(f"Proof techniques: {', '.join(techniques)}")
        
        # Notation-specific notes
        if target_notation == MathNotation.NATURAL_LANGUAGE:
            notes.append("Translated to natural language for readability")
            notes.append("Some mathematical precision may be lost in translation")
        elif target_notation == MathNotation.LATEX:
            notes.append("Translated to LaTeX for formal presentation")
            notes.append("Mathematical symbols rendered properly")
        elif target_notation == MathNotation.FORMAL_LOGIC:
            notes.append("Translated to formal logical notation")
            notes.append("Requires understanding of logical syntax")
        
        return notes
    
    async def _generate_warnings(self, proof_structure: MathematicalProof,
                               target_notation: MathNotation) -> List[str]:
        """Generate warnings about potential translation issues"""
        warnings = []
        
        # Completeness warnings
        if proof_structure.completeness < 0.7:
            warnings.append("Proof may be incomplete or lack sufficient detail")
        
        # Rigor warnings
        if proof_structure.rigor < 0.6:
            warnings.append("Proof may lack mathematical rigor")
        
        # Complex technique warnings
        advanced_techniques = {
            ProofTechnique.PROOF_BY_CONTRADICTION,
            ProofTechnique.PROOF_BY_INDUCTION,
            ProofTechnique.PROOF_BY_INFINITE_DESCENT
        }
        
        if proof_structure.techniques_used & advanced_techniques:
            if target_notation == MathNotation.NATURAL_LANGUAGE:
                warnings.append("Advanced proof techniques may lose precision in natural language")
        
        # Field-specific warnings
        if proof_structure.field == MathField.TOPOLOGY and target_notation == MathNotation.ASCII_MATH:
            warnings.append("Topological concepts may not translate well to ASCII notation")
        
        return warnings
    
    async def batch_translate_proofs(self, proofs: List[Tuple[str, MathNotation]],
                                   target_notation: MathNotation) -> List[TranslationResult]:
        """Translate multiple proofs in batch"""
        tasks = [
            self.translate_mathematical_proof(proof, source_notation, target_notation)
            for proof, source_notation in proofs
        ]
        
        return await asyncio.gather(*tasks)

# Example usage
async def main():
    """Example usage of mathematical proof translation system"""
    
    # Initialize the system
    translator = MathematicalProofTranslationSystem()
    
    print("Mathematical Proof Translation System Demo")
    print("=" * 50)
    
    # Example 1: LaTeX proof to natural language
    latex_proof = r"""
    Theorem: For all real numbers x, if x > 0, then x^2 > 0.
    
    Proof:
    Let x \in \mathbb{R} such that x > 0.
    Since x > 0, we have x \cdot x > 0 \cdot x = 0.
    Therefore x^2 > 0.
    QED.
    """
    
    print("Original LaTeX proof:")
    print(latex_proof)
    print("\n" + "=" * 30)
    
    result1 = await translator.translate_mathematical_proof(
        proof_text=latex_proof,
        source_notation=MathNotation.LATEX,
        target_notation=MathNotation.NATURAL_LANGUAGE
    )
    
    print("Translated to natural language:")
    print(result1.translated_proof)
    print(f"Confidence: {result1.confidence:.3f}")
    print(f"Processing time: {result1.processing_time:.2f}s")
    
    # Example 2: Natural language proof to LaTeX
    print("\n" + "=" * 50)
    natural_proof = """
    Theorem: The sum of two even integers is even.
    
    Proof:
    Let m and n be even integers.
    Then there exist integers k and j such that m = 2k and n = 2j.
    The sum m + n = 2k + 2j = 2(k + j).
    Since k + j is an integer, m + n is even.
    Therefore, the sum of two even integers is even.
    """
    
    print("Natural language proof:")
    print(natural_proof)
    
    result2 = await translator.translate_mathematical_proof(
        proof_text=natural_proof,
        source_notation=MathNotation.NATURAL_LANGUAGE,
        target_notation=MathNotation.LATEX
    )
    
    print("\nTranslated to LaTeX:")
    print(result2.translated_proof)
    print(f"Confidence: {result2.confidence:.3f}")
    
    # Show proof analysis
    if result2.proof_structure:
        print(f"\nProof Analysis:")
        print(f"Field: {result2.proof_structure.field.value}")
        print(f"Difficulty: {result2.proof_structure.difficulty}")
        print(f"Steps: {len(result2.proof_structure.steps)}")
        print(f"Techniques: {[t.value for t in result2.proof_structure.techniques_used]}")
    
    # Show translation notes
    if result2.translation_notes:
        print("\nTranslation Notes:")
        for note in result2.translation_notes[:3]:
            print(f"  📝 {note}")
    
    if result2.warnings:
        print("\nWarnings:")
        for warning in result2.warnings:
            print(f"  ⚠️  {warning}")

if __name__ == "__main__":
    asyncio.run(main())