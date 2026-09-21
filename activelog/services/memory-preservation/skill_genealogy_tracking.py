"""
Skill Genealogy Tracking System

This module provides comprehensive skill inheritance and evolution tracking
across generations, including skill lineage mapping, competency analysis,
and knowledge transfer patterns.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
from datetime import datetime, date
import uuid
import numpy as np
from collections import defaultdict, deque

class SkillCategory(Enum):
    """Categories of skills"""
    TECHNICAL = "technical"
    CREATIVE = "creative"
    PHYSICAL = "physical"
    COGNITIVE = "cognitive"
    SOCIAL = "social"
    EMOTIONAL = "emotional"
    PROFESSIONAL = "professional"
    DOMESTIC = "domestic"
    CULTURAL = "cultural"
    SPIRITUAL = "spiritual"
    SURVIVAL = "survival"
    LEADERSHIP = "leadership"

class SkillType(Enum):
    """Types of skill acquisition and expression"""
    INNATE = "innate"
    LEARNED = "learned"
    INHERITED = "inherited"
    ADAPTIVE = "adaptive"
    HYBRID = "hybrid"

class TransmissionMethod(Enum):
    """Methods of skill transmission"""
    DIRECT_TEACHING = "direct_teaching"
    OBSERVATION = "observation"
    PRACTICE = "practice"
    APPRENTICESHIP = "apprenticeship"
    FORMAL_EDUCATION = "formal_education"
    SELF_DISCOVERY = "self_discovery"
    GENETIC = "genetic"
    CULTURAL_OSMOSIS = "cultural_osmosis"
    MENTORSHIP = "mentorship"
    PEER_LEARNING = "peer_learning"

class SkillProficiency(Enum):
    """Levels of skill proficiency"""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"
    GRANDMASTER = "grandmaster"

@dataclass
class SkillRecord:
    """Individual skill record with detailed tracking"""
    skill_id: str
    skill_name: str
    category: SkillCategory
    skill_type: SkillType
    person_id: str
    person_name: str
    proficiency_level: SkillProficiency
    acquisition_date: Optional[date] = None
    source_person_id: Optional[str] = None
    transmission_method: TransmissionMethod = TransmissionMethod.SELF_DISCOVERY
    description: str = ""
    applications: List[str] = field(default_factory=list)
    variations: List[str] = field(default_factory=list)
    related_skills: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    teaching_history: List[str] = field(default_factory=list)  # People taught this skill
    evolution_notes: List[str] = field(default_factory=list)
    practice_frequency: str = "unknown"  # daily, weekly, monthly, rarely
    mastery_indicators: List[str] = field(default_factory=list)
    cultural_context: Dict[str, Any] = field(default_factory=dict)
    documentation: List[str] = field(default_factory=list)
    multimedia_evidence: Dict[str, List[str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class SkillLineage:
    """Tracks skill inheritance across generations"""
    lineage_id: str
    skill_name: str
    origin_person_id: str
    current_generation: int
    lineage_path: List[str]  # Person IDs in order
    transmission_methods: List[TransmissionMethod]
    skill_evolution: List[Dict[str, Any]]
    proficiency_trajectory: List[Tuple[str, SkillProficiency]]  # (person_id, proficiency)
    lineage_strength: float  # 0-1 indicating how well skill was preserved
    adaptations: List[Dict[str, Any]]
    branches: List[str]  # Other lineage IDs that branched from this one
    cultural_influences: List[str]
    time_span: Tuple[Optional[date], Optional[date]]
    lineage_notes: str = ""
    risk_factors: List[str] = field(default_factory=list)  # Threats to continuation

@dataclass
class SkillCluster:
    """Groups of related skills that often appear together"""
    cluster_id: str
    cluster_name: str
    core_skills: List[str]
    supporting_skills: List[str]
    skill_synergies: Dict[str, List[str]]  # skill_id -> synergistic skills
    common_contexts: List[str]
    typical_progression: List[str]  # Skill acquisition order
    cluster_strength: float
    cultural_associations: List[str]
    professional_relevance: Dict[str, float]  # profession -> relevance score

@dataclass
class SkillEvolution:
    """Tracks how skills change over time and across contexts"""
    evolution_id: str
    skill_id: str
    evolution_type: str  # refinement, adaptation, fusion, specialization
    time_period: Tuple[date, date]
    driving_factors: List[str]
    changes_description: str
    skill_before: Dict[str, Any]
    skill_after: Dict[str, Any]
    impact_on_lineage: str
    cultural_influences: List[str]
    technological_factors: List[str]
    environmental_factors: List[str]

class SkillGenealogyTracker:
    """Main system for tracking skill inheritance and evolution"""
    
    def __init__(self):
        self.skill_records: Dict[str, SkillRecord] = {}
        self.skill_lineages: Dict[str, SkillLineage] = {}
        self.skill_clusters: Dict[str, SkillCluster] = {}
        self.skill_evolutions: Dict[str, SkillEvolution] = {}
        self.person_skills: Dict[str, List[str]] = defaultdict(list)
        self.skill_networks: Dict[str, Set[str]] = defaultdict(set)
        self.lineage_graphs: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
    async def add_skill_record(self, skill_record: SkillRecord) -> Dict[str, Any]:
        """Add new skill record and analyze lineage connections"""
        self.skill_records[skill_record.skill_id] = skill_record
        self.person_skills[skill_record.person_id].append(skill_record.skill_id)
        
        # Update skill networks
        for related_skill in skill_record.related_skills:
            if related_skill in self.skill_records:
                self.skill_networks[skill_record.skill_id].add(related_skill)
                self.skill_networks[related_skill].add(skill_record.skill_id)
        
        # Check for lineage connections
        lineage_updates = []
        if skill_record.source_person_id:
            lineage_updates = await self._update_skill_lineages(skill_record)
        
        # Analyze for new clusters
        cluster_updates = await self._analyze_skill_clusters(skill_record)
        
        return {
            'success': True,
            'skill_id': skill_record.skill_id,
            'lineage_updates': lineage_updates,
            'cluster_updates': cluster_updates,
            'network_connections': len(self.skill_networks[skill_record.skill_id])
        }
    
    async def trace_skill_lineage(self, skill_name: str, person_id: Optional[str] = None) -> List[SkillLineage]:
        """Trace the lineage of a specific skill"""
        matching_lineages = []
        
        for lineage in self.skill_lineages.values():
            if (lineage.skill_name.lower() == skill_name.lower() and
                (person_id is None or person_id in lineage.lineage_path)):
                matching_lineages.append(lineage)
        
        # Sort by lineage strength and generation depth
        matching_lineages.sort(key=lambda x: (x.lineage_strength, x.current_generation), reverse=True)
        
        return matching_lineages
    
    async def analyze_skill_inheritance_patterns(self, family_tree: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns of skill inheritance within families"""
        inheritance_patterns = {
            'strong_inheritance': [],  # Skills consistently passed down
            'weak_inheritance': [],   # Skills sporadically passed down
            'lost_skills': [],        # Skills that stopped being transmitted
            'evolved_skills': [],     # Skills that changed significantly
            'new_skills': [],         # Skills that emerged in recent generations
            'family_specializations': {},  # Skill areas families excel in
            'transmission_effectiveness': {}  # Method effectiveness by family
        }
        
        # Analyze each family lineage
        for family_id, family_data in family_tree.items():
            family_skills = await self._analyze_family_skill_patterns(family_data)
            
            # Categorize skill patterns
            for skill_name, pattern_data in family_skills.items():
                generations_with_skill = pattern_data['generations_with_skill']
                total_generations = pattern_data['total_generations']
                inheritance_rate = generations_with_skill / total_generations if total_generations > 0 else 0
                
                if inheritance_rate > 0.8:
                    inheritance_patterns['strong_inheritance'].append({
                        'skill': skill_name,
                        'family': family_id,
                        'inheritance_rate': inheritance_rate,
                        'generations': total_generations
                    })
                elif inheritance_rate > 0.3:
                    inheritance_patterns['weak_inheritance'].append({
                        'skill': skill_name,
                        'family': family_id,
                        'inheritance_rate': inheritance_rate,
                        'last_generation': pattern_data.get('last_generation', 'unknown')
                    })
                elif pattern_data.get('was_present', False) and inheritance_rate == 0:
                    inheritance_patterns['lost_skills'].append({
                        'skill': skill_name,
                        'family': family_id,
                        'lost_generation': pattern_data.get('lost_generation', 'unknown')
                    })
        
        return inheritance_patterns
    
    async def generate_skill_evolution_report(self, skill_name: str) -> Dict[str, Any]:
        """Generate comprehensive evolution report for a specific skill"""
        skill_records = [sr for sr in self.skill_records.values() 
                        if sr.skill_name.lower() == skill_name.lower()]
        
        if not skill_records:
            return {'error': f'No records found for skill: {skill_name}'}
        
        # Sort by acquisition date
        skill_records.sort(key=lambda x: x.acquisition_date or date.min)
        
        # Analyze evolution patterns
        proficiency_evolution = []
        method_evolution = []
        application_evolution = []
        
        for i, record in enumerate(skill_records):
            proficiency_evolution.append({
                'person': record.person_name,
                'date': record.acquisition_date.isoformat() if record.acquisition_date else 'unknown',
                'proficiency': record.proficiency_level.value,
                'generation': i + 1
            })
            
            method_evolution.append({
                'person': record.person_name,
                'method': record.transmission_method.value,
                'effectiveness': await self._calculate_transmission_effectiveness(record)
            })
            
            application_evolution.extend([{
                'person': record.person_name,
                'application': app,
                'generation': i + 1
            } for app in record.applications])
        
        # Find related evolutions
        skill_evolutions = [se for se in self.skill_evolutions.values() 
                           if se.skill_id in [sr.skill_id for sr in skill_records]]
        
        # Calculate skill health metrics
        current_practitioners = len([sr for sr in skill_records 
                                   if sr.practice_frequency in ['daily', 'weekly']])
        
        master_level_practitioners = len([sr for sr in skill_records 
                                        if sr.proficiency_level in [SkillProficiency.MASTER, 
                                                                   SkillProficiency.GRANDMASTER]])
        
        skill_health_score = self._calculate_skill_health(skill_records)
        
        return {
            'skill_name': skill_name,
            'total_records': len(skill_records),
            'current_practitioners': current_practitioners,
            'master_practitioners': master_level_practitioners,
            'skill_health_score': skill_health_score,
            'proficiency_evolution': proficiency_evolution,
            'transmission_methods': method_evolution,
            'application_evolution': application_evolution,
            'documented_evolutions': len(skill_evolutions),
            'evolution_timeline': [se.time_period for se in skill_evolutions],
            'risk_assessment': await self._assess_skill_continuation_risk(skill_records),
            'recommendations': await self._generate_skill_preservation_recommendations(skill_records)
        }
    
    async def identify_skill_clusters(self) -> List[SkillCluster]:
        """Identify clusters of related skills"""
        if not self.skill_records:
            return []
        
        # Group skills by common patterns
        category_clusters = defaultdict(list)
        context_clusters = defaultdict(list)
        person_clusters = defaultdict(list)
        
        for skill_record in self.skill_records.values():
            category_clusters[skill_record.category].append(skill_record.skill_id)
            
            # Group by cultural context
            for context in skill_record.cultural_context.get('contexts', []):
                context_clusters[context].append(skill_record.skill_id)
            
            # Group by person (skills that appear together in individuals)
            person_clusters[skill_record.person_id].append(skill_record.skill_id)
        
        clusters = []
        
        # Create category-based clusters
        for category, skill_ids in category_clusters.items():
            if len(skill_ids) >= 3:  # Minimum cluster size
                cluster = await self._create_skill_cluster(
                    f"{category.value}_cluster",
                    f"{category.value.title()} Skills Cluster",
                    skill_ids
                )
                clusters.append(cluster)
        
        # Create context-based clusters
        for context, skill_ids in context_clusters.items():
            if len(skill_ids) >= 3:
                cluster = await self._create_skill_cluster(
                    f"{context}_cluster",
                    f"{context.title()} Context Cluster",
                    skill_ids
                )
                clusters.append(cluster)
        
        # Find co-occurring skill patterns
        co_occurrence_clusters = await self._find_co_occurring_skills()
        clusters.extend(co_occurrence_clusters)
        
        # Store clusters
        for cluster in clusters:
            self.skill_clusters[cluster.cluster_id] = cluster
        
        return clusters
    
    async def predict_skill_trajectories(self, person_id: str) -> Dict[str, Any]:
        """Predict skill development trajectories for a person"""
        person_skills = self.person_skills.get(person_id, [])
        if not person_skills:
            return {'error': 'No skills found for person'}
        
        current_skills = [self.skill_records[skill_id] for skill_id in person_skills]
        
        predictions = {
            'skill_progression': [],
            'potential_new_skills': [],
            'mastery_timeline': [],
            'teaching_opportunities': [],
            'skill_risks': []
        }
        
        for skill_record in current_skills:
            # Predict skill progression
            current_prof = skill_record.proficiency_level
            if current_prof != SkillProficiency.GRANDMASTER:
                next_level = self._get_next_proficiency_level(current_prof)
                estimated_time = await self._estimate_progression_time(skill_record)
                
                predictions['skill_progression'].append({
                    'skill': skill_record.skill_name,
                    'current_level': current_prof.value,
                    'next_level': next_level.value if next_level else 'maximum_reached',
                    'estimated_months': estimated_time,
                    'probability': await self._calculate_progression_probability(skill_record)
                })
            
            # Predict mastery timeline
            if current_prof in [SkillProficiency.ADVANCED, SkillProficiency.EXPERT]:
                mastery_time = await self._estimate_mastery_time(skill_record)
                predictions['mastery_timeline'].append({
                    'skill': skill_record.skill_name,
                    'current_level': current_prof.value,
                    'estimated_mastery_months': mastery_time,
                    'factors': await self._identify_mastery_factors(skill_record)
                })
            
            # Identify teaching opportunities
            if current_prof in [SkillProficiency.EXPERT, SkillProficiency.MASTER, SkillProficiency.GRANDMASTER]:
                teaching_potential = await self._assess_teaching_potential(skill_record)
                if teaching_potential['score'] > 0.6:
                    predictions['teaching_opportunities'].append(teaching_potential)
        
        # Predict potential new skills
        potential_skills = await self._predict_skill_acquisition(current_skills)
        predictions['potential_new_skills'] = potential_skills
        
        return predictions
    
    async def generate_lineage_visualization_data(self, skill_name: str) -> Dict[str, Any]:
        """Generate data for skill lineage visualization"""
        lineages = await self.trace_skill_lineage(skill_name)
        
        if not lineages:
            return {'error': f'No lineages found for skill: {skill_name}'}
        
        # Create graph data for visualization
        nodes = []
        edges = []
        
        for lineage in lineages:
            # Add person nodes
            for i, person_id in enumerate(lineage.lineage_path):
                person_skill_record = None
                for skill_id, record in self.skill_records.items():
                    if record.person_id == person_id and record.skill_name.lower() == skill_name.lower():
                        person_skill_record = record
                        break
                
                node = {
                    'id': person_id,
                    'name': person_skill_record.person_name if person_skill_record else f'Person {person_id}',
                    'generation': i,
                    'proficiency': person_skill_record.proficiency_level.value if person_skill_record else 'unknown',
                    'acquisition_date': person_skill_record.acquisition_date.isoformat() if person_skill_record and person_skill_record.acquisition_date else None,
                    'lineage_id': lineage.lineage_id
                }
                nodes.append(node)
                
                # Add edges between generations
                if i > 0:
                    edge = {
                        'source': lineage.lineage_path[i-1],
                        'target': person_id,
                        'transmission_method': lineage.transmission_methods[i-1].value if i-1 < len(lineage.transmission_methods) else 'unknown',
                        'lineage_id': lineage.lineage_id,
                        'strength': lineage.lineage_strength
                    }
                    edges.append(edge)
        
        return {
            'skill_name': skill_name,
            'nodes': nodes,
            'edges': edges,
            'lineage_count': len(lineages),
            'total_generations': max(len(l.lineage_path) for l in lineages) if lineages else 0,
            'visualization_metadata': {
                'layout_type': 'hierarchical',
                'time_span': {
                    'start': min(l.time_span[0] for l in lineages if l.time_span[0]).isoformat() if any(l.time_span[0] for l in lineages) else None,
                    'end': max(l.time_span[1] for l in lineages if l.time_span[1]).isoformat() if any(l.time_span[1] for l in lineages) else None
                }
            }
        }
    
    async def _update_skill_lineages(self, skill_record: SkillRecord) -> List[str]:
        """Update skill lineages when new skill record is added"""
        lineage_updates = []
        
        # Find existing lineage for this skill
        existing_lineage = None
        for lineage in self.skill_lineages.values():
            if (lineage.skill_name.lower() == skill_record.skill_name.lower() and
                skill_record.source_person_id in lineage.lineage_path):
                existing_lineage = lineage
                break
        
        if existing_lineage:
            # Extend existing lineage
            existing_lineage.lineage_path.append(skill_record.person_id)
            existing_lineage.current_generation += 1
            existing_lineage.transmission_methods.append(skill_record.transmission_method)
            existing_lineage.proficiency_trajectory.append((skill_record.person_id, skill_record.proficiency_level))
            existing_lineage.time_span = (existing_lineage.time_span[0], skill_record.acquisition_date)
            
            # Update lineage strength based on proficiency maintenance
            existing_lineage.lineage_strength = self._calculate_lineage_strength(existing_lineage)
            
            lineage_updates.append(existing_lineage.lineage_id)
            
        elif skill_record.source_person_id:
            # Create new lineage
            new_lineage = SkillLineage(
                lineage_id=f"lineage_{uuid.uuid4().hex}",
                skill_name=skill_record.skill_name,
                origin_person_id=skill_record.source_person_id,
                current_generation=1,
                lineage_path=[skill_record.source_person_id, skill_record.person_id],
                transmission_methods=[skill_record.transmission_method],
                skill_evolution=[],
                proficiency_trajectory=[
                    (skill_record.source_person_id, SkillProficiency.ADVANCED),  # Assumed
                    (skill_record.person_id, skill_record.proficiency_level)
                ],
                lineage_strength=0.8,  # Initial strength
                adaptations=[],
                branches=[],
                cultural_influences=[],
                time_span=(skill_record.acquisition_date, skill_record.acquisition_date)
            )
            
            self.skill_lineages[new_lineage.lineage_id] = new_lineage
            lineage_updates.append(new_lineage.lineage_id)
        
        return lineage_updates
    
    async def _analyze_skill_clusters(self, new_skill: SkillRecord) -> List[str]:
        """Analyze for new skill clusters when skill is added"""
        cluster_updates = []
        
        # Check if this skill completes any potential clusters
        related_skills = set(new_skill.related_skills)
        
        # Find skills from the same person
        person_skills = [self.skill_records[skill_id] for skill_id in self.person_skills[new_skill.person_id] 
                        if skill_id != new_skill.skill_id]
        
        if len(person_skills) >= 2:
            # Create or update person-based cluster
            cluster_id = f"person_{new_skill.person_id}_cluster"
            skill_ids = [s.skill_id for s in person_skills] + [new_skill.skill_id]
            
            cluster = await self._create_skill_cluster(
                cluster_id,
                f"{new_skill.person_name}'s Skill Set",
                skill_ids
            )
            
            self.skill_clusters[cluster_id] = cluster
            cluster_updates.append(cluster_id)
        
        return cluster_updates
    
    async def _create_skill_cluster(self, cluster_id: str, cluster_name: str, skill_ids: List[str]) -> SkillCluster:
        """Create skill cluster from list of skill IDs"""
        skills = [self.skill_records[sid] for sid in skill_ids if sid in self.skill_records]
        
        # Analyze skill relationships
        core_skills = []
        supporting_skills = []
        skill_synergies = {}
        
        # Categorize skills by proficiency and centrality
        for skill in skills:
            if skill.proficiency_level in [SkillProficiency.EXPERT, SkillProficiency.MASTER, SkillProficiency.GRANDMASTER]:
                core_skills.append(skill.skill_id)
            else:
                supporting_skills.append(skill.skill_id)
            
            # Map synergies
            skill_synergies[skill.skill_id] = [s.skill_id for s in skills 
                                              if s.skill_id != skill.skill_id and 
                                              s.skill_id in skill.related_skills]
        
        # Find common contexts
        all_contexts = []
        for skill in skills:
            all_contexts.extend(skill.cultural_context.get('contexts', []))
        
        common_contexts = [ctx for ctx in set(all_contexts) 
                          if all_contexts.count(ctx) >= len(skills) * 0.5]
        
        # Calculate cluster strength
        cluster_strength = len(core_skills) / len(skills) if skills else 0.0
        
        return SkillCluster(
            cluster_id=cluster_id,
            cluster_name=cluster_name,
            core_skills=core_skills,
            supporting_skills=supporting_skills,
            skill_synergies=skill_synergies,
            common_contexts=common_contexts,
            typical_progression=[],  # Could be analyzed from skill acquisition patterns
            cluster_strength=cluster_strength,
            cultural_associations=[],
            professional_relevance={}
        )
    
    async def _find_co_occurring_skills(self) -> List[SkillCluster]:
        """Find skills that frequently appear together across different people"""
        skill_co_occurrence = defaultdict(lambda: defaultdict(int))
        
        # Count skill co-occurrences
        for person_skills in self.person_skills.values():
            if len(person_skills) > 1:
                for i, skill1 in enumerate(person_skills):
                    for j, skill2 in enumerate(person_skills):
                        if i != j:
                            skill1_name = self.skill_records[skill1].skill_name
                            skill2_name = self.skill_records[skill2].skill_name
                            skill_co_occurrence[skill1_name][skill2_name] += 1
        
        # Identify strong co-occurrence patterns
        clusters = []
        processed_skills = set()
        
        for skill1, co_skills in skill_co_occurrence.items():
            if skill1 in processed_skills:
                continue
            
            # Find highly co-occurring skills
            strong_connections = [(skill2, count) for skill2, count in co_skills.items() 
                                if count >= 2]  # Appears together at least twice
            
            if strong_connections:
                cluster_skills = [skill1] + [skill2 for skill2, _ in strong_connections]
                skill_ids = []
                
                # Get skill IDs for cluster skills
                for cluster_skill in cluster_skills:
                    for skill_id, record in self.skill_records.items():
                        if record.skill_name == cluster_skill:
                            skill_ids.append(skill_id)
                            break
                
                if len(skill_ids) >= 3:
                    cluster = await self._create_skill_cluster(
                        f"co_occurrence_{uuid.uuid4().hex}",
                        f"Co-occurring Skills: {skill1}+",
                        skill_ids
                    )
                    clusters.append(cluster)
                    
                    # Mark skills as processed
                    processed_skills.update(cluster_skills)
        
        return clusters
    
    async def _analyze_family_skill_patterns(self, family_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Analyze skill patterns within a family"""
        family_skills = defaultdict(lambda: {
            'generations_with_skill': 0,
            'total_generations': 0,
            'proficiency_levels': [],
            'transmission_methods': [],
            'was_present': False,
            'last_generation': None,
            'lost_generation': None
        })
        
        # Process each family member
        for member_id, member_data in family_data.get('members', {}).items():
            generation = member_data.get('generation', 0)
            member_skills = self.person_skills.get(member_id, [])
            
            # Update generation counts for all skills
            for skill_record in self.skill_records.values():
                skill_name = skill_record.skill_name
                family_skills[skill_name]['total_generations'] = max(
                    family_skills[skill_name]['total_generations'], 
                    generation + 1
                )
            
            # Process member's skills
            for skill_id in member_skills:
                skill_record = self.skill_records[skill_id]
                skill_name = skill_record.skill_name
                
                family_skills[skill_name]['generations_with_skill'] += 1
                family_skills[skill_name]['proficiency_levels'].append(skill_record.proficiency_level.value)
                family_skills[skill_name]['transmission_methods'].append(skill_record.transmission_method.value)
                family_skills[skill_name]['was_present'] = True
                family_skills[skill_name]['last_generation'] = generation
        
        return dict(family_skills)
    
    async def _calculate_transmission_effectiveness(self, skill_record: SkillRecord) -> float:
        """Calculate effectiveness of skill transmission method"""
        method_effectiveness = {
            TransmissionMethod.DIRECT_TEACHING: 0.9,
            TransmissionMethod.APPRENTICESHIP: 0.95,
            TransmissionMethod.MENTORSHIP: 0.85,
            TransmissionMethod.FORMAL_EDUCATION: 0.8,
            TransmissionMethod.OBSERVATION: 0.6,
            TransmissionMethod.PRACTICE: 0.7,
            TransmissionMethod.SELF_DISCOVERY: 0.5,
            TransmissionMethod.CULTURAL_OSMOSIS: 0.4,
            TransmissionMethod.PEER_LEARNING: 0.65,
            TransmissionMethod.GENETIC: 0.3,
        }
        
        base_effectiveness = method_effectiveness.get(skill_record.transmission_method, 0.5)
        
        # Adjust based on proficiency achieved
        proficiency_multiplier = {
            SkillProficiency.NOVICE: 0.3,
            SkillProficiency.BEGINNER: 0.5,
            SkillProficiency.INTERMEDIATE: 0.7,
            SkillProficiency.ADVANCED: 0.85,
            SkillProficiency.EXPERT: 0.95,
            SkillProficiency.MASTER: 1.0,
            SkillProficiency.GRANDMASTER: 1.0
        }
        
        proficiency_factor = proficiency_multiplier.get(skill_record.proficiency_level, 0.5)
        
        return base_effectiveness * proficiency_factor
    
    def _calculate_skill_health(self, skill_records: List[SkillRecord]) -> float:
        """Calculate overall health score for a skill"""
        if not skill_records:
            return 0.0
        
        factors = {
            'practitioner_count': len(skill_records),
            'master_count': len([sr for sr in skill_records 
                               if sr.proficiency_level in [SkillProficiency.MASTER, SkillProficiency.GRANDMASTER]]),
            'active_practice': len([sr for sr in skill_records 
                                  if sr.practice_frequency in ['daily', 'weekly']]),
            'teaching_activity': len([sr for sr in skill_records if sr.teaching_history]),
            'documentation': len([sr for sr in skill_records if sr.documentation])
        }
        
        # Weighted scoring
        score = (
            min(factors['practitioner_count'] / 10, 1.0) * 0.3 +  # Up to 10 practitioners = full score
            min(factors['master_count'] / 3, 1.0) * 0.3 +         # Up to 3 masters = full score  
            min(factors['active_practice'] / 5, 1.0) * 0.2 +      # Up to 5 active practitioners = full score
            min(factors['teaching_activity'] / 3, 1.0) * 0.1 +    # Up to 3 teachers = full score
            min(factors['documentation'] / 2, 1.0) * 0.1          # Up to 2 documented = full score
        )
        
        return score
    
    async def _assess_skill_continuation_risk(self, skill_records: List[SkillRecord]) -> Dict[str, Any]:
        """Assess risk factors for skill continuation"""
        risk_factors = []
        risk_level = "low"
        
        # Check practitioner count
        if len(skill_records) < 3:
            risk_factors.append("Few practitioners")
            risk_level = "high"
        
        # Check for masters
        master_count = len([sr for sr in skill_records 
                          if sr.proficiency_level in [SkillProficiency.MASTER, SkillProficiency.GRANDMASTER]])
        if master_count == 0:
            risk_factors.append("No master-level practitioners")
            risk_level = "critical"
        
        # Check active practice
        active_practitioners = len([sr for sr in skill_records 
                                  if sr.practice_frequency in ['daily', 'weekly']])
        if active_practitioners == 0:
            risk_factors.append("No active practitioners")
            risk_level = "critical"
        
        # Check teaching activity
        teachers = len([sr for sr in skill_records if sr.teaching_history])
        if teachers == 0:
            risk_factors.append("No documented teaching activity")
            if risk_level == "low":
                risk_level = "medium"
        
        # Check documentation
        documented = len([sr for sr in skill_records if sr.documentation])
        if documented == 0:
            risk_factors.append("No documentation")
            if risk_level == "low":
                risk_level = "medium"
        
        return {
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'practitioner_count': len(skill_records),
            'master_count': master_count,
            'active_practitioners': active_practitioners,
            'teachers': teachers,
            'documentation_level': documented
        }
    
    async def _generate_skill_preservation_recommendations(self, skill_records: List[SkillRecord]) -> List[str]:
        """Generate recommendations for skill preservation"""
        recommendations = []
        risk_assessment = await self._assess_skill_continuation_risk(skill_records)
        
        if risk_assessment['risk_level'] == "critical":
            recommendations.append("URGENT: Document all aspects of the skill immediately")
            recommendations.append("Identify and interview all remaining practitioners")
            recommendations.append("Create multimedia documentation (video, audio, written)")
            recommendations.append("Establish emergency teaching program")
        
        if risk_assessment['master_count'] == 0:
            recommendations.append("Identify highest-proficiency practitioners for intensive development")
            recommendations.append("Connect with related skills masters for guidance")
        
        if risk_assessment['teachers'] == 0:
            recommendations.append("Encourage experienced practitioners to begin teaching")
            recommendations.append("Develop structured teaching materials and curriculum")
        
        if risk_assessment['active_practitioners'] < 3:
            recommendations.append("Recruit new practitioners through cultural programs")
            recommendations.append("Create incentives for practice and involvement")
        
        if risk_assessment['documentation_level'] == 0:
            recommendations.append("Begin systematic documentation project")
            recommendations.append("Record oral histories and practice sessions")
        
        # Always good practices
        recommendations.append("Create skill-sharing events and demonstrations")
        recommendations.append("Connect practitioners with each other")
        recommendations.append("Integrate skill into cultural education programs")
        
        return recommendations
    
    def _calculate_lineage_strength(self, lineage: SkillLineage) -> float:
        """Calculate strength of skill lineage based on proficiency maintenance"""
        if not lineage.proficiency_trajectory:
            return 0.5  # Default
        
        proficiency_values = {
            SkillProficiency.NOVICE: 1,
            SkillProficiency.BEGINNER: 2,
            SkillProficiency.INTERMEDIATE: 3,
            SkillProficiency.ADVANCED: 4,
            SkillProficiency.EXPERT: 5,
            SkillProficiency.MASTER: 6,
            SkillProficiency.GRANDMASTER: 7
        }
        
        trajectory_values = [proficiency_values.get(prof, 3) for _, prof in lineage.proficiency_trajectory]
        
        if len(trajectory_values) < 2:
            return 0.5
        
        # Calculate trend
        average_change = sum(trajectory_values[i] - trajectory_values[i-1] 
                           for i in range(1, len(trajectory_values))) / (len(trajectory_values) - 1)
        
        # Normalize to 0-1 scale
        strength = 0.5 + (average_change / 6.0)  # Max change is 6 levels
        
        return max(0.0, min(1.0, strength))
    
    def _get_next_proficiency_level(self, current: SkillProficiency) -> Optional[SkillProficiency]:
        """Get next proficiency level"""
        progression = [
            SkillProficiency.NOVICE,
            SkillProficiency.BEGINNER,
            SkillProficiency.INTERMEDIATE,
            SkillProficiency.ADVANCED,
            SkillProficiency.EXPERT,
            SkillProficiency.MASTER,
            SkillProficiency.GRANDMASTER
        ]
        
        try:
            current_index = progression.index(current)
            if current_index < len(progression) - 1:
                return progression[current_index + 1]
        except ValueError:
            pass
        
        return None
    
    async def _estimate_progression_time(self, skill_record: SkillRecord) -> int:
        """Estimate time to next proficiency level in months"""
        base_times = {
            SkillProficiency.NOVICE: 6,      # 6 months to beginner
            SkillProficiency.BEGINNER: 12,   # 12 months to intermediate
            SkillProficiency.INTERMEDIATE: 18, # 18 months to advanced
            SkillProficiency.ADVANCED: 24,   # 24 months to expert
            SkillProficiency.EXPERT: 36,     # 36 months to master
            SkillProficiency.MASTER: 60      # 60 months to grandmaster
        }
        
        base_time = base_times.get(skill_record.proficiency_level, 12)
        
        # Adjust based on practice frequency
        practice_multipliers = {
            'daily': 0.7,
            'weekly': 1.0,
            'monthly': 1.5,
            'rarely': 2.0,
            'unknown': 1.2
        }
        
        multiplier = practice_multipliers.get(skill_record.practice_frequency, 1.2)
        
        return int(base_time * multiplier)
    
    async def _calculate_progression_probability(self, skill_record: SkillRecord) -> float:
        """Calculate probability of skill progression"""
        base_probability = 0.7
        
        # Adjust based on current proficiency
        if skill_record.proficiency_level in [SkillProficiency.EXPERT, SkillProficiency.MASTER]:
            base_probability = 0.4  # Harder to progress at higher levels
        
        # Adjust based on practice frequency
        practice_bonuses = {
            'daily': 0.2,
            'weekly': 0.1,
            'monthly': 0.0,
            'rarely': -0.2,
            'unknown': -0.1
        }
        
        practice_bonus = practice_bonuses.get(skill_record.practice_frequency, 0.0)
        
        # Adjust based on teaching activity (teaching improves understanding)
        teaching_bonus = 0.1 if skill_record.teaching_history else 0.0
        
        probability = base_probability + practice_bonus + teaching_bonus
        
        return max(0.0, min(1.0, probability))
    
    async def _estimate_mastery_time(self, skill_record: SkillRecord) -> int:
        """Estimate time to achieve mastery"""
        current_level = skill_record.proficiency_level
        
        levels_to_master = {
            SkillProficiency.ADVANCED: 60,  # months
            SkillProficiency.EXPERT: 36
        }
        
        return levels_to_master.get(current_level, 24)
    
    async def _identify_mastery_factors(self, skill_record: SkillRecord) -> List[str]:
        """Identify factors that could accelerate mastery"""
        factors = []
        
        if skill_record.practice_frequency == 'daily':
            factors.append("Daily practice routine")
        
        if skill_record.teaching_history:
            factors.append("Teaching experience")
        
        if len(skill_record.related_skills) > 3:
            factors.append("Strong skill synergies")
        
        if skill_record.documentation:
            factors.append("Well-documented practice")
        
        return factors
    
    async def _assess_teaching_potential(self, skill_record: SkillRecord) -> Dict[str, Any]:
        """Assess potential for teaching others"""
        score = 0.0
        factors = []
        
        # Proficiency level
        if skill_record.proficiency_level == SkillProficiency.GRANDMASTER:
            score += 0.4
            factors.append("Grandmaster level")
        elif skill_record.proficiency_level == SkillProficiency.MASTER:
            score += 0.3
            factors.append("Master level")
        elif skill_record.proficiency_level == SkillProficiency.EXPERT:
            score += 0.2
            factors.append("Expert level")
        
        # Teaching history
        if skill_record.teaching_history:
            score += 0.2
            factors.append("Previous teaching experience")
        
        # Documentation
        if skill_record.documentation:
            score += 0.1
            factors.append("Skill documentation available")
        
        # Practice frequency
        if skill_record.practice_frequency in ['daily', 'weekly']:
            score += 0.1
            factors.append("Active practice")
        
        return {
            'skill': skill_record.skill_name,
            'person': skill_record.person_name,
            'score': score,
            'factors': factors,
            'recommendation': 'Excellent teaching candidate' if score > 0.7 else 
                            'Good teaching potential' if score > 0.5 else 
                            'Moderate teaching potential'
        }
    
    async def _predict_skill_acquisition(self, current_skills: List[SkillRecord]) -> List[Dict[str, Any]]:
        """Predict potential new skills based on current skill set"""
        predictions = []
        
        # Analyze skill clusters and common progressions
        current_skill_names = set(skill.skill_name for skill in current_skills)
        current_categories = set(skill.category for skill in current_skills)
        
        # Find skills commonly associated with current skills
        skill_associations = defaultdict(float)
        
        for skill in current_skills:
            for related_skill in skill.related_skills:
                if related_skill not in current_skill_names:
                    skill_associations[related_skill] += 0.3
        
        # Find skills in same categories
        for skill_record in self.skill_records.values():
            if (skill_record.category in current_categories and 
                skill_record.skill_name not in current_skill_names):
                skill_associations[skill_record.skill_name] += 0.2
        
        # Convert to predictions
        for skill_name, score in skill_associations.items():
            if score > 0.3:  # Minimum threshold
                predictions.append({
                    'skill': skill_name,
                    'probability': min(score, 1.0),
                    'reasoning': f"Associated with {len([s for s in current_skills if skill_name in s.related_skills])} current skills"
                })
        
        # Sort by probability
        predictions.sort(key=lambda x: x['probability'], reverse=True)
        
        return predictions[:10]  # Top 10 predictions

# Example usage
async def main():
    """Example usage of skill genealogy tracking system"""
    
    print("Skill Genealogy Tracking System Demo")
    print("=" * 50)
    
    # Initialize skill tracker
    tracker = SkillGenealogyTracker()
    
    # Add sample skill records
    skills = [
        SkillRecord(
            skill_id="skill_001",
            skill_name="Traditional Pottery",
            category=SkillCategory.CREATIVE,
            skill_type=SkillType.LEARNED,
            person_id="person_001",
            person_name="Maria Gonzalez",
            proficiency_level=SkillProficiency.MASTER,
            acquisition_date=date(1960, 5, 15),
            source_person_id="person_000",  # Her grandmother
            transmission_method=TransmissionMethod.APPRENTICESHIP,
            description="Traditional clay pottery techniques passed down through family",
            applications=["decorative pottery", "functional vessels", "ceremonial items"],
            teaching_history=["person_002", "person_003"],
            practice_frequency="daily",
            cultural_context={"contexts": ["Mexican heritage", "family tradition"]}
        ),
        
        SkillRecord(
            skill_id="skill_002",
            skill_name="Traditional Pottery",
            category=SkillCategory.CREATIVE,
            skill_type=SkillType.INHERITED,
            person_id="person_002",
            person_name="Carlos Gonzalez",
            proficiency_level=SkillProficiency.ADVANCED,
            acquisition_date=date(1985, 8, 10),
            source_person_id="person_001",
            transmission_method=TransmissionMethod.DIRECT_TEACHING,
            description="Learned pottery from mother, specializing in modern adaptations",
            applications=["artistic pottery", "teaching workshops"],
            practice_frequency="weekly",
            cultural_context={"contexts": ["Mexican heritage", "artistic expression"]}
        ),
        
        SkillRecord(
            skill_id="skill_003",
            skill_name="Wood Carving",
            category=SkillCategory.CREATIVE,
            skill_type=SkillType.LEARNED,
            person_id="person_002",
            person_name="Carlos Gonzalez",
            proficiency_level=SkillProficiency.INTERMEDIATE,
            acquisition_date=date(1990, 3, 20),
            transmission_method=TransmissionMethod.SELF_DISCOVERY,
            description="Self-taught wood carving to complement pottery work",
            applications=["pottery tools", "decorative elements"],
            practice_frequency="monthly",
            related_skills=["skill_002"]
        ),
        
        SkillRecord(
            skill_id="skill_004",
            skill_name="Digital Art",
            category=SkillCategory.TECHNICAL,
            skill_type=SkillType.LEARNED,
            person_id="person_003",
            person_name="Ana Gonzalez",
            proficiency_level=SkillProficiency.EXPERT,
            acquisition_date=date(2010, 1, 15),
            transmission_method=TransmissionMethod.FORMAL_EDUCATION,
            description="Digital art and design skills for modern creative work",
            applications=["graphic design", "digital pottery designs", "teaching"],
            practice_frequency="daily"
        )
    ]
    
    # Add skills to tracker
    for skill in skills:
        result = await tracker.add_skill_record(skill)
        print(f"Added skill: {skill.skill_name} for {skill.person_name} - Success: {result['success']}")
    
    # Trace skill lineage
    print("\n" + "=" * 50)
    print("SKILL LINEAGE ANALYSIS")
    print("=" * 50)
    
    pottery_lineages = await tracker.trace_skill_lineage("Traditional Pottery")
    print(f"Found {len(pottery_lineages)} pottery lineages:")
    
    for lineage in pottery_lineages:
        print(f"\nLineage: {lineage.lineage_id}")
        print(f"Generations: {lineage.current_generation}")
        print(f"Path: {' -> '.join([tracker.skill_records[sid].person_name for sid in lineage.lineage_path if sid in tracker.skill_records])}")
        print(f"Strength: {lineage.lineage_strength:.2f}")
        print(f"Methods: {[method.value for method in lineage.transmission_methods]}")
    
    # Generate skill evolution report
    print("\n" + "=" * 50)
    print("SKILL EVOLUTION REPORT")
    print("=" * 50)
    
    evolution_report = await tracker.generate_skill_evolution_report("Traditional Pottery")
    print(f"Skill: {evolution_report['skill_name']}")
    print(f"Total records: {evolution_report['total_records']}")
    print(f"Current practitioners: {evolution_report['current_practitioners']}")
    print(f"Master practitioners: {evolution_report['master_practitioners']}")
    print(f"Health score: {evolution_report['skill_health_score']:.2f}")
    print(f"Risk level: {evolution_report['risk_assessment']['risk_level']}")
    
    print("\nRecommendations:")
    for rec in evolution_report['recommendations'][:3]:
        print(f"  - {rec}")
    
    # Identify skill clusters
    print("\n" + "=" * 50)
    print("SKILL CLUSTER ANALYSIS")
    print("=" * 50)
    
    clusters = await tracker.identify_skill_clusters()
    print(f"Identified {len(clusters)} skill clusters:")
    
    for cluster in clusters:
        print(f"\nCluster: {cluster.cluster_name}")
        print(f"Core skills: {len(cluster.core_skills)}")
        print(f"Supporting skills: {len(cluster.supporting_skills)}")
        print(f"Strength: {cluster.cluster_strength:.2f}")
        if cluster.common_contexts:
            print(f"Common contexts: {', '.join(cluster.common_contexts)}")
    
    # Predict skill trajectories
    print("\n" + "=" * 50)
    print("SKILL TRAJECTORY PREDICTIONS")
    print("=" * 50)
    
    predictions = await tracker.predict_skill_trajectories("person_002")
    print("Skill progression predictions:")
    for pred in predictions['skill_progression']:
        print(f"  - {pred['skill']}: {pred['current_level']} -> {pred['next_level']} ({pred['estimated_months']} months, {pred['probability']:.1%} probability)")
    
    print("\nTeaching opportunities:")
    for opp in predictions['teaching_opportunities']:
        print(f"  - {opp['skill']}: {opp['recommendation']} (score: {opp['score']:.2f})")
    
    print("\nPotential new skills:")
    for skill in predictions['potential_new_skills'][:3]:
        print(f"  - {skill['skill']}: {skill['probability']:.1%} probability")
    
    # Generate visualization data
    print("\n" + "=" * 50)
    print("LINEAGE VISUALIZATION DATA")
    print("=" * 50)
    
    viz_data = await tracker.generate_lineage_visualization_data("Traditional Pottery")
    print(f"Nodes: {len(viz_data['nodes'])}")
    print(f"Edges: {len(viz_data['edges'])}")
    print(f"Lineages: {viz_data['lineage_count']}")
    print(f"Generations: {viz_data['total_generations']}")

if __name__ == "__main__":
    asyncio.run(main())