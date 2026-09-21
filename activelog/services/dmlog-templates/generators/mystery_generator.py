"""
Murder mystery generator for investigative scenarios
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from ..models.base import BaseTemplate, ComplexityLevel, DifficultyLevel
from ..models.mystery import (
    Mystery, Clue, Suspect, RedHerring, MysteryEvent, 
    Investigation, CrimeScene, InvestigationTechnique
)
from ..models.character import NPCProfile
from .base_generator import BaseGenerator
from .character_generator import CharacterGenerator
from ..config import MYSTERY_CONFIG


class MysteryGenerator(BaseGenerator):
    """Generates murder mystery scenarios with clues, suspects, and investigations"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.character_generator = CharacterGenerator(seed)
    
    async def generate_mystery(self, 
                             mystery_type: str = "murder",
                             complexity: str = "moderate",
                             party_level: int = 5,
                             suspect_count: int = 5) -> Mystery:
        """Generate a complete mystery scenario"""
        
        mystery_config = MYSTERY_CONFIG["mystery_types"].get(mystery_type, 
                                                           MYSTERY_CONFIG["mystery_types"]["murder"])
        
        # Generate victim and perpetrator first
        victim = await self._generate_victim(mystery_type, party_level)
        perpetrator = await self._generate_perpetrator(mystery_type, party_level)
        
        # Generate suspects (including the perpetrator)
        suspects = await self._generate_suspects(
            mystery_type, suspect_count, party_level, perpetrator, victim
        )
        
        # Generate timeline of events
        timeline = await self._generate_timeline(mystery_type, victim, perpetrator, suspects)
        
        # Generate clues
        clues = await self._generate_clues(
            mystery_type, complexity, perpetrator, victim, suspects, timeline
        )
        
        # Generate red herrings
        red_herrings = await self._generate_red_herrings(complexity, suspects, clues)
        
        # Generate crime scene
        crime_scene = await self._generate_crime_scene(mystery_type, clues)
        
        # Generate witness NPCs
        witnesses = await self._generate_witnesses(timeline, suspects)
        
        mystery = Mystery(
            name=f"The {mystery_config['name']} at {crime_scene}",
            description=f"A {complexity} {mystery_type} mystery requiring investigation",
            mystery_type=mystery_type,
            central_question=mystery_config.get("central_question", f"Who committed the {mystery_type}?"),
            true_solution=self._generate_solution(perpetrator, victim, timeline),
            victim=victim.id,
            perpetrator=perpetrator.id,
            timeline=timeline,
            key_suspects=suspects,
            witnesses=witnesses,
            clues=clues,
            red_herrings=red_herrings,
            crime_scene=crime_scene,
            key_locations=self._generate_key_locations(mystery_type, timeline),
            required_breakthroughs=self._generate_required_breakthroughs(complexity, clues),
            themes=mystery_config.get("themes", []),
            moral_complications=self._generate_moral_complications(perpetrator, victim),
            unexpected_twists=self._generate_twists(complexity, suspects, timeline),
            confrontation_scenarios=self._generate_confrontation_scenarios(perpetrator),
            evidence_needed_for_conviction=self._select_conviction_evidence(clues),
            investigation_flowchart=self._create_investigation_flowchart(clues, suspects),
            npc_interaction_notes=self._create_npc_notes(suspects, witnesses),
            pacing_guidelines=self._generate_pacing_guidelines(complexity),
            backup_clues=self._generate_backup_clues(clues),
            tags=[mystery_type, complexity, f"level_{party_level}", f"suspects_{suspect_count}"]
        )
        
        return mystery
    
    async def _generate_victim(self, mystery_type: str, party_level: int) -> NPCProfile:
        """Generate the victim of the mystery"""
        
        victim_templates = MYSTERY_CONFIG["victim_types"].get(mystery_type, 
                                                            MYSTERY_CONFIG["victim_types"]["murder"])
        template = self.rng.choice(victim_templates)
        
        victim = NPCProfile(
            name=template["name"],
            description=template["description"],
            role=template["role"],
            background_type=template.get("background", "folk_hero"),
            personality_traits=template.get("personality", []),
            secrets=template.get("secrets", []),
            relationships=template.get("relationships", []),
            motivations=template.get("motivations", []),
            stats=template.get("stats", {}),
            tags=["victim", mystery_type]
        )
        
        return victim
    
    async def _generate_perpetrator(self, mystery_type: str, party_level: int) -> NPCProfile:
        """Generate the perpetrator of the mystery"""
        
        perp_templates = MYSTERY_CONFIG["perpetrator_types"].get(mystery_type, 
                                                               MYSTERY_CONFIG["perpetrator_types"]["murder"])
        template = self.rng.choice(perp_templates)
        
        perpetrator = NPCProfile(
            name=template["name"],
            description=template["description"],
            role=template["role"],
            background_type=template.get("background", "criminal"),
            personality_traits=template.get("personality", []),
            secrets=template.get("secrets", []),
            motivations=template.get("motivations", []),
            stats=self._scale_stats_for_level(template.get("stats", {}), party_level),
            tags=["perpetrator", mystery_type, "hidden_identity"]
        )
        
        return perpetrator
    
    async def _generate_suspects(self, 
                               mystery_type: str, 
                               suspect_count: int,
                               party_level: int,
                               perpetrator: NPCProfile,
                               victim: NPCProfile) -> List[Suspect]:
        """Generate suspects including the perpetrator"""
        
        suspects = []
        
        # Create suspect for the perpetrator
        perp_suspect = Suspect(
            name=f"Suspect: {perpetrator.name}",
            description=f"Investigation profile for {perpetrator.name}",
            npc_profile=perpetrator,
            guilt_level="guilty",
            true_role="perpetrator",
            public_role=perpetrator.role,
            motive=self._generate_motive(perpetrator, victim),
            means=self._generate_means(mystery_type),
            opportunity=self._generate_opportunity(),
            alibi=self._generate_false_alibi(),
            alibi_strength="weak",
            suspicious_behaviors=MYSTERY_CONFIG["suspicious_behaviors"][:3],
            lies_told=self._generate_lies(perpetrator),
            secrets_hidden=perpetrator.secrets,
            reaction_to_questioning="defensive",
            willingness_to_cooperate="reluctant",
            tags=["guilty", "perpetrator"]
        )
        suspects.append(perp_suspect)
        
        # Generate innocent suspects
        for i in range(suspect_count - 1):
            innocent_npc = await self.character_generator.generate_npc(
                f"Suspect {i+2}",
                party_level=party_level
            )
            
            innocent_suspect = Suspect(
                name=f"Suspect: {innocent_npc.name}",
                description=f"Investigation profile for {innocent_npc.name}",
                npc_profile=innocent_npc,
                guilt_level="innocent",
                true_role="bystander",
                public_role=innocent_npc.role,
                motive="None (red herring motive possible)",
                means=self._generate_innocent_means(mystery_type),
                opportunity=self._generate_limited_opportunity(),
                alibi=self._generate_true_alibi(),
                alibi_strength=self.rng.choice(["moderate", "strong"]),
                suspicious_behaviors=self.rng.sample(MYSTERY_CONFIG["suspicious_behaviors"], 
                                                   self.rng.randint(0, 2)),
                connections_to_victim=self._generate_victim_connections(victim),
                reaction_to_questioning=self.rng.choice(["cooperative", "nervous", "defensive"]),
                willingness_to_cooperate=self.rng.choice(["eager", "reluctant", "conditional"]),
                tags=["innocent", "suspect"]
            )
            suspects.append(innocent_suspect)
        
        return suspects
    
    async def _generate_timeline(self, 
                               mystery_type: str,
                               victim: NPCProfile,
                               perpetrator: NPCProfile,
                               suspects: List[Suspect]) -> List[MysteryEvent]:
        """Generate timeline of events"""
        
        events = []
        
        # Core crime event
        crime_event = MysteryEvent(
            name=f"The {mystery_type.title()}",
            description=f"The {mystery_type} of {victim.name} occurs",
            event_type="crime",
            when_occurred="0 hours ago",
            location="crime_scene",
            perpetrator=perpetrator.id,
            victim=victim.id,
            public_version=f"{victim.name} was found dead",
            true_version=f"{perpetrator.name} killed {victim.name}",
            when_discovered="investigation_start",
            discovery_method="body_found",
            significance="central"
        )
        events.append(crime_event)
        
        # Events leading up to the crime
        leadup_events = [
            {"hours": -24, "event": "victim_last_seen", "description": f"{victim.name} seen going about normal routine"},
            {"hours": -8, "event": "confrontation", "description": f"Argument between {victim.name} and {perpetrator.name}"},
            {"hours": -2, "event": "preparation", "description": f"{perpetrator.name} acquires means"},
            {"hours": -1, "event": "approach", "description": f"{perpetrator.name} approaches victim"}
        ]
        
        for event_data in leadup_events:
            event = MysteryEvent(
                name=event_data["event"].replace("_", " ").title(),
                description=event_data["description"],
                event_type="preparation",
                when_occurred=f"{abs(event_data['hours'])} hours before crime",
                location="various",
                perpetrator=perpetrator.id if "perpetrator" in event_data["description"] else "",
                victim=victim.id if "victim" in event_data["description"] else "",
                public_version=event_data["description"],
                true_version=event_data["description"],
                significance="minor"
            )
            events.append(event)
        
        return events
    
    async def _generate_clues(self, 
                            mystery_type: str,
                            complexity: str,
                            perpetrator: NPCProfile,
                            victim: NPCProfile,
                            suspects: List[Suspect],
                            timeline: List[MysteryEvent]) -> List[Clue]:
        """Generate clues for the mystery"""
        
        clues = []
        
        # Number of clues based on complexity
        clue_count = {"simple": 4, "moderate": 6, "complex": 8, "epic": 10}.get(complexity, 6)
        
        # Generate different types of clues
        clue_types = ["physical", "testimonial", "circumstantial", "documentary"]
        
        for i in range(clue_count):
            clue_type = self.rng.choice(clue_types)
            
            if clue_type == "physical":
                clue = self._generate_physical_clue(perpetrator, victim, i)
            elif clue_type == "testimonial":
                clue = self._generate_testimonial_clue(suspects, i)
            elif clue_type == "circumstantial":
                clue = self._generate_circumstantial_clue(timeline, i)
            else:  # documentary
                clue = self._generate_documentary_clue(perpetrator, victim, i)
            
            clues.append(clue)
        
        return clues
    
    def _generate_physical_clue(self, perpetrator: NPCProfile, victim: NPCProfile, index: int) -> Clue:
        """Generate a physical clue"""
        
        physical_evidence = [
            {"name": "Bloodstained weapon", "info": f"Weapon belongs to {perpetrator.name}"},
            {"name": "Fingerprints", "info": f"Prints match {perpetrator.name}"},
            {"name": "Torn fabric", "info": f"Matches clothing worn by {perpetrator.name}"},
            {"name": "Personal item", "info": f"Belongs to {perpetrator.name}"},
            {"name": "Footprints", "info": f"Boot size matches {perpetrator.name}"}
        ]
        
        evidence = self.rng.choice(physical_evidence)
        
        return Clue(
            name=evidence["name"],
            description=f"Physical evidence found at the crime scene",
            clue_type="physical",
            location="crime_scene",
            evidence_description=evidence["name"],
            information_revealed=[evidence["info"]],
            revelation_level="major" if "weapon" in evidence["name"] else "moderate",
            true_significance=f"Directly implicates {perpetrator.name}",
            tags=["physical", "crime_scene", "perpetrator_evidence"]
        )
    
    def _generate_testimonial_clue(self, suspects: List[Suspect], index: int) -> Clue:
        """Generate a testimonial clue"""
        
        witness = self.rng.choice([s for s in suspects if s.guilt_level == "innocent"])
        
        testimonies = [
            f"Saw someone matching perpetrator's description near victim",
            f"Heard argument between victim and unknown person",
            f"Noticed suspicious behavior from one of the suspects",
            f"Can provide alibi information for some suspects"
        ]
        
        testimony = self.rng.choice(testimonies)
        
        return Clue(
            name=f"Witness Testimony #{index + 1}",
            description=f"Statement from {witness.npc_profile.name}",
            clue_type="testimonial",
            location="interview_room",
            discovery_method="questioning",
            evidence_description=f"{witness.npc_profile.name} provides testimony",
            information_revealed=[testimony],
            related_suspects=[witness.id],
            revelation_level="moderate",
            true_significance="Provides timeline or eliminates suspects",
            tags=["testimony", "witness", "interview"]
        )
    
    def _generate_circumstantial_clue(self, timeline: List[MysteryEvent], index: int) -> Clue:
        """Generate a circumstantial clue"""
        
        circumstances = [
            "Financial records show motive for the crime",
            "Timeline evidence places suspect at scene",
            "Victim's routine was known to perpetrator",
            "Recent changes in victim's behavior noted"
        ]
        
        circumstance = self.rng.choice(circumstances)
        
        return Clue(
            name=f"Circumstantial Evidence #{index + 1}",
            description="Evidence that supports or contradicts suspect theories",
            clue_type="circumstantial",
            location="various",
            evidence_description=circumstance,
            information_revealed=[circumstance],
            revelation_level="minor",
            true_significance="Builds case against perpetrator",
            tags=["circumstantial", "motive", "timeline"]
        )
    
    def _generate_documentary_clue(self, perpetrator: NPCProfile, victim: NPCProfile, index: int) -> Clue:
        """Generate a documentary clue"""
        
        documents = [
            {"name": "Threatening letter", "info": f"Written by {perpetrator.name} to {victim.name}"},
            {"name": "Financial records", "info": f"Show debt from {perpetrator.name} to {victim.name}"},
            {"name": "Diary entry", "info": f"{victim.name}'s diary mentions fear of {perpetrator.name}"},
            {"name": "Contract or agreement", "info": f"Business dispute between victim and perpetrator"}
        ]
        
        doc = self.rng.choice(documents)
        
        return Clue(
            name=doc["name"],
            description="Written evidence relevant to the case",
            clue_type="documentary",
            location=self.rng.choice(["victim_home", "perpetrator_home", "office"]),
            evidence_description=doc["name"],
            information_revealed=[doc["info"]],
            revelation_level="major",
            true_significance="Establishes motive and connection",
            tags=["documentary", "motive", "written_evidence"]
        )
    
    async def _generate_red_herrings(self, 
                                   complexity: str,
                                   suspects: List[Suspect],
                                   clues: List[Clue]) -> List[RedHerring]:
        """Generate red herrings to mislead investigation"""
        
        red_herrings = []
        
        # Number based on complexity
        herring_count = {"simple": 1, "moderate": 2, "complex": 3, "epic": 4}.get(complexity, 2)
        
        herring_templates = MYSTERY_CONFIG["red_herrings"]
        
        for i in range(herring_count):
            template = self.rng.choice(herring_templates)
            innocent_suspect = self.rng.choice([s for s in suspects if s.guilt_level == "innocent"])
            
            herring = RedHerring(
                name=template["name"],
                description=template["description"],
                false_narrative=template["narrative"].format(suspect=innocent_suspect.npc_profile.name),
                apparent_significance="major",
                how_it_misleads=template["misleads"],
                grain_of_truth=template["truth"],
                actual_explanation=template["explanation"],
                how_revealed_false=template["revealed"],
                time_wasted_if_followed=template.get("time_wasted", 30),
                tags=["red_herring", "misdirection"]
            )
            
            red_herrings.append(herring)
        
        return red_herrings
    
    async def _generate_crime_scene(self, mystery_type: str, clues: List[Clue]) -> str:
        """Generate crime scene description"""
        
        scenes = MYSTERY_CONFIG["crime_scenes"].get(mystery_type, 
                                                  MYSTERY_CONFIG["crime_scenes"]["murder"])
        
        return self.rng.choice(scenes)["name"]
    
    async def _generate_witnesses(self, 
                                timeline: List[MysteryEvent],
                                suspects: List[Suspect]) -> List[NPCProfile]:
        """Generate witness NPCs"""
        
        witnesses = []
        witness_templates = MYSTERY_CONFIG["witness_types"]
        
        # Generate 2-3 witnesses
        for i in range(self.rng.randint(2, 3)):
            template = self.rng.choice(witness_templates)
            
            witness = NPCProfile(
                name=template["name"] + f" #{i+1}",
                description=template["description"],
                role=template["role"],
                personality_traits=template.get("personality", []),
                information_known=template.get("information", []),
                reliability=template.get("reliability", "reliable"),
                tags=["witness", "npc"]
            )
            
            witnesses.append(witness)
        
        return witnesses
    
    # Helper methods for generating various mystery elements
    
    def _generate_solution(self, perpetrator: NPCProfile, victim: NPCProfile, timeline: List[MysteryEvent]) -> str:
        """Generate the true solution to the mystery"""
        
        motive = self._generate_motive(perpetrator, victim)
        return f"{perpetrator.name} killed {victim.name} because {motive}. The crime occurred as shown in the timeline evidence."
    
    def _generate_motive(self, perpetrator: NPCProfile, victim: NPCProfile) -> str:
        """Generate motive for the crime"""
        
        motives = [
            "of a financial dispute",
            "of jealousy and revenge",
            "the victim discovered their secret",
            "of a business rivalry",
            "of a romantic entanglement",
            "the victim was blackmailing them"
        ]
        
        return self.rng.choice(motives)
    
    def _generate_means(self, mystery_type: str) -> str:
        """Generate means of committing the crime"""
        
        means_by_type = {
            "murder": ["knife", "poison", "blunt weapon", "magical spell", "strangulation"],
            "theft": ["lockpicking", "inside knowledge", "distraction", "magical assistance"],
            "disappearance": ["kidnapping", "magical transportation", "secret passage"]
        }
        
        return self.rng.choice(means_by_type.get(mystery_type, means_by_type["murder"]))
    
    def _generate_opportunity(self) -> str:
        """Generate opportunity for committing the crime"""
        
        opportunities = [
            "Was alone with victim",
            "Had access to crime scene",
            "Knew victim's schedule",
            "Had legitimate reason to be present"
        ]
        
        return self.rng.choice(opportunities)
    
    def _generate_false_alibi(self) -> str:
        """Generate false alibi for perpetrator"""
        
        alibis = [
            "Claims to have been at home alone",
            "Says was with friend who won't verify",
            "Provides receipt from different time",
            "Claims business meeting that didn't happen"
        ]
        
        return self.rng.choice(alibis)
    
    def _generate_true_alibi(self) -> str:
        """Generate true alibi for innocent suspects"""
        
        alibis = [
            "Was with family during time of crime",
            "Has security footage proving location",
            "Was in public place with witnesses",
            "Has official meeting records"
        ]
        
        return self.rng.choice(alibis)
    
    def _generate_innocent_means(self, mystery_type: str) -> str:
        """Generate limited means for innocent suspects"""
        
        return "Limited opportunity - lacks direct means"
    
    def _generate_limited_opportunity(self) -> str:
        """Generate limited opportunity for innocent suspects"""
        
        return "Had some access but limited opportunity"
    
    def _generate_lies(self, perpetrator: NPCProfile) -> List[str]:
        """Generate lies told by perpetrator"""
        
        lies = [
            "Denies knowing victim well",
            "Claims to have been elsewhere",
            "Lies about motive",
            "Provides false timeline"
        ]
        
        return self.rng.sample(lies, self.rng.randint(2, 4))
    
    def _generate_victim_connections(self, victim: NPCProfile) -> List[str]:
        """Generate connections to victim for suspects"""
        
        connections = [
            "Knew victim professionally",
            "Was neighbor of victim",
            "Had business dealings with victim",
            "Shared mutual friends with victim"
        ]
        
        return self.rng.sample(connections, self.rng.randint(1, 2))
    
    def _generate_key_locations(self, mystery_type: str, timeline: List[MysteryEvent]) -> List[str]:
        """Generate key investigation locations"""
        
        base_locations = ["crime_scene", "victim_home", "perpetrator_home"]
        additional = ["victim_workplace", "local_tavern", "town_square", "witness_homes"]
        
        return base_locations + self.rng.sample(additional, 2)
    
    def _generate_required_breakthroughs(self, complexity: str, clues: List[Clue]) -> List[str]:
        """Generate required breakthroughs to solve mystery"""
        
        breakthrough_count = {"simple": 2, "moderate": 3, "complex": 4, "epic": 5}.get(complexity, 3)
        
        breakthroughs = [
            "Identify the murder weapon",
            "Establish timeline of events",
            "Discover the motive",
            "Find evidence linking perpetrator to scene",
            "Break false alibi",
            "Connect seemingly unrelated evidence"
        ]
        
        return self.rng.sample(breakthroughs, min(len(breakthroughs), breakthrough_count))
    
    def _generate_moral_complications(self, perpetrator: NPCProfile, victim: NPCProfile) -> List[str]:
        """Generate moral complications for the mystery"""
        
        complications = [
            "Perpetrator had justifiable grievance",
            "Victim was not entirely innocent",
            "Revealing truth will hurt innocent people",
            "Justice vs. mercy dilemma"
        ]
        
        return self.rng.sample(complications, self.rng.randint(1, 2))
    
    def _generate_twists(self, complexity: str, suspects: List[Suspect], timeline: List[MysteryEvent]) -> List[str]:
        """Generate unexpected twists"""
        
        twist_count = {"simple": 1, "moderate": 1, "complex": 2, "epic": 3}.get(complexity, 1)
        
        twists = [
            "The victim is still alive",
            "There were multiple perpetrators",
            "The crime was self-defense",
            "Key witness is lying",
            "Crime scene was staged",
            "Wrong person was the intended victim"
        ]
        
        return self.rng.sample(twists, min(len(twists), twist_count))
    
    def _generate_confrontation_scenarios(self, perpetrator: NPCProfile) -> List[str]:
        """Generate ways to confront the perpetrator"""
        
        scenarios = [
            "Direct accusation with evidence",
            "Set trap to catch perpetrator in lie",
            "Confront with witnesses present",
            "Use psychological pressure",
            "Offer deal for confession"
        ]
        
        return self.rng.sample(scenarios, 3)
    
    def _select_conviction_evidence(self, clues: List[Clue]) -> List[str]:
        """Select evidence needed for conviction"""
        
        major_clues = [c.id for c in clues if c.revelation_level == "major"]
        return self.rng.sample(major_clues, min(len(major_clues), 2))
    
    def _create_investigation_flowchart(self, clues: List[Clue], suspects: List[Suspect]) -> Dict[str, Any]:
        """Create investigation flowchart"""
        
        return {
            "starting_points": ["crime_scene_investigation", "witness_interviews"],
            "clue_connections": {c.id: c.leads_to for c in clues},
            "suspect_elimination": [s.id for s in suspects if s.guilt_level == "innocent"],
            "breakthrough_moments": ["finding_murder_weapon", "breaking_alibi", "discovering_motive"]
        }
    
    def _create_npc_notes(self, suspects: List[Suspect], witnesses: List[NPCProfile]) -> Dict[str, str]:
        """Create DM notes for NPC interactions"""
        
        notes = {}
        
        for suspect in suspects:
            notes[suspect.npc_profile.id] = f"Attitude: {suspect.reaction_to_questioning}. Will reveal: {suspect.information_they_provide}. Will hide: {suspect.information_they_withhold}"
        
        for witness in witnesses:
            notes[witness.id] = f"Reliability: {getattr(witness, 'reliability', 'reliable')}. Information: {getattr(witness, 'information_known', [])}"
        
        return notes
    
    def _generate_pacing_guidelines(self, complexity: str) -> List[str]:
        """Generate pacing guidelines for the mystery"""
        
        guidelines = {
            "simple": [
                "Present crime scene immediately",
                "Introduce all suspects by session 1",
                "Major breakthrough by mid-session",
                "Resolve in 1-2 sessions"
            ],
            "moderate": [
                "Build tension with initial investigation",
                "Introduce suspects gradually",
                "Major breakthrough by session 2",
                "Red herring revealed session 2",
                "Resolve in 2-3 sessions"
            ],
            "complex": [
                "Extended investigation phase",
                "Multiple false leads",
                "Breakthrough moments spread across sessions",
                "Complex confrontation scene",
                "Resolve in 3-4 sessions"
            ]
        }
        
        return guidelines.get(complexity, guidelines["moderate"])
    
    def _generate_backup_clues(self, clues: List[Clue]) -> List[str]:
        """Generate backup clues in case players miss important ones"""
        
        backup_clues = [
            "Additional witness comes forward",
            "Anonymous tip points to evidence",
            "Perpetrator makes mistake",
            "New evidence discovered at secondary location"
        ]
        
        return self.rng.sample(backup_clues, 2)
    
    def _scale_stats_for_level(self, base_stats: Dict, party_level: int) -> Dict:
        """Scale NPC stats for party level"""
        
        if not base_stats:
            return {"cr": max(1, party_level // 2)}
        
        scaled = base_stats.copy()
        if "cr" in scaled:
            scaled["cr"] = max(1, scaled["cr"] + (party_level // 4))
        
        return scaled
    
    async def generate_quick_mystery(self, mystery_type: str = "murder") -> Mystery:
        """Generate a quick mystery with default settings"""
        
        return await self.generate_mystery(
            mystery_type=mystery_type,
            complexity="moderate",
            party_level=5,
            suspect_count=4
        )