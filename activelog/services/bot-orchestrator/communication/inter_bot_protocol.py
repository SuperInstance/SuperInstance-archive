"""
Advanced Inter-Bot Communication Protocol
Enables sophisticated communication, coordination, and collaboration between bots
"""

import asyncio
import json
import logging
import uuid
import time
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
import websockets

logger = logging.getLogger(__name__)

class MessageType(Enum):
    # Basic Communication
    PING = "ping"
    PONG = "pong"
    BROADCAST = "broadcast"
    DIRECT_MESSAGE = "direct_message"
    
    # Task Coordination  
    TASK_REQUEST = "task_request"
    TASK_ACCEPT = "task_accept"
    TASK_DECLINE = "task_decline"
    TASK_HANDOFF = "task_handoff"
    TASK_COMPLETE = "task_complete"
    
    # Collaboration
    COLLABORATION_INVITE = "collaboration_invite"
    COLLABORATION_JOIN = "collaboration_join"
    COLLABORATION_LEAVE = "collaboration_leave"
    CONTEXT_SHARE = "context_share"
    KNOWLEDGE_UPDATE = "knowledge_update"
    
    # Coordination
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    STATUS_UPDATE = "status_update"
    CAPABILITY_ANNOUNCEMENT = "capability_announcement"
    
    # Resource Management
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_GRANT = "resource_grant"
    RESOURCE_DENY = "resource_deny"
    RESOURCE_RELEASE = "resource_release"
    
    # Error Handling
    ERROR_REPORT = "error_report"
    RECOVERY_REQUEST = "recovery_request"
    ASSISTANCE_REQUEST = "assistance_request"

class Priority(Enum):
    LOW = 1
    NORMAL = 2  
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

