"""
SwarmDesign - Generative Art Platform
Revolutionary visual creation through multi-swarm intelligence
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import math


class ArtStyle(Enum):
    """Visual art styles"""
    ABSTRACT = "abstract"
    GEOMETRIC = "geometric"
    ORGANIC = "organic"
    MINIMALIST = "minimalist"
    BAROQUE = "baroque"
    SURREAL = "surreal"
    IMPRESSIONIST = "impressionist"
    CYBERPUNK = "cyberpunk"


class ColorPalette(Enum):
    """Color scheme templates"""
    MONOCHROME = "monochrome"
    COMPLEMENTARY = "complementary"
    ANALOGOUS = "analogous"
    TRIADIC = "triadic"
    WARM = "warm"
    COOL = "cool"
    VIBRANT = "vibrant"
    PASTEL = "pastel"


@dataclass
class Color:
    """RGB color representation"""
    r: int  # 0-255
    g: int  # 0-255
    b: int  # 0-255
    a: float = 1.0  # Alpha (transparency)

    def to_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def to_rgb_string(self) -> str:
        return f"rgb({self.r}, {self.g}, {self.b})"


@dataclass
class Shape:
    """Geometric shape representation"""
    shape_type: str  # "circle", "rectangle", "polygon", "line", "curve"
    position: Tuple[float, float]  # (x, y)
    size: Tuple[float, float]  # (width, height)
    color: Color
    rotation: float = 0.0  # degrees
    opacity: float = 1.0
    layer: int = 0


@dataclass
class ArtworkComposition:
    """Complete artwork representation"""
    shapes: List[Shape]
    canvas_size: Tuple[int, int]
    background_color: Color
    style: ArtStyle
    color_palette: List[Color]
    complexity_score: float
    harmony_score: float


@dataclass
class DesignConstraints:
    """User-specified design constraints"""
    style_preference: Optional[ArtStyle] = None
    color_scheme: Optional[ColorPalette] = None
    complexity: float = 0.5  # 0-1
    symmetry: float = 0.5  # 0-1
    organic_vs_geometric: float = 0.5  # 0=geometric, 1=organic
    canvas_size: Tuple[int, int] = (1920, 1080)


class StyleSwarmAgent:
    """Agent specializing in artistic style"""

    def __init__(self, agent_id: int, style: ArtStyle):
        self.agent_id = agent_id
        self.style = style
        self.fitness = 0.0

    def apply_style(self, shapes: List[Shape]) -> List[Shape]:
        """Apply style transformations to shapes"""

        styled_shapes = []

        for shape in shapes:
            styled = Shape(
                shape_type=shape.shape_type,
                position=shape.position,
                size=shape.size,
                color=shape.color,
                rotation=shape.rotation,
                opacity=shape.opacity,
                layer=shape.layer
            )

            # Style-specific transformations
            if self.style == ArtStyle.ABSTRACT:
                # Irregular shapes, bold colors
                styled.rotation = random.uniform(0, 360)
                styled.opacity = random.uniform(0.6, 1.0)

            elif self.style == ArtStyle.GEOMETRIC:
                # Clean lines, precise angles
                styled.rotation = round(styled.rotation / 45) * 45
                styled.opacity = 1.0

            elif self.style == ArtStyle.ORGANIC:
                # Flowing, natural forms
                styled.rotation += random.gauss(0, 15)
                styled.size = (
                    styled.size[0] * random.uniform(0.9, 1.1),
                    styled.size[1] * random.uniform(0.9, 1.1)
                )

            elif self.style == ArtStyle.MINIMALIST:
                # Simple, sparse composition
                styled.opacity = 1.0
                styled.color = Color(0, 0, 0) if random.random() > 0.2 else styled.color

            styled_shapes.append(styled)

        return styled_shapes

    def evaluate_style_consistency(self, shapes: List[Shape]) -> float:
        """Evaluate how well shapes match style"""

        consistency_score = 1.0

        # Check rotation consistency
        rotations = [s.rotation for s in shapes]

        if self.style == ArtStyle.GEOMETRIC:
            # Prefer 45-degree increments
            aligned = sum(1 for r in rotations if r % 45 == 0)
            consistency_score *= aligned / len(rotations)

        elif self.style == ArtStyle.ORGANIC:
            # Prefer varied rotations
            rotation_variance = np.var(rotations) if len(rotations) > 1 else 0
            consistency_score *= min(1.0, rotation_variance / 1000)

        self.fitness = consistency_score
        return consistency_score


class ColorSwarmAgent:
    """Agent exploring color combinations"""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.palette: List[Color] = []
        self.harmony_score = 0.0

    def generate_palette(self, scheme: ColorPalette, size: int = 5) -> List[Color]:
        """Generate color palette based on scheme"""

        palette = []

        if scheme == ColorPalette.MONOCHROME:
            # Shades of single hue
            base_hue = random.randint(0, 255)
            for i in range(size):
                lightness = int(50 + (i / size) * 150)
                palette.append(Color(base_hue, base_hue, base_hue))

        elif scheme == ColorPalette.COMPLEMENTARY:
            # Opposite colors on color wheel
            hue1 = random.randint(0, 255)
            hue2 = (hue1 + 128) % 256
            palette.append(Color(hue1, 100, 100))
            palette.append(Color(hue2, 100, 100))
            # Add neutrals
            for _ in range(size - 2):
                gray = random.randint(100, 200)
                palette.append(Color(gray, gray, gray))

        elif scheme == ColorPalette.TRIADIC:
            # Three evenly spaced colors
            base = random.randint(0, 255)
            for i in range(3):
                hue = (base + i * 85) % 256
                palette.append(Color(hue, 150, 150))
            # Fill remaining
            for _ in range(size - 3):
                palette.append(Color(200, 200, 200))

        elif scheme == ColorPalette.WARM:
            # Reds, oranges, yellows
            warm_hues = [(255, 0, 0), (255, 127, 0), (255, 255, 0)]
            for _ in range(size):
                base = random.choice(warm_hues)
                variation = random.randint(-30, 30)
                palette.append(Color(
                    max(0, min(255, base[0] + variation)),
                    max(0, min(255, base[1] + variation)),
                    max(0, min(255, base[2] + variation))
                ))

        elif scheme == ColorPalette.COOL:
            # Blues, greens, purples
            cool_hues = [(0, 0, 255), (0, 255, 0), (128, 0, 255)]
            for _ in range(size):
                base = random.choice(cool_hues)
                variation = random.randint(-30, 30)
                palette.append(Color(
                    max(0, min(255, base[0] + variation)),
                    max(0, min(255, base[1] + variation)),
                    max(0, min(255, base[2] + variation))
                ))

        elif scheme == ColorPalette.VIBRANT:
            # Saturated colors
            for _ in range(size):
                palette.append(Color(
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255)
                ))

        elif scheme == ColorPalette.PASTEL:
            # Light, desaturated colors
            for _ in range(size):
                palette.append(Color(
                    random.randint(180, 255),
                    random.randint(180, 255),
                    random.randint(180, 255)
                ))

        else:  # ANALOGOUS or default
            # Adjacent colors on wheel
            base = random.randint(0, 255)
            for i in range(size):
                hue = (base + i * 30) % 256
                palette.append(Color(hue, 150, 150))

        self.palette = palette
        return palette

    def evaluate_harmony(self, palette: List[Color]) -> float:
        """Evaluate color harmony"""

        if len(palette) < 2:
            return 0.5

        # Calculate color distances
        distances = []
        for i in range(len(palette)):
            for j in range(i + 1, len(palette)):
                c1, c2 = palette[i], palette[j]
                dist = math.sqrt(
                    (c1.r - c2.r)**2 +
                    (c1.g - c2.g)**2 +
                    (c1.b - c2.b)**2
                )
                distances.append(dist)

        # Good harmony has moderate color distances
        avg_distance = sum(distances) / len(distances)
        ideal_distance = 150  # Moderate contrast

        harmony = 1.0 - abs(avg_distance - ideal_distance) / 255

        self.harmony_score = max(0, min(1, harmony))
        return self.harmony_score


class CompositionSwarmAgent:
    """Agent arranging visual elements"""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.composition: List[Shape] = []
        self.balance_score = 0.0

    def generate_composition(self,
                           canvas_size: Tuple[int, int],
                           num_shapes: int,
                           palette: List[Color],
                           constraints: DesignConstraints) -> List[Shape]:
        """Generate composition of shapes"""

        shapes = []
        width, height = canvas_size

        for i in range(num_shapes):
            # Determine shape type based on organic vs geometric preference
            if constraints.organic_vs_geometric > 0.5:
                shape_type = random.choice(["circle", "curve", "blob"])
            else:
                shape_type = random.choice(["rectangle", "polygon", "line"])

            # Position
            if constraints.symmetry > 0.7:
                # Symmetrical placement
                x = width // 2 if i % 2 == 0 else width // 4
            else:
                # Random placement
                x = random.uniform(0, width)

            y = random.uniform(0, height)

            # Size based on complexity
            base_size = 100 if constraints.complexity < 0.5 else 50
            size = (
                random.uniform(base_size * 0.5, base_size * 1.5),
                random.uniform(base_size * 0.5, base_size * 1.5)
            )

            # Color from palette
            color = random.choice(palette) if palette else Color(128, 128, 128)

            shape = Shape(
                shape_type=shape_type,
                position=(x, y),
                size=size,
                color=color,
                rotation=random.uniform(0, 360),
                opacity=random.uniform(0.7, 1.0),
                layer=i
            )

            shapes.append(shape)

        self.composition = shapes
        return shapes

    def evaluate_balance(self, shapes: List[Shape],
                        canvas_size: Tuple[int, int]) -> float:
        """Evaluate visual balance of composition"""

        if not shapes:
            return 0.5

        width, height = canvas_size
        center_x, center_y = width / 2, height / 2

        # Calculate center of mass
        total_weight = 0
        weighted_x = 0
        weighted_y = 0

        for shape in shapes:
            weight = shape.size[0] * shape.size[1] * shape.opacity
            weighted_x += shape.position[0] * weight
            weighted_y += shape.position[1] * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5

        com_x = weighted_x / total_weight
        com_y = weighted_y / total_weight

        # Distance from canvas center
        distance = math.sqrt((com_x - center_x)**2 + (com_y - center_y)**2)
        max_distance = math.sqrt(width**2 + height**2) / 2

        # Good balance is near center
        balance = 1.0 - (distance / max_distance)

        self.balance_score = max(0, min(1, balance))
        return self.balance_score


class GenerativeArtSwarm:
    """Swarm creating generative art"""

    def __init__(self, size: int = 50):
        self.style_agents: List[StyleSwarmAgent] = []
        self.color_agents = [ColorSwarmAgent(i) for i in range(size // 2)]
        self.composition_agents = [CompositionSwarmAgent(i) for i in range(size // 2)]
        self.best_artwork: Optional[ArtworkComposition] = None
        self.best_fitness = 0.0

    async def create_artwork(self,
                            constraints: DesignConstraints,
                            generations: int = 30) -> ArtworkComposition:
        """Create artwork through swarm evolution"""

        print(f"🎨 Generative art swarm creating {constraints.style_preference.value if constraints.style_preference else 'mixed style'} artwork...")

        # Create style agents
        if constraints.style_preference:
            self.style_agents = [
                StyleSwarmAgent(i, constraints.style_preference)
                for i in range(10)
            ]
        else:
            # Diverse style exploration
            styles = list(ArtStyle)
            self.style_agents = [
                StyleSwarmAgent(i, random.choice(styles))
                for i in range(10)
            ]

        for generation in range(generations):
            artworks = []

            # Generate color palettes
            color_palettes = []
            for agent in self.color_agents[:10]:
                scheme = constraints.color_scheme or random.choice(list(ColorPalette))
                palette = agent.generate_palette(scheme)
                agent.evaluate_harmony(palette)
                color_palettes.append((palette, agent.harmony_score))

            # Select best palette
            color_palettes.sort(key=lambda x: x[1], reverse=True)
            best_palette = color_palettes[0][0]

            # Generate compositions
            for comp_agent in self.composition_agents[:10]:
                num_shapes = int(5 + constraints.complexity * 20)

                shapes = comp_agent.generate_composition(
                    constraints.canvas_size,
                    num_shapes,
                    best_palette,
                    constraints
                )

                # Apply style
                style_agent = random.choice(self.style_agents)
                styled_shapes = style_agent.apply_style(shapes)

                # Evaluate
                balance = comp_agent.evaluate_balance(
                    styled_shapes,
                    constraints.canvas_size
                )
                style_consistency = style_agent.evaluate_style_consistency(styled_shapes)

                fitness = (balance + style_consistency + color_palettes[0][1]) / 3

                artwork = ArtworkComposition(
                    shapes=styled_shapes,
                    canvas_size=constraints.canvas_size,
                    background_color=Color(255, 255, 255),
                    style=style_agent.style,
                    color_palette=best_palette,
                    complexity_score=constraints.complexity,
                    harmony_score=fitness
                )

                artworks.append((artwork, fitness))

            # Select best
            artworks.sort(key=lambda x: x[1], reverse=True)
            if artworks[0][1] > self.best_fitness:
                self.best_fitness = artworks[0][1]
                self.best_artwork = artworks[0][0]

            if generation % 10 == 0:
                print(f"  Generation {generation}: fitness = {self.best_fitness:.3f}")

        return self.best_artwork


class Architecture3DSwarm:
    """Swarm designing 3D architecture"""

    def __init__(self, size: int = 30):
        self.size = size

    async def design_structure(self,
                              building_type: str = "modern",
                              constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Design architectural structure"""

        print(f"🏛️ Architecture swarm designing {building_type} structure...")

        if constraints is None:
            constraints = {
                'max_height': 100,
                'footprint': (50, 50),
                'style': building_type
            }

        # Simplified architectural design
        design = {
            'building_type': building_type,
            'dimensions': {
                'width': constraints['footprint'][0],
                'length': constraints['footprint'][1],
                'height': constraints['max_height']
            },
            'floors': constraints['max_height'] // 3,
            'materials': ['concrete', 'glass', 'steel'],
            'features': [
                'Energy-efficient windows',
                'Green roof',
                'Solar panels',
                'Open floor plan'
            ],
            'structural_elements': [
                {'type': 'foundation', 'depth': 10},
                {'type': 'columns', 'count': 16},
                {'type': 'beams', 'material': 'steel'},
                {'type': 'walls', 'material': 'reinforced concrete'}
            ]
        }

        print(f"  ✓ Structure: {design['floors']} floors, {design['dimensions']['height']}m height")

        return design


