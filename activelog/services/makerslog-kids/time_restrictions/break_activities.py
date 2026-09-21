import random
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum


class ActivityCategory(Enum):
    PHYSICAL = "physical"
    CREATIVE = "creative"
    MINDFULNESS = "mindfulness"
    EDUCATIONAL = "educational"
    SOCIAL = "social"


@dataclass
class BreakActivity:
    name: str
    description: str
    duration_minutes: int
    category: ActivityCategory
    age_min: int
    age_max: int
    instructions: List[str]
    benefits: List[str]


class BreakActivityManager:
    def __init__(self):
        self.activities = self._initialize_activities()
    
    def _initialize_activities(self) -> List[BreakActivity]:
        return [
            # Physical Activities
            BreakActivity(
                name="Stretch Break",
                description="Simple stretching exercises to relax your body",
                duration_minutes=5,
                category=ActivityCategory.PHYSICAL,
                age_min=6,
                age_max=18,
                instructions=[
                    "Stand up and reach your arms high above your head",
                    "Touch your toes gently (don't force it!)",
                    "Roll your shoulders backwards 5 times",
                    "Turn your head left and right slowly",
                    "Take 5 deep breaths"
                ],
                benefits=["Improves posture", "Reduces eye strain", "Increases blood flow"]
            ),
            
            BreakActivity(
                name="Dance Party",
                description="Put on your favorite song and dance!",
                duration_minutes=10,
                category=ActivityCategory.PHYSICAL,
                age_min=5,
                age_max=16,
                instructions=[
                    "Put on a fun, energetic song",
                    "Dance however feels good to you",
                    "Try different moves like jumping, spinning, or marching",
                    "Invite family members to join if they want"
                ],
                benefits=["Boosts mood", "Gets heart pumping", "Burns energy"]
            ),
            
            BreakActivity(
                name="Walk Around",
                description="Take a short walk indoors or outdoors",
                duration_minutes=10,
                category=ActivityCategory.PHYSICAL,
                age_min=5,
                age_max=18,
                instructions=[
                    "Walk around your house or outside if safe",
                    "Look for interesting things you hadn't noticed before",
                    "Count your steps if you want",
                    "Take deep breaths of fresh air"
                ],
                benefits=["Gets you moving", "Fresh perspective", "Clears your mind"]
            ),
            
            # Creative Activities
            BreakActivity(
                name="Quick Sketch",
                description="Draw whatever comes to mind",
                duration_minutes=10,
                category=ActivityCategory.CREATIVE,
                age_min=5,
                age_max=18,
                instructions=[
                    "Get paper and any drawing tool (pencil, crayon, marker)",
                    "Draw the first thing that comes to mind",
                    "Don't worry about making it perfect",
                    "Add colors if you want"
                ],
                benefits=["Exercises creativity", "Relaxes the mind", "Improves focus"]
            ),
            
            BreakActivity(
                name="Story Creation",
                description="Make up a short story about anything",
                duration_minutes=15,
                category=ActivityCategory.CREATIVE,
                age_min=7,
                age_max=18,
                instructions=[
                    "Think of a character (person, animal, or made-up creature)",
                    "Give them a problem to solve",
                    "Write or tell how they solve it",
                    "Add funny or exciting details"
                ],
                benefits=["Develops imagination", "Improves writing", "Exercises storytelling"]
            ),
            
            BreakActivity(
                name="Origami Fun",
                description="Fold paper into simple shapes",
                duration_minutes=15,
                category=ActivityCategory.CREATIVE,
                age_min=8,
                age_max=18,
                instructions=[
                    "Get a square piece of paper",
                    "Try making a simple crane, frog, or flower",
                    "Look up easy origami instructions if needed",
                    "Decorate your creation if you want"
                ],
                benefits=["Improves fine motor skills", "Develops patience", "Satisfying accomplishment"]
            ),
            
            # Mindfulness Activities  
            BreakActivity(
                name="Deep Breathing",
                description="Practice calm, focused breathing",
                duration_minutes=5,
                category=ActivityCategory.MINDFULNESS,
                age_min=6,
                age_max=18,
                instructions=[
                    "Sit or lie down comfortably",
                    "Close your eyes or look at one spot",
                    "Breathe in slowly for 4 counts",
                    "Hold for 4 counts",
                    "Breathe out slowly for 6 counts",
                    "Repeat 5-10 times"
                ],
                benefits=["Reduces stress", "Improves focus", "Calms the mind"]
            ),
            
            BreakActivity(
                name="Gratitude Moment",
                description="Think about things you're thankful for",
                duration_minutes=5,
                category=ActivityCategory.MINDFULNESS,
                age_min=7,
                age_max=18,
                instructions=[
                    "Think of 3 things that made you happy today",
                    "Think of 1 person you're grateful for",
                    "Think of 1 place that makes you feel good",
                    "Say 'thank you' for each one, either out loud or in your head"
                ],
                benefits=["Improves mood", "Develops positive thinking", "Reduces anxiety"]
            ),
            
            BreakActivity(
                name="Body Scan",
                description="Notice how different parts of your body feel",
                duration_minutes=10,
                category=ActivityCategory.MINDFULNESS,
                age_min=8,
                age_max=18,
                instructions=[
                    "Lie down or sit comfortably",
                    "Start at your toes - notice how they feel",
                    "Slowly move attention up your body",
                    "Notice each part without trying to change anything",
                    "End at the top of your head"
                ],
                benefits=["Develops body awareness", "Promotes relaxation", "Reduces tension"]
            ),
            
            # Educational Activities
            BreakActivity(
                name="Word Game",
                description="Play with words and language",
                duration_minutes=10,
                category=ActivityCategory.EDUCATIONAL,
                age_min=7,
                age_max=18,
                instructions=[
                    "Pick a topic (animals, food, places, etc.)",
                    "Try to name as many things in that category as you can",
                    "Or make up rhymes with your name",
                    "Or find words that start with each letter of your name"
                ],
                benefits=["Builds vocabulary", "Exercises memory", "Improves language skills"]
            ),
            
            BreakActivity(
                name="Nature Observation",
                description="Look closely at plants, animals, or weather",
                duration_minutes=15,
                category=ActivityCategory.EDUCATIONAL,
                age_min=6,
                age_max=18,
                instructions=[
                    "Go outside or look out a window",
                    "Pick one thing in nature to observe closely",
                    "Notice details like colors, shapes, movements",
                    "Write down or remember what you noticed"
                ],
                benefits=["Develops observation skills", "Connects with nature", "Encourages curiosity"]
            ),
            
            # Social Activities
            BreakActivity(
                name="Family Check-in",
                description="Have a quick conversation with a family member",
                duration_minutes=10,
                category=ActivityCategory.SOCIAL,
                age_min=5,
                age_max=18,
                instructions=[
                    "Find a family member who's available",
                    "Ask them about their day",
                    "Share something interesting about yours",
                    "Give them a hug if they want one"
                ],
                benefits=["Strengthens relationships", "Practices communication", "Provides emotional support"]
            ),
            
            BreakActivity(
                name="Help Someone",
                description="Do a small helpful task for someone else",
                duration_minutes=10,
                category=ActivityCategory.SOCIAL,
                age_min=6,
                age_max=18,
                instructions=[
                    "Think of someone who might need help",
                    "Offer to do a small task (tidy up, get water, etc.)",
                    "Do it cheerfully without expecting anything back",
                    "Notice how helping others makes you feel"
                ],
                benefits=["Develops empathy", "Builds confidence", "Creates positive connections"]
            ),
            
            BreakActivity(
                name="Pet Time",
                description="Spend quality time with a pet",
                duration_minutes=10,
                category=ActivityCategory.SOCIAL,
                age_min=5,
                age_max=18,
                instructions=[
                    "Find your pet (or visit a neighbor's pet if allowed)",
                    "Pet them gently and talk to them",
                    "Play a simple game they enjoy",
                    "Notice how they respond to your attention"
                ],
                benefits=["Reduces stress", "Provides companionship", "Teaches responsibility"]
            )
        ]
    
    def get_activities_for_age(self, age: int, duration_limit: int = None) -> List[BreakActivity]:
        """Get activities appropriate for a specific age"""
        suitable_activities = [
            activity for activity in self.activities
            if activity.age_min <= age <= activity.age_max
        ]
        
        if duration_limit:
            suitable_activities = [
                activity for activity in suitable_activities
                if activity.duration_minutes <= duration_limit
            ]
        
        return suitable_activities
    
    def get_random_activity(self, age: int, duration_limit: int = None, category: ActivityCategory = None) -> BreakActivity:
        """Get a random activity based on criteria"""
        suitable_activities = self.get_activities_for_age(age, duration_limit)
        
        if category:
            suitable_activities = [
                activity for activity in suitable_activities
                if activity.category == category
            ]
        
        if not suitable_activities:
            # Fallback to basic stretch activity
            return self.activities[0]  # Stretch Break
        
        return random.choice(suitable_activities)
    
    def get_activity_by_category(self, category: ActivityCategory, age: int) -> List[BreakActivity]:
        """Get all activities in a specific category for an age"""
        return [
            activity for activity in self.activities
            if activity.category == category and activity.age_min <= age <= activity.age_max
        ]
    
    def get_varied_break_sequence(self, age: int, total_duration: int) -> List[BreakActivity]:
        """Get a sequence of varied activities for a longer break"""
        activities = []
        remaining_time = total_duration
        used_categories = set()
        
        while remaining_time > 5:
            # Try to get activity from unused category
            available_categories = [cat for cat in ActivityCategory if cat not in used_categories]
            if not available_categories:
                used_categories = set()  # Reset if all categories used
                available_categories = list(ActivityCategory)
            
            category = random.choice(available_categories)
            suitable_activities = self.get_activity_by_category(category, age)
            suitable_activities = [a for a in suitable_activities if a.duration_minutes <= remaining_time]
            
            if suitable_activities:
                activity = random.choice(suitable_activities)
                activities.append(activity)
                remaining_time -= activity.duration_minutes
                used_categories.add(category)
            else:
                break
        
        return activities
    
    def format_activity_for_display(self, activity: BreakActivity) -> Dict:
        """Format activity data for UI display"""
        return {
            "name": activity.name,
            "description": activity.description,
            "duration_minutes": activity.duration_minutes,
            "category": activity.category.value,
            "instructions": activity.instructions,
            "benefits": activity.benefits,
            "estimated_time": f"{activity.duration_minutes} minutes"
        }
    
    def get_break_recommendations(self, age: int, session_duration: int, break_duration: int) -> Dict:
        """Get personalized break recommendations based on usage patterns"""
        recommendations = {
            "primary_activity": None,
            "alternative_activities": [],
            "tips": []
        }
        
        # Determine primary activity based on session length
        if session_duration >= 60:  # Long session
            recommendations["primary_activity"] = self.get_random_activity(age, break_duration, ActivityCategory.PHYSICAL)
            recommendations["tips"].append("After a long session, physical activity helps reset your energy!")
        elif session_duration >= 30:  # Medium session
            recommendations["primary_activity"] = self.get_random_activity(age, break_duration, ActivityCategory.MINDFULNESS)
            recommendations["tips"].append("A mindfulness break helps you refocus and reduce eye strain.")
        else:  # Short session
            recommendations["primary_activity"] = self.get_random_activity(age, break_duration, ActivityCategory.CREATIVE)
            recommendations["tips"].append("A creative break exercises different parts of your brain!")
        
        # Add alternatives from different categories
        all_suitable = self.get_activities_for_age(age, break_duration)
        primary_category = recommendations["primary_activity"].category if recommendations["primary_activity"] else None
        
        alternatives = [
            activity for activity in all_suitable
            if activity.category != primary_category
        ][:3]  # Limit to 3 alternatives
        
        recommendations["alternative_activities"] = [
            self.format_activity_for_display(activity) for activity in alternatives
        ]
        
        # Add general tips
        if break_duration >= 15:
            recommendations["tips"].append("For longer breaks, try combining different activities!")
        
        recommendations["tips"].append("Remember to stay hydrated during your break!")
        
        return {
            "primary": self.format_activity_for_display(recommendations["primary_activity"]) if recommendations["primary_activity"] else None,
            "alternatives": recommendations["alternative_activities"],
            "tips": recommendations["tips"],
            "break_duration": break_duration
        }