# Financial Integration API
# FastAPI endpoints for financial service integrations

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pydantic import BaseModel, Field
import asyncio

from financial_integration_hub import (
    FinancialIntegrationHub, AdsIntegration, 
    MarketplaceIntegration, BlockchainIntegration
)

logger = logging.getLogger(__name__)

# Pydantic models for API requests

class TransactionRequest(BaseModel):
    service: str
    transaction_type: str
    amount: float
    currency: str = "USD"
    description: str = ""
    metadata: Optional[Dict[str, Any]] = None

class AdRevenueRequest(BaseModel):
    ad_id: str
    advertiser: str
    revenue: float
    impressions: int = 0
    clicks: int = 0
    creator_id: Optional[str] = None

class MarketplaceTransactionRequest(BaseModel):
    marketplace: str  # dmlog, ai
    item_type: str
    price: float
    seller_id: str
    buyer_id: str
    item_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BlockchainTransactionRequest(BaseModel):
    transaction_type: str = "transfer"
    amount: float
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    contract_address: Optional[str] = None
    gas_price: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

# FastAPI app
app = FastAPI(
    title="ActiveLedger Financial Integration API",
    description="Financial integration hub connecting all services to ActiveLedger",
    version="1.0.0"
)

# Global instances
financial_hub = None
ads_integration = None
marketplace_integration = None
blockchain_integration = None

@app.on_event("startup")
async def startup_event():
    """Initialize financial integrations on startup"""
    global financial_hub, ads_integration, marketplace_integration, blockchain_integration
    
    try:
        # Initialize financial hub
        financial_hub = FinancialIntegrationHub()
        
        # Initialize service integrations
        ads_integration = AdsIntegration(financial_hub)
        marketplace_integration = MarketplaceIntegration(financial_hub)
        blockchain_integration = BlockchainIntegration(financial_hub)
        
        logger.info("Financial integration hub initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize financial hub: {e}")
        raise

# Dependency to get financial hub
def get_financial_hub() -> FinancialIntegrationHub:
    if financial_hub is None:
        raise HTTPException(status_code=503, detail="Financial hub not initialized")
    return financial_hub

# Health and status endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if financial_hub:
        health_status = await financial_hub.health_check()
        if health_status["status"] == "healthy":
            return health_status
        else:
            return JSONResponse(
                status_code=503,
                content=health_status
            )
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Financial hub not initialized"}
        )

@app.get("/status")
async def get_status(hub: FinancialIntegrationHub = Depends(get_financial_hub)):
    """Get financial hub status and statistics"""
    summary = await hub.get_financial_summary()
    return summary

# Core transaction endpoints

@app.post("/transactions")
async def create_transaction(
    request: TransactionRequest,
    background_tasks: BackgroundTasks,
    hub: FinancialIntegrationHub = Depends(get_financial_hub)
):
    """Create a new financial transaction"""
    try:
        transaction_id = await hub.register_transaction(
            service=request.service,
            transaction_type=request.transaction_type,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "service": request.service,
            "amount": request.amount,
            "currency": request.currency,
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    hub: FinancialIntegrationHub = Depends(get_financial_hub)
):
    """Get transaction details"""
    if transaction_id in hub.processed_transactions:
        transaction = hub.processed_transactions[transaction_id]
        return {
            "transaction_id": transaction.transaction_id,
            "service": transaction.service,
            "type": transaction.type,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "description": transaction.description,
            "metadata": transaction.metadata,
            "timestamp": transaction.timestamp,
            "status": transaction.status
        }
    else:
        raise HTTPException(status_code=404, detail="Transaction not found")

@app.get("/balance/{service}")
async def get_service_balance(
    service: str,
    force_refresh: bool = False,
    hub: FinancialIntegrationHub = Depends(get_financial_hub)
):
    """Get balance for a specific service"""
    balance = await hub.get_service_balance(service, force_refresh)
    return balance

# Ads service integration endpoints

