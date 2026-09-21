"""
Social Energy Tracker

AI-powered system for monitoring and optimizing social interaction patterns
to maintain healthy social energy levels and prevent burnout.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import json
import math

class InteractionType(Enum):
    IN_PERSON_MEETING = "in_person_meeting"
    VIDEO_CALL = "video_call"
    PHONE_CALL = "phone_call"
    TEXT_MESSAGE = "text_message"
    EMAIL = "email"
    SOCIAL_EVENT = "social_event"
    GROUP_MEETING = "group_meeting"
    PRESENTATION = "presentation"
    NETWORKING = "networking"
    CASUAL_CHAT = "casual_chat"

class EnergyImpact(Enum):
    HIGHLY_DRAINING = -2
    DRAINING = -1
    NEUTRAL = 0
    ENERGIZING = 1
    HIGHLY_ENERGIZING = 2

class SocialPersonaType(Enum):
    INTROVERT = "introvert"
    EXTROVERT = "extrovert"
    AMBIVERT = "ambivert"

class EnergyState(Enum):
    CRITICALLY_LOW = "critically_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    OPTIMAL = "optimal"

@dataclass
class SocialInteraction:
    id: Optional[int] = None
    user_id: str = ""
    interaction_type: InteractionType = InteractionType.CASUAL_CHAT
    participants: List[str] = None
    duration_minutes: int = 30
    energy_before: int = 5  # 1-10 scale
    energy_after: int = 5   # 1-10 scale
    context: str = ""
    location: str = ""
    is_planned: bool = True
    quality_rating: int = 5  # 1-10 scale
    notes: str = ""
    timestamp: datetime = datetime.now()
    tags: List[str] = None

    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.tags is None:
            self.tags = []

@dataclass
class EnergyProfile:
    user_id: str = ""
    persona_type: SocialPersonaType = SocialPersonaType.AMBIVERT
    baseline_energy: int = 6  # Natural energy level
    energy_capacity: int = 10  # Maximum sustainable energy
    recovery_rate: float = 1.0  # Energy recovery per hour
    optimal_interaction_frequency: int = 5  # Interactions per day
    preferred_interaction_types: List[InteractionType] = None
    energy_drains: List[InteractionType] = None
    recharge_activities: List[str] = None
    social_battery_size: int = 100  # Total social energy capacity
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.preferred_interaction_types is None:
            self.preferred_interaction_types = []
        if self.energy_drains is None:
            self.energy_drains = []
        if self.recharge_activities is None:
            self.recharge_activities = []

@dataclass
class EnergyRecommendation:
    id: Optional[int] = None
    user_id: str = ""
    recommendation_type: str = "balance"
    title: str = ""
    description: str = ""
    priority: int = 5  # 1-10 priority
    estimated_impact: int = 3  # 1-5 expected energy impact
    time_to_implement: str = "immediate"
    category: str = "interaction_management"
    action_items: List[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.action_items is None:
            self.action_items = []

class SocialEnergyTracker:
    """AI-powered social energy tracking and optimization system"""
    
    def __init__(self, db_path: str = "social_energy.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the social energy tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_interactions (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                participants TEXT,
                duration_minutes INTEGER,
                energy_before INTEGER,
                energy_after INTEGER,
                context TEXT,
                location TEXT,
                is_planned BOOLEAN,
                quality_rating INTEGER,
                notes TEXT,
                timestamp TEXT,
                tags TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS energy_profiles (
                user_id TEXT PRIMARY KEY,
                persona_type TEXT NOT NULL,
                baseline_energy INTEGER DEFAULT 6,
                energy_capacity INTEGER DEFAULT 10,
                recovery_rate REAL DEFAULT 1.0,
                optimal_interaction_frequency INTEGER DEFAULT 5,
                preferred_interaction_types TEXT,
                energy_drains TEXT,
                recharge_activities TEXT,
                social_battery_size INTEGER DEFAULT 100,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS energy_recommendations (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 5,
                estimated_impact INTEGER DEFAULT 3,
                time_to_implement TEXT DEFAULT 'immediate',
                category TEXT DEFAULT 'interaction_management',
                action_items TEXT,
                expires_at TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def create_energy_profile(self, profile: EnergyProfile) -> str:
        """Create or update a user's energy profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO energy_profiles 
            (user_id, persona_type, baseline_energy, energy_capacity, recovery_rate,
             optimal_interaction_frequency, preferred_interaction_types, energy_drains,
             recharge_activities, social_battery_size, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.user_id, profile.persona_type.value, profile.baseline_energy,
            profile.energy_capacity, profile.recovery_rate, profile.optimal_interaction_frequency,
            json.dumps([t.value for t in profile.preferred_interaction_types]),
            json.dumps([t.value for t in profile.energy_drains]),
            json.dumps(profile.recharge_activities), profile.social_battery_size,
            profile.created_at.isoformat(), profile.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return profile.user_id
    
    async def log_interaction(self, interaction: SocialInteraction) -> int:
        """Log a social interaction and its energy impact"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO social_interactions 
            (user_id, interaction_type, participants, duration_minutes, energy_before,
             energy_after, context, location, is_planned, quality_rating, notes, timestamp, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.user_id, interaction.interaction_type.value,
            json.dumps(interaction.participants), interaction.duration_minutes,
            interaction.energy_before, interaction.energy_after, interaction.context,
            interaction.location, interaction.is_planned, interaction.quality_rating,
            interaction.notes, interaction.timestamp.isoformat(), json.dumps(interaction.tags)
        ))
        
        interaction_id = cursor.lastrowid
        conn.commit()
        
        # Generate recommendations based on this interaction
        await self._generate_energy_recommendations(interaction.user_id)
        
        conn.close()
        return interaction_id
    
    async def calculate_current_energy_state(self, user_id: str) -> Dict[str, Any]:
        """Calculate current energy state and predictions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user profile
        cursor.execute("SELECT * FROM energy_profiles WHERE user_id = ?", (user_id,))
        profile_row = cursor.fetchone()
        
        if not profile_row:
            return {"error": "No energy profile found for user"}
        
        profile_cols = [description[0] for description in cursor.description]
        profile = dict(zip(profile_cols, profile_row))
        
        # Get recent interactions (last 24 hours)
        yesterday = datetime.now() - timedelta(hours=24)
        cursor.execute("""
            SELECT * FROM social_interactions 
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        """, (user_id, yesterday.isoformat()))
        
        recent_interactions = cursor.fetchall()
        interaction_cols = [description[0] for description in cursor.description]
        
        # Calculate energy metrics
        total_energy_change = 0
        total_interactions = len(recent_interactions)
        total_duration = 0
        interaction_types_count = {}
        
        for row in recent_interactions:
            interaction = dict(zip(interaction_cols, row))
            energy_delta = interaction['energy_after'] - interaction['energy_before']
            total_energy_change += energy_delta
            total_duration += interaction['duration_minutes']
            
            int_type = interaction['interaction_type']
            interaction_types_count[int_type] = interaction_types_count.get(int_type, 0) + 1
        
        # Estimate current energy level
        baseline = profile['baseline_energy']
        recovery_hours = 24
        natural_recovery = profile['recovery_rate'] * recovery_hours
        current_estimated_energy = min(
            profile['energy_capacity'],
            baseline + natural_recovery + total_energy_change
        )
        
        # Determine energy state
        energy_percentage = current_estimated_energy / profile['energy_capacity']
        if energy_percentage < 0.2:
            energy_state = EnergyState.CRITICALLY_LOW
        elif energy_percentage < 0.4:
            energy_state = EnergyState.LOW
        elif energy_percentage < 0.7:
            energy_state = EnergyState.MODERATE
        elif energy_percentage < 0.9:
            energy_state = EnergyState.HIGH
        else:
            energy_state = EnergyState.OPTIMAL
        
        # Social battery calculation
        battery_used = max(0, (total_duration / 60) * 10)  # 10% per hour of interaction
        battery_remaining = max(0, profile['social_battery_size'] - battery_used)
        
        conn.close()
        
        return {
            'user_id': user_id,
            'current_energy_level': round(current_estimated_energy, 1),
            'energy_capacity': profile['energy_capacity'],
            'energy_percentage': round(energy_percentage * 100, 1),
            'energy_state': energy_state.value,
            'social_battery_remaining': round(battery_remaining, 1),
            'total_interactions_today': total_interactions,
            'total_interaction_time_minutes': total_duration,
            'net_energy_change': total_energy_change,
            'interaction_type_breakdown': interaction_types_count,
            'recovery_needed_hours': max(0, (profile['baseline_energy'] - current_estimated_energy) / profile['recovery_rate']),
            'optimal_interactions_remaining': max(0, profile['optimal_interaction_frequency'] - total_interactions)
        }
    
    async def _generate_energy_recommendations(self, user_id: str):
        """Generate personalized energy management recommendations"""
        energy_state = await self.calculate_current_energy_state(user_id)
        
        if 'error' in energy_state:
            return
        
        recommendations = []
        
        # Critical energy recommendations
        if energy_state['energy_state'] == EnergyState.CRITICALLY_LOW.value:
            recommendations.extend([
                EnergyRecommendation(
                    user_id=user_id,
                    recommendation_type="urgent_recovery",
                    title="Immediate Energy Recovery Needed",
                    description="Your energy levels are critically low. Consider canceling non-essential meetings and prioritizing rest.",
                    priority=10,
                    estimated_impact=5,
                    category="energy_recovery",
                    action_items=[
                        "Cancel or postpone optional meetings",
                        "Take a 30-minute break from social interactions",
                        "Engage in solo recharge activities",
                        "Limit new commitments today"
                    ]
                )
            ])
        
        # Low energy recommendations
        elif energy_state['energy_state'] == EnergyState.LOW.value:
            recommendations.extend([
                EnergyRecommendation(
                    user_id=user_id,
                    recommendation_type="energy_conservation",
                    title="Energy Conservation Mode",
                    description="Your energy is low. Focus on high-value interactions and avoid energy drains.",
                    priority=8,
                    estimated_impact=4,
                    category="interaction_optimization",
                    action_items=[
                        "Prioritize one-on-one over group meetings",
                        "Choose shorter meeting durations",
                        "Schedule recovery time between interactions",
                        "Avoid challenging conversations today"
                    ]
                )
            ])
        
        # Optimal energy recommendations
        elif energy_state['energy_state'] == EnergyState.OPTIMAL.value:
            recommendations.extend([
                EnergyRecommendation(
                    user_id=user_id,
                    recommendation_type="energy_optimization",
                    title="Great Energy - Optimize Your Interactions",
                    description="Your energy levels are optimal. This is a great time for important conversations and networking.",
                    priority=6,
                    estimated_impact=3,
                    category="opportunity_maximization",
                    action_items=[
                        "Schedule important meetings or presentations",
                        "Engage in networking activities",
                        "Have those challenging conversations you've been postponing",
                        "Mentor or help others"
                    ]
                )
            ])
        
        # Over-interaction recommendations
        if energy_state['total_interactions_today'] > energy_state.get('optimal_interactions_remaining', 0) + 5:
            recommendations.append(
                EnergyRecommendation(
                    user_id=user_id,
                    recommendation_type="interaction_overload",
                    title="High Interaction Volume Detected",
                    description=f"You've had {energy_state['total_interactions_today']} interactions today, which may be above your optimal level.",
                    priority=7,
                    estimated_impact=3,
                    category="interaction_management",
                    action_items=[
                        "Consider shorter interactions for the rest of the day",
                        "Build in buffer time between meetings",
                        "Delegate some interactions if possible",
                        "Plan lighter schedule for tomorrow"
                    ]
                )
            )
        
        # Social battery recommendations
        if energy_state['social_battery_remaining'] < 20:
            recommendations.append(
                EnergyRecommendation(
                    user_id=user_id,
                    recommendation_type="social_battery_low",
                    title="Social Battery Running Low",
                    description="Your social battery is nearly depleted. Time for recharge activities.",
                    priority=8,
                    estimated_impact=4,
                    category="battery_management",
                    action_items=[
                        "Take breaks between social interactions",
                        "Engage in solo activities you enjoy",
                        "Spend time in nature or quiet spaces",
                        "Practice mindfulness or meditation"
                    ]
                )
            )
        
        # Store recommendations
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Deactivate old recommendations
        cursor.execute("""
            UPDATE energy_recommendations 
            SET is_active = FALSE 
            WHERE user_id = ? AND created_at < ?
        """, (user_id, (datetime.now() - timedelta(hours=6)).isoformat()))
        
        # Add new recommendations
        for rec in recommendations:
            cursor.execute("""
                INSERT INTO energy_recommendations 
                (user_id, recommendation_type, title, description, priority,
                 estimated_impact, time_to_implement, category, action_items,
                 expires_at, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.user_id, rec.recommendation_type, rec.title, rec.description,
                rec.priority, rec.estimated_impact, rec.time_to_implement,
                rec.category, json.dumps(rec.action_items),
                rec.expires_at.isoformat() if rec.expires_at else None,
                rec.is_active, rec.created_at.isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    async def get_active_recommendations(self, user_id: str) -> List[Dict]:
        """Get active energy recommendations for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM energy_recommendations 
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY priority DESC, created_at DESC
        """, (user_id,))
        
        recommendations = []
        for row in cursor.fetchall():
            rec_dict = dict(zip([col[0] for col in cursor.description], row))
            rec_dict['action_items'] = json.loads(rec_dict['action_items']) if rec_dict['action_items'] else []
            recommendations.append(rec_dict)
        
        conn.close()
        return recommendations
    
    async def analyze_energy_patterns(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Analyze energy patterns over time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        cursor.execute("""
            SELECT interaction_type, 
                   AVG(energy_after - energy_before) as avg_energy_delta,
                   AVG(quality_rating) as avg_quality,
                   COUNT(*) as frequency,
                   AVG(duration_minutes) as avg_duration
            FROM social_interactions 
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY interaction_type
            ORDER BY avg_energy_delta DESC
        """, (user_id, start_date.isoformat()))
        
        interaction_analysis = {}
        for row in cursor.fetchall():
            interaction_analysis[row[0]] = {
                'average_energy_impact': round(row[1], 2),
                'average_quality': round(row[2], 2),
                'frequency': row[3],
                'average_duration_minutes': round(row[4], 1)
            }
        
        # Daily energy patterns
        cursor.execute("""
            SELECT DATE(timestamp) as date,
                   AVG(energy_before) as avg_start_energy,
                   AVG(energy_after) as avg_end_energy,
                   COUNT(*) as interactions_count,
                   SUM(duration_minutes) as total_duration
            FROM social_interactions 
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (user_id, start_date.isoformat()))
        
        daily_patterns = {}
        total_days = 0
        total_energy_variance = 0
        
        for row in cursor.fetchall():
            daily_patterns[row[0]] = {
                'average_start_energy': round(row[1], 2),
                'average_end_energy': round(row[2], 2),
                'net_energy_change': round(row[2] - row[1], 2),
                'interactions_count': row[3],
                'total_duration_minutes': row[4]
            }
            total_days += 1
            total_energy_variance += abs(row[2] - row[1])
        
        energy_stability = 10 - min(10, (total_energy_variance / max(1, total_days)))
        
        # Find most energizing and draining activities
        energizing_activities = [(k, v) for k, v in interaction_analysis.items() 
                                if v['average_energy_impact'] > 0]
        energizing_activities.sort(key=lambda x: x[1]['average_energy_impact'], reverse=True)
        
        draining_activities = [(k, v) for k, v in interaction_analysis.items() 
                              if v['average_energy_impact'] < 0]
        draining_activities.sort(key=lambda x: x[1]['average_energy_impact'])
        
        conn.close()
        
        return {
            'user_id': user_id,
            'analysis_period_days': days_back,
            'total_days_with_data': total_days,
            'energy_stability_score': round(energy_stability, 2),
            'interaction_type_analysis': interaction_analysis,
            'most_energizing_activities': energizing_activities[:3],
            'most_draining_activities': draining_activities[:3],
            'daily_patterns': daily_patterns,
            'recommendations': {
                'focus_on': [act[0] for act in energizing_activities[:2]],
                'minimize': [act[0] for act in draining_activities[:2]],
                'energy_management_tip': "Schedule high-energy activities when you're most energized" if energy_stability > 7 else "Work on stabilizing your energy patterns"
            }
        }
    
    async def predict_optimal_schedule(self, user_id: str, date: datetime) -> Dict[str, Any]:
        """Predict optimal interaction schedule for a given day"""
        energy_state = await self.calculate_current_energy_state(user_id)
        patterns = await self.analyze_energy_patterns(user_id, 14)  # 2 weeks of data
        
        # Get user profile
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM energy_profiles WHERE user_id = ?", (user_id,))
        profile_row = cursor.fetchone()
        conn.close()
        
        if not profile_row:
            return {"error": "No energy profile found"}
        
        profile_cols = [description[0] for description in cursor.description]
        profile = dict(zip(profile_cols, profile_row))
        
        # Generate time-based recommendations
        schedule_recommendations = {
            'morning': {
                'recommended_activities': [],
                'energy_forecast': 'high',
                'max_interactions': 3,
                'interaction_types': ['in_person_meeting', 'presentation']
            },
            'afternoon': {
                'recommended_activities': [],
                'energy_forecast': 'moderate',
                'max_interactions': 2,
                'interaction_types': ['video_call', 'group_meeting']
            },
            'evening': {
                'recommended_activities': [],
                'energy_forecast': 'low',
                'max_interactions': 1,
                'interaction_types': ['casual_chat', 'text_message']
            }
        }
        
        # Customize based on persona type
        if profile['persona_type'] == SocialPersonaType.INTROVERT.value:
            schedule_recommendations['morning']['max_interactions'] = 2
            schedule_recommendations['afternoon']['max_interactions'] = 1
            schedule_recommendations['evening']['max_interactions'] = 0
        elif profile['persona_type'] == SocialPersonaType.EXTROVERT.value:
            schedule_recommendations['morning']['max_interactions'] = 4
            schedule_recommendations['afternoon']['max_interactions'] = 3
            schedule_recommendations['evening']['max_interactions'] = 2
        
        return {
            'date': date.strftime('%Y-%m-%d'),
            'current_energy_level': energy_state.get('current_energy_level', profile['baseline_energy']),
            'optimal_total_interactions': profile['optimal_interaction_frequency'],
            'schedule_recommendations': schedule_recommendations,
            'energy_tips': [
                "Schedule most important meetings when energy is highest",
                "Build in 15-minute buffers between interactions",
                "Plan recovery activities between draining interactions",
                "Keep challenging conversations for high-energy times"
            ]
        }

# Demo function
async def demo_social_energy_tracker():
    """Demonstrate the Social Energy Tracker functionality"""
    print("⚡ Social Energy Tracker Demo")
    print("=" * 50)
    
    tracker = SocialEnergyTracker()
    
    # Create energy profile
    print("\n1. Creating Energy Profile...")
    profile = EnergyProfile(
        user_id="alice_w",
        persona_type=SocialPersonaType.AMBIVERT,
        baseline_energy=7,
        energy_capacity=10,
        recovery_rate=1.2,
        optimal_interaction_frequency=6,
        preferred_interaction_types=[InteractionType.IN_PERSON_MEETING, InteractionType.CASUAL_CHAT],
        energy_drains=[InteractionType.GROUP_MEETING, InteractionType.PRESENTATION],
        recharge_activities=["reading", "walking", "meditation", "coffee break"],
        social_battery_size=120
    )
    
    await tracker.create_energy_profile(profile)
    print(f"✅ Created energy profile for {profile.user_id}")
    print(f"   Persona: {profile.persona_type.value}")
    print(f"   Baseline energy: {profile.baseline_energy}/10")
    print(f"   Social battery size: {profile.social_battery_size}")
    
    # Log interactions
    print("\n2. Logging Social Interactions...")
    interactions = [
        SocialInteraction(
            user_id="alice_w",
            interaction_type=InteractionType.IN_PERSON_MEETING,
            participants=["bob_k", "carol_m"],
            duration_minutes=45,
            energy_before=7,
            energy_after=8,
            context="Project planning meeting",
            quality_rating=8,
            is_planned=True,
            timestamp=datetime.now() - timedelta(hours=3)
        ),
        SocialInteraction(
            user_id="alice_w",
            interaction_type=InteractionType.GROUP_MEETING,
            participants=["team_alpha"],
            duration_minutes=90,
            energy_before=8,
            energy_after=5,
            context="All-hands meeting",
            quality_rating=6,
            is_planned=True,
            timestamp=datetime.now() - timedelta(hours=2)
        ),
        SocialInteraction(
            user_id="alice_w",
            interaction_type=InteractionType.CASUAL_CHAT,
            participants=["david_s"],
            duration_minutes=15,
            energy_before=5,
            energy_after=6,
            context="Coffee break conversation",
            quality_rating=8,
            is_planned=False,
            timestamp=datetime.now() - timedelta(hours=1)
        )
    ]
    
    for interaction in interactions:
        interaction_id = await tracker.log_interaction(interaction)
        energy_delta = interaction.energy_after - interaction.energy_before
        print(f"✅ Logged {interaction.interaction_type.value}: {energy_delta:+d} energy")
    
    # Calculate current energy state
    print("\n3. Current Energy Analysis...")
    energy_state = await tracker.calculate_current_energy_state("alice_w")
    
    print(f"📊 Current energy level: {energy_state['current_energy_level']}/10")
    print(f"📊 Energy state: {energy_state['energy_state']}")
    print(f"📊 Social battery remaining: {energy_state['social_battery_remaining']:.1f}%")
    print(f"📊 Total interactions today: {energy_state['total_interactions_today']}")
    print(f"📊 Net energy change: {energy_state['net_energy_change']:+d}")
    print(f"📊 Recovery needed: {energy_state['recovery_needed_hours']:.1f} hours")
    
    # Get recommendations
    print("\n4. Active Recommendations...")
    recommendations = await tracker.get_active_recommendations("alice_w")
    for i, rec in enumerate(recommendations[:2], 1):  # Show top 2
        print(f"💡 Recommendation {i}: {rec['title']}")
        print(f"   Priority: {rec['priority']}/10")
        print(f"   {rec['description']}")
        print(f"   Action items:")
        for item in rec['action_items'][:2]:  # Show first 2 items
            print(f"     • {item}")
    
    # Analyze patterns
    print("\n5. Energy Pattern Analysis (Last 30 days)...")
    patterns = await tracker.analyze_energy_patterns("alice_w", 30)
    
    print(f"📈 Energy stability score: {patterns['energy_stability_score']}/10")
    
    if patterns['most_energizing_activities']:
        print("📈 Most energizing activities:")
        for activity, stats in patterns['most_energizing_activities']:
            print(f"   • {activity}: +{stats['average_energy_impact']} energy")
    
    if patterns['most_draining_activities']:
        print("📉 Most draining activities:")
        for activity, stats in patterns['most_draining_activities']:
            print(f"   • {activity}: {stats['average_energy_impact']} energy")
    
    print(f"\n💡 Recommendations: Focus on {', '.join(patterns['recommendations']['focus_on'])}")
    print(f"💡 Minimize: {', '.join(patterns['recommendations']['minimize'])}")
    
    # Optimal schedule prediction
    print("\n6. Tomorrow's Optimal Schedule...")
    tomorrow = datetime.now() + timedelta(days=1)
    schedule = await tracker.predict_optimal_schedule("alice_w", tomorrow)
    
    print(f"📅 Schedule for {schedule['date']}:")
    print(f"   Current energy level: {schedule['current_energy_level']}/10")
    print(f"   Optimal total interactions: {schedule['optimal_total_interactions']}")
    
    for period, recs in schedule['schedule_recommendations'].items():
        print(f"\n   {period.title()}:")
        print(f"     Max interactions: {recs['max_interactions']}")
        print(f"     Energy forecast: {recs['energy_forecast']}")
        print(f"     Best interaction types: {', '.join(recs['interaction_types'][:2])}")
    
    print("\n   Energy Tips:")
    for tip in schedule['energy_tips'][:2]:
        print(f"     • {tip}")
    
    print("\n✅ Social Energy Tracker Demo Complete!")

if __name__ == "__main__":
    asyncio.run(demo_social_energy_tracker())