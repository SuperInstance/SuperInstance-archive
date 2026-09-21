"""
Social Encounter Generator

Creates complex social encounters with NPCs, negotiations, intrigue,
and relationship dynamics for D&D sessions.
"""

import random
from typing import List, Dict, Any, Optional, Tuple

from ..models.encounter import SocialEncounter
from ..models.character import NPCProfile
from ..models.base import SkillCheck, SkillType, StatBlock
from ..config import SOCIAL_CONFIG
from .base_generator import BaseGenerator


class SocialEncounterGenerator(BaseGenerator):
    """Generates social encounters and NPC interactions"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.npc_archetypes = self._load_npc_archetypes()
        self.social_situations = self._load_social_situations()
        self.negotiation_frameworks = self._load_negotiation_frameworks()
        self.relationship_dynamics = self._load_relationship_dynamics()
    
    def _load_npc_archetypes(self) -> Dict[str, Dict[str, Any]]:
        """Load NPC archetype templates"""
        return {
            "ally": {
                "attitudes": ["friendly", "helpful", "supportive", "enthusiastic"],
                "motivations": ["help_party", "mutual_benefit", "moral_duty", "friendship"],
                "typical_goals": ["provide_aid", "share_information", "offer_resources"],
                "interaction_styles": ["direct", "warm", "encouraging"],
                "trust_levels": ["trusting", "cautious_but_willing"]
            },
            "neutral": {
                "attitudes": ["indifferent", "curious", "cautious", "professional"],
                "motivations": ["self_interest", "job_duty", "curiosity", "fair_trade"],
                "typical_goals": ["complete_transaction", "gather_information", "avoid_trouble"],
                "interaction_styles": ["businesslike", "formal", "reserved"],
                "trust_levels": ["cautious", "transactional"]
            },
            "rival": {
                "attitudes": ["competitive", "dismissive", "challenging", "smug"],
                "motivations": ["prove_superiority", "win_at_all_costs", "gain_recognition"],
                "typical_goals": ["outperform_party", "claim_credit", "undermine_efforts"],
                "interaction_styles": ["boastful", "condescending", "provocative"],
                "trust_levels": ["suspicious", "unreliable"]
            },
            "enemy": {
                "attitudes": ["hostile", "threatening", "contemptuous", "angry"],
                "motivations": ["harm_party", "revenge", "ideology", "orders"],
                "typical_goals": ["defeat_party", "steal_resources", "cause_suffering"],
                "interaction_styles": ["aggressive", "intimidating", "deceptive"],
                "trust_levels": ["untrustworthy", "dangerous"]
            },
            "informant": {
                "attitudes": ["secretive", "nervous", "calculating", "paranoid"],
                "motivations": ["payment", "safety", "revenge", "ideology"],
                "typical_goals": ["sell_information", "stay_hidden", "manipulate_events"],
                "interaction_styles": ["whispered", "indirect", "coded"],
                "trust_levels": ["paranoid", "transactional"]
            },
            "merchant": {
                "attitudes": ["greedy", "shrewd", "friendly", "opportunistic"],
                "motivations": ["profit", "reputation", "market_expansion", "survival"],
                "typical_goals": ["make_sale", "build_relationship", "gather_market_intel"],
                "interaction_styles": ["persuasive", "haggling", "sociable"],
                "trust_levels": ["business_focused", "profit_motivated"]
            },
            "authority": {
                "attitudes": ["authoritative", "bureaucratic", "suspicious", "duty_bound"],
                "motivations": ["maintain_order", "follow_protocol", "protect_citizens"],
                "typical_goals": ["enforce_law", "investigate_crime", "maintain_stability"],
                "interaction_styles": ["formal", "interrogative", "commanding"],
                "trust_levels": ["by_the_book", "evidence_based"]
            },
            "commoner": {
                "attitudes": ["fearful", "curious", "gossipy", "humble"],
                "motivations": ["safety", "family", "community", "survival"],
                "typical_goals": ["avoid_trouble", "help_neighbors", "live_peacefully"],
                "interaction_styles": ["simple", "honest", "emotional"],
                "trust_levels": ["naive", "community_minded"]
            },
            "expert": {
                "attitudes": ["knowledgeable", "passionate", "eccentric", "focused"],
                "motivations": ["advance_knowledge", "solve_problems", "recognition"],
                "typical_goals": ["share_expertise", "learn_new_things", "solve_mysteries"],
                "interaction_styles": ["technical", "enthusiastic", "detailed"],
                "trust_levels": ["evidence_based", "peer_respect"]
            },
            "noble": {
                "attitudes": ["entitled", "refined", "condescending", "political"],
                "motivations": ["status", "power", "family_honor", "political_gain"],
                "typical_goals": ["maintain_position", "gain_influence", "family_agenda"],
                "interaction_styles": ["formal", "diplomatic", "manipulative"],
                "trust_levels": ["politically_motivated", "class_conscious"]
            },
            "criminal": {
                "attitudes": ["suspicious", "opportunistic", "streetwise", "desperate"],
                "motivations": ["survival", "profit", "freedom", "revenge"],
                "typical_goals": ["avoid_law", "make_money", "protect_territory"],
                "interaction_styles": ["guarded", "street_smart", "threatening"],
                "trust_levels": ["honor_among_thieves", "self_preservation"]
            }
        }
    
    def _load_social_situations(self) -> Dict[str, Dict[str, Any]]:
        """Load social situation templates"""
        return {
            "negotiation": {
                "description": "Parties must reach an agreement through discussion",
                "common_stakes": ["payment", "services", "information", "alliances"],
                "complications": ["time_pressure", "competing_interests", "hidden_agendas"],
                "success_metrics": ["full_agreement", "partial_compromise", "future_deal"]
            },
            "interrogation": {
                "description": "Extract information from reluctant or hostile subject",
                "common_stakes": ["critical_information", "confession", "location_details"],
                "complications": ["lies_and_deception", "legal_constraints", "time_limits"],
                "success_metrics": ["full_truth", "partial_information", "leads_only"]
            },
            "persuasion": {
                "description": "Convince someone to change their mind or take action",
                "common_stakes": ["change_allegiance", "provide_help", "ignore_crime"],
                "complications": ["strong_beliefs", "personal_interests", "fear"],
                "success_metrics": ["complete_conversion", "temporary_agreement", "consideration"]
            },
            "deception": {
                "description": "Mislead others while avoiding detection",
                "common_stakes": ["false_identity", "fake_credentials", "misdirection"],
                "complications": ["contradictory_evidence", "suspicious_observers", "time_pressure"],
                "success_metrics": ["complete_belief", "temporary_acceptance", "doubt_avoided"]
            },
            "intimidation": {
                "description": "Use fear or threats to achieve compliance",
                "common_stakes": ["extract_information", "force_compliance", "create_fear"],
                "complications": ["moral_objections", "legal_consequences", "retaliation"],
                "success_metrics": ["complete_submission", "reluctant_compliance", "temporary_fear"]
            },
            "diplomacy": {
                "description": "Formal negotiations between groups or factions",
                "common_stakes": ["peace_treaty", "trade_agreement", "territorial_rights"],
                "complications": ["historical_grievances", "cultural_differences", "hidden_agendas"],
                "success_metrics": ["lasting_agreement", "temporary_peace", "framework_established"]
            },
            "courtly_intrigue": {
                "description": "Navigate complex social politics and hidden agendas",
                "common_stakes": ["political_favor", "information_gathering", "alliance_building"],
                "complications": ["multiple_factions", "changing_loyalties", "social_protocols"],
                "success_metrics": ["major_influence", "useful_connections", "avoided_scandal"]
            },
            "public_speaking": {
                "description": "Address a crowd or assembly to influence opinion",
                "common_stakes": ["public_opinion", "call_to_action", "reputation"],
                "complications": ["hostile_audience", "competing_speakers", "interruptions"],
                "success_metrics": ["crowd_converted", "neutral_reception", "avoided_riot"]
            }
        }
    
    def _load_negotiation_frameworks(self) -> Dict[str, Dict[str, Any]]:
        """Load negotiation structure templates"""
        return {
            "simple_trade": {
                "structure": ["opening_offer", "counteroffer", "final_terms"],
                "typical_rounds": 3,
                "key_factors": ["price", "quality", "timing"],
                "resolution_methods": ["split_difference", "added_value", "future_promise"]
            },
            "complex_bargain": {
                "structure": ["position_statements", "interest_exploration", "option_generation", "agreement"],
                "typical_rounds": 5,
                "key_factors": ["multiple_issues", "relationship_building", "long_term_impact"],
                "resolution_methods": ["package_deal", "contingent_agreement", "staged_implementation"]
            },
            "crisis_negotiation": {
                "structure": ["establish_contact", "build_rapport", "address_demands", "resolution"],
                "typical_rounds": 4,
                "key_factors": ["safety", "time_pressure", "emotional_state"],
                "resolution_methods": ["concession_trading", "face_saving", "third_party_mediation"]
            },
            "diplomatic_summit": {
                "structure": ["formal_opening", "position_presentations", "private_consultations", "public_agreement"],
                "typical_rounds": 6,
                "key_factors": ["protocol", "public_perception", "multiple_stakeholders"],
                "resolution_methods": ["framework_agreement", "phased_implementation", "ongoing_dialogue"]
            }
        }
    
    def _load_relationship_dynamics(self) -> Dict[str, List[str]]:
        """Load relationship dynamic modifiers"""
        return {
            "positive_modifiers": [
                "shared_values", "mutual_respect", "common_enemy", "past_favors",
                "family_connections", "guild_membership", "cultural_affinity"
            ],
            "negative_modifiers": [
                "historical_conflict", "cultural_prejudice", "economic_competition",
                "personal_grudge", "ideological_differences", "resource_scarcity"
            ],
            "neutral_modifiers": [
                "professional_relationship", "transactional_history", "mutual_acquaintances",
                "geographic_neighbors", "similar_backgrounds", "parallel_interests"
            ]
        }
    
    async def generate_social_encounter(self, encounter_type: str = "negotiation",
                                      complexity: str = "moderate", party_level: int = 5,
                                      num_npcs: int = 1) -> SocialEncounter:
        """Generate a social encounter"""
        
        # Get situation template
        situation = self.social_situations.get(encounter_type, self.social_situations["negotiation"])
        
        # Create base encounter
        encounter = SocialEncounter(
            name=f"{encounter_type.title()} Encounter",
            description=situation["description"],
            social_complexity=complexity,
            party_level=party_level,
            estimated_duration=30 + (15 * SOCIAL_CONFIG["social_complexities"][complexity]["participants"])
        )
        
        # Generate NPCs
        npcs = await self._generate_encounter_npcs(num_npcs, encounter_type, complexity)
        if npcs:
            encounter.main_npc = npcs[0]
            encounter.supporting_npcs = npcs[1:] if len(npcs) > 1 else []
        
        # Set NPC goals and relationships
        encounter.npc_goals = await self._generate_npc_goals(npcs, encounter_type)
        encounter.npc_relationships = await self._generate_npc_relationships(npcs)
        
        # Set starting attitudes
        encounter.starting_attitudes = await self._generate_starting_attitudes(npcs, encounter_type)
        
        # Generate interaction mechanics
        encounter.skill_challenges = await self._generate_social_skill_challenges(
            encounter_type, complexity, party_level
        )
        
        # Set conversation topics and information
        encounter.conversation_topics = await self._generate_conversation_topics(encounter_type)
        encounter.information_available = await self._generate_available_information(npcs, encounter_type)
        
        # Generate potential outcomes
        encounter.negotiation_outcomes = await self._generate_negotiation_outcomes(encounter_type, situation)
        encounter.relationship_changes = await self._generate_relationship_changes(encounter_type)
        
        # Set objectives
        encounter.primary_objective = self._generate_primary_objective(encounter_type, situation)
        encounter.secondary_objectives = situation.get("success_metrics", [])
        
        # Add complications
        if complexity != "simple":
            encounter.special_conditions.extend(
                self.rng.sample(situation.get("complications", []), 
                               min(2, len(situation.get("complications", []))))
            )
        
        # Generate read-aloud text
        encounter.read_aloud_text = await self._generate_read_aloud_text(encounter, encounter_type)
        
        # Add DM notes
        encounter.dm_notes = await self._generate_social_dm_notes(encounter, encounter_type)
        
        return encounter
    
    async def _generate_encounter_npcs(self, num_npcs: int, encounter_type: str,
                                     complexity: str) -> List[StatBlock]:
        """Generate NPCs for the social encounter"""
        npcs = []
        
        # Determine NPC archetypes based on encounter type
        archetype_preferences = {
            "negotiation": ["merchant", "authority", "expert", "rival"],
            "interrogation": ["criminal", "informant", "enemy", "commoner"],
            "persuasion": ["neutral", "authority", "commoner", "expert"],
            "deception": ["authority", "merchant", "expert", "rival"],
            "intimidation": ["criminal", "enemy", "commoner", "informant"],
            "diplomacy": ["authority", "noble", "expert", "rival"],
            "courtly_intrigue": ["noble", "authority", "rival", "informant"],
            "public_speaking": ["commoner", "authority", "rival", "ally"]
        }
        
        preferred_archetypes = archetype_preferences.get(encounter_type, ["neutral", "ally", "rival"])
        
        for i in range(num_npcs):
            # Select archetype
            if i == 0:  # Main NPC
                archetype = self.rng.choice(preferred_archetypes[:2])  # Prefer first two
            else:  # Supporting NPCs
                archetype = self.rng.choice(preferred_archetypes)
            
            # Generate NPC
            npc = await self._generate_social_npc(archetype, encounter_type)
            npcs.append(npc)
        
        return npcs
    
    async def _generate_social_npc(self, archetype: str, encounter_type: str) -> StatBlock:
        """Generate a single NPC for social encounters"""
        archetype_data = self.npc_archetypes.get(archetype, self.npc_archetypes["neutral"])
        
        # Generate basic stats (social NPCs don't need full combat stats)
        npc = StatBlock(
            name=self.generate_name("fantasy"),
            size="medium",
            creature_type="humanoid",
            alignment=self._generate_alignment_for_archetype(archetype),
            armor_class=10 + self.rng.randint(0, 3),
            hit_points=self.rng.randint(4, 12),
            speed={"walk": 30}
        )
        
        # Generate ability scores (focus on social stats)
        if archetype in ["noble", "authority", "merchant"]:
            npc.charisma = self.rng.randint(14, 18)
            npc.intelligence = self.rng.randint(12, 16)
        elif archetype in ["expert", "informant"]:
            npc.intelligence = self.rng.randint(15, 18)
            npc.wisdom = self.rng.randint(13, 16)
        elif archetype in ["criminal", "enemy"]:
            npc.dexterity = self.rng.randint(13, 16)
            npc.charisma = self.rng.randint(10, 14)
        else:
            npc.charisma = self.rng.randint(10, 16)
            npc.wisdom = self.rng.randint(10, 16)
        
        # Set other abilities to reasonable values
        for attr in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            if not hasattr(npc, attr) or getattr(npc, attr) == 0:
                setattr(npc, attr, self.rng.randint(8, 14))
        
        # Add social skills
        social_skills = self._get_archetype_skills(archetype)
        for skill in social_skills:
            modifier = self.format_modifier(getattr(npc, self._get_skill_ability(skill)))
            npc.skills[skill] = int(modifier) + self.rng.randint(2, 6)
        
        # Add special abilities relevant to social encounters
        npc.special_abilities = self._generate_social_abilities(archetype)
        
        return npc
    
    def _generate_alignment_for_archetype(self, archetype: str) -> str:
        """Generate appropriate alignment for archetype"""
        alignment_tendencies = {
            "ally": ["lawful_good", "neutral_good", "chaotic_good"],
            "neutral": ["lawful_neutral", "true_neutral", "chaotic_neutral"],
            "rival": ["lawful_neutral", "chaotic_neutral", "lawful_evil"],
            "enemy": ["lawful_evil", "neutral_evil", "chaotic_evil"],
            "informant": ["chaotic_neutral", "neutral_evil", "chaotic_evil"],
            "merchant": ["lawful_neutral", "neutral_good", "lawful_evil"],
            "authority": ["lawful_good", "lawful_neutral", "lawful_evil"],
            "commoner": ["neutral_good", "lawful_neutral", "true_neutral"],
            "expert": ["lawful_neutral", "true_neutral", "chaotic_neutral"],
            "noble": ["lawful_neutral", "lawful_evil", "neutral_evil"],
            "criminal": ["chaotic_neutral", "chaotic_evil", "neutral_evil"]
        }
        
        alignments = alignment_tendencies.get(archetype, ["true_neutral"])
        return self.rng.choice(alignments)
    
    def _get_archetype_skills(self, archetype: str) -> List[SkillType]:
        """Get relevant skills for archetype"""
        archetype_skills = {
            "ally": [SkillType.PERSUASION, SkillType.INSIGHT],
            "neutral": [SkillType.INSIGHT, SkillType.PERCEPTION],
            "rival": [SkillType.DECEPTION, SkillType.INTIMIDATION],
            "enemy": [SkillType.INTIMIDATION, SkillType.DECEPTION],
            "informant": [SkillType.DECEPTION, SkillType.STEALTH],
            "merchant": [SkillType.PERSUASION, SkillType.DECEPTION],
            "authority": [SkillType.INTIMIDATION, SkillType.INSIGHT],
            "commoner": [SkillType.PERCEPTION, SkillType.SURVIVAL],
            "expert": [SkillType.INVESTIGATION, SkillType.HISTORY],
            "noble": [SkillType.PERSUASION, SkillType.HISTORY],
            "criminal": [SkillType.DECEPTION, SkillType.STEALTH]
        }
        
        return archetype_skills.get(archetype, [SkillType.INSIGHT, SkillType.PERCEPTION])
    
    def _get_skill_ability(self, skill: SkillType) -> str:
        """Get the ability score associated with a skill"""
        skill_abilities = {
            SkillType.DECEPTION: 'charisma',
            SkillType.INTIMIDATION: 'charisma',
            SkillType.PERSUASION: 'charisma',
            SkillType.PERFORMANCE: 'charisma',
            SkillType.INSIGHT: 'wisdom',
            SkillType.PERCEPTION: 'wisdom',
            SkillType.INVESTIGATION: 'intelligence',
            SkillType.HISTORY: 'intelligence',
            SkillType.STEALTH: 'dexterity',
            SkillType.SURVIVAL: 'wisdom'
        }
        return skill_abilities.get(skill, 'charisma')
    
    def _generate_social_abilities(self, archetype: str) -> List[Dict[str, str]]:
        """Generate social special abilities"""
        abilities_by_archetype = {
            "merchant": [
                {"name": "Silver Tongue", "description": "Advantage on Persuasion checks involving money or trade"},
                {"name": "Appraise", "description": "Can determine the value of items accurately"}
            ],
            "noble": [
                {"name": "Noble Bearing", "description": "Advantage on Charisma checks with lower social classes"},
                {"name": "Court Training", "description": "Proficient in etiquette and protocol"}
            ],
            "authority": [
                {"name": "Badge of Office", "description": "Can compel cooperation from citizens"},
                {"name": "Investigate", "description": "Advantage on Investigation checks for criminal activity"}
            ],
            "criminal": [
                {"name": "Streetwise", "description": "Advantage on checks to gather information in criminal areas"},
                {"name": "Thieves' Cant", "description": "Can communicate secretly with other criminals"}
            ],
            "expert": [
                {"name": "Specialized Knowledge", "description": "Expertise in specific subject area"},
                {"name": "Research", "description": "Can find information others cannot"}
            ],
            "informant": [
                {"name": "Secrets", "description": "Knows valuable but dangerous information"},
                {"name": "Paranoid", "description": "Advantage on Perception checks to detect surveillance"}
            ]
        }
        
        return abilities_by_archetype.get(archetype, [])
    
    async def _generate_npc_goals(self, npcs: List[StatBlock], encounter_type: str) -> Dict[str, str]:
        """Generate goals for each NPC"""
        goals = {}
        
        goal_templates = {
            "negotiation": ["get_best_deal", "maintain_relationship", "establish_precedent"],
            "interrogation": ["protect_secrets", "mislead_questioners", "minimize_damage"],
            "persuasion": ["maintain_position", "protect_interests", "avoid_commitment"],
            "deception": ["discover_truth", "avoid_being_fooled", "gather_information"],
            "intimidation": ["resist_pressure", "protect_others", "maintain_dignity"],
            "diplomacy": ["advance_faction_interests", "prevent_conflict", "gain_concessions"]
        }
        
        available_goals = goal_templates.get(encounter_type, ["achieve_objective"])
        
        for npc in npcs:
            goals[npc.name] = self.rng.choice(available_goals)
        
        return goals
    
    async def _generate_npc_relationships(self, npcs: List[StatBlock]) -> Dict[str, str]:
        """Generate relationships between NPCs"""
        relationships = {}
        
        if len(npcs) < 2:
            return relationships
        
        relationship_types = [
            "allies", "rivals", "neutral", "superior_subordinate", 
            "old_friends", "former_enemies", "family_relation", "business_partners"
        ]
        
        # Generate relationships for pairs
        for i, npc1 in enumerate(npcs):
            for npc2 in npcs[i+1:]:
                relationship = self.rng.choice(relationship_types)
                relationships[f"{npc1.name}-{npc2.name}"] = relationship
        
        return relationships
    
    async def _generate_starting_attitudes(self, npcs: List[StatBlock], 
                                         encounter_type: str) -> Dict[str, str]:
        """Generate starting attitudes toward the party"""
        attitudes = {}
        
        attitude_options = {
            "negotiation": ["neutral", "cautious", "interested", "skeptical"],
            "interrogation": ["defensive", "hostile", "fearful", "defiant"],
            "persuasion": ["skeptical", "resistant", "curious", "dismissive"],
            "deception": ["suspicious", "trusting", "analytical", "distracted"],
            "intimidation": ["defiant", "fearful", "angry", "protective"],
            "diplomacy": ["formal", "cautious", "hopeful", "rigid"]
        }
        
        available_attitudes = attitude_options.get(encounter_type, ["neutral", "cautious"])
        
        for npc in npcs:
            attitudes[npc.name] = self.rng.choice(available_attitudes)
        
        return attitudes
    
    async def _generate_social_skill_challenges(self, encounter_type: str,
                                              complexity: str, party_level: int) -> List[SkillCheck]:
        """Generate skill challenges for the social encounter"""
        skill_challenges = []
        
        # Base DC calculation
        base_dc = 10 + party_level // 2
        complexity_modifier = {"simple": 0, "moderate": 2, "complex": 4}.get(complexity, 2)
        final_dc = base_dc + complexity_modifier
        
        # Skills relevant to encounter type
        encounter_skills = {
            "negotiation": [SkillType.PERSUASION, SkillType.INSIGHT, SkillType.DECEPTION],
            "interrogation": [SkillType.INTIMIDATION, SkillType.INSIGHT, SkillType.INVESTIGATION],
            "persuasion": [SkillType.PERSUASION, SkillType.PERFORMANCE, SkillType.DECEPTION],
            "deception": [SkillType.DECEPTION, SkillType.PERFORMANCE, SkillType.SLEIGHT_OF_HAND],
            "intimidation": [SkillType.INTIMIDATION, SkillType.PERCEPTION, SkillType.ATHLETICS],
            "diplomacy": [SkillType.PERSUASION, SkillType.HISTORY, SkillType.INSIGHT]
        }
        
        relevant_skills = encounter_skills.get(encounter_type, [SkillType.PERSUASION, SkillType.INSIGHT])
        
        # Generate 2-4 skill challenges based on complexity
        num_challenges = {"simple": 2, "moderate": 3, "complex": 4}.get(complexity, 3)
        
        for i in range(num_challenges):
            skill = self.rng.choice(relevant_skills)
            
            challenge = SkillCheck(
                skill=skill,
                dc=final_dc + self.rng.randint(-2, 2),  # Add some variance
                description=self._get_skill_challenge_description(skill, encounter_type),
                success_description=f"Successfully uses {skill.value} to advance the encounter",
                failure_description=f"The {skill.value} attempt doesn't go as planned"
            )
            
            skill_challenges.append(challenge)
        
        return skill_challenges
    
    def _get_skill_challenge_description(self, skill: SkillType, encounter_type: str) -> str:
        """Get description for skill challenge"""
        descriptions = {
            SkillType.PERSUASION: f"Convince the NPCs through reasoning and charm during this {encounter_type}",
            SkillType.DECEPTION: f"Mislead or misdirect the NPCs during this {encounter_type}",
            SkillType.INTIMIDATION: f"Use threats or force of presence during this {encounter_type}",
            SkillType.INSIGHT: f"Read the NPCs' true intentions during this {encounter_type}",
            SkillType.INVESTIGATION: f"Analyze evidence or clues during this {encounter_type}",
            SkillType.PERFORMANCE: f"Use acting or presentation skills during this {encounter_type}",
            SkillType.HISTORY: f"Draw upon historical knowledge relevant to this {encounter_type}",
            SkillType.PERCEPTION: f"Notice important details during this {encounter_type}"
        }
        
        return descriptions.get(skill, f"Use {skill.value} effectively in this {encounter_type}")
    
    async def _generate_conversation_topics(self, encounter_type: str) -> List[str]:
        """Generate conversation topics"""
        topic_categories = {
            "negotiation": ["terms", "prices", "conditions", "timelines", "guarantees"],
            "interrogation": ["whereabouts", "accomplices", "motives", "methods", "evidence"],
            "persuasion": ["benefits", "consequences", "alternatives", "personal_stakes", "moral_arguments"],
            "deception": ["false_identity", "fabricated_story", "misleading_evidence", "fake_credentials"],
            "intimidation": ["threats", "consequences", "power_demonstration", "past_examples"],
            "diplomacy": ["treaties", "trade_agreements", "territorial_disputes", "mutual_benefits"]
        }
        
        topics = topic_categories.get(encounter_type, ["general_discussion", "mutual_interests"])
        return self.rng.sample(topics, min(4, len(topics)))
    
    async def _generate_available_information(self, npcs: List[StatBlock],
                                            encounter_type: str) -> Dict[str, List[str]]:
        """Generate information that NPCs possess"""
        information = {}
        
        info_categories = {
            "local_knowledge": ["area_layout", "recent_events", "important_people", "local_customs"],
            "secret_information": ["hidden_passages", "secret_alliances", "criminal_activities", "conspiracies"],
            "professional_knowledge": ["trade_routes", "guild_politics", "technical_expertise", "historical_events"],
            "personal_information": ["family_connections", "personal_grudges", "private_affairs", "individual_goals"]
        }
        
        for npc in npcs:
            npc_info = []
            
            # Each NPC knows 2-4 pieces of information
            num_info = self.rng.randint(2, 4)
            for _ in range(num_info):
                category = self.rng.choice(list(info_categories.keys()))
                specific_info = self.rng.choice(info_categories[category])
                npc_info.append(specific_info)
            
            information[npc.name] = npc_info
        
        return information
    
    async def _generate_negotiation_outcomes(self, encounter_type: str,
                                           situation: Dict[str, Any]) -> Dict[str, str]:
        """Generate possible outcomes"""
        outcomes = {}
        
        success_levels = ["complete_success", "partial_success", "minimal_success", "failure"]
        
        for level in success_levels:
            if level == "complete_success":
                outcomes[level] = "All objectives achieved with bonus benefits"
            elif level == "partial_success":
                outcomes[level] = "Primary objectives achieved with minor compromises"
            elif level == "minimal_success":
                outcomes[level] = "Some objectives achieved but at significant cost"
            else:
                outcomes[level] = "Objectives not achieved, relationship damaged"
        
        return outcomes
    
    async def _generate_relationship_changes(self, encounter_type: str) -> Dict[str, str]:
        """Generate how relationships change based on outcomes"""
        return {
            "great_success": "Relationship significantly improved, future benefits",
            "success": "Relationship improved, neutral to positive",
            "partial_success": "Relationship maintained, slight improvement",
            "failure": "Relationship damaged, future complications",
            "critical_failure": "Relationship severely damaged, active hostility"
        }
    
    def _generate_primary_objective(self, encounter_type: str, 
                                   situation: Dict[str, Any]) -> str:
        """Generate primary objective for the encounter"""
        objective_templates = {
            "negotiation": "Reach a mutually beneficial agreement",
            "interrogation": "Extract crucial information from the subject",
            "persuasion": "Convince the NPC to change their position",
            "deception": "Successfully mislead the NPC without detection",
            "intimidation": "Use fear to compel compliance",
            "diplomacy": "Establish formal agreement between parties",
            "courtly_intrigue": "Navigate court politics to achieve goals",
            "public_speaking": "Win over the crowd to your cause"
        }
        
        return objective_templates.get(encounter_type, "Achieve positive outcome through social interaction")
    
    async def _generate_read_aloud_text(self, encounter: SocialEncounter, 
                                      encounter_type: str) -> str:
        """Generate descriptive text for the encounter"""
        
        setting_descriptions = {
            "negotiation": "You find yourselves seated across from",
            "interrogation": "The subject sits before you, clearly",
            "persuasion": "The person before you appears",
            "deception": "As you approach with your fabricated story,",
            "intimidation": "Your target looks up as you loom over them,",
            "diplomacy": "The formal meeting chamber holds an air of",
            "courtly_intrigue": "The elegant court setting masks the",
            "public_speaking": "The gathered crowd turns their attention toward you,"
        }
        
        mood_descriptors = {
            "negotiation": "businesslike tension",
            "interrogation": "nervous and defensive", 
            "persuasion": "skeptical but curious",
            "deception": "unsuspecting of your true motives",
            "intimidation": "fearful but defiant",
            "diplomacy": "formal importance and ceremony",
            "courtly_intrigue": "underlying tensions and hidden agendas",
            "public_speaking": "mixture of curiosity and skepticism"
        }
        
        base_text = setting_descriptions.get(encounter_type, "You encounter")
        mood = mood_descriptors.get(encounter_type, "tension")
        
        npc_name = encounter.main_npc.name if encounter.main_npc else "the NPC"
        
        return f"{base_text} {npc_name}, and you sense an atmosphere of {mood}. The social dynamics here will require careful navigation to achieve your goals."
    
    async def _generate_social_dm_notes(self, encounter: SocialEncounter, 
                                      encounter_type: str) -> List[str]:
        """Generate helpful DM notes"""
        notes = [
            f"This is a {encounter.social_complexity} {encounter_type} encounter",
            f"Estimated duration: {encounter.estimated_duration} minutes"
        ]
        
        if encounter.main_npc:
            notes.append(f"Main NPC: {encounter.main_npc.name} (primary negotiator)")
        
        if encounter.supporting_npcs:
            npc_names = [npc.name for npc in encounter.supporting_npcs]
            notes.append(f"Supporting NPCs: {', '.join(npc_names)}")
        
        # Add encounter-specific notes
        encounter_notes = {
            "negotiation": [
                "Track concessions made by each side",
                "Allow creative solutions beyond obvious trades",
                "Consider long-term relationship impact"
            ],
            "interrogation": [
                "NPCs may lie, misdirect, or withhold information",
                "Consider legal and moral implications",
                "Allow multiple approaches (good cop/bad cop, etc.)"
            ],
            "persuasion": [
                "Focus on NPC motivations and values",
                "Allow multiple arguments to build cumulative effect",
                "Consider emotional appeals alongside logical ones"
            ],
            "deception": [
                "Track consistency of false story",
                "NPCs may become suspicious of contradictions",
                "Allow Insight checks to detect lies"
            ]
        }
        
        if encounter_type in encounter_notes:
            notes.extend(encounter_notes[encounter_type][:2])  # Add 2 specific notes
        
        return notes