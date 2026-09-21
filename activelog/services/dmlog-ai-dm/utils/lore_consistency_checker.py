"""
Lore Consistency Checker for maintaining world continuity and fact accuracy
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from difflib import SequenceMatcher
import hashlib

from ..models.base import LoreEntry, Campaign, NarrativeEvent
from ..config import LORE_CONFIG
from ..utils.ai_client import AIClient


logger = logging.getLogger(__name__)


class LoreInconsistency:
    """Represents a detected lore inconsistency"""
    
    def __init__(self, inconsistency_type: str, severity: float, 
                 description: str, conflicting_entries: List[str],
                 suggested_resolution: str = ""):
        self.type = inconsistency_type
        self.severity = severity  # 0.0 to 1.0
        self.description = description
        self.conflicting_entries = conflicting_entries
        self.suggested_resolution = suggested_resolution
        self.detected_at = datetime.utcnow()
        self.resolved = False


class LoreConsistencyChecker:
    """Checks and maintains consistency of campaign lore and world facts"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        
        # Lore database
        self.lore_entries: Dict[str, LoreEntry] = {}
        self.category_index: Dict[str, Set[str]] = {}  # category -> entry_ids
        self.name_index: Dict[str, str] = {}  # name -> entry_id
        
        # Consistency tracking
        self.detected_inconsistencies: List[LoreInconsistency] = []
        self.consistency_score: float = 1.0
        self.last_check_time: Optional[datetime] = None
        
        # Analysis cache
        self.similarity_cache: Dict[str, float] = {}
        self.fact_verification_cache: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.consistency_threshold = LORE_CONFIG["consistency_threshold"]
        self.auto_correction = LORE_CONFIG["auto_correction"]
        self.lore_categories = LORE_CONFIG["lore_categories"]
    
    async def initialize_lore_database(self, campaign: Campaign) -> None:
        """Initialize lore database from campaign data"""
        try:
            # Load existing lore entries
            for entry_id, entry_data in campaign.lore_database.items():
                lore_entry = LoreEntry(**entry_data)
                await self.add_lore_entry(lore_entry)
            
            # Build indices
            await self._rebuild_indices()
            
            # Perform initial consistency check
            await self.perform_full_consistency_check()
            
            logger.info(f"Lore database initialized: {len(self.lore_entries)} entries, "
                       f"consistency score: {self.consistency_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error initializing lore database: {e}")
            raise
    
    async def add_lore_entry(self, lore_entry: LoreEntry) -> Dict[str, Any]:
        """Add a new lore entry and check for consistency"""
        try:
            entry_id = lore_entry.id
            
            # Check for conflicts with existing entries
            conflicts = await self._check_entry_conflicts(lore_entry)
            
            # Add to database
            self.lore_entries[entry_id] = lore_entry
            
            # Update indices
            await self._update_indices_for_entry(lore_entry)
            
            # If conflicts found, create inconsistency records
            if conflicts:
                for conflict in conflicts:
                    inconsistency = LoreInconsistency(
                        inconsistency_type=conflict["type"],
                        severity=conflict["severity"],
                        description=conflict["description"],
                        conflicting_entries=[entry_id] + conflict["conflicting_with"],
                        suggested_resolution=conflict.get("resolution", "")
                    )
                    self.detected_inconsistencies.append(inconsistency)
            
            # Update consistency score
            await self._update_consistency_score()
            
            return {
                "entry_added": True,
                "entry_id": entry_id,
                "conflicts_detected": len(conflicts),
                "conflicts": conflicts,
                "new_consistency_score": self.consistency_score
            }
            
        except Exception as e:
            logger.error(f"Error adding lore entry: {e}")
            return {"error": str(e)}
    
    async def verify_statement(self, statement: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Verify a statement against known lore"""
        try:
            # Check cache first
            statement_hash = hashlib.md5(statement.encode()).hexdigest()
            if statement_hash in self.fact_verification_cache:
                cached_result = self.fact_verification_cache[statement_hash]
                if (datetime.utcnow() - datetime.fromisoformat(cached_result["verified_at"])).seconds < 3600:
                    return cached_result
            
            # Extract key facts from statement
            extracted_facts = await self._extract_facts_from_statement(statement)
            
            # Check each fact against lore database
            verification_results = []
            overall_consistency = True
            
            for fact in extracted_facts:
                fact_check = await self._verify_single_fact(fact, context)
                verification_results.append(fact_check)
                
                if not fact_check["consistent"]:
                    overall_consistency = False
            
            # Generate overall assessment
            confidence = await self._calculate_statement_confidence(statement, verification_results)
            
            # Suggest corrections if needed
            corrections = []
            if not overall_consistency:
                corrections = await self._suggest_statement_corrections(
                    statement, verification_results
                )
            
            result = {
                "statement": statement,
                "consistent": overall_consistency,
                "confidence": confidence,
                "fact_checks": verification_results,
                "corrections": corrections,
                "verified_at": datetime.utcnow().isoformat()
            }
            
            # Cache result
            self.fact_verification_cache[statement_hash] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying statement: {e}")
            return {"error": str(e)}
    
    async def check_character_consistency(self, character_id: str, 
                                        new_information: Dict[str, Any]) -> Dict[str, Any]:
        """Check consistency of character information"""
        try:
            # Find existing character entries
            character_entries = await self._find_character_entries(character_id)
            
            if not character_entries:
                return {
                    "consistent": True,
                    "message": "No existing character information found"
                }
            
            # Check each piece of new information
            inconsistencies = []
            
            for info_type, info_value in new_information.items():
                consistency_check = await self._check_character_info_consistency(
                    character_id, info_type, info_value, character_entries
                )
                
                if not consistency_check["consistent"]:
                    inconsistencies.append(consistency_check)
            
            # Generate overall assessment
            overall_consistent = len(inconsistencies) == 0
            
            return {
                "character_id": character_id,
                "consistent": overall_consistent,
                "inconsistencies": inconsistencies,
                "existing_entries": [entry.id for entry in character_entries],
                "recommendations": await self._generate_character_consistency_recommendations(
                    inconsistencies
                )
            }
            
        except Exception as e:
            logger.error(f"Error checking character consistency: {e}")
            return {"error": str(e)}
    
    async def check_timeline_consistency(self, events: List[NarrativeEvent]) -> Dict[str, Any]:
        """Check timeline consistency across events"""
        try:
            timeline_issues = []
            
            # Sort events by timestamp
            sorted_events = sorted(events, key=lambda x: x.timestamp)
            
            # Check for temporal inconsistencies
            for i, event in enumerate(sorted_events):
                # Check against previous events
                for j in range(max(0, i-10), i):  # Check last 10 events
                    previous_event = sorted_events[j]
                    
                    inconsistency = await self._check_temporal_consistency(
                        previous_event, event
                    )
                    
                    if inconsistency:
                        timeline_issues.append(inconsistency)
                
                # Check against lore entries
                lore_conflicts = await self._check_event_against_lore(event)
                timeline_issues.extend(lore_conflicts)
            
            # Assess overall timeline health
            timeline_consistency_score = self._calculate_timeline_consistency_score(
                timeline_issues, len(events)
            )
            
            return {
                "timeline_consistent": len(timeline_issues) == 0,
                "consistency_score": timeline_consistency_score,
                "issues_found": len(timeline_issues),
                "issues": timeline_issues,
                "recommendations": await self._generate_timeline_recommendations(
                    timeline_issues
                )
            }
            
        except Exception as e:
            logger.error(f"Error checking timeline consistency: {e}")
            return {"error": str(e)}
    
    async def detect_world_rule_violations(self, proposed_action: str, 
                                         world_context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect violations of established world rules"""
        try:
            # Extract world rules from lore
            world_rules = await self._extract_world_rules()
            
            # Check action against each rule
            violations = []
            
            for rule in world_rules:
                violation_check = await self._check_action_against_rule(
                    proposed_action, rule, world_context
                )
                
                if violation_check["violates"]:
                    violations.append(violation_check)
            
            # Check for logical consistency
            logic_violations = await self._check_logical_consistency(
                proposed_action, world_context
            )
            violations.extend(logic_violations)
            
            return {
                "action": proposed_action,
                "violations_detected": len(violations),
                "violations": violations,
                "severity": max([v["severity"] for v in violations]) if violations else 0.0,
                "recommended_modifications": await self._suggest_action_modifications(
                    proposed_action, violations
                )
            }
            
        except Exception as e:
            logger.error(f"Error detecting world rule violations: {e}")
            return {"error": str(e)}
    
    async def perform_full_consistency_check(self) -> Dict[str, Any]:
        """Perform comprehensive consistency check of entire lore database"""
        try:
            logger.info("Starting full consistency check...")
            
            # Clear previous inconsistencies
            self.detected_inconsistencies = []
            
            # Check all entries against each other
            entry_ids = list(self.lore_entries.keys())
            
            for i, entry_id_1 in enumerate(entry_ids):
                for j in range(i + 1, len(entry_ids)):
                    entry_id_2 = entry_ids[j]
                    
                    inconsistencies = await self._check_entries_consistency(
                        entry_id_1, entry_id_2
                    )
                    
                    self.detected_inconsistencies.extend(inconsistencies)
            
            # Check category-specific consistency
            for category in self.category_index.keys():
                category_inconsistencies = await self._check_category_consistency(category)
                self.detected_inconsistencies.extend(category_inconsistencies)
            
            # Update overall consistency score
            await self._update_consistency_score()
            
            # Generate report
            report = await self._generate_consistency_report()
            
            self.last_check_time = datetime.utcnow()
            
            logger.info(f"Full consistency check completed: {len(self.detected_inconsistencies)} "
                       f"issues found, consistency score: {self.consistency_score:.2f}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error performing full consistency check: {e}")
            return {"error": str(e)}
    
    async def get_lore_suggestions(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get lore-consistent suggestions for a query"""
        try:
            # Find relevant lore entries
            relevant_entries = await self._find_relevant_lore(query, context)
            
            # Generate suggestions based on existing lore
            suggestions = await self._generate_lore_based_suggestions(
                query, relevant_entries, context
            )
            
            # Check suggestions for consistency
            consistency_checks = []
            for suggestion in suggestions:
                check = await self.verify_statement(suggestion["text"])
                consistency_checks.append({
                    "suggestion": suggestion,
                    "consistency_check": check
                })
            
            # Filter and rank suggestions
            valid_suggestions = [
                cc for cc in consistency_checks 
                if cc["consistency_check"]["consistent"]
            ]
            
            return {
                "query": query,
                "suggestions_found": len(suggestions),
                "consistent_suggestions": len(valid_suggestions),
                "suggestions": valid_suggestions,
                "relevant_lore_entries": [entry.id for entry in relevant_entries]
            }
            
        except Exception as e:
            logger.error(f"Error getting lore suggestions: {e}")
            return {"error": str(e)}
    
    async def resolve_inconsistency(self, inconsistency_id: str, 
                                  resolution_method: str) -> Dict[str, Any]:
        """Resolve a detected lore inconsistency"""
        try:
            # Find the inconsistency
            inconsistency = next(
                (inc for inc in self.detected_inconsistencies if inc.id == inconsistency_id),
                None
            )
            
            if not inconsistency:
                return {"error": "Inconsistency not found"}
            
            resolution_result = None
            
            if resolution_method == "update_conflicting":
                resolution_result = await self._resolve_by_updating_entries(inconsistency)
            elif resolution_method == "create_explanation":
                resolution_result = await self._resolve_by_explanation(inconsistency)
            elif resolution_method == "mark_exception":
                resolution_result = await self._resolve_by_exception(inconsistency)
            elif resolution_method == "retcon":
                resolution_result = await self._resolve_by_retcon(inconsistency)
            else:
                return {"error": "Unknown resolution method"}
            
            # Mark as resolved
            inconsistency.resolved = True
            
            # Update consistency score
            await self._update_consistency_score()
            
            return {
                "inconsistency_id": inconsistency_id,
                "resolution_method": resolution_method,
                "resolution_result": resolution_result,
                "new_consistency_score": self.consistency_score
            }
            
        except Exception as e:
            logger.error(f"Error resolving inconsistency: {e}")
            return {"error": str(e)}
    
    # Private methods
    
    async def _check_entry_conflicts(self, new_entry: LoreEntry) -> List[Dict[str, Any]]:
        """Check for conflicts between new entry and existing lore"""
        conflicts = []
        
        # Check against entries in same category
        if new_entry.category in self.category_index:
            for existing_entry_id in self.category_index[new_entry.category]:
                existing_entry = self.lore_entries[existing_entry_id]
                
                conflict = await self._check_direct_conflict(new_entry, existing_entry)
                if conflict:
                    conflicts.append(conflict)
        
        # Check name conflicts
        if new_entry.name.lower() in self.name_index:
            existing_entry_id = self.name_index[new_entry.name.lower()]
            existing_entry = self.lore_entries[existing_entry_id]
            
            if existing_entry.id != new_entry.id:  # Different entries with same name
                conflicts.append({
                    "type": "name_conflict",
                    "severity": 0.8,
                    "description": f"Name '{new_entry.name}' already exists",
                    "conflicting_with": [existing_entry_id],
                    "resolution": "Use different name or merge entries"
                })
        
        return conflicts
    
    async def _check_direct_conflict(self, entry1: LoreEntry, entry2: LoreEntry) -> Optional[Dict[str, Any]]:
        """Check for direct conflicts between two lore entries"""
        # Same name, different details
        if entry1.name.lower() == entry2.name.lower() and entry1.id != entry2.id:
            similarity = self._calculate_entry_similarity(entry1, entry2)
            
            if similarity < 0.7:  # Different enough to be conflicting
                return {
                    "type": "content_conflict",
                    "severity": 1.0 - similarity,
                    "description": f"Conflicting information about '{entry1.name}'",
                    "conflicting_with": [entry2.id],
                    "resolution": "Reconcile conflicting details"
                }
        
        # Contradictory statements
        contradictions = self._find_contradictory_statements(entry1, entry2)
        if contradictions:
            return {
                "type": "contradiction",
                "severity": 0.7,
                "description": f"Contradictory statements found",
                "conflicting_with": [entry2.id],
                "details": contradictions,
                "resolution": "Resolve contradictory information"
            }
        
        return None
    
    def _calculate_entry_similarity(self, entry1: LoreEntry, entry2: LoreEntry) -> float:
        """Calculate similarity between two lore entries"""
        cache_key = f"{entry1.id}_{entry2.id}"
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]
        
        # Compare names
        name_similarity = SequenceMatcher(None, entry1.name, entry2.name).ratio()
        
        # Compare descriptions
        desc_similarity = SequenceMatcher(None, entry1.description, entry2.description).ratio()
        
        # Compare details (if both have details)
        details_similarity = 0.5
        if entry1.details and entry2.details:
            details1_str = str(entry1.details)
            details2_str = str(entry2.details)
            details_similarity = SequenceMatcher(None, details1_str, details2_str).ratio()
        
        # Weighted average
        similarity = (name_similarity * 0.4 + desc_similarity * 0.4 + details_similarity * 0.2)
        
        # Cache result
        self.similarity_cache[cache_key] = similarity
        
        return similarity
    
    def _find_contradictory_statements(self, entry1: LoreEntry, entry2: LoreEntry) -> List[str]:
        """Find contradictory statements between entries"""
        contradictions = []
        
        # Simple keyword-based contradiction detection
        contradiction_pairs = [
            ("alive", "dead"),
            ("good", "evil"),
            ("friend", "enemy"),
            ("young", "old"),
            ("rich", "poor"),
            ("strong", "weak")
        ]
        
        text1 = f"{entry1.description} {entry1.details}".lower()
        text2 = f"{entry2.description} {entry2.details}".lower()
        
        for word1, word2 in contradiction_pairs:
            if word1 in text1 and word2 in text2:
                contradictions.append(f"'{word1}' vs '{word2}'")
            elif word2 in text1 and word1 in text2:
                contradictions.append(f"'{word2}' vs '{word1}'")
        
        return contradictions
    
    async def _update_indices(self) -> None:
        """Update all indices"""
        await self._rebuild_indices()
    
    async def _rebuild_indices(self) -> None:
        """Rebuild all indices from current lore entries"""
        self.category_index.clear()
        self.name_index.clear()
        
        for entry_id, entry in self.lore_entries.items():
            await self._update_indices_for_entry(entry)
    
    async def _update_indices_for_entry(self, entry: LoreEntry) -> None:
        """Update indices for a single entry"""
        # Category index
        if entry.category not in self.category_index:
            self.category_index[entry.category] = set()
        self.category_index[entry.category].add(entry.id)
        
        # Name index
        self.name_index[entry.name.lower()] = entry.id
    
    async def _update_consistency_score(self) -> None:
        """Update overall consistency score"""
        if not self.lore_entries:
            self.consistency_score = 1.0
            return
        
        # Count unresolved inconsistencies
        unresolved_inconsistencies = [
            inc for inc in self.detected_inconsistencies if not inc.resolved
        ]
        
        if not unresolved_inconsistencies:
            self.consistency_score = 1.0
            return
        
        # Calculate weighted penalty based on severity
        total_penalty = sum(inc.severity for inc in unresolved_inconsistencies)
        max_possible_penalty = len(self.lore_entries)  # Rough estimate
        
        # Normalize to 0-1 scale
        penalty_ratio = min(1.0, total_penalty / max_possible_penalty) if max_possible_penalty > 0 else 0
        
        self.consistency_score = max(0.0, 1.0 - penalty_ratio)
    
    async def _extract_facts_from_statement(self, statement: str) -> List[Dict[str, Any]]:
        """Extract verifiable facts from a statement"""
        # Use AI to extract facts
        try:
            prompt = f"""
            Extract specific, verifiable facts from this statement:
            "{statement}"
            
            Return facts in the format:
            - Subject: [who/what]
            - Predicate: [action/property]
            - Object: [what/how]
            
            Focus on concrete, checkable facts.
            """
            
            response = await self.ai_client.generate_completion(prompt, max_tokens=200)
            
            # Parse response into fact objects
            # This would be more sophisticated in a real implementation
            facts = [
                {
                    "text": statement,  # Simplified - would extract individual facts
                    "subject": "",
                    "predicate": "",
                    "object": "",
                    "confidence": 0.7
                }
            ]
            
            return facts
            
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return []
    
    async def _verify_single_fact(self, fact: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Verify a single fact against lore database"""
        fact_text = fact.get("text", "")
        
        # Find potentially relevant lore entries
        relevant_entries = await self._find_relevant_lore(fact_text, context)
        
        # Check each relevant entry
        supports_fact = []
        contradicts_fact = []
        
        for entry in relevant_entries:
            relationship = await self._determine_fact_entry_relationship(fact, entry)
            
            if relationship == "supports":
                supports_fact.append(entry.id)
            elif relationship == "contradicts":
                contradicts_fact.append(entry.id)
        
        # Determine consistency
        consistent = len(contradicts_fact) == 0
        confidence = len(supports_fact) / max(1, len(relevant_entries)) if relevant_entries else 0.5
        
        return {
            "fact": fact,
            "consistent": consistent,
            "confidence": confidence,
            "supporting_entries": supports_fact,
            "contradicting_entries": contradicts_fact,
            "relevant_entries_checked": len(relevant_entries)
        }
    
    async def _find_relevant_lore(self, query: str, context: Dict[str, Any] = None) -> List[LoreEntry]:
        """Find lore entries relevant to a query"""
        relevant_entries = []
        query_lower = query.lower()
        
        # Simple keyword matching
        for entry in self.lore_entries.values():
            entry_text = f"{entry.name} {entry.description}".lower()
            
            # Check for keyword overlap
            query_words = set(query_lower.split())
            entry_words = set(entry_text.split())
            overlap = len(query_words.intersection(entry_words))
            
            if overlap > 0:
                relevance_score = overlap / len(query_words)
                if relevance_score > 0.3:  # Threshold for relevance
                    relevant_entries.append(entry)
        
        # Sort by relevance (simplified)
        return relevant_entries[:10]  # Return top 10
    
    async def _determine_fact_entry_relationship(self, fact: Dict[str, Any], 
                                               entry: LoreEntry) -> str:
        """Determine relationship between fact and lore entry"""
        fact_text = fact.get("text", "").lower()
        entry_text = f"{entry.description} {entry.details}".lower()
        
        # Simple heuristic - would use AI in real implementation
        if fact_text in entry_text or any(word in entry_text for word in fact_text.split()):
            return "supports"
        
        # Check for contradictions
        contradiction_indicators = ["not", "never", "isn't", "wasn't", "cannot"]
        if any(indicator in entry_text for indicator in contradiction_indicators):
            return "contradicts"
        
        return "neutral"
    
    async def _calculate_statement_confidence(self, statement: str, 
                                           verification_results: List[Dict[str, Any]]) -> float:
        """Calculate confidence in statement verification"""
        if not verification_results:
            return 0.5
        
        fact_confidences = [result.get("confidence", 0.5) for result in verification_results]
        return sum(fact_confidences) / len(fact_confidences)
    
    async def _suggest_statement_corrections(self, statement: str,
                                           verification_results: List[Dict[str, Any]]) -> List[str]:
        """Suggest corrections for inconsistent statements"""
        corrections = []
        
        for result in verification_results:
            if not result["consistent"] and result["contradicting_entries"]:
                corrections.append(f"Check against lore entries: {result['contradicting_entries']}")
        
        return corrections
    
    async def _find_character_entries(self, character_id: str) -> List[LoreEntry]:
        """Find lore entries related to a character"""
        character_entries = []
        
        for entry in self.lore_entries.values():
            if (entry.category == "character" and 
                (character_id in entry.name.lower() or character_id in str(entry.details).lower())):
                character_entries.append(entry)
        
        return character_entries
    
    async def _check_character_info_consistency(self, character_id: str, 
                                              info_type: str, info_value: Any,
                                              existing_entries: List[LoreEntry]) -> Dict[str, Any]:
        """Check consistency of specific character information"""
        for entry in existing_entries:
            existing_value = entry.details.get(info_type) if entry.details else None
            
            if existing_value is not None and existing_value != info_value:
                return {
                    "consistent": False,
                    "info_type": info_type,
                    "new_value": info_value,
                    "existing_value": existing_value,
                    "conflicting_entry": entry.id,
                    "severity": 0.7
                }
        
        return {"consistent": True, "info_type": info_type}
    
    async def _generate_character_consistency_recommendations(self, inconsistencies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for character consistency issues"""
        recommendations = []
        
        for inconsistency in inconsistencies:
            info_type = inconsistency.get("info_type", "unknown")
            recommendations.append(f"Resolve {info_type} inconsistency - update or explain difference")
        
        return recommendations
    
    async def _check_temporal_consistency(self, earlier_event: NarrativeEvent, 
                                        later_event: NarrativeEvent) -> Optional[Dict[str, Any]]:
        """Check temporal consistency between two events"""
        # Check for impossible causality
        # This would be more sophisticated in a real implementation
        
        # Simple example: character can't be in two places at once
        if (earlier_event.participants and later_event.participants and
            set(earlier_event.participants).intersection(set(later_event.participants))):
            
            time_diff = (later_event.timestamp - earlier_event.timestamp).total_seconds()
            if time_diff < 3600:  # Less than 1 hour
                return {
                    "type": "temporal_inconsistency",
                    "severity": 0.5,
                    "description": "Character appears in multiple locations within short timeframe",
                    "events": [earlier_event.id, later_event.id]
                }
        
        return None
    
    async def _check_event_against_lore(self, event: NarrativeEvent) -> List[Dict[str, Any]]:
        """Check event consistency against lore entries"""
        conflicts = []
        
        # Find relevant lore entries
        relevant_entries = await self._find_relevant_lore(event.description)
        
        for entry in relevant_entries:
            # Check for contradictions
            # This would be more sophisticated in a real implementation
            if any(word in event.description.lower() for word in ["impossible", "never", "cannot"]):
                conflicts.append({
                    "type": "lore_violation",
                    "severity": 0.6,
                    "description": f"Event may violate established lore in entry {entry.id}",
                    "event": event.id,
                    "conflicting_entry": entry.id
                })
        
        return conflicts
    
    def _calculate_timeline_consistency_score(self, issues: List[Dict[str, Any]], 
                                           total_events: int) -> float:
        """Calculate timeline consistency score"""
        if total_events == 0:
            return 1.0
        
        issue_penalty = sum(issue.get("severity", 0.5) for issue in issues)
        max_penalty = total_events  # Rough estimate
        
        penalty_ratio = min(1.0, issue_penalty / max_penalty) if max_penalty > 0 else 0
        return max(0.0, 1.0 - penalty_ratio)
    
    async def _generate_timeline_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for timeline issues"""
        recommendations = []
        
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            if issue_type == "temporal_inconsistency":
                recommendations.append("Consider travel time between locations")
            elif issue_type == "lore_violation":
                recommendations.append("Check event against established world rules")
        
        return recommendations
    
    async def _extract_world_rules(self) -> List[Dict[str, Any]]:
        """Extract world rules from lore entries"""
        world_rules = []
        
        for entry in self.lore_entries.values():
            if entry.category == "world_rule" or "rule" in entry.name.lower():
                world_rules.append({
                    "entry_id": entry.id,
                    "rule_text": entry.description,
                    "details": entry.details
                })
        
        return world_rules
    
    async def _check_action_against_rule(self, action: str, rule: Dict[str, Any],
                                       world_context: Dict[str, Any]) -> Dict[str, Any]:
        """Check action against a specific world rule"""
        rule_text = rule.get("rule_text", "").lower()
        action_lower = action.lower()
        
        # Simple violation detection
        violation_keywords = ["cannot", "impossible", "forbidden", "never"]
        
        for keyword in violation_keywords:
            if keyword in rule_text:
                # Extract what's forbidden
                rule_parts = rule_text.split(keyword)
                if len(rule_parts) > 1:
                    forbidden_action = rule_parts[1].strip()
                    
                    if forbidden_action in action_lower:
                        return {
                            "violates": True,
                            "rule_id": rule["entry_id"],
                            "violation_type": "explicit_prohibition",
                            "severity": 0.8,
                            "description": f"Action violates rule: {rule_text}"
                        }
        
        return {"violates": False}
    
    async def _check_logical_consistency(self, action: str, 
                                       world_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check action for logical consistency"""
        violations = []
        
        # Simple logical checks
        action_lower = action.lower()
        
        # Check for impossible combinations
        if "fly" in action_lower and "underground" in action_lower:
            violations.append({
                "violates": True,
                "violation_type": "logical_impossibility",
                "severity": 0.9,
                "description": "Cannot fly underground"
            })
        
        return violations
    
    async def _suggest_action_modifications(self, action: str, 
                                          violations: List[Dict[str, Any]]) -> List[str]:
        """Suggest modifications to make action consistent"""
        modifications = []
        
        for violation in violations:
            violation_type = violation.get("violation_type", "unknown")
            
            if violation_type == "explicit_prohibition":
                modifications.append("Remove or modify the prohibited element")
            elif violation_type == "logical_impossibility":
                modifications.append("Choose one aspect or find alternative approach")
        
        return modifications
    
    async def _check_entries_consistency(self, entry_id_1: str, 
                                       entry_id_2: str) -> List[LoreInconsistency]:
        """Check consistency between two specific entries"""
        entry1 = self.lore_entries.get(entry_id_1)
        entry2 = self.lore_entries.get(entry_id_2)
        
        if not entry1 or not entry2:
            return []
        
        inconsistencies = []
        
        # Check for conflicts
        conflict = await self._check_direct_conflict(entry1, entry2)
        if conflict:
            inconsistency = LoreInconsistency(
                inconsistency_type=conflict["type"],
                severity=conflict["severity"],
                description=conflict["description"],
                conflicting_entries=[entry_id_1, entry_id_2],
                suggested_resolution=conflict.get("resolution", "")
            )
            inconsistencies.append(inconsistency)
        
        return inconsistencies
    
    async def _check_category_consistency(self, category: str) -> List[LoreInconsistency]:
        """Check consistency within a category"""
        category_inconsistencies = []
        
        if category not in self.category_index:
            return category_inconsistencies
        
        entry_ids = list(self.category_index[category])
        
        # Check for duplicate names within category
        names_seen = {}
        for entry_id in entry_ids:
            entry = self.lore_entries[entry_id]
            name_lower = entry.name.lower()
            
            if name_lower in names_seen:
                inconsistency = LoreInconsistency(
                    inconsistency_type="duplicate_name",
                    severity=0.6,
                    description=f"Duplicate name '{entry.name}' in category '{category}'",
                    conflicting_entries=[entry_id, names_seen[name_lower]],
                    suggested_resolution="Rename one entry or merge if they're the same thing"
                )
                category_inconsistencies.append(inconsistency)
            else:
                names_seen[name_lower] = entry_id
        
        return category_inconsistencies
    
    async def _generate_consistency_report(self) -> Dict[str, Any]:
        """Generate comprehensive consistency report"""
        report = {
            "overall_consistency_score": self.consistency_score,
            "total_lore_entries": len(self.lore_entries),
            "total_inconsistencies": len(self.detected_inconsistencies),
            "unresolved_inconsistencies": len([inc for inc in self.detected_inconsistencies if not inc.resolved]),
            "inconsistencies_by_type": {},
            "inconsistencies_by_severity": {},
            "category_breakdown": {},
            "recommendations": []
        }
        
        # Analyze inconsistencies by type
        for inconsistency in self.detected_inconsistencies:
            inc_type = inconsistency.type
            if inc_type not in report["inconsistencies_by_type"]:
                report["inconsistencies_by_type"][inc_type] = 0
            report["inconsistencies_by_type"][inc_type] += 1
            
            # By severity
            severity_bucket = "high" if inconsistency.severity > 0.7 else "medium" if inconsistency.severity > 0.3 else "low"
            if severity_bucket not in report["inconsistencies_by_severity"]:
                report["inconsistencies_by_severity"][severity_bucket] = 0
            report["inconsistencies_by_severity"][severity_bucket] += 1
        
        # Category breakdown
        for category, entry_ids in self.category_index.items():
            report["category_breakdown"][category] = len(entry_ids)
        
        # Generate recommendations
        if report["unresolved_inconsistencies"] > 0:
            report["recommendations"].append("Resolve inconsistencies to improve lore quality")
        if self.consistency_score < 0.8:
            report["recommendations"].append("Consider reviewing and consolidating lore entries")
        
        return report
    
    async def _generate_lore_based_suggestions(self, query: str, 
                                             relevant_entries: List[LoreEntry],
                                             context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate suggestions based on existing lore"""
        suggestions = []
        
        for entry in relevant_entries[:5]:  # Top 5 most relevant
            suggestion = {
                "text": f"Based on {entry.name}: {entry.description}",
                "source_entry": entry.id,
                "confidence": 0.7,
                "category": entry.category
            }
            suggestions.append(suggestion)
        
        return suggestions
    
    # Resolution methods
    
    async def _resolve_by_updating_entries(self, inconsistency: LoreInconsistency) -> Dict[str, Any]:
        """Resolve inconsistency by updating conflicting entries"""
        # This would update the conflicting entries to make them consistent
        return {
            "method": "update_entries",
            "entries_updated": inconsistency.conflicting_entries,
            "description": "Updated conflicting entries to resolve inconsistency"
        }
    
    async def _resolve_by_explanation(self, inconsistency: LoreInconsistency) -> Dict[str, Any]:
        """Resolve inconsistency by adding explanatory lore"""
        return {
            "method": "add_explanation",
            "description": "Added explanatory lore to account for apparent inconsistency"
        }
    
    async def _resolve_by_exception(self, inconsistency: LoreInconsistency) -> Dict[str, Any]:
        """Resolve inconsistency by marking as special exception"""
        return {
            "method": "mark_exception",
            "description": "Marked as legitimate exception to general rule"
        }
    
    async def _resolve_by_retcon(self, inconsistency: LoreInconsistency) -> Dict[str, Any]:
        """Resolve inconsistency by retconning (changing established facts)"""
        return {
            "method": "retcon",
            "description": "Retconned conflicting information",
            "warning": "This changes established facts - inform players"
        }