"""
NATS-based message queue service for video processing pipeline
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from uuid import uuid4

import nats
from nats.errors import TimeoutError
import structlog

from config.settings import settings

logger = structlog.get_logger()


class MessageQueueService:
    """
    NATS-based message queue service for handling async video processing tasks
    """
    
    def __init__(self):
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[nats.js.JetStreamContext] = None
        self.subjects = settings.nats_subjects
        self._subscribers = {}
        
    async def connect(self) -> None:
        """Connect to NATS server and set up JetStream"""
        try:
            self.nc = await nats.connect(settings.nats_url)
            self.js = self.nc.jetstream()
            
            # Create streams if they don't exist
            await self._setup_streams()
            
            logger.info("Connected to NATS server", url=settings.nats_url)
            
        except Exception as e:
            logger.error("Failed to connect to NATS", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from NATS server"""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS server")

    async def _setup_streams(self) -> None:
        """Set up JetStream streams for video processing"""
        streams_config = [
            {
                "name": "VIDEO_EVENTS",
                "subjects": [
                    self.subjects["video_uploaded"],
                    self.subjects["video_processed"],
                    self.subjects["video_failed"]
                ],
                "retention": nats.js.api.RetentionPolicy.WORK_QUEUE,
                "max_age": 7 * 24 * 3600,  # 7 days
                "storage": nats.js.api.StorageType.FILE
            },
            {
                "name": "PROCESSING_TASKS",
                "subjects": [
                    self.subjects["transcode_request"],
                    self.subjects["analysis_request"]
                ],
                "retention": nats.js.api.RetentionPolicy.WORK_QUEUE,
                "max_age": 24 * 3600,  # 1 day
                "storage": nats.js.api.StorageType.FILE
            },
            {
                "name": "NOTIFICATIONS",
                "subjects": [self.subjects["notification"]],
                "retention": nats.js.api.RetentionPolicy.LIMITS,
                "max_age": 3 * 24 * 3600,  # 3 days
                "storage": nats.js.api.StorageType.FILE
            }
        ]
        
        for stream_config in streams_config:
            try:
                stream_info = await self.js.stream_info(stream_config["name"])
                logger.info("Stream already exists", name=stream_config["name"])
            except:
                # Stream doesn't exist, create it
                await self.js.add_stream(
                    name=stream_config["name"],
                    subjects=stream_config["subjects"],
                    retention=stream_config["retention"],
                    max_age=stream_config["max_age"],
                    storage=stream_config["storage"]
                )
                logger.info("Created stream", name=stream_config["name"])

    async def publish_video_uploaded(
        self,
        video_id: str,
        video_path: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publish video uploaded event"""
        message = {
            "event_id": str(uuid4()),
            "video_id": video_id,
            "video_path": video_path,
            "user_id": user_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "video_uploaded"
        }
        
        await self._publish_message(
            subject=self.subjects["video_uploaded"],
            message=message
        )

    async def publish_video_processed(
        self,
        video_id: str,
        processing_results: Dict[str, Any],
        processing_time: float
    ) -> None:
        """Publish video processed event"""
        message = {
            "event_id": str(uuid4()),
            "video_id": video_id,
            "processing_results": processing_results,
            "processing_time_seconds": processing_time,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "video_processed"
        }
        
        await self._publish_message(
            subject=self.subjects["video_processed"],
            message=message
        )

    async def publish_video_failed(
        self,
        video_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publish video processing failed event"""
        message = {
            "event_id": str(uuid4()),
            "video_id": video_id,
            "error_message": error_message,
            "error_details": error_details or {},
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "video_failed"
        }
        
        await self._publish_message(
            subject=self.subjects["video_failed"],
            message=message
        )

    async def publish_transcode_request(
        self,
        video_id: str,
        input_path: str,
        output_config: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """Publish transcoding request and return job ID"""
        job_id = str(uuid4())
        
        message = {
            "job_id": job_id,
            "video_id": video_id,
            "input_path": input_path,
            "output_config": output_config,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
            "job_type": "transcode"
        }
        
        await self._publish_message(
            subject=self.subjects["transcode_request"],
            message=message
        )
        
        return job_id

    async def publish_analysis_request(
        self,
        video_id: str,
        video_path: str,
        analysis_config: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """Publish analysis request and return job ID"""
        job_id = str(uuid4())
        
        message = {
            "job_id": job_id,
            "video_id": video_id,
            "video_path": video_path,
            "analysis_config": analysis_config,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
            "job_type": "analysis"
        }
        
        await self._publish_message(
            subject=self.subjects["analysis_request"],
            message=message
        )
        
        return job_id

    async def publish_notification(
        self,
        recipient_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publish notification message"""
        notification = {
            "notification_id": str(uuid4()),
            "recipient_id": recipient_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
            "read": False
        }
        
        await self._publish_message(
            subject=self.subjects["notification"],
            message=notification
        )

    async def subscribe_video_uploaded(
        self,
        callback: Callable[[Dict[str, Any]], None],
        durable_name: str = "video_uploaded_consumer"
    ) -> None:
        """Subscribe to video uploaded events"""
        await self._subscribe_to_subject(
            subject=self.subjects["video_uploaded"],
            callback=callback,
            durable_name=durable_name
        )

    async def subscribe_transcode_requests(
        self,
        callback: Callable[[Dict[str, Any]], None],
        durable_name: str = "transcode_worker"
    ) -> None:
        """Subscribe to transcoding requests"""
        await self._subscribe_to_subject(
            subject=self.subjects["transcode_request"],
            callback=callback,
            durable_name=durable_name
        )

    async def subscribe_analysis_requests(
        self,
        callback: Callable[[Dict[str, Any]], None],
        durable_name: str = "analysis_worker"
    ) -> None:
        """Subscribe to analysis requests"""
        await self._subscribe_to_subject(
            subject=self.subjects["analysis_request"],
            callback=callback,
            durable_name=durable_name
        )

    async def _publish_message(
        self,
        subject: str,
        message: Dict[str, Any]
    ) -> None:
        """Publish message to NATS JetStream"""
        try:
            message_data = json.dumps(message).encode()
            
            ack = await self.js.publish(
                subject=subject,
                payload=message_data
            )
            
            logger.debug("Message published",
                        subject=subject,
                        sequence=ack.seq,
                        message_id=message.get("event_id") or message.get("job_id"))
                        
        except Exception as e:
            logger.error("Failed to publish message",
                        subject=subject,
                        error=str(e))
            raise

    async def _subscribe_to_subject(
        self,
        subject: str,
        callback: Callable[[Dict[str, Any]], None],
        durable_name: str,
        max_deliver: int = 3
    ) -> None:
        """Subscribe to a subject with JetStream"""
        try:
            async def message_handler(msg):
                try:
                    # Parse message
                    message_data = json.loads(msg.data.decode())
                    
                    # Call callback
                    await callback(message_data)
                    
                    # Acknowledge message
                    await msg.ack()
                    
                    logger.debug("Message processed",
                               subject=subject,
                               message_id=message_data.get("event_id") or message_data.get("job_id"))
                    
                except Exception as e:
                    logger.error("Message processing failed",
                               subject=subject,
                               error=str(e))
                    
                    # Negative acknowledge to retry
                    await msg.nak()
            
            # Create consumer
            consumer_config = nats.js.api.ConsumerConfig(
                durable_name=durable_name,
                deliver_policy=nats.js.api.DeliverPolicy.ALL,
                ack_policy=nats.js.api.AckPolicy.EXPLICIT,
                max_deliver=max_deliver,
                ack_wait=300,  # 5 minutes
                replay_policy=nats.js.api.ReplayPolicy.INSTANT
            )
            
            # Subscribe
            subscription = await self.js.subscribe(
                subject=subject,
                cb=message_handler,
                config=consumer_config
            )
            
            # Store subscription
            self._subscribers[subject] = subscription
            
            logger.info("Subscribed to subject",
                       subject=subject,
                       durable_name=durable_name)
            
        except Exception as e:
            logger.error("Failed to subscribe to subject",
                        subject=subject,
                        error=str(e))
            raise

    async def get_pending_messages(
        self,
        subject: str,
        consumer_name: str
    ) -> int:
        """Get number of pending messages for a consumer"""
        try:
            consumer_info = await self.js.consumer_info(
                stream="PROCESSING_TASKS",
                consumer=consumer_name
            )
            return consumer_info.num_pending
            
        except Exception as e:
            logger.error("Failed to get pending messages",
                        subject=subject,
                        consumer=consumer_name,
                        error=str(e))
            return 0

    async def get_stream_info(self, stream_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a stream"""
        try:
            stream_info = await self.js.stream_info(stream_name)
            return {
                "name": stream_info.config.name,
                "subjects": stream_info.config.subjects,
                "messages": stream_info.state.messages,
                "bytes": stream_info.state.bytes,
                "first_seq": stream_info.state.first_seq,
                "last_seq": stream_info.state.last_seq,
                "consumers": stream_info.state.consumer_count
            }
            
        except Exception as e:
            logger.error("Failed to get stream info",
                        stream_name=stream_name,
                        error=str(e))
            return None

    async def purge_stream(self, stream_name: str) -> bool:
        """Purge all messages from a stream"""
        try:
            await self.js.purge_stream(stream_name)
            logger.info("Stream purged", stream_name=stream_name)
            return True
            
        except Exception as e:
            logger.error("Failed to purge stream",
                        stream_name=stream_name,
                        error=str(e))
            return False

    async def create_consumer_group(
        self,
        stream_name: str,
        consumer_name: str,
        filter_subject: str,
        max_workers: int = 3
    ) -> None:
        """Create a consumer group for load balancing"""
        try:
            consumer_config = nats.js.api.ConsumerConfig(
                durable_name=consumer_name,
                deliver_policy=nats.js.api.DeliverPolicy.ALL,
                ack_policy=nats.js.api.AckPolicy.EXPLICIT,
                max_deliver=3,
                filter_subject=filter_subject,
                deliver_group=f"{consumer_name}_group"
            )
            
            await self.js.add_consumer(
                stream=stream_name,
                config=consumer_config
            )
            
            logger.info("Consumer group created",
                       stream=stream_name,
                       consumer=consumer_name,
                       max_workers=max_workers)
            
        except Exception as e:
            logger.error("Failed to create consumer group",
                        stream_name=stream_name,
                        consumer_name=consumer_name,
                        error=str(e))
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on NATS connection and streams"""
        health_status = {
            "connected": False,
            "streams": {},
            "latency_ms": None
        }
        
        try:
            if not self.nc or not self.nc.is_connected:
                return health_status
                
            health_status["connected"] = True
            
            # Test latency
            start_time = asyncio.get_event_loop().time()
            await self.nc.flush(timeout=5.0)
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            health_status["latency_ms"] = round(latency, 2)
            
            # Check streams
            stream_names = ["VIDEO_EVENTS", "PROCESSING_TASKS", "NOTIFICATIONS"]
            for stream_name in stream_names:
                stream_info = await self.get_stream_info(stream_name)
                health_status["streams"][stream_name] = {
                    "exists": stream_info is not None,
                    "messages": stream_info.get("messages", 0) if stream_info else 0,
                    "consumers": stream_info.get("consumers", 0) if stream_info else 0
                }
                
        except Exception as e:
            logger.error("NATS health check failed", error=str(e))
            health_status["error"] = str(e)
            
        return health_status


# Global message queue service instance
mq_service = MessageQueueService()