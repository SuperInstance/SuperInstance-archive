"""
Puzzle and Riddle Generator

Creates various types of puzzles, riddles, and brain teasers for D&D sessions
with appropriate difficulty scaling and solution verification.
"""

import random
import math
from typing import List, Dict, Any, Optional, Tuple

from ..models.encounter import Puzzle
from ..models.base import SkillCheck, SkillType, DifficultyLevel
from ..config import PUZZLE_CONFIG
from .base_generator import BaseGenerator


class PuzzleGenerator(BaseGenerator):
    """Generates puzzles and riddles of various types"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.riddle_database = self._load_riddle_database()
        self.logic_patterns = self._load_logic_patterns()
        self.puzzle_themes = self._load_puzzle_themes()
    
    def _load_riddle_database(self) -> Dict[str, List[Dict[str, str]]]:
        """Load database of riddles by difficulty"""
        return {
            "simple": [
                {
                    "question": "I have keys but no locks. I have space but no room. You can enter, but you can't go outside. What am I?",
                    "answer": "keyboard",
                    "hints": ["I help you type", "I'm found with computers", "Letters are arranged on me"],
                    "category": "object"
                },
                {
                    "question": "The more you take, the more you leave behind. What am I?",
                    "answer": "footsteps",
                    "hints": ["Think about walking", "They're behind you", "You make them as you move"],
                    "category": "action"
                },
                {
                    "question": "What has hands but cannot clap?",
                    "answer": "clock",
                    "hints": ["It tells time", "Found on walls", "Has numbers"],
                    "category": "object"
                },
                {
                    "question": "I'm tall when I'm young, short when I'm old. What am I?",
                    "answer": "candle",
                    "hints": ["I give light", "I burn", "I melt as I'm used"],
                    "category": "object"
                }
            ],
            "moderate": [
                {
                    "question": "Born in battle, I grow in strife. I'm sharpened by conflict, dulled by peace. What am I?",
                    "answer": "courage",
                    "hints": ["I'm not physical", "Heroes possess me", "I grow through adversity"],
                    "category": "concept"
                },
                {
                    "question": "I speak without voice, remember without mind, and my words can kill or heal. What am I?",
                    "answer": "book",
                    "hints": ["I contain words", "I preserve knowledge", "I can be dangerous"],
                    "category": "object"
                },
                {
                    "question": "The first half is a container, the second half is hot. Together we help you see in the dark. What are we?",
                    "answer": "lantern",
                    "hints": ["Lan + tern", "I provide light", "I have fuel inside"],
                    "category": "wordplay"
                }
            ],
            "complex": [
                {
                    "question": "Three gods A, B, and C are called True, False, and Random in some order. True always speaks truly, False always lies, and Random answers randomly. You may ask three yes-no questions to determine which is which. What questions do you ask?",
                    "answer": "complex_logic",
                    "hints": ["Ask about identities indirectly", "Use logical implications", "Consider what each god would say"],
                    "category": "logic"
                },
                {
                    "question": "I am the beginning of sorrow and sadness. I am the end of sickness and the start of sunshine. I am in the center of speech but not in speaking. What am I?",
                    "answer": "letter_s",
                    "hints": ["I'm a letter", "Look at the first/last letters", "I appear in specific positions"],
                    "category": "wordplay"
                }
            ]
        }
    
    def _load_logic_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load logical puzzle patterns"""
        return {
            "sequence": {
                "patterns": [
                    {"sequence": [1, 1, 2, 3, 5, 8], "rule": "fibonacci", "next": 13},
                    {"sequence": [2, 4, 8, 16, 32], "rule": "powers_of_2", "next": 64},
                    {"sequence": [1, 4, 9, 16, 25], "rule": "perfect_squares", "next": 36},
                    {"sequence": [1, 3, 6, 10, 15], "rule": "triangular_numbers", "next": 21},
                    {"sequence": [2, 3, 5, 7, 11], "rule": "prime_numbers", "next": 13}
                ]
            },
            "grid_logic": {
                "types": [
                    {"name": "sudoku", "size": 9, "rule": "numbers_1_to_9"},
                    {"name": "magic_square", "size": 3, "rule": "all_sums_equal"},
                    {"name": "latin_square", "size": 4, "rule": "each_symbol_once"}
                ]
            },
            "weighing_puzzles": [
                {
                    "setup": "12 coins, one is different weight",
                    "tools": "balance scale",
                    "weighings": 3,
                    "goal": "find_odd_coin"
                },
                {
                    "setup": "9 coins, one is lighter",
                    "tools": "balance scale", 
                    "weighings": 2,
                    "goal": "find_light_coin"
                }
            ]
        }
    
    def _load_puzzle_themes(self) -> Dict[str, Dict[str, Any]]:
        """Load themed puzzle elements"""
        return {
            "dungeon": {
                "elements": ["ancient runes", "pressure plates", "rotating stones", "gem slots"],
                "mechanisms": ["door locks", "trap triggers", "hidden passages", "magical seals"],
                "themes": ["dwarven engineering", "ancient magic", "divine trials", "elemental powers"]
            },
            "magical": {
                "elements": ["crystals", "spell components", "magical circles", "enchanted objects"],
                "mechanisms": ["mana flows", "elemental alignment", "spell combinations", "arcane formulas"],
                "themes": ["wizard's test", "magical academy", "planar convergence", "time magic"]
            },
            "mechanical": {
                "elements": ["gears", "levers", "pulleys", "counterweights"],
                "mechanisms": ["clockwork", "hydraulics", "steam power", "precision timing"],
                "themes": ["inventor's workshop", "gnomish contraption", "ancient technology", "siege engines"]
            },
            "nature": {
                "elements": ["growing plants", "flowing water", "changing seasons", "animal behaviors"],
                "mechanisms": ["natural cycles", "ecosystem balance", "druidic magic", "primal forces"],
                "themes": ["druid's grove", "fey crossing", "world tree", "elemental shrine"]
            }
        }
    
    async def generate_puzzle(self, puzzle_type: str = "riddle", 
                            complexity: str = "moderate",
                            theme: str = "dungeon",
                            party_level: int = 5) -> Puzzle:
        """Generate a puzzle of specified type and complexity"""
        
        if puzzle_type == "riddle":
            return await self._generate_riddle(complexity, party_level)
        elif puzzle_type == "logic":
            return await self._generate_logic_puzzle(complexity, party_level)
        elif puzzle_type == "pattern":
            return await self._generate_pattern_puzzle(complexity, party_level)
        elif puzzle_type == "mechanical":
            return await self._generate_mechanical_puzzle(complexity, theme, party_level)
        elif puzzle_type == "mathematical":
            return await self._generate_math_puzzle(complexity, party_level)
        elif puzzle_type == "wordplay":
            return await self._generate_wordplay_puzzle(complexity, party_level)
        else:
            # Default to riddle
            return await self._generate_riddle(complexity, party_level)
    
    async def _generate_riddle(self, complexity: str, party_level: int) -> Puzzle:
        """Generate a riddle puzzle"""
        riddles = self.riddle_database.get(complexity, self.riddle_database["moderate"])
        riddle_data = self.rng.choice(riddles)
        
        puzzle = Puzzle(
            name=f"The {riddle_data['category'].title()} Riddle",
            description=f"A {complexity} riddle that challenges the mind",
            puzzle_type="riddle",
            complexity=complexity,
            solution=riddle_data["answer"],
            read_aloud_text=f"You see ancient runes that, when touched, speak aloud: '{riddle_data['question']}'"
        )
        
        puzzle.clues = riddle_data.get("hints", [])
        puzzle.hint_system = self._create_progressive_hints(riddle_data["hints"])
        
        # Set failure consequences
        if complexity == "simple":
            puzzle.failure_consequences = ["Minor magical backlash", "Door remains locked"]
        elif complexity == "moderate":
            puzzle.failure_consequences = ["Moderate damage to party", "Alarm is triggered"]
        else:
            puzzle.failure_consequences = ["Significant damage", "Summoned guardian appears"]
        
        # Set skill checks for alternative solutions
        puzzle.skill_checks = [
            SkillCheck(
                skill=SkillType.INVESTIGATION,
                dc=self._calculate_dc(complexity, party_level),
                description="Study the riddle for hidden clues"
            ),
            SkillCheck(
                skill=SkillType.HISTORY,
                dc=self._calculate_dc(complexity, party_level) - 2,
                description="Recall knowledge about similar riddles"
            )
        ]
        
        return puzzle
    
    async def _generate_logic_puzzle(self, complexity: str, party_level: int) -> Puzzle:
        """Generate a logic-based puzzle"""
        if complexity == "simple":
            return await self._generate_sequence_puzzle(party_level)
        elif complexity == "moderate":
            return await self._generate_grid_puzzle(party_level)
        else:
            return await self._generate_complex_logic_puzzle(party_level)
    
    async def _generate_sequence_puzzle(self, party_level: int) -> Puzzle:
        """Generate a number sequence puzzle"""
        pattern_data = self.rng.choice(self.logic_patterns["sequence"]["patterns"])
        
        puzzle = Puzzle(
            name="The Sequence Chamber",
            description="Ancient stones display a sequence of numbers",
            puzzle_type="logic",
            complexity="simple",
            solution=str(pattern_data["next"])
        )
        
        sequence_str = ", ".join(map(str, pattern_data["sequence"]))
        puzzle.read_aloud_text = f"Glowing numbers appear in sequence: {sequence_str}, ?"
        
        puzzle.clues = [
            f"The pattern follows the rule of {pattern_data['rule'].replace('_', ' ')}",
            "Each number relates to the previous ones in a specific way",
            "Mathematical progression is the key"
        ]
        
        puzzle.skill_checks = [
            SkillCheck(
                skill=SkillType.INVESTIGATION,
                dc=12 + party_level // 2,
                description="Analyze the mathematical pattern"
            )
        ]
        
        return puzzle
    
    async def _generate_grid_puzzle(self, party_level: int) -> Puzzle:
        """Generate a grid-based logic puzzle"""
        grid_type = self.rng.choice(self.logic_patterns["grid_logic"]["types"])
        
        puzzle = Puzzle(
            name=f"The {grid_type['name'].title()} Lock",
            description=f"A magical {grid_type['size']}x{grid_type['size']} grid puzzle",
            puzzle_type="logic",
            complexity="moderate"
        )
        
        if grid_type["name"] == "magic_square":
            # Generate a 3x3 magic square puzzle
            target_sum = 15
            puzzle.solution = "magic_square_solution"
            puzzle.read_aloud_text = f"A {grid_type['size']}x{grid_type['size']} grid where all rows, columns, and diagonals must sum to {target_sum}"
            
            puzzle.clues = [
                f"All rows must sum to {target_sum}",
                f"All columns must sum to {target_sum}",
                f"Both diagonals must sum to {target_sum}",
                "Use each number 1-9 exactly once"
            ]
        
        puzzle.skill_checks = [
            SkillCheck(
                skill=SkillType.INVESTIGATION,
                dc=14 + party_level // 2,
                description="Analyze the grid pattern requirements"
            ),
            SkillCheck(
                skill=SkillType.ARCANA,
                dc=16 + party_level // 2,
                description="Understand the magical mathematics"
            )
        ]
        
        return puzzle
    
    async def _generate_pattern_puzzle(self, complexity: str, party_level: int) -> Puzzle:
        """Generate a visual/spatial pattern puzzle"""
        pattern_types = [
            {"name": "symbol_rotation", "description": "Symbols rotate in a specific pattern"},
            {"name": "color_sequence", "description": "Colors follow a repeating sequence"},
            {"name": "shape_transformation", "description": "Shapes transform according to rules"},
            {"name": "mirror_symmetry", "description": "Pattern follows mirror symmetry rules"}
        ]
        
        pattern = self.rng.choice(pattern_types)
        
        puzzle = Puzzle(
            name=f"The {pattern['name'].replace('_', ' ').title()} Puzzle",
            description=f"A visual puzzle involving {pattern['description'].lower()}",
            puzzle_type="pattern",
            complexity=complexity
        )
        
        if pattern["name"] == "symbol_rotation":
            puzzle.solution = "clockwise_90_degrees"
            puzzle.read_aloud_text = "Four panels show the same symbol rotated differently. The fifth panel is empty."
            puzzle.clues = [
                "Each symbol rotates from the previous",
                "The rotation is consistent",
                "Follow the established pattern"
            ]
        
        puzzle.skill_checks = [
            SkillCheck(
                skill=SkillType.PERCEPTION,
                dc=self._calculate_dc(complexity, party_level),
                description="Notice the visual pattern"
            ),
            SkillCheck(
                skill=SkillType.INVESTIGATION,
                dc=self._calculate_dc(complexity, party_level) - 2,
                description="Analyze the pattern systematically"
            )
        ]
        
        return puzzle
    
    async def _generate_mechanical_puzzle(self, complexity: str, theme: str, 
                                        party_level: int) -> Puzzle:
        """Generate a mechanical puzzle"""
        theme_data = self.puzzle_themes.get(theme, self.puzzle_themes["mechanical"])
        elements = theme_data["elements"]
        mechanisms = theme_data["mechanisms"]
        
        puzzle = Puzzle(
            name=f"The {self.rng.choice(elements).title()} Mechanism",
            description=f"A complex {theme} contraption blocks your path",
            puzzle_type="mechanical",
            complexity=complexity
        )
        
        mechanism = self.rng.choice(mechanisms)
        element = self.rng.choice(elements)
        
        puzzle.read_aloud_text = f"Before you stands an intricate {mechanism} featuring {element}. "
        
        if complexity == "simple":
            puzzle.solution = "align_symbols"
            puzzle.read_aloud_text += "Three symbols must be aligned correctly."
            puzzle.clues = [
                "The symbols represent elemental forces",
                "Balance is key to harmony",
                "Fire opposes ice, earth opposes air"
            ]
        elif complexity == "moderate":
            puzzle.solution = "sequence_activation"
            puzzle.read_aloud_text += "Multiple components must be activated in the right sequence."
            puzzle.clues = [
                "The sequence follows a logical order",
                "Each step prepares for the next",
                "Start with the foundation element"
            ]
        else:
            puzzle.solution = "complex_calibration"
            puzzle.read_aloud_text += "Precise calibration of multiple interconnected systems is required."
            puzzle.clues = [
                "All systems must work in harmony",
                "Small adjustments have large effects",
                "The master control coordinates everything"
            ]
        
        puzzle.tools_needed = ["thieves' tools", "mechanical knowledge", "patience"]
        
        puzzle.skill_checks = [
            SkillCheck(
                skill=SkillType.INVESTIGATION,
                dc=self._calculate_dc(complexity, party_level),
                description="Understand how the mechanism works"
            ),
            SkillCheck(
                skill=SkillType.SLEIGHT_OF_HAND,
                dc=self._calculate_dc(complexity, party_level),
                description="Manipulate the delicate components"
            )
        ]
        
        return puzzle
    
    async def _generate_math_puzzle(self, complexity: str, party_level: int) -> Puzzle:
        """Generate a mathematical puzzle"""
        if complexity == "simple":
            # Basic arithmetic
            a, b, c = self.rng.randint(1, 20), self.rng.randint(1, 20), self.rng.randint(1, 20)
            target = a + b + c
            puzzle = Puzzle(
                name="The Sum Stones",
                description="Ancient stones with numbers that must equal a target sum",
                puzzle_type="mathematical",
                complexity=complexity,
                solution=str(target)
            )
            puzzle.read_aloud_text = f"Three stones bear the numbers {a}, {b}, and {c}. The door requires their sum."
            
        elif complexity == "moderate":
            # Equation solving
            x = self.rng.randint(5, 15)
            a, b = self.rng.randint(2, 5), self.rng.randint(10, 30)
            result = a * x + b
            puzzle = Puzzle(
                name="The Equation Lock",
                description="A magical lock requiring algebraic solution",
                puzzle_type="mathematical",
                complexity=complexity,
                solution=str(x)
            )
            puzzle.read_aloud_text = f"The inscription reads: '{a} times an unknown number plus {b} equals {result}. What is the unknown number?'"
            
        else:
            # Complex mathematical concept
            puzzle = Puzzle(
                name="The Geometric Paradox",
                description="A puzzle involving advanced mathematical concepts",
                puzzle_type="mathematical",
                complexity=complexity,
                solution="golden_ratio"
            )
            puzzle.read_aloud_text = "The chamber's proportions seem to follow a divine mathematical ratio..."
        
        puzzle.skill_checks = [
            SkillCheck(
                skill=SkillType.INVESTIGATION,
                dc=self._calculate_dc(complexity, party_level),
                description="Work through the mathematical problem"
            )
        ]
        
        return puzzle
    
    async def _generate_wordplay_puzzle(self, complexity: str, party_level: int) -> Puzzle:
        """Generate a wordplay-based puzzle"""
        wordplay_types = [
            "anagram", "acrostic", "palindrome", "rhyme_scheme", "word_association"
        ]
        
        wordplay_type = self.rng.choice(wordplay_types)
        
        puzzle = Puzzle(
            name=f"The {wordplay_type.title()} Challenge",
            description=f"A linguistic puzzle involving {wordplay_type.replace('_', ' ')}",
            puzzle_type="wordplay",
            complexity=complexity
        )
        
        if wordplay_type == "anagram":
            original_word = self.rng.choice(["DRAGON", "WIZARD", "CASTLE", "TREASURE", "MAGIC"])
            puzzle.solution = original_word.lower()
            scrambled = ''.join(self.rng.sample(original_word, len(original_word)))
            puzzle.read_aloud_text = f"The letters '{scrambled}' glow on the wall, waiting to be unscrambled."
            puzzle.clues = [
                "Rearrange the letters to form a word",
                "The word relates to your current quest",
                "Think of fantasy themes"
            ]
        
        elif wordplay_type == "acrostic":
            word = "COURAGE"
            puzzle.solution = word.lower()
            puzzle.read_aloud_text = "Seven lines of text, each beginning with a different letter, spell out a virtue."
            puzzle.clues = [
                "Read the first letter of each line",
                "The virtue is needed by all heroes",
                "It helps you face danger"
            ]
        
        puzzle.skill_checks = [
            SkillCheck(
                skill=SkillType.INVESTIGATION,
                dc=self._calculate_dc(complexity, party_level),
                description="Analyze the wordplay pattern"
            )
        ]
        
        return puzzle
    
    async def _generate_complex_logic_puzzle(self, party_level: int) -> Puzzle:
        """Generate a complex logic puzzle"""
        puzzle = Puzzle(
            name="The Truthteller's Dilemma",
            description="A complex logic puzzle involving multiple statements and deductions",
            puzzle_type="logic",
            complexity="complex"
        )
        
        # Classic logic puzzle setup
        puzzle.read_aloud_text = """Three guardians stand before three doors. 
        One always tells the truth, one always lies, and one alternates between truth and lies.
        Each knows which door leads to treasure, which to danger, and which to nothing.
        You may ask each guardian one yes-or-no question."""
        
        puzzle.solution = "ask_about_others"
        puzzle.clues = [
            "Consider what each type of guardian would say about the others",
            "Use indirect questions to identify the liar",
            "The alternating guardian is unpredictable first time",
            "Logical deduction eliminates impossible combinations"
        ]
        
        puzzle.alternative_solutions = [
            "identify_truth_teller_first",
            "use_self_referential_questions",
            "process_of_elimination"
        ]
        
        puzzle.skill_checks = [
            SkillCheck(
                skill=SkillType.INSIGHT,
                dc=18 + party_level // 2,
                description="Understand the logical implications"
            ),
            SkillCheck(
                skill=SkillType.INVESTIGATION,
                dc=20 + party_level // 2,
                description="Work through all logical possibilities"
            )
        ]
        
        return puzzle
    
    def _calculate_dc(self, complexity: str, party_level: int) -> int:
        """Calculate appropriate DC for puzzle skill checks"""
        base_dcs = {
            "simple": 12,
            "moderate": 15,
            "complex": 18,
            "legendary": 22
        }
        
        base_dc = base_dcs.get(complexity, 15)
        level_adjustment = party_level // 4  # +1 every 4 levels
        
        return min(base_dc + level_adjustment, 25)
    
    def _create_progressive_hints(self, hints: List[str]) -> List[str]:
        """Create progressive hint system"""
        if len(hints) <= 3:
            return hints
        
        # Create three levels of hints: subtle, moderate, obvious
        progressive = []
        if len(hints) >= 1:
            progressive.append(f"Subtle hint: {hints[0]}")
        if len(hints) >= 2:
            progressive.append(f"Clearer hint: {hints[1]}")
        if len(hints) >= 3:
            progressive.append(f"Direct hint: {hints[2]}")
        
        return progressive
    
    async def generate_puzzle_room(self, complexity: str, theme: str, 
                                 party_level: int, num_puzzles: int = 1) -> List[Puzzle]:
        """Generate a room with multiple interconnected puzzles"""
        puzzles = []
        
        # Primary puzzle
        main_types = ["riddle", "logic", "mechanical"]
        main_puzzle = await self.generate_puzzle(
            self.rng.choice(main_types), complexity, theme, party_level
        )
        puzzles.append(main_puzzle)
        
        # Additional puzzles if requested
        for i in range(num_puzzles - 1):
            secondary_types = ["pattern", "wordplay", "mathematical"]
            secondary_puzzle = await self.generate_puzzle(
                self.rng.choice(secondary_types), 
                "simple" if complexity == "complex" else complexity,
                theme, 
                party_level
            )
            secondary_puzzle.name = f"Secondary {secondary_puzzle.name}"
            puzzles.append(secondary_puzzle)
        
        # Connect puzzles if multiple
        if len(puzzles) > 1:
            main_puzzle.description += f" However, {num_puzzles - 1} smaller puzzles must be solved first to reveal the main solution."
            for i, puzzle in enumerate(puzzles[1:], 1):
                puzzle.description += f" Solving this reveals part {i} of the main puzzle solution."
        
        return puzzles
    
    async def generate_riddle_contest(self, num_riddles: int = 3, 
                                    escalating_difficulty: bool = True) -> List[Puzzle]:
        """Generate a series of riddles for a contest or challenge"""
        riddles = []
        
        difficulties = ["simple", "moderate", "complex"]
        if not escalating_difficulty:
            difficulties = ["moderate"] * num_riddles
        elif num_riddles <= 3:
            difficulties = difficulties[:num_riddles]
        else:
            # Repeat pattern for longer contests
            difficulties = (difficulties * ((num_riddles // 3) + 1))[:num_riddles]
        
        for i, difficulty in enumerate(difficulties):
            riddle = await self._generate_riddle(difficulty, 5)  # Level 5 baseline
            riddle.name = f"Riddle {i + 1}: {riddle.name}"
            riddles.append(riddle)
        
        return riddles