@app.post("/ads/impression")
async def process_ad_impression(
    request: AdRevenueRequest,
    background_tasks: BackgroundTasks
):
    """Process ad impression revenue"""
    if not ads_integration:
        raise HTTPException(status_code=503, detail="Ads integration not available")
    
    try:
        result = await ads_integration.process_impression(
            request.ad_id,
            request.advertiser,
            request.revenue
        )
        
        return {
            "success": True,
            "ad_id": request.ad_id,
            "revenue": request.revenue,
            "transactions": result,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process ad impression: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ads/click")
async def process_ad_click(
    request: AdRevenueRequest,
    background_tasks: BackgroundTasks
):
    """Process ad click revenue"""
    if not ads_integration:
        raise HTTPException(status_code=503, detail="Ads integration not available")
    
    try:
        result = await ads_integration.process_click(
            request.ad_id,
            request.advertiser,
            request.revenue
        )
        
        return {
            "success": True,
            "ad_id": request.ad_id,
            "revenue": request.revenue,
            "transactions": result,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process ad click: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Marketplace integration endpoints

@app.post("/marketplace/dmlog/sale")
async def process_dmlog_sale(
    request: MarketplaceTransactionRequest,
    background_tasks: BackgroundTasks
):
    """Process DMLog marketplace sale"""
    if not marketplace_integration:
        raise HTTPException(status_code=503, detail="Marketplace integration not available")
    
    try:
        item_data = {
            "price": request.price,
            "seller_id": request.seller_id,
            "buyer_id": request.buyer_id,
            "item_type": request.item_type,
            "item_id": request.item_id,
            "metadata": request.metadata
        }
        
        result = await marketplace_integration.process_dmlog_sale(item_data)
        
        return {
            "success": True,
            "marketplace": "dmlog",
            "item_type": request.item_type,
            "price": request.price,
            "transactions": result,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process DMLog sale: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/marketplace/ai/sale")
async def process_ai_model_sale(
    request: MarketplaceTransactionRequest,
    background_tasks: BackgroundTasks
):
    """Process AI model marketplace sale"""
    if not marketplace_integration:
        raise HTTPException(status_code=503, detail="Marketplace integration not available")
    
    try:
        model_data = {
            "price": request.price,
            "seller_id": request.seller_id,
            "buyer_id": request.buyer_id,
            "item_type": request.item_type,
            "item_id": request.item_id,
            "metadata": request.metadata
        }
        
        result = await marketplace_integration.process_ai_model_sale(model_data)
        
        return {
            "success": True,
            "marketplace": "ai",
            "item_type": request.item_type,
            "price": request.price,
            "transactions": result,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process AI model sale: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Blockchain integration endpoints

@app.post("/blockchain/transfer")
async def process_blockchain_transfer(
    request: BlockchainTransactionRequest,
    background_tasks: BackgroundTasks
):
    """Process blockchain transfer"""
    if not blockchain_integration:
        raise HTTPException(status_code=503, detail="Blockchain integration not available")
    
    try:
        if not request.from_address or not request.to_address:
            raise HTTPException(status_code=400, detail="From and to addresses are required for transfer")
        
        result = await blockchain_integration.process_transfer(
            request.from_address,
            request.to_address,
            request.amount
        )
        
        return {
            "success": True,
            "type": "transfer",
            "amount": request.amount,
            "from": request.from_address,
            "to": request.to_address,
            "transactions": result,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process blockchain transfer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/blockchain/contract")
async def process_smart_contract(
    request: BlockchainTransactionRequest,
    background_tasks: BackgroundTasks
):
    """Process smart contract transaction"""
    if not blockchain_integration:
        raise HTTPException(status_code=503, detail="Blockchain integration not available")
    
    try:
        if not request.contract_address:
            raise HTTPException(status_code=400, detail="Contract address is required")
        
        result = await blockchain_integration.process_smart_contract(
            request.contract_address,
            request.metadata.get("function", "unknown") if request.metadata else "unknown",
            request.amount
        )
        
        return {
            "success": True,
            "type": "contract_call",
            "amount": request.amount,
            "contract": request.contract_address,
            "transactions": result,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process smart contract: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Batch processing endpoints

@app.post("/batch/transactions")
async def process_batch_transactions(
    requests: List[TransactionRequest],
    background_tasks: BackgroundTasks,
    hub: FinancialIntegrationHub = Depends(get_financial_hub)
):
    """Process multiple transactions in batch"""
    try:
        results = []
        
        for i, request in enumerate(requests):
            try:
                transaction_id = await hub.register_transaction(
                    service=request.service,
                    transaction_type=request.transaction_type,
                    amount=request.amount,
                    currency=request.currency,
                    description=request.description,
                    metadata=request.metadata
                )
                
                results.append({
                    "index": i,
                    "status": "success",
                    "transaction_id": transaction_id,
                    "service": request.service,
                    "amount": request.amount
                })
                
            except Exception as e:
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(e),
                    "service": request.service
                })
        
        # Summary
        successful = len([r for r in results if r["status"] == "success"])
        failed = len(results) - successful
        
        return {
            "success": True,
            "results": results,
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed,
                "success_rate": successful / len(results) * 100 if results else 0
            },
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch transaction processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics and reporting endpoints

@app.get("/analytics/summary")
async def get_analytics_summary(
    service: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    hub: FinancialIntegrationHub = Depends(get_financial_hub)
):
    """Get financial analytics summary"""
    summary = await hub.get_financial_summary()
    
    # Filter by service if specified
    if service and service in summary["services"]:
        return {
            "service": service,
            "data": summary["services"][service],
            "generated_at": summary["generated_at"]
        }
    
    return summary

@app.get("/analytics/services")
async def get_service_analytics(hub: FinancialIntegrationHub = Depends(get_financial_hub)):
    """Get per-service financial analytics"""
    summary = await hub.get_financial_summary()
    
    # Enhanced service analytics
    service_analytics = {}
    for service, data in summary["services"].items():
        service_analytics[service] = {
            **data,
            "average_transaction": data["total_amount"] / data["transaction_count"] if data["transaction_count"] > 0 else 0,
            "primary_currency": max(data["currencies"].items(), key=lambda x: x[1])[0] if data["currencies"] else "USD"
        }
    
    return {
        "services": service_analytics,
        "total_services": len(service_analytics),
        "generated_at": summary["generated_at"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8123)