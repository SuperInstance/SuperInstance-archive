"""
Gift Suggestion Engine

AI-powered system for generating personalized gift recommendations based on
recipient preferences, relationship context, occasion analysis, and budget
considerations using machine learning and social intelligence.
"""

import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from enum import Enum
import numpy as np
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GiftCategory(Enum):
    BOOKS = "books"
    TECHNOLOGY = "technology"
    FASHION = "fashion"
    HOME_DECOR = "home_decor"
    EXPERIENCES = "experiences"
    FOOD_DRINK = "food_drink"
    HOBBY_CRAFTS = "hobby_crafts"
    HEALTH_FITNESS = "health_fitness"
    TRAVEL = "travel"
    ART_CULTURE = "art_culture"
    GAMES_TOYS = "games_toys"
    JEWELRY = "jewelry"
    SUBSCRIPTION = "subscription"
    PERSONALIZED = "personalized"
    CHARITABLE = "charitable"

class OccasionType(Enum):
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    WEDDING = "wedding"
    GRADUATION = "graduation"
    PROMOTION = "promotion"
    HOUSEWARMING = "housewarming"
    HOLIDAY = "holiday"
    CHRISTMAS = "christmas"
    VALENTINES = "valentines"
    MOTHERS_DAY = "mothers_day"
    FATHERS_DAY = "fathers_day"
    THANK_YOU = "thank_you"
    APOLOGY = "apology"
    GET_WELL = "get_well"
    RETIREMENT = "retirement"
    BABY_SHOWER = "baby_shower"
    JUST_BECAUSE = "just_because"

class RelationshipLevel(Enum):
    FAMILY_CLOSE = "family_close"
    FAMILY_EXTENDED = "family_extended"
    ROMANTIC_PARTNER = "romantic_partner"
    CLOSE_FRIEND = "close_friend"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    BOSS = "boss"
    ACQUAINTANCE = "acquaintance"
    BUSINESS_CLIENT = "business_client"

class PersonalityTrait(Enum):
    CREATIVE = "creative"
    PRACTICAL = "practical"
    ADVENTUROUS = "adventurous"
    INTROVERTED = "introverted"
    EXTROVERTED = "extroverted"
    TECH_SAVVY = "tech_savvy"
    TRADITIONAL = "traditional"
    MINIMALIST = "minimalist"
    LUXURIOUS = "luxurious"
    ECO_CONSCIOUS = "eco_conscious"
    FITNESS_ORIENTED = "fitness_oriented"
    INTELLECTUAL = "intellectual"

@dataclass
class RecipientProfile:
    user_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    interests: List[str] = field(default_factory=list)
    hobbies: List[str] = field(default_factory=list)
    personality_traits: List[PersonalityTrait] = field(default_factory=list)
    preferred_categories: List[GiftCategory] = field(default_factory=list)
    disliked_categories: List[GiftCategory] = field(default_factory=list)
    lifestyle: Dict[str, Any] = field(default_factory=dict)
    past_gifts_received: List[str] = field(default_factory=list)
    past_gifts_given: List[str] = field(default_factory=list)
    cultural_background: Optional[str] = None
    living_situation: Optional[str] = None  # apartment, house, etc.
    professional_context: Optional[str] = None
    social_media_activity: Dict[str, Any] = field(default_factory=dict)
    recent_life_events: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class GiftItem:
    item_id: str
    name: str
    description: str
    category: GiftCategory
    price_min: float
    price_max: float
    occasion_suitability: List[OccasionType] = field(default_factory=list)
    personality_match: List[PersonalityTrait] = field(default_factory=list)
    age_range: Tuple[int, int] = (0, 100)
    gender_preference: Optional[str] = None
    relationship_levels: List[RelationshipLevel] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    personalization_options: List[str] = field(default_factory=list)
    delivery_time: int = 7  # days
    popularity_score: float = 0.5
    uniqueness_score: float = 0.5
    practicality_score: float = 0.5
    emotional_impact_score: float = 0.5
    vendor_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GiftSuggestion:
    suggestion_id: str
    recipient_id: str
    giver_id: str
    occasion: OccasionType
    recommended_item: GiftItem
    confidence_score: float
    personalization_suggestions: List[str] = field(default_factory=list)
    reasoning: str = ""
    alternative_items: List[str] = field(default_factory=list)
    budget_justification: str = ""
    timing_recommendations: str = ""
    presentation_tips: List[str] = field(default_factory=list)
    generated_date: datetime = field(default_factory=datetime.now)
    feedback_score: Optional[float] = None

