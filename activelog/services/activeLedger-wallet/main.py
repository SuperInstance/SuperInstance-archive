#!/usr/bin/env python3
"""
ActiveLedger Wallet Server
CC wallet management with enhanced security
Instance: t3.medium
"""

import asyncio
import json
import time
import uuid
import secrets
import hashlib
import hmac
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import aioredis
import sqlite3
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import requests

app = FastAPI(title="ActiveLedger Wallet Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

@dataclass
class Wallet:
    wallet_id: str
    user_id: str
    address: str
    encrypted_private_key: str
    public_key: str
    balance: Decimal
    locked_balance: Decimal
    created_timestamp: float
    last_activity: float
    wallet_type: str = 'standard'  # 'standard', 'multisig', 'cold'
    status: str = 'active'  # 'active', 'frozen', 'disabled'

@dataclass
class Transaction:
    tx_id: str
    from_wallet: str
    to_wallet: str
    amount: Decimal
    fee: Decimal
    status: str  # 'pending', 'confirmed', 'failed'
    transaction_type: str  # 'transfer', 'deposit', 'withdrawal'
    timestamp: float
    confirmation_count: int = 0
    block_hash: Optional[str] = None
    signature: Optional[str] = None
    memo: Optional[str] = None

@dataclass
class MultiSigWallet:
    wallet_id: str
    required_signatures: int
    total_signers: int
    signer_public_keys: List[str]
    pending_transactions: List[str]
    created_timestamp: float

@dataclass
class PaymentIntegration:
    provider: str  # 'stripe', 'paypal', 'ach'
    account_id: str
    api_key: str
    webhook_secret: str
    enabled: bool

class WalletServer:
    def __init__(self):
        self.redis_client = None
        self.db_path = "data/wallet.db"
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Transaction fees
        self.base_fee = Decimal('0.1')  # 0.1 CC base fee
        self.fee_rate = Decimal('0.001')  # 0.1% of transaction amount
        
        # Security settings
        self.max_daily_withdrawal = Decimal('10000')  # 10,000 CC daily limit
        self.require_2fa_above = Decimal('1000')     # Require 2FA for transactions > 1,000 CC
        
        # Payment integrations
        self.payment_integrations: Dict[str, PaymentIntegration] = {}
        
        self._init_database()
        self._init_payment_integrations()
        
        # Start background tasks
        asyncio.create_task(self._process_pending_transactions())
        asyncio.create_task(self._monitor_suspicious_activity())
    
    def _init_database(self):
        """Initialize SQLite database for wallet data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Wallets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                wallet_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                address TEXT UNIQUE NOT NULL,
                encrypted_private_key TEXT NOT NULL,
                public_key TEXT NOT NULL,
                balance TEXT NOT NULL DEFAULT '0',
                locked_balance TEXT NOT NULL DEFAULT '0',
                created_timestamp REAL NOT NULL,
                last_activity REAL NOT NULL,
                wallet_type TEXT NOT NULL DEFAULT 'standard',
                status TEXT NOT NULL DEFAULT 'active'
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                from_wallet TEXT NOT NULL,
                to_wallet TEXT NOT NULL,
                amount TEXT NOT NULL,
                fee TEXT NOT NULL,
                status TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                confirmation_count INTEGER DEFAULT 0,
                block_hash TEXT,
                signature TEXT,
                memo TEXT
            )
        ''')
        
        # Multi-signature wallets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS multisig_wallets (
                wallet_id TEXT PRIMARY KEY,
                required_signatures INTEGER NOT NULL,
                total_signers INTEGER NOT NULL,
                signer_public_keys TEXT NOT NULL,
                pending_transactions TEXT NOT NULL,
                created_timestamp REAL NOT NULL
            )
        ''')
        
        # Address book table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS address_book (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                label TEXT NOT NULL,
                address TEXT NOT NULL,
                created_timestamp REAL NOT NULL
            )
        ''')
        
        # Security events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_events (
                id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                timestamp REAL NOT NULL,
                severity TEXT NOT NULL
            )
        ''')
        
        # Payment integration records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_records (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                external_tx_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                created_timestamp REAL NOT NULL,
                completed_timestamp REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_payment_integrations(self):
        """Initialize payment provider integrations"""
        # In production, these would be loaded from environment variables
        self.payment_integrations['stripe'] = PaymentIntegration(
            provider='stripe',
            account_id='acct_test_stripe',
            api_key='sk_test_stripe_key',
            webhook_secret='whsec_test_stripe',
            enabled=True
        )
        
        self.payment_integrations['paypal'] = PaymentIntegration(
            provider='paypal',
            account_id='paypal_merchant_id',
            api_key='paypal_api_key',
            webhook_secret='paypal_webhook_secret',
            enabled=True
        )
        
        self.payment_integrations['ach'] = PaymentIntegration(
            provider='ach',
            account_id='ach_account_id',
            api_key='ach_api_key',
            webhook_secret='ach_webhook_secret',
            enabled=True
        )
    
    async def initialize_redis(self):
        self.redis_client = await aioredis.from_url("redis://localhost:6379")
    
    def _generate_key_pair(self) -> Tuple[str, str]:
        """Generate RSA key pair for wallet"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode(), public_pem.decode()
    
    def _generate_address(self, public_key: str) -> str:
        """Generate wallet address from public key"""
        key_hash = hashlib.sha256(public_key.encode()).hexdigest()
        return f"CC{key_hash[:32].upper()}"
    
    def create_wallet(self, user_id: str, wallet_type: str = 'standard') -> Wallet:
        """Create new wallet for user"""
        # Generate key pair
        private_key, public_key = self._generate_key_pair()
        address = self._generate_address(public_key)
        
        # Encrypt private key
        encrypted_private_key = self.cipher_suite.encrypt(private_key.encode()).decode()
        
        wallet = Wallet(
            wallet_id=str(uuid.uuid4()),
            user_id=user_id,
            address=address,
            encrypted_private_key=encrypted_private_key,
            public_key=public_key,
            balance=Decimal('0'),
            locked_balance=Decimal('0'),
            created_timestamp=time.time(),
            last_activity=time.time(),
            wallet_type=wallet_type
        )
        
        self._store_wallet(wallet)
        
        # Log security event
        self._log_security_event(wallet.wallet_id, 'wallet_created', 
                                f'New {wallet_type} wallet created')
        
        return wallet
    
    def _store_wallet(self, wallet: Wallet):
        """Store wallet in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO wallets
            (wallet_id, user_id, address, encrypted_private_key, public_key, 
             balance, locked_balance, created_timestamp, last_activity, wallet_type, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wallet.wallet_id,
            wallet.user_id,
            wallet.address,
            wallet.encrypted_private_key,
            wallet.public_key,
            str(wallet.balance),
            str(wallet.locked_balance),
            wallet.created_timestamp,
            wallet.last_activity,
            wallet.wallet_type,
            wallet.status
        ))
        
        conn.commit()
        conn.close()
    
    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM wallets WHERE wallet_id = ?', (wallet_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        columns = ['wallet_id', 'user_id', 'address', 'encrypted_private_key', 'public_key',
                  'balance', 'locked_balance', 'created_timestamp', 'last_activity',
                  'wallet_type', 'status']
        
        wallet_data = dict(zip(columns, row))
        
        return Wallet(
            wallet_id=wallet_data['wallet_id'],
            user_id=wallet_data['user_id'],
            address=wallet_data['address'],
            encrypted_private_key=wallet_data['encrypted_private_key'],
            public_key=wallet_data['public_key'],
            balance=Decimal(wallet_data['balance']),
            locked_balance=Decimal(wallet_data['locked_balance']),
            created_timestamp=wallet_data['created_timestamp'],
            last_activity=wallet_data['last_activity'],
            wallet_type=wallet_data['wallet_type'],
            status=wallet_data['status']
        )
    
    def get_user_wallets(self, user_id: str) -> List[Wallet]:
        """Get all wallets for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM wallets WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        wallets = []
        columns = ['wallet_id', 'user_id', 'address', 'encrypted_private_key', 'public_key',
                  'balance', 'locked_balance', 'created_timestamp', 'last_activity',
                  'wallet_type', 'status']
        
        for row in rows:
            wallet_data = dict(zip(columns, row))
            wallets.append(Wallet(
                wallet_id=wallet_data['wallet_id'],
                user_id=wallet_data['user_id'],
                address=wallet_data['address'],
                encrypted_private_key=wallet_data['encrypted_private_key'],
                public_key=wallet_data['public_key'],
                balance=Decimal(wallet_data['balance']),
                locked_balance=Decimal(wallet_data['locked_balance']),
                created_timestamp=wallet_data['created_timestamp'],
                last_activity=wallet_data['last_activity'],
                wallet_type=wallet_data['wallet_type'],
                status=wallet_data['status']
            ))
        
        return wallets
    
    def calculate_transaction_fee(self, amount: Decimal) -> Decimal:
        """Calculate transaction fee"""
        percentage_fee = amount * self.fee_rate
        total_fee = self.base_fee + percentage_fee
        return total_fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    async def create_transaction(self, from_wallet_id: str, to_address: str, 
                               amount: Decimal, memo: str = None) -> Transaction:
        """Create new transaction"""
        from_wallet = self.get_wallet(from_wallet_id)
        if not from_wallet:
            raise ValueError("Source wallet not found")
        
        if from_wallet.status != 'active':
            raise ValueError("Source wallet is not active")
        
        fee = self.calculate_transaction_fee(amount)
        total_amount = amount + fee
        
        # Check balance
        if from_wallet.balance < total_amount:
            raise ValueError(f"Insufficient balance: {from_wallet.balance} < {total_amount}")
        
        # Security checks
        await self._perform_security_checks(from_wallet, amount)
        
        # Create transaction
        transaction = Transaction(
            tx_id=str(uuid.uuid4()),
            from_wallet=from_wallet_id,
            to_wallet=to_address,
            amount=amount,
            fee=fee,
            status='pending',
            transaction_type='transfer',
            timestamp=time.time(),
            memo=memo
        )
        
        # Lock funds
        from_wallet.balance -= total_amount
        from_wallet.locked_balance += total_amount
        from_wallet.last_activity = time.time()
        self._store_wallet(from_wallet)
        
        # Store transaction
        self._store_transaction(transaction)
        
        # Log security event
        self._log_security_event(from_wallet_id, 'transaction_created',
                                f'Transaction created: {amount} CC to {to_address}')
        
        return transaction
    
    async def _perform_security_checks(self, wallet: Wallet, amount: Decimal):
        """Perform security checks on transaction"""
        # Check daily withdrawal limit
        today_start = time.time() - (24 * 60 * 60)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(CAST(amount AS REAL)) FROM transactions 
            WHERE from_wallet = ? AND timestamp >= ? AND status != 'failed'
        ''', (wallet.wallet_id, today_start))
        
        daily_total = cursor.fetchone()[0] or 0
        daily_total = Decimal(str(daily_total)) + amount
        
        if daily_total > self.max_daily_withdrawal:
            conn.close()
            raise ValueError(f"Daily withdrawal limit exceeded: {daily_total} > {self.max_daily_withdrawal}")
        
        # Check for suspicious patterns
        cursor.execute('''
            SELECT COUNT(*) FROM transactions 
            WHERE from_wallet = ? AND timestamp >= ? AND status = 'pending'
        ''', (wallet.wallet_id, time.time() - 300))  # Last 5 minutes
        
        recent_pending = cursor.fetchone()[0]
        if recent_pending > 5:  # More than 5 pending transactions
            self._log_security_event(wallet.wallet_id, 'suspicious_activity',
                                   f'High frequency transactions detected: {recent_pending} pending')
        
        conn.close()
    
    def _store_transaction(self, transaction: Transaction):
        """Store transaction in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transactions
            (tx_id, from_wallet, to_wallet, amount, fee, status, transaction_type,
             timestamp, confirmation_count, block_hash, signature, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction.tx_id,
            transaction.from_wallet,
            transaction.to_wallet,
            str(transaction.amount),
            str(transaction.fee),
            transaction.status,
            transaction.transaction_type,
            transaction.timestamp,
            transaction.confirmation_count,
            transaction.block_hash,
            transaction.signature,
            transaction.memo
        ))
        
        conn.commit()
        conn.close()
    
    def _log_security_event(self, wallet_id: str, event_type: str, description: str,
                           severity: str = 'info', ip_address: str = None, user_agent: str = None):
        """Log security event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO security_events
            (id, wallet_id, event_type, description, ip_address, user_agent, timestamp, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            wallet_id,
            event_type,
            description,
            ip_address,
            user_agent,
            time.time(),
            severity
        ))
        
        conn.commit()
        conn.close()
    
    async def _process_pending_transactions(self):
        """Process pending transactions"""
        while True:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM transactions WHERE status = 'pending'")
            rows = cursor.fetchall()
            conn.close()
            
            columns = ['tx_id', 'from_wallet', 'to_wallet', 'amount', 'fee', 'status',
                      'transaction_type', 'timestamp', 'confirmation_count', 'block_hash',
                      'signature', 'memo']
            
            for row in rows:
                tx_data = dict(zip(columns, row))
                
                # Simulate transaction processing
                if time.time() - tx_data['timestamp'] > 30:  # Process after 30 seconds
                    success = random.choice([True, True, True, False])  # 75% success rate
                    
                    if success:
                        await self._confirm_transaction(tx_data['tx_id'])
                    else:
                        await self._fail_transaction(tx_data['tx_id'], "Network error")
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def _confirm_transaction(self, tx_id: str):
        """Confirm transaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get transaction details
        cursor.execute("SELECT * FROM transactions WHERE tx_id = ?", (tx_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return
        
        columns = ['tx_id', 'from_wallet', 'to_wallet', 'amount', 'fee', 'status',
                  'transaction_type', 'timestamp', 'confirmation_count', 'block_hash',
                  'signature', 'memo']
        tx_data = dict(zip(columns, row))
        
        # Update transaction status
        block_hash = hashlib.sha256(f"{tx_id}{time.time()}".encode()).hexdigest()
        
        cursor.execute('''
            UPDATE transactions 
            SET status = 'confirmed', confirmation_count = 1, block_hash = ?
            WHERE tx_id = ?
        ''', (block_hash, tx_id))
        
        # Update wallet balances
        from_wallet = self.get_wallet(tx_data['from_wallet'])
        if from_wallet:
            total_amount = Decimal(tx_data['amount']) + Decimal(tx_data['fee'])
            from_wallet.locked_balance -= total_amount
            self._store_wallet(from_wallet)
        
        # Credit destination wallet if it's internal
        to_wallet = self.get_wallet_by_address(tx_data['to_wallet'])
        if to_wallet:
            to_wallet.balance += Decimal(tx_data['amount'])
            to_wallet.last_activity = time.time()
            self._store_wallet(to_wallet)
        
        conn.commit()
        conn.close()
        
        # Log security event
        self._log_security_event(tx_data['from_wallet'], 'transaction_confirmed',
                                f'Transaction {tx_id} confirmed')
    
    async def _fail_transaction(self, tx_id: str, error_message: str):
        """Fail transaction and return funds"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get transaction details
        cursor.execute("SELECT * FROM transactions WHERE tx_id = ?", (tx_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return
        
        columns = ['tx_id', 'from_wallet', 'to_wallet', 'amount', 'fee', 'status',
                  'transaction_type', 'timestamp', 'confirmation_count', 'block_hash',
                  'signature', 'memo']
        tx_data = dict(zip(columns, row))
        
        # Update transaction status
        cursor.execute("UPDATE transactions SET status = 'failed' WHERE tx_id = ?", (tx_id,))
        
        # Return funds to source wallet
        from_wallet = self.get_wallet(tx_data['from_wallet'])
        if from_wallet:
            total_amount = Decimal(tx_data['amount']) + Decimal(tx_data['fee'])
            from_wallet.balance += total_amount
            from_wallet.locked_balance -= total_amount
            self._store_wallet(from_wallet)
        
        conn.commit()
        conn.close()
        
        # Log security event
        self._log_security_event(tx_data['from_wallet'], 'transaction_failed',
                                f'Transaction {tx_id} failed: {error_message}', 'warning')
    
    def get_wallet_by_address(self, address: str) -> Optional[Wallet]:
        """Get wallet by address"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM wallets WHERE address = ?', (address,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        columns = ['wallet_id', 'user_id', 'address', 'encrypted_private_key', 'public_key',
                  'balance', 'locked_balance', 'created_timestamp', 'last_activity',
                  'wallet_type', 'status']
        
        wallet_data = dict(zip(columns, row))
        
        return Wallet(**{k: Decimal(v) if k in ['balance', 'locked_balance'] else v 
                        for k, v in wallet_data.items()})
    
    async def _monitor_suspicious_activity(self):
        """Monitor for suspicious wallet activity"""
        while True:
            # This would implement ML-based fraud detection
            # For now, just log activity patterns
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def process_payment_deposit(self, provider: str, external_tx_id: str, 
                                    user_id: str, amount: Decimal, currency: str) -> bool:
        """Process deposit from payment provider"""
        if provider not in self.payment_integrations:
            return False
        
        integration = self.payment_integrations[provider]
        if not integration.enabled:
            return False
        
        # Get user's primary wallet
        wallets = self.get_user_wallets(user_id)
        if not wallets:
            # Create wallet if user doesn't have one
            wallet = self.create_wallet(user_id)
        else:
            wallet = wallets[0]  # Use first wallet
        
        # Convert currency to CC (simplified conversion)
        cc_amount = amount  # In production, this would use real exchange rates
        
        # Credit wallet
        wallet.balance += cc_amount
        wallet.last_activity = time.time()
        self._store_wallet(wallet)
        
        # Record payment
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payment_records
            (id, user_id, provider, external_tx_id, amount, currency, status, created_timestamp, completed_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            user_id,
            provider,
            external_tx_id,
            str(cc_amount),
            currency,
            'completed',
            time.time(),
            time.time()
        ))
        
        conn.commit()
        conn.close()
        
        # Log security event
        self._log_security_event(wallet.wallet_id, 'deposit_processed',
                                f'Deposit from {provider}: {cc_amount} CC')
        
        return True

# Initialize wallet server
wallet_server = WalletServer()

@app.on_event("startup")
async def startup_event():
    await wallet_server.initialize_redis()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "wallet-server"}

@app.post("/api/wallets")
async def create_wallet(wallet_data: dict):
    """Create new wallet"""
    wallet = wallet_server.create_wallet(
        user_id=wallet_data['user_id'],
        wallet_type=wallet_data.get('wallet_type', 'standard')
    )
    
    # Don't return private key in response
    wallet_response = asdict(wallet)
    del wallet_response['encrypted_private_key']
    
    return {"success": True, "wallet": wallet_response}

@app.get("/api/wallets/{wallet_id}")
async def get_wallet(wallet_id: str):
    """Get wallet by ID"""
    wallet = wallet_server.get_wallet(wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    # Don't return private key in response
    wallet_response = asdict(wallet)
    del wallet_response['encrypted_private_key']
    
    return {"success": True, "wallet": wallet_response}

@app.get("/api/users/{user_id}/wallets")
async def get_user_wallets(user_id: str):
    """Get all wallets for user"""
    wallets = wallet_server.get_user_wallets(user_id)
    
    # Don't return private keys in response
    wallets_response = []
    for wallet in wallets:
        wallet_data = asdict(wallet)
        del wallet_data['encrypted_private_key']
        wallets_response.append(wallet_data)
    
    return {"success": True, "wallets": wallets_response}

@app.post("/api/transactions")
async def create_transaction(tx_data: dict):
    """Create new transaction"""
    try:
        transaction = await wallet_server.create_transaction(
            from_wallet_id=tx_data['from_wallet_id'],
            to_address=tx_data['to_address'],
            amount=Decimal(str(tx_data['amount'])),
            memo=tx_data.get('memo')
        )
        return {"success": True, "transaction": asdict(transaction)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/payments/deposit")
async def process_deposit(payment_data: dict):
    """Process payment deposit"""
    success = await wallet_server.process_payment_deposit(
        provider=payment_data['provider'],
        external_tx_id=payment_data['external_tx_id'],
        user_id=payment_data['user_id'],
        amount=Decimal(str(payment_data['amount'])),
        currency=payment_data['currency']
    )
    
    return {"success": success}

@app.get("/api/wallets/{wallet_id}/transactions")
async def get_wallet_transactions(wallet_id: str, limit: int = 50):
    """Get wallet transaction history"""
    conn = sqlite3.connect(wallet_server.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM transactions 
        WHERE from_wallet = ? OR to_wallet = ?
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (wallet_id, wallet_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    columns = ['tx_id', 'from_wallet', 'to_wallet', 'amount', 'fee', 'status',
              'transaction_type', 'timestamp', 'confirmation_count', 'block_hash',
              'signature', 'memo']
    
    transactions = []
    for row in rows:
        tx_data = dict(zip(columns, row))
        transactions.append(tx_data)
    
    return {"success": True, "transactions": transactions}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8504))
    uvicorn.run(app, host="0.0.0.0", port=port)