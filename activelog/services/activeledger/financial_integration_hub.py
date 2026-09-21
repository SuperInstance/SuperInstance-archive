# Financial Integration Hub
# Connects all financial services to ActiveLedger

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

class FinancialServiceType(Enum):
    ADS = "ads"
    BLOCKCHAIN = "blockchain" 
    DMLOG_MARKETPLACE = "dmlog-marketplace"
    AI_MARKETPLACE = "ai-marketplace"
    PAYMENT_GATEWAY = "payment-gateway"
    AFFILIATE = "affiliate"
    EXCHANGE_RATES = "exchange-rates"

@dataclass
class FinancialTransaction:
    transaction_id: str
    service: str
    type: str  # credit, debit, transfer, commission, refund
    amount: float
    currency: str
    description: str
    metadata: Dict[str, Any]
    timestamp: str
    status: str = "pending"  # pending, processed, failed, cancelled
    
@dataclass
class ServiceEndpoint:
    name: str
    service_type: FinancialServiceType
    base_url: str
    port: int
    auth_type: str = "none"  # none, api_key, oauth
    auth_credentials: Dict[str, str] = None
    priority: int = 1

class FinancialIntegrationHub:
    """Central hub managing all financial services integration with ActiveLedger"""
    
    def __init__(self, activeledger_url: str = "http://activeledger.activelog:8122"):
        self.activeledger_url = activeledger_url
        self.services = {}
        self.transaction_queue = []
        self.processed_transactions = {}
        self.balance_cache = {}
        self.setup_services()
        
    def setup_services(self):
        """Initialize all financial service endpoints"""
        
        # Ads Service
        self.services[FinancialServiceType.ADS] = ServiceEndpoint(
            name="ads",
            service_type=FinancialServiceType.ADS,
            base_url="http://ads.activelog",
            port=8141,
            priority=2
        )
        
        # Blockchain Service
        self.services[FinancialServiceType.BLOCKCHAIN] = ServiceEndpoint(
            name="blockchain",
            service_type=FinancialServiceType.BLOCKCHAIN,
            base_url="http://blockchain.activelog",
            port=8121,
            priority=1
        )
        
        # DMLog Marketplace
        self.services[FinancialServiceType.DMLOG_MARKETPLACE] = ServiceEndpoint(
            name="dmlog-marketplace",
            service_type=FinancialServiceType.DMLOG_MARKETPLACE,
            base_url="http://dmlog-marketplace.activelog",
            port=8076,
            priority=2
        )
        
        # AI Marketplace (part of ai-tools)
        self.services[FinancialServiceType.AI_MARKETPLACE] = ServiceEndpoint(
            name="ai-marketplace",
            service_type=FinancialServiceType.AI_MARKETPLACE,
            base_url="http://ai-tools.activelog",
            port=8031,
            priority=2
        )

    async def register_transaction(self, service: str, transaction_type: str, 
                                 amount: float, currency: str = "USD", 
                                 description: str = "", metadata: Dict[str, Any] = None) -> str:
        """Register a new financial transaction"""
        
        transaction_id = str(uuid.uuid4())
        transaction = FinancialTransaction(
            transaction_id=transaction_id,
            service=service,
            type=transaction_type,
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata or {},
            timestamp=datetime.utcnow().isoformat(),
            status="pending"
        )
        
        # Add to queue for processing
        self.transaction_queue.append(transaction)
        
        # Send to ActiveLedger immediately
        try:
            result = await self.send_to_activeledger(transaction)
            transaction.status = "processed" if result.get("success") else "failed"
            self.processed_transactions[transaction_id] = transaction
        except Exception as e:
            logger.error(f"Failed to process transaction {transaction_id}: {e}")
            transaction.status = "failed"
            
        return transaction_id

    async def send_to_activeledger(self, transaction: FinancialTransaction) -> Dict[str, Any]:
        """Send transaction to ActiveLedger for processing"""
        
        payload = {
            "transaction_id": transaction.transaction_id,
            "service": transaction.service,
            "type": transaction.type,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "description": transaction.description,
            "metadata": transaction.metadata,
            "timestamp": transaction.timestamp
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.activeledger_url}/api/v1/transactions"
                timeout = aiohttp.ClientTimeout(total=10)
                
                async with session.post(url, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Transaction {transaction.transaction_id} processed successfully")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"ActiveLedger rejected transaction: {response.status} - {error_text}")
                        return {"success": False, "error": error_text}
                        
            except Exception as e:
                logger.error(f"Failed to send transaction to ActiveLedger: {e}")
                return {"success": False, "error": str(e)}

    async def process_ad_revenue(self, ad_data: Dict[str, Any]) -> str:
        """Process ad revenue from ads service"""
        
        revenue = ad_data.get("revenue", 0)
        impressions = ad_data.get("impressions", 0)
        clicks = ad_data.get("clicks", 0)
        advertiser = ad_data.get("advertiser", "unknown")
        
        # Calculate commission (10% platform fee)
        platform_commission = revenue * 0.10
        creator_payment = revenue - platform_commission
        
        # Register platform commission
        commission_tx = await self.register_transaction(
            service="ads",
            transaction_type="commission",
            amount=platform_commission,
            description=f"Platform commission from {advertiser} ads",
            metadata={
                "advertiser": advertiser,
                "impressions": impressions,
                "clicks": clicks,
                "commission_rate": 0.10
            }
        )
        
        # Register creator payment
        creator_tx = await self.register_transaction(
            service="ads",
            transaction_type="creator_payment",
            amount=creator_payment,
            description=f"Creator payment from {advertiser} ads",
            metadata={
                "advertiser": advertiser,
                "impressions": impressions,
                "clicks": clicks,
                "creator_id": ad_data.get("creator_id", "unknown")
            }
        )
        
        return {"commission_tx": commission_tx, "creator_tx": creator_tx}

    async def process_marketplace_transaction(self, marketplace: str, transaction_data: Dict[str, Any]) -> str:
        """Process marketplace transactions (DMLog, AI models, etc.)"""
        
        item_price = transaction_data.get("price", 0)
        seller_id = transaction_data.get("seller_id")
        buyer_id = transaction_data.get("buyer_id")
        item_type = transaction_data.get("item_type", "unknown")
        
        # Calculate fees
        if marketplace == "dmlog":
            platform_fee_rate = 0.15  # 15% for DMLog marketplace
        elif marketplace == "ai":
            platform_fee_rate = 0.20  # 20% for AI model marketplace
        else:
            platform_fee_rate = 0.10  # Default 10%
            
        platform_fee = item_price * platform_fee_rate
        seller_payment = item_price - platform_fee
        
        # Process buyer charge
        buyer_charge_tx = await self.register_transaction(
            service=f"{marketplace}-marketplace",
            transaction_type="purchase",
            amount=-item_price,  # Negative for charge
            description=f"Purchase of {item_type} from {marketplace} marketplace",
            metadata={
                "buyer_id": buyer_id,
                "seller_id": seller_id,
                "item_type": item_type,
                "marketplace": marketplace
            }
        )
        
        # Process seller payment
        seller_payment_tx = await self.register_transaction(
            service=f"{marketplace}-marketplace",
            transaction_type="sale",
            amount=seller_payment,
            description=f"Sale of {item_type} in {marketplace} marketplace",
            metadata={
                "seller_id": seller_id,
                "buyer_id": buyer_id,
                "item_type": item_type,
                "marketplace": marketplace,
                "platform_fee": platform_fee
            }
        )
        
        # Process platform fee
        platform_fee_tx = await self.register_transaction(
            service=f"{marketplace}-marketplace",
            transaction_type="platform_fee",
            amount=platform_fee,
            description=f"Platform fee from {marketplace} marketplace sale",
            metadata={
                "seller_id": seller_id,
                "item_type": item_type,
                "marketplace": marketplace,
                "fee_rate": platform_fee_rate
            }
        )
        
        return {
            "buyer_charge": buyer_charge_tx,
            "seller_payment": seller_payment_tx,
            "platform_fee": platform_fee_tx
        }

    async def process_blockchain_transaction(self, blockchain_data: Dict[str, Any]) -> str:
        """Process blockchain-related transactions"""
        
        tx_type = blockchain_data.get("type", "transfer")
        amount = blockchain_data.get("amount", 0)
        from_address = blockchain_data.get("from")
        to_address = blockchain_data.get("to")
        contract_address = blockchain_data.get("contract")
        
        # Calculate gas fees
        gas_fee = blockchain_data.get("gas_fee", amount * 0.001)  # Default 0.1%
        
        # Register the blockchain transaction
        blockchain_tx = await self.register_transaction(
            service="blockchain",
            transaction_type=tx_type,
            amount=amount,
            currency="ACTV",  # ActiveLog token
            description=f"Blockchain {tx_type} transaction",
            metadata={
                "from_address": from_address,
                "to_address": to_address,
                "contract_address": contract_address,
                "gas_fee": gas_fee,
                "blockchain": "activeledger"
            }
        )
        
        # Register gas fee if applicable
        if gas_fee > 0:
            gas_tx = await self.register_transaction(
                service="blockchain",
                transaction_type="gas_fee",
                amount=gas_fee,
                currency="ACTV",
                description="Gas fee for blockchain transaction",
                metadata={
                    "parent_tx": blockchain_tx,
                    "from_address": from_address,
                    "gas_price": blockchain_data.get("gas_price", 0)
                }
            )
            return {"main_tx": blockchain_tx, "gas_tx": gas_tx}
        
        return {"main_tx": blockchain_tx}

    async def get_service_balance(self, service: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get balance information for a specific service"""
        
        cache_key = f"balance:{service}"
        
        # Check cache first
        if not force_refresh and cache_key in self.balance_cache:
            cached_data = self.balance_cache[cache_key]
            cache_age = datetime.utcnow() - datetime.fromisoformat(cached_data["cached_at"])
            if cache_age < timedelta(minutes=5):  # Cache for 5 minutes
                return cached_data["data"]
        
        # Fetch from ActiveLedger
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.activeledger_url}/api/v1/balance/{service}"
                timeout = aiohttp.ClientTimeout(total=5)
                
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        balance_data = await response.json()
                        
                        # Cache the result
                        self.balance_cache[cache_key] = {
                            "data": balance_data,
                            "cached_at": datetime.utcnow().isoformat()
                        }
                        
                        return balance_data
                    else:
                        logger.error(f"Failed to get balance for {service}: {response.status}")
                        return {"error": f"HTTP {response.status}"}
                        
            except Exception as e:
                logger.error(f"Error fetching balance for {service}: {e}")
                return {"error": str(e)}

    async def get_financial_summary(self) -> Dict[str, Any]:
        """Get overall financial summary across all services"""
        
        summary = {
            "total_transactions": len(self.processed_transactions),
            "pending_transactions": len([t for t in self.transaction_queue if t.status == "pending"]),
            "services": {},
            "currency_totals": {},
            "transaction_types": {},
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Analyze processed transactions
        for tx in self.processed_transactions.values():
            service = tx.service
            currency = tx.currency
            tx_type = tx.type
            
            # Service breakdown
            if service not in summary["services"]:
                summary["services"][service] = {
                    "transaction_count": 0,
                    "total_amount": 0,
                    "currencies": {}
                }
            
            summary["services"][service]["transaction_count"] += 1
            summary["services"][service]["total_amount"] += tx.amount
            
            if currency not in summary["services"][service]["currencies"]:
                summary["services"][service]["currencies"][currency] = 0
            summary["services"][service]["currencies"][currency] += tx.amount
            
            # Currency totals
            if currency not in summary["currency_totals"]:
                summary["currency_totals"][currency] = 0
            summary["currency_totals"][currency] += tx.amount
            
            # Transaction type breakdown
            if tx_type not in summary["transaction_types"]:
                summary["transaction_types"][tx_type] = 0
            summary["transaction_types"][tx_type] += 1
        
        return summary

    async def health_check(self) -> Dict[str, Any]:
        """Check health of financial integration hub"""
        
        health_status = {
            "status": "healthy",
            "services": {},
            "activeledger_connection": "unknown",
            "queue_size": len(self.transaction_queue),
            "processed_count": len(self.processed_transactions),
            "cache_size": len(self.balance_cache),
            "checked_at": datetime.utcnow().isoformat()
        }
        
        # Check ActiveLedger connection
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=3)
                async with session.get(f"{self.activeledger_url}/health", timeout=timeout) as response:
                    if response.status == 200:
                        health_status["activeledger_connection"] = "healthy"
                    else:
                        health_status["activeledger_connection"] = f"error_{response.status}"
                        health_status["status"] = "degraded"
        except Exception as e:
            health_status["activeledger_connection"] = f"unreachable: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check individual services
        async with aiohttp.ClientSession() as session:
            for service_type, service in self.services.items():
                try:
                    url = f"{service.base_url}:{service.port}/health"
                    timeout = aiohttp.ClientTimeout(total=3)
                    
                    async with session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            health_status["services"][service.name] = "healthy"
                        else:
                            health_status["services"][service.name] = f"error_{response.status}"
                            
                except Exception as e:
                    health_status["services"][service.name] = f"unreachable: {str(e)}"
        
        # Determine overall status
        unhealthy_services = [s for s in health_status["services"].values() if not s == "healthy"]
        if len(unhealthy_services) > len(health_status["services"]) / 2:
            health_status["status"] = "unhealthy"
        elif len(unhealthy_services) > 0:
            health_status["status"] = "degraded"
        
        return health_status

# Integration endpoints for individual services

class AdsIntegration:
    """Integration layer for ads service"""
    
    def __init__(self, financial_hub: FinancialIntegrationHub):
        self.hub = financial_hub
        
    async def process_impression(self, ad_id: str, advertiser: str, revenue: float):
        """Process ad impression revenue"""
        return await self.hub.process_ad_revenue({
            "ad_id": ad_id,
            "advertiser": advertiser,
            "revenue": revenue,
            "impressions": 1,
            "clicks": 0
        })
        
    async def process_click(self, ad_id: str, advertiser: str, revenue: float):
        """Process ad click revenue"""
        return await self.hub.process_ad_revenue({
            "ad_id": ad_id,
            "advertiser": advertiser,
            "revenue": revenue,
            "impressions": 0,
            "clicks": 1
        })

class MarketplaceIntegration:
    """Integration layer for marketplace services"""
    
    def __init__(self, financial_hub: FinancialIntegrationHub):
        self.hub = financial_hub
        
    async def process_dmlog_sale(self, item_data: Dict[str, Any]):
        """Process DMLog marketplace sale"""
        return await self.hub.process_marketplace_transaction("dmlog", item_data)
        
    async def process_ai_model_sale(self, model_data: Dict[str, Any]):
        """Process AI model marketplace sale"""
        return await self.hub.process_marketplace_transaction("ai", model_data)

class BlockchainIntegration:
    """Integration layer for blockchain service"""
    
    def __init__(self, financial_hub: FinancialIntegrationHub):
        self.hub = financial_hub
        
    async def process_transfer(self, from_addr: str, to_addr: str, amount: float):
        """Process blockchain transfer"""
        return await self.hub.process_blockchain_transaction({
            "type": "transfer",
            "from": from_addr,
            "to": to_addr,
            "amount": amount
        })
        
    async def process_smart_contract(self, contract_addr: str, function: str, amount: float):
        """Process smart contract transaction"""
        return await self.hub.process_blockchain_transaction({
            "type": "contract_call",
            "contract": contract_addr,
            "function": function,
            "amount": amount
        })