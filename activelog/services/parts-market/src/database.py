"""
Database models for Parts Marketplace Service
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey, Float, Numeric, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


# Enums
class VendorType(str, Enum):
    RETAILER = "retailer"
    DISTRIBUTOR = "distributor"
    MANUFACTURER = "manufacturer"
    INDIVIDUAL = "individual"
    GARAGE_SALE = "garage_sale"


class ComponentCategory(str, Enum):
    ELECTRONIC = "electronic"
    MECHANICAL = "mechanical"
    MATERIAL = "material"
    TOOL = "tool"
    CONSUMABLE = "consumable"
    HARDWARE = "hardware"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    PCB = "pcb"
    CABLE = "cable"


class ComponentType(str, Enum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    TRANSISTOR = "transistor"
    DIODE = "diode"
    IC = "integrated_circuit"
    CONNECTOR = "connector"
    SWITCH = "switch"
    RELAY = "relay"
    SENSOR = "sensor"
    MOTOR = "motor"
    SERVO = "servo"
    BEARING = "bearing"
    SCREW = "screw"
    NUT = "nut"
    WASHER = "washer"
    WIRE = "wire"
    PCB = "pcb"
    BREADBOARD = "breadboard"
    ENCLOSURE = "enclosure"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class ShippingMethod(str, Enum):
    LOCAL_PICKUP = "local_pickup"
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    INTERNATIONAL = "international"
    FREIGHT = "freight"


class NotificationType(str, Enum):
    AVAILABILITY = "availability"
    PRICE_DROP = "price_drop"
    STOCK_ALERT = "stock_alert"
    REORDER = "reorder"
    PROMOTION = "promotion"


class ListingType(str, Enum):
    REGULAR = "regular"
    GARAGE_SALE = "garage_sale"
    BULK = "bulk"
    AUCTION = "auction"


# Core Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(JSON, nullable=True)  # Street, city, state, zip, country
    preferences = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    vendors = relationship("Vendor", back_populates="owner")
    orders = relationship("Order", back_populates="buyer")
    reviews = relationship("Review", back_populates="reviewer")
    notifications = relationship("Notification", back_populates="user")


class Vendor(Base):
    __tablename__ = "vendors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    vendor_type = Column(SQLEnum(VendorType), nullable=False)
    description = Column(Text, nullable=True)
    business_address = Column(JSON, nullable=True)
    contact_info = Column(JSON, nullable=True)
    shipping_locations = Column(JSON, nullable=True)  # Countries/regions they ship to
    pickup_locations = Column(JSON, nullable=True)   # Physical pickup locations
    payment_methods = Column(JSON, nullable=True)
    policies = Column(JSON, nullable=True)  # Return, shipping policies
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="vendors")
    inventory_items = relationship("InventoryItem", back_populates="vendor")
    orders = relationship("Order", back_populates="vendor")
    reviews = relationship("Review", back_populates="vendor")


class Component(Base):
    __tablename__ = "components"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    part_number = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    category = Column(SQLEnum(ComponentCategory), nullable=False)
    component_type = Column(SQLEnum(ComponentType), nullable=False)
    description = Column(Text, nullable=True)
    specifications = Column(JSON, nullable=False)  # Technical specs
    datasheet_url = Column(String, nullable=True)
    image_urls = Column(JSON, nullable=True)
    footprint = Column(String, nullable=True)  # For PCB components
    package_type = Column(String, nullable=True)
    operating_conditions = Column(JSON, nullable=True)  # Temperature, voltage, etc.
    compatibility_tags = Column(JSON, nullable=True)  # Tags for compatibility matching
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="component")
    project_components = relationship("ProjectComponent", back_populates="component")


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String, nullable=False)
    quantity_available = Column(Integer, nullable=False, default=0)
    quantity_reserved = Column(Integer, nullable=False, default=0)
    unit_price = Column(Numeric(10, 2), nullable=False)
    bulk_pricing = Column(JSON, nullable=True)  # Quantity-based pricing tiers
    min_order_quantity = Column(Integer, default=1)
    max_order_quantity = Column(Integer, nullable=True)
    condition = Column(String, nullable=True)  # New, used, refurbished
    listing_type = Column(SQLEnum(ListingType), default=ListingType.REGULAR)
    garage_sale_info = Column(JSON, nullable=True)  # Location, date, contact
    lead_time_days = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    component_id = Column(UUID(as_uuid=True), ForeignKey("components.id"), nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="inventory_items")
    component = relationship("Component", back_populates="inventory_items")
    order_items = relationship("OrderItem", back_populates="inventory_item")


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String, unique=True, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    shipping_cost = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    shipping_method = Column(SQLEnum(ShippingMethod), nullable=False)
    shipping_address = Column(JSON, nullable=True)
    tracking_number = Column(String, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    
    # Relationships
    buyer = relationship("User", back_populates="orders")
    vendor = relationship("Vendor", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    inventory_item = relationship("InventoryItem", back_populates="order_items")


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    difficulty_level = Column(String, nullable=True)  # Beginner, Intermediate, Advanced
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    estimated_time = Column(String, nullable=True)
    instructions_url = Column(String, nullable=True)
    image_urls = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    creator = relationship("User")
    project_components = relationship("ProjectComponent", back_populates="project")
    bundles = relationship("Bundle", back_populates="project")


class ProjectComponent(Base):
    __tablename__ = "project_components"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quantity_needed = Column(Integer, nullable=False)
    is_optional = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    component_id = Column(UUID(as_uuid=True), ForeignKey("components.id"), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="project_components")
    component = relationship("Component", back_populates="project_components")


class Bundle(Base):
    __tablename__ = "bundles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    bundle_price = Column(Numeric(10, 2), nullable=False)
    individual_price = Column(Numeric(10, 2), nullable=False)
    discount_percentage = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    
    # Relationships
    vendor = relationship("Vendor")
    project = relationship("Project", back_populates="bundles")
    bundle_items = relationship("BundleItem", back_populates="bundle")


class BundleItem(Base):
    __tablename__ = "bundle_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quantity = Column(Integer, nullable=False)
    bundle_id = Column(UUID(as_uuid=True), ForeignKey("bundles.id"), nullable=False)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    
    # Relationships
    bundle = relationship("Bundle", back_populates="bundle_items")
    inventory_item = relationship("InventoryItem")


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    is_verified_purchase = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    
    # Relationships
    reviewer = relationship("User", back_populates="reviews")
    vendor = relationship("Vendor", back_populates="reviews")
    order = relationship("Order")


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional notification data
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notifications")


class WatchList(Base):
    __tablename__ = "watch_lists"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_price = Column(Numeric(10, 2), nullable=True)
    notify_when_available = Column(Boolean, default=True)
    notify_price_drop = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    component_id = Column(UUID(as_uuid=True), ForeignKey("components.id"), nullable=False)
    
    # Relationships
    user = relationship("User")
    component = relationship("Component")


class ReorderRule(Base):
    __tablename__ = "reorder_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reorder_point = Column(Integer, nullable=False)
    reorder_quantity = Column(Integer, nullable=False)
    max_price = Column(Numeric(10, 2), nullable=True)
    preferred_vendors = Column(JSON, nullable=True)  # List of vendor IDs
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    component_id = Column(UUID(as_uuid=True), ForeignKey("components.id"), nullable=False)
    
    # Relationships
    user = relationship("User")
    component = relationship("Component")


class ManufacturingCapability(Base):
    __tablename__ = "manufacturing_capabilities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capability_type = Column(String, nullable=False)  # 3D_PRINT, CNC, LASER_CUT, PCB
    materials = Column(JSON, nullable=True)  # Supported materials
    specifications = Column(JSON, nullable=False)  # Size limits, tolerances, etc.
    pricing_model = Column(JSON, nullable=False)  # Base price, per-unit, per-volume
    lead_time_days = Column(Integer, nullable=False)
    min_order_value = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, default=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    
    # Relationships
    vendor = relationship("Vendor")


class ShippingRate(Base):
    __tablename__ = "shipping_rates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    origin_country = Column(String, nullable=False)
    origin_region = Column(String, nullable=True)
    destination_country = Column(String, nullable=False)
    destination_region = Column(String, nullable=True)
    shipping_method = Column(SQLEnum(ShippingMethod), nullable=False)
    base_cost = Column(Numeric(10, 2), nullable=False)
    per_kg_cost = Column(Numeric(10, 2), nullable=False)
    per_item_cost = Column(Numeric(10, 2), nullable=True)
    min_delivery_days = Column(Integer, nullable=False)
    max_delivery_days = Column(Integer, nullable=False)
    max_weight_kg = Column(Float, nullable=True)
    max_dimensions = Column(JSON, nullable=True)  # Length, width, height in cm
    restrictions = Column(JSON, nullable=True)  # Item type restrictions
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    
    # Relationships
    vendor = relationship("Vendor")


class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price = Column(Numeric(10, 2), nullable=False)
    quantity_available = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    
    # Relationships
    inventory_item = relationship("InventoryItem")


class CompatibilityRule(Base):
    __tablename__ = "compatibility_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_type = Column(String, nullable=False)  # REQUIRES, CONFLICTS, RECOMMENDS
    description = Column(Text, nullable=True)
    conditions = Column(JSON, nullable=False)  # Rule conditions
    created_at = Column(DateTime, default=datetime.utcnow)
    primary_component_id = Column(UUID(as_uuid=True), ForeignKey("components.id"), nullable=False)
    related_component_id = Column(UUID(as_uuid=True), ForeignKey("components.id"), nullable=False)
    
    # Relationships
    primary_component = relationship("Component", foreign_keys=[primary_component_id])
    related_component = relationship("Component", foreign_keys=[related_component_id])


# Database configuration
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/parts_market"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()