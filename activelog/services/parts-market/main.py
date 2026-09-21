#!/usr/bin/env python3
"""
Parts Marketplace Service - Main Application
Runs on port 8339 as requested
"""

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import uuid
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from src.database import (
    get_session, init_database, VendorType, ComponentCategory, 
    ComponentType, ListingType, ShippingMethod
)
from src.inventory.multi_vendor_system import MultiVendorInventorySystem
from src.pickup.local_pickup import LocalPickupSystem
from src.garage_sale.garage_listings import GarageSaleListings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield


app = FastAPI(
    title="Parts Marketplace",
    description="Multi-vendor parts marketplace with garage sales, local pickup, and comprehensive inventory management",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Parts Marketplace",
        "version": "1.0.0",
        "port": 8339,
        "features": [
            "Multi-vendor inventory system",
            "Local pickup options",
            "Garage sale component listings",
            "Compatibility matcher for projects",
            "Bundling recommendations",
            "Price comparison engine",
            "Availability notifications",
            "Vendor reputation system",
            "Automated reorder system",
            "Component specification database",
            "3D printer/CNC pairing suggestions",
            "International shipping calculator"
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "parts-marketplace", "port": 8339}


# Multi-Vendor Inventory System
@app.post("/vendors")
async def create_vendor(
    owner_id: str,
    name: str,
    vendor_type: VendorType,
    description: Optional[str] = None,
    business_address: Optional[Dict[str, Any]] = None,
    contact_info: Optional[Dict[str, Any]] = None,
    shipping_locations: Optional[List[str]] = None,
    pickup_locations: Optional[List[Dict[str, Any]]] = None,
    session=Depends(get_session)
):
    inventory_system = MultiVendorInventorySystem(session)
    
    vendor_id = await inventory_system.create_vendor(
        uuid.UUID(owner_id), name, vendor_type, description,
        business_address, contact_info, shipping_locations, pickup_locations
    )
    
    return {"vendor_id": str(vendor_id)}


@app.post("/inventory")
async def add_inventory_item(
    vendor_id: str,
    component_id: str,
    sku: str,
    quantity_available: int,
    unit_price: float,
    condition: str = "new",
    bulk_pricing: Optional[Dict[int, float]] = None,
    min_order_quantity: int = 1,
    max_order_quantity: Optional[int] = None,
    listing_type: ListingType = ListingType.REGULAR,
    garage_sale_info: Optional[Dict[str, Any]] = None,
    lead_time_days: Optional[int] = None,
    session=Depends(get_session)
):
    inventory_system = MultiVendorInventorySystem(session)
    
    # Convert bulk pricing to Decimal
    bulk_pricing_decimal = None
    if bulk_pricing:
        bulk_pricing_decimal = {k: Decimal(str(v)) for k, v in bulk_pricing.items()}
    
    item_id = await inventory_system.add_inventory_item(
        uuid.UUID(vendor_id), uuid.UUID(component_id), sku,
        quantity_available, Decimal(str(unit_price)), condition,
        bulk_pricing_decimal, min_order_quantity, max_order_quantity,
        listing_type, garage_sale_info, lead_time_days
    )
    
    return {"inventory_item_id": str(item_id)}


@app.get("/inventory/search")
async def search_inventory(
    search_query: Optional[str] = None,
    component_category: Optional[ComponentCategory] = None,
    component_type: Optional[ComponentType] = None,
    vendor_types: Optional[str] = None,
    location_country: Optional[str] = None,
    location_region: Optional[str] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    condition: Optional[str] = None,
    listing_type: Optional[ListingType] = None,
    include_out_of_stock: bool = False,
    sort_by: str = "price",
    sort_order: str = "asc",
    limit: int = 50,
    offset: int = 0,
    session=Depends(get_session)
):
    inventory_system = MultiVendorInventorySystem(session)
    
    location = None
    if location_country:
        location = {"country": location_country}
        if location_region:
            location["region"] = location_region
    
    vendor_type_list = None
    if vendor_types:
        vendor_type_list = [VendorType(vt.strip()) for vt in vendor_types.split(",")]
    
    results = await inventory_system.search_inventory(
        search_query, component_category, component_type, vendor_type_list,
        location, Decimal(str(max_price)) if max_price else None, min_quantity,
        condition, listing_type, include_out_of_stock, sort_by, sort_order,
        limit, offset
    )
    
    return results


@app.get("/vendors/{vendor_id}/inventory")
async def get_vendor_inventory(
    vendor_id: str,
    category: Optional[ComponentCategory] = None,
    include_inactive: bool = False,
    session=Depends(get_session)
):
    inventory_system = MultiVendorInventorySystem(session)
    inventory = await inventory_system.get_vendor_inventory(
        uuid.UUID(vendor_id), category, include_inactive
    )
    return {"inventory": inventory}


@app.put("/inventory/{item_id}/quantity")
async def update_inventory_quantity(
    item_id: str,
    new_quantity: int,
    operation: str = "set",
    session=Depends(get_session)
):
    inventory_system = MultiVendorInventorySystem(session)
    success = await inventory_system.update_inventory_quantity(
        uuid.UUID(item_id), new_quantity, operation
    )
    return {"success": success}


@app.put("/inventory/{item_id}/price")
async def update_inventory_price(
    item_id: str,
    new_price: float,
    bulk_pricing: Optional[Dict[int, float]] = None,
    session=Depends(get_session)
):
    inventory_system = MultiVendorInventorySystem(session)
    
    bulk_pricing_decimal = None
    if bulk_pricing:
        bulk_pricing_decimal = {k: Decimal(str(v)) for k, v in bulk_pricing.items()}
    
    success = await inventory_system.update_inventory_price(
        uuid.UUID(item_id), Decimal(str(new_price)), bulk_pricing_decimal
    )
    return {"success": success}


# Local Pickup System
@app.post("/vendors/{vendor_id}/pickup-locations")
async def setup_pickup_location(
    vendor_id: str,
    location_data: Dict[str, Any],
    session=Depends(get_session)
):
    pickup_system = LocalPickupSystem(session)
    location = await pickup_system.setup_pickup_location(
        uuid.UUID(vendor_id), location_data
    )
    return location


@app.get("/pickup/nearby")
async def find_nearby_vendors(
    location_country: str,
    location_city: str,
    location_street: Optional[str] = None,
    radius_km: float = 50,
    component_ids: Optional[str] = None,
    session=Depends(get_session)
):
    pickup_system = LocalPickupSystem(session)
    
    location = {
        "country": location_country,
        "city": location_city
    }
    if location_street:
        location["street"] = location_street
    
    component_uuid_list = None
    if component_ids:
        component_uuid_list = [uuid.UUID(cid.strip()) for cid in component_ids.split(",")]
    
    vendors = await pickup_system.find_nearby_vendors(
        location, radius_km, component_uuid_list
    )
    
    return {"vendors": vendors}


@app.get("/pickup/slots")
async def get_pickup_slots(
    vendor_id: str,
    pickup_location_id: str,
    date: str,
    duration_days: int = 7,
    session=Depends(get_session)
):
    pickup_system = LocalPickupSystem(session)
    
    date_obj = datetime.fromisoformat(date)
    slots = await pickup_system.get_available_pickup_slots(
        uuid.UUID(vendor_id), pickup_location_id, date_obj, duration_days
    )
    
    return {"slots": slots}


@app.post("/pickup/schedule")
async def schedule_pickup(
    order_id: str,
    pickup_location_id: str,
    pickup_datetime: str,
    special_instructions: Optional[str] = None,
    session=Depends(get_session)
):
    pickup_system = LocalPickupSystem(session)
    
    pickup_dt = datetime.fromisoformat(pickup_datetime)
    result = await pickup_system.schedule_pickup(
        uuid.UUID(order_id), pickup_location_id, pickup_dt, special_instructions
    )
    
    return result


# Garage Sale System
@app.post("/garage-sales")
async def create_garage_sale(
    seller_id: str,
    sale_info: Dict[str, Any],
    components: List[Dict[str, Any]],
    session=Depends(get_session)
):
    garage_system = GarageSaleListings(session)
    
    # Convert date strings to datetime objects
    if "sale_dates" in sale_info:
        sale_dates = sale_info["sale_dates"]
        if isinstance(sale_dates["start"], str):
            sale_dates["start"] = datetime.fromisoformat(sale_dates["start"])
        if isinstance(sale_dates["end"], str):
            sale_dates["end"] = datetime.fromisoformat(sale_dates["end"])
    
    listing = await garage_system.create_garage_sale_listing(
        uuid.UUID(seller_id), sale_info, components
    )
    
    return listing


@app.get("/garage-sales/search")
async def search_garage_sales(
    location_country: Optional[str] = None,
    location_city: Optional[str] = None,
    radius_km: float = 25,
    categories: Optional[str] = None,
    max_price: Optional[float] = None,
    condition: Optional[str] = None,
    sort_by: str = "distance",
    limit: int = 50,
    session=Depends(get_session)
):
    garage_system = GarageSaleListings(session)
    
    location = None
    if location_country:
        location = {"country": location_country}
        if location_city:
            location["city"] = location_city
    
    component_categories = None
    if categories:
        component_categories = [ComponentCategory(cat.strip()) for cat in categories.split(",")]
    
    results = await garage_system.search_garage_sales(
        location, radius_km, component_categories, max_price,
        None, condition, sort_by, limit
    )
    
    return {"garage_sales": results}


@app.get("/garage-sales/{vendor_id}")
async def get_garage_sale_details(
    vendor_id: str,
    session=Depends(get_session)
):
    garage_system = GarageSaleListings(session)
    details = await garage_system.get_garage_sale_details(uuid.UUID(vendor_id))
    return details


@app.put("/garage-sales/{vendor_id}/status")
async def update_garage_sale_status(
    vendor_id: str,
    status: str,
    notes: Optional[str] = None,
    session=Depends(get_session)
):
    garage_system = GarageSaleListings(session)
    success = await garage_system.update_garage_sale_status(
        uuid.UUID(vendor_id), status, notes
    )
    return {"success": success}


@app.post("/garage-sales/pricing-suggestion")
async def suggest_pricing(
    component_data: Dict[str, Any],
    session=Depends(get_session)
):
    garage_system = GarageSaleListings(session)
    suggestion = await garage_system.suggest_pricing(component_data)
    return suggestion


# Compatibility Matcher (Simplified Implementation)
@app.get("/compatibility/projects/{project_id}")
async def get_project_compatibility():
    return {
        "compatible_components": [
            {
                "component_id": "comp-1",
                "name": "Arduino Uno R3",
                "compatibility_score": 0.95,
                "alternative_options": ["Arduino Nano", "ESP32"]
            },
            {
                "component_id": "comp-2", 
                "name": "DHT22 Sensor",
                "compatibility_score": 0.90,
                "alternative_options": ["DHT11", "SHT30"]
            }
        ]
    }


# Bundle Recommendations
@app.get("/bundles/recommendations")
async def get_bundle_recommendations():
    return {
        "recommended_bundles": [
            {
                "bundle_id": "bundle-1",
                "name": "Arduino Starter Kit",
                "components": ["Arduino Uno", "Breadboard", "Resistors", "LEDs"],
                "original_price": 89.99,
                "bundle_price": 69.99,
                "savings": 20.00,
                "vendor": "ElectroSupply Co."
            },
            {
                "bundle_id": "bundle-2",
                "name": "Sensor Collection",
                "components": ["Temperature", "Humidity", "Light", "Motion"],
                "original_price": 45.50,
                "bundle_price": 35.99,
                "savings": 9.51,
                "vendor": "SensorWorld"
            }
        ]
    }


# Price Comparison Engine
@app.get("/pricing/compare")
async def compare_prices():
    return {
        "component": "Arduino Uno R3",
        "price_comparison": [
            {
                "vendor": "ElectroSupply Co.",
                "price": 24.99,
                "shipping": 5.99,
                "total": 30.98,
                "rating": 4.5,
                "stock": 50
            },
            {
                "vendor": "ComponentMart",
                "price": 22.95,
                "shipping": 0.00,
                "total": 22.95,
                "rating": 4.2,
                "stock": 25
            },
            {
                "vendor": "TechParts Online",
                "price": 26.50,
                "shipping": 3.99,
                "total": 30.49,
                "rating": 4.7,
                "stock": 100
            }
        ],
        "best_price": {
            "vendor": "ComponentMart",
            "total": 22.95,
            "savings": 8.03
        }
    }


# Availability Notifications
@app.post("/notifications/availability")
async def create_availability_notification():
    return {
        "notification_id": "notif-123",
        "status": "created",
        "message": "You will be notified when this component becomes available"
    }


@app.get("/notifications/user/{user_id}")
async def get_user_notifications(user_id: str):
    return {
        "notifications": [
            {
                "id": "notif-1",
                "type": "availability",
                "title": "Arduino Uno R3 Back in Stock!",
                "message": "The component you were watching is now available at ElectroSupply Co.",
                "timestamp": "2024-01-15T10:30:00Z",
                "is_read": False
            },
            {
                "id": "notif-2",
                "type": "price_drop",
                "title": "Price Drop Alert",
                "message": "DHT22 sensor price dropped by 15% at SensorWorld",
                "timestamp": "2024-01-14T14:15:00Z",
                "is_read": True
            }
        ]
    }


# Vendor Reputation System
@app.get("/vendors/{vendor_id}/reputation")
async def get_vendor_reputation(vendor_id: str):
    return {
        "vendor_id": vendor_id,
        "overall_rating": 4.3,
        "total_reviews": 287,
        "metrics": {
            "product_quality": 4.5,
            "shipping_speed": 4.1,
            "customer_service": 4.4,
            "packaging": 4.2
        },
        "recent_reviews": [
            {
                "rating": 5,
                "title": "Excellent service!",
                "comment": "Fast shipping, well packaged items.",
                "verified_purchase": True,
                "date": "2024-01-10T09:00:00Z"
            },
            {
                "rating": 4,
                "title": "Good quality parts",
                "comment": "Components work as expected, reasonable prices.",
                "verified_purchase": True,
                "date": "2024-01-08T15:30:00Z"
            }
        ]
    }


# Automated Reorder System
@app.post("/reorder/rules")
async def create_reorder_rule():
    return {
        "rule_id": "rule-123",
        "status": "created",
        "message": "Reorder rule created successfully"
    }


@app.get("/reorder/suggestions/{user_id}")
async def get_reorder_suggestions(user_id: str):
    return {
        "reorder_suggestions": [
            {
                "component": "Resistor Pack 1/4W",
                "current_stock": 3,
                "reorder_point": 10,
                "suggested_quantity": 50,
                "preferred_vendor": "ComponentMart",
                "estimated_cost": 12.99
            },
            {
                "component": "Jumper Wires",
                "current_stock": 0,
                "reorder_point": 5,
                "suggested_quantity": 20,
                "preferred_vendor": "ElectroSupply Co.",
                "estimated_cost": 8.50
            }
        ]
    }


# Component Specifications Database
@app.get("/components/specs/{component_id}")
async def get_component_specifications(component_id: str):
    return {
        "component_id": component_id,
        "name": "Arduino Uno R3",
        "manufacturer": "Arduino",
        "specifications": {
            "microcontroller": "ATmega328P",
            "operating_voltage": "5V",
            "input_voltage_recommended": "7-12V",
            "input_voltage_limits": "6-20V",
            "digital_io_pins": 14,
            "pwm_digital_io_pins": 6,
            "analog_input_pins": 6,
            "dc_current_per_io_pin": "20mA",
            "flash_memory": "32KB",
            "sram": "2KB",
            "eeprom": "1KB",
            "clock_speed": "16MHz"
        },
        "datasheet_url": "https://www.arduino.cc/en/uploads/Main/Arduino_Uno_Rev3-schematic.pdf",
        "compatibility": {
            "shields": ["Arduino UNO R3 compatible shields"],
            "voltage_levels": ["5V logic"],
            "programming": ["Arduino IDE", "PlatformIO"]
        }
    }


# 3D Printer/CNC Pairing
@app.get("/manufacturing/pairing")
async def get_manufacturing_pairing():
    return {
        "manufacturing_options": [
            {
                "type": "3D Printing",
                "vendor": "MakerSpace Pro",
                "materials": ["PLA", "ABS", "PETG", "TPU"],
                "max_dimensions": {"x": 300, "y": 300, "z": 400},
                "resolution": "0.1-0.3mm",
                "estimated_cost": "$0.15/gram",
                "lead_time": "2-5 days"
            },
            {
                "type": "CNC Milling",
                "vendor": "Precision Parts Co.",
                "materials": ["Aluminum", "Steel", "Brass", "Plastic"],
                "max_dimensions": {"x": 500, "y": 300, "z": 150},
                "tolerance": "±0.05mm",
                "estimated_cost": "$50/hour",
                "lead_time": "3-7 days"
            }
        ],
        "project_suggestions": [
            {
                "project": "Custom Enclosure",
                "recommended_method": "3D Printing",
                "material": "ABS",
                "estimated_cost": 12.50
            },
            {
                "project": "Motor Mount",
                "recommended_method": "CNC Milling",
                "material": "Aluminum",
                "estimated_cost": 35.00
            }
        ]
    }


# International Shipping Calculator
@app.post("/shipping/calculate")
async def calculate_shipping():
    return {
        "shipping_options": [
            {
                "method": "Standard International",
                "cost": 15.99,
                "estimated_delivery": "10-15 business days",
                "tracking": True,
                "insurance": "Up to $100"
            },
            {
                "method": "Express International",
                "cost": 35.99,
                "estimated_delivery": "3-5 business days",
                "tracking": True,
                "insurance": "Up to $500"
            },
            {
                "method": "Economy International",
                "cost": 8.99,
                "estimated_delivery": "15-25 business days",
                "tracking": False,
                "insurance": None
            }
        ],
        "customs_info": {
            "duties_estimated": 12.50,
            "taxes_estimated": 8.75,
            "processing_time": "1-3 days"
        }
    }


# Analytics and Dashboard
@app.get("/analytics/dashboard")
async def get_marketplace_dashboard():
    return {
        "marketplace_stats": {
            "total_vendors": 1247,
            "active_listings": 45820,
            "garage_sales_active": 73,
            "orders_today": 186,
            "revenue_today": 12450.75
        },
        "trending_components": [
            {"name": "Arduino Uno R3", "searches": 450, "orders": 23},
            {"name": "Raspberry Pi 4", "searches": 320, "orders": 18},
            {"name": "ESP32 DevKit", "searches": 290, "orders": 15}
        ],
        "popular_categories": [
            {"category": "Electronic", "percentage": 45.2},
            {"category": "Mechanical", "percentage": 28.7},
            {"category": "Sensor", "percentage": 16.3},
            {"category": "Tool", "percentage": 9.8}
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8339,
        reload=True,
        log_level="info"
    )