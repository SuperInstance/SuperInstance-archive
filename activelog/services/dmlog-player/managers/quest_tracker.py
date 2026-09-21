"""
Character goal and quest tracking system
"""

from datetime import datetime, date
from typing import Dict, List, Any, Optional
from ..models.base import Quest, QuestStatus, Priority, Character


class QuestTracker:
    """Manages character goals, quests, and objectives"""
    
    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self.character_quests: Dict[str, List[str]] = {}  # character_id -> quest_ids
        self.party_quests: Dict[str, List[str]] = {}  # party_id -> quest_ids
        self.quest_templates: Dict[str, Dict[str, Any]] = {}
        
        self._initialize_quest_templates()
    
    def create_quest(
        self, 
        character_id: str,
        title: str,
        description: str,
        category: str = "personal",
        priority: Priority = Priority.MEDIUM,
        deadline: Optional[date] = None,
        experience_reward: int = 0,
        gold_reward: int = 0,
        related_npcs: Optional[List[str]] = None,
        related_locations: Optional[List[str]] = None
    ) -> Quest:
        """Create a new quest or goal"""
        
        quest = Quest(
            character_id=character_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            deadline=deadline,
            experience_reward=experience_reward,
            gold_reward=gold_reward,
            related_npcs=related_npcs or [],
            related_locations=related_locations or []
        )
        
        # Store quest
        self.quests[quest.id] = quest
        
        # Index by character
        if character_id not in self.character_quests:
            self.character_quests[character_id] = []
        self.character_quests[character_id].append(quest.id)
        
        return quest
    
    def update_quest(
        self, 
        quest_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[QuestStatus] = None,
        priority: Optional[Priority] = None,
        progress: Optional[int] = None,
        deadline: Optional[date] = None,
        notes: Optional[str] = None
    ) -> Optional[Quest]:
        """Update an existing quest"""
        
        if quest_id not in self.quests:
            return None
        
        quest = self.quests[quest_id]
        
        if title is not None:
            quest.title = title
        if description is not None:
            quest.description = description
        if status is not None:
            quest.status = status
        if priority is not None:
            quest.priority = priority
        if progress is not None:
            quest.progress = max(0, min(100, progress))  # Clamp to 0-100
        if deadline is not None:
            quest.deadline = deadline
        
        quest.updated_at = datetime.utcnow()
        return quest
    
    def add_milestone(
        self, 
        quest_id: str,
        milestone_title: str,
        milestone_description: str,
        completed: bool = False,
        experience_reward: int = 0
    ) -> bool:
        """Add a milestone to a quest"""
        
        if quest_id not in self.quests:
            return False
        
        quest = self.quests[quest_id]
        
        milestone = {
            "title": milestone_title,
            "description": milestone_description,
            "completed": completed,
            "experience_reward": experience_reward,
            "completed_at": datetime.utcnow() if completed else None,
            "created_at": datetime.utcnow()
        }
        
        quest.milestones.append(milestone)
        quest.updated_at = datetime.utcnow()
        
        # Update progress based on completed milestones
        if quest.milestones:
            completed_milestones = sum(1 for m in quest.milestones if m["completed"])
            quest.progress = int((completed_milestones / len(quest.milestones)) * 100)
        
        return True
    
    def complete_milestone(self, quest_id: str, milestone_index: int) -> bool:
        """Mark a milestone as completed"""
        
        if quest_id not in self.quests:
            return False
        
        quest = self.quests[quest_id]
        
        if milestone_index < 0 or milestone_index >= len(quest.milestones):
            return False
        
        milestone = quest.milestones[milestone_index]
        if not milestone["completed"]:
            milestone["completed"] = True
            milestone["completed_at"] = datetime.utcnow()
            
            # Update quest progress
            completed_milestones = sum(1 for m in quest.milestones if m["completed"])
            quest.progress = int((completed_milestones / len(quest.milestones)) * 100)
            quest.updated_at = datetime.utcnow()
            
            # Check if quest should be completed
            if quest.progress >= 100 and quest.status != QuestStatus.COMPLETED:
                quest.status = QuestStatus.COMPLETED
        
        return True
    
    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get a quest by ID"""
        return self.quests.get(quest_id)
    
    def get_character_quests(
        self, 
        character_id: str,
        status: Optional[QuestStatus] = None,
        category: Optional[str] = None,
        priority: Optional[Priority] = None
    ) -> List[Quest]:
        """Get all quests for a character with optional filters"""
        
        if character_id not in self.character_quests:
            return []
        
        quest_ids = self.character_quests[character_id]
        quests = [self.quests[qid] for qid in quest_ids if qid in self.quests]
        
        # Apply filters
        if status is not None:
            quests = [q for q in quests if q.status == status]
        
        if category is not None:
            quests = [q for q in quests if q.category == category]
        
        if priority is not None:
            quests = [q for q in quests if q.priority == priority]
        
        # Sort by priority (high first), then by deadline
        def sort_key(quest):
            priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
            return (
                priority_order.get(quest.priority, 4),
                quest.deadline or date.max,
                quest.created_at
            )
        
        return sorted(quests, key=sort_key)
    
    def get_active_quests(self, character_id: str) -> List[Quest]:
        """Get active (in-progress) quests"""
        return self.get_character_quests(character_id, status=QuestStatus.IN_PROGRESS)
    
    def get_completed_quests(self, character_id: str) -> List[Quest]:
        """Get completed quests"""
        return self.get_character_quests(character_id, status=QuestStatus.COMPLETED)
    
    def get_overdue_quests(self, character_id: str) -> List[Quest]:
        """Get quests that are past their deadline"""
        
        active_quests = self.get_character_quests(character_id, status=QuestStatus.IN_PROGRESS)
        today = date.today()
        
        return [q for q in active_quests if q.deadline and q.deadline < today]
    
    def get_upcoming_deadlines(self, character_id: str, days: int = 7) -> List[Quest]:
        """Get quests with deadlines in the next N days"""
        
        active_quests = self.get_character_quests(character_id, status=QuestStatus.IN_PROGRESS)
        today = date.today()
        cutoff_date = date.fromordinal(today.toordinal() + days)
        
        upcoming = [
            q for q in active_quests 
            if q.deadline and today <= q.deadline <= cutoff_date
        ]
        
        return sorted(upcoming, key=lambda q: q.deadline)
    
    def search_quests(
        self, 
        character_id: str,
        query: str,
        include_completed: bool = False
    ) -> List[Quest]:
        """Search quests by title, description, or related NPCs/locations"""
        
        quests = self.get_character_quests(character_id)
        
        if not include_completed:
            quests = [q for q in quests if q.status != QuestStatus.COMPLETED]
        
        query_lower = query.lower()
        results = []
        
        for quest in quests:
            # Search in title and description
            if (query_lower in quest.title.lower() or 
                query_lower in quest.description.lower()):
                results.append(quest)
                continue
            
            # Search in related NPCs and locations
            related_text = " ".join(quest.related_npcs + quest.related_locations).lower()
            if query_lower in related_text:
                results.append(quest)
                continue
            
            # Search in milestones
            milestone_text = " ".join(
                m["title"] + " " + m["description"] for m in quest.milestones
            ).lower()
            if query_lower in milestone_text:
                results.append(quest)
        
        return results
    
    def get_quest_statistics(self, character_id: str) -> Dict[str, Any]:
        """Get quest statistics for a character"""
        
        all_quests = self.get_character_quests(character_id)
        
        if not all_quests:
            return {
                "total_quests": 0,
                "active_quests": 0,
                "completed_quests": 0,
                "failed_quests": 0,
                "completion_rate": 0.0,
                "total_experience_earned": 0,
                "total_gold_earned": 0,
                "average_progress": 0.0,
                "quests_by_category": {},
                "quests_by_priority": {},
                "overdue_quests": 0
            }
        
        # Count by status
        status_counts = {}
        for quest in all_quests:
            status = quest.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        completed_quests = [q for q in all_quests if q.status == QuestStatus.COMPLETED]
        active_quests = [q for q in all_quests if q.status == QuestStatus.IN_PROGRESS]
        
        # Calculate completion rate
        completion_rate = len(completed_quests) / len(all_quests) * 100 if all_quests else 0.0
        
        # Calculate rewards earned
        total_experience = sum(q.experience_reward for q in completed_quests)
        total_gold = sum(q.gold_reward for q in completed_quests)
        
        # Average progress of active quests
        average_progress = sum(q.progress for q in active_quests) / len(active_quests) if active_quests else 0.0
        
        # Count by category
        category_counts = {}
        for quest in all_quests:
            cat = quest.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Count by priority
        priority_counts = {}
        for quest in all_quests:
            pri = quest.priority.value
            priority_counts[pri] = priority_counts.get(pri, 0) + 1
        
        # Count overdue
        overdue_count = len(self.get_overdue_quests(character_id))
        
        return {
            "total_quests": len(all_quests),
            "active_quests": len(active_quests),
            "completed_quests": len(completed_quests),
            "failed_quests": status_counts.get("failed", 0),
            "completion_rate": completion_rate,
            "total_experience_earned": total_experience,
            "total_gold_earned": total_gold,
            "average_progress": average_progress,
            "quests_by_category": category_counts,
            "quests_by_priority": priority_counts,
            "overdue_quests": overdue_count
        }
    
    def create_quest_from_template(
        self, 
        character_id: str,
        template_name: str,
        customizations: Optional[Dict[str, Any]] = None
    ) -> Optional[Quest]:
        """Create a quest from a predefined template"""
        
        if template_name not in self.quest_templates:
            return None
        
        template = self.quest_templates[template_name].copy()
        
        # Apply customizations
        if customizations:
            template.update(customizations)
        
        return self.create_quest(
            character_id=character_id,
            title=template.get("title", "Untitled Quest"),
            description=template.get("description", ""),
            category=template.get("category", "personal"),
            priority=Priority(template.get("priority", "medium")),
            experience_reward=template.get("experience_reward", 0),
            gold_reward=template.get("gold_reward", 0),
            related_npcs=template.get("related_npcs", []),
            related_locations=template.get("related_locations", [])
        )
    
    def generate_quest_summary(self, quest_id: str) -> Dict[str, Any]:
        """Generate a comprehensive quest summary"""
        
        quest = self.get_quest(quest_id)
        if not quest:
            return {}
        
        # Calculate time statistics
        days_active = (datetime.utcnow() - quest.created_at).days
        days_until_deadline = None
        if quest.deadline:
            days_until_deadline = (quest.deadline - date.today()).days
        
        # Milestone statistics
        total_milestones = len(quest.milestones)
        completed_milestones = sum(1 for m in quest.milestones if m["completed"])
        
        return {
            "quest_id": quest.id,
            "title": quest.title,
            "status": quest.status.value,
            "priority": quest.priority.value,
            "category": quest.category,
            "progress": quest.progress,
            "days_active": days_active,
            "days_until_deadline": days_until_deadline,
            "overdue": days_until_deadline is not None and days_until_deadline < 0,
            "milestones": {
                "total": total_milestones,
                "completed": completed_milestones,
                "remaining": total_milestones - completed_milestones
            },
            "rewards": {
                "experience": quest.experience_reward,
                "gold": quest.gold_reward,
                "items": quest.item_rewards
            },
            "related_content": {
                "npcs": quest.related_npcs,
                "locations": quest.related_locations
            }
        }
    
    def create_quest_dependencies(
        self, 
        prerequisite_quest_id: str, 
        dependent_quest_id: str
    ) -> bool:
        """Create a dependency relationship between quests"""
        
        # This would be expanded to handle complex quest dependencies
        # For now, just store in quest data
        
        dependent_quest = self.get_quest(dependent_quest_id)
        if not dependent_quest:
            return False
        
        if "dependencies" not in dependent_quest.system_specific:
            dependent_quest.system_specific["dependencies"] = []
        
        if prerequisite_quest_id not in dependent_quest.system_specific["dependencies"]:
            dependent_quest.system_specific["dependencies"].append(prerequisite_quest_id)
        
        return True
    
    def get_available_quests(self, character_id: str) -> List[Quest]:
        """Get quests that are available to start (dependencies met)"""
        
        not_started_quests = self.get_character_quests(character_id, status=QuestStatus.NOT_STARTED)
        available_quests = []
        
        for quest in not_started_quests:
            dependencies = quest.system_specific.get("dependencies", [])
            
            if not dependencies:
                # No dependencies, always available
                available_quests.append(quest)
                continue
            
            # Check if all dependencies are completed
            all_completed = True
            for dep_id in dependencies:
                dep_quest = self.get_quest(dep_id)
                if not dep_quest or dep_quest.status != QuestStatus.COMPLETED:
                    all_completed = False
                    break
            
            if all_completed:
                available_quests.append(quest)
        
        return available_quests
    
    def delete_quest(self, quest_id: str) -> bool:
        """Delete a quest"""
        
        if quest_id not in self.quests:
            return False
        
        quest = self.quests[quest_id]
        
        # Remove from character index
        character_id = quest.character_id
        if character_id in self.character_quests:
            self.character_quests[character_id].remove(quest_id)
        
        # Delete quest
        del self.quests[quest_id]
        return True
    
    def _initialize_quest_templates(self):
        """Initialize common quest templates"""
        
        self.quest_templates = {
            "character_development": {
                "title": "Character Development Goal",
                "description": "Work on developing a specific aspect of your character",
                "category": "personal",
                "priority": "medium",
                "experience_reward": 0,
                "gold_reward": 0
            },
            "backstory_resolution": {
                "title": "Resolve Backstory Element",
                "description": "Address an unresolved element from your character's backstory",
                "category": "personal",
                "priority": "high",
                "experience_reward": 100,
                "gold_reward": 0
            },
            "skill_mastery": {
                "title": "Master a Skill",
                "description": "Become proficient or gain expertise in a specific skill",
                "category": "advancement",
                "priority": "medium",
                "experience_reward": 50,
                "gold_reward": 0
            },
            "acquire_item": {
                "title": "Acquire Specific Item",
                "description": "Obtain a particular item or piece of equipment",
                "category": "equipment",
                "priority": "medium",
                "experience_reward": 25,
                "gold_reward": 0
            },
            "defeat_nemesis": {
                "title": "Defeat Personal Nemesis",
                "description": "Confront and defeat a recurring enemy or rival",
                "category": "combat",
                "priority": "high",
                "experience_reward": 200,
                "gold_reward": 100
            }
        }