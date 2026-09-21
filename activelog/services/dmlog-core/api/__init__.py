"""
API router modules for the DMLog Core RPG Rules Engine.
"""

from .dice import router as dice_router
from .character import router as character_router
from .combat import router as combat_router
from .spell import router as spell_router
# from .inventory import router as inventory_router  # Service not implemented yet
# from .npc import router as npc_router  # models.npc not implemented yet
from .encounter import router as encounter_router
from .experience import router as experience_router
from .loot import router as loot_router
from .campaign import router as campaign_router
from .rules import router as rules_router
from .relationship import router as relationship_router

__all__ = [
    "dice_router",
    "character_router", 
    "combat_router",
    "spell_router",
    # "inventory_router",
    # "npc_router",
    "encounter_router",
    "experience_router",
    "loot_router", 
    "campaign_router",
    "rules_router",
    "relationship_router"
]