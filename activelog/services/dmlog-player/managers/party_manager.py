"""
Party formation and management tools
"""

from datetime import datetime, date
from typing import Dict, List, Any, Optional, Set
from ..models.base import Party, Character, PartyFund


class PartyManager:
    """Manages party formation, coordination, and shared resources"""
    
    def __init__(self):
        self.parties: Dict[str, Party] = {}
        self.party_funds: Dict[str, PartyFund] = {}  # party_id -> fund
        self.character_parties: Dict[str, str] = {}  # character_id -> party_id
        self.party_invitations: Dict[str, List[Dict[str, Any]]] = {}  # character_id -> invitations
        
    def create_party(
        self, 
        name: str,
        campaign_id: str,
        leader_id: str,
        description: str = ""
    ) -> Party:
        """Create a new party"""
        
        party = Party(
            name=name,
            description=description,
            campaign_id=campaign_id,
            leader_id=leader_id,
            member_ids=[leader_id]
        )
        
        self.parties[party.id] = party
        self.character_parties[leader_id] = party.id
        
        # Create party fund
        fund = PartyFund(
            party_id=party.id,
            name=f"{name} Treasury",
            managers=[leader_id]
        )
        self.party_funds[party.id] = fund
        
        return party
    
    def invite_character(
        self, 
        party_id: str,
        character_id: str,
        inviter_id: str,
        message: str = ""
    ) -> bool:
        """Send party invitation to a character"""
        
        party = self.get_party(party_id)
        if not party:
            return False
        
        # Check if inviter has permission
        if inviter_id != party.leader_id and inviter_id not in party.member_ids:
            return False
        
        # Check if character is already in a party
        if character_id in self.character_parties:
            return False
        
        # Check if already invited
        existing_invites = self.party_invitations.get(character_id, [])
        if any(inv["party_id"] == party_id for inv in existing_invites):
            return False
        
        # Create invitation
        invitation = {
            "party_id": party_id,
            "party_name": party.name,
            "inviter_id": inviter_id,
            "message": message,
            "invited_at": datetime.utcnow(),
            "expires_at": datetime.utcnow().replace(hour=23, minute=59, second=59) + \
                         datetime.timedelta(days=7)  # Expires in 7 days
        }
        
        if character_id not in self.party_invitations:
            self.party_invitations[character_id] = []
        
        self.party_invitations[character_id].append(invitation)
        return True
    
    def respond_to_invitation(
        self, 
        character_id: str,
        party_id: str,
        accept: bool
    ) -> bool:
        """Respond to a party invitation"""
        
        if character_id not in self.party_invitations:
            return False
        
        # Find the invitation
        invitations = self.party_invitations[character_id]
        invitation = None
        
        for inv in invitations:
            if inv["party_id"] == party_id:
                invitation = inv
                break
        
        if not invitation:
            return False
        
        # Remove invitation
        invitations.remove(invitation)
        
        if accept:
            return self.add_character_to_party(party_id, character_id)
        
        return True
    
    def add_character_to_party(self, party_id: str, character_id: str) -> bool:
        """Add a character to a party"""
        
        party = self.get_party(party_id)
        if not party:
            return False
        
        # Check if character is already in a party
        if character_id in self.character_parties:
            return False
        
        # Add to party
        party.member_ids.append(character_id)
        self.character_parties[character_id] = party_id
        
        return True
    
    def remove_character_from_party(
        self, 
        party_id: str, 
        character_id: str,
        remover_id: Optional[str] = None
    ) -> bool:
        """Remove a character from a party"""
        
        party = self.get_party(party_id)
        if not party or character_id not in party.member_ids:
            return False
        
        # Check permissions (self-removal or leader action)
        if remover_id and remover_id != character_id and remover_id != party.leader_id:
            return False
        
        # Remove from party
        party.member_ids.remove(character_id)
        del self.character_parties[character_id]
        
        # Handle leadership transfer if leader left
        if character_id == party.leader_id:
            if party.member_ids:
                party.leader_id = party.member_ids[0]  # First remaining member becomes leader
            else:
                # Party is empty, could be disbanded
                party.leader_id = None
        
        return True
    
    def transfer_leadership(
        self, 
        party_id: str, 
        new_leader_id: str,
        current_leader_id: str
    ) -> bool:
        """Transfer party leadership"""
        
        party = self.get_party(party_id)
        if not party:
            return False
        
        # Check if current user is the leader
        if party.leader_id != current_leader_id:
            return False
        
        # Check if new leader is in the party
        if new_leader_id not in party.member_ids:
            return False
        
        party.leader_id = new_leader_id
        return True
    
    def get_party(self, party_id: str) -> Optional[Party]:
        """Get party by ID"""
        return self.parties.get(party_id)
    
    def get_character_party(self, character_id: str) -> Optional[Party]:
        """Get the party a character belongs to"""
        
        party_id = self.character_parties.get(character_id)
        if party_id:
            return self.get_party(party_id)
        return None
    
    def get_party_members(self, party_id: str) -> List[str]:
        """Get list of party member IDs"""
        
        party = self.get_party(party_id)
        if party:
            return party.member_ids.copy()
        return []
    
    def get_character_invitations(self, character_id: str) -> List[Dict[str, Any]]:
        """Get pending invitations for a character"""
        
        invitations = self.party_invitations.get(character_id, [])
        
        # Filter out expired invitations
        now = datetime.utcnow()
        valid_invitations = []
        
        for inv in invitations:
            if inv["expires_at"] > now:
                valid_invitations.append(inv)
        
        # Update stored invitations
        if character_id in self.party_invitations:
            self.party_invitations[character_id] = valid_invitations
        
        return valid_invitations
    
    def set_party_objective(
        self, 
        party_id: str, 
        objective: str,
        setter_id: str
    ) -> bool:
        """Set a party objective"""
        
        party = self.get_party(party_id)
        if not party:
            return False
        
        # Check if setter is a member
        if setter_id not in party.member_ids:
            return False
        
        if objective not in party.objectives:
            party.objectives.append(objective)
        
        return True
    
    def remove_party_objective(
        self, 
        party_id: str, 
        objective: str,
        remover_id: str
    ) -> bool:
        """Remove a party objective"""
        
        party = self.get_party(party_id)
        if not party:
            return False
        
        # Check if remover is leader or member who set it
        if remover_id != party.leader_id and remover_id not in party.member_ids:
            return False
        
        if objective in party.objectives:
            party.objectives.remove(objective)
        
        return True
    
    def update_party_reputation(
        self, 
        party_id: str,
        faction: str,
        reputation_change: int,
        reason: str = ""
    ) -> bool:
        """Update party reputation with a faction"""
        
        party = self.get_party(party_id)
        if not party:
            return False
        
        current_rep = party.reputation.get(faction, 0)
        new_rep = max(-100, min(100, current_rep + reputation_change))  # Clamp to -100 to 100
        
        party.reputation[faction] = new_rep
        
        # Could log reputation changes here
        
        return True
    
    def get_party_statistics(self, party_id: str) -> Dict[str, Any]:
        """Get party statistics and information"""
        
        party = self.get_party(party_id)
        if not party:
            return {}
        
        # Calculate party level (this would require character data)
        # For now, just return basic stats
        
        days_active = (datetime.utcnow() - party.created_at).days
        last_session_days = None
        if party.last_session:
            last_session_days = (date.today() - party.last_session).days
        
        return {
            "party_id": party.id,
            "name": party.name,
            "member_count": len(party.member_ids),
            "leader_id": party.leader_id,
            "days_active": days_active,
            "days_since_last_session": last_session_days,
            "objectives_count": len(party.objectives),
            "reputation_count": len(party.reputation),
            "average_reputation": sum(party.reputation.values()) / len(party.reputation) if party.reputation else 0,
            "shared_funds": self._get_party_fund_summary(party_id)
        }
    
    def create_party_communication(
        self, 
        party_id: str,
        sender_id: str,
        message: str,
        message_type: str = "general"
    ) -> Dict[str, Any]:
        """Create a party communication/announcement"""
        
        party = self.get_party(party_id)
        if not party or sender_id not in party.member_ids:
            return {}
        
        communication = {
            "id": str(datetime.utcnow().timestamp()),
            "party_id": party_id,
            "sender_id": sender_id,
            "message": message,
            "message_type": message_type,
            "created_at": datetime.utcnow(),
            "read_by": [sender_id]  # Sender has already "read" it
        }
        
        # In a full implementation, this would be stored in a message system
        return communication
    
    def calculate_party_synergy(self, party_id: str, character_data: List[Character]) -> Dict[str, Any]:
        """Calculate party composition and synergy"""
        
        party = self.get_party(party_id)
        if not party:
            return {}
        
        # Filter characters to party members
        party_characters = [c for c in character_data if c.id in party.member_ids]
        
        if not party_characters:
            return {"synergy_score": 0, "recommendations": []}
        
        synergy_score = 50  # Base score
        recommendations = []
        
        # Class distribution
        classes = [c.character_class.lower() for c in party_characters if c.character_class]
        class_counts = {cls: classes.count(cls) for cls in set(classes)}
        
        # Check for role coverage
        roles = {
            "tank": ["fighter", "paladin", "barbarian"],
            "healer": ["cleric", "druid", "bard"],
            "damage": ["wizard", "sorcerer", "warlock", "ranger", "rogue"],
            "support": ["bard", "cleric", "druid"]
        }
        
        covered_roles = set()
        for character in party_characters:
            char_class = character.character_class.lower()
            for role, role_classes in roles.items():
                if char_class in role_classes:
                    covered_roles.add(role)
        
        # Bonus for role coverage
        synergy_score += len(covered_roles) * 10
        
        # Penalty for missing essential roles
        if "tank" not in covered_roles:
            synergy_score -= 15
            recommendations.append("Consider adding a tank class (Fighter, Paladin, Barbarian)")
        
        if "healer" not in covered_roles:
            synergy_score -= 10
            recommendations.append("Consider adding a healer class (Cleric, Druid, Bard)")
        
        # Check for party size
        party_size = len(party_characters)
        if party_size < 3:
            synergy_score -= 20
            recommendations.append("Party might benefit from additional members")
        elif party_size > 6:
            synergy_score -= 10
            recommendations.append("Large party may face coordination challenges")
        
        # Level balance
        levels = [c.level for c in party_characters]
        level_range = max(levels) - min(levels) if levels else 0
        
        if level_range > 3:
            synergy_score -= 15
            recommendations.append("Consider leveling to reduce level disparity")
        
        # Attribute synergy (simplified)
        # This would be more complex with actual character data
        synergy_score = max(0, min(100, synergy_score))
        
        return {
            "synergy_score": synergy_score,
            "party_size": party_size,
            "class_distribution": class_counts,
            "covered_roles": list(covered_roles),
            "missing_roles": [role for role in roles.keys() if role not in covered_roles],
            "level_range": level_range,
            "recommendations": recommendations
        }
    
    def suggest_party_formation(
        self, 
        available_characters: List[Character],
        preferred_size: int = 4
    ) -> List[Dict[str, Any]]:
        """Suggest optimal party formations from available characters"""
        
        if len(available_characters) < preferred_size:
            return []
        
        suggestions = []
        
        # Group characters by class/role
        role_characters = {
            "tank": [],
            "healer": [],
            "damage": [],
            "support": []
        }
        
        role_mappings = {
            "fighter": "tank", "paladin": "tank", "barbarian": "tank",
            "cleric": "healer", "druid": "healer",
            "wizard": "damage", "sorcerer": "damage", "warlock": "damage", 
            "ranger": "damage", "rogue": "damage",
            "bard": "support"
        }
        
        for char in available_characters:
            char_class = char.character_class.lower()
            role = role_mappings.get(char_class, "damage")
            role_characters[role].append(char)
        
        # Try to build balanced parties
        # This is a simplified approach - could use more sophisticated algorithms
        
        if (role_characters["tank"] and role_characters["healer"] and 
            len(role_characters["damage"]) >= 2):
            
            suggestion = {
                "formation_type": "balanced",
                "characters": [
                    role_characters["tank"][0].id,
                    role_characters["healer"][0].id,
                    role_characters["damage"][0].id,
                    role_characters["damage"][1].id if len(role_characters["damage"]) > 1 else role_characters["support"][0].id if role_characters["support"] else None
                ],
                "synergy_score": 85,
                "description": "Well-balanced party with tank, healer, and damage dealers"
            }
            
            # Remove None values
            suggestion["characters"] = [c for c in suggestion["characters"] if c]
            
            if len(suggestion["characters"]) >= 3:
                suggestions.append(suggestion)
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def _get_party_fund_summary(self, party_id: str) -> Dict[str, Any]:
        """Get summary of party funds"""
        
        fund = self.party_funds.get(party_id)
        if not fund:
            return {"total_gp_value": 0, "balances": {}}
        
        # Convert all currency to GP for total
        conversion_rates = {"pp": 10, "gp": 1, "sp": 0.1, "cp": 0.01}
        total_gp = 0
        
        for currency, amount in fund.balances.items():
            if currency in conversion_rates:
                total_gp += amount * conversion_rates[currency]
        
        return {
            "total_gp_value": total_gp,
            "balances": fund.balances.copy(),
            "managers": len(fund.managers),
            "transactions": len(fund.transactions)
        }