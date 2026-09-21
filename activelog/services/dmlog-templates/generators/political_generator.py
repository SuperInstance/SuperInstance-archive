"""
Political intrigue generator for faction-based scenarios
"""

from typing import List, Optional, Dict, Any
from ..models.base import BaseTemplate, ComplexityLevel, DifficultyLevel
from ..models.political import (
    PoliticalIntrigue, Faction, Plot, Agenda, PoliticalEvent, 
    Blackmail, Scandal
)
from ..models.character import NPCProfile
from .base_generator import BaseGenerator
from .character_generator import CharacterGenerator
from ..config import POLITICAL_CONFIG


class PoliticalGenerator(BaseGenerator):
    """Generates political intrigue scenarios with factions, plots, and schemes"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.character_generator = CharacterGenerator(seed)
    
    async def generate_political_intrigue(self, 
                                        scope: str = "local",
                                        complexity: str = "moderate",
                                        party_level: int = 8,
                                        faction_count: int = 4) -> PoliticalIntrigue:
        """Generate a complete political intrigue scenario"""
        
        intrigue_config = POLITICAL_CONFIG["intrigue_scopes"].get(scope, 
                                                                POLITICAL_CONFIG["intrigue_scopes"]["local"])
        
        # Generate major factions
        factions = await self._generate_factions(
            scope, faction_count, party_level, complexity
        )
        
        # Generate key individuals
        key_individuals = await self._generate_key_individuals(
            factions, party_level
        )
        
        # Generate central conflict
        core_dispute, competing_interests = self._generate_central_conflict(
            factions, scope
        )
        
        # Generate plots and schemes
        major_plots = await self._generate_major_plots(
            factions, key_individuals, complexity, party_level
        )
        
        # Generate political events
        current_crisis = self._generate_current_crisis(scope, factions)
        
        # Generate player involvement opportunities
        entry_points = self._generate_entry_points(factions, major_plots)
        potential_roles = self._generate_potential_roles(scope, complexity)
        
        intrigue = PoliticalIntrigue(
            name=f"{scope.title()} Political Intrigue: {core_dispute}",
            description=f"A {complexity} political scenario involving {faction_count} major factions",
            intrigue_scope=scope,
            political_system=intrigue_config.get("political_system", "monarchy"),
            current_crisis=current_crisis,
            background_tensions=self._generate_background_tensions(scope),
            major_factions=factions,
            key_individuals=key_individuals,
            power_brokers=self._select_power_brokers(key_individuals),
            core_dispute=core_dispute,
            competing_interests=competing_interests,
            irreconcilable_differences=self._generate_irreconcilable_differences(factions),
            major_plots=major_plots,
            minor_schemes=self._generate_minor_schemes(factions, complexity),
            counter_intelligence=self._generate_counter_intelligence(factions),
            propaganda_campaigns=self._generate_propaganda_campaigns(factions),
            disinformation=self._generate_disinformation(factions, major_plots),
            intelligence_networks=self._assess_intelligence_networks(factions),
            immediate_stakes=self._generate_immediate_stakes(core_dispute, scope),
            long_term_consequences=self._generate_long_term_consequences(scope, major_plots),
            potential_for_violence=self._assess_violence_potential(factions, major_plots),
            entry_points=entry_points,
            potential_roles=potential_roles,
            moral_dilemmas=self._generate_moral_dilemmas(factions, major_plots),
            peaceful_solutions=self._generate_peaceful_solutions(core_dispute, factions),
            violent_resolutions=self._generate_violent_resolutions(factions),
            compromise_options=self._generate_compromise_options(factions, competing_interests),
            ties_to_main_plot=self._generate_main_plot_ties(scope),
            recurring_consequences=self._generate_recurring_consequences(major_plots),
            future_intrigue_seeds=self._generate_future_seeds(factions, major_plots),
            tags=[scope, complexity, f"level_{party_level}", f"factions_{faction_count}"]
        )
        
        return intrigue
    
    async def _generate_factions(self, 
                               scope: str, 
                               faction_count: int,
                               party_level: int,
                               complexity: str) -> List[Faction]:
        """Generate major factions for the intrigue"""
        
        factions = []
        faction_templates = POLITICAL_CONFIG["faction_templates"].get(scope, 
                                                                    POLITICAL_CONFIG["faction_templates"]["local"])
        
        # Ensure variety in faction types
        faction_types = list(faction_templates.keys())
        selected_types = self.rng.sample(faction_types, min(len(faction_types), faction_count))
        
        # Add more types if needed
        while len(selected_types) < faction_count:
            selected_types.append(self.rng.choice(faction_types))
        
        for i, faction_type in enumerate(selected_types):
            template = faction_templates[faction_type]
            
            # Generate leaders for the faction
            leaders = []
            for j in range(self.rng.randint(1, 3)):
                leader = await self.character_generator.generate_npc(
                    f"{template['name']} Leader {j+1}",
                    party_level=party_level
                )
                leader.role = template.get("leader_role", "leader")
                leaders.append(leader)
            
            faction = Faction(
                name=template["name"] + (f" #{i+1}" if faction_count > len(faction_types) else ""),
                description=template["description"],
                faction_type=faction_type,
                public_face=template["public_face"],
                true_nature=template.get("true_nature", template["public_face"]),
                founding_principles=template.get("principles", []),
                current_goals=self._generate_faction_goals(template, scope),
                power_level=self._determine_power_level(i, faction_count),
                influence_areas=template.get("influence_areas", []),
                resources=template.get("resources", {}),
                leadership_structure=template.get("leadership", "hierarchical"),
                key_leaders=leaders,
                total_members=template.get("member_count", 100) * (1 + party_level // 5),
                active_agents=template.get("agent_count", 10) * (1 + party_level // 8),
                current_schemes=self._generate_faction_schemes(template, complexity),
                intelligence_network=template.get("intelligence", "limited"),
                military_capability=template.get("military", "none"),
                public_secrets=template.get("public_secrets", []),
                hidden_secrets=template.get("hidden_secrets", []),
                deep_secrets=template.get("deep_secrets", []),
                vulnerabilities=template.get("vulnerabilities", []),
                preferred_methods=template.get("methods", []),
                moral_boundaries=template.get("moral_limits", []),
                taboo_actions=template.get("taboos", []),
                public_support=template.get("support_level", "mixed"),
                tags=[faction_type, scope, f"power_{self._determine_power_level(i, faction_count)}"]
            )
            
            factions.append(faction)
        
        # Generate relationships between factions
        self._establish_faction_relationships(factions)
        
        return factions
    
    async def _generate_key_individuals(self, 
                                      factions: List[Faction],
                                      party_level: int) -> List[NPCProfile]:
        """Generate key individuals beyond faction leaders"""
        
        individuals = []
        
        # Collect all faction leaders
        for faction in factions:
            individuals.extend(faction.key_leaders)
        
        # Add independent power brokers
        power_broker_templates = POLITICAL_CONFIG["power_brokers"]
        for i in range(self.rng.randint(2, 4)):
            template = self.rng.choice(power_broker_templates)
            
            power_broker = await self.character_generator.generate_npc(
                template["name"] + f" #{i+1}",
                party_level=party_level
            )
            power_broker.role = template["role"]
            power_broker.description = template["description"]
            power_broker.influence_type = template.get("influence", "social")
            power_broker.tags.extend(["power_broker", "independent"])
            
            individuals.append(power_broker)
        
        return individuals
    
    def _generate_central_conflict(self, 
                                 factions: List[Faction],
                                 scope: str) -> tuple[str, Dict[str, str]]:
        """Generate the central conflict and competing interests"""
        
        conflict_templates = POLITICAL_CONFIG["central_conflicts"].get(scope,
                                                                     POLITICAL_CONFIG["central_conflicts"]["local"])
        
        conflict = self.rng.choice(conflict_templates)
        
        # Generate competing interests
        competing_interests = {}
        for faction in factions:
            interests = conflict.get("faction_interests", {}).get(faction.faction_type, 
                                                                ["maintain status quo"])
            competing_interests[faction.name] = self.rng.choice(interests)
        
        return conflict["name"], competing_interests
    
    async def _generate_major_plots(self, 
                                  factions: List[Faction],
                                  key_individuals: List[NPCProfile],
                                  complexity: str,
                                  party_level: int) -> List[Plot]:
        """Generate major plots and schemes"""
        
        plots = []
        plot_count = {"simple": 2, "moderate": 3, "complex": 4, "epic": 5}.get(complexity, 3)
        
        plot_templates = POLITICAL_CONFIG["plot_templates"]
        
        for i in range(plot_count):
            template = self.rng.choice(plot_templates)
            mastermind_faction = self.rng.choice(factions)
            mastermind = self.rng.choice(mastermind_faction.key_leaders)
            
            # Select conspirators from same or allied factions
            conspirators = []
            potential_conspirators = [ind for ind in key_individuals 
                                    if ind.id != mastermind.id and 
                                    ind not in mastermind_faction.key_leaders]
            conspirators.extend(self.rng.sample(potential_conspirators, 
                                              min(len(potential_conspirators), 2)))
            
            # Select unwitting pawns and obstacles
            remaining_individuals = [ind for ind in key_individuals 
                                   if ind not in conspirators and ind.id != mastermind.id]
            pawns = self.rng.sample(remaining_individuals, 
                                  min(len(remaining_individuals), 2))
            
            obstacles = [f.name for f in factions if f.id != mastermind_faction.id][:2]
            
            plot = Plot(
                name=template["name"] + f" - {mastermind.name}",
                description=template["description"],
                plot_type=template["type"],
                primary_goal=template["primary_goal"],
                secondary_goals=template.get("secondary_goals", []),
                ultimate_objective=template.get("ultimate_objective", ""),
                mastermind=mastermind.id,
                conspirators=[c.id for c in conspirators],
                unwitting_pawns=[p.id for p in pawns],
                potential_obstacles=obstacles,
                complexity=ComplexityLevel(complexity),
                phases=self._generate_plot_phases(template, complexity),
                contingency_plans=template.get("contingencies", []),
                preparation_time=template.get("prep_time", "months"),
                execution_window=template.get("window", "narrow"),
                time_pressure=template.get("pressure", "moderate"),
                resources_needed=template.get("resources", {}),
                permissions_required=template.get("permissions", []),
                information_needed=template.get("information", []),
                exposure_risks=template.get("risks", []),
                security_measures=template.get("security", []),
                failure_consequences=template.get("failure", []),
                early_warning_signs=template.get("warning_signs", []),
                investigation_difficulty=template.get("investigation", "moderate"),
                evidence_trail=template.get("evidence", []),
                success_indicators=template.get("success", []),
                partial_success_outcomes=template.get("partial", []),
                failure_outcomes=template.get("failure_outcomes", []),
                world_changing_potential=template.get("impact", "moderate"),
                future_complications=template.get("complications", []),
                sequel_hooks=template.get("hooks", []),
                tags=[template["type"], complexity, mastermind_faction.name]
            )
            
            plots.append(plot)
        
        return plots
    
    def _generate_faction_goals(self, template: Dict, scope: str) -> List[str]:
        """Generate current goals for a faction"""
        
        base_goals = template.get("current_goals", [])
        scope_goals = POLITICAL_CONFIG["scope_specific_goals"].get(scope, [])
        
        all_goals = base_goals + scope_goals
        return self.rng.sample(all_goals, min(len(all_goals), 3))
    
    def _determine_power_level(self, faction_index: int, total_factions: int) -> str:
        """Determine power level for faction based on position"""
        
        power_levels = ["dominant", "major", "moderate", "minor", "minimal"]
        
        # Distribute power levels
        if faction_index == 0:
            return "major"
        elif faction_index == 1 and total_factions > 2:
            return "moderate"
        elif faction_index < total_factions - 1:
            return "moderate"
        else:
            return "minor"
    
    def _generate_faction_schemes(self, template: Dict, complexity: str) -> List[str]:
        """Generate current schemes for a faction"""
        
        base_schemes = template.get("schemes", [])
        scheme_count = {"simple": 1, "moderate": 2, "complex": 3, "epic": 4}.get(complexity, 2)
        
        return self.rng.sample(base_schemes, min(len(base_schemes), scheme_count))
    
    def _establish_faction_relationships(self, factions: List[Faction]) -> None:
        """Establish relationships between factions"""
        
        for i, faction in enumerate(factions):
            other_factions = [f for f in factions if f.id != faction.id]
            
            # Randomly assign relationships
            for other in other_factions:
                relationship = self.rng.choice(["allied", "rival", "enemy", "neutral"])
                
                if relationship == "allied":
                    faction.allied_factions.append(other.id)
                    other.allied_factions.append(faction.id)
                elif relationship == "rival":
                    faction.rival_factions.append(other.id)
                    other.rival_factions.append(faction.id)
                elif relationship == "enemy":
                    faction.enemy_factions.append(other.id)
                    other.enemy_factions.append(faction.id)
                else:
                    faction.neutral_relations.append(other.id)
                    other.neutral_relations.append(faction.id)
    
    def _generate_current_crisis(self, scope: str, factions: List[Faction]) -> str:
        """Generate current crisis driving the intrigue"""
        
        crisis_templates = POLITICAL_CONFIG["current_crises"].get(scope,
                                                               POLITICAL_CONFIG["current_crises"]["local"])
        
        crisis = self.rng.choice(crisis_templates)
        affected_faction = self.rng.choice(factions)
        
        return crisis.format(faction=affected_faction.name)
    
    def _generate_background_tensions(self, scope: str) -> List[str]:
        """Generate background tensions"""
        
        tensions = POLITICAL_CONFIG["background_tensions"].get(scope,
                                                             POLITICAL_CONFIG["background_tensions"]["local"])
        
        return self.rng.sample(tensions, min(len(tensions), 3))
    
    def _select_power_brokers(self, key_individuals: List[NPCProfile]) -> List[str]:
        """Select key power brokers from individuals"""
        
        power_brokers = [ind for ind in key_individuals 
                        if hasattr(ind, 'influence_type') or 'power_broker' in ind.tags]
        
        return [pb.id for pb in power_brokers[:3]]
    
    def _generate_irreconcilable_differences(self, factions: List[Faction]) -> List[str]:
        """Generate differences that cannot be resolved"""
        
        differences = [
            "Fundamental disagreement about governance",
            "Religious or ideological opposition",
            "Historical grievances cannot be forgiven",
            "Competing claims to same resources",
            "Mutually exclusive goals"
        ]
        
        return self.rng.sample(differences, min(len(differences), 2))
    
    def _generate_minor_schemes(self, factions: List[Faction], complexity: str) -> List[str]:
        """Generate minor schemes and plots"""
        
        minor_schemes = []
        scheme_count = {"simple": 2, "moderate": 4, "complex": 6, "epic": 8}.get(complexity, 4)
        
        scheme_templates = [
            "Spreading rumors about rival faction",
            "Intercepting communications",
            "Bribing key officials",
            "Sabotaging rival operations",
            "Recruiting double agents",
            "Organizing public demonstrations"
        ]
        
        for _ in range(scheme_count):
            faction = self.rng.choice(factions)
            scheme = self.rng.choice(scheme_templates)
            minor_schemes.append(f"{faction.name}: {scheme}")
        
        return minor_schemes
    
    def _generate_counter_intelligence(self, factions: List[Faction]) -> List[str]:
        """Generate counter-intelligence operations"""
        
        counter_ops = []
        
        for faction in factions:
            if faction.intelligence_network in ["moderate", "extensive"]:
                ops = [
                    f"{faction.name} monitors rival communications",
                    f"{faction.name} plants misinformation",
                    f"{faction.name} runs double agents",
                    f"{faction.name} conducts surveillance"
                ]
                counter_ops.extend(self.rng.sample(ops, 2))
        
        return counter_ops
    
    def _generate_propaganda_campaigns(self, factions: List[Faction]) -> List[str]:
        """Generate propaganda campaigns"""
        
        campaigns = []
        
        for faction in factions:
            campaign_themes = [
                f"Promoting {faction.name}'s legitimacy",
                f"Undermining rival factions' credibility",
                f"Rallying public support for their cause",
                f"Spreading fear about opposition"
            ]
            campaigns.append(self.rng.choice(campaign_themes))
        
        return campaigns
    
    def _generate_disinformation(self, factions: List[Faction], plots: List[Plot]) -> List[str]:
        """Generate disinformation campaigns"""
        
        disinfo = []
        
        for plot in plots:
            mastermind_faction = next((f for f in factions if plot.mastermind in [l.id for l in f.key_leaders]), None)
            if mastermind_faction:
                disinfo.append(f"False information about {plot.name} to cover tracks")
        
        return disinfo
    
    def _assess_intelligence_networks(self, factions: List[Faction]) -> Dict[str, str]:
        """Assess intelligence capabilities of factions"""
        
        networks = {}
        for faction in factions:
            networks[faction.name] = faction.intelligence_network
        
        return networks
    
    def _generate_immediate_stakes(self, core_dispute: str, scope: str) -> List[str]:
        """Generate immediate stakes"""
        
        stakes_templates = POLITICAL_CONFIG["immediate_stakes"].get(scope,
                                                                  POLITICAL_CONFIG["immediate_stakes"]["local"])
        
        return self.rng.sample(stakes_templates, min(len(stakes_templates), 3))
    
    def _generate_long_term_consequences(self, scope: str, plots: List[Plot]) -> List[str]:
        """Generate long-term consequences"""
        
        consequences = []
        
        for plot in plots:
            if plot.world_changing_potential in ["major", "world_shaking"]:
                consequences.extend(plot.future_complications)
        
        # Add scope-specific consequences
        scope_consequences = POLITICAL_CONFIG["long_term_consequences"].get(scope, [])
        consequences.extend(self.rng.sample(scope_consequences, 2))
        
        return consequences
    
    def _assess_violence_potential(self, factions: List[Faction], plots: List[Plot]) -> str:
        """Assess potential for violence"""
        
        violence_factors = 0
        
        # Check faction military capabilities
        for faction in factions:
            if faction.military_capability in ["professional", "elite"]:
                violence_factors += 2
            elif faction.military_capability == "militia":
                violence_factors += 1
        
        # Check plot types
        for plot in plots:
            if plot.plot_type in ["assassination", "coup", "revolution"]:
                violence_factors += 2
            elif plot.plot_type in ["sabotage", "blackmail"]:
                violence_factors += 1
        
        if violence_factors >= 6:
            return "inevitable"
        elif violence_factors >= 4:
            return "high"
        elif violence_factors >= 2:
            return "moderate"
        else:
            return "low"
    
    def _generate_entry_points(self, factions: List[Faction], plots: List[Plot]) -> List[str]:
        """Generate ways for players to get involved"""
        
        entry_points = [
            "Hired as neutral investigators",
            "Approached by faction seeking allies",
            "Witness to key event",
            "Possess information factions want",
            "Asked to mediate dispute",
            "Caught between competing factions",
            "Discover conspiracy by accident"
        ]
        
        return self.rng.sample(entry_points, min(len(entry_points), 4))
    
    def _generate_potential_roles(self, scope: str, complexity: str) -> List[str]:
        """Generate potential roles players can take"""
        
        base_roles = [
            "Mediators and negotiators",
            "Intelligence gatherers",
            "Double agents",
            "Faction representatives",
            "Independent investigators",
            "Power brokers"
        ]
        
        if complexity in ["complex", "epic"]:
            advanced_roles = [
                "Conspiracy masterminds",
                "Revolutionary leaders",
                "Shadow puppet masters"
            ]
            base_roles.extend(advanced_roles)
        
        return self.rng.sample(base_roles, min(len(base_roles), 4))
    
    def _generate_moral_dilemmas(self, factions: List[Faction], plots: List[Plot]) -> List[str]:
        """Generate moral dilemmas"""
        
        dilemmas = [
            "Supporting lesser evil vs greater evil",
            "Loyalty vs justice",
            "Individual rights vs collective good",
            "Truth vs stability",
            "Law vs morality",
            "Ends justify means dilemma"
        ]
        
        return self.rng.sample(dilemmas, min(len(dilemmas), 3))
    
    def _generate_peaceful_solutions(self, core_dispute: str, factions: List[Faction]) -> List[str]:
        """Generate peaceful resolution options"""
        
        solutions = [
            "Negotiate power-sharing agreement",
            "Establish neutral oversight body",
            "Create compromise solution",
            "Mediated settlement",
            "Democratic resolution process",
            "Third-party arbitration"
        ]
        
        return self.rng.sample(solutions, min(len(solutions), 3))
    
    def _generate_violent_resolutions(self, factions: List[Faction]) -> List[str]:
        """Generate violent resolution scenarios"""
        
        resolutions = [
            "Open warfare between factions",
            "Coup attempt",
            "Assassination of key leaders",
            "Popular uprising",
            "Military intervention",
            "Revolutionary overthrow"
        ]
        
        return self.rng.sample(resolutions, min(len(resolutions), 3))
    
    def _generate_compromise_options(self, factions: List[Faction], competing_interests: Dict[str, str]) -> List[str]:
        """Generate compromise options"""
        
        compromises = [
            "Divide contested resources",
            "Rotate power between factions",
            "Create coalition government",
            "Establish autonomous regions",
            "Share decision-making authority",
            "Create mutual oversight"
        ]
        
        return self.rng.sample(compromises, min(len(compromises), 3))
    
    def _generate_main_plot_ties(self, scope: str) -> str:
        """Generate ties to main campaign plot"""
        
        ties = {
            "local": "Local intrigue affects regional stability",
            "regional": "Regional politics impact national affairs",
            "national": "National politics affect international relations",
            "international": "International intrigue shapes world events"
        }
        
        return ties.get(scope, "Intrigue connects to larger campaign themes")
    
    def _generate_recurring_consequences(self, plots: List[Plot]) -> List[str]:
        """Generate recurring consequences"""
        
        consequences = []
        
        for plot in plots:
            consequences.extend(plot.future_complications)
        
        return consequences[:4]  # Limit to top consequences
    
    def _generate_future_seeds(self, factions: List[Faction], plots: List[Plot]) -> List[str]:
        """Generate seeds for future intrigue"""
        
        seeds = []
        
        # Seeds from faction relationships
        for faction in factions:
            if faction.enemy_factions:
                seeds.append(f"Ongoing conflict with {faction.name}")
        
        # Seeds from plot hooks
        for plot in plots:
            seeds.extend(plot.sequel_hooks)
        
        return seeds[:5]  # Limit to manageable number
    
    def _generate_plot_phases(self, template: Dict, complexity: str) -> List[Dict[str, Any]]:
        """Generate phases for a plot"""
        
        phase_count = {"simple": 2, "moderate": 3, "complex": 4, "epic": 5}.get(complexity, 3)
        
        phases = []
        base_phases = template.get("phases", [
            {"name": "Preparation", "description": "Gathering resources and allies"},
            {"name": "Implementation", "description": "Executing the plan"},
            {"name": "Resolution", "description": "Dealing with consequences"}
        ])
        
        # Select and expand phases based on complexity
        for i in range(min(phase_count, len(base_phases))):
            phases.append({
                "phase": i + 1,
                "name": base_phases[i]["name"],
                "description": base_phases[i]["description"],
                "duration": f"{self.rng.randint(1, 4)} weeks",
                "key_actions": base_phases[i].get("actions", [])
            })
        
        return phases
    
    async def generate_quick_intrigue(self, scope: str = "local") -> PoliticalIntrigue:
        """Generate a quick political intrigue with default settings"""
        
        return await self.generate_political_intrigue(
            scope=scope,
            complexity="moderate",
            party_level=8,
            faction_count=3
        )