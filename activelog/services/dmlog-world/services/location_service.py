"""
Location description generator service with rich sensory details.
"""

import random
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from sqlalchemy.orm import Session
import logging

from ..models.location import (
    LocationType, Atmosphere, LightLevel, SoundLevel, 
    LocationSchema, LocationDescriptionRequest, LocationDescriptionResponse,
    SensoryDetails, EnvironmentalConditions, LocationFeature,
    DescriptionTemplate, LocationAnalysis
)
from ..models.base import BiomeType, WeatherType, TileType
from ..config import Config

logger = logging.getLogger(__name__)

class LocationDescriptionService:
    def __init__(self):
        self.config = Config()
        self.templates = self._initialize_templates()
        self.sensory_libraries = self._initialize_sensory_libraries()
        self.feature_pools = self._initialize_feature_pools()
        self.atmosphere_effects = self._initialize_atmosphere_effects()
        
    def _initialize_templates(self) -> Dict[LocationType, DescriptionTemplate]:
        """Initialize description templates for different location types."""
        
        templates = {}
        
        # Dungeon room templates
        templates[LocationType.DUNGEON_ROOM] = DescriptionTemplate(
            location_type=LocationType.DUNGEON_ROOM,
            base_templates=[
                "This {adjective} {room_type} {size_desc} with {ceiling_desc}.",
                "The {room_type} {condition_desc} and {lighting_desc}.",
                "You find yourself in {article} {atmosphere_adj} {room_type} that {unique_feature}."
            ],
            sensory_templates={
                "visual": [
                    "{walls_desc}", "{floor_desc}", "{ceiling_desc}", "{lighting_desc}",
                    "Shadows dance across {surface}", "The {feature} catches your eye",
                    "{color} stains mark the {surface}"
                ],
                "auditory": [
                    "{echo_desc}", "The sound of {ambient_sound}",
                    "A faint {sound} echoes from {direction}",
                    "Complete silence pervades the space"
                ],
                "olfactory": [
                    "The air smells of {scent}", "A {intensity} odor of {smell} lingers",
                    "The musty scent of {age_indicator}", "Fresh air suggests {air_source}"
                ],
                "tactile": [
                    "The air feels {temperature} and {humidity}",
                    "Stone surfaces are {texture} to the touch",
                    "A {air_movement} stirs the air"
                ]
            },
            feature_pools={
                "walls": ["rough stone walls", "smooth carved stone", "crumbling brick", "damp stone blocks"],
                "floors": ["uneven flagstones", "polished marble", "dirt and debris", "ancient tiles"],
                "ceilings": ["vaulted ceiling", "low stone ceiling", "collapsed sections", "ornate stonework"],
                "lighting": ["torch brackets", "magical orbs", "shaft of sunlight", "flickering candles"]
            },
            atmosphere_modifiers={
                Atmosphere.ANCIENT: {
                    "adjectives": ["time-worn", "weathered", "crumbling", "forgotten"],
                    "features": ["ancient carvings", "worn inscriptions", "moss-covered stones"]
                },
                Atmosphere.THREATENING: {
                    "adjectives": ["ominous", "foreboding", "menacing", "dark"],
                    "features": ["bloodstains", "claw marks", "broken weapons", "bones"]
                }
            },
            weather_effects={}  # Indoor locations not affected by weather
        )
        
        # Outdoor area templates
        templates[LocationType.OUTDOOR_AREA] = DescriptionTemplate(
            location_type=LocationType.OUTDOOR_AREA,
            base_templates=[
                "The {terrain_type} stretches {direction_desc} under {sky_desc}.",
                "This {biome_desc} area {weather_effect} with {notable_feature}.",
                "You stand in {article} {adjective} {landscape} where {unique_element}."
            ],
            sensory_templates={
                "visual": [
                    "The landscape {terrain_desc}", "{vegetation_desc}",
                    "{sky_desc}", "{horizon_desc}", "{color_palette}"
                ],
                "auditory": [
                    "The sound of {natural_sound}", "{weather_sound}",
                    "{wildlife_sound}", "The {ambient_desc} creates a {mood} atmosphere"
                ],
                "olfactory": [
                    "The air carries the scent of {natural_scent}",
                    "{seasonal_scent}", "{weather_scent}"
                ],
                "tactile": [
                    "The {weather_feel} against your skin",
                    "{ground_texture} underfoot", "{air_quality_desc}"
                ]
            },
            feature_pools={
                "terrain": ["rolling hills", "rocky outcroppings", "dense forest", "open meadow"],
                "vegetation": ["ancient trees", "wildflowers", "thick underbrush", "sparse grass"],
                "water": ["babbling brook", "still pond", "rushing river", "distant waterfall"],
                "landmarks": ["moss-covered boulder", "lightning-struck tree", "stone circle", "weathered statue"]
            },
            atmosphere_modifiers={
                Atmosphere.PEACEFUL: {
                    "adjectives": ["serene", "tranquil", "calm", "idyllic"],
                    "features": ["gentle breeze", "bird songs", "dappled sunlight"]
                },
                Atmosphere.MYSTERIOUS: {
                    "adjectives": ["enigmatic", "otherworldly", "strange", "peculiar"],
                    "features": ["unusual plants", "odd formations", "ethereal mist"]
                }
            },
            weather_effects={
                WeatherType.RAIN: {
                    "visual": ["rain-soaked landscape", "puddles reflecting sky", "mist rising"],
                    "auditory": ["pattering of raindrops", "dripping from leaves"],
                    "olfactory": ["petrichor", "fresh, clean air"]
                }
            }
        )
        
        # Settlement area templates  
        templates[LocationType.SETTLEMENT_AREA] = DescriptionTemplate(
            location_type=LocationType.SETTLEMENT_AREA,
            base_templates=[
                "This {area_type} {activity_desc} with {architectural_desc}.",
                "The {settlement_desc} area {atmosphere_desc} and {population_activity}.",
                "You find yourself in {article} {adjective} part of town where {local_feature}."
            ],
            sensory_templates={
                "visual": [
                    "{building_desc}", "{street_desc}", "{people_desc}",
                    "{shop_signs}", "{architectural_details}"
                ],
                "auditory": [
                    "The sounds of {urban_activity}", "{conversation_buzz}",
                    "{craft_sounds}", "{transport_sounds}"
                ],
                "olfactory": [
                    "The aroma of {food_scents}", "{craft_smells}",
                    "{urban_scents}", "{cooking_smells}"
                ],
                "tactile": [
                    "{pavement_feel}", "{crowd_feeling}",
                    "{temperature_urban}", "{air_quality}"
                ]
            },
            feature_pools={
                "buildings": ["timber-framed houses", "stone shops", "thatched cottages", "brick warehouses"],
                "streets": ["cobblestone roads", "muddy paths", "well-paved streets", "narrow alleys"],
                "people": ["busy merchants", "playing children", "gossiping neighbors", "hurried travelers"],
                "shops": ["baker's shop", "blacksmith forge", "general store", "tavern"]
            },
            atmosphere_modifiers={
                Atmosphere.BUSTLING: {
                    "adjectives": ["lively", "energetic", "crowded", "vibrant"],
                    "features": ["market stalls", "street performers", "heavy foot traffic"]
                }
            },
            weather_effects={
                WeatherType.SNOW: {
                    "visual": ["snow-covered rooftops", "icicles hanging from eaves"],
                    "auditory": ["muffled sounds", "crunching snow underfoot"],
                    "tactile": ["biting cold air", "slippery cobblestones"]
                }
            }
        )
        
        return templates
        
    def _initialize_sensory_libraries(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize libraries of sensory descriptions."""
        
        return {
            "visual": {
                "colors": ["deep crimson", "pale golden", "rich emerald", "dusky purple", "stark white", "charcoal grey"],
                "lighting": ["soft glow", "harsh glare", "flickering light", "deep shadows", "dappled sunlight"],
                "textures": ["rough and weathered", "smooth as silk", "cracked and worn", "polished to a shine"],
                "movement": ["swaying gently", "dancing in the breeze", "perfectly still", "trembling slightly"]
            },
            "auditory": {
                "natural": ["rustling leaves", "chirping birds", "flowing water", "howling wind", "crackling fire"],
                "urban": ["distant conversations", "clattering hooves", "creaking wheels", "ringing bells"],
                "dungeon": ["dripping water", "scurrying rats", "grinding stone", "echoing footsteps"],
                "volume": ["barely audible", "soft and gentle", "clearly heard", "loud and intrusive", "deafeningly loud"]
            },
            "olfactory": {
                "natural": ["fresh rain", "blooming flowers", "pine needles", "rich earth", "crisp mountain air"],
                "urban": ["baking bread", "wood smoke", "leather and metal", "spices and herbs"],
                "dungeon": ["musty air", "stagnant water", "ancient stone", "decay and mold"],
                "intensity": ["faint hint", "subtle aroma", "strong scent", "overwhelming odor"]
            },
            "tactile": {
                "temperature": ["pleasantly warm", "comfortably cool", "bitterly cold", "swelteringly hot"],
                "humidity": ["dry and arid", "comfortably humid", "sticky and muggy", "crisp and dry"],
                "air_movement": ["still air", "gentle breeze", "strong wind", "gusting air"],
                "textures": ["smooth surface", "rough texture", "soft material", "hard as stone"]
            },
            "emotional": {
                "positive": ["sense of peace", "feeling of wonder", "surge of excitement", "warm comfort"],
                "negative": ["unease creeping in", "feeling of dread", "mounting anxiety", "cold fear"],
                "neutral": ["sense of curiosity", "alert awareness", "quiet contemplation"]
            }
        }
    
    def _initialize_feature_pools(self) -> Dict[LocationType, Dict[str, List[LocationFeature]]]:
        """Initialize pools of features for different location types."""
        
        pools = {}
        
        # Dungeon room features
        pools[LocationType.DUNGEON_ROOM] = {
            "furniture": [
                LocationFeature(name="ancient altar", description="A weathered stone altar stained with dark marks", feature_type="religious", interactive=True),
                LocationFeature(name="wooden chest", description="A sturdy iron-bound chest", feature_type="storage", interactive=True),
                LocationFeature(name="stone pedestal", description="A carved pedestal that once held something important", feature_type="display"),
            ],
            "architectural": [
                LocationFeature(name="carved archway", description="An ornate archway with intricate stonework", feature_type="architectural"),
                LocationFeature(name="spiral staircase", description="Stone steps winding upward into darkness", feature_type="architectural", interactive=True),
                LocationFeature(name="wall niche", description="A recessed alcove in the wall", feature_type="architectural", hidden=True),
            ]
        }
        
        # Outdoor area features  
        pools[LocationType.OUTDOOR_AREA] = {
            "natural": [
                LocationFeature(name="ancient oak", description="A massive oak tree with gnarled branches", feature_type="natural"),
                LocationFeature(name="crystal stream", description="Clear water flowing over smooth stones", feature_type="natural", interactive=True),
                LocationFeature(name="moss-covered boulder", description="A large stone covered in soft green moss", feature_type="natural"),
            ],
            "landmarks": [
                LocationFeature(name="standing stone", description="A weathered monolith covered in ancient runes", feature_type="landmark", interactive=True),
                LocationFeature(name="old campsite", description="Remnants of a long-abandoned camp", feature_type="artificial"),
            ]
        }
        
        return pools
    
    def _initialize_atmosphere_effects(self) -> Dict[Atmosphere, Dict[str, Any]]:
        """Initialize atmospheric effects for different moods."""
        
        return {
            Atmosphere.ANCIENT: {
                "descriptors": ["time-worn", "weathered", "forgotten", "lost to ages"],
                "visual_modifiers": ["covered in dust", "partially crumbled", "bearing ancient marks"],
                "scents": ["musty age", "old stone", "forgotten time"],
                "sounds": ["settling stones", "whispers of history"]
            },
            Atmosphere.MYSTERIOUS: {
                "descriptors": ["enigmatic", "puzzling", "otherworldly", "strange"],
                "visual_modifiers": ["shrouded in mist", "oddly shaped", "defying explanation"],
                "scents": ["ethereal fragrance", "unknown spices", "magic in the air"],
                "sounds": ["distant whispers", "unexplained echoes", "supernatural silence"]
            },
            Atmosphere.PEACEFUL: {
                "descriptors": ["serene", "tranquil", "harmonious", "restful"],
                "visual_modifiers": ["bathed in soft light", "perfectly maintained", "inviting"],
                "scents": ["fresh flowers", "clean air", "gentle herbs"],
                "sounds": ["gentle breeze", "distant laughter", "peaceful quiet"]
            }
        }

    async def generate_description(
        self,
        request: LocationDescriptionRequest,
        db_session: Optional[Session] = None
    ) -> LocationDescriptionResponse:
        """Generate a rich location description with sensory details."""
        
        start_time = datetime.utcnow()
        
        try:
            # Set random seed if provided
            if request.seed:
                random.seed(request.seed)
            
            # Generate base description
            location = await self._create_base_location(request)
            
            # Add sensory details if requested
            if request.include_sensory_details:
                location.sensory_details = await self._generate_sensory_details(location, request)
            
            # Add environmental features
            location.features = await self._select_features(location, request)
            
            # Generate atmospheric elements
            await self._apply_atmosphere_effects(location, request)
            
            # Apply weather effects if applicable
            if request.weather and location.location_type == LocationType.OUTDOOR_AREA:
                await self._apply_weather_effects(location, request.weather)
            
            # Adjust for time of day
            await self._apply_time_effects(location, request.time_of_day)
            
            # Calculate generation time
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            return LocationDescriptionResponse(
                success=True,
                location_data=location,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error generating location description: {e}")
            return LocationDescriptionResponse(
                success=False,
                message=f"Failed to generate location description: {str(e)}",
                errors=[str(e)]
            )

    async def _create_base_location(self, request: LocationDescriptionRequest) -> LocationSchema:
        """Create the base location with initial description."""
        
        template = self.templates.get(request.location_type)
        if not template:
            raise ValueError(f"No template found for location type: {request.location_type}")
        
        # Generate name
        name = await self._generate_location_name(request.location_type, request.biome)
        
        # Select base template
        base_template = random.choice(template.base_templates)
        
        # Generate template variables
        template_vars = await self._generate_template_variables(request, template)
        
        # Create descriptions
        short_desc = await self._generate_short_description(base_template, template_vars, request)
        detailed_desc = await self._generate_detailed_description(template, template_vars, request)
        
        # Set environmental conditions
        environment = await self._create_environmental_conditions(request)
        
        return LocationSchema(
            name=name,
            location_type=request.location_type,
            biome=request.biome,
            short_description=short_desc,
            detailed_description=detailed_desc,
            atmosphere=request.atmosphere or Atmosphere.PEACEFUL,
            environment=environment,
            generation_seed=request.seed,
            generation_params={"detail_level": request.detail_level, "style": request.style}
        )

    async def _generate_location_name(self, location_type: LocationType, biome: Optional[BiomeType]) -> str:
        """Generate an appropriate name for the location."""
        
        name_patterns = {
            LocationType.DUNGEON_ROOM: [
                "The {adjective} {room_type}",
                "{descriptor} Chamber", 
                "Room of {concept}",
                "The {ancient} {room_type}"
            ],
            LocationType.OUTDOOR_AREA: [
                "{adjective} {terrain}",
                "The {descriptor} {biome_feature}",
                "{landmark} {area_type}"
            ],
            LocationType.SETTLEMENT_AREA: [
                "{adjective} {district_type}",
                "The {descriptor} Quarter",
                "{landmark} District"
            ]
        }
        
        patterns = name_patterns.get(location_type, ["Unnamed Location"])
        pattern = random.choice(patterns)
        
        # Generate variables for the pattern
        variables = {
            "adjective": random.choice(["Ancient", "Forgotten", "Sacred", "Hidden", "Lost"]),
            "room_type": random.choice(["Chamber", "Hall", "Sanctum", "Vault"]),
            "descriptor": random.choice(["Whispering", "Silent", "Eternal", "Mystic"]),
            "concept": random.choice(["Shadows", "Echoes", "Memories", "Secrets"]),
            "terrain": random.choice(["Grove", "Clearing", "Dell", "Hollow"]),
            "biome_feature": self._get_biome_feature(biome),
            "area_type": random.choice(["Expanse", "Reach", "Vale", "Heights"]),
            "district_type": random.choice(["Quarter", "Ward", "District", "Square"]),
            "landmark": random.choice(["Market", "Temple", "Tower", "Bridge"]),
            "ancient": random.choice(["Forgotten", "Ancient", "Old", "Timeless"])
        }
        
        try:
            return pattern.format(**variables)
        except KeyError:
            return "Mysterious Location"

    def _get_biome_feature(self, biome: Optional[BiomeType]) -> str:
        """Get a feature name appropriate for the biome."""
        
        biome_features = {
            BiomeType.TEMPERATE_FOREST: "Woods",
            BiomeType.TROPICAL_FOREST: "Jungle",
            BiomeType.GRASSLAND: "Plains",
            BiomeType.DESERT: "Dunes",
            BiomeType.MOUNTAINS: "Peaks",
            BiomeType.SWAMP: "Marsh",
            BiomeType.ARCTIC: "Tundra",
            BiomeType.COAST: "Shore"
        }
        
        return biome_features.get(biome, "Lands")

    async def _generate_template_variables(
        self,
        request: LocationDescriptionRequest,
        template: DescriptionTemplate
    ) -> Dict[str, str]:
        """Generate variables to fill in description templates."""
        
        variables = {}
        
        # Basic variables
        variables.update({
            "article": random.choice(["a", "an"]),
            "adjective": await self._select_appropriate_adjective(request),
            "size_desc": random.choice(["spans before you", "extends into shadow", "opens around you"]),
            "condition_desc": random.choice(["appears well-maintained", "shows signs of age", "bears the marks of time"]),
            "lighting_desc": await self._generate_lighting_description(request),
            "unique_feature": await self._generate_unique_feature(request.location_type),
            "direction_desc": random.choice(["in all directions", "toward the horizon", "as far as the eye can see"]),
            "sky_desc": await self._generate_sky_description(request.weather, request.time_of_day)
        })
        
        # Location-specific variables
        if request.location_type == LocationType.DUNGEON_ROOM:
            variables.update({
                "room_type": random.choice(["chamber", "hall", "room", "sanctum"]),
                "walls_desc": random.choice(template.feature_pools.get("walls", ["stone walls"])),
                "floor_desc": random.choice(template.feature_pools.get("floors", ["stone floor"])),
                "ceiling_desc": random.choice(template.feature_pools.get("ceilings", ["arched ceiling"]))
            })
        
        elif request.location_type == LocationType.OUTDOOR_AREA:
            variables.update({
                "terrain_type": await self._get_terrain_for_biome(request.biome),
                "biome_desc": self._get_biome_description(request.biome),
                "landscape": random.choice(["wilderness", "countryside", "terrain", "expanse"])
            })
        
        return variables

    async def _select_appropriate_adjective(self, request: LocationDescriptionRequest) -> str:
        """Select an adjective appropriate for the atmosphere and location type."""
        
        if request.atmosphere:
            effects = self.atmosphere_effects.get(request.atmosphere, {})
            descriptors = effects.get("descriptors", [])
            if descriptors:
                return random.choice(descriptors)
        
        # Fallback adjectives by location type
        fallback_adjectives = {
            LocationType.DUNGEON_ROOM: ["dark", "shadowy", "ancient", "forgotten"],
            LocationType.OUTDOOR_AREA: ["vast", "open", "wild", "natural"],
            LocationType.SETTLEMENT_AREA: ["busy", "populated", "civilized", "urban"]
        }
        
        adjectives = fallback_adjectives.get(request.location_type, ["interesting"])
        return random.choice(adjectives)

    async def _generate_lighting_description(self, request: LocationDescriptionRequest) -> str:
        """Generate appropriate lighting description."""
        
        if request.location_type == LocationType.OUTDOOR_AREA:
            if request.time_of_day == "night":
                return "is bathed in moonlight"
            elif request.time_of_day == "dawn":
                return "glows with the soft light of dawn"
            elif request.time_of_day == "dusk":
                return "is painted in the warm colors of sunset"
            else:
                return "is illuminated by natural daylight"
        
        else:  # Indoor locations
            lighting_options = [
                "is dimly lit by flickering torches",
                "glows with an otherworldly light",
                "is shrouded in deep shadows",
                "is lit by mysterious luminescence"
            ]
            return random.choice(lighting_options)

    async def _generate_unique_feature(self, location_type: LocationType) -> str:
        """Generate a unique feature for the location."""
        
        features_by_type = {
            LocationType.DUNGEON_ROOM: [
                "holds secrets of ages past",
                "echoes with ancient whispers",
                "bears mysterious inscriptions",
                "contains remnants of former glory"
            ],
            LocationType.OUTDOOR_AREA: [
                "stretches beyond the horizon",
                "teems with natural life", 
                "holds the beauty of the wild",
                "whispers stories in the wind"
            ],
            LocationType.SETTLEMENT_AREA: [
                "bustles with daily activity",
                "forms the heart of community life",
                "echoes with human endeavor",
                "represents civilization's reach"
            ]
        }
        
        features = features_by_type.get(location_type, ["holds untold mysteries"])
        return random.choice(features)

    async def _generate_sky_description(self, weather: Optional[WeatherType], time_of_day: str) -> str:
        """Generate sky description based on weather and time."""
        
        if weather == WeatherType.CLEAR:
            if time_of_day == "night":
                return "a star-filled night sky"
            else:
                return "clear blue skies"
        elif weather == WeatherType.CLOUDY:
            return "overcast skies"
        elif weather == WeatherType.RAIN:
            return "storm-darkened clouds"
        elif weather == WeatherType.SNOW:
            return "heavy, snow-laden clouds"
        else:
            return "the open sky"

    async def _get_terrain_for_biome(self, biome: Optional[BiomeType]) -> str:
        """Get terrain description for biome."""
        
        terrain_map = {
            BiomeType.TEMPERATE_FOREST: "forested landscape",
            BiomeType.TROPICAL_FOREST: "dense jungle",
            BiomeType.GRASSLAND: "rolling grasslands",
            BiomeType.DESERT: "sandy desert",
            BiomeType.MOUNTAINS: "rugged mountains",
            BiomeType.SWAMP: "wetland marsh",
            BiomeType.ARCTIC: "frozen tundra"
        }
        
        return terrain_map.get(biome, "natural terrain")

    def _get_biome_description(self, biome: Optional[BiomeType]) -> str:
        """Get descriptive text for biome."""
        
        descriptions = {
            BiomeType.TEMPERATE_FOREST: "tree-covered",
            BiomeType.TROPICAL_FOREST: "lush jungle",
            BiomeType.GRASSLAND: "open grassland",
            BiomeType.DESERT: "arid desert",
            BiomeType.MOUNTAINS: "mountainous",
            BiomeType.SWAMP: "marshy wetland"
        }
        
        return descriptions.get(biome, "natural")

    async def _generate_short_description(
        self,
        template: str,
        variables: Dict[str, str],
        request: LocationDescriptionRequest
    ) -> str:
        """Generate a concise description of the location."""
        
        try:
            # Fill in template variables
            description = template.format(**variables)
            
            # Capitalize first letter
            description = description[0].upper() + description[1:] if description else ""
            
            # Ensure proper sentence ending
            if not description.endswith('.'):
                description += '.'
                
            return description
            
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return f"This {request.location_type.value} presents an intriguing sight."

    async def _generate_detailed_description(
        self,
        template: DescriptionTemplate,
        variables: Dict[str, str],
        request: LocationDescriptionRequest
    ) -> str:
        """Generate a detailed, immersive description."""
        
        # Start with the base description
        base_desc = await self._generate_short_description(
            random.choice(template.base_templates), variables, request
        )
        
        # Add 2-4 additional descriptive sentences
        additional_sentences = []
        sentence_count = 3 if request.detail_level == "detailed" else 2
        
        for _ in range(sentence_count):
            sentence_type = random.choice(["visual", "atmospheric", "feature"])
            
            if sentence_type == "visual":
                sentence = await self._generate_visual_detail(request.location_type, variables)
            elif sentence_type == "atmospheric":
                sentence = await self._generate_atmospheric_detail(request)
            else:
                sentence = await self._generate_feature_detail(request.location_type)
            
            if sentence:
                additional_sentences.append(sentence)
        
        # Combine all sentences
        full_description = base_desc + " " + " ".join(additional_sentences)
        
        return full_description

    async def _generate_visual_detail(self, location_type: LocationType, variables: Dict[str, str]) -> str:
        """Generate visual details for the location."""
        
        visual_details = {
            LocationType.DUNGEON_ROOM: [
                "Carved stone columns support the vaulted ceiling above.",
                "Ancient sconces line the walls, some still bearing traces of old torches.",
                "The floor is worn smooth by countless footsteps over the ages."
            ],
            LocationType.OUTDOOR_AREA: [
                "Wildflowers dot the landscape with splashes of vibrant color.",
                "Trees sway gently in the breeze, their leaves rustling softly.",
                "The horizon stretches endlessly, meeting the sky in a hazy line."
            ],
            LocationType.SETTLEMENT_AREA: [
                "Buildings of various sizes and styles line the streets.",
                "People move about their daily business with purposeful steps.",
                "Signs and banners indicate shops and services available."
            ]
        }
        
        details = visual_details.get(location_type, ["The area has a distinct character."])
        return random.choice(details)

    async def _generate_atmospheric_detail(self, request: LocationDescriptionRequest) -> str:
        """Generate atmospheric details based on the mood."""
        
        if request.atmosphere:
            effects = self.atmosphere_effects.get(request.atmosphere, {})
            descriptors = effects.get("descriptors", [])
            if descriptors:
                return f"The atmosphere feels {random.choice(descriptors)} and evocative."
        
        return "The space has a unique and memorable quality."

    async def _generate_feature_detail(self, location_type: LocationType) -> str:
        """Generate details about specific features."""
        
        feature_details = {
            LocationType.DUNGEON_ROOM: [
                "Mysterious symbols are etched into the stone surfaces.",
                "A faint draft suggests hidden passages nearby.",
                "The remains of ancient furniture can be glimpsed in the shadows."
            ],
            LocationType.OUTDOOR_AREA: [
                "Natural landmarks provide reference points in the landscape.",
                "Wildlife signs indicate the presence of various creatures.",
                "The terrain shows evidence of both natural and human activity."
            ],
            LocationType.SETTLEMENT_AREA: [
                "The architecture reflects local building traditions and materials.",
                "Street layout follows practical needs for trade and movement.",
                "Public spaces serve as gathering points for the community."
            ]
        }
        
        details = feature_details.get(location_type, ["Notable features distinguish this location."])
        return random.choice(details)

    async def _create_environmental_conditions(self, request: LocationDescriptionRequest) -> EnvironmentalConditions:
        """Create environmental conditions for the location."""
        
        # Base conditions
        conditions = EnvironmentalConditions()
        
        # Apply weather if outdoor
        if request.location_type == LocationType.OUTDOOR_AREA and request.weather:
            conditions.weather = request.weather
            
            # Adjust other conditions based on weather
            if request.weather in [WeatherType.RAIN, WeatherType.HEAVY_RAIN]:
                conditions.humidity = min(1.0, conditions.humidity + 0.3)
                conditions.temperature -= 5
            elif request.weather == WeatherType.SNOW:
                conditions.temperature = min(-5, conditions.temperature - 10)
                conditions.humidity = max(0.2, conditions.humidity - 0.2)
        
        # Adjust for time of day
        if request.time_of_day == "night":
            conditions.light_level = LightLevel.DIM if request.location_type == LocationType.OUTDOOR_AREA else LightLevel.DARK
            conditions.temperature -= 5
        elif request.time_of_day in ["dawn", "dusk"]:
            conditions.light_level = LightLevel.DIM
            
        # Adjust for biome
        if request.biome:
            conditions.temperature = self._adjust_temperature_for_biome(conditions.temperature, request.biome)
            conditions.humidity = self._adjust_humidity_for_biome(conditions.humidity, request.biome)
        
        return conditions

    def _adjust_temperature_for_biome(self, base_temp: float, biome: BiomeType) -> float:
        """Adjust temperature based on biome."""
        
        adjustments = {
            BiomeType.ARCTIC: -20,
            BiomeType.TUNDRA: -10,
            BiomeType.MOUNTAINS: -5,
            BiomeType.TEMPERATE_FOREST: 0,
            BiomeType.GRASSLAND: 2,
            BiomeType.DESERT: 10,
            BiomeType.TROPICAL_FOREST: 8,
            BiomeType.SWAMP: 5
        }
        
        return base_temp + adjustments.get(biome, 0)

    def _adjust_humidity_for_biome(self, base_humidity: float, biome: BiomeType) -> float:
        """Adjust humidity based on biome."""
        
        adjustments = {
            BiomeType.DESERT: -0.4,
            BiomeType.ARCTIC: -0.3,
            BiomeType.MOUNTAINS: -0.2,
            BiomeType.GRASSLAND: -0.1,
            BiomeType.TEMPERATE_FOREST: 0,
            BiomeType.TROPICAL_FOREST: 0.3,
            BiomeType.SWAMP: 0.4
        }
        
        adjustment = adjustments.get(biome, 0)
        return max(0.0, min(1.0, base_humidity + adjustment))

    async def _generate_sensory_details(
        self,
        location: LocationSchema,
        request: LocationDescriptionRequest
    ) -> SensoryDetails:
        """Generate rich sensory details for immersion."""
        
        sensory = SensoryDetails()
        
        # Visual details
        sensory.visual = await self._generate_visual_sensory(location, request)
        
        # Auditory details
        sensory.auditory = await self._generate_auditory_sensory(location, request)
        
        # Olfactory details
        sensory.olfactory = await self._generate_olfactory_sensory(location, request)
        
        # Tactile details
        sensory.tactile = await self._generate_tactile_sensory(location, request)
        
        # Emotional impressions
        sensory.emotional = await self._generate_emotional_sensory(location, request)
        
        return sensory

    async def _generate_visual_sensory(self, location: LocationSchema, request: LocationDescriptionRequest) -> List[str]:
        """Generate visual sensory details."""
        
        visuals = []
        library = self.sensory_libraries["visual"]
        
        # Add color descriptions
        visuals.append(f"The predominant colors are {random.choice(library['colors'])} and {random.choice(library['colors'])}")
        
        # Add lighting descriptions
        visuals.append(f"The space is characterized by {random.choice(library['lighting'])}")
        
        # Add texture descriptions
        if random.random() < 0.7:  # 70% chance
            visuals.append(f"Surfaces appear {random.choice(library['textures'])}")
        
        # Add movement if applicable
        if request.location_type == LocationType.OUTDOOR_AREA:
            visuals.append(f"Elements in the scene are {random.choice(library['movement'])}")
        
        return visuals

    async def _generate_auditory_sensory(self, location: LocationSchema, request: LocationDescriptionRequest) -> List[str]:
        """Generate auditory sensory details."""
        
        sounds = []
        library = self.sensory_libraries["auditory"]
        
        # Choose appropriate sound category
        if location.location_type == LocationType.OUTDOOR_AREA:
            sound_category = "natural"
        elif location.location_type == LocationType.SETTLEMENT_AREA:
            sound_category = "urban"
        else:
            sound_category = "dungeon"
        
        # Add 2-3 sound descriptions
        available_sounds = library[sound_category]
        for _ in range(random.randint(2, 3)):
            sound = random.choice(available_sounds)
            volume = random.choice(library["volume"])
            sounds.append(f"{sound}, {volume}")
        
        return sounds

    async def _generate_olfactory_sensory(self, location: LocationSchema, request: LocationDescriptionRequest) -> List[str]:
        """Generate olfactory sensory details."""
        
        smells = []
        library = self.sensory_libraries["olfactory"]
        
        # Choose appropriate smell category
        if location.location_type == LocationType.OUTDOOR_AREA:
            smell_category = "natural"
        elif location.location_type == LocationType.SETTLEMENT_AREA:
            smell_category = "urban"
        else:
            smell_category = "dungeon"
        
        # Add 1-2 smell descriptions
        available_smells = library[smell_category]
        for _ in range(random.randint(1, 2)):
            smell = random.choice(available_smells)
            intensity = random.choice(library["intensity"])
            smells.append(f"{intensity} of {smell}")
        
        return smells

    async def _generate_tactile_sensory(self, location: LocationSchema, request: LocationDescriptionRequest) -> List[str]:
        """Generate tactile sensory details."""
        
        tactile = []
        library = self.sensory_libraries["tactile"]
        
        # Temperature
        temp_desc = random.choice(library["temperature"])
        tactile.append(f"The air feels {temp_desc}")
        
        # Humidity if applicable
        if location.location_type == LocationType.OUTDOOR_AREA:
            humidity_desc = random.choice(library["humidity"])
            tactile.append(f"The atmosphere is {humidity_desc}")
        
        # Air movement
        air_desc = random.choice(library["air_movement"])
        tactile.append(f"You notice {air_desc}")
        
        return tactile

    async def _generate_emotional_sensory(self, location: LocationSchema, request: LocationDescriptionRequest) -> List[str]:
        """Generate emotional impressions and feelings."""
        
        emotions = []
        library = self.sensory_libraries["emotional"]
        
        # Base emotional response based on atmosphere
        if location.atmosphere in [Atmosphere.PEACEFUL, Atmosphere.SACRED]:
            emotion_category = "positive"
        elif location.atmosphere in [Atmosphere.THREATENING, Atmosphere.CURSED]:
            emotion_category = "negative"
        else:
            emotion_category = "neutral"
        
        # Add 1-2 emotional impressions
        available_emotions = library[emotion_category]
        for _ in range(random.randint(1, 2)):
            emotions.append(random.choice(available_emotions))
        
        return emotions

    async def _select_features(self, location: LocationSchema, request: LocationDescriptionRequest) -> List[LocationFeature]:
        """Select appropriate features for the location."""
        
        features = []
        feature_pool = self.feature_pools.get(location.location_type, {})
        
        if not feature_pool:
            return features
        
        # Select features from each category
        feature_count = random.randint(1, 3)
        
        for category, category_features in feature_pool.items():
            if len(features) >= feature_count:
                break
                
            if random.random() < 0.6:  # 60% chance for each category
                feature = random.choice(category_features)
                features.append(feature)
        
        return features

    async def _apply_atmosphere_effects(self, location: LocationSchema, request: LocationDescriptionRequest) -> None:
        """Apply atmospheric effects to the location description."""
        
        if not request.atmosphere:
            return
            
        effects = self.atmosphere_effects.get(request.atmosphere, {})
        
        # Add atmospheric descriptors to mood
        descriptors = effects.get("descriptors", [])
        location.mood_descriptors.extend(random.choices(descriptors, k=min(2, len(descriptors))))
        
        # Modify sensory details based on atmosphere
        if effects.get("scents"):
            additional_scents = random.choices(effects["scents"], k=1)
            location.sensory_details.olfactory.extend(additional_scents)
        
        if effects.get("sounds"):
            additional_sounds = random.choices(effects["sounds"], k=1)
            location.sensory_details.auditory.extend(additional_sounds)

    async def _apply_weather_effects(self, location: LocationSchema, weather: WeatherType) -> None:
        """Apply weather effects to outdoor locations."""
        
        if location.location_type != LocationType.OUTDOOR_AREA:
            return
            
        weather_effects = {
            WeatherType.RAIN: {
                "visual": ["glistening wet surfaces", "puddles reflecting the sky"],
                "auditory": ["steady patter of raindrops", "dripping from leaves"],
                "olfactory": ["fresh scent of rain", "petrichor rising from earth"],
                "tactile": ["cool moisture in the air", "damp ground underfoot"]
            },
            WeatherType.SNOW: {
                "visual": ["pristine white coating", "delicate snowflakes falling"],
                "auditory": ["muffled sounds", "soft crunch of snow"],
                "olfactory": ["crisp, clean air", "absence of summer scents"],
                "tactile": ["biting cold", "soft snow yielding underfoot"]
            },
            WeatherType.FOG: {
                "visual": ["limited visibility", "ghostly shapes in the mist"],
                "auditory": ["sounds seem muffled and distant"],
                "olfactory": ["damp, misty air"],
                "tactile": ["cool moisture against skin"]
            }
        }
        
        effects = weather_effects.get(weather, {})
        
        for sense, descriptions in effects.items():
            if hasattr(location.sensory_details, sense):
                sense_list = getattr(location.sensory_details, sense)
                sense_list.extend(descriptions)

    async def _apply_time_effects(self, location: LocationSchema, time_of_day: str) -> None:
        """Apply time-of-day effects to the location."""
        
        time_effects = {
            "dawn": {
                "visual": ["soft golden light", "long shadows stretching"],
                "auditory": ["awakening birds", "quiet morning sounds"],
                "atmosphere": "fresh and hopeful"
            },
            "day": {
                "visual": ["bright natural light", "clear visibility"],
                "auditory": ["full activity", "daytime sounds"],
                "atmosphere": "active and vibrant"
            },
            "dusk": {
                "visual": ["warm orange light", "deepening shadows"],
                "auditory": ["evening sounds", "settling activity"],
                "atmosphere": "peaceful and contemplative"
            },
            "night": {
                "visual": ["limited visibility", "mysterious shadows"],
                "auditory": ["nocturnal sounds", "hushed tones"],
                "atmosphere": "mysterious and quiet"
            }
        }
        
        effects = time_effects.get(time_of_day, {})
        
        # Apply visual effects
        if "visual" in effects:
            location.sensory_details.visual.extend(effects["visual"])
        
        # Apply auditory effects  
        if "auditory" in effects:
            location.sensory_details.auditory.extend(effects["auditory"])
        
        # Adjust lighting
        if time_of_day == "night":
            location.environment.light_level = LightLevel.DIM
        elif time_of_day in ["dawn", "dusk"]:
            location.environment.light_level = LightLevel.DIM

    async def analyze_location(self, location: LocationSchema) -> LocationAnalysis:
        """Analyze location description quality and provide suggestions."""
        
        # Calculate readability (simplified)
        description_length = len(location.detailed_description.split())
        readability_score = min(1.0, max(0.0, (description_length - 20) / 100))
        
        # Calculate immersion based on sensory details
        sensory_count = (
            len(location.sensory_details.visual) +
            len(location.sensory_details.auditory) + 
            len(location.sensory_details.olfactory) +
            len(location.sensory_details.tactile) +
            len(location.sensory_details.emotional)
        )
        immersion_score = min(1.0, sensory_count / 10.0)
        
        # Analyze detail balance
        detail_balance = {
            "visual": len(location.sensory_details.visual) / max(1, sensory_count),
            "auditory": len(location.sensory_details.auditory) / max(1, sensory_count),
            "olfactory": len(location.sensory_details.olfactory) / max(1, sensory_count),
            "tactile": len(location.sensory_details.tactile) / max(1, sensory_count),
            "emotional": len(location.sensory_details.emotional) / max(1, sensory_count)
        }
        
        # Generate suggestions
        suggestions = []
        missing_elements = []
        
        if len(location.sensory_details.olfactory) == 0:
            missing_elements.append("olfactory details")
            suggestions.append("Add scent descriptions to enhance immersion")
        
        if len(location.sensory_details.auditory) < 2:
            suggestions.append("Include more auditory details for atmosphere")
        
        if len(location.features) == 0:
            missing_elements.append("interactive features")
            suggestions.append("Add interactive features for player engagement")
        
        # Identify strengths
        strengths = []
        if immersion_score > 0.7:
            strengths.append("Rich sensory details")
        if len(location.features) > 2:
            strengths.append("Good variety of features")
        if len(location.mood_descriptors) > 0:
            strengths.append("Clear atmospheric mood")
        
        return LocationAnalysis(
            location_id=location.id or "unknown",
            readability_score=readability_score,
            immersion_score=immersion_score,
            detail_balance=detail_balance,
            suggested_improvements=suggestions,
            missing_elements=missing_elements,
            strengths=strengths
        )