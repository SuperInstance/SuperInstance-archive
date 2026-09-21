"""
Rule lookup and search service.
"""

import re
import math
from typing import List, Dict, Optional, Tuple, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func, text
from uuid import uuid4
from datetime import datetime
from collections import defaultdict, Counter
from difflib import SequenceMatcher

from models.rules import (
    Rule, RuleInterpretation, RuleClarification, SearchIndex,
    RuleSchema, RuleInterpretationSchema, RuleClarificationSchema,
    RuleSearchQuery, RuleSearchResult, RuleReference, RuleCollection,
    QuickReference, RuleConflict, SearchSuggestion,
    RuleType, GameSystemRule, RuleCategory
)

class SearchEngine:
    """Advanced search engine for rules with fuzzy matching and relevance scoring."""
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text for search processing."""
        # Convert to lowercase and split on non-alphanumeric characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return [token for token in tokens if len(token) > 2]  # Filter short words
    
    @staticmethod
    def calculate_relevance_score(query_tokens: List[str], rule: Rule, match_type: str = "") -> float:
        """Calculate relevance score for a rule based on query tokens."""
        score = 0.0
        
        # Title matches have highest weight
        title_tokens = SearchEngine.tokenize(rule.title)
        title_matches = sum(1 for token in query_tokens if token in title_tokens)
        if title_matches > 0:
            score += title_matches * 10.0
        
        # Exact phrase matches in title
        if len(query_tokens) > 1:
            query_phrase = " ".join(query_tokens)
            if query_phrase in rule.title.lower():
                score += 15.0
        
        # Summary matches
        if rule.summary:
            summary_tokens = SearchEngine.tokenize(rule.summary)
            summary_matches = sum(1 for token in query_tokens if token in summary_tokens)
            score += summary_matches * 5.0
        
        # Content matches (lower weight due to length)
        content_tokens = SearchEngine.tokenize(rule.content)
        content_matches = sum(1 for token in query_tokens if token in content_tokens)
        score += content_matches * 2.0
        
        # Tag matches
        if rule.tags:
            tag_tokens = []
            for tag in rule.tags:
                tag_tokens.extend(SearchEngine.tokenize(tag))
            tag_matches = sum(1 for token in query_tokens if token in tag_tokens)
            score += tag_matches * 7.0
        
        # Keyword matches
        if rule.keywords:
            keyword_tokens = []
            for keyword in rule.keywords:
                keyword_tokens.extend(SearchEngine.tokenize(keyword))
            keyword_matches = sum(1 for token in query_tokens if token in keyword_tokens)
            score += keyword_matches * 8.0
        
        # Boost popular rules slightly
        if rule.view_count > 0:
            popularity_boost = math.log10(rule.view_count + 1) * 0.1
            score += popularity_boost
        
        # Boost official rules
        if rule.is_official:
            score += 1.0
        
        return score
    
    @staticmethod
    def fuzzy_match_score(query: str, text: str) -> float:
        """Calculate fuzzy matching score using sequence similarity."""
        return SequenceMatcher(None, query.lower(), text.lower()).ratio()
    
    @staticmethod
    def find_fuzzy_matches(query_tokens: List[str], rules: List[Rule], threshold: float = 0.6) -> List[Tuple[Rule, float]]:
        """Find rules using fuzzy string matching."""
        matches = []
        
        for rule in rules:
            # Check fuzzy matches in title
            for token in query_tokens:
                title_score = SearchEngine.fuzzy_match_score(token, rule.title)
                if title_score >= threshold:
                    relevance = title_score * 10.0  # High weight for title matches
                    matches.append((rule, relevance))
                    break
            
            # Check fuzzy matches in tags/keywords
            if rule.tags:
                for tag in rule.tags:
                    for token in query_tokens:
                        tag_score = SearchEngine.fuzzy_match_score(token, tag)
                        if tag_score >= threshold:
                            relevance = tag_score * 5.0
                            matches.append((rule, relevance))
                            break
        
        return matches

class RuleIndexer:
    """Indexes rules for efficient searching."""
    
    @staticmethod
    def create_search_index(rule: Rule, db: Session) -> SearchIndex:
        """Create or update search index for a rule."""
        # Combine all searchable text
        search_parts = [
            rule.title,
            rule.summary or "",
            rule.content,
            " ".join(rule.tags or []),
            " ".join(rule.keywords or [])
        ]
        
        search_text = " ".join(search_parts).lower()
        
        # Check if index exists
        existing_index = db.query(SearchIndex).filter(
            SearchIndex.rule_id == rule.id
        ).first()
        
        if existing_index:
            existing_index.search_text = search_text
            db.commit()
            return existing_index
        else:
            search_index = SearchIndex(
                id=str(uuid4()),
                rule_id=rule.id,
                search_text=search_text
            )
            db.add(search_index)
            db.commit()
            return search_index
    
    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract keywords from rule text."""
        # Common RPG keywords to boost
        rpg_terms = {
            'attack', 'damage', 'spell', 'action', 'bonus action', 'reaction',
            'saving throw', 'ability check', 'skill check', 'advantage', 'disadvantage',
            'concentration', 'ritual', 'cantrip', 'hit points', 'armor class',
            'proficiency', 'modifier', 'level', 'class', 'race', 'feat'
        }
        
        tokens = SearchEngine.tokenize(text)
        keywords = []
        
        # Add RPG terms found in text
        for term in rpg_terms:
            if term in text.lower():
                keywords.append(term)
        
        # Add frequent meaningful words
        word_freq = Counter(tokens)
        for word, freq in word_freq.most_common(10):
            if len(word) > 4 and freq > 1:
                keywords.append(word)
        
        return list(set(keywords))

