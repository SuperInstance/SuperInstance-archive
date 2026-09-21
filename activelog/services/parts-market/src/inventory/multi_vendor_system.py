"""
Multi-Vendor Inventory Management System
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from ..database import (
    Vendor, Component, InventoryItem, VendorType, ComponentCategory, 
    ComponentType, ListingType, User
)


class MultiVendorInventorySystem:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_vendor(
        self,
        owner_id: uuid.UUID,
        name: str,
        vendor_type: VendorType,
        description: Optional[str] = None,
        business_address: Optional[Dict[str, Any]] = None,
        contact_info: Optional[Dict[str, Any]] = None,
        shipping_locations: Optional[List[str]] = None,
        pickup_locations: Optional[List[Dict[str, Any]]] = None
    ) -> uuid.UUID:
        """Create a new vendor"""
        
        vendor = Vendor(
            name=name,
            vendor_type=vendor_type,
            description=description,
            business_address=business_address,
            contact_info=contact_info,
            shipping_locations=shipping_locations or [],
            pickup_locations=pickup_locations or [],
            owner_id=owner_id
        )
        
        self.session.add(vendor)
        await self.session.commit()
        await self.session.refresh(vendor)
        
        return vendor.id
    
    async def add_inventory_item(
        self,
        vendor_id: uuid.UUID,
        component_id: uuid.UUID,
        sku: str,
        quantity_available: int,
        unit_price: Decimal,
        condition: str = "new",
        bulk_pricing: Optional[Dict[int, Decimal]] = None,
        min_order_quantity: int = 1,
        max_order_quantity: Optional[int] = None,
        listing_type: ListingType = ListingType.REGULAR,
        garage_sale_info: Optional[Dict[str, Any]] = None,
        lead_time_days: Optional[int] = None
    ) -> uuid.UUID:
        """Add an inventory item for a vendor"""
        
        inventory_item = InventoryItem(
            vendor_id=vendor_id,
            component_id=component_id,
            sku=sku,
            quantity_available=quantity_available,
            unit_price=unit_price,
            bulk_pricing=bulk_pricing,
            min_order_quantity=min_order_quantity,
            max_order_quantity=max_order_quantity,
            condition=condition,
            listing_type=listing_type,
            garage_sale_info=garage_sale_info,
            lead_time_days=lead_time_days
        )
        
        self.session.add(inventory_item)
        await self.session.commit()
        await self.session.refresh(inventory_item)
        
        return inventory_item.id
    
    async def search_inventory(
        self,
        search_query: Optional[str] = None,
        component_category: Optional[ComponentCategory] = None,
        component_type: Optional[ComponentType] = None,
        vendor_types: Optional[List[VendorType]] = None,
        location: Optional[Dict[str, str]] = None,
        max_price: Optional[Decimal] = None,
        min_quantity: Optional[int] = None,
        condition: Optional[str] = None,
        listing_type: Optional[ListingType] = None,
        include_out_of_stock: bool = False,
        sort_by: str = "price",
        sort_order: str = "asc",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search inventory across all vendors with comprehensive filtering"""
        
        # Build base query with joins
        query = (
            select(InventoryItem)
            .join(Component)
            .join(Vendor)
            .options(
                selectinload(InventoryItem.component),
                selectinload(InventoryItem.vendor)
            )
            .where(InventoryItem.is_active == True)
            .where(Vendor.is_active == True)
        )
        
        # Apply filters
        if not include_out_of_stock:
            query = query.where(InventoryItem.quantity_available > 0)
        
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                or_(
                    Component.name.ilike(search_pattern),
                    Component.part_number.ilike(search_pattern),
                    Component.manufacturer.ilike(search_pattern),
                    Component.description.ilike(search_pattern),
                    InventoryItem.sku.ilike(search_pattern)
                )
            )
        
        if component_category:
            query = query.where(Component.category == component_category)
        
        if component_type:
            query = query.where(Component.component_type == component_type)
        
        if vendor_types:
            query = query.where(Vendor.vendor_type.in_(vendor_types))
        
        if max_price:
            query = query.where(InventoryItem.unit_price <= max_price)
        
        if min_quantity:
            query = query.where(InventoryItem.quantity_available >= min_quantity)
        
        if condition:
            query = query.where(InventoryItem.condition == condition)
        
        if listing_type:
            query = query.where(InventoryItem.listing_type == listing_type)
        
        # Location-based filtering
        if location:
            # Filter by vendors that ship to location or have local pickup
            country = location.get("country")
            region = location.get("region")
            
            if country:
                query = query.where(
                    or_(
                        Vendor.shipping_locations.contains([country]),
                        Vendor.pickup_locations.isnot(None)
                    )
                )
        
        # Apply sorting
        if sort_by == "price":
            order_col = InventoryItem.unit_price
        elif sort_by == "quantity":
            order_col = InventoryItem.quantity_available
        elif sort_by == "vendor":
            order_col = Vendor.name
        elif sort_by == "component":
            order_col = Component.name
        elif sort_by == "date":
            order_col = InventoryItem.created_at
        else:
            order_col = InventoryItem.unit_price
        
        if sort_order == "desc":
            query = query.order_by(desc(order_col))
        else:
            query = query.order_by(order_col)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = (await self.session.execute(count_query)).scalar()
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await self.session.execute(query)
        inventory_items = result.scalars().all()
        
        # Format results
        items = []
        for item in inventory_items:
            item_data = {
                "id": str(item.id),
                "sku": item.sku,
                "quantity_available": item.quantity_available,
                "unit_price": float(item.unit_price),
                "bulk_pricing": item.bulk_pricing,
                "condition": item.condition,
                "listing_type": item.listing_type.value,
                "min_order_quantity": item.min_order_quantity,
                "max_order_quantity": item.max_order_quantity,
                "lead_time_days": item.lead_time_days,
                "garage_sale_info": item.garage_sale_info,
                "component": {
                    "id": str(item.component.id),
                    "name": item.component.name,
                    "part_number": item.component.part_number,
                    "manufacturer": item.component.manufacturer,
                    "category": item.component.category.value,
                    "component_type": item.component.component_type.value,
                    "description": item.component.description,
                    "image_urls": item.component.image_urls
                },
                "vendor": {
                    "id": str(item.vendor.id),
                    "name": item.vendor.name,
                    "vendor_type": item.vendor.vendor_type.value,
                    "is_verified": item.vendor.is_verified,
                    "pickup_locations": item.vendor.pickup_locations,
                    "shipping_locations": item.vendor.shipping_locations
                }
            }
            items.append(item_data)
        
        return {
            "items": items,
            "total_count": total_count,
            "page_size": limit,
            "page": offset // limit + 1,
            "total_pages": (total_count + limit - 1) // limit
        }
    
    async def get_vendor_inventory(
        self,
        vendor_id: uuid.UUID,
        category: Optional[ComponentCategory] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all inventory for a specific vendor"""
        
        query = (
            select(InventoryItem)
            .join(Component)
            .options(selectinload(InventoryItem.component))
            .where(InventoryItem.vendor_id == vendor_id)
        )
        
        if not include_inactive:
            query = query.where(InventoryItem.is_active == True)
        
        if category:
            query = query.where(Component.category == category)
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [
            {
                "id": str(item.id),
                "sku": item.sku,
                "quantity_available": item.quantity_available,
                "unit_price": float(item.unit_price),
                "component": {
                    "name": item.component.name,
                    "part_number": item.component.part_number,
                    "category": item.component.category.value
                },
                "is_active": item.is_active,
                "created_at": item.created_at.isoformat()
            }
            for item in items
        ]
    
    async def update_inventory_quantity(
        self,
        inventory_item_id: uuid.UUID,
        new_quantity: int,
        operation: str = "set"
    ) -> bool:
        """Update inventory quantity (set, add, or subtract)"""
        
        item = await self._get_inventory_item(inventory_item_id)
        if not item:
            return False
        
        if operation == "set":
            new_quantity_value = new_quantity
        elif operation == "add":
            new_quantity_value = item.quantity_available + new_quantity
        elif operation == "subtract":
            new_quantity_value = max(0, item.quantity_available - new_quantity)
        else:
            return False
        
        await self.session.execute(
            update(InventoryItem)
            .where(InventoryItem.id == inventory_item_id)
            .values(
                quantity_available=new_quantity_value,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
        
        return True
    
    async def update_inventory_price(
        self,
        inventory_item_id: uuid.UUID,
        new_price: Decimal,
        bulk_pricing: Optional[Dict[int, Decimal]] = None
    ) -> bool:
        """Update inventory item price"""
        
        update_values = {
            "unit_price": new_price,
            "updated_at": datetime.utcnow()
        }
        
        if bulk_pricing is not None:
            update_values["bulk_pricing"] = bulk_pricing
        
        await self.session.execute(
            update(InventoryItem)
            .where(InventoryItem.id == inventory_item_id)
            .values(**update_values)
        )
        await self.session.commit()
        
        return True
    
    async def reserve_inventory(
        self,
        inventory_item_id: uuid.UUID,
        quantity: int,
        reservation_duration: int = 30  # minutes
    ) -> Optional[str]:
        """Reserve inventory for a specific duration"""
        
        item = await self._get_inventory_item(inventory_item_id)
        if not item or item.quantity_available < quantity:
            return None
        
        # Check if enough unreserved quantity is available
        unreserved = item.quantity_available - item.quantity_reserved
        if unreserved < quantity:
            return None
        
        # Create reservation
        await self.session.execute(
            update(InventoryItem)
            .where(InventoryItem.id == inventory_item_id)
            .values(quantity_reserved=item.quantity_reserved + quantity)
        )
        await self.session.commit()
        
        # Generate reservation ID
        reservation_id = str(uuid.uuid4())
        
        # In a production system, you'd store reservations in a separate table
        # with expiration times and cleanup tasks
        
        return reservation_id
    
    async def release_reservation(
        self,
        inventory_item_id: uuid.UUID,
        quantity: int,
        reservation_id: str
    ) -> bool:
        """Release a quantity reservation"""
        
        item = await self._get_inventory_item(inventory_item_id)
        if not item:
            return False
        
        new_reserved = max(0, item.quantity_reserved - quantity)
        
        await self.session.execute(
            update(InventoryItem)
            .where(InventoryItem.id == inventory_item_id)
            .values(quantity_reserved=new_reserved)
        )
        await self.session.commit()
        
        return True
    
    async def get_low_stock_items(
        self,
        vendor_id: Optional[uuid.UUID] = None,
        threshold: int = 5
    ) -> List[Dict[str, Any]]:
        """Get inventory items with low stock"""
        
        query = (
            select(InventoryItem)
            .join(Component)
            .options(
                selectinload(InventoryItem.component),
                selectinload(InventoryItem.vendor)
            )
            .where(InventoryItem.quantity_available <= threshold)
            .where(InventoryItem.is_active == True)
        )
        
        if vendor_id:
            query = query.where(InventoryItem.vendor_id == vendor_id)
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [
            {
                "id": str(item.id),
                "sku": item.sku,
                "quantity_available": item.quantity_available,
                "component_name": item.component.name,
                "vendor_name": item.vendor.name,
                "unit_price": float(item.unit_price)
            }
            for item in items
        ]
    
    async def get_vendor_performance_metrics(
        self,
        vendor_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for a vendor"""
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get basic inventory stats
        inventory_query = (
            select(
                func.count(InventoryItem.id).label("total_items"),
                func.sum(InventoryItem.quantity_available).label("total_quantity"),
                func.avg(InventoryItem.unit_price).label("avg_price")
            )
            .where(InventoryItem.vendor_id == vendor_id)
            .where(InventoryItem.is_active == True)
        )
        
        inventory_stats = (await self.session.execute(inventory_query)).first()
        
        # Get recent activity (new items added)
        recent_items_query = (
            select(func.count(InventoryItem.id))
            .where(InventoryItem.vendor_id == vendor_id)
            .where(InventoryItem.created_at >= since_date)
        )
        
        recent_items = (await self.session.execute(recent_items_query)).scalar()
        
        return {
            "vendor_id": str(vendor_id),
            "period_days": days,
            "total_active_items": inventory_stats.total_items or 0,
            "total_quantity_available": int(inventory_stats.total_quantity or 0),
            "average_price": float(inventory_stats.avg_price or 0),
            "items_added_recently": recent_items or 0
        }
    
    async def bulk_update_prices(
        self,
        vendor_id: uuid.UUID,
        price_adjustments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Bulk update prices for multiple inventory items"""
        
        updated_count = 0
        failed_items = []
        
        for adjustment in price_adjustments:
            try:
                item_id = uuid.UUID(adjustment["inventory_item_id"])
                new_price = Decimal(str(adjustment["new_price"]))
                
                # Verify item belongs to vendor
                item = await self._get_inventory_item(item_id)
                if not item or item.vendor_id != vendor_id:
                    failed_items.append({
                        "item_id": adjustment["inventory_item_id"],
                        "error": "Item not found or access denied"
                    })
                    continue
                
                await self.session.execute(
                    update(InventoryItem)
                    .where(InventoryItem.id == item_id)
                    .values(
                        unit_price=new_price,
                        updated_at=datetime.utcnow()
                    )
                )
                updated_count += 1
                
            except Exception as e:
                failed_items.append({
                    "item_id": adjustment.get("inventory_item_id", "unknown"),
                    "error": str(e)
                })
        
        await self.session.commit()
        
        return {
            "updated_count": updated_count,
            "failed_count": len(failed_items),
            "failed_items": failed_items
        }
    
    async def get_inventory_statistics(
        self,
        vendor_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get comprehensive inventory statistics"""
        
        base_query = select(InventoryItem).where(InventoryItem.is_active == True)
        
        if vendor_id:
            base_query = base_query.where(InventoryItem.vendor_id == vendor_id)
        
        # Total items and quantities
        stats_query = (
            select(
                func.count(InventoryItem.id).label("total_items"),
                func.sum(InventoryItem.quantity_available).label("total_quantity"),
                func.avg(InventoryItem.unit_price).label("avg_price"),
                func.min(InventoryItem.unit_price).label("min_price"),
                func.max(InventoryItem.unit_price).label("max_price")
            )
            .select_from(base_query.subquery())
        )
        
        stats = (await self.session.execute(stats_query)).first()
        
        # Category breakdown
        category_query = (
            select(
                Component.category,
                func.count(InventoryItem.id).label("item_count")
            )
            .join(Component)
            .where(InventoryItem.is_active == True)
        )
        
        if vendor_id:
            category_query = category_query.where(InventoryItem.vendor_id == vendor_id)
        
        category_query = category_query.group_by(Component.category)
        
        category_result = await self.session.execute(category_query)
        category_breakdown = [
            {"category": row.category.value, "item_count": row.item_count}
            for row in category_result
        ]
        
        # Stock status breakdown
        stock_status = {
            "in_stock": 0,
            "low_stock": 0,
            "out_of_stock": 0
        }
        
        stock_query = (
            select(
                func.sum(func.case(
                    (InventoryItem.quantity_available == 0, 1),
                    else_=0
                )).label("out_of_stock"),
                func.sum(func.case(
                    (and_(InventoryItem.quantity_available > 0, InventoryItem.quantity_available <= 5), 1),
                    else_=0
                )).label("low_stock"),
                func.sum(func.case(
                    (InventoryItem.quantity_available > 5, 1),
                    else_=0
                )).label("in_stock")
            )
            .select_from(base_query.subquery())
        )
        
        stock_result = (await self.session.execute(stock_query)).first()
        
        return {
            "total_items": stats.total_items or 0,
            "total_quantity_available": int(stats.total_quantity or 0),
            "average_price": float(stats.avg_price or 0),
            "price_range": {
                "min": float(stats.min_price or 0),
                "max": float(stats.max_price or 0)
            },
            "category_breakdown": category_breakdown,
            "stock_status": {
                "in_stock": int(stock_result.in_stock or 0),
                "low_stock": int(stock_result.low_stock or 0),
                "out_of_stock": int(stock_result.out_of_stock or 0)
            }
        }
    
    async def _get_inventory_item(self, item_id: uuid.UUID) -> Optional[InventoryItem]:
        """Get inventory item by ID"""
        result = await self.session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        return result.scalar_one_or_none()
    
    async def get_similar_components(
        self,
        component_id: uuid.UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar components based on specifications and category"""
        
        # Get the reference component
        ref_component_result = await self.session.execute(
            select(Component).where(Component.id == component_id)
        )
        ref_component = ref_component_result.scalar_one_or_none()
        
        if not ref_component:
            return []
        
        # Find components in same category and type
        query = (
            select(InventoryItem)
            .join(Component)
            .join(Vendor)
            .options(
                selectinload(InventoryItem.component),
                selectinload(InventoryItem.vendor)
            )
            .where(Component.category == ref_component.category)
            .where(Component.component_type == ref_component.component_type)
            .where(Component.id != component_id)
            .where(InventoryItem.is_active == True)
            .where(InventoryItem.quantity_available > 0)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [
            {
                "component": {
                    "id": str(item.component.id),
                    "name": item.component.name,
                    "part_number": item.component.part_number,
                    "manufacturer": item.component.manufacturer
                },
                "inventory": {
                    "id": str(item.id),
                    "unit_price": float(item.unit_price),
                    "quantity_available": item.quantity_available,
                    "vendor_name": item.vendor.name
                }
            }
            for item in items
        ]