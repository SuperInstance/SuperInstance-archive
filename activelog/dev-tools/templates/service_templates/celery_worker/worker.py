"""
{{SERVICE_NAME_TITLE}} Celery Worker
{{SERVICE_DESCRIPTION}}
"""

from celery import Celery
import logging
import os
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    '{{SERVICE_NAME_SNAKE}}',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=['{{SERVICE_NAME_SNAKE}}.tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        '{{SERVICE_NAME_SNAKE}}.tasks.*': {'queue': '{{SERVICE_NAME_SNAKE}}'},
    }
)


@celery_app.task(bind=True)
def health_check(self):
    """Health check task."""
    return {
        'status': 'healthy',
        'worker': '{{SERVICE_NAME_SNAKE}}',
        'timestamp': datetime.utcnow().isoformat(),
        'task_id': self.request.id
    }


@celery_app.task(bind=True)
def process_item(self, item_data: Dict[str, Any]):
    """Process item task."""
    logger.info(f"Processing item: {item_data}")
    
    try:
        # Implement your processing logic here
        result = {
            'status': 'completed',
            'item_id': item_data.get('id'),
            'processed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Item processed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing item: {e}")
        self.retry(countdown=60, max_retries=3)


@celery_app.task(bind=True)
def batch_process_items(self, items_data: list):
    """Batch process multiple items."""
    logger.info(f"Processing batch of {len(items_data)} items")
    
    results = []
    for item_data in items_data:
        try:
            # Process each item
            result = process_item.delay(item_data)
            results.append(result.id)
        except Exception as e:
            logger.error(f"Error queuing item for processing: {e}")
            results.append(None)
    
    return {
        'status': 'batch_queued',
        'total_items': len(items_data),
        'task_ids': results,
        'queued_at': datetime.utcnow().isoformat()
    }


if __name__ == '__main__':
    celery_app.start()