class RuleValidator:
    """Validates rules and checks for conflicts."""
    
    @staticmethod
    def find_rule_conflicts(rules: List[Rule]) -> List[RuleConflict]:
        """Find potential conflicts between rules."""
        conflicts = []
        
        # Group rules by category for comparison
        by_category = defaultdict(list)
        for rule in rules:
            by_category[rule.category].append(rule)
        
        # Check for conflicting rules within categories
        for category, category_rules in by_category.items():
            for i, rule1 in enumerate(category_rules):
                for rule2 in category_rules[i+1:]:
                    conflict = RuleValidator._check_rule_pair_conflict(rule1, rule2)
                    if conflict:
                        conflicts.append(conflict)
        
        return conflicts
    
    @staticmethod
    def _check_rule_pair_conflict(rule1: Rule, rule2: Rule) -> Optional[RuleConflict]:
        """Check if two rules conflict with each other."""
        # Simple conflict detection - look for contradictory language
        contradiction_patterns = [
            (r'\bcannot\b', r'\bcan\b'),
            (r'\bmust\b', r'\bmay\b'),
            (r'\brequired\b', r'\boptional\b'),
            (r'\balways\b', r'\bnever\b')
        ]
        
        rule1_text = f"{rule1.title} {rule1.content}".lower()
        rule2_text = f"{rule2.title} {rule2.content}".lower()
        
        for pattern1, pattern2 in contradiction_patterns:
            if (re.search(pattern1, rule1_text) and re.search(pattern2, rule2_text)) or \
               (re.search(pattern2, rule1_text) and re.search(pattern1, rule2_text)):
                
                return RuleConflict(
                    rule1_id=rule1.id,
                    rule2_id=rule2.id,
                    conflict_description=f"Potential contradiction between '{rule1.title}' and '{rule2.title}'",
                    severity="moderate"
                )
        
        return None