class BotRole(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    ASSISTANT = "assistant"

@dataclass
class BotMessage:
    """Standard inter-bot message format"""
    message_id: str
    sender_id: str
    recipient_id: str  # Can be "*" for broadcast
    message_type: MessageType
    priority: Priority
    timestamp: float
    content: Dict[str, Any]
    
    # Message routing and delivery
    route: List[str] = None  # Message routing path
    ttl: int = 10  # Time to live (hops)
    requires_ack: bool = False
    correlation_id: Optional[str] = None  # For request-response patterns
    
    # Context and metadata
    task_context: Optional[str] = None
    session_id: Optional[str] = None
    encryption_level: str = "none"  # none, basic, high
    
    def __post_init__(self):
        if self.route is None:
            self.route = []

@dataclass
class BotCapabilityProfile:
    """Detailed bot capability profile for communication"""
    bot_id: str
    name: str
    capabilities: List[str]
    specializations: List[str]
    
    # Communication preferences
    max_concurrent_collaborations: int = 3
    preferred_communication_style: str = "formal"  # formal, casual, technical
    response_time_sla_ms: int = 5000
    
    # Resource information
    available_resources: Dict[str, float] = None
    current_load: float = 0.0
    reliability_score: float = 1.0
    
    # Collaboration metrics
    successful_collaborations: int = 0
    collaboration_rating: float = 5.0
    
    def __post_init__(self):
        if self.available_resources is None:
            self.available_resources = {}

@dataclass
class CollaborationSession:
    """Active collaboration session between bots"""
    session_id: str
    task_id: str
    participants: List[str]
    leader_bot_id: str
    created_at: datetime
    
    # Session state
    status: str = "active"  # active, paused, completed, failed
    shared_context: Dict[str, Any] = None
    coordination_rules: Dict[str, Any] = None
    
    # Progress tracking
    milestones: List[Dict[str, Any]] = None
    current_phase: str = "initialization"
    completion_percentage: float = 0.0
    
    def __post_init__(self):
        if self.shared_context is None:
            self.shared_context = {}
        if self.coordination_rules is None:
            self.coordination_rules = {}
        if self.milestones is None:
            self.milestones = []

class InterBotCommunicationHub:
    """Central hub for inter-bot communication and coordination"""
    
    def __init__(self, hub_port: int = 8482):
        self.hub_port = hub_port
        self.connected_bots: Dict[str, Dict[str, Any]] = {}
        self.bot_capabilities: Dict[str, BotCapabilityProfile] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.collaboration_sessions: Dict[str, CollaborationSession] = {}
        
        # Message handling
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.message_history: List[BotMessage] = []
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Network topology and routing
        self.bot_network_graph: Dict[str, Set[str]] = {}  # Bot -> Connected bots
        self.routing_table: Dict[str, List[str]] = {}  # Bot -> Route path
        
        # Performance and reliability
        self.message_stats = {
            "total_sent": 0,
            "total_received": 0,
            "total_delivered": 0,
            "average_latency_ms": 0.0,
            "failed_deliveries": 0
        }
        
        self.running = False
        self._setup_default_handlers()
    
    async def start(self):
        """Start the communication hub"""
        logger.info(f"Starting Inter-Bot Communication Hub on port {self.hub_port}")
        
        self.running = True
        
        # Start message processing
        asyncio.create_task(self._message_processor())
        
        # Start WebSocket server for bot connections
        asyncio.create_task(self._start_websocket_server())
        
        # Start periodic maintenance
        asyncio.create_task(self._periodic_maintenance())
        
        logger.info("Inter-Bot Communication Hub started successfully")
    
    async def stop(self):
        """Stop the communication hub"""
        logger.info("Stopping Inter-Bot Communication Hub")
        self.running = False
    
    async def register_bot(
        self, 
        bot_id: str, 
        capabilities: BotCapabilityProfile,
        websocket: Optional[Any] = None
    ):
        """Register a new bot in the communication network"""
        
        self.connected_bots[bot_id] = {
            "websocket": websocket,
            "connected_at": datetime.now(),
            "last_seen": datetime.now(),
            "status": "online",
            "message_count": 0
        }
        
        self.bot_capabilities[bot_id] = capabilities
        self.bot_network_graph[bot_id] = set()
        
        # Announce new bot to network
        await self._broadcast_message(BotMessage(
            message_id=str(uuid.uuid4()),
            sender_id="hub",
            recipient_id="*",
            message_type=MessageType.CAPABILITY_ANNOUNCEMENT,
            priority=Priority.NORMAL,
            timestamp=time.time(),
            content={
                "new_bot_id": bot_id,
                "capabilities": asdict(capabilities),
                "action": "joined"
            }
        ))
        
        logger.info(f"Bot {bot_id} registered with capabilities: {capabilities.capabilities}")
    
    async def unregister_bot(self, bot_id: str):
        """Unregister a bot from the network"""
        
        if bot_id not in self.connected_bots:
            return
        
        # End any active collaborations
        for session_id, session in list(self.collaboration_sessions.items()):
            if bot_id in session.participants:
                await self._end_collaboration_session(session_id, f"Bot {bot_id} disconnected")
        
        # Remove from network
        del self.connected_bots[bot_id]
        if bot_id in self.bot_capabilities:
            del self.bot_capabilities[bot_id]
        if bot_id in self.bot_network_graph:
            del self.bot_network_graph[bot_id]
        
        # Remove from other bots' connection lists
        for connections in self.bot_network_graph.values():
            connections.discard(bot_id)
        
        # Announce departure
        await self._broadcast_message(BotMessage(
            message_id=str(uuid.uuid4()),
            sender_id="hub",
            recipient_id="*",
            message_type=MessageType.CAPABILITY_ANNOUNCEMENT,
            priority=Priority.NORMAL,
            timestamp=time.time(),
            content={
                "departed_bot_id": bot_id,
                "action": "left"
            }
        ))
        
        logger.info(f"Bot {bot_id} unregistered from network")
    
    async def send_message(self, message: BotMessage) -> bool:
        """Send a message through the network"""
        
        # Validate message
        if not self._validate_message(message):
            logger.error(f"Invalid message format: {message.message_id}")
            return False
        
        # Add to processing queue
        await self.message_queue.put(message)
        self.message_stats["total_sent"] += 1
        
        return True
    
    async def send_request_response(
        self, 
        request: BotMessage, 
        timeout_seconds: float = 10.0
    ) -> Optional[BotMessage]:
        """Send a request and wait for response"""
        
        request.requires_ack = True
        request.correlation_id = str(uuid.uuid4())
        
        # Create future for response
        response_future = asyncio.Future()
        self.pending_responses[request.correlation_id] = response_future
        
        # Send request
        success = await self.send_message(request)
        if not success:
            del self.pending_responses[request.correlation_id]
            return None
        
        try:
            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout_seconds)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request {request.correlation_id} timed out")
            return None
        finally:
            if request.correlation_id in self.pending_responses:
                del self.pending_responses[request.correlation_id]
    
    async def create_collaboration_session(
        self, 
        task_id: str, 
        required_capabilities: List[str],
        max_participants: int = 5
    ) -> Optional[str]:
        """Create a new collaboration session"""
        
        # Find suitable bots
        suitable_bots = self._find_bots_with_capabilities(required_capabilities)
        
        if len(suitable_bots) < 2:
            logger.warning(f"Insufficient bots for collaboration on task {task_id}")
            return None
        
        # Select participants (limit to max_participants)
        participants = suitable_bots[:max_participants]
        
        # Choose leader (bot with highest collaboration rating)
        leader_bot = max(participants, 
                        key=lambda bot_id: self.bot_capabilities[bot_id].collaboration_rating)
        
        # Create session
        session_id = str(uuid.uuid4())
        session = CollaborationSession(
            session_id=session_id,
            task_id=task_id,
            participants=participants,
            leader_bot_id=leader_bot,
            created_at=datetime.now()
        )
        
        self.collaboration_sessions[session_id] = session
        
        # Send collaboration invites
        for bot_id in participants:
            invite_message = BotMessage(
                message_id=str(uuid.uuid4()),
                sender_id="hub",
                recipient_id=bot_id,
                message_type=MessageType.COLLABORATION_INVITE,
                priority=Priority.HIGH,
                timestamp=time.time(),
                content={
                    "session_id": session_id,
                    "task_id": task_id,
                    "participants": participants,
                    "leader_bot_id": leader_bot,
                    "required_capabilities": required_capabilities,
                    "role": "leader" if bot_id == leader_bot else "participant"
                },
                requires_ack=True
            )
            
            await self.send_message(invite_message)
        
        logger.info(f"Collaboration session {session_id} created for task {task_id} with {len(participants)} participants")
        return session_id
    
    async def join_collaboration(self, session_id: str, bot_id: str) -> bool:
        """Bot joins a collaboration session"""
        
        session = self.collaboration_sessions.get(session_id)
        if not session or bot_id not in session.participants:
            return False
        
        # Send join message to all participants
        join_message = BotMessage(
            message_id=str(uuid.uuid4()),
            sender_id="hub", 
            recipient_id="*",
            message_type=MessageType.COLLABORATION_JOIN,
            priority=Priority.NORMAL,
            timestamp=time.time(),
            content={
                "session_id": session_id,
                "bot_id": bot_id,
                "action": "joined"
            },
            session_id=session_id
        )
        
        await self._broadcast_to_session(session_id, join_message)
        return True
    
    async def share_context_in_session(
        self, 
        session_id: str, 
        sender_bot_id: str, 
        context_data: Dict[str, Any]
    ):
        """Share context within a collaboration session"""
        
        session = self.collaboration_sessions.get(session_id)
        if not session or sender_bot_id not in session.participants:
            return False
        
        # Update shared context
        session.shared_context[sender_bot_id] = context_data
        session.shared_context["last_update"] = datetime.now().isoformat()
        
        # Broadcast context update
        context_message = BotMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_bot_id,
            recipient_id="*",
            message_type=MessageType.CONTEXT_SHARE,
            priority=Priority.NORMAL,
            timestamp=time.time(),
            content={
                "context_data": context_data,
                "sender_bot_id": sender_bot_id
            },
            session_id=session_id
        )
        
        await self._broadcast_to_session(session_id, context_message)
        return True
    
    def _setup_default_handlers(self):
        """Setup default message handlers"""
        
        self.message_handlers[MessageType.PING] = self._handle_ping
        self.message_handlers[MessageType.TASK_REQUEST] = self._handle_task_request
        self.message_handlers[MessageType.COLLABORATION_JOIN] = self._handle_collaboration_join
        self.message_handlers[MessageType.STATUS_UPDATE] = self._handle_status_update
        self.message_handlers[MessageType.ERROR_REPORT] = self._handle_error_report
        self.message_handlers[MessageType.ASSISTANCE_REQUEST] = self._handle_assistance_request
    
    async def _message_processor(self):
        """Main message processing loop"""
        
        while self.running:
            try:
                # Get next message from queue
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # Process message
                await self._process_message(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message processing error: {e}")
    
    async def _process_message(self, message: BotMessage):
        """Process an individual message"""
        
        start_time = time.time()
        
        try:
            # Update routing path
            message.route.append("hub")
            
            # Check TTL
            if message.ttl <= 0:
                logger.warning(f"Message {message.message_id} expired (TTL exceeded)")
                return
            
            message.ttl -= 1
            
            # Handle response messages
            if message.correlation_id and message.correlation_id in self.pending_responses:
                future = self.pending_responses[message.correlation_id]
                if not future.done():
                    future.set_result(message)
                return
            
            # Call appropriate handler
            handler = self.message_handlers.get(message.message_type)
            if handler:
                await handler(message)
            else:
                # Route to recipient(s)
                await self._route_message(message)
            
            # Update stats
            latency_ms = (time.time() - start_time) * 1000
            self._update_latency_stats(latency_ms)
            
            # Store in history (keep last 1000 messages)
            self.message_history.append(message)
            if len(self.message_history) > 1000:
                self.message_history = self.message_history[-1000:]
                
        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {e}")
            self.message_stats["failed_deliveries"] += 1
    
    async def _route_message(self, message: BotMessage):
        """Route message to appropriate recipient(s)"""
        
        if message.recipient_id == "*":
            # Broadcast message
            await self._broadcast_message(message)
        else:
            # Direct message
            await self._deliver_message(message.recipient_id, message)
    
    async def _broadcast_message(self, message: BotMessage):
        """Broadcast message to all connected bots"""
        
        for bot_id in self.connected_bots:
            if bot_id != message.sender_id:  # Don't send back to sender
                await self._deliver_message(bot_id, message)
    
    async def _broadcast_to_session(self, session_id: str, message: BotMessage):
        """Broadcast message to all bots in a collaboration session"""
        
        session = self.collaboration_sessions.get(session_id)
        if not session:
            return
        
        for bot_id in session.participants:
            if bot_id != message.sender_id:
                await self._deliver_message(bot_id, message)
    
    async def _deliver_message(self, bot_id: str, message: BotMessage):
        """Deliver message to a specific bot"""
        
        bot_info = self.connected_bots.get(bot_id)
        if not bot_info:
            logger.warning(f"Bot {bot_id} not found for message delivery")
            return
        
        websocket = bot_info["websocket"]
        if websocket:
            try:
                await websocket.send(json.dumps(asdict(message)))
                bot_info["message_count"] += 1
                bot_info["last_seen"] = datetime.now()
                self.message_stats["total_delivered"] += 1
            except Exception as e:
                logger.error(f"Failed to deliver message to {bot_id}: {e}")
                # Mark bot as disconnected
                bot_info["status"] = "disconnected"
    
    async def _start_websocket_server(self):
        """Start WebSocket server for bot connections"""
        
        async def handle_bot_connection(websocket, path):
            bot_id = None
            try:
                # Bot registration handshake
                registration_message = await websocket.recv()
                registration_data = json.loads(registration_message)
                
                bot_id = registration_data["bot_id"]
                capabilities_data = registration_data["capabilities"]
                
                capabilities = BotCapabilityProfile(**capabilities_data)
                await self.register_bot(bot_id, capabilities, websocket)
                
                # Send confirmation
                await websocket.send(json.dumps({
                    "type": "registration_confirmed",
                    "bot_id": bot_id,
                    "network_size": len(self.connected_bots)
                }))
                
                # Handle incoming messages
                async for message_data in websocket:
                    try:
                        message_dict = json.loads(message_data)
                        # Convert to BotMessage
                        message = BotMessage(
                            message_id=message_dict["message_id"],
                            sender_id=message_dict["sender_id"],
                            recipient_id=message_dict["recipient_id"],
                            message_type=MessageType(message_dict["message_type"]),
                            priority=Priority(message_dict["priority"]),
                            timestamp=message_dict["timestamp"],
                            content=message_dict["content"],
                            route=message_dict.get("route", []),
                            ttl=message_dict.get("ttl", 10),
                            requires_ack=message_dict.get("requires_ack", False),
                            correlation_id=message_dict.get("correlation_id"),
                            task_context=message_dict.get("task_context"),
                            session_id=message_dict.get("session_id")
                        )
                        
                        await self.message_queue.put(message)
                        
                    except Exception as e:
                        logger.error(f"Error processing message from {bot_id}: {e}")
                        
            except websockets.exceptions.ConnectionClosed:
                if bot_id:
                    await self.unregister_bot(bot_id)
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                if bot_id:
                    await self.unregister_bot(bot_id)
        
        try:
            server = await websockets.serve(handle_bot_connection, "localhost", self.hub_port)
            logger.info(f"WebSocket server started on port {self.hub_port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def _periodic_maintenance(self):
        """Periodic maintenance tasks"""
        
        while self.running:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Check bot health
                await self._check_bot_health()
                
                # Clean up old collaboration sessions
                await self._cleanup_old_sessions()
                
                # Update routing table
                self._update_routing_table()
                
            except Exception as e:
                logger.error(f"Maintenance error: {e}")
    
    async def _check_bot_health(self):
        """Check health of connected bots"""
        
        current_time = datetime.now()
        
        for bot_id, bot_info in list(self.connected_bots.items()):
            last_seen = bot_info["last_seen"]
            
            # If bot hasn't been seen for 5 minutes, ping it
            if (current_time - last_seen).total_seconds() > 300:
                ping_message = BotMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id="hub",
                    recipient_id=bot_id,
                    message_type=MessageType.PING,
                    priority=Priority.LOW,
                    timestamp=time.time(),
                    content={"ping_time": time.time()},
                    requires_ack=True
                )
                
                await self.send_message(ping_message)
                
                # If no response for 10 minutes, consider disconnected
                if (current_time - last_seen).total_seconds() > 600:
                    logger.warning(f"Bot {bot_id} appears disconnected")
                    await self.unregister_bot(bot_id)
    
    async def _cleanup_old_sessions(self):
        """Clean up old collaboration sessions"""
        
        current_time = datetime.now()
        
        for session_id, session in list(self.collaboration_sessions.items()):
            # Remove completed or failed sessions older than 1 hour
            if session.status in ["completed", "failed"]:
                if (current_time - session.created_at).total_seconds() > 3600:
                    del self.collaboration_sessions[session_id]
                    logger.info(f"Cleaned up old collaboration session {session_id}")
            
            # Remove abandoned sessions older than 24 hours
            elif (current_time - session.created_at).total_seconds() > 86400:
                await self._end_collaboration_session(session_id, "Session timeout")
    
    def _update_routing_table(self):
        """Update routing table for efficient message routing"""
        
        # For now, use direct routing (all bots connect to hub)
        # In a more complex topology, this would calculate optimal paths
        
        for bot_id in self.connected_bots:
            self.routing_table[bot_id] = [bot_id]  # Direct connection
    
    def _find_bots_with_capabilities(self, required_capabilities: List[str]) -> List[str]:
        """Find bots that have the required capabilities"""
        
        suitable_bots = []
        
        for bot_id, capabilities in self.bot_capabilities.items():
            if bot_id not in self.connected_bots:
                continue
                
            bot_caps = set(capabilities.capabilities + capabilities.specializations)
            required_caps = set(required_capabilities)
            
            # Check if bot has all required capabilities
            if required_caps.issubset(bot_caps):
                suitable_bots.append(bot_id)
        
        # Sort by collaboration rating
        suitable_bots.sort(
            key=lambda bot_id: self.bot_capabilities[bot_id].collaboration_rating,
            reverse=True
        )
        
        return suitable_bots
    
    def _validate_message(self, message: BotMessage) -> bool:
        """Validate message format and content"""
        
        # Basic validation
        if not message.message_id or not message.sender_id:
            return False
        
        if message.ttl <= 0:
            return False
        
        # Check if sender is registered
        if message.sender_id != "hub" and message.sender_id not in self.connected_bots:
            logger.warning(f"Message from unregistered bot: {message.sender_id}")
            return False
        
        return True
    
    def _update_latency_stats(self, latency_ms: float):
        """Update average latency statistics"""
        
        current_avg = self.message_stats["average_latency_ms"]
        total_delivered = self.message_stats["total_delivered"]
        
        if total_delivered > 0:
            self.message_stats["average_latency_ms"] = (
                (current_avg * (total_delivered - 1) + latency_ms) / total_delivered
            )
        else:
            self.message_stats["average_latency_ms"] = latency_ms
    
    # Message Handlers
    
    async def _handle_ping(self, message: BotMessage):
        """Handle ping message"""
        
        pong_message = BotMessage(
            message_id=str(uuid.uuid4()),
            sender_id="hub",
            recipient_id=message.sender_id,
            message_type=MessageType.PONG,
            priority=Priority.LOW,
            timestamp=time.time(),
            content={
                "original_ping_time": message.content.get("ping_time"),
                "pong_time": time.time()
            },
            correlation_id=message.correlation_id
        )
        
        await self.send_message(pong_message)
    
    async def _handle_task_request(self, message: BotMessage):
        """Handle task request from bot"""
        
        # Find suitable bots for the task
        required_capabilities = message.content.get("required_capabilities", [])
        suitable_bots = self._find_bots_with_capabilities(required_capabilities)
        
        # Remove sender from candidates
        if message.sender_id in suitable_bots:
            suitable_bots.remove(message.sender_id)
        
        if not suitable_bots:
            # No suitable bots found
            response = BotMessage(
                message_id=str(uuid.uuid4()),
                sender_id="hub",
                recipient_id=message.sender_id,
                message_type=MessageType.TASK_DECLINE,
                priority=Priority.NORMAL,
                timestamp=time.time(),
                content={"reason": "No suitable bots available"},
                correlation_id=message.correlation_id
            )
            
            await self.send_message(response)
            return
        
        # Forward request to the best suitable bot
        best_bot = suitable_bots[0]
        
        forwarded_request = BotMessage(
            message_id=str(uuid.uuid4()),
            sender_id=message.sender_id,
            recipient_id=best_bot,
            message_type=MessageType.TASK_REQUEST,
            priority=message.priority,
            timestamp=time.time(),
            content=message.content,
            correlation_id=message.correlation_id
        )
        
        await self.send_message(forwarded_request)
    
    async def _handle_collaboration_join(self, message: BotMessage):
        """Handle bot joining collaboration"""
        
        session_id = message.content.get("session_id")
        bot_id = message.content.get("bot_id")
        
        if session_id and bot_id:
            await self.join_collaboration(session_id, bot_id)
    
    async def _handle_status_update(self, message: BotMessage):
        """Handle status update from bot"""
        
        bot_id = message.sender_id
        status_data = message.content
        
        # Update bot information
        if bot_id in self.connected_bots:
            self.connected_bots[bot_id]["status"] = status_data.get("status", "online")
            self.connected_bots[bot_id]["last_seen"] = datetime.now()
        
        # Update capabilities if provided
        if bot_id in self.bot_capabilities and "capabilities" in status_data:
            capabilities = self.bot_capabilities[bot_id]
            capabilities.current_load = status_data.get("current_load", 0.0)
            capabilities.available_resources = status_data.get("available_resources", {})
    
    async def _handle_error_report(self, message: BotMessage):
        """Handle error report from bot"""
        
        error_data = message.content
        logger.error(f"Bot {message.sender_id} reported error: {error_data}")
        
        # Could implement automatic error handling/recovery here
        # For now, just log and potentially notify other bots if needed
    
    async def _handle_assistance_request(self, message: BotMessage):
        """Handle assistance request from bot"""
        
        assistance_type = message.content.get("assistance_type")
        required_capabilities = message.content.get("required_capabilities", [])
        
        # Find bots that can provide assistance
        helper_bots = self._find_bots_with_capabilities(required_capabilities)
        
        # Remove requesting bot
        if message.sender_id in helper_bots:
            helper_bots.remove(message.sender_id)
        
        if helper_bots:
            # Forward assistance request to the best helper
            helper_bot = helper_bots[0]
            
            assistance_message = BotMessage(
                message_id=str(uuid.uuid4()),
                sender_id="hub",
                recipient_id=helper_bot,
                message_type=MessageType.ASSISTANCE_REQUEST,
                priority=Priority.HIGH,
                timestamp=time.time(),
                content={
                    "requesting_bot": message.sender_id,
                    "assistance_type": assistance_type,
                    "details": message.content
                },
                correlation_id=message.correlation_id
            )
            
            await self.send_message(assistance_message)
    
    async def _end_collaboration_session(self, session_id: str, reason: str):
        """End a collaboration session"""
        
        session = self.collaboration_sessions.get(session_id)
        if not session:
            return
        
        session.status = "completed"
        
        # Notify all participants
        end_message = BotMessage(
            message_id=str(uuid.uuid4()),
            sender_id="hub",
            recipient_id="*",
            message_type=MessageType.COLLABORATION_LEAVE,
            priority=Priority.NORMAL,
            timestamp=time.time(),
            content={
                "session_id": session_id,
                "reason": reason,
                "action": "session_ended"
            },
            session_id=session_id
        )
        
        await self._broadcast_to_session(session_id, end_message)
        
        logger.info(f"Collaboration session {session_id} ended: {reason}")
    
    # Public API Methods
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        
        return {
            "connected_bots": len(self.connected_bots),
            "active_collaborations": len([s for s in self.collaboration_sessions.values() if s.status == "active"]),
            "message_stats": self.message_stats.copy(),
            "network_health": "healthy" if len(self.connected_bots) > 0 else "empty"
        }
    
    def get_bot_directory(self) -> List[Dict[str, Any]]:
        """Get directory of all connected bots"""
        
        directory = []
        
        for bot_id, capabilities in self.bot_capabilities.items():
            bot_info = self.connected_bots.get(bot_id, {})
            
            directory.append({
                "bot_id": bot_id,
                "name": capabilities.name,
                "capabilities": capabilities.capabilities,
                "specializations": capabilities.specializations,
                "status": bot_info.get("status", "offline"),
                "current_load": capabilities.current_load,
                "collaboration_rating": capabilities.collaboration_rating,
                "connected_at": bot_info.get("connected_at", "").isoformat() if bot_info.get("connected_at") else "",
                "message_count": bot_info.get("message_count", 0)
            })
        
        return directory
    
    def get_collaboration_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active collaboration sessions"""
        
        sessions = []
        
        for session_id, session in self.collaboration_sessions.items():
            sessions.append({
                "session_id": session_id,
                "task_id": session.task_id,
                "participants": session.participants,
                "leader_bot_id": session.leader_bot_id,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "current_phase": session.current_phase,
                "completion_percentage": session.completion_percentage,
                "participant_count": len(session.participants)
            })
        
        return sessions