class FashionPatternSwarm:
    """Swarm generating fashion patterns"""

    def __init__(self, size: int = 25):
        self.size = size

    async def generate_pattern(self,
                              garment_type: str = "dress",
                              style: str = "modern") -> Dict[str, Any]:
        """Generate fashion pattern"""

        print(f"👗 Fashion swarm generating {style} {garment_type} pattern...")

        pattern = {
            'garment_type': garment_type,
            'style': style,
            'pattern_pieces': [
                {'name': 'front', 'cuts': 2},
                {'name': 'back', 'cuts': 1},
                {'name': 'sleeve', 'cuts': 2},
                {'name': 'collar', 'cuts': 1}
            ],
            'measurements': {
                'chest': 90,
                'waist': 70,
                'hip': 95,
                'length': 100
            },
            'fabric_suggestions': ['silk', 'cotton', 'linen'],
            'color_recommendations': ['navy', 'burgundy', 'forest green'],
            'construction_notes': [
                'Use French seams for clean finish',
                'Add interfacing to collar',
                'Include pockets in side seams'
            ]
        }

        print(f"  ✓ Pattern pieces: {len(pattern['pattern_pieces'])}")

        return pattern


class SwarmDesign:
    """
    Main SwarmDesign system coordinating all design swarms
    """

    def __init__(self):
        self.art_swarm = GenerativeArtSwarm(size=50)
        self.architecture_swarm = Architecture3DSwarm(size=30)
        self.fashion_swarm = FashionPatternSwarm(size=25)

        self.design_history: List[Dict[str, Any]] = []

    async def create_visual_art(self,
                               style: Optional[ArtStyle] = None,
                               color_scheme: Optional[ColorPalette] = None,
                               complexity: float = 0.5) -> ArtworkComposition:
        """Create visual artwork"""

        constraints = DesignConstraints(
            style_preference=style,
            color_scheme=color_scheme,
            complexity=complexity,
            canvas_size=(1920, 1080)
        )

        artwork = await self.art_swarm.create_artwork(constraints, generations=30)

        self.design_history.append({
            'type': 'visual_art',
            'artwork': artwork,
            'timestamp': 'now'
        })

        return artwork

    async def design_architecture(self,
                                 building_type: str = "modern") -> Dict[str, Any]:
        """Design architectural structure"""

        design = await self.architecture_swarm.design_structure(building_type)

        self.design_history.append({
            'type': 'architecture',
            'design': design,
            'timestamp': 'now'
        })

        return design

    async def generate_fashion_pattern(self,
                                      garment_type: str = "dress") -> Dict[str, Any]:
        """Generate fashion pattern"""

        pattern = await self.fashion_swarm.generate_pattern(garment_type)

        self.design_history.append({
            'type': 'fashion',
            'pattern': pattern,
            'timestamp': 'now'
        })

        return pattern

    def export_svg(self, artwork: ArtworkComposition, filename: str = "artwork.svg"):
        """Export artwork to SVG format"""

        width, height = artwork.canvas_size

        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" fill="{artwork.background_color.to_hex()}"/>

