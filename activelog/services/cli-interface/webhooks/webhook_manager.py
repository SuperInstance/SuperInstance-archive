#!/usr/bin/env python3
"""
Webhook Manager - Handles webhook registration, processing, and delivery
Provides reliable webhook system with retry logic, signature verification, and event filtering
"""

import json
import uuid
import hmac
import hashlib
import time
import asyncio
import aiohttp
import requests
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from urllib.parse import urlparse
import threading
from queue import Queue, Empty
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    """Webhook configuration"""
    id: str
    url: str
    events: List[str]
    secret: Optional[str] = None
    active: bool = True
    created_at: str = None
    updated_at: str = None
    retry_count: int = 3
    timeout: int = 30
    headers: Optional[Dict[str, str]] = None
    filters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at


@dataclass
class WebhookEvent:
    """Webhook event data"""
    id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: str
    source: str
    webhook_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class WebhookDelivery:
    """Webhook delivery attempt"""
    id: str
    webhook_id: str
    event_id: str
    status: str  # pending, success, failed, retrying
    attempt: int
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    delivered_at: Optional[str] = None
    next_retry: Optional[str] = None


class WebhookManager:
    """Manages webhook registration, processing, and delivery"""
    
    def __init__(self, config):
        self.config = config
        self.webhooks = {}
        self.event_queue = Queue()
        self.delivery_queue = Queue()
        
        # Database for persistent storage
        self.db_path = Path("/home/activeloguser/activelog/data/cli-interface/webhooks.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Load existing webhooks
        self._load_webhooks()
        
        # Start background workers
        self.running = True
        self.event_processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self.delivery_worker_thread = threading.Thread(target=self._process_deliveries, daemon=True)
        
        self.event_processor_thread.start()
        self.delivery_worker_thread.start()
        
        logger.info("Webhook Manager initialized with persistent storage")

    def register_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new webhook"""
        try:
            # Validate webhook data
            self._validate_webhook_data(webhook_data)
            
            # Create webhook configuration
            webhook_id = webhook_data.get('id', str(uuid.uuid4()))
            webhook = WebhookConfig(
                id=webhook_id,
                url=webhook_data['url'],
                events=webhook_data['events'],
                secret=webhook_data.get('secret'),
                active=webhook_data.get('active', True),
                retry_count=webhook_data.get('retry_count', 3),
                timeout=webhook_data.get('timeout', 30),
                headers=webhook_data.get('headers', {}),
                filters=webhook_data.get('filters', {})
            )
            
            # Store webhook
            self.webhooks[webhook_id] = webhook
            self._save_webhook(webhook)
            
            logger.info(f"Registered webhook {webhook_id} for events: {webhook.events}")
            
            return {
                'webhook_id': webhook_id,
                'url': webhook.url,
                'events': webhook.events,
                'active': webhook.active,
                'created_at': webhook.created_at
            }
            
        except Exception as e:
            logger.error(f"Failed to register webhook: {e}")
            raise

    def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister webhook"""
        try:
            if webhook_id in self.webhooks:
                del self.webhooks[webhook_id]
                self._delete_webhook(webhook_id)
                logger.info(f"Unregistered webhook {webhook_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unregister webhook {webhook_id}: {e}")
            return False

    def update_webhook(self, webhook_id: str, updates: Dict[str, Any]) -> bool:
        """Update webhook configuration"""
        try:
            if webhook_id not in self.webhooks:
                return False
            
            webhook = self.webhooks[webhook_id]
            
            # Update fields
            if 'url' in updates:
                webhook.url = updates['url']
            if 'events' in updates:
                webhook.events = updates['events']
            if 'secret' in updates:
                webhook.secret = updates['secret']
            if 'active' in updates:
                webhook.active = updates['active']
            if 'headers' in updates:
                webhook.headers = updates['headers']
            if 'filters' in updates:
                webhook.filters = updates['filters']
            
            webhook.updated_at = datetime.utcnow().isoformat()
            
            # Save changes
            self._save_webhook(webhook)
            
            logger.info(f"Updated webhook {webhook_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update webhook {webhook_id}: {e}")
            return False

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhooks"""
        try:
            webhooks = []
            for webhook in self.webhooks.values():
                webhooks.append({
                    'id': webhook.id,
                    'url': webhook.url,
                    'events': webhook.events,
                    'active': webhook.active,
                    'created_at': webhook.created_at,
                    'updated_at': webhook.updated_at,
                    'retry_count': webhook.retry_count,
                    'timeout': webhook.timeout
                })
            return webhooks
        except Exception as e:
            logger.error(f"Failed to list webhooks: {e}")
            return []

    def get_webhook(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Get webhook by ID"""
        webhook = self.webhooks.get(webhook_id)
        if webhook:
            return {
                'id': webhook.id,
                'url': webhook.url,
                'events': webhook.events,
                'active': webhook.active,
                'created_at': webhook.created_at,
                'updated_at': webhook.updated_at,
                'retry_count': webhook.retry_count,
                'timeout': webhook.timeout,
                'headers': webhook.headers,
                'filters': webhook.filters
            }
        return None

    def trigger_event(self, event_type: str, data: Dict[str, Any], source: str = "cli-interface") -> str:
        """Trigger webhook event"""
        try:
            event = WebhookEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                data=data,
                timestamp=datetime.utcnow().isoformat(),
                source=source
            )
            
            # Queue event for processing
            self.event_queue.put(event)
            
            logger.info(f"Triggered event {event_type} with ID {event.id}")
            return event.id
            
        except Exception as e:
            logger.error(f"Failed to trigger event {event_type}: {e}")
            raise

    def process_webhook(self, webhook_id: str, payload: Dict[str, Any], 
                       headers: Dict[str, str]) -> Dict[str, Any]:
        """Process incoming webhook payload"""
        try:
            # Verify webhook exists
            webhook = self.webhooks.get(webhook_id)
            if not webhook:
                return {
                    'success': False,
                    'error': f'Webhook {webhook_id} not found'
                }
            
            if not webhook.active:
                return {
                    'success': False,
                    'error': f'Webhook {webhook_id} is inactive'
                }
            
            # Verify signature if secret is configured
            if webhook.secret:
                signature = headers.get('X-Webhook-Signature', '')
                if not self._verify_signature(payload, webhook.secret, signature):
                    return {
                        'success': False,
                        'error': 'Invalid signature'
                    }
            
            # Extract event information
            event_type = payload.get('event_type', 'webhook.received')
            event_data = payload.get('data', payload)
            
            # Create event
            event = WebhookEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                data=event_data,
                timestamp=datetime.utcnow().isoformat(),
                source='external',
                webhook_id=webhook_id
            )
            
            # Process event
            self._process_incoming_webhook_event(webhook, event)
            
            return {
                'success': True,
                'event_id': event.id,
                'processed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process webhook {webhook_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_webhook_deliveries(self, webhook_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get webhook delivery history"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM webhook_deliveries 
                WHERE webhook_id = ? 
                ORDER BY delivered_at DESC 
                LIMIT ?
            """, (webhook_id, limit))
            
            deliveries = []
            for row in cursor.fetchall():
                deliveries.append({
                    'id': row[0],
                    'webhook_id': row[1],
                    'event_id': row[2],
                    'status': row[3],
                    'attempt': row[4],
                    'response_code': row[5],
                    'response_body': row[6],
                    'error_message': row[7],
                    'delivered_at': row[8],
                    'next_retry': row[9]
                })
            
            conn.close()
            return deliveries
            
        except Exception as e:
            logger.error(f"Failed to get deliveries for webhook {webhook_id}: {e}")
            return []

    def retry_failed_deliveries(self, webhook_id: Optional[str] = None) -> int:
        """Retry failed webhook deliveries"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Query failed deliveries ready for retry
            if webhook_id:
                cursor.execute("""
                    SELECT * FROM webhook_deliveries 
                    WHERE webhook_id = ? AND status = 'failed' 
                    AND (next_retry IS NULL OR next_retry <= ?)
                """, (webhook_id, datetime.utcnow().isoformat()))
            else:
                cursor.execute("""
                    SELECT * FROM webhook_deliveries 
                    WHERE status = 'failed' 
                    AND (next_retry IS NULL OR next_retry <= ?)
                """, (datetime.utcnow().isoformat(),))
            
            failed_deliveries = cursor.fetchall()
            conn.close()
            
            # Queue for retry
            retry_count = 0
            for delivery_row in failed_deliveries:
                delivery = WebhookDelivery(
                    id=delivery_row[0],
                    webhook_id=delivery_row[1],
                    event_id=delivery_row[2],
                    status='retrying',
                    attempt=delivery_row[4] + 1,
                    response_code=delivery_row[5],
                    response_body=delivery_row[6],
                    error_message=delivery_row[7],
                    delivered_at=delivery_row[8],
                    next_retry=delivery_row[9]
                )
                
                self.delivery_queue.put(delivery)
                retry_count += 1
            
            logger.info(f"Queued {retry_count} deliveries for retry")
            return retry_count
            
        except Exception as e:
            logger.error(f"Failed to retry deliveries: {e}")
            return 0

    def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Test webhook with a ping event"""
        try:
            webhook = self.webhooks.get(webhook_id)
            if not webhook:
                return {
                    'success': False,
                    'error': f'Webhook {webhook_id} not found'
                }
            
            # Create test event
            test_data = {
                'test': True,
                'webhook_id': webhook_id,
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'This is a test webhook delivery'
            }
            
            # Trigger ping event
            event_id = self.trigger_event('webhook.ping', test_data)
            
            return {
                'success': True,
                'event_id': event_id,
                'message': 'Test event triggered'
            }
            
        except Exception as e:
            logger.error(f"Failed to test webhook {webhook_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _validate_webhook_data(self, data: Dict[str, Any]):
        """Validate webhook registration data"""
        required_fields = ['url', 'events']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate URL
        parsed_url = urlparse(data['url'])
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid webhook URL")
        
        # Validate events
        if not isinstance(data['events'], list) or not data['events']:
            raise ValueError("Events must be a non-empty list")

    def _process_events(self):
        """Background thread to process webhook events"""
        while self.running:
            try:
                # Get event from queue (blocking with timeout)
                event = self.event_queue.get(timeout=1)
                
                # Find matching webhooks
                matching_webhooks = self._find_matching_webhooks(event)
                
                # Create deliveries for each matching webhook
                for webhook in matching_webhooks:
                    delivery = WebhookDelivery(
                        id=str(uuid.uuid4()),
                        webhook_id=webhook.id,
                        event_id=event.id,
                        status='pending',
                        attempt=1
                    )
                    
                    # Queue delivery
                    self.delivery_queue.put((event, webhook, delivery))
                
                self.event_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    def _process_deliveries(self):
        """Background thread to process webhook deliveries"""
        while self.running:
            try:
                # Get delivery from queue (blocking with timeout)
                delivery_item = self.delivery_queue.get(timeout=1)
                
                if isinstance(delivery_item, WebhookDelivery):
                    # This is a retry delivery
                    self._retry_delivery(delivery_item)
                else:
                    # This is a new delivery
                    event, webhook, delivery = delivery_item
                    self._deliver_webhook(event, webhook, delivery)
                
                self.delivery_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing delivery: {e}")

    def _find_matching_webhooks(self, event: WebhookEvent) -> List[WebhookConfig]:
        """Find webhooks that match the event"""
        matching = []
        
        for webhook in self.webhooks.values():
            if not webhook.active:
                continue
            
            # Check if event type matches
            if event.event_type in webhook.events or '*' in webhook.events:
                # Apply filters if configured
                if self._event_matches_filters(event, webhook.filters):
                    matching.append(webhook)
        
        return matching

    def _event_matches_filters(self, event: WebhookEvent, filters: Optional[Dict[str, Any]]) -> bool:
        """Check if event matches webhook filters"""
        if not filters:
            return True
        
        try:
            # Simple filter matching - can be extended for complex filters
            for filter_key, filter_value in filters.items():
                if filter_key == 'source' and event.source != filter_value:
                    return False
                elif filter_key in event.data:
                    if event.data[filter_key] != filter_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return True  # Default to include on error

    def _deliver_webhook(self, event: WebhookEvent, webhook: WebhookConfig, delivery: WebhookDelivery):
        """Deliver webhook event"""
        try:
            # Prepare payload
            payload = {
                'event_id': event.id,
                'event_type': event.event_type,
                'timestamp': event.timestamp,
                'data': event.data,
                'source': event.source
            }
            
            # Prepare headers
            headers = {'Content-Type': 'application/json'}
            if webhook.headers:
                headers.update(webhook.headers)
            
            # Add signature if secret is configured
            if webhook.secret:
                signature = self._generate_signature(payload, webhook.secret)
                headers['X-Webhook-Signature'] = signature
            
            # Make HTTP request
            response = requests.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=webhook.timeout
            )
            
            # Update delivery status
            delivery.response_code = response.status_code
            delivery.response_body = response.text[:1000]  # Limit size
            delivery.delivered_at = datetime.utcnow().isoformat()
            
            if 200 <= response.status_code < 300:
                delivery.status = 'success'
                logger.info(f"Successfully delivered webhook {webhook.id} for event {event.id}")
            else:
                delivery.status = 'failed'
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(f"Failed to deliver webhook {webhook.id}: HTTP {response.status_code}")
                
                # Schedule retry if attempts remaining
                self._schedule_retry(delivery, webhook)
            
        except requests.exceptions.Timeout:
            delivery.status = 'failed'
            delivery.error_message = 'Request timeout'
            delivery.delivered_at = datetime.utcnow().isoformat()
            self._schedule_retry(delivery, webhook)
            logger.warning(f"Webhook {webhook.id} delivery timed out")
            
        except Exception as e:
            delivery.status = 'failed'
            delivery.error_message = str(e)
            delivery.delivered_at = datetime.utcnow().isoformat()
            self._schedule_retry(delivery, webhook)
            logger.error(f"Failed to deliver webhook {webhook.id}: {e}")
        
        finally:
            # Save delivery record
            self._save_delivery(delivery)

    def _schedule_retry(self, delivery: WebhookDelivery, webhook: WebhookConfig):
        """Schedule webhook delivery retry"""
        if delivery.attempt < webhook.retry_count:
            # Calculate backoff delay (exponential backoff)
            delay_seconds = (2 ** (delivery.attempt - 1)) * 60  # 1, 2, 4 minutes
            next_retry = datetime.utcnow() + timedelta(seconds=delay_seconds)
            delivery.next_retry = next_retry.isoformat()
            delivery.status = 'retrying'
            
            logger.info(f"Scheduled retry {delivery.attempt}/{webhook.retry_count} for webhook {webhook.id} at {next_retry}")

    def _retry_delivery(self, delivery: WebhookDelivery):
        """Retry failed webhook delivery"""
        try:
            # Get webhook and recreate event from database
            webhook = self.webhooks.get(delivery.webhook_id)
            if not webhook:
                logger.error(f"Webhook {delivery.webhook_id} not found for retry")
                return
            
            # This is a simplified retry - in production you'd want to store full event data
            # For now, create a retry event
            retry_event = WebhookEvent(
                id=delivery.event_id,
                event_type='webhook.retry',
                data={'retry_attempt': delivery.attempt},
                timestamp=datetime.utcnow().isoformat(),
                source='retry'
            )
            
            self._deliver_webhook(retry_event, webhook, delivery)
            
        except Exception as e:
            logger.error(f"Failed to retry delivery {delivery.id}: {e}")

    def _process_incoming_webhook_event(self, webhook: WebhookConfig, event: WebhookEvent):
        """Process incoming webhook event (from external source)"""
        try:
            # Log the incoming event
            logger.info(f"Processed incoming webhook event {event.event_type} for webhook {webhook.id}")
            
            # Here you could trigger internal events, update state, etc.
            # For now, we just log it
            
        except Exception as e:
            logger.error(f"Failed to process incoming webhook event: {e}")

    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC signature for webhook payload"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def _verify_signature(self, payload: Dict[str, Any], secret: str, signature: str) -> bool:
        """Verify HMAC signature"""
        try:
            expected_signature = self._generate_signature(payload, secret)
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create webhooks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS webhooks (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    events TEXT NOT NULL,
                    secret TEXT,
                    active INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT,
                    retry_count INTEGER DEFAULT 3,
                    timeout INTEGER DEFAULT 30,
                    headers TEXT,
                    filters TEXT
                )
            """)
            
            # Create deliveries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS webhook_deliveries (
                    id TEXT PRIMARY KEY,
                    webhook_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER DEFAULT 1,
                    response_code INTEGER,
                    response_body TEXT,
                    error_message TEXT,
                    delivered_at TEXT,
                    next_retry TEXT,
                    FOREIGN KEY (webhook_id) REFERENCES webhooks (id)
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _load_webhooks(self):
        """Load webhooks from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM webhooks")
            rows = cursor.fetchall()
            
            for row in rows:
                webhook = WebhookConfig(
                    id=row[0],
                    url=row[1],
                    events=json.loads(row[2]),
                    secret=row[3],
                    active=bool(row[4]),
                    created_at=row[5],
                    updated_at=row[6],
                    retry_count=row[7],
                    timeout=row[8],
                    headers=json.loads(row[9]) if row[9] else None,
                    filters=json.loads(row[10]) if row[10] else None
                )
                self.webhooks[webhook.id] = webhook
            
            conn.close()
            logger.info(f"Loaded {len(self.webhooks)} webhooks from database")
            
        except Exception as e:
            logger.error(f"Failed to load webhooks: {e}")

    def _save_webhook(self, webhook: WebhookConfig):
        """Save webhook to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO webhooks 
                (id, url, events, secret, active, created_at, updated_at, 
                 retry_count, timeout, headers, filters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                webhook.id,
                webhook.url,
                json.dumps(webhook.events),
                webhook.secret,
                int(webhook.active),
                webhook.created_at,
                webhook.updated_at,
                webhook.retry_count,
                webhook.timeout,
                json.dumps(webhook.headers) if webhook.headers else None,
                json.dumps(webhook.filters) if webhook.filters else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save webhook {webhook.id}: {e}")

    def _delete_webhook(self, webhook_id: str):
        """Delete webhook from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
            cursor.execute("DELETE FROM webhook_deliveries WHERE webhook_id = ?", (webhook_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to delete webhook {webhook_id}: {e}")

    def _save_delivery(self, delivery: WebhookDelivery):
        """Save delivery record to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO webhook_deliveries 
                (id, webhook_id, event_id, status, attempt, response_code, 
                 response_body, error_message, delivered_at, next_retry)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                delivery.id,
                delivery.webhook_id,
                delivery.event_id,
                delivery.status,
                delivery.attempt,
                delivery.response_code,
                delivery.response_body,
                delivery.error_message,
                delivery.delivered_at,
                delivery.next_retry
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save delivery {delivery.id}: {e}")

    def shutdown(self):
        """Shutdown webhook manager"""
        self.running = False
        
        # Wait for threads to finish
        if self.event_processor_thread.is_alive():
            self.event_processor_thread.join(timeout=5)
        
        if self.delivery_worker_thread.is_alive():
            self.delivery_worker_thread.join(timeout=5)
        
        logger.info("Webhook Manager shut down")