"""
Gear Configuration Tracking System
Comprehensive fishing gear management and performance tracking
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging

logger = logging.getLogger(__name__)

class GearCategory(Enum):
    ROD = "rod"
    REEL = "reel"
    LINE = "line"
    TERMINAL_TACKLE = "terminal_tackle"
    LURE = "lure"
    BAIT = "bait"
    NET = "net"
    ELECTRONICS = "electronics"
    SAFETY = "safety"
    TOOLS = "tools"
    STORAGE = "storage"

class GearCondition(Enum):
    NEW = "new"
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    NEEDS_REPAIR = "needs_repair"
    RETIRED = "retired"

class RodType(Enum):
    SPINNING = "spinning"
    CASTING = "casting"
    FLY = "fly"
    TROLLING = "trolling"
    JIGGING = "jigging"
    SURF = "surf"
    ICE = "ice"

class ReelType(Enum):
    SPINNING = "spinning"
    BAITCASTING = "baitcasting"
    CONVENTIONAL = "conventional"
    FLY = "fly"
    CENTERPIN = "centerpin"

class LineType(Enum):
    MONOFILAMENT = "monofilament"
    FLUOROCARBON = "fluorocarbon"
    BRAIDED = "braided"
    FLY_LINE = "fly_line"
    WIRE = "wire"
    LEAD_CORE = "lead_core"

@dataclass
class GearItem:
    gear_id: str
    name: str
    category: GearCategory
    brand: Optional[str] = None
    model: Optional[str] = None
    description: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    condition: GearCondition = GearCondition.NEW
    location: Optional[str] = None  # Boat, tackle box, home, etc.
    serial_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    maintenance_notes: Optional[str] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    performance_rating: Optional[float] = None  # 1-5 stars
    photos: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.gear_id:
            self.gear_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.specifications is None:
            self.specifications = {}
        if self.photos is None:
            self.photos = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['category'] = self.category.value
        result['condition'] = self.condition.value
        if result.get('purchase_date'):
            result['purchase_date'] = result['purchase_date'].isoformat()
        if result.get('last_used'):
            result['last_used'] = result['last_used'].isoformat()
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        if result.get('updated_at'):
            result['updated_at'] = result['updated_at'].isoformat()
        return result

@dataclass
class GearSetup:
    setup_id: str
    name: str
    description: Optional[str] = None
    gear_items: Optional[List[str]] = None  # List of gear_ids
    target_species: Optional[List[str]] = None
    fishing_techniques: Optional[List[str]] = None
    water_conditions: Optional[str] = None  # Deep water, shallow, structure, etc.
    performance_notes: Optional[str] = None
    success_rate: Optional[float] = None  # Percentage
    times_used: int = 0
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.setup_id:
            self.setup_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.gear_items is None:
            self.gear_items = []
        if self.target_species is None:
            self.target_species = []
        if self.fishing_techniques is None:
            self.fishing_techniques = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if result.get('last_used'):
            result['last_used'] = result['last_used'].isoformat()
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        if result.get('updated_at'):
            result['updated_at'] = result['updated_at'].isoformat()
        return result

@dataclass
class MaintenanceRecord:
    record_id: str
    gear_id: str
    maintenance_date: datetime
    maintenance_type: str  # cleaning, repair, replacement, inspection
    description: str
    cost: Optional[float] = None
    performed_by: Optional[str] = None
    next_maintenance_due: Optional[datetime] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if not self.record_id:
            self.record_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['maintenance_date'] = self.maintenance_date.isoformat()
        if result.get('next_maintenance_due'):
            result['next_maintenance_due'] = result['next_maintenance_due'].isoformat()
        return result

class GearDatabase:
    """SQLite database for gear management"""
    
    def __init__(self, db_path: str = "fishing_gear.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Gear items table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gear_items (
                    gear_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    description TEXT,
                    purchase_date TEXT,
                    purchase_price REAL,
                    condition TEXT NOT NULL,
                    location TEXT,
                    serial_number TEXT,
                    specifications TEXT,
                    maintenance_notes TEXT,
                    last_used TEXT,
                    usage_count INTEGER DEFAULT 0,
                    performance_rating REAL,
                    photos TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Gear setups table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gear_setups (
                    setup_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    gear_items TEXT,
                    target_species TEXT,
                    fishing_techniques TEXT,
                    water_conditions TEXT,
                    performance_notes TEXT,
                    success_rate REAL,
                    times_used INTEGER DEFAULT 0,
                    last_used TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Maintenance records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_records (
                    record_id TEXT PRIMARY KEY,
                    gear_id TEXT NOT NULL,
                    maintenance_date TEXT NOT NULL,
                    maintenance_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    cost REAL,
                    performed_by TEXT,
                    next_maintenance_due TEXT,
                    notes TEXT,
                    FOREIGN KEY (gear_id) REFERENCES gear_items (gear_id)
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_gear_category 
                ON gear_items(category)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_gear_condition 
                ON gear_items(condition)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_maintenance_gear 
                ON maintenance_records(gear_id)
            """)
    
    def save_gear_item(self, item: GearItem) -> bool:
        """Save gear item to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO gear_items (
                        gear_id, name, category, brand, model, description,
                        purchase_date, purchase_price, condition, location,
                        serial_number, specifications, maintenance_notes,
                        last_used, usage_count, performance_rating, photos,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.gear_id, item.name, item.category.value, item.brand, item.model,
                    item.description,
                    item.purchase_date.isoformat() if item.purchase_date else None,
                    item.purchase_price, item.condition.value, item.location,
                    item.serial_number,
                    json.dumps(item.specifications) if item.specifications else None,
                    item.maintenance_notes,
                    item.last_used.isoformat() if item.last_used else None,
                    item.usage_count, item.performance_rating,
                    json.dumps(item.photos) if item.photos else None,
                    item.created_at.isoformat(), item.updated_at.isoformat()
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save gear item: {e}")
            return False
    
    def get_gear_item(self, gear_id: str) -> Optional[Dict[str, Any]]:
        """Get gear item by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM gear_items WHERE gear_id = ?
            """, (gear_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_gear_items(self, category: Optional[GearCategory] = None, 
                      condition: Optional[GearCondition] = None) -> List[Dict[str, Any]]:
        """Get gear items with optional filtering"""
        query = "SELECT * FROM gear_items"
        params = []
        conditions = []
        
        if category:
            conditions.append("category = ?")
            params.append(category.value)
        
        if condition:
            conditions.append("condition = ?")
            params.append(condition.value)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY name"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_gear_setup(self, setup: GearSetup) -> bool:
        """Save gear setup to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO gear_setups (
                        setup_id, name, description, gear_items, target_species,
                        fishing_techniques, water_conditions, performance_notes,
                        success_rate, times_used, last_used, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    setup.setup_id, setup.name, setup.description,
                    json.dumps(setup.gear_items) if setup.gear_items else None,
                    json.dumps(setup.target_species) if setup.target_species else None,
                    json.dumps(setup.fishing_techniques) if setup.fishing_techniques else None,
                    setup.water_conditions, setup.performance_notes,
                    setup.success_rate, setup.times_used,
                    setup.last_used.isoformat() if setup.last_used else None,
                    setup.created_at.isoformat(), setup.updated_at.isoformat()
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save gear setup: {e}")
            return False
    
    def get_gear_setups(self) -> List[Dict[str, Any]]:
        """Get all gear setups"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM gear_setups ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_maintenance_record(self, record: MaintenanceRecord) -> bool:
        """Save maintenance record"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO maintenance_records (
                        record_id, gear_id, maintenance_date, maintenance_type,
                        description, cost, performed_by, next_maintenance_due, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.record_id, record.gear_id,
                    record.maintenance_date.isoformat(), record.maintenance_type,
                    record.description, record.cost, record.performed_by,
                    record.next_maintenance_due.isoformat() if record.next_maintenance_due else None,
                    record.notes
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save maintenance record: {e}")
            return False
    
    def get_maintenance_records(self, gear_id: str) -> List[Dict[str, Any]]:
        """Get maintenance records for gear item"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM maintenance_records 
                WHERE gear_id = ?
                ORDER BY maintenance_date DESC
            """, (gear_id,))
            return [dict(row) for row in cursor.fetchall()]

