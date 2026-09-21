"""
Local Pickup Options System
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, time
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import geopy.distance
from geopy.geocoders import Nominatim

from ..database import Vendor, InventoryItem, Order, OrderStatus, ShippingMethod


class LocalPickupSystem:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.geocoder = Nominatim(user_agent="parts-market")
        
        # Pickup time slots configuration
        self.default_time_slots = [
            {"start": "09:00", "end": "12:00", "label": "Morning"},
            {"start": "12:00", "end": "17:00", "label": "Afternoon"},
            {"start": "17:00", "end": "20:00", "label": "Evening"}
        ]
    
    async def setup_pickup_location(
        self,
        vendor_id: uuid.UUID,
        location_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Setup or update pickup location for a vendor"""
        
        # Geocode the address
        address_string = self._format_address(location_data["address"])
        coordinates = await self._geocode_address(address_string)
        
        if not coordinates:
            raise ValueError("Could not geocode the provided address")
        
        pickup_location = {
            "id": str(uuid.uuid4()),
            "name": location_data.get("name", "Main Pickup Location"),
            "address": location_data["address"],
            "coordinates": coordinates,
            "contact_info": location_data.get("contact_info", {}),
            "hours": location_data.get("hours", {
                "monday": {"open": "09:00", "close": "17:00"},
                "tuesday": {"open": "09:00", "close": "17:00"},
                "wednesday": {"open": "09:00", "close": "17:00"},
                "thursday": {"open": "09:00", "close": "17:00"},
                "friday": {"open": "09:00", "close": "17:00"},
                "saturday": {"open": "10:00", "close": "15:00"},
                "sunday": {"closed": True}
            }),
            "instructions": location_data.get("instructions", ""),
            "time_slots": location_data.get("time_slots", self.default_time_slots),
            "max_items_per_slot": location_data.get("max_items_per_slot", 10),
            "advance_notice_hours": location_data.get("advance_notice_hours", 2),
            "is_active": location_data.get("is_active", True)
        }
        
        # Update vendor's pickup locations
        vendor_result = await self.session.execute(
            select(Vendor).where(Vendor.id == vendor_id)
        )
        vendor = vendor_result.scalar_one_or_none()
        
        if not vendor:
            raise ValueError("Vendor not found")
        
        pickup_locations = vendor.pickup_locations or []
        
        # Check if updating existing location
        location_id = location_data.get("id")
        if location_id:
            for i, loc in enumerate(pickup_locations):
                if loc.get("id") == location_id:
                    pickup_locations[i] = pickup_location
                    break
        else:
            pickup_locations.append(pickup_location)
        
        # Update vendor
        from sqlalchemy import update
        await self.session.execute(
            update(Vendor)
            .where(Vendor.id == vendor_id)
            .values(pickup_locations=pickup_locations)
        )
        await self.session.commit()
        
        return pickup_location
    
    async def find_nearby_vendors(
        self,
        location: Dict[str, Any],
        radius_km: float = 50,
        component_ids: Optional[List[uuid.UUID]] = None
    ) -> List[Dict[str, Any]]:
        """Find vendors with pickup locations near a given location"""
        
        # Geocode user location
        user_address = self._format_address(location)
        user_coords = await self._geocode_address(user_address)
        
        if not user_coords:
            raise ValueError("Could not geocode the provided location")
        
        # Get vendors with pickup locations
        query = select(Vendor).where(
            and_(
                Vendor.pickup_locations.isnot(None),
                Vendor.is_active == True
            )
        )
        
        if component_ids:
            # Filter vendors that have the requested components
            query = query.join(InventoryItem).where(
                and_(
                    InventoryItem.component_id.in_(component_ids),
                    InventoryItem.quantity_available > 0,
                    InventoryItem.is_active == True
                )
            ).distinct()
        
        result = await self.session.execute(query)
        vendors = result.scalars().all()
        
        nearby_vendors = []
        
        for vendor in vendors:
            for pickup_location in vendor.pickup_locations:
                if not pickup_location.get("is_active", True):
                    continue
                
                pickup_coords = pickup_location.get("coordinates")
                if not pickup_coords:
                    continue
                
                # Calculate distance
                distance = geopy.distance.distance(
                    user_coords, 
                    (pickup_coords["lat"], pickup_coords["lng"])
                ).kilometers
                
                if distance <= radius_km:
                    vendor_data = {
                        "vendor_id": str(vendor.id),
                        "vendor_name": vendor.name,
                        "vendor_type": vendor.vendor_type.value,
                        "is_verified": vendor.is_verified,
                        "pickup_location": {
                            **pickup_location,
                            "distance_km": round(distance, 2)
                        }
                    }
                    
                    # Add available components if filtering by components
                    if component_ids:
                        available_components = await self._get_vendor_components(
                            vendor.id, component_ids
                        )
                        vendor_data["available_components"] = available_components
                    
                    nearby_vendors.append(vendor_data)
        
        # Sort by distance
        nearby_vendors.sort(key=lambda x: x["pickup_location"]["distance_km"])
        
        return nearby_vendors
    
    async def get_available_pickup_slots(
        self,
        vendor_id: uuid.UUID,
        pickup_location_id: str,
        date: datetime,
        duration_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get available pickup time slots for a location"""
        
        vendor_result = await self.session.execute(
            select(Vendor).where(Vendor.id == vendor_id)
        )
        vendor = vendor_result.scalar_one_or_none()
        
        if not vendor:
            raise ValueError("Vendor not found")
        
        # Find pickup location
        pickup_location = None
        for loc in vendor.pickup_locations or []:
            if loc.get("id") == pickup_location_id:
                pickup_location = loc
                break
        
        if not pickup_location:
            raise ValueError("Pickup location not found")
        
        available_slots = []
        
        for i in range(duration_days):
            check_date = date + timedelta(days=i)
            day_name = check_date.strftime("%A").lower()
            
            # Check if location is open on this day
            day_hours = pickup_location["hours"].get(day_name, {})
            if day_hours.get("closed", False):
                continue
            
            # Get existing bookings for this day
            existing_bookings = await self._get_pickup_bookings(
                vendor_id, pickup_location_id, check_date
            )
            
            # Generate available slots
            for slot in pickup_location.get("time_slots", self.default_time_slots):
                slot_datetime = datetime.combine(
                    check_date.date(),
                    datetime.strptime(slot["start"], "%H:%M").time()
                )
                
                # Check if slot is in the future
                advance_notice = timedelta(
                    hours=pickup_location.get("advance_notice_hours", 2)
                )
                if slot_datetime < datetime.utcnow() + advance_notice:
                    continue
                
                # Check availability
                max_items = pickup_location.get("max_items_per_slot", 10)
                booked_items = existing_bookings.get(slot["start"], 0)
                available_slots.append({
                    "date": check_date.isoformat(),
                    "time_slot": slot,
                    "available_capacity": max_items - booked_items,
                    "is_available": booked_items < max_items,
                    "datetime": slot_datetime.isoformat()
                })
        
        return available_slots
    
    async def schedule_pickup(
        self,
        order_id: uuid.UUID,
        pickup_location_id: str,
        pickup_datetime: datetime,
        special_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Schedule a pickup for an order"""
        
        # Get order details
        order_result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        
        if not order:
            raise ValueError("Order not found")
        
        # Get vendor and pickup location
        vendor_result = await self.session.execute(
            select(Vendor).where(Vendor.id == order.vendor_id)
        )
        vendor = vendor_result.scalar_one()
        
        pickup_location = None
        for loc in vendor.pickup_locations or []:
            if loc.get("id") == pickup_location_id:
                pickup_location = loc
                break
        
        if not pickup_location:
            raise ValueError("Pickup location not found")
        
        # Check if slot is still available
        slots = await self.get_available_pickup_slots(
            order.vendor_id, pickup_location_id, pickup_datetime, 1
        )
        
        available_slot = None
        for slot in slots:
            slot_dt = datetime.fromisoformat(slot["datetime"])
            if abs((slot_dt - pickup_datetime).total_seconds()) < 3600:  # Within 1 hour
                available_slot = slot
                break
        
        if not available_slot or not available_slot["is_available"]:
            raise ValueError("Selected pickup slot is no longer available")
        
        # Update order with pickup information
        pickup_info = {
            "pickup_location_id": pickup_location_id,
            "pickup_location": pickup_location,
            "scheduled_datetime": pickup_datetime.isoformat(),
            "special_instructions": special_instructions,
            "confirmation_code": self._generate_confirmation_code()
        }
        
        from sqlalchemy import update
        await self.session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(
                shipping_method=ShippingMethod.LOCAL_PICKUP,
                shipping_address=pickup_info,
                status=OrderStatus.CONFIRMED
            )
        )
        await self.session.commit()
        
        return {
            "order_id": str(order_id),
            "pickup_info": pickup_info,
            "vendor_contact": pickup_location.get("contact_info", {}),
            "estimated_preparation_time": "2-4 hours"
        }
    
    async def get_pickup_orders(
        self,
        vendor_id: uuid.UUID,
        pickup_location_id: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get pickup orders for a vendor location"""
        
        query = (
            select(Order)
            .options(selectinload(Order.buyer))
            .where(
                and_(
                    Order.vendor_id == vendor_id,
                    Order.shipping_method == ShippingMethod.LOCAL_PICKUP
                )
            )
        )
        
        if date:
            # Filter by pickup date
            start_date = datetime.combine(date.date(), time.min)
            end_date = datetime.combine(date.date(), time.max)
            # This is a simplified filter - in practice you'd check the pickup datetime in shipping_address JSON
        
        result = await self.session.execute(query)
        orders = result.scalars().all()
        
        pickup_orders = []
        for order in orders:
            pickup_info = order.shipping_address or {}
            
            # Filter by pickup location if specified
            if pickup_location_id and pickup_info.get("pickup_location_id") != pickup_location_id:
                continue
            
            pickup_orders.append({
                "order_id": str(order.id),
                "order_number": order.order_number,
                "buyer": {
                    "name": f"{order.buyer.first_name} {order.buyer.last_name}",
                    "email": order.buyer.email,
                    "phone": order.buyer.phone
                },
                "status": order.status.value,
                "total_amount": float(order.total_amount),
                "pickup_info": pickup_info,
                "created_at": order.created_at.isoformat()
            })
        
        return pickup_orders
    
    async def confirm_pickup_completion(
        self,
        order_id: uuid.UUID,
        completion_notes: Optional[str] = None
    ) -> bool:
        """Mark a pickup as completed"""
        
        from sqlalchemy import update
        await self.session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(
                status=OrderStatus.DELIVERED,
                notes=completion_notes,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
        
        return True
    
    async def get_pickup_analytics(
        self,
        vendor_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get pickup analytics for a vendor"""
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get pickup order counts
        query = (
            select(
                func.count(Order.id).label("total_pickups"),
                func.count(func.case(
                    (Order.status == OrderStatus.DELIVERED, Order.id)
                )).label("completed_pickups"),
                func.avg(Order.total_amount).label("avg_order_value")
            )
            .where(
                and_(
                    Order.vendor_id == vendor_id,
                    Order.shipping_method == ShippingMethod.LOCAL_PICKUP,
                    Order.created_at >= since_date
                )
            )
        )
        
        stats = (await self.session.execute(query)).first()
        
        # Get popular pickup locations
        location_query = (
            select(func.count(Order.id).label("pickup_count"))
            .where(
                and_(
                    Order.vendor_id == vendor_id,
                    Order.shipping_method == ShippingMethod.LOCAL_PICKUP,
                    Order.created_at >= since_date
                )
            )
        )
        
        return {
            "period_days": days,
            "total_pickup_orders": stats.total_pickups or 0,
            "completed_pickups": stats.completed_pickups or 0,
            "completion_rate": (stats.completed_pickups or 0) / max(stats.total_pickups or 1, 1) * 100,
            "average_order_value": float(stats.avg_order_value or 0)
        }
    
    def _format_address(self, address: Dict[str, str]) -> str:
        """Format address dictionary into a string"""
        parts = []
        
        if address.get("street"):
            parts.append(address["street"])
        if address.get("city"):
            parts.append(address["city"])
        if address.get("state"):
            parts.append(address["state"])
        if address.get("zip_code"):
            parts.append(address["zip_code"])
        if address.get("country"):
            parts.append(address["country"])
        
        return ", ".join(parts)
    
    async def _geocode_address(self, address: str) -> Optional[Dict[str, float]]:
        """Geocode an address to coordinates"""
        
        try:
            location = self.geocoder.geocode(address)
            if location:
                return {
                    "lat": location.latitude,
                    "lng": location.longitude
                }
        except Exception as e:
            print(f"Geocoding error: {str(e)}")
        
        return None
    
    async def _get_pickup_bookings(
        self,
        vendor_id: uuid.UUID,
        pickup_location_id: str,
        date: datetime
    ) -> Dict[str, int]:
        """Get existing pickup bookings for a specific date"""
        
        # This is a simplified implementation
        # In practice, you'd track pickup bookings in a separate table
        
        # Query orders with pickup scheduled for this date and location
        query = (
            select(func.count(Order.id))
            .where(
                and_(
                    Order.vendor_id == vendor_id,
                    Order.shipping_method == ShippingMethod.LOCAL_PICKUP,
                    Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
                )
            )
        )
        
        result = (await self.session.execute(query)).scalar()
        
        # Simplified: assume even distribution across time slots
        return {"09:00": result // 3, "12:00": result // 3, "17:00": result // 3}
    
    async def _get_vendor_components(
        self,
        vendor_id: uuid.UUID,
        component_ids: List[uuid.UUID]
    ) -> List[Dict[str, Any]]:
        """Get available components for a vendor"""
        
        query = (
            select(InventoryItem)
            .join(InventoryItem.component)
            .where(
                and_(
                    InventoryItem.vendor_id == vendor_id,
                    InventoryItem.component_id.in_(component_ids),
                    InventoryItem.quantity_available > 0,
                    InventoryItem.is_active == True
                )
            )
        )
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [
            {
                "component_id": str(item.component_id),
                "inventory_item_id": str(item.id),
                "quantity_available": item.quantity_available,
                "unit_price": float(item.unit_price)
            }
            for item in items
        ]
    
    def _generate_confirmation_code(self) -> str:
        """Generate a pickup confirmation code"""
        import random
        import string
        
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))