@dataclass
class GiftContext:
    occasion: OccasionType
    budget_min: float
    budget_max: float
    relationship_level: RelationshipLevel
    urgency: int = 5  # 1-10 scale
    surprise_factor: bool = True
    group_gift: bool = False
    cultural_considerations: List[str] = field(default_factory=list)
    special_requirements: List[str] = field(default_factory=list)
    shipping_constraints: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GiftTrend:
    trend_id: str
    trend_name: str
    category: GiftCategory
    popularity_growth: float
    target_demographics: List[str] = field(default_factory=list)
    seasonal_relevance: Dict[str, float] = field(default_factory=dict)
    price_trend: str = "stable"  # increasing, decreasing, stable
    social_media_buzz: float = 0.5
    sustainability_rating: float = 0.5
    identified_date: datetime = field(default_factory=datetime.now)

class GiftSuggestionEngine:
    def __init__(self, db_path: str = "social_ai.db"):
        self.db_path = db_path
        self.gift_catalog = {}
        self.personalization_rules = {}
        self.cultural_preferences = {}
        self.seasonal_adjustments = {}
        self.init_database()
        self._load_gift_catalog()
        self._load_personalization_rules()
        
    def init_database(self):
        """Initialize database tables for gift suggestion system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipient_profiles (
                user_id TEXT PRIMARY KEY,
                age INTEGER,
                gender TEXT,
                interests TEXT,
                hobbies TEXT,
                personality_traits TEXT,
                preferred_categories TEXT,
                disliked_categories TEXT,
                lifestyle TEXT,
                past_gifts_received TEXT,
                past_gifts_given TEXT,
                cultural_background TEXT,
                living_situation TEXT,
                professional_context TEXT,
                social_media_activity TEXT,
                recent_life_events TEXT,
                last_updated TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gift_catalog (
                item_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                category TEXT,
                price_min REAL,
                price_max REAL,
                occasion_suitability TEXT,
                personality_match TEXT,
                age_range TEXT,
                gender_preference TEXT,
                relationship_levels TEXT,
                tags TEXT,
                personalization_options TEXT,
                delivery_time INTEGER,
                popularity_score REAL,
                uniqueness_score REAL,
                practicality_score REAL,
                emotional_impact_score REAL,
                vendor_info TEXT,
                added_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gift_suggestions (
                suggestion_id TEXT PRIMARY KEY,
                recipient_id TEXT,
                giver_id TEXT,
                occasion TEXT,
                recommended_item_id TEXT,
                confidence_score REAL,
                personalization_suggestions TEXT,
                reasoning TEXT,
                alternative_items TEXT,
                budget_justification TEXT,
                timing_recommendations TEXT,
                presentation_tips TEXT,
                generated_date TIMESTAMP,
                feedback_score REAL,
                FOREIGN KEY (recommended_item_id) REFERENCES gift_catalog (item_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gift_feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_id TEXT,
                recipient_id TEXT,
                giver_id TEXT,
                success_rating REAL,
                recipient_reaction REAL,
                appropriateness_rating REAL,
                value_perception REAL,
                feedback_text TEXT,
                feedback_date TIMESTAMP,
                FOREIGN KEY (suggestion_id) REFERENCES gift_suggestions (suggestion_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gift_trends (
                trend_id TEXT PRIMARY KEY,
                trend_name TEXT,
                category TEXT,
                popularity_growth REAL,
                target_demographics TEXT,
                seasonal_relevance TEXT,
                price_trend TEXT,
                social_media_buzz REAL,
                sustainability_rating REAL,
                identified_date TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Gift suggestion engine database initialized")

    def _load_gift_catalog(self):
        """Load sample gift catalog"""
        sample_gifts = [
            GiftItem(
                item_id="book_001",
                name="Bestselling Fiction Novel",
                description="Latest bestseller from acclaimed author",
                category=GiftCategory.BOOKS,
                price_min=12.99,
                price_max=24.99,
                occasion_suitability=[OccasionType.BIRTHDAY, OccasionType.THANK_YOU, OccasionType.JUST_BECAUSE],
                personality_match=[PersonalityTrait.INTELLECTUAL, PersonalityTrait.INTROVERTED],
                age_range=(16, 80),
                relationship_levels=[RelationshipLevel.FRIEND, RelationshipLevel.COLLEAGUE, RelationshipLevel.CLOSE_FRIEND],
                tags=["reading", "literature", "fiction", "entertainment"],
                personalization_options=["signed copy", "book inscription", "gift wrapping"],
                popularity_score=0.8,
                practicality_score=0.7,
                emotional_impact_score=0.6
            ),
            GiftItem(
                item_id="tech_001",
                name="Wireless Earbuds",
                description="High-quality noise-cancelling wireless earbuds",
                category=GiftCategory.TECHNOLOGY,
                price_min=79.99,
                price_max=199.99,
                occasion_suitability=[OccasionType.BIRTHDAY, OccasionType.GRADUATION, OccasionType.PROMOTION],
                personality_match=[PersonalityTrait.TECH_SAVVY, PersonalityTrait.FITNESS_ORIENTED, PersonalityTrait.PRACTICAL],
                age_range=(13, 65),
                relationship_levels=[RelationshipLevel.CLOSE_FRIEND, RelationshipLevel.FAMILY_CLOSE, RelationshipLevel.ROMANTIC_PARTNER],
                tags=["technology", "music", "wireless", "modern"],
                personalization_options=["engraving", "custom case", "color choice"],
                popularity_score=0.9,
                practicality_score=0.9,
                emotional_impact_score=0.7
            ),
            GiftItem(
                item_id="exp_001",
                name="Cooking Class Experience",
                description="Professional cooking class with chef instructor",
                category=GiftCategory.EXPERIENCES,
                price_min=75.00,
                price_max=150.00,
                occasion_suitability=[OccasionType.BIRTHDAY, OccasionType.ANNIVERSARY, OccasionType.VALENTINES],
                personality_match=[PersonalityTrait.CREATIVE, PersonalityTrait.ADVENTUROUS, PersonalityTrait.EXTROVERTED],
                age_range=(18, 70),
                relationship_levels=[RelationshipLevel.ROMANTIC_PARTNER, RelationshipLevel.CLOSE_FRIEND, RelationshipLevel.FAMILY_CLOSE],
                tags=["experience", "cooking", "learning", "social", "food"],
                personalization_options=["cuisine type", "private class", "couple's class"],
                uniqueness_score=0.8,
                emotional_impact_score=0.9,
                practicality_score=0.6
            ),
            GiftItem(
                item_id="home_001",
                name="Aromatherapy Diffuser Set",
                description="Essential oil diffuser with starter oil collection",
                category=GiftCategory.HOME_DECOR,
                price_min=35.00,
                price_max=85.00,
                occasion_suitability=[OccasionType.HOUSEWARMING, OccasionType.BIRTHDAY, OccasionType.THANK_YOU],
                personality_match=[PersonalityTrait.MINIMALIST, PersonalityTrait.ECO_CONSCIOUS, PersonalityTrait.INTROVERTED],
                age_range=(22, 65),
                relationship_levels=[RelationshipLevel.FRIEND, RelationshipLevel.COLLEAGUE, RelationshipLevel.FAMILY_EXTENDED],
                tags=["wellness", "aromatherapy", "home", "relaxation", "self-care"],
                personalization_options=["oil selection", "custom engraving", "decorative design"],
                popularity_score=0.7,
                practicality_score=0.8,
                emotional_impact_score=0.7
            ),
            GiftItem(
                item_id="fitness_001",
                name="Smart Fitness Tracker",
                description="Advanced fitness tracker with health monitoring",
                category=GiftCategory.HEALTH_FITNESS,
                price_min=99.99,
                price_max=249.99,
                occasion_suitability=[OccasionType.BIRTHDAY, OccasionType.GRADUATION, OccasionType.PROMOTION],
                personality_match=[PersonalityTrait.FITNESS_ORIENTED, PersonalityTrait.TECH_SAVVY, PersonalityTrait.PRACTICAL],
                age_range=(16, 60),
                relationship_levels=[RelationshipLevel.CLOSE_FRIEND, RelationshipLevel.FAMILY_CLOSE, RelationshipLevel.ROMANTIC_PARTNER],
                tags=["fitness", "health", "technology", "tracking", "motivation"],
                personalization_options=["band color", "engraving", "fitness goals setup"],
                popularity_score=0.8,
                practicality_score=0.9,
                emotional_impact_score=0.6
            )
        ]
        
        # Store in memory and database
        for gift in sample_gifts:
            self.gift_catalog[gift.item_id] = gift
            asyncio.create_task(self._save_gift_item(gift))

    def _load_personalization_rules(self):
        """Load personalization rules for different contexts"""
        self.personalization_rules = {
            RelationshipLevel.ROMANTIC_PARTNER: {
                "personalization_importance": 0.9,
                "emotional_weight": 0.8,
                "surprise_factor": 0.9,
                "budget_flexibility": 0.7,
                "preferred_categories": [GiftCategory.JEWELRY, GiftCategory.EXPERIENCES, GiftCategory.PERSONALIZED]
            },
            RelationshipLevel.FAMILY_CLOSE: {
                "personalization_importance": 0.7,
                "emotional_weight": 0.8,
                "surprise_factor": 0.6,
                "budget_flexibility": 0.6,
                "preferred_categories": [GiftCategory.EXPERIENCES, GiftCategory.HOME_DECOR, GiftCategory.BOOKS]
            },
            RelationshipLevel.CLOSE_FRIEND: {
                "personalization_importance": 0.6,
                "emotional_weight": 0.7,
                "surprise_factor": 0.8,
                "budget_flexibility": 0.5,
                "preferred_categories": [GiftCategory.EXPERIENCES, GiftCategory.HOBBY_CRAFTS, GiftCategory.TECHNOLOGY]
            },
            RelationshipLevel.COLLEAGUE: {
                "personalization_importance": 0.3,
                "emotional_weight": 0.4,
                "surprise_factor": 0.3,
                "budget_flexibility": 0.4,
                "preferred_categories": [GiftCategory.FOOD_DRINK, GiftCategory.BOOKS, GiftCategory.SUBSCRIPTION]
            }
        }

    async def create_recipient_profile(self, user_id: str, **profile_data) -> RecipientProfile:
        """
        Create or update recipient profile
        
        Args:
            user_id: User identifier
            **profile_data: Profile information
            
        Returns:
            Created recipient profile
        """
        profile = RecipientProfile(
            user_id=user_id,
            age=profile_data.get('age'),
            gender=profile_data.get('gender'),
            interests=profile_data.get('interests', []),
            hobbies=profile_data.get('hobbies', []),
            personality_traits=[PersonalityTrait(t) for t in profile_data.get('personality_traits', [])],
            preferred_categories=[GiftCategory(c) for c in profile_data.get('preferred_categories', [])],
            disliked_categories=[GiftCategory(c) for c in profile_data.get('disliked_categories', [])],
            lifestyle=profile_data.get('lifestyle', {}),
            cultural_background=profile_data.get('cultural_background'),
            living_situation=profile_data.get('living_situation'),
            professional_context=profile_data.get('professional_context')
        )
        
        await self._save_recipient_profile(profile)
        logger.info(f"Created recipient profile for {user_id}")
        return profile

    async def suggest_gifts(self, recipient_id: str, giver_id: str, 
                          context: GiftContext,
                          num_suggestions: int = 5) -> List[GiftSuggestion]:
        """
        Generate personalized gift suggestions
        
        Args:
            recipient_id: Recipient user ID
            giver_id: Giver user ID  
            context: Gift context (occasion, budget, etc.)
            num_suggestions: Number of suggestions to generate
            
        Returns:
            List of ranked gift suggestions
        """
        # Get recipient profile
        recipient_profile = await self.get_recipient_profile(recipient_id)
        if not recipient_profile:
            # Create basic profile if none exists
            recipient_profile = RecipientProfile(user_id=recipient_id)
        
        # Get candidate gifts
        candidate_gifts = await self._filter_candidate_gifts(context, recipient_profile)
        
        if not candidate_gifts:
            logger.warning(f"No candidate gifts found for recipient {recipient_id}")
            return []
        
        # Score and rank gifts
        scored_gifts = []
        for gift in candidate_gifts:
            score = self._calculate_gift_score(gift, recipient_profile, context)
            scored_gifts.append((gift, score))
        
        # Sort by score
        scored_gifts.sort(key=lambda x: x[1], reverse=True)
        
        # Generate suggestions
        suggestions = []
        for i, (gift, score) in enumerate(scored_gifts[:num_suggestions]):
            suggestion = await self._create_gift_suggestion(
                gift, recipient_profile, giver_id, context, score, i
            )
            suggestions.append(suggestion)
        
        # Save suggestions
        for suggestion in suggestions:
            await self._save_gift_suggestion(suggestion)
        
        logger.info(f"Generated {len(suggestions)} gift suggestions for {recipient_id}")
        return suggestions

    async def _filter_candidate_gifts(self, context: GiftContext, 
                                    recipient_profile: RecipientProfile) -> List[GiftItem]:
        """Filter gift catalog based on context and recipient"""
        candidates = []
        
        for gift in self.gift_catalog.values():
            # Budget filter
            if not (context.budget_min <= gift.price_max and context.budget_max >= gift.price_min):
                continue
            
            # Occasion filter
            if context.occasion not in gift.occasion_suitability and gift.occasion_suitability:
                continue
            
            # Age filter
            if recipient_profile.age:
                if not (gift.age_range[0] <= recipient_profile.age <= gift.age_range[1]):
                    continue
            
            # Gender filter
            if gift.gender_preference and recipient_profile.gender:
                if gift.gender_preference != recipient_profile.gender:
                    continue
            
            # Relationship level filter
            if context.relationship_level not in gift.relationship_levels and gift.relationship_levels:
                continue
            
            # Category preferences
            if recipient_profile.disliked_categories:
                if gift.category in recipient_profile.disliked_categories:
                    continue
            
            # Past gifts filter (avoid repeating recent gifts)
            if gift.name in recipient_profile.past_gifts_received[-5:]:  # Last 5 gifts
                continue
            
            candidates.append(gift)
        
        return candidates

    def _calculate_gift_score(self, gift: GiftItem, recipient_profile: RecipientProfile,
                            context: GiftContext) -> float:
        """Calculate comprehensive gift score"""
        score = 0.0
        
        # Base compatibility scores
        occasion_score = 1.0 if context.occasion in gift.occasion_suitability else 0.3
        score += occasion_score * 0.2
        
        # Personality matching
        personality_match = len(set(recipient_profile.personality_traits) & set(gift.personality_match))
        personality_score = min(personality_match / max(len(gift.personality_match), 1), 1.0)
        score += personality_score * 0.25
        
        # Interest alignment
        interest_matches = sum(1 for interest in recipient_profile.interests 
                             if any(interest.lower() in tag.lower() for tag in gift.tags))
        interest_score = min(interest_matches / max(len(recipient_profile.interests), 1), 1.0)
        score += interest_score * 0.2
        
        # Category preference
        category_score = 0.5  # neutral
        if gift.category in recipient_profile.preferred_categories:
            category_score = 1.0
        elif gift.category in recipient_profile.disliked_categories:
            category_score = 0.0
        score += category_score * 0.15
        
        # Relationship appropriateness
        relationship_rules = self.personalization_rules.get(context.relationship_level, {})
        
        # Emotional impact weighting
        emotional_weight = relationship_rules.get("emotional_weight", 0.5)
        score += gift.emotional_impact_score * emotional_weight * 0.1
        
        # Practicality consideration
        practicality_weight = 1.0 - emotional_weight  # Inverse relationship
        score += gift.practicality_score * practicality_weight * 0.05
        
        # Uniqueness for surprise factor
        if context.surprise_factor:
            uniqueness_weight = relationship_rules.get("surprise_factor", 0.5)
            score += gift.uniqueness_score * uniqueness_weight * 0.05
        
        # Budget optimization
        budget_fit = self._calculate_budget_fit(gift, context)
        score += budget_fit * 0.1
        
        return min(score, 1.0)

    def _calculate_budget_fit(self, gift: GiftItem, context: GiftContext) -> float:
        """Calculate how well gift fits budget"""
        budget_midpoint = (context.budget_min + context.budget_max) / 2
        gift_midpoint = (gift.price_min + gift.price_max) / 2
        
        # Prefer gifts near budget midpoint
        budget_range = context.budget_max - context.budget_min
        if budget_range == 0:
            return 1.0 if context.budget_min >= gift.price_min else 0.0
        
        deviation = abs(gift_midpoint - budget_midpoint) / budget_range
        return max(0.0, 1.0 - deviation)

    async def _create_gift_suggestion(self, gift: GiftItem, recipient_profile: RecipientProfile,
                                    giver_id: str, context: GiftContext, 
                                    score: float, rank: int) -> GiftSuggestion:
        """Create comprehensive gift suggestion"""
        suggestion_id = f"suggestion_{recipient_profile.user_id}_{giver_id}_{int(datetime.now().timestamp())}_{rank}"
        
        # Generate personalization suggestions
        personalization = self._generate_personalization_suggestions(gift, recipient_profile, context)
        
        # Generate reasoning
        reasoning = self._generate_gift_reasoning(gift, recipient_profile, context, score)
        
        # Find alternative items
        alternatives = await self._find_alternative_gifts(gift, context, recipient_profile)
        
        # Budget justification
        budget_justification = self._generate_budget_justification(gift, context)
        
        # Timing recommendations
        timing = self._generate_timing_recommendations(gift, context)
        
        # Presentation tips
        presentation = self._generate_presentation_tips(gift, context)
        
        return GiftSuggestion(
            suggestion_id=suggestion_id,
            recipient_id=recipient_profile.user_id,
            giver_id=giver_id,
            occasion=context.occasion,
            recommended_item=gift,
            confidence_score=score,
            personalization_suggestions=personalization,
            reasoning=reasoning,
            alternative_items=alternatives,
            budget_justification=budget_justification,
            timing_recommendations=timing,
            presentation_tips=presentation
        )

    def _generate_personalization_suggestions(self, gift: GiftItem, 
                                            recipient_profile: RecipientProfile,
                                            context: GiftContext) -> List[str]:
        """Generate personalization suggestions"""
        suggestions = []
        
        # Use available personalization options
        if gift.personalization_options:
            for option in gift.personalization_options[:3]:  # Top 3 options
                if option == "engraving":
                    suggestions.append("Consider engraving with recipient's name or meaningful date")
                elif option == "custom message":
                    suggestions.append("Add a personalized message reflecting your relationship")
                elif option == "color choice":
                    suggestions.append("Choose color based on recipient's preferences")
                else:
                    suggestions.append(f"Consider {option} to make it more personal")
        
        # Relationship-specific suggestions
        relationship_rules = self.personalization_rules.get(context.relationship_level, {})
        if relationship_rules.get("personalization_importance", 0) > 0.6:
            suggestions.append("Include a handwritten note explaining why you chose this gift")
        
        # Occasion-specific suggestions
        if context.occasion == OccasionType.BIRTHDAY:
            suggestions.append("Consider delivery on their actual birthday for maximum impact")
        elif context.occasion == OccasionType.ANNIVERSARY:
            suggestions.append("Reference shared memories or experiences in your presentation")
        
        return suggestions[:4]  # Limit to top 4 suggestions

    def _generate_gift_reasoning(self, gift: GiftItem, recipient_profile: RecipientProfile,
                               context: GiftContext, score: float) -> str:
        """Generate explanation for why this gift was recommended"""
        reasons = []
        
        # Personality alignment
        matching_traits = set(recipient_profile.personality_traits) & set(gift.personality_match)
        if matching_traits:
            trait_names = [trait.value.replace('_', ' ') for trait in matching_traits]
            reasons.append(f"Matches their {', '.join(trait_names)} personality")
        
        # Interest alignment
        matching_interests = [interest for interest in recipient_profile.interests
                            if any(interest.lower() in tag.lower() for tag in gift.tags)]
        if matching_interests:
            reasons.append(f"Aligns with their interest in {', '.join(matching_interests[:2])}")
        
        # Occasion appropriateness
        reasons.append(f"Perfect for {context.occasion.value.replace('_', ' ')}")
        
        # Practical considerations
        if gift.practicality_score > 0.7:
            reasons.append("Highly practical and useful in daily life")
        
        # Uniqueness factor
        if gift.uniqueness_score > 0.7:
            reasons.append("Unique choice that shows thoughtful consideration")
        
        # Budget appropriateness
        if context.budget_min <= gift.price_min <= context.budget_max:
            reasons.append("Well-suited to your budget range")
        
        reasoning = "This gift was recommended because it " + ", and it ".join(reasons[:3]) + "."
        return reasoning

    async def _find_alternative_gifts(self, primary_gift: GiftItem, context: GiftContext,
                                    recipient_profile: RecipientProfile) -> List[str]:
        """Find alternative gift options"""
        alternatives = []
        
        # Find gifts in same category
        same_category_gifts = [gift for gift in self.gift_catalog.values()
                             if gift.category == primary_gift.category and gift.item_id != primary_gift.item_id]
        
        # Find gifts with similar price range
        similar_price_gifts = [gift for gift in self.gift_catalog.values()
                             if abs(gift.price_min - primary_gift.price_min) < 20 and gift.item_id != primary_gift.item_id]
        
        # Combine and score alternatives
        candidate_alternatives = list(set(same_category_gifts + similar_price_gifts))
        
        for gift in candidate_alternatives[:3]:  # Limit to 3 alternatives
            alternatives.append(gift.item_id)
        
        return alternatives

    def _generate_budget_justification(self, gift: GiftItem, context: GiftContext) -> str:
        """Generate budget justification"""
        avg_price = (gift.price_min + gift.price_max) / 2
        budget_midpoint = (context.budget_min + context.budget_max) / 2
        
        if avg_price <= budget_midpoint:
            return f"Excellent value at ${avg_price:.2f}, leaving room in your ${context.budget_max:.2f} budget for personalization or accessories."
        else:
            return f"Premium choice at ${avg_price:.2f}, representing quality investment within your ${context.budget_max:.2f} budget."

    def _generate_timing_recommendations(self, gift: GiftItem, context: GiftContext) -> str:
        """Generate timing recommendations"""
        if context.urgency > 7:
            return f"Order immediately - {gift.delivery_time} day delivery time needed for your urgent timeline."
        elif context.urgency > 5:
            return f"Order within 2-3 days to ensure {gift.delivery_time} day delivery arrives on time."
        else:
            return f"Plenty of time to order - {gift.delivery_time} day standard delivery works well."

    def _generate_presentation_tips(self, gift: GiftItem, context: GiftContext) -> List[str]:
        """Generate gift presentation tips"""
        tips = []
        
        # Relationship-specific tips
        relationship_rules = self.personalization_rules.get(context.relationship_level, {})
        
        if relationship_rules.get("emotional_weight", 0) > 0.6:
            tips.append("Present in person to see their reaction and share the moment")
        
        # Occasion-specific tips
        if context.occasion == OccasionType.BIRTHDAY:
            tips.append("Consider wrapping in their favorite colors")
        elif context.occasion == OccasionType.ANNIVERSARY:
            tips.append("Present in a meaningful location related to your relationship")
        
        # Gift-specific tips
        if gift.category == GiftCategory.EXPERIENCES:
            tips.append("Present with a creative invitation or announcement")
        elif gift.category == GiftCategory.TECHNOLOGY:
            tips.append("Include setup assistance if needed")
        elif gift.category == GiftCategory.BOOKS:
            tips.append("Include a bookmark with a personal note")
        
        # Surprise factor
        if context.surprise_factor:
            tips.append("Keep delivery timing flexible to maintain surprise")
        
        return tips[:3]  # Limit to top 3 tips

    async def record_gift_feedback(self, suggestion_id: str, success_rating: float,
                                 recipient_reaction: float, feedback_text: str = "") -> None:
        """Record feedback on gift suggestion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get suggestion details
        cursor.execute('SELECT recipient_id, giver_id FROM gift_suggestions WHERE suggestion_id = ?', (suggestion_id,))
        result = cursor.fetchone()
        
        if result:
            recipient_id, giver_id = result
            
            cursor.execute('''
                INSERT INTO gift_feedback
                (suggestion_id, recipient_id, giver_id, success_rating, recipient_reaction,
                 appropriateness_rating, value_perception, feedback_text, feedback_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (suggestion_id, recipient_id, giver_id, success_rating, recipient_reaction,
                  success_rating, recipient_reaction, feedback_text, datetime.now()))
            
            # Update suggestion feedback score
            cursor.execute('''
                UPDATE gift_suggestions SET feedback_score = ? WHERE suggestion_id = ?
            ''', (success_rating, suggestion_id))
            
            conn.commit()
            logger.info(f"Recorded feedback for suggestion {suggestion_id}: {success_rating:.1f}/5.0")
        
        conn.close()

    async def get_trending_gifts(self, category: Optional[GiftCategory] = None,
                               demographic: Optional[str] = None) -> List[GiftTrend]:
        """Get trending gift information"""
        # This would connect to external trend APIs in a real implementation
        sample_trends = [
            GiftTrend(
                trend_id="trend_001",
                trend_name="Sustainable Tech Accessories",
                category=GiftCategory.TECHNOLOGY,
                popularity_growth=0.23,
                target_demographics=["millennials", "gen_z"],
                seasonal_relevance={"spring": 0.8, "summer": 0.9},
                social_media_buzz=0.85,
                sustainability_rating=0.9
            ),
            GiftTrend(
                trend_id="trend_002", 
                trend_name="DIY Craft Kits",
                category=GiftCategory.HOBBY_CRAFTS,
                popularity_growth=0.31,
                target_demographics=["teens", "young_adults"],
                seasonal_relevance={"fall": 0.9, "winter": 0.8},
                social_media_buzz=0.75,
                sustainability_rating=0.7
            )
        ]
        
        filtered_trends = sample_trends
        if category:
            filtered_trends = [t for t in filtered_trends if t.category == category]
        
        return filtered_trends

    async def get_recipient_profile(self, user_id: str) -> Optional[RecipientProfile]:
        """Get recipient profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, age, gender, interests, hobbies, personality_traits,
                   preferred_categories, disliked_categories, lifestyle,
                   past_gifts_received, past_gifts_given, cultural_background,
                   living_situation, professional_context, social_media_activity,
                   recent_life_events, last_updated
            FROM recipient_profiles
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return RecipientProfile(
            user_id=row[0],
            age=row[1],
            gender=row[2],
            interests=json.loads(row[3]) if row[3] else [],
            hobbies=json.loads(row[4]) if row[4] else [],
            personality_traits=[PersonalityTrait(t) for t in json.loads(row[5])] if row[5] else [],
            preferred_categories=[GiftCategory(c) for c in json.loads(row[6])] if row[6] else [],
            disliked_categories=[GiftCategory(c) for c in json.loads(row[7])] if row[7] else [],
            lifestyle=json.loads(row[8]) if row[8] else {},
            past_gifts_received=json.loads(row[9]) if row[9] else [],
            past_gifts_given=json.loads(row[10]) if row[10] else [],
            cultural_background=row[11],
            living_situation=row[12],
            professional_context=row[13],
            social_media_activity=json.loads(row[14]) if row[14] else {},
            recent_life_events=json.loads(row[15]) if row[15] else [],
            last_updated=datetime.fromisoformat(row[16])
        )

    async def _save_recipient_profile(self, profile: RecipientProfile):
        """Save recipient profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO recipient_profiles
            (user_id, age, gender, interests, hobbies, personality_traits,
             preferred_categories, disliked_categories, lifestyle,
             past_gifts_received, past_gifts_given, cultural_background,
             living_situation, professional_context, social_media_activity,
             recent_life_events, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (profile.user_id, profile.age, profile.gender,
              json.dumps(profile.interests), json.dumps(profile.hobbies),
              json.dumps([t.value for t in profile.personality_traits]),
              json.dumps([c.value for c in profile.preferred_categories]),
              json.dumps([c.value for c in profile.disliked_categories]),
              json.dumps(profile.lifestyle), json.dumps(profile.past_gifts_received),
              json.dumps(profile.past_gifts_given), profile.cultural_background,
              profile.living_situation, profile.professional_context,
              json.dumps(profile.social_media_activity), json.dumps(profile.recent_life_events),
              profile.last_updated))
        
        conn.commit()
        conn.close()

    async def _save_gift_item(self, gift: GiftItem):
        """Save gift item to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO gift_catalog
            (item_id, name, description, category, price_min, price_max,
             occasion_suitability, personality_match, age_range, gender_preference,
             relationship_levels, tags, personalization_options, delivery_time,
             popularity_score, uniqueness_score, practicality_score,
             emotional_impact_score, vendor_info, added_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (gift.item_id, gift.name, gift.description, gift.category.value,
              gift.price_min, gift.price_max,
              json.dumps([o.value for o in gift.occasion_suitability]),
              json.dumps([p.value for p in gift.personality_match]),
              json.dumps(gift.age_range), gift.gender_preference,
              json.dumps([r.value for r in gift.relationship_levels]),
              json.dumps(gift.tags), json.dumps(gift.personalization_options),
              gift.delivery_time, gift.popularity_score, gift.uniqueness_score,
              gift.practicality_score, gift.emotional_impact_score,
              json.dumps(gift.vendor_info), datetime.now()))
        
        conn.commit()
        conn.close()

    async def _save_gift_suggestion(self, suggestion: GiftSuggestion):
        """Save gift suggestion to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO gift_suggestions
            (suggestion_id, recipient_id, giver_id, occasion, recommended_item_id,
             confidence_score, personalization_suggestions, reasoning,
             alternative_items, budget_justification, timing_recommendations,
             presentation_tips, generated_date, feedback_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (suggestion.suggestion_id, suggestion.recipient_id, suggestion.giver_id,
              suggestion.occasion.value, suggestion.recommended_item.item_id,
              suggestion.confidence_score, json.dumps(suggestion.personalization_suggestions),
              suggestion.reasoning, json.dumps(suggestion.alternative_items),
              suggestion.budget_justification, suggestion.timing_recommendations,
              json.dumps(suggestion.presentation_tips), suggestion.generated_date,
              suggestion.feedback_score))
        
        conn.commit()
        conn.close()

async def demo_gift_suggestion_engine():
    """Demonstrate gift suggestion engine"""
    engine = GiftSuggestionEngine()
    
    print("=== Gift Suggestion Engine Demo ===")
    
    # Create recipient profile
    recipient_profile = await engine.create_recipient_profile(
        user_id="user_sarah",
        age=28,
        gender="female",
        interests=["reading", "cooking", "yoga", "travel"],
        hobbies=["photography", "gardening", "painting"],
        personality_traits=["creative", "introverted", "eco_conscious"],
        preferred_categories=["books", "experiences", "art_culture"],
        lifestyle={"active": True, "environmentally_conscious": True},
        living_situation="apartment",
        professional_context="designer"
    )
    
    print(f"Created recipient profile for Sarah:")
    print(f"Age: {recipient_profile.age}")
    print(f"Interests: {', '.join(recipient_profile.interests)}")
    print(f"Personality: {', '.join(t.value for t in recipient_profile.personality_traits)}")
    
    # Create gift context
    context = GiftContext(
        occasion=OccasionType.BIRTHDAY,
        budget_min=50.0,
        budget_max=150.0,
        relationship_level=RelationshipLevel.CLOSE_FRIEND,
        urgency=6,
        surprise_factor=True
    )
    
    print(f"\nGift Context:")
    print(f"Occasion: {context.occasion.value}")
    print(f"Budget: ${context.budget_min:.2f} - ${context.budget_max:.2f}")
    print(f"Relationship: {context.relationship_level.value}")
    
    # Get gift suggestions
    suggestions = await engine.suggest_gifts(
        recipient_id="user_sarah",
        giver_id="user_mike",
        context=context,
        num_suggestions=3
    )
    
    print(f"\n=== Gift Suggestions ===")
    for i, suggestion in enumerate(suggestions, 1):
        gift = suggestion.recommended_item
        print(f"\n{i}. {gift.name}")
        print(f"   Category: {gift.category.value}")
        print(f"   Price Range: ${gift.price_min:.2f} - ${gift.price_max:.2f}")
        print(f"   Confidence: {suggestion.confidence_score:.1%}")
        print(f"   Reasoning: {suggestion.reasoning}")
        
        if suggestion.personalization_suggestions:
            print(f"   Personalization Ideas:")
            for idea in suggestion.personalization_suggestions:
                print(f"     • {idea}")
        
        if suggestion.presentation_tips:
            print(f"   Presentation Tips:")
            for tip in suggestion.presentation_tips:
                print(f"     • {tip}")
        
        print(f"   Budget Justification: {suggestion.budget_justification}")
        print(f"   Timing: {suggestion.timing_recommendations}")
    
    # Simulate feedback
    if suggestions:
        await engine.record_gift_feedback(
            suggestion_id=suggestions[0].suggestion_id,
            success_rating=4.5,
            recipient_reaction=4.8,
            feedback_text="Sarah loved the cooking class experience! Perfect match for her interests."
        )
        print(f"\n✓ Recorded positive feedback for top suggestion")
    
    # Show trending gifts
    trends = await engine.get_trending_gifts()
    print(f"\n=== Current Gift Trends ===")
    for trend in trends:
        print(f"• {trend.trend_name} ({trend.category.value})")
        print(f"  Growth: {trend.popularity_growth:.1%}, Buzz: {trend.social_media_buzz:.1%}")

if __name__ == "__main__":
    asyncio.run(demo_gift_suggestion_engine())