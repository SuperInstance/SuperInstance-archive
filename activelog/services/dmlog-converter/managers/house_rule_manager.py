"""
House rule manager for creating, validating, and applying custom rules
"""

from typing import Dict, List, Any, Optional, Set
from enum import Enum
from datetime import datetime
from ..models.base import HouseRule, ValidationResult, ConversionResult
from ..config.systems import GameSystem


class RuleCategory(Enum):
    COMBAT = "combat"
    MAGIC = "magic"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    CHARACTER_CREATION = "character_creation"
    ADVANCEMENT = "advancement"
    EQUIPMENT = "equipment"
    GENERAL = "general"


class RuleImpact(Enum):
    MINOR = "minor"      # Small tweaks, no major balance impact
    MODERATE = "moderate" # Noticeable changes, some balance considerations
    MAJOR = "major"      # Significant changes, careful review needed
    EXTREME = "extreme"  # Fundamental changes to core mechanics


class HouseRuleManager:
    """Manages house rules and their application to game systems"""
    
    def __init__(self):
        self.active_rules: Dict[str, HouseRule] = {}
        self.rule_templates: Dict[str, Dict[str, Any]] = {}
        self.rule_conflicts: Dict[str, Set[str]] = {}
        self.system_integrations: Dict[GameSystem, List[str]] = {}
        
        # Initialize common rule templates
        self._initialize_rule_templates()
    
    def create_house_rule(
        self, 
        name: str,
        system: GameSystem,
        category: RuleCategory,
        description: str,
        rationale: str = "",
        replaces: Optional[List[str]] = None,
        modifies: Optional[List[str]] = None,
        adds: Optional[List[str]] = None,
        procedure: Optional[List[str]] = None,
        examples: Optional[List[str]] = None,
        created_by: str = "user"
    ) -> HouseRule:
        """Create a new house rule"""
        
        house_rule = HouseRule(
            name=name,
            system=system,
            category=category.value,
            description=description,
            rationale=rationale,
            replaces=replaces or [],
            modifies=modifies or [],
            adds=adds or [],
            procedure=procedure or [],
            examples=examples or [],
            created_by=created_by
        )
        
        self.active_rules[house_rule.id] = house_rule
        return house_rule
    
    def validate_house_rule(self, rule: HouseRule) -> ValidationResult:
        """Validate a house rule for balance and compatibility"""
        
        result = ValidationResult(
            valid=True,
            content_type="house_rule",
            content_id=rule.id,
            system=rule.system
        )
        
        try:
            # Check rule completeness
            completeness_issues = self._check_rule_completeness(rule)
            result.missing_required_fields.extend(completeness_issues)
            
            # Check for conflicts with existing rules
            conflicts = self._check_rule_conflicts(rule)
            if conflicts:
                result.warnings.extend([f"Conflicts with rule: {conflict}" for conflict in conflicts])
            
            # Analyze rule impact
            impact_analysis = self._analyze_rule_impact(rule)
            result.suggestions.extend(impact_analysis["suggestions"])
            
            if impact_analysis["impact"] == RuleImpact.EXTREME:
                result.warnings.append("This rule has extreme impact - careful playtesting recommended")
            
            # Check balance implications
            balance_issues = self._check_balance_implications(rule)
            result.warnings.extend(balance_issues)
            
            # Check system compatibility
            compatibility_issues = self._check_system_compatibility(rule)
            result.semantic_errors.extend(compatibility_issues)
            
            # Calculate scores
            result.completeness_score = self._calculate_completeness_score(rule)
            result.clarity_score = self._calculate_clarity_score(rule)
            result.consistency_score = self._calculate_consistency_score(rule)
            
            # Determine overall validity
            if result.semantic_errors or result.completeness_score < 0.6:
                result.valid = False
            elif result.warnings and result.completeness_score < 0.8:
                result.suggestions.append("Consider addressing warnings before implementation")
            
        except Exception as e:
            result.valid = False
            result.semantic_errors.append(f"Validation failed: {str(e)}")
        
        return result
    
    def apply_house_rules(
        self, 
        content_data: Dict[str, Any],
        content_type: str,
        rule_ids: List[str]
    ) -> ConversionResult:
        """Apply house rules to game content"""
        
        result = ConversionResult(
            success=True,
            source_system=GameSystem.D_AND_D_5E,  # Default
            target_system=GameSystem.D_AND_D_5E
        )
        
        try:
            modified_content = content_data.copy()
            applied_rules = []
            
            for rule_id in rule_ids:
                if rule_id not in self.active_rules:
                    result.warnings.append(f"Rule {rule_id} not found")
                    continue
                
                rule = self.active_rules[rule_id]
                
                # Validate rule before applying
                validation = self.validate_house_rule(rule)
                if not validation.valid:
                    result.warnings.append(f"Rule {rule.name} failed validation")
                    continue
                
                # Apply rule modifications
                rule_application = self._apply_single_rule(
                    modified_content, content_type, rule
                )
                
                if rule_application["success"]:
                    modified_content = rule_application["modified_content"]
                    applied_rules.append(rule.name)
                    result.conversion_notes.extend(rule_application["notes"])
                else:
                    result.warnings.extend(rule_application["errors"])
            
            result.converted_data = modified_content
            result.conversion_notes.append(f"Applied rules: {', '.join(applied_rules)}")
            
            # Calculate confidence based on number of successful applications
            success_rate = len(applied_rules) / len(rule_ids) if rule_ids else 1.0
            result.conversion_confidence = max(0.5, success_rate * 0.9)
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Rule application failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def suggest_house_rules(
        self, 
        system: GameSystem,
        content_type: str,
        content_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest house rules that might improve the content"""
        
        suggestions = []
        
        # Analyze content for common issues
        issues = self._analyze_content_issues(content_data, content_type)
        
        # Suggest rules based on issues found
        for issue in issues:
            matching_templates = self._find_matching_templates(issue, system)
            suggestions.extend(matching_templates)
        
        # Suggest popular rules for the system
        popular_rules = self._get_popular_rules(system, content_type)
        suggestions.extend(popular_rules)
        
        return suggestions[:10]  # Limit to top 10 suggestions
    
    def get_rule_conflicts(self, rule_id: str) -> List[str]:
        """Get list of rules that conflict with the given rule"""
        
        if rule_id not in self.active_rules:
            return []
        
        rule = self.active_rules[rule_id]
        conflicts = []
        
        for other_id, other_rule in self.active_rules.items():
            if other_id == rule_id:
                continue
            
            if self._rules_conflict(rule, other_rule):
                conflicts.append(other_id)
        
        return conflicts
    
    def export_house_rules(self, rule_ids: List[str]) -> Dict[str, Any]:
        """Export house rules in a shareable format"""
        
        export_data = {
            "format_version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "rules": []
        }
        
        for rule_id in rule_ids:
            if rule_id in self.active_rules:
                rule = self.active_rules[rule_id]
                export_data["rules"].append(rule.dict())
        
        return export_data
    
    def import_house_rules(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import house rules from exported data"""
        
        result = {
            "imported": [],
            "skipped": [],
            "errors": []
        }
        
        try:
            rules_data = import_data.get("rules", [])
            
            for rule_data in rules_data:
                try:
                    rule = HouseRule(**rule_data)
                    
                    # Check for duplicates
                    if any(existing.name == rule.name and existing.system == rule.system 
                           for existing in self.active_rules.values()):
                        result["skipped"].append(f"Rule '{rule.name}' already exists")
                        continue
                    
                    # Validate imported rule
                    validation = self.validate_house_rule(rule)
                    if not validation.valid:
                        result["errors"].append(f"Rule '{rule.name}' failed validation")
                        continue
                    
                    self.active_rules[rule.id] = rule
                    result["imported"].append(rule.name)
                
                except Exception as e:
                    result["errors"].append(f"Failed to import rule: {str(e)}")
        
        except Exception as e:
            result["errors"].append(f"Import failed: {str(e)}")
        
        return result
    
    def _initialize_rule_templates(self):
        """Initialize common rule templates"""
        
        self.rule_templates = {
            "critical_hit_tables": {
                "name": "Critical Hit Tables",
                "category": RuleCategory.COMBAT,
                "description": "Use critical hit tables for more dramatic critical hits",
                "impact": RuleImpact.MODERATE,
                "systems": [GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E]
            },
            "gritty_realism": {
                "name": "Gritty Realism Rest Rules",
                "category": RuleCategory.GENERAL,
                "description": "Short rests take 8 hours, long rests take a week",
                "impact": RuleImpact.MAJOR,
                "systems": [GameSystem.D_AND_D_5E]
            },
            "spell_points": {
                "name": "Spell Points Variant",
                "category": RuleCategory.MAGIC,
                "description": "Use spell points instead of spell slots",
                "impact": RuleImpact.MAJOR,
                "systems": [GameSystem.D_AND_D_5E]
            },
            "flanking": {
                "name": "Flanking Rules",
                "category": RuleCategory.COMBAT,
                "description": "Flanking grants advantage on attack rolls",
                "impact": RuleImpact.MODERATE,
                "systems": [GameSystem.D_AND_D_5E]
            },
            "background_skills": {
                "name": "Background Skill Bonuses",
                "category": RuleCategory.CHARACTER_CREATION,
                "description": "Backgrounds grant additional skill proficiencies",
                "impact": RuleImpact.MINOR,
                "systems": [GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E]
            }
        }
    
    def _check_rule_completeness(self, rule: HouseRule) -> List[str]:
        """Check if a rule has all required information"""
        
        issues = []
        
        if not rule.name.strip():
            issues.append("Rule name is required")
        
        if not rule.description.strip():
            issues.append("Rule description is required")
        
        if not rule.replaces and not rule.modifies and not rule.adds:
            issues.append("Rule must specify what it replaces, modifies, or adds")
        
        if not rule.procedure and rule.adds:
            issues.append("Rules that add new mechanics should include procedures")
        
        return issues
    
    def _check_rule_conflicts(self, rule: HouseRule) -> List[str]:
        """Check for conflicts with existing rules"""
        
        conflicts = []
        
        for existing_id, existing_rule in self.active_rules.items():
            if existing_rule.system != rule.system:
                continue
            
            if self._rules_conflict(rule, existing_rule):
                conflicts.append(existing_rule.name)
        
        return conflicts
    
    def _rules_conflict(self, rule1: HouseRule, rule2: HouseRule) -> bool:
        """Check if two rules conflict with each other"""
        
        # Check if they modify the same mechanics
        rule1_mechanics = set(rule1.replaces + rule1.modifies)
        rule2_mechanics = set(rule2.replaces + rule2.modifies)
        
        if rule1_mechanics & rule2_mechanics:
            return True
        
        # Check if one replaces what the other modifies
        if set(rule1.replaces) & set(rule2.modifies):
            return True
        
        if set(rule2.replaces) & set(rule1.modifies):
            return True
        
        return False
    
    def _analyze_rule_impact(self, rule: HouseRule) -> Dict[str, Any]:
        """Analyze the impact level of a house rule"""
        
        impact_score = 0
        suggestions = []
        
        # Check what the rule affects
        if rule.replaces:
            impact_score += len(rule.replaces) * 3
            suggestions.append("Replacing core mechanics increases impact significantly")
        
        if rule.modifies:
            impact_score += len(rule.modifies) * 2
        
        if rule.adds:
            impact_score += len(rule.adds) * 1
        
        # Analyze rule category impact
        category_impact = {
            "combat": 2, "magic": 3, "character_creation": 2,
            "advancement": 3, "general": 1
        }
        impact_score += category_impact.get(rule.category, 1)
        
        # Determine impact level
        if impact_score <= 3:
            impact = RuleImpact.MINOR
        elif impact_score <= 6:
            impact = RuleImpact.MODERATE
        elif impact_score <= 10:
            impact = RuleImpact.MAJOR
        else:
            impact = RuleImpact.EXTREME
            suggestions.append("Consider breaking this into smaller rules")
        
        return {"impact": impact, "score": impact_score, "suggestions": suggestions}
    
    def _check_balance_implications(self, rule: HouseRule) -> List[str]:
        """Check for potential balance issues"""
        
        issues = []
        
        # Check for power creep indicators
        description_lower = rule.description.lower()
        power_keywords = ["always", "automatically", "free", "bonus", "extra", "additional"]
        
        for keyword in power_keywords:
            if keyword in description_lower:
                issues.append(f"Keyword '{keyword}' may indicate power creep")
        
        # Check for complexity issues
        if len(rule.procedure) > 10:
            issues.append("Complex rules may slow down gameplay")
        
        # Check for vague language
        vague_keywords = ["reasonable", "appropriate", "as needed", "when necessary"]
        for keyword in vague_keywords:
            if keyword in description_lower:
                issues.append(f"Vague language '{keyword}' may lead to confusion")
        
        return issues
    
    def _check_system_compatibility(self, rule: HouseRule) -> List[str]:
        """Check if rule is compatible with the target system"""
        
        issues = []
        
        # Check for system-specific terminology
        system_terms = {
            GameSystem.D_AND_D_5E: ["advantage", "disadvantage", "proficiency", "spell slot"],
            GameSystem.PATHFINDER_2E: ["fortune", "misfortune", "proficiency", "spell point"]
        }
        
        rule_text = (rule.description + " " + " ".join(rule.procedure)).lower()
        
        for system, terms in system_terms.items():
            if system != rule.system:
                for term in terms:
                    if term in rule_text:
                        issues.append(f"Uses {system.value} terminology: '{term}'")
        
        return issues
    
    def _calculate_completeness_score(self, rule: HouseRule) -> float:
        """Calculate how complete a rule definition is"""
        
        score = 0.0
        max_score = 0.0
        
        # Required fields
        if rule.name.strip():
            score += 2.0
        max_score += 2.0
        
        if rule.description.strip():
            score += 2.0
        max_score += 2.0
        
        # Optional but recommended fields
        if rule.rationale.strip():
            score += 1.0
        max_score += 1.0
        
        if rule.procedure:
            score += 1.5
        max_score += 1.5
        
        if rule.examples:
            score += 1.0
        max_score += 1.0
        
        if rule.replaces or rule.modifies or rule.adds:
            score += 1.5
        max_score += 1.5
        
        return score / max_score if max_score > 0 else 0.0
    
    def _calculate_clarity_score(self, rule: HouseRule) -> float:
        """Calculate how clear and well-written a rule is"""
        
        score = 1.0
        
        # Check description length
        desc_words = len(rule.description.split())
        if desc_words < 10:
            score -= 0.3  # Too short
        elif desc_words > 100:
            score -= 0.2  # Too long
        
        # Check for clear structure
        if rule.procedure and len(rule.procedure) > 1:
            score += 0.1  # Well-structured procedure
        
        # Check for examples
        if rule.examples:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_consistency_score(self, rule: HouseRule) -> float:
        """Calculate how consistent a rule is with system conventions"""
        
        # This would check terminology, formatting, etc.
        # For now, return a reasonable default
        return 0.8
    
    def _apply_single_rule(
        self, 
        content: Dict[str, Any], 
        content_type: str, 
        rule: HouseRule
    ) -> Dict[str, Any]:
        """Apply a single house rule to content"""
        
        result = {
            "success": True,
            "modified_content": content.copy(),
            "notes": [],
            "errors": []
        }
        
        try:
            # Apply rule based on what it does
            if rule.replaces:
                for replaced_mechanic in rule.replaces:
                    result["notes"].append(f"Replaced {replaced_mechanic} with {rule.name}")
            
            if rule.modifies:
                for modified_mechanic in rule.modifies:
                    result["notes"].append(f"Modified {modified_mechanic} using {rule.name}")
            
            if rule.adds:
                for added_mechanic in rule.adds:
                    result["notes"].append(f"Added {added_mechanic} from {rule.name}")
            
            # Apply specific modifications based on content type
            if content_type == "character":
                result["modified_content"] = self._apply_rule_to_character(
                    result["modified_content"], rule
                )
            elif content_type == "monster":
                result["modified_content"] = self._apply_rule_to_monster(
                    result["modified_content"], rule
                )
            # Add more content types as needed
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"Failed to apply rule {rule.name}: {str(e)}")
        
        return result
    
    def _apply_rule_to_character(self, character: Dict[str, Any], rule: HouseRule) -> Dict[str, Any]:
        """Apply rule specifically to character data"""
        
        # Example implementations for common rule categories
        if rule.category == "character_creation":
            if "background_skills" in rule.name.lower():
                # Add extra skill proficiencies
                character["skills"] = character.get("skills", {})
                character["skills"]["house_rule_bonus"] = "Applied background skill bonuses"
        
        return character
    
    def _apply_rule_to_monster(self, monster: Dict[str, Any], rule: HouseRule) -> Dict[str, Any]:
        """Apply rule specifically to monster data"""
        
        if rule.category == "combat":
            if "critical" in rule.name.lower():
                # Modify critical hit mechanics
                monster["house_rules"] = monster.get("house_rules", [])
                monster["house_rules"].append(f"Uses {rule.name}")
        
        return monster
    
    def _analyze_content_issues(self, content: Dict[str, Any], content_type: str) -> List[str]:
        """Analyze content for common issues that house rules might address"""
        
        issues = []
        
        # Generic analysis - could be expanded for specific content types
        if content_type == "character":
            # Check for low-powered characters
            level = content.get("level", 1)
            if level > 10 and not content.get("magic_items"):
                issues.append("high_level_low_magic")
        
        return issues
    
    def _find_matching_templates(self, issue: str, system: GameSystem) -> List[Dict[str, Any]]:
        """Find rule templates that address a specific issue"""
        
        matches = []
        
        issue_templates = {
            "high_level_low_magic": ["spell_points", "background_skills"],
            "slow_combat": ["flanking", "critical_hit_tables"]
        }
        
        template_names = issue_templates.get(issue, [])
        
        for template_name in template_names:
            if template_name in self.rule_templates:
                template = self.rule_templates[template_name]
                if system in template.get("systems", []):
                    matches.append({
                        "template_id": template_name,
                        "name": template["name"],
                        "category": template["category"].value,
                        "description": template["description"],
                        "impact": template["impact"].value
                    })
        
        return matches
    
    def _get_popular_rules(self, system: GameSystem, content_type: str) -> List[Dict[str, Any]]:
        """Get popular rules for a system and content type"""
        
        # This would normally query a database of popular rules
        # For now, return some common ones
        popular = []
        
        if system == GameSystem.D_AND_D_5E:
            popular.extend([
                {
                    "template_id": "flanking",
                    "name": "Flanking Rules",
                    "category": "combat",
                    "description": "Flanking grants advantage",
                    "popularity": 0.8
                },
                {
                    "template_id": "gritty_realism",
                    "name": "Gritty Realism",
                    "category": "general",
                    "description": "Longer rest periods",
                    "popularity": 0.3
                }
            ])
        
        return popular