"""

        for shape in artwork.shapes:
            x, y = shape.position
            w, h = shape.size

            if shape.shape_type == "rectangle":
                svg += f"""  <rect x="{x}" y="{y}" width="{w}" height="{h}"
       fill="{shape.color.to_hex()}"
       opacity="{shape.opacity}"
       transform="rotate({shape.rotation} {x+w/2} {y+h/2})"/>
"""
            elif shape.shape_type == "circle":
                svg += f"""  <circle cx="{x}" cy="{y}" r="{w/2}"
       fill="{shape.color.to_hex()}"
       opacity="{shape.opacity}"/>
"""

        svg += "</svg>"

        with open(filename, 'w') as f:
            f.write(svg)

        print(f"🖼️ SVG exported to {filename}")

    def export_design_json(self, design: Dict[str, Any], filename: str):
        """Export design to JSON"""

        with open(filename, 'w') as f:
            json.dump(design, f, indent=2)

        print(f"💾 Design exported to {filename}")


# Demo usage
async def demo_visual_art():
    """Generate various visual artworks"""

    designer = SwarmDesign()

    print("\n" + "="*60)
    print("SWARMDESIGN - Visual Art Generation Demo")
    print("="*60 + "\n")

    # Abstract art
    artwork1 = await designer.create_visual_art(
        style=ArtStyle.ABSTRACT,
        color_scheme=ColorPalette.VIBRANT,
        complexity=0.8
    )
    designer.export_svg(artwork1, "abstract_art.svg")

    # Minimalist art
    artwork2 = await designer.create_visual_art(
        style=ArtStyle.MINIMALIST,
        color_scheme=ColorPalette.MONOCHROME,
        complexity=0.3
    )
    designer.export_svg(artwork2, "minimalist_art.svg")

    # Geometric art
    artwork3 = await designer.create_visual_art(
        style=ArtStyle.GEOMETRIC,
        color_scheme=ColorPalette.COMPLEMENTARY,
        complexity=0.6
    )
    designer.export_svg(artwork3, "geometric_art.svg")


async def demo_architecture():
    """Generate architectural designs"""

    designer = SwarmDesign()

    print("\n" + "="*60)
    print("SWARMDESIGN - Architecture Generation Demo")
    print("="*60 + "\n")

    # Modern building
    modern = await designer.design_architecture("modern")
    designer.export_design_json(modern, "modern_building.json")

    # Sustainable structure
    sustainable = await designer.design_architecture("sustainable")
    designer.export_design_json(sustainable, "sustainable_building.json")


async def demo_fashion():
    """Generate fashion patterns"""

    designer = SwarmDesign()

    print("\n" + "="*60)
    print("SWARMDESIGN - Fashion Pattern Generation Demo")
    print("="*60 + "\n")

    # Dress pattern
    dress = await designer.generate_fashion_pattern("dress")
    designer.export_design_json(dress, "dress_pattern.json")

    # Jacket pattern
    jacket = await designer.generate_fashion_pattern("jacket")
    designer.export_design_json(jacket, "jacket_pattern.json")


if __name__ == "__main__":
    # Run demos
    asyncio.run(demo_visual_art())
    asyncio.run(demo_architecture())
    asyncio.run(demo_fashion())

    print("\n✨ SwarmDesign demo complete!")
    print("🎨 Check the generated files for design outputs")