class GearManager:
    """Main gear management service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.database = GearDatabase(self.config.get('database_path', 'fishing_gear.db'))
    
    def add_gear_item(self, name: str, category: GearCategory, 
                     brand: Optional[str] = None, model: Optional[str] = None,
                     **kwargs) -> GearItem:
        """Add a new gear item"""
        item = GearItem(
            gear_id=str(uuid.uuid4()),
            name=name,
            category=category,
            brand=brand,
            model=model,
            **kwargs
        )
        
        success = self.database.save_gear_item(item)
        if success:
            logger.info(f"Added gear item: {name} ({item.gear_id})")
        else:
            logger.error(f"Failed to add gear item: {name}")
        
        return item
    
    def update_gear_condition(self, gear_id: str, condition: GearCondition, 
                            notes: Optional[str] = None) -> bool:
        """Update gear condition"""
        item_data = self.database.get_gear_item(gear_id)
        if not item_data:
            return False
        
        # Update condition
        item_data['condition'] = condition.value
        if notes:
            item_data['maintenance_notes'] = notes
        item_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Convert back to GearItem and save
        item = self._dict_to_gear_item(item_data)
        return self.database.save_gear_item(item)
    
    def record_gear_usage(self, gear_id: str, used_date: Optional[datetime] = None) -> bool:
        """Record gear usage"""
        item_data = self.database.get_gear_item(gear_id)
        if not item_data:
            return False
        
        if used_date is None:
            used_date = datetime.now(timezone.utc)
        
        # Update usage stats
        item_data['last_used'] = used_date.isoformat()
        item_data['usage_count'] = (item_data.get('usage_count', 0) or 0) + 1
        item_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Convert back to GearItem and save
        item = self._dict_to_gear_item(item_data)
        return self.database.save_gear_item(item)
    
    def create_gear_setup(self, name: str, gear_ids: List[str],
                         target_species: Optional[List[str]] = None,
                         **kwargs) -> GearSetup:
        """Create a gear setup configuration"""
        setup = GearSetup(
            setup_id=str(uuid.uuid4()),
            name=name,
            gear_items=gear_ids,
            target_species=target_species or [],
            **kwargs
        )
        
        success = self.database.save_gear_setup(setup)
        if success:
            logger.info(f"Created gear setup: {name} ({setup.setup_id})")
        else:
            logger.error(f"Failed to create gear setup: {name}")
        
        return setup
    
    def record_setup_usage(self, setup_id: str, success: bool, 
                          catches_count: int = 0) -> bool:
        """Record usage of a gear setup"""
        setups = self.database.get_gear_setups()
        setup_data = None
        
        for setup in setups:
            if setup['setup_id'] == setup_id:
                setup_data = setup
                break
        
        if not setup_data:
            return False
        
        # Update setup statistics
        times_used = (setup_data.get('times_used', 0) or 0) + 1
        setup_data['times_used'] = times_used
        setup_data['last_used'] = datetime.now(timezone.utc).isoformat()
        
        # Update success rate
        current_success_rate = setup_data.get('success_rate', 0) or 0
        if times_used == 1:
            new_success_rate = 100.0 if success else 0.0
        else:
            # Weighted average of previous success rate
            total_successes = (current_success_rate / 100.0) * (times_used - 1)
            if success:
                total_successes += 1
            new_success_rate = (total_successes / times_used) * 100.0
        
        setup_data['success_rate'] = new_success_rate
        setup_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Convert back to GearSetup and save
        setup = self._dict_to_gear_setup(setup_data)
        
        # Also record usage for individual gear items
        gear_ids = setup.gear_items or []
        for gear_id in gear_ids:
            self.record_gear_usage(gear_id)
        
        return self.database.save_gear_setup(setup)
    
    def add_maintenance_record(self, gear_id: str, maintenance_type: str,
                             description: str, cost: Optional[float] = None,
                             **kwargs) -> MaintenanceRecord:
        """Add maintenance record for gear item"""
        record = MaintenanceRecord(
            record_id=str(uuid.uuid4()),
            gear_id=gear_id,
            maintenance_date=datetime.now(timezone.utc),
            maintenance_type=maintenance_type,
            description=description,
            cost=cost,
            **kwargs
        )
        
        success = self.database.save_maintenance_record(record)
        if success:
            logger.info(f"Added maintenance record for gear {gear_id}: {maintenance_type}")
        else:
            logger.error(f"Failed to add maintenance record for gear {gear_id}")
        
        return record
    
    def get_gear_inventory(self, category: Optional[GearCategory] = None) -> Dict[str, Any]:
        """Get gear inventory summary"""
        items = self.database.get_gear_items(category=category)
        
        # Calculate statistics
        total_items = len(items)
        total_value = sum(item.get('purchase_price', 0) or 0 for item in items)
        
        condition_counts = {}
        category_counts = {}
        
        for item in items:
            # Count by condition
            condition = item.get('condition', 'unknown')
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
            
            # Count by category
            cat = item.get('category', 'unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Find items needing attention
        needs_maintenance = [item for item in items 
                           if item.get('condition') in ['needs_repair', 'poor']]
        
        return {
            'total_items': total_items,
            'total_value': total_value,
            'condition_breakdown': condition_counts,
            'category_breakdown': category_counts,
            'items': items,
            'needs_maintenance': needs_maintenance
        }
    
    def get_gear_recommendations(self, target_species: str) -> List[Dict[str, Any]]:
        """Get gear recommendations based on target species and setup performance"""
        setups = self.database.get_gear_setups()
        
        # Find setups that target this species
        relevant_setups = []
        for setup in setups:
            target_species_list = json.loads(setup.get('target_species', '[]'))
            if target_species.lower() in [s.lower() for s in target_species_list]:
                relevant_setups.append(setup)
        
        # Sort by success rate and times used
        def sort_key(setup):
            success_rate = setup.get('success_rate', 0) or 0
            times_used = setup.get('times_used', 0) or 0
            # Weight success rate more heavily, but give credit for proven setups
            return success_rate * 0.8 + min(times_used * 2, 20) * 0.2
        
        relevant_setups.sort(key=sort_key, reverse=True)
        
        recommendations = []
        for setup in relevant_setups[:5]:  # Top 5 recommendations
            # Get gear details
            gear_ids = json.loads(setup.get('gear_items', '[]'))
            gear_details = []
            
            for gear_id in gear_ids:
                gear_item = self.database.get_gear_item(gear_id)
                if gear_item:
                    gear_details.append(gear_item)
            
            recommendations.append({
                'setup': setup,
                'gear_details': gear_details,
                'recommendation_score': sort_key(setup)
            })
        
        return recommendations
    
    def get_maintenance_schedule(self) -> List[Dict[str, Any]]:
        """Get maintenance schedule for all gear"""
        items = self.database.get_gear_items()
        maintenance_items = []
        
        for item in items:
            # Get latest maintenance records
            records = self.database.get_maintenance_records(item['gear_id'])
            
            # Check if maintenance is due
            condition = item.get('condition')
            last_maintenance = None
            
            if records:
                latest_record = records[0]  # Most recent
                last_maintenance = datetime.fromisoformat(latest_record['maintenance_date'])
                next_due = latest_record.get('next_maintenance_due')
                if next_due:
                    next_due_date = datetime.fromisoformat(next_due)
                    if next_due_date <= datetime.now(timezone.utc):
                        maintenance_items.append({
                            'gear_item': item,
                            'reason': 'scheduled_maintenance',
                            'last_maintenance': last_maintenance,
                            'next_due': next_due_date
                        })
            
            # Check for condition-based maintenance needs
            if condition in ['needs_repair', 'poor']:
                maintenance_items.append({
                    'gear_item': item,
                    'reason': 'condition_based',
                    'last_maintenance': last_maintenance
                })
            
            # Check for usage-based maintenance (high usage items)
            usage_count = item.get('usage_count', 0) or 0
            if usage_count > 50 and not records:  # High usage, no maintenance records
                maintenance_items.append({
                    'gear_item': item,
                    'reason': 'usage_based',
                    'usage_count': usage_count
                })
        
        # Sort by priority
        def priority_key(item):
            if item['reason'] == 'condition_based':
                return 1
            elif item['reason'] == 'scheduled_maintenance':
                return 2
            else:
                return 3
        
        return sorted(maintenance_items, key=priority_key)
    
    def _dict_to_gear_item(self, data: Dict[str, Any]) -> GearItem:
        """Convert dictionary to GearItem"""
        # Parse JSON fields
        if isinstance(data.get('specifications'), str):
            data['specifications'] = json.loads(data['specifications'])
        if isinstance(data.get('photos'), str):
            data['photos'] = json.loads(data['photos'])
        
        # Parse datetime fields
        datetime_fields = ['purchase_date', 'last_used', 'created_at', 'updated_at']
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Parse enum fields
        data['category'] = GearCategory(data['category'])
        data['condition'] = GearCondition(data['condition'])
        
        return GearItem(**data)
    
    def _dict_to_gear_setup(self, data: Dict[str, Any]) -> GearSetup:
        """Convert dictionary to GearSetup"""
        # Parse JSON fields
        json_fields = ['gear_items', 'target_species', 'fishing_techniques']
        for field in json_fields:
            if isinstance(data.get(field), str):
                data[field] = json.loads(data[field])
        
        # Parse datetime fields
        datetime_fields = ['last_used', 'created_at', 'updated_at']
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        return GearSetup(**data)

async def main():
    """Example usage of gear tracking system"""
    
    # Initialize gear manager
    gear_manager = GearManager({
        'database_path': 'fishing_gear.db'
    })
    
    print("=== Gear Tracking System Demo ===")
    
    # Add some gear items
    rod1 = gear_manager.add_gear_item(
        name="Shimano Stradic Rod",
        category=GearCategory.ROD,
        brand="Shimano",
        model="Stradic CI4+",
        description="7' medium action spinning rod",
        purchase_price=150.0,
        condition=GearCondition.EXCELLENT,
        location="boat",
        specifications={
            "length": "7'0\"",
            "action": "medium",
            "power": "medium",
            "line_weight": "10-17 lb",
            "lure_weight": "1/4-3/4 oz"
        }
    )
    
    reel1 = gear_manager.add_gear_item(
        name="Penn Battle III Reel",
        category=GearCategory.REEL,
        brand="Penn",
        model="Battle III 3000",
        description="Spinning reel with 5+1 bearings",
        purchase_price=89.99,
        condition=GearCondition.GOOD,
        location="boat",
        specifications={
            "size": "3000",
            "gear_ratio": "6.2:1",
            "line_capacity": "240/12",
            "bearings": "5+1",
            "max_drag": "20 lb"
        }
    )
    
    line1 = gear_manager.add_gear_item(
        name="PowerPro Braided Line",
        category=GearCategory.LINE,
        brand="PowerPro",
        model="Super 8 Slick",
        description="15lb braided fishing line",
        purchase_price=24.99,
        condition=GearCondition.GOOD,
        specifications={
            "test_strength": "15 lb",
            "diameter": "0.008\"",
            "material": "braided",
            "length": "300 yards"
        }
    )
    
    print(f"Added rod: {rod1.name} ({rod1.gear_id})")
    print(f"Added reel: {reel1.name} ({reel1.gear_id})")
    print(f"Added line: {line1.name} ({line1.gear_id})")
    
    # Create a gear setup
    setup1 = gear_manager.create_gear_setup(
        name="Striper Setup #1",
        gear_ids=[rod1.gear_id, reel1.gear_id, line1.gear_id],
        target_species=["Striped Bass", "Bluefish"],
        fishing_techniques=["trolling", "casting"],
        water_conditions="moderate depth, structure",
        description="Versatile setup for striped bass fishing"
    )
    
    print(f"\nCreated setup: {setup1.name} ({setup1.setup_id})")
    
    # Record setup usage
    success = gear_manager.record_setup_usage(setup1.setup_id, success=True, catches_count=3)
    if success:
        print("Recorded successful fishing trip with setup")
    
    # Add maintenance record
    maintenance = gear_manager.add_maintenance_record(
        gear_id=reel1.gear_id,
        maintenance_type="cleaning",
        description="Cleaned and lubricated reel after saltwater use",
        cost=0.0,
        performed_by="self",
        notes="Reel was full of salt, cleaned thoroughly"
    )
    
    print(f"Added maintenance record: {maintenance.description}")
    
    # Get inventory summary
    inventory = gear_manager.get_gear_inventory()
    print(f"\nInventory Summary:")
    print(f"- Total items: {inventory['total_items']}")
    print(f"- Total value: ${inventory['total_value']:.2f}")
    print(f"- Categories: {inventory['category_breakdown']}")
    print(f"- Conditions: {inventory['condition_breakdown']}")
    
    # Get gear recommendations
    recommendations = gear_manager.get_gear_recommendations("Striped Bass")
    print(f"\nRecommendations for Striped Bass:")
    for i, rec in enumerate(recommendations, 1):
        setup = rec['setup']
        print(f"{i}. {setup['name']} (Score: {rec['recommendation_score']:.1f})")
        print(f"   Success rate: {setup.get('success_rate', 0):.1f}%")
        print(f"   Times used: {setup.get('times_used', 0)}")
    
    # Get maintenance schedule
    maintenance_schedule = gear_manager.get_maintenance_schedule()
    print(f"\nMaintenance Schedule:")
    if maintenance_schedule:
        for item in maintenance_schedule:
            gear = item['gear_item']
            print(f"- {gear['name']}: {item['reason']}")
    else:
        print("No maintenance items due")

if __name__ == "__main__":
    asyncio.run(main())