"""
Inventory Sync System
Handles real-time inventory management, stock tracking, and multi-location sync
"""

import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import queue
import time


class InventoryOperation(Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    RESERVE = "reserve"
    RELEASE = "release"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"


class StockStatus(Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    BACKORDER = "backorder"
    DISCONTINUED = "discontinued"


@dataclass
class InventoryItem:
    product_id: str
    variant_id: Optional[str]
    sku: str
    location_id: str
    quantity_available: int
    quantity_reserved: int
    quantity_incoming: int
    reorder_point: int
    reorder_quantity: int
    cost: Optional[float]
    last_updated: datetime


@dataclass
class InventoryTransaction:
    transaction_id: str
    product_id: str
    variant_id: Optional[str]
    location_id: str
    operation: InventoryOperation
    quantity: int
    reference_id: Optional[str]  # Order ID, Transfer ID, etc.
    reference_type: Optional[str]  # 'order', 'transfer', 'adjustment'
    notes: Optional[str]
    created_at: datetime
    created_by: Optional[str]


class InventorySync:
    """Real-time inventory management and synchronization"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Multi-location support
        self.locations = self.load_locations()
        self.default_location = config.get('default_location', 'main')
        
        # Real-time sync settings
        self.sync_enabled = config.get('inventory_sync_enabled', True)
        self.sync_interval = config.get('sync_interval_seconds', 30)
        self.batch_size = config.get('sync_batch_size', 100)
        
        # Low stock alerts
        self.low_stock_alerts_enabled = config.get('low_stock_alerts', True)
        self.alert_threshold_days = config.get('alert_threshold_days', 7)
        
        # Background processing
        self.sync_queue = queue.Queue()
        self.running = False
        self.sync_thread = None
        
        # External integrations
        self.shopify_config = config.get('shopify', {})
        self.woocommerce_config = config.get('woocommerce', {})
        self.warehouse_config = config.get('warehouse_systems', {})
        
        # Start background sync if enabled
        if self.sync_enabled:
            self.start_background_sync()
            
    def get_inventory(self, product_id: str, variant_id: Optional[str] = None, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current inventory for product/variant"""
        try:
            location = location_id or self.default_location
            
            inventory = self.db.get_inventory_item(product_id, variant_id, location)
            if not inventory:
                # Create default inventory record
                inventory = self.create_inventory_record(product_id, variant_id, location)
                
            # Calculate derived values
            total_quantity = inventory['quantity_available'] + inventory['quantity_reserved']
            available_to_sell = max(0, inventory['quantity_available'])
            
            # Determine stock status
            stock_status = self.determine_stock_status(inventory)
            
            # Get incoming stock
            incoming_stock = self.get_incoming_stock(product_id, variant_id, location)
            
            return {
                'product_id': product_id,
                'variant_id': variant_id,
                'location_id': location,
                'quantity_available': inventory['quantity_available'],
                'quantity_reserved': inventory['quantity_reserved'],
                'quantity_incoming': incoming_stock,
                'total_quantity': total_quantity,
                'available_to_sell': available_to_sell,
                'reorder_point': inventory.get('reorder_point', 10),
                'reorder_quantity': inventory.get('reorder_quantity', 50),
                'stock_status': stock_status.value,
                'cost': inventory.get('cost'),
                'last_updated': inventory.get('last_updated'),
                'locations': self.get_all_location_inventory(product_id, variant_id)
            }
            
        except Exception as e:
            raise Exception(f"Error getting inventory: {e}")
            
    def update_inventory(self, inventory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update inventory levels"""
        try:
            product_id = inventory_data['product_id']
            variant_id = inventory_data.get('variant_id')
            location_id = inventory_data.get('location_id', self.default_location)
            operation = InventoryOperation(inventory_data['operation'])
            quantity = int(inventory_data['quantity'])
            reference_id = inventory_data.get('reference_id')
            reference_type = inventory_data.get('reference_type')
            notes = inventory_data.get('notes')
            
            # Get current inventory
            current_inventory = self.db.get_inventory_item(product_id, variant_id, location_id)
            if not current_inventory:
                current_inventory = self.create_inventory_record(product_id, variant_id, location_id)
                
            # Calculate new quantities based on operation
            new_available = current_inventory['quantity_available']
            new_reserved = current_inventory['quantity_reserved']
            
            if operation == InventoryOperation.INCREASE:
                new_available += quantity
            elif operation == InventoryOperation.DECREASE:
                new_available = max(0, new_available - quantity)
            elif operation == InventoryOperation.RESERVE:
                if new_available >= quantity:
                    new_available -= quantity
                    new_reserved += quantity
                else:
                    raise ValueError(f"Insufficient inventory to reserve {quantity} units")
            elif operation == InventoryOperation.RELEASE:
                new_reserved = max(0, new_reserved - quantity)
                new_available += min(quantity, current_inventory['quantity_reserved'])
            elif operation == InventoryOperation.ADJUSTMENT:
                # Direct adjustment to available quantity
                new_available = quantity
                
            # Update inventory record
            updated_inventory = {
                'product_id': product_id,
                'variant_id': variant_id,
                'location_id': location_id,
                'quantity_available': new_available,
                'quantity_reserved': new_reserved,
                'last_updated': datetime.now().isoformat()
            }
            
            success = self.db.update_inventory_item(updated_inventory)
            
            if success:
                # Create transaction record
                transaction = InventoryTransaction(
                    transaction_id=f"txn_{datetime.now().timestamp()}",
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=location_id,
                    operation=operation,
                    quantity=quantity,
                    reference_id=reference_id,
                    reference_type=reference_type,
                    notes=notes,
                    created_at=datetime.now(),
                    created_by=inventory_data.get('user_id')
                )
                
                self.db.save_inventory_transaction(asdict(transaction))
                
                # Queue for external sync
                if self.sync_enabled:
                    self.queue_sync_operation(product_id, variant_id, location_id)
                    
                # Check for low stock alerts
                if self.low_stock_alerts_enabled:
                    self.check_low_stock_alert(product_id, variant_id, location_id, new_available)
                    
                return {
                    'success': True,
                    'message': f'Inventory updated: {operation.value} {quantity} units',
                    'transaction_id': transaction.transaction_id,
                    'new_available': new_available,
                    'new_reserved': new_reserved
                }
            else:
                raise Exception("Failed to update inventory record")
                
        except Exception as e:
            raise Exception(f"Error updating inventory: {e}")
            
    def reserve_inventory(self, reservation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reserve inventory for orders"""
        try:
            items = reservation_data['items']  # List of items to reserve
            order_id = reservation_data['order_id']
            
            reserved_items = []
            failed_items = []
            
            for item in items:
                try:
                    # Reserve each item
                    reserve_result = self.update_inventory({
                        'product_id': item['product_id'],
                        'variant_id': item.get('variant_id'),
                        'location_id': item.get('location_id', self.default_location),
                        'operation': 'reserve',
                        'quantity': item['quantity'],
                        'reference_id': order_id,
                        'reference_type': 'order',
                        'notes': f'Reserved for order {order_id}'
                    })
                    
                    reserved_items.append({
                        'product_id': item['product_id'],
                        'variant_id': item.get('variant_id'),
                        'quantity': item['quantity'],
                        'transaction_id': reserve_result['transaction_id']
                    })
                    
                except Exception as e:
                    failed_items.append({
                        'product_id': item['product_id'],
                        'variant_id': item.get('variant_id'),
                        'quantity': item['quantity'],
                        'error': str(e)
                    })
                    
            return {
                'success': len(failed_items) == 0,
                'reserved_items': reserved_items,
                'failed_items': failed_items,
                'message': f'Reserved {len(reserved_items)} items, {len(failed_items)} failed'
            }
            
        except Exception as e:
            raise Exception(f"Error reserving inventory: {e}")
            
    def release_reservation(self, reservation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Release reserved inventory"""
        try:
            items = reservation_data['items']
            order_id = reservation_data['order_id']
            
            released_items = []
            
            for item in items:
                # Release reservation
                release_result = self.update_inventory({
                    'product_id': item['product_id'],
                    'variant_id': item.get('variant_id'),
                    'location_id': item.get('location_id', self.default_location),
                    'operation': 'release',
                    'quantity': item['quantity'],
                    'reference_id': order_id,
                    'reference_type': 'order_cancellation',
                    'notes': f'Released from cancelled order {order_id}'
                })
                
                released_items.append({
                    'product_id': item['product_id'],
                    'variant_id': item.get('variant_id'),
                    'quantity': item['quantity'],
                    'transaction_id': release_result['transaction_id']
                })
                
            return {
                'success': True,
                'released_items': released_items,
                'message': f'Released {len(released_items)} reserved items'
            }
            
        except Exception as e:
            raise Exception(f"Error releasing reservation: {e}")
            
    def transfer_inventory(self, transfer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transfer inventory between locations"""
        try:
            product_id = transfer_data['product_id']
            variant_id = transfer_data.get('variant_id')
            from_location = transfer_data['from_location']
            to_location = transfer_data['to_location']
            quantity = int(transfer_data['quantity'])
            notes = transfer_data.get('notes', '')
            
            transfer_id = f"transfer_{datetime.now().timestamp()}"
            
            # Decrease from source location
            decrease_result = self.update_inventory({
                'product_id': product_id,
                'variant_id': variant_id,
                'location_id': from_location,
                'operation': 'decrease',
                'quantity': quantity,
                'reference_id': transfer_id,
                'reference_type': 'transfer_out',
                'notes': f'Transfer to {to_location}: {notes}'
            })
            
            # Increase at destination location
            increase_result = self.update_inventory({
                'product_id': product_id,
                'variant_id': variant_id,
                'location_id': to_location,
                'operation': 'increase',
                'quantity': quantity,
                'reference_id': transfer_id,
                'reference_type': 'transfer_in',
                'notes': f'Transfer from {from_location}: {notes}'
            })
            
            # Save transfer record
            transfer_record = {
                'transfer_id': transfer_id,
                'product_id': product_id,
                'variant_id': variant_id,
                'from_location': from_location,
                'to_location': to_location,
                'quantity': quantity,
                'status': 'completed',
                'notes': notes,
                'created_at': datetime.now().isoformat()
            }
            
            self.db.save_inventory_transfer(transfer_record)
            
            return {
                'success': True,
                'transfer_id': transfer_id,
                'message': f'Transferred {quantity} units from {from_location} to {to_location}',
                'transactions': [
                    decrease_result['transaction_id'],
                    increase_result['transaction_id']
                ]
            }
            
        except Exception as e:
            raise Exception(f"Error transferring inventory: {e}")
            
    def bulk_update_inventory(self, bulk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Bulk update inventory levels"""
        try:
            updates = bulk_data['updates']
            update_results = []
            
            for update in updates:
                try:
                    result = self.update_inventory(update)
                    update_results.append({
                        'product_id': update['product_id'],
                        'variant_id': update.get('variant_id'),
                        'success': True,
                        'transaction_id': result['transaction_id']
                    })
                except Exception as e:
                    update_results.append({
                        'product_id': update['product_id'],
                        'variant_id': update.get('variant_id'),
                        'success': False,
                        'error': str(e)
                    })
                    
            successful = sum(1 for r in update_results if r['success'])
            failed = len(update_results) - successful
            
            return {
                'success': failed == 0,
                'total_updates': len(updates),
                'successful': successful,
                'failed': failed,
                'results': update_results
            }
            
        except Exception as e:
            raise Exception(f"Error in bulk inventory update: {e}")
            
    def get_inventory_report(self, report_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate inventory report"""
        try:
            location_id = report_params.get('location_id')
            category_id = report_params.get('category_id')
            low_stock_only = report_params.get('low_stock_only', False)
            
            inventory_items = self.db.get_inventory_report(location_id, category_id, low_stock_only)
            
            report_data = []
            total_value = 0
            low_stock_count = 0
            out_of_stock_count = 0
            
            for item in inventory_items:
                # Get product details
                product = self.db.get_product(item['product_id'])
                
                # Calculate values
                item_value = (item.get('cost', 0) or 0) * item['quantity_available']
                total_value += item_value
                
                # Determine status
                stock_status = self.determine_stock_status(item)
                if stock_status == StockStatus.LOW_STOCK:
                    low_stock_count += 1
                elif stock_status == StockStatus.OUT_OF_STOCK:
                    out_of_stock_count += 1
                    
                report_item = {
                    'product_id': item['product_id'],
                    'variant_id': item.get('variant_id'),
                    'sku': item.get('sku', ''),
                    'product_name': product.get('name', '') if product else '',
                    'location_id': item['location_id'],
                    'quantity_available': item['quantity_available'],
                    'quantity_reserved': item['quantity_reserved'],
                    'reorder_point': item.get('reorder_point', 0),
                    'stock_status': stock_status.value,
                    'cost': item.get('cost', 0),
                    'value': round(item_value, 2),
                    'last_updated': item.get('last_updated')
                }
                report_data.append(report_item)
                
            return {
                'success': True,
                'report_data': report_data,
                'summary': {
                    'total_items': len(report_data),
                    'total_value': round(total_value, 2),
                    'low_stock_items': low_stock_count,
                    'out_of_stock_items': out_of_stock_count,
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            raise Exception(f"Error generating inventory report: {e}")
            
    def sync_external_inventory(self, sync_params: Dict[str, Any]) -> Dict[str, Any]:
        """Sync inventory with external systems"""
        try:
            platform = sync_params.get('platform')  # 'shopify', 'woocommerce', etc.
            product_ids = sync_params.get('product_ids', [])
            
            sync_results = []
            
            if platform == 'shopify' and self.shopify_config.get('enabled'):
                sync_results = self.sync_shopify_inventory(product_ids)
            elif platform == 'woocommerce' and self.woocommerce_config.get('enabled'):
                sync_results = self.sync_woocommerce_inventory(product_ids)
            elif platform == 'warehouse':
                sync_results = self.sync_warehouse_inventory(product_ids)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
                
            return {
                'success': True,
                'platform': platform,
                'synced_products': len(sync_results),
                'sync_results': sync_results,
                'synced_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error syncing external inventory: {e}")
            
    def create_inventory_record(self, product_id: str, variant_id: Optional[str], location_id: str) -> Dict[str, Any]:
        """Create new inventory record with defaults"""
        try:
            inventory_record = {
                'product_id': product_id,
                'variant_id': variant_id,
                'location_id': location_id,
                'quantity_available': 0,
                'quantity_reserved': 0,
                'quantity_incoming': 0,
                'reorder_point': 10,
                'reorder_quantity': 50,
                'cost': None,
                'last_updated': datetime.now().isoformat()
            }
            
            self.db.save_inventory_item(inventory_record)
            return inventory_record
            
        except Exception as e:
            raise Exception(f"Error creating inventory record: {e}")
            
    def determine_stock_status(self, inventory: Dict[str, Any]) -> StockStatus:
        """Determine stock status based on inventory levels"""
        try:
            available = inventory['quantity_available']
            reorder_point = inventory.get('reorder_point', 10)
            
            if available <= 0:
                return StockStatus.OUT_OF_STOCK
            elif available <= reorder_point:
                return StockStatus.LOW_STOCK
            else:
                return StockStatus.IN_STOCK
                
        except Exception:
            return StockStatus.OUT_OF_STOCK
            
    def get_incoming_stock(self, product_id: str, variant_id: Optional[str], location_id: str) -> int:
        """Get incoming stock from purchase orders"""
        try:
            # This would query purchase orders, transfers in transit, etc.
            return 0  # Placeholder
        except Exception:
            return 0
            
    def get_all_location_inventory(self, product_id: str, variant_id: Optional[str]) -> List[Dict[str, Any]]:
        """Get inventory across all locations"""
        try:
            locations = self.db.get_product_inventory_all_locations(product_id, variant_id)
            
            location_data = []
            for location in locations:
                location_data.append({
                    'location_id': location['location_id'],
                    'location_name': self.get_location_name(location['location_id']),
                    'quantity_available': location['quantity_available'],
                    'quantity_reserved': location['quantity_reserved']
                })
                
            return location_data
            
        except Exception:
            return []
            
    def queue_sync_operation(self, product_id: str, variant_id: Optional[str], location_id: str):
        """Queue inventory change for external sync"""
        try:
            sync_item = {
                'product_id': product_id,
                'variant_id': variant_id,
                'location_id': location_id,
                'timestamp': datetime.now().isoformat()
            }
            self.sync_queue.put(sync_item)
        except Exception as e:
            print(f"Error queuing sync operation: {e}")
            
    def check_low_stock_alert(self, product_id: str, variant_id: Optional[str], location_id: str, current_quantity: int):
        """Check and send low stock alerts"""
        try:
            inventory = self.db.get_inventory_item(product_id, variant_id, location_id)
            if not inventory:
                return
                
            reorder_point = inventory.get('reorder_point', 10)
            
            if current_quantity <= reorder_point:
                # Send alert
                alert_data = {
                    'product_id': product_id,
                    'variant_id': variant_id,
                    'location_id': location_id,
                    'current_quantity': current_quantity,
                    'reorder_point': reorder_point,
                    'alert_type': 'low_stock',
                    'created_at': datetime.now().isoformat()
                }
                
                # This would send email, webhook, or queue notification
                print(f"LOW STOCK ALERT: {product_id} at {location_id} - {current_quantity} units remaining")
                
        except Exception as e:
            print(f"Error checking low stock alert: {e}")
            
    def start_background_sync(self):
        """Start background sync thread"""
        try:
            if not self.running:
                self.running = True
                self.sync_thread = threading.Thread(target=self._background_sync_worker, daemon=True)
                self.sync_thread.start()
        except Exception as e:
            print(f"Error starting background sync: {e}")
            
    def stop_background_sync(self):
        """Stop background sync thread"""
        try:
            self.running = False
            if self.sync_thread:
                self.sync_thread.join(timeout=5)
        except Exception as e:
            print(f"Error stopping background sync: {e}")
            
    def _background_sync_worker(self):
        """Background worker for inventory sync"""
        while self.running:
            try:
                # Process sync queue
                sync_items = []
                
                # Collect items from queue (up to batch size)
                while len(sync_items) < self.batch_size:
                    try:
                        item = self.sync_queue.get_nowait()
                        sync_items.append(item)
                    except queue.Empty:
                        break
                        
                # Sync collected items
                if sync_items:
                    self._process_sync_batch(sync_items)
                    
                # Sleep between batches
                time.sleep(self.sync_interval)
                
            except Exception as e:
                print(f"Error in background sync worker: {e}")
                time.sleep(10)  # Wait longer on error
                
    def _process_sync_batch(self, sync_items: List[Dict[str, Any]]):
        """Process a batch of sync items"""
        try:
            # Group by platform for efficient syncing
            shopify_items = []
            woocommerce_items = []
            
            for item in sync_items:
                if self.shopify_config.get('enabled'):
                    shopify_items.append(item)
                if self.woocommerce_config.get('enabled'):
                    woocommerce_items.append(item)
                    
            # Sync with each platform
            if shopify_items:
                self.sync_shopify_inventory([item['product_id'] for item in shopify_items])
            if woocommerce_items:
                self.sync_woocommerce_inventory([item['product_id'] for item in woocommerce_items])
                
        except Exception as e:
            print(f"Error processing sync batch: {e}")
            
    def sync_shopify_inventory(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Sync inventory with Shopify"""
        try:
            # This would use Shopify Admin API
            results = []
            
            for product_id in product_ids:
                # Get current inventory
                inventory = self.get_inventory(product_id)
                
                # Update Shopify inventory (mock)
                results.append({
                    'product_id': product_id,
                    'platform': 'shopify',
                    'success': True,
                    'updated_quantity': inventory['quantity_available']
                })
                
            return results
            
        except Exception as e:
            print(f"Error syncing Shopify inventory: {e}")
            return []
            
    def sync_woocommerce_inventory(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Sync inventory with WooCommerce"""
        try:
            # This would use WooCommerce REST API
            results = []
            
            for product_id in product_ids:
                inventory = self.get_inventory(product_id)
                
                results.append({
                    'product_id': product_id,
                    'platform': 'woocommerce',
                    'success': True,
                    'updated_quantity': inventory['quantity_available']
                })
                
            return results
            
        except Exception as e:
            print(f"Error syncing WooCommerce inventory: {e}")
            return []
            
    def sync_warehouse_inventory(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Sync inventory with warehouse management system"""
        try:
            # This would integrate with warehouse APIs
            results = []
            
            for product_id in product_ids:
                results.append({
                    'product_id': product_id,
                    'platform': 'warehouse',
                    'success': True,
                    'message': 'Warehouse sync completed'
                })
                
            return results
            
        except Exception as e:
            print(f"Error syncing warehouse inventory: {e}")
            return []
            
    def load_locations(self) -> Dict[str, Dict[str, Any]]:
        """Load inventory locations configuration"""
        try:
            return {
                'main': {
                    'name': 'Main Warehouse',
                    'address': '123 Main St, City, State',
                    'type': 'warehouse'
                },
                'store_1': {
                    'name': 'Retail Store 1',
                    'address': '456 Store Ave, City, State',
                    'type': 'retail'
                },
                'fulfillment': {
                    'name': 'Fulfillment Center',
                    'address': '789 Ship Dr, City, State',
                    'type': 'fulfillment'
                }
            }
        except Exception:
            return {'main': {'name': 'Main Location', 'type': 'warehouse'}}
            
    def get_location_name(self, location_id: str) -> str:
        """Get location name by ID"""
        try:
            return self.locations.get(location_id, {}).get('name', location_id)
        except Exception:
            return location_id