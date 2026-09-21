"""
Wishlist System
Handles customer wishlists, product saving, and sharing functionality
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class WishlistType(Enum):
    PRIVATE = "private"
    PUBLIC = "public" 
    SHARED = "shared"


class WishlistItemStatus(Enum):
    ACTIVE = "active"
    PURCHASED = "purchased"
    REMOVED = "removed"
    OUT_OF_STOCK = "out_of_stock"


@dataclass
class WishlistItem:
    item_id: str
    wishlist_id: str
    product_id: str
    variant_id: Optional[str]
    quantity: int
    added_at: datetime
    status: WishlistItemStatus
    notes: Optional[str]
    price_when_added: Optional[float]


class WishlistSystem:
    """Manages customer wishlists and saved items"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Wishlist settings
        self.max_wishlists_per_customer = config.get('max_wishlists_per_customer', 10)
        self.max_items_per_wishlist = config.get('max_items_per_wishlist', 500)
        self.allow_public_wishlists = config.get('allow_public_wishlists', True)
        self.allow_wishlist_sharing = config.get('allow_wishlist_sharing', True)
        
        # Guest wishlist settings
        self.enable_guest_wishlists = config.get('enable_guest_wishlists', True)
        self.guest_wishlist_expiry_days = config.get('guest_wishlist_expiry_days', 30)
        
        # Notification settings
        self.price_drop_notifications = config.get('price_drop_notifications', True)
        self.back_in_stock_notifications = config.get('back_in_stock_notifications', True)
        
    def create_wishlist(self, wishlist_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new wishlist"""
        try:
            customer_id = wishlist_data.get('customer_id')
            guest_id = wishlist_data.get('guest_id')
            
            if not customer_id and not guest_id:
                raise ValueError("Either customer_id or guest_id is required")
                
            # Check wishlist limits for registered customers
            if customer_id:
                existing_count = self.db.get_customer_wishlist_count(customer_id)
                if existing_count >= self.max_wishlists_per_customer:
                    raise ValueError(f"Maximum {self.max_wishlists_per_customer} wishlists allowed per customer")
                    
            # Generate wishlist ID
            wishlist_id = f"wishlist_{datetime.now().timestamp()}"
            
            # Create wishlist record
            wishlist = {
                'wishlist_id': wishlist_id,
                'customer_id': customer_id,
                'guest_id': guest_id,
                'name': wishlist_data.get('name', 'My Wishlist'),
                'description': wishlist_data.get('description', ''),
                'type': wishlist_data.get('type', WishlistType.PRIVATE.value),
                'is_default': wishlist_data.get('is_default', False),
                'share_token': self.generate_share_token() if wishlist_data.get('type') == WishlistType.SHARED.value else None,
                'tags': wishlist_data.get('tags', []),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=self.guest_wishlist_expiry_days)).isoformat() if guest_id else None
            }
            
            # If this is the first wishlist or marked as default, make it default
            if wishlist['is_default'] or (customer_id and existing_count == 0):
                self.db.unset_default_wishlists(customer_id)
                wishlist['is_default'] = True
                
            # Save wishlist
            success = self.db.save_wishlist(wishlist)
            if not success:
                raise Exception("Failed to create wishlist")
                
            return {
                'success': True,
                'wishlist_id': wishlist_id,
                'name': wishlist['name'],
                'type': wishlist['type'],
                'share_token': wishlist.get('share_token'),
                'message': 'Wishlist created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error creating wishlist: {e}")
            
    def add_item_to_wishlist(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add item to wishlist"""
        try:
            wishlist_id = item_data['wishlist_id']
            product_id = item_data['product_id']
            variant_id = item_data.get('variant_id')
            quantity = item_data.get('quantity', 1)
            notes = item_data.get('notes')
            
            # Get wishlist
            wishlist = self.db.get_wishlist(wishlist_id)
            if not wishlist:
                raise ValueError("Wishlist not found")
                
            # Check item limits
            current_item_count = self.db.get_wishlist_item_count(wishlist_id)
            if current_item_count >= self.max_items_per_wishlist:
                raise ValueError(f"Maximum {self.max_items_per_wishlist} items allowed per wishlist")
                
            # Check if item already exists in wishlist
            existing_item = self.db.get_wishlist_item(wishlist_id, product_id, variant_id)
            if existing_item:
                # Update quantity instead of adding duplicate
                return self.update_wishlist_item_quantity(
                    existing_item['item_id'],
                    existing_item['quantity'] + quantity
                )
                
            # Get product information
            product = self.db.get_product(product_id)
            if not product:
                raise ValueError("Product not found")
                
            # Get current price for price tracking
            current_price = self.get_product_current_price(product_id, variant_id)
            
            # Generate item ID
            item_id = f"item_{datetime.now().timestamp()}"
            
            # Create wishlist item
            wishlist_item = {
                'item_id': item_id,
                'wishlist_id': wishlist_id,
                'product_id': product_id,
                'variant_id': variant_id,
                'quantity': quantity,
                'notes': notes,
                'price_when_added': current_price,
                'status': WishlistItemStatus.ACTIVE.value,
                'added_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save item
            success = self.db.save_wishlist_item(wishlist_item)
            if not success:
                raise Exception("Failed to add item to wishlist")
                
            # Update wishlist timestamp
            self.db.update_wishlist(wishlist_id, {'updated_at': datetime.now().isoformat()})
            
            # Set up price tracking if enabled
            if self.price_drop_notifications:
                self.setup_price_tracking(item_id, product_id, variant_id, current_price)
                
            return {
                'success': True,
                'item_id': item_id,
                'wishlist_id': wishlist_id,
                'product_id': product_id,
                'variant_id': variant_id,
                'quantity': quantity,
                'message': 'Item added to wishlist successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error adding item to wishlist: {e}")
            
    def remove_item_from_wishlist(self, item_id: str) -> Dict[str, Any]:
        """Remove item from wishlist"""
        try:
            # Get item
            item = self.db.get_wishlist_item_by_id(item_id)
            if not item:
                raise ValueError("Wishlist item not found")
                
            # Update item status instead of hard delete
            success = self.db.update_wishlist_item(item_id, {
                'status': WishlistItemStatus.REMOVED.value,
                'removed_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
            
            if not success:
                raise Exception("Failed to remove item from wishlist")
                
            # Update wishlist timestamp
            self.db.update_wishlist(item['wishlist_id'], {'updated_at': datetime.now().isoformat()})
            
            return {
                'success': True,
                'item_id': item_id,
                'message': 'Item removed from wishlist successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error removing item from wishlist: {e}")
            
    def update_wishlist_item_quantity(self, item_id: str, quantity: int) -> Dict[str, Any]:
        """Update wishlist item quantity"""
        try:
            if quantity <= 0:
                return self.remove_item_from_wishlist(item_id)
                
            # Get item
            item = self.db.get_wishlist_item_by_id(item_id)
            if not item:
                raise ValueError("Wishlist item not found")
                
            # Update quantity
            success = self.db.update_wishlist_item(item_id, {
                'quantity': quantity,
                'updated_at': datetime.now().isoformat()
            })
            
            if not success:
                raise Exception("Failed to update item quantity")
                
            # Update wishlist timestamp
            self.db.update_wishlist(item['wishlist_id'], {'updated_at': datetime.now().isoformat()})
            
            return {
                'success': True,
                'item_id': item_id,
                'quantity': quantity,
                'message': 'Item quantity updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error updating item quantity: {e}")
            
    def get_customer_wishlists(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all wishlists for customer"""
        try:
            wishlists = self.db.get_customer_wishlists(customer_id)
            
            # Enrich wishlist data
            enriched_wishlists = []
            for wishlist in wishlists:
                enriched_wishlist = self.enrich_wishlist_data(wishlist)
                enriched_wishlists.append(enriched_wishlist)
                
            return enriched_wishlists
            
        except Exception as e:
            raise Exception(f"Error getting customer wishlists: {e}")
            
    def get_wishlist_details(self, wishlist_id: str, access_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get wishlist details with items"""
        try:
            # Get wishlist
            wishlist = self.db.get_wishlist(wishlist_id)
            if not wishlist:
                return None
                
            # Check access permissions
            if wishlist['type'] == WishlistType.PRIVATE.value:
                # Private wishlists can only be accessed by owner
                # In a real implementation, you'd verify ownership here
                pass
            elif wishlist['type'] == WishlistType.SHARED.value:
                # Shared wishlists require access token
                if access_token != wishlist.get('share_token'):
                    return None
                    
            # Get wishlist items
            items = self.db.get_wishlist_items(wishlist_id)
            
            # Enrich item data
            enriched_items = []
            for item in items:
                if item['status'] == WishlistItemStatus.ACTIVE.value:
                    enriched_item = self.enrich_wishlist_item_data(item)
                    enriched_items.append(enriched_item)
                    
            # Enrich wishlist data
            enriched_wishlist = self.enrich_wishlist_data(wishlist)
            enriched_wishlist['items'] = enriched_items
            enriched_wishlist['item_count'] = len(enriched_items)
            
            return enriched_wishlist
            
        except Exception as e:
            raise Exception(f"Error getting wishlist details: {e}")
            
    def move_item_to_cart(self, move_data: Dict[str, Any]) -> Dict[str, Any]:
        """Move wishlist item to shopping cart"""
        try:
            item_id = move_data['item_id']
            cart_id = move_data['cart_id']
            remove_from_wishlist = move_data.get('remove_from_wishlist', True)
            
            # Get wishlist item
            item = self.db.get_wishlist_item_by_id(item_id)
            if not item:
                raise ValueError("Wishlist item not found")
                
            # Get product information
            product = self.db.get_product(item['product_id'])
            if not product:
                raise ValueError("Product not found")
                
            # Check product availability
            inventory = self.db.get_product_inventory(item['product_id'], item['variant_id'])
            if inventory and inventory['available_quantity'] < item['quantity']:
                raise ValueError("Insufficient stock available")
                
            # Add to cart (this would integrate with cart system)
            cart_item = {
                'product_id': item['product_id'],
                'variant_id': item['variant_id'],
                'quantity': item['quantity']
            }
            
            # Mock cart addition (in real implementation, use cart system)
            cart_success = True  # self.cart_system.add_item(cart_id, cart_item)
            
            if cart_success:
                # Remove from wishlist if requested
                if remove_from_wishlist:
                    self.remove_item_from_wishlist(item_id)
                else:
                    # Mark as purchased but keep in wishlist
                    self.db.update_wishlist_item(item_id, {
                        'status': WishlistItemStatus.PURCHASED.value,
                        'purchased_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    })
                    
                return {
                    'success': True,
                    'item_id': item_id,
                    'cart_id': cart_id,
                    'product_id': item['product_id'],
                    'quantity': item['quantity'],
                    'message': 'Item moved to cart successfully'
                }
            else:
                raise Exception("Failed to add item to cart")
                
        except Exception as e:
            raise Exception(f"Error moving item to cart: {e}")
            
    def share_wishlist(self, share_data: Dict[str, Any]) -> Dict[str, Any]:
        """Share wishlist with others"""
        try:
            wishlist_id = share_data['wishlist_id']
            recipient_emails = share_data.get('recipient_emails', [])
            message = share_data.get('message', '')
            
            # Get wishlist
            wishlist = self.db.get_wishlist(wishlist_id)
            if not wishlist:
                raise ValueError("Wishlist not found")
                
            # Generate share token if needed
            if not wishlist.get('share_token'):
                share_token = self.generate_share_token()
                self.db.update_wishlist(wishlist_id, {
                    'share_token': share_token,
                    'type': WishlistType.SHARED.value,
                    'updated_at': datetime.now().isoformat()
                })
                wishlist['share_token'] = share_token
                
            # Create share record
            share_record = {
                'share_id': f"share_{datetime.now().timestamp()}",
                'wishlist_id': wishlist_id,
                'shared_by': wishlist.get('customer_id'),
                'recipient_emails': json.dumps(recipient_emails),
                'message': message,
                'share_token': wishlist['share_token'],
                'created_at': datetime.now().isoformat()
            }
            
            self.db.save_wishlist_share(share_record)
            
            # Send share notifications
            if recipient_emails:
                self.send_wishlist_share_emails(wishlist, recipient_emails, message)
                
            # Generate share URL
            share_url = self.generate_share_url(wishlist_id, wishlist['share_token'])
            
            return {
                'success': True,
                'wishlist_id': wishlist_id,
                'share_token': wishlist['share_token'],
                'share_url': share_url,
                'recipients_notified': len(recipient_emails),
                'message': 'Wishlist shared successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error sharing wishlist: {e}")
            
    def merge_wishlists(self, merge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two wishlists"""
        try:
            source_wishlist_id = merge_data['source_wishlist_id']
            target_wishlist_id = merge_data['target_wishlist_id']
            delete_source = merge_data.get('delete_source', True)
            
            # Get both wishlists
            source_wishlist = self.db.get_wishlist(source_wishlist_id)
            target_wishlist = self.db.get_wishlist(target_wishlist_id)
            
            if not source_wishlist or not target_wishlist:
                raise ValueError("One or both wishlists not found")
                
            # Verify same owner (for security)
            if source_wishlist.get('customer_id') != target_wishlist.get('customer_id'):
                raise ValueError("Can only merge wishlists from same customer")
                
            # Get items from source wishlist
            source_items = self.db.get_wishlist_items(source_wishlist_id)
            
            merged_count = 0
            skipped_count = 0
            
            for item in source_items:
                if item['status'] == WishlistItemStatus.ACTIVE.value:
                    # Check if item already exists in target wishlist
                    existing_item = self.db.get_wishlist_item(
                        target_wishlist_id,
                        item['product_id'],
                        item['variant_id']
                    )
                    
                    if existing_item:
                        # Update quantity in existing item
                        new_quantity = existing_item['quantity'] + item['quantity']
                        self.db.update_wishlist_item(existing_item['item_id'], {
                            'quantity': new_quantity,
                            'updated_at': datetime.now().isoformat()
                        })
                        skipped_count += 1
                    else:
                        # Move item to target wishlist
                        self.db.update_wishlist_item(item['item_id'], {
                            'wishlist_id': target_wishlist_id,
                            'updated_at': datetime.now().isoformat()
                        })
                        merged_count += 1
                        
            # Delete source wishlist if requested
            if delete_source:
                self.db.delete_wishlist(source_wishlist_id)
                
            # Update target wishlist timestamp
            self.db.update_wishlist(target_wishlist_id, {
                'updated_at': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'target_wishlist_id': target_wishlist_id,
                'merged_items': merged_count,
                'skipped_items': skipped_count,
                'source_deleted': delete_source,
                'message': f'Successfully merged {merged_count} items'
            }
            
        except Exception as e:
            raise Exception(f"Error merging wishlists: {e}")
            
    def get_wishlist_analytics(self, wishlist_id: str) -> Dict[str, Any]:
        """Get wishlist analytics"""
        try:
            wishlist = self.db.get_wishlist(wishlist_id)
            if not wishlist:
                raise ValueError("Wishlist not found")
                
            items = self.db.get_wishlist_items(wishlist_id)
            
            # Calculate analytics
            total_items = len([i for i in items if i['status'] == WishlistItemStatus.ACTIVE.value])
            purchased_items = len([i for i in items if i['status'] == WishlistItemStatus.PURCHASED.value])
            
            total_value = 0
            price_changes = 0
            
            for item in items:
                if item['status'] == WishlistItemStatus.ACTIVE.value:
                    current_price = self.get_product_current_price(item['product_id'], item['variant_id'])
                    if current_price:
                        total_value += current_price * item['quantity']
                        
                        # Check for price changes
                        if item.get('price_when_added') and current_price != item['price_when_added']:
                            price_changes += 1
                            
            return {
                'wishlist_id': wishlist_id,
                'total_items': total_items,
                'purchased_items': purchased_items,
                'total_value': round(total_value, 2),
                'items_with_price_changes': price_changes,
                'created_date': wishlist.get('created_at'),
                'last_updated': wishlist.get('updated_at'),
                'most_wanted_category': self.get_most_wanted_category(items),
                'average_item_price': round(total_value / max(total_items, 1), 2)
            }
            
        except Exception as e:
            raise Exception(f"Error getting wishlist analytics: {e}")
            
    def enrich_wishlist_data(self, wishlist: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich wishlist data with additional information"""
        try:
            # Add item count
            item_count = self.db.get_active_wishlist_item_count(wishlist['wishlist_id'])
            wishlist['item_count'] = item_count
            
            # Add total value
            items = self.db.get_wishlist_items(wishlist['wishlist_id'])
            total_value = 0
            
            for item in items:
                if item['status'] == WishlistItemStatus.ACTIVE.value:
                    current_price = self.get_product_current_price(item['product_id'], item['variant_id'])
                    if current_price:
                        total_value += current_price * item['quantity']
                        
            wishlist['total_value'] = round(total_value, 2)
            
            # Add share URL for shared wishlists
            if wishlist['type'] == WishlistType.SHARED.value and wishlist.get('share_token'):
                wishlist['share_url'] = self.generate_share_url(wishlist['wishlist_id'], wishlist['share_token'])
                
            return wishlist
            
        except Exception:
            return wishlist
            
    def enrich_wishlist_item_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich wishlist item data with product information"""
        try:
            # Get product data
            product = self.db.get_product(item['product_id'])
            if product:
                item['product_name'] = product.get('name', '')
                item['product_images'] = product.get('images', [])
                item['product_url'] = product.get('url', '')
                
            # Get variant data if applicable
            if item.get('variant_id'):
                variant = self.db.get_product_variant(item['variant_id'])
                if variant:
                    item['variant_title'] = variant.get('title', '')
                    item['variant_sku'] = variant.get('sku', '')
                    
            # Get current price and compare with price when added
            current_price = self.get_product_current_price(item['product_id'], item['variant_id'])
            if current_price:
                item['current_price'] = current_price
                item['total_current_price'] = current_price * item['quantity']
                
                if item.get('price_when_added'):
                    price_difference = current_price - item['price_when_added']
                    item['price_difference'] = price_difference
                    item['price_change_percentage'] = round((price_difference / item['price_when_added']) * 100, 2)
                    
            # Check stock availability
            inventory = self.db.get_product_inventory(item['product_id'], item['variant_id'])
            if inventory:
                item['in_stock'] = inventory['available_quantity'] >= item['quantity']
                item['available_quantity'] = inventory['available_quantity']
            else:
                item['in_stock'] = False
                item['available_quantity'] = 0
                
            return item
            
        except Exception:
            return item
            
    def get_product_current_price(self, product_id: str, variant_id: Optional[str]) -> Optional[float]:
        """Get current price for product/variant"""
        try:
            if variant_id:
                variant = self.db.get_product_variant(variant_id)
                return variant.get('price') if variant else None
            else:
                product = self.db.get_product(product_id)
                return product.get('price') if product else None
        except Exception:
            return None
            
    def generate_share_token(self) -> str:
        """Generate unique share token"""
        try:
            import secrets
            return secrets.token_urlsafe(32)
        except Exception:
            return f"token_{datetime.now().timestamp()}"
            
    def generate_share_url(self, wishlist_id: str, share_token: str) -> str:
        """Generate share URL for wishlist"""
        try:
            base_url = self.config.get('frontend_base_url', 'https://example.com')
            return f"{base_url}/wishlist/{wishlist_id}?token={share_token}"
        except Exception:
            return f"/wishlist/{wishlist_id}?token={share_token}"
            
    def get_most_wanted_category(self, items: List[Dict[str, Any]]) -> Optional[str]:
        """Get most wanted product category from wishlist items"""
        try:
            category_counts = {}
            
            for item in items:
                if item['status'] == WishlistItemStatus.ACTIVE.value:
                    product = self.db.get_product(item['product_id'])
                    if product and product.get('category_id'):
                        category_id = product['category_id']
                        category_counts[category_id] = category_counts.get(category_id, 0) + 1
                        
            if category_counts:
                most_wanted_category_id = max(category_counts, key=category_counts.get)
                category = self.db.get_category(most_wanted_category_id)
                return category.get('name', most_wanted_category_id) if category else most_wanted_category_id
                
            return None
            
        except Exception:
            return None
            
    def setup_price_tracking(self, item_id: str, product_id: str, variant_id: Optional[str], current_price: float):
        """Set up price tracking for wishlist item"""
        try:
            tracking_record = {
                'item_id': item_id,
                'product_id': product_id,
                'variant_id': variant_id,
                'tracked_price': current_price,
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            
            self.db.save_price_tracking(tracking_record)
            
        except Exception as e:
            print(f"Error setting up price tracking: {e}")
            
    def send_wishlist_share_emails(self, wishlist: Dict[str, Any], recipient_emails: List[str], message: str):
        """Send wishlist share notification emails"""
        try:
            # This would integrate with email service
            share_url = self.generate_share_url(wishlist['wishlist_id'], wishlist['share_token'])
            
            for email in recipient_emails:
                print(f"Wishlist '{wishlist['name']}' shared with {email}: {share_url}")
                
        except Exception as e:
            print(f"Error sending share emails: {e}")
            
    def cleanup_expired_guest_wishlists(self) -> int:
        """Clean up expired guest wishlists"""
        try:
            if not self.enable_guest_wishlists:
                return 0
                
            expired_count = self.db.delete_expired_guest_wishlists()
            return expired_count
            
        except Exception as e:
            print(f"Error cleaning up expired guest wishlists: {e}")
            return 0
            
    def get_public_wishlists(self, filters: Dict[str, Any] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """Get public wishlists for browsing"""
        try:
            if not self.allow_public_wishlists:
                return {'wishlists': [], 'pagination': {'total_count': 0}}
                
            if filters is None:
                filters = {}
                
            filters['type'] = WishlistType.PUBLIC.value
            
            wishlists = self.db.list_public_wishlists(filters, page, limit)
            
            # Enrich wishlist data
            enriched_wishlists = []
            for wishlist in wishlists:
                enriched_wishlist = self.enrich_wishlist_data(wishlist)
                # Remove sensitive information
                enriched_wishlist.pop('customer_id', None)
                enriched_wishlists.append(enriched_wishlist)
                
            total_count = self.db.get_public_wishlist_count(filters)
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'wishlists': enriched_wishlists,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting public wishlists: {e}")