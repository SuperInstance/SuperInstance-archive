#!/usr/bin/env python3
"""
ActiveLedger Settlement Server
Transaction finalization and settlement system
Instance: t3.large
"""

import asyncio
import json
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import aioredis
from cryptography.fernet import Fernet
import sqlite3
import hashlib
import hmac
import os

app = FastAPI(title="ActiveLedger Settlement Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dataclass
class Settlement:
    id: str
    trade_id: str
    buyer_id: str
    seller_id: str
    symbol: str
    quantity: Decimal
    price: Decimal
    total_amount: Decimal
    fees: Decimal
    net_amount: Decimal
    status: str  # 'pending', 'processing', 'settled', 'failed'
    timestamp: float
    settlement_timestamp: Optional[float] = None
    error_message: Optional[str] = None

@dataclass
class WalletBalance:
    user_id: str
    currency: str
    available_balance: Decimal
    locked_balance: Decimal
    total_balance: Decimal
    last_updated: float

class SettlementEngine:
    def __init__(self):
        self.redis_client = None
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.fee_rate = Decimal('0.001')  # 0.1% transaction fee
        self.db_path = "data/settlement.db"
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for settlements"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Settlements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settlements (
                id TEXT PRIMARY KEY,
                trade_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity TEXT NOT NULL,
                price TEXT NOT NULL,
                total_amount TEXT NOT NULL,
                fees TEXT NOT NULL,
                net_amount TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp REAL NOT NULL,
                settlement_timestamp REAL,
                error_message TEXT
            )
        ''')
        
        # Wallet balances table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet_balances (
                user_id TEXT NOT NULL,
                currency TEXT NOT NULL,
                available_balance TEXT NOT NULL,
                locked_balance TEXT NOT NULL,
                total_balance TEXT NOT NULL,
                last_updated REAL NOT NULL,
                PRIMARY KEY (user_id, currency)
            )
        ''')
        
        # Transaction history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                currency TEXT NOT NULL,
                amount TEXT NOT NULL,
                reference_id TEXT,
                timestamp REAL NOT NULL,
                description TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def initialize_redis(self):
        self.redis_client = await aioredis.from_url("redis://localhost:6379")
    
    def get_wallet_balance(self, user_id: str, currency: str) -> WalletBalance:
        """Get wallet balance for user and currency"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT available_balance, locked_balance, total_balance, last_updated
            FROM wallet_balances 
            WHERE user_id = ? AND currency = ?
        ''', (user_id, currency))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return WalletBalance(
                user_id=user_id,
                currency=currency,
                available_balance=Decimal(row[0]),
                locked_balance=Decimal(row[1]),
                total_balance=Decimal(row[2]),
                last_updated=row[3]
            )
        else:
            # Create new wallet with zero balance
            balance = WalletBalance(
                user_id=user_id,
                currency=currency,
                available_balance=Decimal('0'),
                locked_balance=Decimal('0'),
                total_balance=Decimal('0'),
                last_updated=time.time()
            )
            self.update_wallet_balance(balance)
            return balance
    
    def update_wallet_balance(self, balance: WalletBalance):
        """Update wallet balance in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO wallet_balances 
            (user_id, currency, available_balance, locked_balance, total_balance, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            balance.user_id,
            balance.currency,
            str(balance.available_balance),
            str(balance.locked_balance),
            str(balance.total_balance),
            balance.last_updated
        ))
        
        conn.commit()
        conn.close()
    
    def lock_funds(self, user_id: str, currency: str, amount: Decimal) -> bool:
        """Lock funds for pending settlement"""
        balance = self.get_wallet_balance(user_id, currency)
        
        if balance.available_balance >= amount:
            balance.available_balance -= amount
            balance.locked_balance += amount
            balance.last_updated = time.time()
            self.update_wallet_balance(balance)
            
            # Record transaction
            self.record_transaction(
                user_id=user_id,
                transaction_type='lock',
                currency=currency,
                amount=amount,
                description=f'Funds locked for settlement'
            )
            
            return True
        return False
    
    def unlock_funds(self, user_id: str, currency: str, amount: Decimal):
        """Unlock funds (e.g., failed settlement)"""
        balance = self.get_wallet_balance(user_id, currency)
        
        balance.available_balance += amount
        balance.locked_balance -= amount
        balance.last_updated = time.time()
        self.update_wallet_balance(balance)
        
        # Record transaction
        self.record_transaction(
            user_id=user_id,
            transaction_type='unlock',
            currency=currency,
            amount=amount,
            description=f'Funds unlocked from settlement'
        )
    
    def transfer_funds(self, from_user: str, to_user: str, currency: str, amount: Decimal):
        """Transfer funds between users"""
        from_balance = self.get_wallet_balance(from_user, currency)
        to_balance = self.get_wallet_balance(to_user, currency)
        
        # Deduct from sender's locked balance
        from_balance.locked_balance -= amount
        from_balance.total_balance -= amount
        from_balance.last_updated = time.time()
        
        # Add to receiver's available balance
        to_balance.available_balance += amount
        to_balance.total_balance += amount
        to_balance.last_updated = time.time()
        
        # Update both balances
        self.update_wallet_balance(from_balance)
        self.update_wallet_balance(to_balance)
        
        # Record transactions
        self.record_transaction(
            user_id=from_user,
            transaction_type='debit',
            currency=currency,
            amount=amount,
            description=f'Transfer to {to_user}'
        )
        
        self.record_transaction(
            user_id=to_user,
            transaction_type='credit',
            currency=currency,
            amount=amount,
            description=f'Transfer from {from_user}'
        )
    
    def record_transaction(self, user_id: str, transaction_type: str, currency: str, 
                          amount: Decimal, description: str, reference_id: str = None):
        """Record transaction in history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transaction_history 
            (id, user_id, type, currency, amount, reference_id, timestamp, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            user_id,
            transaction_type,
            currency,
            str(amount),
            reference_id,
            time.time(),
            description
        ))
        
        conn.commit()
        conn.close()
    
    def calculate_fees(self, amount: Decimal) -> Decimal:
        """Calculate transaction fees"""
        return (amount * self.fee_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    async def create_settlement(self, trade_data: dict) -> Settlement:
        """Create settlement from trade data"""
        total_amount = Decimal(str(trade_data['quantity'])) * Decimal(str(trade_data['price']))
        fees = self.calculate_fees(total_amount)
        net_amount = total_amount - fees
        
        settlement = Settlement(
            id=str(uuid.uuid4()),
            trade_id=trade_data['trade_id'],
            buyer_id=trade_data['buyer_id'],
            seller_id=trade_data['seller_id'],
            symbol=trade_data['symbol'],
            quantity=Decimal(str(trade_data['quantity'])),
            price=Decimal(str(trade_data['price'])),
            total_amount=total_amount,
            fees=fees,
            net_amount=net_amount,
            status='pending',
            timestamp=time.time()
        )
        
        # Store settlement in database
        self.store_settlement(settlement)
        
        return settlement
    
    def store_settlement(self, settlement: Settlement):
        """Store settlement in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO settlements 
            (id, trade_id, buyer_id, seller_id, symbol, quantity, price, 
             total_amount, fees, net_amount, status, timestamp, settlement_timestamp, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            settlement.id,
            settlement.trade_id,
            settlement.buyer_id,
            settlement.seller_id,
            settlement.symbol,
            str(settlement.quantity),
            str(settlement.price),
            str(settlement.total_amount),
            str(settlement.fees),
            str(settlement.net_amount),
            settlement.status,
            settlement.timestamp,
            settlement.settlement_timestamp,
            settlement.error_message
        ))
        
        conn.commit()
        conn.close()
    
    def update_settlement_status(self, settlement_id: str, status: str, 
                                error_message: str = None):
        """Update settlement status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        settlement_timestamp = time.time() if status == 'settled' else None
        
        cursor.execute('''
            UPDATE settlements 
            SET status = ?, settlement_timestamp = ?, error_message = ?
            WHERE id = ?
        ''', (status, settlement_timestamp, error_message, settlement_id))
        
        conn.commit()
        conn.close()
    
    async def process_settlement(self, settlement: Settlement) -> bool:
        """Process settlement with security checks"""
        try:
            # Update status to processing
            self.update_settlement_status(settlement.id, 'processing')
            
            # Check if buyer has sufficient funds
            buyer_balance = self.get_wallet_balance(settlement.buyer_id, 'CC')
            if buyer_balance.available_balance < settlement.total_amount:
                self.update_settlement_status(
                    settlement.id, 
                    'failed', 
                    'Insufficient funds'
                )
                return False
            
            # Lock buyer's funds
            if not self.lock_funds(settlement.buyer_id, 'CC', settlement.total_amount):
                self.update_settlement_status(
                    settlement.id, 
                    'failed', 
                    'Failed to lock funds'
                )
                return False
            
            # Transfer asset from seller to buyer
            # (In real implementation, this would involve asset registry)
            
            # Transfer payment from buyer to seller (minus fees)
            self.transfer_funds(
                from_user=settlement.buyer_id,
                to_user=settlement.seller_id,
                currency='CC',
                amount=settlement.net_amount
            )
            
            # Transfer fees to system wallet
            system_wallet = 'system'
            system_balance = self.get_wallet_balance(system_wallet, 'CC')
            system_balance.available_balance += settlement.fees
            system_balance.total_balance += settlement.fees
            system_balance.last_updated = time.time()
            self.update_wallet_balance(system_balance)
            
            # Mark settlement as completed
            self.update_settlement_status(settlement.id, 'settled')
            
            # Notify audit logger
            if self.redis_client:
                audit_data = {
                    'event': 'settlement_completed',
                    'settlement_id': settlement.id,
                    'trade_id': settlement.trade_id,
                    'amount': str(settlement.total_amount),
                    'fees': str(settlement.fees),
                    'timestamp': time.time()
                }
                await self.redis_client.publish('audit_log', json.dumps(audit_data))
            
            return True
            
        except Exception as e:
            self.update_settlement_status(
                settlement.id, 
                'failed', 
                str(e)
            )
            
            # Unlock funds if they were locked
            try:
                self.unlock_funds(settlement.buyer_id, 'CC', settlement.total_amount)
            except:
                pass
                
            return False

# Initialize settlement engine
settlement_engine = SettlementEngine()

@app.on_event("startup")
async def startup_event():
    await settlement_engine.initialize_redis()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "settlement-server"}

@app.post("/api/settlements")
async def create_settlement(trade_data: dict, background_tasks: BackgroundTasks):
    """Create and process settlement"""
    settlement = await settlement_engine.create_settlement(trade_data)
    
    # Process settlement in background
    background_tasks.add_task(settlement_engine.process_settlement, settlement)
    
    return {"success": True, "settlement_id": settlement.id, "data": asdict(settlement)}

@app.get("/api/settlements/{settlement_id}")
async def get_settlement(settlement_id: str):
    """Get settlement by ID"""
    conn = sqlite3.connect(settlement_engine.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM settlements WHERE id = ?', (settlement_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Settlement not found")
    
    columns = ['id', 'trade_id', 'buyer_id', 'seller_id', 'symbol', 'quantity', 
              'price', 'total_amount', 'fees', 'net_amount', 'status', 'timestamp',
              'settlement_timestamp', 'error_message']
    
    settlement_data = dict(zip(columns, row))
    return {"success": True, "data": settlement_data}

@app.get("/api/wallets/{user_id}")
async def get_wallet_balances(user_id: str):
    """Get all wallet balances for a user"""
    conn = sqlite3.connect(settlement_engine.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM wallet_balances WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    balances = []
    columns = ['user_id', 'currency', 'available_balance', 'locked_balance', 
              'total_balance', 'last_updated']
    
    for row in rows:
        balance_data = dict(zip(columns, row))
        balances.append(balance_data)
    
    return {"success": True, "user_id": user_id, "balances": balances}

@app.get("/api/transactions/{user_id}")
async def get_transaction_history(user_id: str, limit: int = 50):
    """Get transaction history for a user"""
    conn = sqlite3.connect(settlement_engine.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM transaction_history 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (user_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    transactions = []
    columns = ['id', 'user_id', 'type', 'currency', 'amount', 'reference_id',
              'timestamp', 'description']
    
    for row in rows:
        transaction_data = dict(zip(columns, row))
        transactions.append(transaction_data)
    
    return {"success": True, "user_id": user_id, "transactions": transactions}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    uvicorn.run(app, host="0.0.0.0", port=port)