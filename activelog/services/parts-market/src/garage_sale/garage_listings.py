"""
Garage Sale Component Listings System
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, time
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
import geopy.distance
from geopy.geocoders import Nominatim

from ..database import (
    Vendor, Component, InventoryItem, ListingType, VendorType,
    ComponentCategory, User, Order
)


class GarageSaleListings:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.geocoder = Nominatim(user_agent="parts-market-garage")
    
    async def create_garage_sale_listing(
        self,
        seller_id: uuid.UUID,
        sale_info: Dict[str, Any],
        components: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a new garage sale listing with multiple components"""
        
        # Create or get garage sale vendor
        vendor_id = await self._create_garage_sale_vendor(seller_id, sale_info)
        
        # Process each component in the sale
        listing_items = []
        total_estimated_value = 0
        
        for comp_data in components:
            # Create or find component
            component_id = await self._create_or_find_component(comp_data)
            
            # Create inventory item for garage sale
            inventory_item_id = await self._create_garage_sale_inventory_item(
                vendor_id, component_id, comp_data, sale_info
            )
            
            listing_items.append({
                "component_id": str(component_id),
                "inventory_item_id": str(inventory_item_id),
                "asking_price": comp_data["asking_price"],
                "estimated_retail": comp_data.get("estimated_retail"),
                "condition": comp_data.get("condition", "used")
            })
            
            total_estimated_value += comp_data.get("estimated_retail", comp_data["asking_price"])
        
        # Calculate sale-wide metrics
        total_asking = sum(item["asking_price"] for item in listing_items)
        discount_percentage = ((total_estimated_value - total_asking) / 
                             max(total_estimated_value, 1)) * 100
        
        return {
            "vendor_id": str(vendor_id),
            "sale_id": sale_info["sale_id"],
            "listing_items": listing_items,
            "total_items": len(listing_items),
            "total_asking_price": total_asking,
            "total_estimated_value": total_estimated_value,
            "discount_percentage": round(discount_percentage, 1),
            "sale_dates": sale_info["sale_dates"],
            "location": sale_info["location"],
            "status": "active"
        }
    
    async def search_garage_sales(
        self,
        location: Optional[Dict[str, Any]] = None,
        radius_km: float = 25,
        component_categories: Optional[List[ComponentCategory]] = None,
        max_price: Optional[float] = None,
        sale_dates: Optional[Dict[str, datetime]] = None,
        condition: Optional[str] = None,
        sort_by: str = "distance",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for garage sale listings"""
        
        # Get user coordinates for distance calculation
        user_coords = None
        if location:
            address = self._format_address(location)
            user_coords = await self._geocode_address(address)
        
        # Build query for garage sale items
        query = (
            select(InventoryItem)
            .join(Component)
            .join(Vendor)
            .options(
                selectinload(InventoryItem.component),
                selectinload(InventoryItem.vendor)
            )
            .where(
                and_(
                    InventoryItem.listing_type == ListingType.GARAGE_SALE,
                    InventoryItem.is_active == True,
                    Vendor.vendor_type == VendorType.GARAGE_SALE,
                    Vendor.is_active == True
                )
            )
        )
        
        # Apply filters
        if component_categories:
            query = query.where(Component.category.in_(component_categories))
        
        if max_price:
            query = query.where(InventoryItem.unit_price <= max_price)
        
        if condition:
            query = query.where(InventoryItem.condition == condition)
        
        # Execute query
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        # Group by garage sale and calculate distances
        garage_sales = {}
        
        for item in items:
            vendor_id = str(item.vendor_id)
            sale_info = item.garage_sale_info or {}
            
            if vendor_id not in garage_sales:
                # Calculate distance if user location provided
                distance_km = None
                if user_coords and sale_info.get("coordinates"):
                    sale_coords = sale_info["coordinates"]
                    distance_km = geopy.distance.distance(
                        user_coords, 
                        (sale_coords["lat"], sale_coords["lng"])
                    ).kilometers
                
                # Filter by distance
                if location and distance_km and distance_km > radius_km:
                    continue
                
                # Check sale dates
                if sale_dates:
                    sale_start = sale_info.get("start_date")
                    sale_end = sale_info.get("end_date")
                    
                    if sale_start and sale_end:
                        sale_start_dt = datetime.fromisoformat(sale_start)
                        sale_end_dt = datetime.fromisoformat(sale_end)
                        
                        # Filter by date range
                        if sale_dates.get("start") and sale_end_dt < sale_dates["start"]:
                            continue
                        if sale_dates.get("end") and sale_start_dt > sale_dates["end"]:
                            continue
                
                garage_sales[vendor_id] = {
                    "vendor_id": vendor_id,
                    "vendor_name": item.vendor.name,
                    "sale_info": sale_info,
                    "distance_km": distance_km,
                    "items": [],
                    "total_items": 0,
                    "price_range": {"min": float('inf'), "max": 0},
                    "categories": set()
                }
            
            # Add item to garage sale
            garage_sale = garage_sales[vendor_id]
            item_price = float(item.unit_price)
            
            garage_sale["items"].append({
                "id": str(item.id),
                "component": {
                    "name": item.component.name,
                    "category": item.component.category.value,
                    "component_type": item.component.component_type.value,
                    "manufacturer": item.component.manufacturer,
                    "description": item.component.description
                },
                "price": item_price,
                "condition": item.condition,
                "quantity": item.quantity_available,
                "estimated_retail": sale_info.get("estimated_retail")
            })
            
            garage_sale["total_items"] += 1
            garage_sale["price_range"]["min"] = min(garage_sale["price_range"]["min"], item_price)
            garage_sale["price_range"]["max"] = max(garage_sale["price_range"]["max"], item_price)
            garage_sale["categories"].add(item.component.category.value)
        
        # Convert to list and clean up
        garage_sale_list = []
        for sale in garage_sales.values():
            if sale["price_range"]["min"] == float('inf'):
                sale["price_range"]["min"] = 0
            sale["categories"] = list(sale["categories"])
            garage_sale_list.append(sale)
        
        # Sort results
        if sort_by == "distance" and user_coords:
            garage_sale_list.sort(key=lambda x: x["distance_km"] or float('inf'))
        elif sort_by == "price":
            garage_sale_list.sort(key=lambda x: x["price_range"]["min"])
        elif sort_by == "items":
            garage_sale_list.sort(key=lambda x: x["total_items"], reverse=True)
        elif sort_by == "date":
            garage_sale_list.sort(
                key=lambda x: x["sale_info"].get("start_date", ""),
                reverse=True
            )
        
        return garage_sale_list[:limit]
    
    async def get_garage_sale_details(
        self,
        vendor_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get detailed information about a garage sale"""
        
        # Get vendor and all items
        vendor_query = (
            select(Vendor)
            .options(selectinload(Vendor.inventory_items))
            .where(Vendor.id == vendor_id)
        )
        
        vendor_result = await self.session.execute(vendor_query)
        vendor = vendor_result.scalar_one_or_none()
        
        if not vendor or vendor.vendor_type != VendorType.GARAGE_SALE:
            raise ValueError("Garage sale not found")
        
        # Get all items with components
        items_query = (
            select(InventoryItem)
            .join(Component)
            .options(selectinload(InventoryItem.component))
            .where(
                and_(
                    InventoryItem.vendor_id == vendor_id,
                    InventoryItem.listing_type == ListingType.GARAGE_SALE,
                    InventoryItem.is_active == True
                )
            )
        )
        
        items_result = await self.session.execute(items_query)
        items = items_result.scalars().all()
        
        # Process items by category
        categories = {}
        total_value = 0
        total_asking = 0
        
        for item in items:
            category = item.component.category.value
            if category not in categories:
                categories[category] = {
                    "items": [],
                    "count": 0,
                    "total_asking": 0,
                    "avg_discount": 0
                }
            
            item_asking = float(item.unit_price)
            item_retail = item.garage_sale_info.get("estimated_retail", item_asking) if item.garage_sale_info else item_asking
            
            categories[category]["items"].append({
                "id": str(item.id),
                "component_name": item.component.name,
                "part_number": item.component.part_number,
                "manufacturer": item.component.manufacturer,
                "description": item.component.description,
                "asking_price": item_asking,
                "estimated_retail": item_retail,
                "condition": item.condition,
                "quantity": item.quantity_available,
                "discount_percent": ((item_retail - item_asking) / max(item_retail, 1)) * 100
            })
            
            categories[category]["count"] += 1
            categories[category]["total_asking"] += item_asking
            
            total_value += item_retail
            total_asking += item_asking
        
        # Calculate category averages
        for category_data in categories.values():
            if category_data["items"]:
                category_data["avg_discount"] = sum(
                    item["discount_percent"] for item in category_data["items"]
                ) / len(category_data["items"])
        
        # Get sale information from the first item (they should all be the same)
        sale_info = items[0].garage_sale_info if items else {}
        
        return {
            "vendor_id": str(vendor_id),
            "vendor_name": vendor.name,
            "sale_info": sale_info,
            "categories": categories,
            "summary": {
                "total_items": len(items),
                "total_asking_price": total_asking,
                "total_estimated_value": total_value,
                "overall_discount": ((total_value - total_asking) / max(total_value, 1)) * 100,
                "categories_count": len(categories)
            },
            "contact_info": vendor.contact_info,
            "created_at": vendor.created_at.isoformat()
        }
    
    async def update_garage_sale_status(
        self,
        vendor_id: uuid.UUID,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update garage sale status (active, paused, ended)"""
        
        is_active = status == "active"
        
        # Update all inventory items
        from sqlalchemy import update
        await self.session.execute(
            update(InventoryItem)
            .where(
                and_(
                    InventoryItem.vendor_id == vendor_id,
                    InventoryItem.listing_type == ListingType.GARAGE_SALE
                )
            )
            .values(is_active=is_active)
        )
        
        # Update vendor
        await self.session.execute(
            update(Vendor)
            .where(Vendor.id == vendor_id)
            .values(
                is_active=is_active,
                description=notes if notes else Vendor.description
            )
        )
        
        await self.session.commit()
        return True
    
    async def get_garage_sale_analytics(
        self,
        location: Optional[Dict[str, Any]] = None,
        radius_km: float = 50,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get analytics for garage sales in an area"""
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get user coordinates
        user_coords = None
        if location:
            address = self._format_address(location)
            user_coords = await self._geocode_address(address)
        
        # Get all garage sale vendors
        vendors_query = (
            select(Vendor)
            .where(
                and_(
                    Vendor.vendor_type == VendorType.GARAGE_SALE,
                    Vendor.created_at >= since_date
                )
            )
        )
        
        vendors_result = await self.session.execute(vendors_query)
        vendors = vendors_result.scalars().all()
        
        # Filter by location if provided
        if user_coords:
            nearby_vendors = []
            for vendor in vendors:
                # Get coordinates from pickup locations or contact info
                vendor_coords = None
                if vendor.pickup_locations:
                    vendor_coords = vendor.pickup_locations[0].get("coordinates")
                elif vendor.contact_info and vendor.contact_info.get("coordinates"):
                    vendor_coords = vendor.contact_info["coordinates"]
                
                if vendor_coords:
                    distance = geopy.distance.distance(
                        user_coords,
                        (vendor_coords["lat"], vendor_coords["lng"])
                    ).kilometers
                    
                    if distance <= radius_km:
                        nearby_vendors.append(vendor)
            
            vendors = nearby_vendors
        
        # Get items statistics
        items_query = (
            select(
                func.count(InventoryItem.id).label("total_items"),
                func.avg(InventoryItem.unit_price).label("avg_price"),
                func.sum(InventoryItem.unit_price * InventoryItem.quantity_available).label("total_value")
            )
            .join(Vendor)
            .where(
                and_(
                    Vendor.vendor_type == VendorType.GARAGE_SALE,
                    InventoryItem.listing_type == ListingType.GARAGE_SALE,
                    Vendor.id.in_([v.id for v in vendors])
                )
            )
        )
        
        items_stats = (await self.session.execute(items_query)).first()
        
        # Get category breakdown
        category_query = (
            select(
                Component.category,
                func.count(InventoryItem.id).label("item_count"),
                func.avg(InventoryItem.unit_price).label("avg_price")
            )
            .join(InventoryItem)
            .join(Vendor)
            .where(
                and_(
                    Vendor.vendor_type == VendorType.GARAGE_SALE,
                    InventoryItem.listing_type == ListingType.GARAGE_SALE,
                    Vendor.id.in_([v.id for v in vendors])
                )
            )
            .group_by(Component.category)
        )
        
        category_result = await self.session.execute(category_query)
        category_breakdown = [
            {
                "category": row.category.value,
                "item_count": row.item_count,
                "average_price": float(row.avg_price)
            }
            for row in category_result
        ]
        
        return {
            "area_summary": {
                "location": location,
                "radius_km": radius_km if location else None,
                "period_days": days
            },
            "garage_sales": {
                "total_sales": len(vendors),
                "active_sales": len([v for v in vendors if v.is_active]),
                "total_items": items_stats.total_items or 0,
                "average_item_price": float(items_stats.avg_price or 0),
                "total_value": float(items_stats.total_value or 0)
            },
            "category_breakdown": category_breakdown
        }
    
    async def suggest_pricing(
        self,
        component_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest pricing for a garage sale item based on market data"""
        
        # Find similar components
        search_terms = [
            component_data.get("name", ""),
            component_data.get("part_number", ""),
            component_data.get("manufacturer", "")
        ]
        
        similar_query = (
            select(InventoryItem)
            .join(Component)
            .where(
                and_(
                    or_(
                        *[Component.name.ilike(f"%{term}%") for term in search_terms if term]
                    ),
                    InventoryItem.is_active == True
                )
            )
        )
        
        result = await self.session.execute(similar_query)
        similar_items = result.scalars().all()
        
        if not similar_items:
            return {
                "suggested_price": None,
                "confidence": "low",
                "message": "No similar items found for price comparison"
            }
        
        # Calculate price statistics
        prices = [float(item.unit_price) for item in similar_items]
        garage_sale_prices = [
            float(item.unit_price) for item in similar_items 
            if item.listing_type == ListingType.GARAGE_SALE
        ]
        
        retail_prices = [p for p in prices if p not in garage_sale_prices]
        
        # Calculate suggestions
        retail_avg = sum(retail_prices) / len(retail_prices) if retail_prices else None
        garage_avg = sum(garage_sale_prices) / len(garage_sale_prices) if garage_sale_prices else None
        
        # Suggest 60-80% of retail price for garage sale
        if retail_avg:
            suggested_price = retail_avg * 0.7  # 70% of retail average
            confidence = "high" if len(retail_prices) >= 5 else "medium"
        elif garage_avg:
            suggested_price = garage_avg
            confidence = "medium"
        else:
            suggested_price = sum(prices) / len(prices)
            confidence = "low"
        
        return {
            "suggested_price": round(suggested_price, 2),
            "confidence": confidence,
            "market_data": {
                "similar_items_found": len(similar_items),
                "retail_average": round(retail_avg, 2) if retail_avg else None,
                "garage_sale_average": round(garage_avg, 2) if garage_avg else None,
                "price_range": {
                    "min": min(prices),
                    "max": max(prices)
                }
            }
        }
    
    async def _create_garage_sale_vendor(
        self,
        seller_id: uuid.UUID,
        sale_info: Dict[str, Any]
    ) -> uuid.UUID:
        """Create or update garage sale vendor"""
        
        # Check if user already has a garage sale vendor
        existing_vendor_query = (
            select(Vendor)
            .where(
                and_(
                    Vendor.owner_id == seller_id,
                    Vendor.vendor_type == VendorType.GARAGE_SALE
                )
            )
        )
        
        result = await self.session.execute(existing_vendor_query)
        existing_vendor = result.scalar_one_or_none()
        
        # Geocode sale location
        address = sale_info["location"]
        coordinates = await self._geocode_address(self._format_address(address))
        
        pickup_location = {
            "id": str(uuid.uuid4()),
            "name": "Garage Sale Location",
            "address": address,
            "coordinates": coordinates,
            "hours": sale_info.get("hours", {}),
            "instructions": sale_info.get("special_instructions", ""),
            "is_active": True
        }
        
        vendor_data = {
            "name": f"Garage Sale - {sale_info['title']}",
            "description": sale_info.get("description", ""),
            "contact_info": sale_info.get("contact_info", {}),
            "pickup_locations": [pickup_location],
            "is_active": True
        }
        
        if existing_vendor:
            # Update existing vendor
            from sqlalchemy import update
            await self.session.execute(
                update(Vendor)
                .where(Vendor.id == existing_vendor.id)
                .values(**vendor_data)
            )
            vendor_id = existing_vendor.id
        else:
            # Create new vendor
            vendor = Vendor(
                owner_id=seller_id,
                vendor_type=VendorType.GARAGE_SALE,
                **vendor_data
            )
            
            self.session.add(vendor)
            await self.session.commit()
            await self.session.refresh(vendor)
            vendor_id = vendor.id
        
        await self.session.commit()
        return vendor_id
    
    async def _create_or_find_component(
        self,
        comp_data: Dict[str, Any]
    ) -> uuid.UUID:
        """Create component if it doesn't exist"""
        
        # Try to find existing component
        search_query = select(Component).where(
            and_(
                Component.name == comp_data["name"],
                Component.part_number == comp_data.get("part_number"),
                Component.manufacturer == comp_data.get("manufacturer")
            )
        )
        
        result = await self.session.execute(search_query)
        existing_component = result.scalar_one_or_none()
        
        if existing_component:
            return existing_component.id
        
        # Create new component
        component = Component(
            name=comp_data["name"],
            part_number=comp_data.get("part_number"),
            manufacturer=comp_data.get("manufacturer"),
            category=ComponentCategory(comp_data.get("category", "electronic")),
            component_type=comp_data.get("component_type", "resistor"),
            description=comp_data.get("description"),
            specifications=comp_data.get("specifications", {}),
            image_urls=comp_data.get("image_urls", [])
        )
        
        self.session.add(component)
        await self.session.commit()
        await self.session.refresh(component)
        
        return component.id
    
    async def _create_garage_sale_inventory_item(
        self,
        vendor_id: uuid.UUID,
        component_id: uuid.UUID,
        comp_data: Dict[str, Any],
        sale_info: Dict[str, Any]
    ) -> uuid.UUID:
        """Create inventory item for garage sale"""
        
        garage_sale_info = {
            "sale_id": sale_info["sale_id"],
            "start_date": sale_info["sale_dates"]["start"].isoformat(),
            "end_date": sale_info["sale_dates"]["end"].isoformat(),
            "location": sale_info["location"],
            "coordinates": await self._geocode_address(self._format_address(sale_info["location"])),
            "contact_info": sale_info.get("contact_info", {}),
            "estimated_retail": comp_data.get("estimated_retail"),
            "purchase_date": comp_data.get("purchase_date"),
            "reason_for_selling": comp_data.get("reason_for_selling")
        }
        
        inventory_item = InventoryItem(
            vendor_id=vendor_id,
            component_id=component_id,
            sku=f"GS-{sale_info['sale_id']}-{uuid.uuid4().hex[:8]}",
            quantity_available=comp_data.get("quantity", 1),
            unit_price=comp_data["asking_price"],
            condition=comp_data.get("condition", "used"),
            listing_type=ListingType.GARAGE_SALE,
            garage_sale_info=garage_sale_info
        )
        
        self.session.add(inventory_item)
        await self.session.commit()
        await self.session.refresh(inventory_item)
        
        return inventory_item.id
    
    def _format_address(self, address: Dict[str, str]) -> str:
        """Format address dictionary into string"""
        parts = []
        for key in ["street", "city", "state", "zip_code", "country"]:
            if address.get(key):
                parts.append(address[key])
        return ", ".join(parts)
    
    async def _geocode_address(self, address: str) -> Optional[Dict[str, float]]:
        """Geocode address to coordinates"""
        try:
            location = self.geocoder.geocode(address)
            if location:
                return {"lat": location.latitude, "lng": location.longitude}
        except Exception as e:
            print(f"Geocoding error: {str(e)}")
        return None