class RulesService:
    """Main rules service handling database operations and search."""
    
    def __init__(self):
        self.search_engine = SearchEngine()
        self.indexer = RuleIndexer()
        self.validator = RuleValidator()
    
    def create_rule(self, rule_data: RuleSchema, db: Session) -> Rule:
        """Create a new rule."""
        # Extract keywords automatically
        keywords = self.indexer.extract_keywords(f"{rule_data.title} {rule_data.content}")
        
        rule = Rule(
            id=str(uuid4()),
            title=rule_data.title,
            content=rule_data.content,
            summary=rule_data.summary,
            rule_type=rule_data.rule_type.value,
            game_system=rule_data.game_system.value,
            category=rule_data.category.value,
            source_book=rule_data.source_book,
            page_number=rule_data.page_number,
            tags=rule_data.tags,
            keywords=keywords + (rule_data.keywords or []),
            related_rules=rule_data.related_rules,
            prerequisites=rule_data.prerequisites,
            version=rule_data.version,
            is_active=rule_data.is_active,
            is_official=rule_data.is_official
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        # Create search index
        self.indexer.create_search_index(rule, db)
        
        return rule
    
    def get_rule(self, rule_id: str, db: Session) -> Optional[Rule]:
        """Get a rule by ID."""
        return db.query(Rule).filter(Rule.id == rule_id).first()
    
    def search_rules(self, query: RuleSearchQuery, db: Session) -> List[RuleSearchResult]:
        """Search for rules based on query parameters."""
        # Start with base query
        base_query = db.query(Rule).filter(Rule.is_active == True)
        
        # Apply filters
        if query.game_system:
            base_query = base_query.filter(Rule.game_system == query.game_system.value)
        
        if query.rule_types:
            base_query = base_query.filter(Rule.rule_type.in_([rt.value for rt in query.rule_types]))
        
        if query.categories:
            base_query = base_query.filter(Rule.category.in_([cat.value for cat in query.categories]))
        
        if not query.include_unofficial:
            base_query = base_query.filter(Rule.is_official == True)
        
        if query.source_books:
            base_query = base_query.filter(Rule.source_book.in_(query.source_books))
        
        # Get all matching rules
        rules = base_query.all()
        
        if not rules:
            return []
        
        # Tokenize search query
        query_tokens = self.search_engine.tokenize(query.query)
        
        # Calculate relevance scores
        scored_rules = []
        
        for rule in rules:
            # Exact token matching
            score = self.search_engine.calculate_relevance_score(query_tokens, rule)
            
            if score > 0:
                scored_rules.append((rule, score, "exact"))
        
        # Fuzzy matching if enabled and we have few exact matches
        if query.fuzzy_search and len(scored_rules) < 5:
            fuzzy_matches = self.search_engine.find_fuzzy_matches(query_tokens, rules)
            for rule, score in fuzzy_matches:
                # Avoid duplicates
                if not any(existing_rule.id == rule.id for existing_rule, _, _ in scored_rules):
                    scored_rules.append((rule, score, "fuzzy"))
        
        # Tag-based filtering
        if query.tags:
            tag_filtered = []
            for rule, score, match_type in scored_rules:
                if rule.tags and any(tag in rule.tags for tag in query.tags):
                    score += 5.0  # Boost for tag matches
                    tag_filtered.append((rule, score, match_type))
            scored_rules = tag_filtered
        
        # Sort by relevance or specified criteria
        if query.sort_by == "relevance":
            scored_rules.sort(key=lambda x: x[1], reverse=True)
        elif query.sort_by == "title":
            scored_rules.sort(key=lambda x: x[0].title)
        elif query.sort_by == "category":
            scored_rules.sort(key=lambda x: x[0].category)
        elif query.sort_by == "view_count":
            scored_rules.sort(key=lambda x: x[0].view_count, reverse=True)
        
        # Limit results
        scored_rules = scored_rules[:query.max_results]
        
        # Build search results
        results = []
        for rule, score, match_type in scored_rules:
            # Get interpretations if requested
            interpretations = None
            if query.include_interpretations:
                interp_query = db.query(RuleInterpretation).filter(
                    RuleInterpretation.rule_id == rule.id
                ).order_by(desc(RuleInterpretation.upvotes)).limit(3)
                interpretations = [RuleInterpretationSchema.from_orm(interp) for interp in interp_query.all()]
            
            # Get clarifications if requested
            clarifications = None
            if query.include_clarifications:
                clarif_query = db.query(RuleClarification).filter(
                    RuleClarification.rule_id == rule.id
                ).order_by(desc(RuleClarification.confidence_level)).limit(3)
                clarifications = [RuleClarificationSchema.from_orm(clarif) for clarif in clarif_query.all()]
            
            # Find matched text snippet
            matched_text = self._extract_matched_text(query.query, rule, match_type)
            
            result = RuleSearchResult(
                rule=RuleSchema.from_orm(rule),
                relevance_score=score,
                match_type=match_type,
                matched_text=matched_text,
                interpretations=interpretations,
                clarifications=clarifications
            )
            results.append(result)
        
        return results
    
    def _extract_matched_text(self, query: str, rule: Rule, match_type: str) -> Optional[str]:
        """Extract relevant text snippet showing the match."""
        query_lower = query.lower()
        
        # Check title first
        if query_lower in rule.title.lower():
            return rule.title
        
        # Check summary
        if rule.summary and query_lower in rule.summary.lower():
            return self._get_text_snippet(rule.summary, query_lower)
        
        # Check content
        if query_lower in rule.content.lower():
            return self._get_text_snippet(rule.content, query_lower)
        
        return None
    
    def _get_text_snippet(self, text: str, query: str, context_chars: int = 100) -> str:
        """Extract a snippet of text around the matched query."""
        query_pos = text.lower().find(query.lower())
        if query_pos == -1:
            return text[:context_chars] + "..." if len(text) > context_chars else text
        
        start = max(0, query_pos - context_chars // 2)
        end = min(len(text), query_pos + len(query) + context_chars // 2)
        
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def get_quick_reference(self, game_system: GameSystemRule, category: RuleCategory, db: Session) -> QuickReference:
        """Generate a quick reference sheet for common rules."""
        rules = db.query(Rule).filter(
            and_(
                Rule.game_system == game_system.value,
                Rule.category == category.value,
                Rule.is_active == True,
                Rule.is_official == True
            )
        ).order_by(Rule.view_count.desc()).limit(20).all()
        
        # Group rules by common subcategories
        sections = defaultdict(list)
        
        for rule in rules:
            # Determine section based on rule type or content analysis
            section = self._categorize_rule_for_reference(rule)
            
            sections[section].append(RuleReference(
                rule_id=rule.id,
                title=rule.title,
                summary=rule.summary,
                category=RuleCategory(rule.category),
                source_book=rule.source_book,
                page_number=rule.page_number
            ))
        
        return QuickReference(
            title=f"{game_system.value.upper()} {category.value.title()} Quick Reference",
            game_system=game_system,
            sections=dict(sections)
        )
    
    def _categorize_rule_for_reference(self, rule: Rule) -> str:
        """Categorize a rule for quick reference organization."""
        title_lower = rule.title.lower()
        content_lower = rule.content.lower()
        
        if rule.category == "combat":
            if any(word in title_lower for word in ["attack", "weapon", "damage"]):
                return "Attacks & Damage"
            elif any(word in title_lower for word in ["action", "movement", "turn"]):
                return "Actions & Movement"
            elif any(word in title_lower for word in ["condition", "status"]):
                return "Conditions"
            else:
                return "General Combat"
        
        elif rule.category == "spellcasting":
            if any(word in title_lower for word in ["cantrip", "0-level"]):
                return "Cantrips"
            elif any(word in title_lower for word in ["concentration", "ritual"]):
                return "Spell Mechanics"
            else:
                return "Spellcasting"
        
        return rule.rule_type.replace("_", " ").title()
    
    def create_interpretation(self, interp_data: RuleInterpretationSchema, db: Session) -> RuleInterpretation:
        """Add an interpretation to a rule."""
        interpretation = RuleInterpretation(
            id=str(uuid4()),
            rule_id=interp_data.rule_id,
            title=interp_data.title,
            interpretation=interp_data.interpretation,
            reasoning=interp_data.reasoning,
            author_id=interp_data.author_id,
            is_official=interp_data.is_official,
            is_verified=interp_data.is_verified
        )
        
        db.add(interpretation)
        db.commit()
        db.refresh(interpretation)
        
        return interpretation
    
    def create_clarification(self, clarif_data: RuleClarificationSchema, db: Session) -> RuleClarification:
        """Add a clarification to a rule."""
        clarification = RuleClarification(
            id=str(uuid4()),
            rule_id=clarif_data.rule_id,
            question=clarif_data.question,
            answer=clarif_data.answer,
            source=clarif_data.source,
            confidence_level=clarif_data.confidence_level
        )
        
        db.add(clarification)
        db.commit()
        db.refresh(clarification)
        
        return clarification
    
    def increment_view_count(self, rule_id: str, db: Session) -> None:
        """Increment view count and update last viewed time."""
        rule = db.query(Rule).filter(Rule.id == rule_id).first()
        if rule:
            rule.view_count += 1
            rule.last_viewed = datetime.utcnow()
            db.commit()
    
    def get_search_suggestions(self, partial_query: str, game_system: Optional[GameSystemRule], db: Session) -> List[SearchSuggestion]:
        """Get search suggestions for autocomplete."""
        suggestions = []
        
        # Rule title suggestions
        title_query = db.query(Rule.title).filter(
            and_(
                Rule.title.ilike(f"%{partial_query}%"),
                Rule.is_active == True,
                Rule.game_system == game_system.value if game_system else True
            )
        ).limit(5)
        
        for title, in title_query.all():
            suggestions.append(SearchSuggestion(
                suggestion=title,
                suggestion_type="rule_title",
                frequency=1
            ))
        
        # Tag suggestions
        tag_query = db.query(Rule).filter(
            and_(
                Rule.is_active == True,
                Rule.game_system == game_system.value if game_system else True
            )
        ).all()
        
        all_tags = []
        for rule in tag_query:
            if rule.tags:
                all_tags.extend(rule.tags)
        
        matching_tags = [tag for tag in set(all_tags) if partial_query.lower() in tag.lower()]
        for tag in matching_tags[:3]:
            suggestions.append(SearchSuggestion(
                suggestion=tag,
                suggestion_type="tag",
                frequency=all_tags.count(tag)
            ))
        
        return suggestions
    
    def get_related_rules(self, rule_id: str, db: Session, max_results: int = 5) -> List[RuleReference]:
        """Get rules related to the specified rule."""
        rule = db.query(Rule).filter(Rule.id == rule_id).first()
        if not rule:
            return []
        
        related_rules = []
        
        # Direct relationships
        if rule.related_rules:
            direct_related = db.query(Rule).filter(
                and_(
                    Rule.id.in_(rule.related_rules),
                    Rule.is_active == True
                )
            ).all()
            
            for related in direct_related:
                related_rules.append(RuleReference(
                    rule_id=related.id,
                    title=related.title,
                    summary=related.summary,
                    category=RuleCategory(related.category),
                    source_book=related.source_book,
                    page_number=related.page_number
                ))
        
        # Same category rules
        if len(related_rules) < max_results:
            category_rules = db.query(Rule).filter(
                and_(
                    Rule.category == rule.category,
                    Rule.id != rule_id,
                    Rule.is_active == True,
                    Rule.game_system == rule.game_system
                )
            ).order_by(desc(Rule.view_count)).limit(max_results - len(related_rules)).all()
            
            for cat_rule in category_rules:
                if not any(ref.rule_id == cat_rule.id for ref in related_rules):
                    related_rules.append(RuleReference(
                        rule_id=cat_rule.id,
                        title=cat_rule.title,
                        summary=cat_rule.summary,
                        category=RuleCategory(cat_rule.category),
                        source_book=cat_rule.source_book,
                        page_number=cat_rule.page_number
                    ))
        
        return related_rules[:max_results]
    
    def find_rule_conflicts(self, game_system: GameSystemRule, db: Session) -> List[RuleConflict]:
        """Find potential conflicts between rules in a game system."""
        rules = db.query(Rule).filter(
            and_(
                Rule.game_system == game_system.value,
                Rule.is_active == True
            )
        ).all()
        
        return self.validator.find_rule_conflicts(rules)