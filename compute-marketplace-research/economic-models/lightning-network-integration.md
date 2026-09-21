# Lightning Network Integration Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Node Setup & Configuration](#node-setup--configuration)
4. [Channel Management](#channel-management)
5. [Invoice Generation & Management](#invoice-generation--management)
6. [Payment Flow Implementation](#payment-flow-implementation)
7. [Escrow with Hold Invoices](#escrow-with-hold-invoices)
8. [Backend Integration](#backend-integration)
9. [Frontend Integration](#frontend-integration)
10. [Monitoring & Operations](#monitoring--operations)
11. [Security Best Practices](#security-best-practices)
12. [Cost Analysis](#cost-analysis)
13. [Testing Strategy](#testing-strategy)
14. [Troubleshooting](#troubleshooting)
15. [References](#references)

---

## Introduction

The Lightning Network is a Layer 2 payment protocol built on Bitcoin that enables instant, low-cost payments. This guide provides comprehensive instructions for integrating Lightning Network payments into a compute marketplace platform.

### Why Lightning Network?

**Advantages:**
- **Instant Settlement:** Payments confirm in <1 second
- **Minimal Fees:** $0.001-0.01 per transaction regardless of amount
- **Micropayment Support:** Send payments as small as 1 satoshi ($0.0004)
- **No Chargebacks:** Cryptographically final payments
- **Privacy:** No blockchain record of individual payments
- **24/7 Availability:** No banking hours or holidays

**Use Cases in Compute Marketplace:**
- Pay-per-second compute billing
- Instant provider payouts
- Streaming payments for long-running jobs
- Cross-border payments without intermediaries
- Anonymous compute purchases

### When to Use Lightning vs Alternatives

| Transaction Type | Recommended Method | Reason |
|-----------------|-------------------|---------|
| <$10 micropayment | Lightning | Low fees, instant |
| $10-100 standard | Lightning/USDC | Cost-effective |
| >$100 large | USDC | Higher liquidity |
| Recurring small | Lightning | Streaming capable |
| International | Lightning/USDC | No FX fees |
| Privacy-focused | Lightning | Off-chain privacy |

---

## Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Compute Marketplace Platform                     │
│                                                                       │
│  ┌────────────────┐      ┌──────────────┐      ┌─────────────────┐  │
│  │   Web/Mobile   │      │   Backend    │      │  Admin Dashboard│  │
│  │   Application  │─────>│     API      │─────>│   (Monitoring)  │  │
│  └────────────────┘      └──────────────┘      └─────────────────┘  │
│         │                        │                                   │
│         │                        │                                   │
│         │                        ▼                                   │
│         │              ┌──────────────────┐                          │
│         │              │  LND Integration │                          │
│         │              │     Service      │                          │
│         │              └──────────────────┘                          │
│         │                        │                                   │
└─────────┼────────────────────────┼───────────────────────────────────┘
          │                        │
          │                        ▼
          │              ┌──────────────────┐
          │              │   LND Lightning  │
          │              │      Node        │
          │              └──────────────────┘
          │                        │
          │              ┌──────────┴──────────┐
          │              │                     │
          │              ▼                     ▼
          │      ┌──────────────┐     ┌──────────────┐
          │      │   Bitcoin    │     │  Lightning   │
          │      │   Network    │     │   Network    │
          │      └──────────────┘     └──────────────┘
          │
          │      Customer Interaction:
          └────> Scan QR Code / Click Payment Link
                 Lightning Wallet → Pay Invoice
                 Platform Confirms → Service Activated
```

### Component Breakdown

**1. LND Node:**
- Core Lightning Network daemon
- Manages channels and routing
- Generates invoices and processes payments
- Exposes gRPC and REST APIs

**2. Integration Service:**
- Middleware between application and LND
- Handles invoice generation
- Monitors payment status
- Manages escrow with hold invoices
- Stores payment metadata

**3. Backend API:**
- Order management
- Payment coordination
- Escrow state machine
- Webhook notifications

**4. Monitoring:**
- Channel health tracking
- Liquidity management
- Payment success rates
- Node uptime alerts

---

## Node Setup & Configuration

### Option 1: Self-Hosted LND (Recommended for Production)

#### System Requirements

```yaml
Minimum Specs:
  CPU: 2 cores
  RAM: 4 GB
  Storage: 500 GB SSD (Bitcoin pruned node)
  Bandwidth: 100 GB/month
  Uptime: 99.5%+ required

Recommended Specs:
  CPU: 4+ cores
  RAM: 8 GB
  Storage: 1 TB NVMe SSD
  Bandwidth: Unlimited
  Uptime: 99.9%+
```

#### Installation on Ubuntu 22.04 LTS

```bash
#!/bin/bash

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y wget git build-essential

# Install Go 1.21+
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
echo 'export GOPATH=$HOME/go' >> ~/.bashrc
echo 'export PATH=$PATH:$GOPATH/bin' >> ~/.bashrc
source ~/.bashrc

# Verify Go installation
go version

# Install Bitcoin Core (for backend)
wget https://bitcoincore.org/bin/bitcoin-core-26.0/bitcoin-26.0-x86_64-linux-gnu.tar.gz
tar xzf bitcoin-26.0-x86_64-linux-gnu.tar.gz
sudo install -m 0755 -o root -g root -t /usr/local/bin bitcoin-26.0/bin/*

# Create Bitcoin data directory
mkdir -p ~/.bitcoin

# Configure Bitcoin Core
cat > ~/.bitcoin/bitcoin.conf <<EOF
# Mainnet configuration
testnet=0
prune=100000
txindex=0

# RPC Settings
server=1
rpcuser=lnd_user
rpcpassword=$(openssl rand -hex 32)
rpcallowip=127.0.0.1

# Performance
dbcache=2000
maxmempool=300

# Network
listen=1
maxconnections=40

# ZMQ for LND
zmqpubrawblock=tcp://127.0.0.1:28332
zmqpubrawtx=tcp://127.0.0.1:28333
EOF

# Create systemd service for Bitcoin
sudo tee /etc/systemd/system/bitcoind.service > /dev/null <<EOF
[Unit]
Description=Bitcoin daemon
After=network.target

[Service]
ExecStart=/usr/local/bin/bitcoind -daemon -conf=/home/$USER/.bitcoin/bitcoin.conf -datadir=/home/$USER/.bitcoin
User=$USER
Type=forking
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Start Bitcoin Core
sudo systemctl enable bitcoind
sudo systemctl start bitcoind

# Wait for initial sync (this takes hours/days)
echo "Bitcoin Core is syncing... This may take 24-48 hours with pruning."
echo "Check progress: bitcoin-cli getblockchaininfo"

# Install LND
cd ~
git clone https://github.com/lightningnetwork/lnd.git
cd lnd
git checkout v0.17.4-beta  # Latest stable version
make install

# Verify LND installation
lnd --version

# Create LND data directory
mkdir -p ~/.lnd

# Configure LND
cat > ~/.lnd/lnd.conf <<EOF
[Application Options]
# Mainnet
bitcoin.mainnet=true
debuglevel=info

# Alias and color for your node
alias=ComputeMarketplace-Node
color=#FF9900

# RESTful API
restlisten=127.0.0.1:8080
rpclisten=127.0.0.1:10009

# Tor for privacy (optional)
# tor.active=true
# tor.streamisolation=true

# Database
db.backend=postgres
db.postgres.dsn=postgresql://lnd:password@localhost:5432/lnd?sslmode=disable

# Watchtower client (for security)
wtclient.active=true

# Auto-accept invoices
accept-keysend=true
accept-amp=true

# Fee settings
bitcoin.feerate=economical

[Bitcoin]
bitcoin.active=true
bitcoin.node=bitcoind

[Bitcoind]
bitcoind.rpchost=127.0.0.1:8332
bitcoind.rpcuser=lnd_user
bitcoind.rpcpass=YOUR_RPC_PASSWORD_FROM_BITCOIN_CONF
bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332
bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333

[autopilot]
autopilot.active=false
autopilot.maxchannels=10
autopilot.allocation=0.6
EOF

# Create systemd service for LND
sudo tee /etc/systemd/system/lnd.service > /dev/null <<EOF
[Unit]
Description=LND Lightning Network Daemon
After=bitcoind.service
Requires=bitcoind.service

[Service]
ExecStart=/home/$USER/go/bin/lnd
User=$USER
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Note: Don't start LND yet - need to initialize wallet first
echo "Installation complete. Initialize LND wallet with: lnd"
echo "Then in another terminal: lncli create"
```

#### LND Wallet Initialization

```bash
# Start LND in a separate terminal
lnd

# In another terminal, create wallet
lncli create

# Follow prompts:
# 1. Enter password (store securely!)
# 2. Choose existing seed or generate new
# 3. Enter optional passphrase
# 4. WRITE DOWN 24-WORD SEED PHRASE (critical backup!)

# After wallet creation, LND will fully start
# Enable and start the systemd service
sudo systemctl enable lnd
sudo systemctl start lnd

# Check LND status
lncli getinfo
lncli walletbalance
```

### Option 2: Hosted Lightning Node (Faster Setup)

#### Voltage.cloud Setup

```bash
# Voltage provides hosted LND nodes
# Sign up at: https://voltage.cloud

# After creating a node, download credentials:
# - TLS certificate (tls.cert)
# - Admin macaroon (admin.macaroon)
# - Node endpoint (e.g., node-123.voltage.cloud:10009)

# Store credentials securely
mkdir -p ~/.lnd-voltage
cp ~/Downloads/tls.cert ~/.lnd-voltage/
cp ~/Downloads/admin.macaroon ~/.lnd-voltage/

# Test connection
lncli --rpcserver=node-123.voltage.cloud:10009 \
      --tlscertpath=~/.lnd-voltage/tls.cert \
      --macaroonpath=~/.lnd-voltage/admin.macaroon \
      getinfo
```

**Voltage Pricing (2025):**
- Lite Node: $20/month (shared infrastructure)
- Standard Node: $50/month (dedicated resources)
- Plus Node: $100/month (high availability)

### Option 3: Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  bitcoind:
    image: btcpayserver/bitcoin:26.0
    container_name: bitcoind
    volumes:
      - bitcoin_data:/data
    environment:
      BITCOIN_NETWORK: mainnet
      BITCOIN_EXTRA_ARGS: |
        prune=100000
        rpcuser=lnd_user
        rpcpassword=secure_password_here
        zmqpubrawblock=tcp://0.0.0.0:28332
        zmqpubrawtx=tcp://0.0.0.0:28333
    ports:
      - "8333:8333"
      - "8332:8332"

  lnd:
    image: lightninglabs/lnd:v0.17.4-beta
    container_name: lnd
    depends_on:
      - bitcoind
    volumes:
      - lnd_data:/root/.lnd
      - ./lnd.conf:/root/.lnd/lnd.conf
    environment:
      LND_CHAIN: bitcoin
      LND_ENVIRONMENT: mainnet
    ports:
      - "9735:9735"  # P2P
      - "10009:10009"  # gRPC
      - "8080:8080"  # REST
    command: >
      lnd
      --bitcoin.active
      --bitcoin.mainnet
      --bitcoin.node=bitcoind
      --bitcoind.rpchost=bitcoind:8332
      --bitcoind.rpcuser=lnd_user
      --bitcoind.rpcpass=secure_password_here
      --bitcoind.zmqpubrawblock=tcp://bitcoind:28332
      --bitcoind.zmqpubrawtx=tcp://bitcoind:28333

volumes:
  bitcoin_data:
  lnd_data:
```

```bash
# Deploy with Docker Compose
docker-compose up -d

# Initialize wallet
docker exec -it lnd lncli create

# Check status
docker exec -it lnd lncli getinfo
```

---

## Channel Management

### Understanding Lightning Channels

Lightning channels are bidirectional payment channels that allow unlimited off-chain transactions between two nodes.

```
Channel Anatomy:

Your Node                                    Peer Node
┌────────────────────────────────────────────────────────┐
│  Local Balance: 0.01 BTC  │  Remote Balance: 0.00 BTC │
│  (You can send →)          │  (← You can receive)      │
└────────────────────────────────────────────────────────┘
         Total Channel Capacity: 0.01 BTC

After receiving 0.002 BTC payment:
┌────────────────────────────────────────────────────────┐
│ Local: 0.008 BTC │ Remote: 0.002 BTC │
└────────────────────────────────────────────────────────┘
```

### Opening Channels - Strategic Approach

#### 1. Identify Key Hubs

```bash
# Find well-connected nodes
# Check these resources:
# - https://1ml.com/ (node rankings)
# - https://amboss.space/ (node analytics)
# - https://terminal.lightning.engineering/ (node suggestions)

# Recommended initial peers (as of 2025):
RECOMMENDED_PEERS=(
  "ACINQ"
  "Wallet of Satoshi"
  "Bitfinex"
  "River Financial"
  "LightningNetwork+"
)

# Get node public keys from 1ml.com or amboss.space
```

#### 2. Open Channels

```bash
# Connect to peer
lncli connect 03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f@34.239.230.56:9735

# Open channel (0.01 BTC = 1,000,000 sats)
lncli openchannel \
  --node_key 03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f \
  --local_amt 1000000 \
  --sat_per_vbyte 5 \
  --min_confs 3

# Monitor channel opening
lncli pendingchannels

# Wait for 3+ confirmations
# Check active channels
lncli listchannels
```

#### 3. Channel Sizing Strategy

```yaml
# For Compute Marketplace (targeting $10K/month volume)

Channel Distribution:
  Large Hubs (5 channels × 0.05 BTC):
    - Purpose: Major routing capacity
    - Peers: ACINQ, WalletOfSatoshi, Bitfinex
    - Total: 0.25 BTC (~$12,500)

  Medium Peers (10 channels × 0.01 BTC):
    - Purpose: Routing diversity
    - Peers: Various popular nodes
    - Total: 0.10 BTC (~$5,000)

  Customer Channels (as needed):
    - Purpose: Direct payment paths
    - Size: 0.001-0.005 BTC per channel
    - Total: Variable

Total Initial Capital: 0.35 BTC (~$17,500)
Expected Monthly Volume Support: $50K
```

### Inbound Liquidity Management

**Problem:** New nodes can only send payments, not receive them (no inbound liquidity).

**Solutions:**

#### Option 1: Loop In (Lightning Labs)

```bash
# Install Loop
go install github.com/lightninglabs/loop/cmd/loop@latest

# Loop In: Pay on-chain, receive on Lightning
# This creates inbound liquidity
loop in --amt 1000000 --conf_target 6

# Cost: On-chain fee + 0.5% service fee
```

#### Option 2: Submarine Swaps (Boltz.exchange)

```bash
# Use Boltz API for submarine swaps
# Swap on-chain BTC → Lightning BTC (inbound liquidity)

curl -X POST https://api.boltz.exchange/createswap \
  -H "Content-Type: application/json" \
  -d '{
    "type": "submarine",
    "pairId": "BTC/BTC",
    "orderSide": "buy",
    "invoice": "lnbc10u1...",
    "refundPublicKey": "02a1b2c3..."
  }'
```

#### Option 3: Liquidity Marketplaces

```bash
# Amboss Magma - Buy inbound liquidity
# https://amboss.space/magma

# Pool (Lightning Labs) - Lease channels
# https://lightning.engineering/pool/

# Typical pricing (2025): 0.1-0.5% of channel size for 4-8 weeks
```

#### Option 4: Circular Rebalancing

```bash
# Use your own outbound capacity to create inbound capacity
# Send funds out through one channel, receive back through another

# Install rebalance-lnd
npm install -g rebalance-lnd

# Rebalance a channel
rebalance-lnd \
  --from=PEER_A_PUBKEY \
  --to=PEER_B_PUBKEY \
  --amount=500000 \
  --max-fee-rate=100
```

### Channel Monitoring

```bash
# Check channel balances
lncli listchannels | jq -r '.channels[] | "\(.remote_pubkey[:16]) Local: \(.local_balance) Remote: \(.remote_balance)"'

# Channel uptime
lncli listchannels | jq '.channels[] | {alias: .chan_id, uptime: .uptime}'

# Inactive channels
lncli listchannels | jq '.channels[] | select(.active == false)'

# Fee settings per channel
lncli listchannels | jq '.channels[] | {chan_id, fee_rate: .fee_per_mil}'
```

### Automated Channel Management Script

```python
#!/usr/bin/env python3
"""
LND Channel Manager
Monitors channels and rebalances as needed
"""

import subprocess
import json
import time

TARGET_LOCAL_RATIO = 0.5  # Keep 50% local balance
REBALANCE_THRESHOLD = 0.2  # Rebalance if >20% away from target

def get_channels():
    """Get all active channels"""
    result = subprocess.run(
        ['lncli', 'listchannels'],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)['channels']

def calculate_balance_ratio(channel):
    """Calculate local balance ratio"""
    total = channel['local_balance'] + channel['remote_balance']
    if total == 0:
        return 0
    return channel['local_balance'] / total

def needs_rebalancing(channel):
    """Check if channel needs rebalancing"""
    ratio = calculate_balance_ratio(channel)
    deviation = abs(ratio - TARGET_LOCAL_RATIO)
    return deviation > REBALANCE_THRESHOLD

def rebalance_channel(channel):
    """Rebalance a channel"""
    chan_id = channel['chan_id']
    current_ratio = calculate_balance_ratio(channel)

    if current_ratio > TARGET_LOCAL_RATIO:
        # Too much local, need to send out
        amount = int((current_ratio - TARGET_LOCAL_RATIO) * channel['local_balance'])
        direction = "send"
    else:
        # Too little local, need to receive
        amount = int((TARGET_LOCAL_RATIO - current_ratio) * channel['remote_balance'])
        direction = "receive"

    print(f"Rebalancing channel {chan_id[:16]}... {direction} {amount} sats")

    # Use rebalance-lnd or circular rebalancing
    # This is a simplified example
    # In production, use proper rebalancing tools

def monitor_channels():
    """Main monitoring loop"""
    while True:
        try:
            channels = get_channels()

            print(f"\n=== Channel Status ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===")

            for channel in channels:
                ratio = calculate_balance_ratio(channel)
                status = "⚖️ Balanced" if not needs_rebalancing(channel) else "⚠️ Needs rebalancing"

                print(f"{channel['chan_id'][:16]} | Local: {ratio:.2%} | {status}")

                if needs_rebalancing(channel):
                    rebalance_channel(channel)

            # Check every 15 minutes
            time.sleep(900)

        except Exception as e:
            print(f"Error monitoring channels: {e}")
            time.sleep(60)

if __name__ == '__main__':
    monitor_channels()
```

---

## Invoice Generation & Management

### Invoice Types

**1. Standard Invoice:**
- Fixed amount
- Single payment
- Expires after timeout

**2. AMP Invoice (Atomic Multi-Path):**
- Supports payments larger than single channel capacity
- Splits payment across multiple routes
- Better success rate for large amounts

**3. Hold Invoice (HODL):**
- Payment held until you release it
- Perfect for escrow scenarios
- Requires custom logic

### Generating Invoices via CLI

```bash
# Basic invoice (0.0001 BTC = 10,000 sats)
lncli addinvoice --amt 10000 --memo "Compute job #12345" --expiry 3600

# Response:
# {
#   "r_hash": "8f7d...",
#   "payment_request": "lnbc100u1p3...",
#   "add_index": "123",
#   "payment_addr": "9a2b..."
# }

# AMP invoice (supports multi-path)
lncli addinvoice --amt 100000 --memo "Large compute job" --amp

# Invoice with private routing hints
lncli addinvoice --amt 5000 --memo "Private payment" --private

# Check invoice status
lncli lookupinvoice --rhash 8f7d...

# List all invoices
lncli listinvoices --max_invoices 100

# List only settled invoices
lncli listinvoices --index_offset 0 --num_max_invoices 50 --reversed | jq '.invoices[] | select(.settled == true)'
```

### Hold Invoice (Escrow) Setup

Hold invoices are essential for marketplace escrow. Payment is held until you explicitly release or cancel it.

```bash
# Hold invoices require custom implementation
# Install lndhub or use custom hold invoice logic

# Example hold invoice flow:
# 1. Generate hash and preimage
# 2. Create invoice with that hash
# 3. Accept payment (funds held)
# 4. When job completes, reveal preimage (release payment)
# 5. Or timeout/cancel invoice (refund payment)
```

---

## Payment Flow Implementation

### Customer Payment Flow

```
1. Customer requests compute service
   └─> Backend creates order

2. Backend generates Lightning invoice
   └─> Amount = job cost + platform fee
   └─> Hold invoice for escrow

3. Invoice presented to customer
   └─> QR code
   └─> Lightning URI
   └─> Payment link

4. Customer pays with Lightning wallet
   └─> Funds held in escrow (hold invoice)

5. Provider completes job
   └─> Customer or platform confirms completion

6. Backend settles hold invoice
   └─> Funds released to provider
   └─> Platform fee captured

7. Confirmation sent to all parties
```

### Backend Integration - Node.js Example

```javascript
// lightning-service.js
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import fs from 'fs';
import crypto from 'crypto';

class LightningService {
  constructor() {
    // Load LND credentials
    const macaroon = fs.readFileSync('/path/to/.lnd/data/chain/bitcoin/mainnet/admin.macaroon');
    const macaroonHex = macaroon.toString('hex');

    // Load proto files
    const packageDefinition = protoLoader.loadSync(
      '/path/to/lnd/lnrpc/lightning.proto',
      {
        keepCase: true,
        longs: String,
        enums: String,
        defaults: true,
        oneofs: true
      }
    );

    const lnrpc = grpc.loadPackageDefinition(packageDefinition).lnrpc;

    // SSL credentials
    const sslCreds = grpc.credentials.createSsl(
      fs.readFileSync('/path/to/.lnd/tls.cert')
    );

    // Macaroon credentials
    const macaroonCreds = grpc.credentials.createFromMetadataGenerator((args, callback) => {
      const metadata = new grpc.Metadata();
      metadata.add('macaroon', macaroonHex);
      callback(null, metadata);
    });

    // Combine credentials
    const creds = grpc.credentials.combineChannelCredentials(sslCreds, macaroonCreds);

    // Create client
    this.lightning = new lnrpc.Lightning('localhost:10009', creds);
  }

  /**
   * Get node info
   */
  async getInfo() {
    return new Promise((resolve, reject) => {
      this.lightning.getInfo({}, (err, response) => {
        if (err) reject(err);
        else resolve(response);
      });
    });
  }

  /**
   * Generate standard invoice
   */
  async createInvoice({ amount, memo, expiry = 3600 }) {
    return new Promise((resolve, reject) => {
      this.lightning.addInvoice(
        {
          value: amount, // satoshis
          memo: memo,
          expiry: expiry
        },
        (err, response) => {
          if (err) reject(err);
          else resolve(response);
        }
      );
    });
  }

  /**
   * Generate hold invoice (for escrow)
   */
  async createHoldInvoice({ amount, memo, expiry = 3600 }) {
    // Generate preimage and hash
    const preimage = crypto.randomBytes(32);
    const hash = crypto.createHash('sha256').update(preimage).digest();

    return new Promise((resolve, reject) => {
      this.lightning.addHoldInvoice(
        {
          hash: hash,
          value: amount,
          memo: memo,
          expiry: expiry
        },
        (err, response) => {
          if (err) reject(err);
          else resolve({
            ...response,
            preimage: preimage.toString('hex'), // Store this securely!
            hash: hash.toString('hex')
          });
        }
      );
    });
  }

  /**
   * Lookup invoice status
   */
  async lookupInvoice(paymentHash) {
    return new Promise((resolve, reject) => {
      this.lightning.lookupInvoice(
        {
          r_hash_str: paymentHash
        },
        (err, response) => {
          if (err) reject(err);
          else resolve(response);
        }
      );
    });
  }

  /**
   * Settle hold invoice (release payment)
   */
  async settleInvoice(preimage) {
    return new Promise((resolve, reject) => {
      this.lightning.settleInvoice(
        {
          preimage: Buffer.from(preimage, 'hex')
        },
        (err, response) => {
          if (err) reject(err);
          else resolve(response);
        }
      );
    });
  }

  /**
   * Cancel hold invoice (refund)
   */
  async cancelInvoice(paymentHash) {
    return new Promise((resolve, reject) => {
      this.lightning.cancelInvoice(
        {
          payment_hash: Buffer.from(paymentHash, 'hex')
        },
        (err, response) => {
          if (err) reject(err);
          else resolve(response);
        }
      );
    });
  }

  /**
   * Subscribe to invoice updates
   */
  subscribeInvoices(callback) {
    const call = this.lightning.subscribeInvoices({});

    call.on('data', (invoice) => {
      callback(null, invoice);
    });

    call.on('error', (err) => {
      callback(err, null);
    });

    call.on('end', () => {
      console.log('Invoice subscription ended');
    });

    return call; // Return to allow cancellation
  }

  /**
   * Send payment
   */
  async sendPayment(paymentRequest) {
    return new Promise((resolve, reject) => {
      this.lightning.sendPaymentSync(
        {
          payment_request: paymentRequest
        },
        (err, response) => {
          if (err) reject(err);
          else if (response.payment_error) reject(new Error(response.payment_error));
          else resolve(response);
        }
      );
    });
  }
}

export default LightningService;
```

### Usage Example

```javascript
// payment-controller.js
import LightningService from './lightning-service.js';
import db from './database.js';

const ln = new LightningService();

// Create payment endpoint
app.post('/api/payments/lightning/create', async (req, res) => {
  try {
    const { orderId, amount, customerId } = req.body;

    const order = await db.orders.findById(orderId);
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // Calculate platform fee
    const platformFee = Math.floor(amount * 0.15);
    const totalAmount = amount;

    // Generate hold invoice for escrow
    const invoice = await ln.createHoldInvoice({
      amount: totalAmount,
      memo: `Compute Marketplace - Order #${orderId}`,
      expiry: 3600 // 1 hour
    });

    // Store in database
    await db.payments.create({
      orderId: orderId,
      paymentMethod: 'lightning',
      amountSats: totalAmount,
      platformFeeSats: platformFee,
      invoicePaymentRequest: invoice.payment_request,
      invoicePaymentHash: invoice.hash,
      invoicePreimage: invoice.preimage, // Store securely!
      status: 'pending',
      expiresAt: new Date(Date.now() + 3600 * 1000)
    });

    res.json({
      paymentRequest: invoice.payment_request,
      paymentHash: invoice.hash,
      amount: totalAmount,
      expiresAt: new Date(Date.now() + 3600 * 1000)
    });
  } catch (error) {
    console.error('Lightning invoice creation failed:', error);
    res.status(500).json({ error: error.message });
  }
});

// Check payment status
app.get('/api/payments/lightning/:paymentHash', async (req, res) => {
  try {
    const { paymentHash } = req.params;

    const payment = await db.payments.findByHash(paymentHash);
    if (!payment) {
      return res.status(404).json({ error: 'Payment not found' });
    }

    // Lookup invoice on Lightning Network
    const invoice = await ln.lookupInvoice(paymentHash);

    // Update database if status changed
    if (invoice.state === 'ACCEPTED' && payment.status === 'pending') {
      await db.payments.update(payment.id, {
        status: 'held',
        paidAt: new Date(invoice.settle_date * 1000)
      });
    }

    res.json({
      status: payment.status,
      settled: invoice.settled,
      amount: invoice.value,
      paidAt: invoice.settle_date ? new Date(invoice.settle_date * 1000) : null
    });
  } catch (error) {
    console.error('Payment status check failed:', error);
    res.status(500).json({ error: error.message });
  }
});

// Release escrow payment
app.post('/api/escrow/lightning/release', async (req, res) => {
  try {
    const { orderId } = req.body;

    const payment = await db.payments.findByOrderId(orderId);
    if (!payment || payment.status !== 'held') {
      return res.status(400).json({ error: 'Invalid payment state' });
    }

    // Settle the hold invoice
    await ln.settleInvoice(payment.invoicePreimage);

    // Update payment status
    await db.payments.update(payment.id, {
      status: 'released',
      releasedAt: new Date()
    });

    // Pay provider (separate Lightning payment or track internally)
    const providerAmount = payment.amountSats - payment.platformFeeSats;

    res.json({
      success: true,
      providerAmount: providerAmount,
      platformFee: payment.platformFeeSats
    });
  } catch (error) {
    console.error('Payment release failed:', error);
    res.status(500).json({ error: error.message });
  }
});

// Refund payment
app.post('/api/escrow/lightning/refund', async (req, res) => {
  try {
    const { orderId } = req.body;

    const payment = await db.payments.findByOrderId(orderId);
    if (!payment || payment.status !== 'held') {
      return res.status(400).json({ error: 'Invalid payment state' });
    }

    // Cancel the hold invoice
    await ln.cancelInvoice(payment.invoicePaymentHash);

    // Update payment status
    await db.payments.update(payment.id, {
      status: 'refunded',
      refundedAt: new Date()
    });

    res.json({ success: true });
  } catch (error) {
    console.error('Payment refund failed:', error);
    res.status(500).json({ error: error.message });
  }
});

// Invoice update subscription
const subscribeToInvoices = () => {
  ln.subscribeInvoices(async (err, invoice) => {
    if (err) {
      console.error('Invoice subscription error:', err);
      return;
    }

    console.log(`Invoice update: ${invoice.payment_request}`);

    // Update database based on invoice state
    const payment = await db.payments.findByHash(invoice.r_hash.toString('hex'));
    if (!payment) return;

    if (invoice.state === 'ACCEPTED' && payment.status === 'pending') {
      await db.payments.update(payment.id, {
        status: 'held',
        paidAt: new Date(invoice.settle_date * 1000)
      });

      // Notify customer and provider
      // await sendNotification(...)
    }

    if (invoice.state === 'SETTLED' && payment.status === 'held') {
      await db.payments.update(payment.id, {
        status: 'released',
        releasedAt: new Date()
      });
    }

    if (invoice.state === 'CANCELED') {
      await db.payments.update(payment.id, {
        status: 'canceled',
        canceledAt: new Date()
      });
    }
  });
};

// Start invoice subscription
subscribeToInvoices();
```

### Python Implementation

```python
#!/usr/bin/env python3
"""
Lightning Network Integration - Python
"""

import codecs
import grpc
import os
from pathlib import Path
import hashlib
import secrets

# Import generated gRPC stubs
import rpc_pb2 as ln
import rpc_pb2_grpc as lnrpc

class LightningClient:
    def __init__(self, lnd_dir=None):
        if lnd_dir is None:
            lnd_dir = Path.home() / '.lnd'
        else:
            lnd_dir = Path(lnd_dir)

        # Load credentials
        macaroon_path = lnd_dir / 'data/chain/bitcoin/mainnet/admin.macaroon'
        tls_cert_path = lnd_dir / 'tls.cert'

        with open(macaroon_path, 'rb') as f:
            macaroon_bytes = f.read()
            macaroon = codecs.encode(macaroon_bytes, 'hex')

        # Create SSL credentials
        cert = open(tls_cert_path, 'rb').read()
        ssl_creds = grpc.ssl_channel_credentials(cert)

        # Create macaroon credentials
        auth_creds = grpc.metadata_call_credentials(
            lambda context, callback: callback([('macaroon', macaroon)], None)
        )

        # Combine credentials
        combined_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)

        # Create channel and stub
        channel = grpc.secure_channel('localhost:10009', combined_creds)
        self.stub = lnrpc.LightningStub(channel)

    def get_info(self):
        """Get node information"""
        request = ln.GetInfoRequest()
        return self.stub.GetInfo(request)

    def create_invoice(self, amount_sats, memo, expiry=3600):
        """Create standard invoice"""
        request = ln.Invoice(
            value=amount_sats,
            memo=memo,
            expiry=expiry
        )
        response = self.stub.AddInvoice(request)
        return {
            'payment_request': response.payment_request,
            'r_hash': response.r_hash.hex(),
            'payment_addr': response.payment_addr.hex()
        }

    def create_hold_invoice(self, amount_sats, memo, expiry=3600):
        """Create hold invoice for escrow"""
        # Generate preimage and hash
        preimage = secrets.token_bytes(32)
        payment_hash = hashlib.sha256(preimage).digest()

        request = ln.Invoice(
            r_preimage=preimage,
            r_hash=payment_hash,
            value=amount_sats,
            memo=memo,
            expiry=expiry
        )

        response = self.stub.AddHoldInvoice(request)

        return {
            'payment_request': response.payment_request,
            'payment_hash': payment_hash.hex(),
            'preimage': preimage.hex(),  # Store securely!
            'payment_addr': response.payment_addr.hex()
        }

    def lookup_invoice(self, payment_hash_hex):
        """Look up invoice by payment hash"""
        payment_hash = bytes.fromhex(payment_hash_hex)
        request = ln.PaymentHash(r_hash=payment_hash)
        return self.stub.LookupInvoice(request)

    def settle_invoice(self, preimage_hex):
        """Settle a hold invoice"""
        preimage = bytes.fromhex(preimage_hex)
        request = ln.SettleInvoiceMsg(preimage=preimage)
        return self.stub.SettleInvoice(request)

    def cancel_invoice(self, payment_hash_hex):
        """Cancel a hold invoice"""
        payment_hash = bytes.fromhex(payment_hash_hex)
        request = ln.CancelInvoiceMsg(payment_hash=payment_hash)
        return self.stub.CancelInvoice(request)

    def subscribe_invoices(self, callback):
        """Subscribe to invoice updates"""
        request = ln.InvoiceSubscription()
        for invoice in self.stub.SubscribeInvoices(request):
            callback(invoice)

    def send_payment(self, payment_request):
        """Send a Lightning payment"""
        request = ln.SendRequest(payment_request=payment_request)
        return self.stub.SendPaymentSync(request)

# Example usage
if __name__ == '__main__':
    client = LightningClient()

    # Get node info
    info = client.get_info()
    print(f"Node alias: {info.alias}")
    print(f"Node pubkey: {info.identity_pubkey}")
    print(f"Block height: {info.block_height}")
    print(f"Active channels: {info.num_active_channels}")

    # Create invoice
    invoice = client.create_invoice(
        amount_sats=10000,
        memo="Test payment"
    )
    print(f"\nInvoice created: {invoice['payment_request']}")

    # Create hold invoice
    hold_invoice = client.create_hold_invoice(
        amount_sats=50000,
        memo="Escrow payment"
    )
    print(f"\nHold invoice created: {hold_invoice['payment_request']}")
    print(f"Payment hash: {hold_invoice['payment_hash']}")
    print(f"Preimage (store securely!): {hold_invoice['preimage']}")
```

---

## Escrow with Hold Invoices

(Continued in next section due to length...)

### Hold Invoice State Machine

```
Invoice States:

OPEN → Invoice created, awaiting payment
  ↓
ACCEPTED → Payment received, funds held
  ↓
  ├─→ SETTLED → Preimage revealed, payment released to recipient
  ├─→ CANCELED → Invoice canceled, payment refunded to sender
  └─→ EXPIRED → Invoice timeout, payment automatically refunded
```

### Complete Escrow Implementation

```javascript
// escrow-manager.js
class LightningEscrowManager {
  constructor(lightningService, database) {
    this.ln = lightningService;
    this.db = database;
  }

  /**
   * Create escrow payment for order
   */
  async createEscrow(orderId, amount, platformFee) {
    const order = await this.db.orders.findById(orderId);

    // Generate hold invoice
    const invoice = await this.ln.createHoldInvoice({
      amount: amount,
      memo: `Escrow for Order #${orderId}`,
      expiry: 3600
    });

    // Store escrow record
    const escrow = await this.db.escrow.create({
      orderId: orderId,
      paymentHash: invoice.hash,
      preimage: invoice.preimage,  // Encrypted in production!
      amount: amount,
      platformFee: platformFee,
      providerAmount: amount - platformFee,
      state: 'awaiting_payment',
      createdAt: new Date(),
      expiresAt: new Date(Date.now() + 3600 * 1000)
    });

    return {
      escrowId: escrow.id,
      paymentRequest: invoice.payment_request,
      paymentHash: invoice.hash,
      expiresAt: escrow.expiresAt
    };
  }

  /**
   * Handle invoice payment (moves to held state)
   */
  async handlePaymentReceived(paymentHash) {
    const escrow = await this.db.escrow.findByHash(paymentHash);
    if (!escrow) {
      console.error(`Escrow not found for hash: ${paymentHash}`);
      return;
    }

    await this.db.escrow.update(escrow.id, {
      state: 'payment_held',
      paidAt: new Date()
    });

    // Notify customer and provider
    await this.notifyPaymentReceived(escrow);

    return escrow;
  }

  /**
   * Release payment to provider
   */
  async releasePayment(orderId, releasedBy) {
    const escrow = await this.db.escrow.findByOrderId(orderId);

    if (escrow.state !== 'payment_held') {
      throw new Error(`Cannot release payment in state: ${escrow.state}`);
    }

    // Settle the hold invoice (reveals preimage)
    await this.ln.settleInvoice(escrow.preimage);

    // Update escrow state
    await this.db.escrow.update(escrow.id, {
      state: 'released',
      releasedAt: new Date(),
      releasedBy: releasedBy
    });

    // Record provider payout (could be instant Lightning payment)
    await this.recordProviderPayout(escrow);

    // Record platform fee capture
    await this.recordPlatformFee(escrow);

    return escrow;
  }

  /**
   * Refund payment to customer
   */
  async refundPayment(orderId, refundedBy, reason) {
    const escrow = await this.db.escrow.findByOrderId(orderId);

    if (escrow.state !== 'payment_held') {
      throw new Error(`Cannot refund payment in state: ${escrow.state}`);
    }

    // Cancel the hold invoice
    await this.ln.cancelInvoice(escrow.paymentHash);

    // Update escrow state
    await this.db.escrow.update(escrow.id, {
      state: 'refunded',
      refundedAt: new Date(),
      refundedBy: refundedBy,
      refundReason: reason
    });

    return escrow;
  }

  /**
   * Handle dispute
   */
  async openDispute(orderId, disputeReason, disputedBy) {
    const escrow = await this.db.escrow.findByOrderId(orderId);

    await this.db.escrow.update(escrow.id, {
      state: 'disputed',
      disputeOpenedAt: new Date(),
      disputeReason: disputeReason,
      disputedBy: disputedBy
    });

    // Notify support team
    await this.notifyDisputeOpened(escrow);

    return escrow;
  }

  /**
   * Resolve dispute
   */
  async resolveDispute(orderId, resolution, resolvedBy) {
    const escrow = await this.db.escrow.findByOrderId(orderId);

    if (escrow.state !== 'disputed') {
      throw new Error('Escrow is not in disputed state');
    }

    if (resolution === 'release_to_provider') {
      await this.releasePayment(orderId, resolvedBy);
    } else if (resolution === 'refund_to_customer') {
      await this.refundPayment(orderId, resolvedBy, 'Dispute resolution');
    } else if (resolution.type === 'split') {
      // Partial refund/release (requires multiple transactions)
      await this.splitPayment(escrow, resolution.customerAmount, resolution.providerAmount);
    }

    return escrow;
  }

  /**
   * Split payment (for partial disputes)
   */
  async splitPayment(escrow, customerAmount, providerAmount) {
    if (customerAmount + providerAmount > escrow.amount) {
      throw new Error('Split amounts exceed total');
    }

    // Cancel original hold invoice (refunds customer)
    await this.ln.cancelInvoice(escrow.paymentHash);

    // Send partial payment to provider
    if (providerAmount > 0) {
      const order = await this.db.orders.findById(escrow.orderId);
      await this.payProvider(order.provider.lightningAddress, providerAmount);
    }

    // Platform keeps remainder as partial fee
    const platformFee = escrow.amount - customerAmount - providerAmount;

    await this.db.escrow.update(escrow.id, {
      state: 'split_resolved',
      customerRefund: customerAmount,
      providerPayout: providerAmount,
      platformFee: platformFee,
      resolvedAt: new Date()
    });
  }

  /**
   * Pay provider via Lightning
   */
  async payProvider(lightningAddress, amount) {
    // Use LNURL-pay or Lightning Address to pay provider
    // This is a simplified example
    const invoice = await this.generateProviderInvoice(lightningAddress, amount);
    return await this.ln.sendPayment(invoice);
  }

  /**
   * Auto-expire escrows
   */
  async expireEscrows() {
    const expiredEscrows = await this.db.escrow.findExpired();

    for (const escrow of expiredEscrows) {
      if (escrow.state === 'awaiting_payment') {
        // Invoice expired before payment
        await this.db.escrow.update(escrow.id, {
          state: 'expired',
          expiredAt: new Date()
        });
      } else if (escrow.state === 'payment_held') {
        // Payment held too long, auto-refund
        await this.refundPayment(
          escrow.orderId,
          'system',
          'Automatic expiry after hold period'
        );
      }
    }
  }
}

module.exports = LightningEscrowManager;
```

---

## Frontend Integration

### QR Code Display

```javascript
// React component for Lightning payment
import React, { useState, useEffect } from 'react';
import QRCode from 'qrcode.react';
import { CopyToClipboard } from 'react-copy-to-clipboard';

function LightningPayment({ orderId, amount }) {
  const [invoice, setInvoice] = useState(null);
  const [status, setStatus] = useState('generating');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Generate invoice
    fetch('/api/payments/lightning/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ orderId, amount })
    })
      .then(res => res.json())
      .then(data => {
        setInvoice(data);
        setStatus('awaiting_payment');
        pollPaymentStatus(data.paymentHash);
      })
      .catch(err => {
        console.error('Failed to generate invoice:', err);
        setStatus('error');
      });
  }, [orderId, amount]);

  const pollPaymentStatus = async (paymentHash) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/payments/lightning/${paymentHash}`);
        const data = await res.json();

        if (data.status === 'held') {
          setStatus('paid');
          clearInterval(interval);
        }
      } catch (err) {
        console.error('Status check failed:', err);
      }
    }, 2000); // Check every 2 seconds

    // Stop after 1 hour
    setTimeout(() => clearInterval(interval), 3600000);
  };

  if (status === 'generating') {
    return <div>Generating Lightning invoice...</div>;
  }

  if (status === 'error') {
    return <div>Error generating invoice. Please try again.</div>;
  }

  if (status === 'paid') {
    return (
      <div className="payment-success">
        <h3>✓ Payment Received!</h3>
        <p>Your compute job is starting...</p>
      </div>
    );
  }

  return (
    <div className="lightning-payment">
      <h3>Pay with Lightning Network</h3>

      <div className="qr-code">
        <QRCode
          value={invoice.paymentRequest.toUpperCase()}
          size={300}
          level="M"
        />
      </div>

      <div className="invoice-details">
        <p>
          <strong>Amount:</strong> {amount.toLocaleString()} sats
          ({(amount / 100000000 * 50000).toFixed(2)} USD)
        </p>
        <p>
          <strong>Expires:</strong> {new Date(invoice.expiresAt).toLocaleTimeString()}
        </p>
      </div>

      <div className="invoice-string">
        <input
          type="text"
          value={invoice.paymentRequest}
          readOnly
          className="invoice-input"
        />
        <CopyToClipboard
          text={invoice.paymentRequest}
          onCopy={() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          }}
        >
          <button className="copy-button">
            {copied ? '✓ Copied' : 'Copy Invoice'}
          </button>
        </CopyToClipboard>
      </div>

      <div className="payment-methods">
        <a
          href={`lightning:${invoice.paymentRequest}`}
          className="lightning-link"
        >
          Open in Lightning Wallet
        </a>
      </div>

      <div className="help-text">
        <p>
          Don't have a Lightning wallet?{' '}
          <a href="https://phoenix.acinq.co/" target="_blank" rel="noopener noreferrer">
            Get Phoenix Wallet
          </a>
        </p>
      </div>
    </div>
  );
}

export default LightningPayment;
```

### WebSocket for Real-Time Updates

```javascript
// Real-time payment status using WebSocket
import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';

function RealtimePaymentStatus({ paymentHash }) {
  const [status, setStatus] = useState('pending');
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    // Connect to WebSocket
    const newSocket = io('wss://your-api.com', {
      auth: { token: localStorage.getItem('auth_token') }
    });

    // Subscribe to payment updates
    newSocket.emit('subscribe_payment', { paymentHash });

    // Listen for status updates
    newSocket.on('payment_update', (data) => {
      console.log('Payment update:', data);
      setStatus(data.status);

      if (data.status === 'held' || data.status === 'released') {
        // Payment successful
        onPaymentSuccess(data);
      }
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, [paymentHash]);

  const onPaymentSuccess = (data) => {
    // Redirect or update UI
    console.log('Payment successful!', data);
  };

  return (
    <div className="payment-status">
      <StatusIndicator status={status} />
    </div>
  );
}

function StatusIndicator({ status }) {
  const statusConfig = {
    pending: { icon: '⏳', text: 'Awaiting payment...', color: 'gray' },
    held: { icon: '🔒', text: 'Payment held in escrow', color: 'orange' },
    released: { icon: '✅', text: 'Payment released', color: 'green' },
    refunded: { icon: '↩️', text: 'Payment refunded', color: 'blue' }
  };

  const config = statusConfig[status] || statusConfig.pending;

  return (
    <div className={`status-indicator status-${config.color}`}>
      <span className="status-icon">{config.icon}</span>
      <span className="status-text">{config.text}</span>
    </div>
  );
}

// Backend WebSocket handler
// server.js
const io = require('socket.io')(server);

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('subscribe_payment', ({ paymentHash }) => {
    // Join room for this payment
    socket.join(`payment:${paymentHash}`);
  });

  // ... other socket handlers
});

// In your invoice subscription handler:
ln.subscribeInvoices(async (err, invoice) => {
  if (err) return console.error(err);

  const paymentHash = invoice.r_hash.toString('hex');

  // Emit to all subscribers
  io.to(`payment:${paymentHash}`).emit('payment_update', {
    paymentHash: paymentHash,
    status: invoiceStateToStatus(invoice.state),
    amount: invoice.value,
    settledAt: invoice.settle_date ? new Date(invoice.settle_date * 1000) : null
  });
});
```

---

## Monitoring & Operations

### Essential Metrics to Track

```yaml
Node Health:
  - Uptime percentage
  - Sync status (blockchain and graph)
  - Peer connections count
  - Channel count (active/inactive)
  - Total liquidity (local + remote)

Payment Performance:
  - Invoice creation rate
  - Payment success rate
  - Average payment time
  - Failed payment reasons
  - Fee income from routing

Channel Health:
  - Balance distribution
  - Channel utilization
  - Force-close rate
  - Routing success rate
  - Fee competitiveness

Financial:
  - Total volume processed
  - Revenue from routing fees
  - Platform fees collected
  - Provider payouts
  - On-chain costs
```

### Prometheus Metrics Exporter

```python
#!/usr/bin/env python3
"""
Lightning Node Prometheus Exporter
"""

from prometheus_client import start_http_server, Gauge, Counter
import time
from lightning_client import LightningClient

# Define metrics
node_uptime = Gauge('lnd_uptime_seconds', 'Node uptime in seconds')
channel_count = Gauge('lnd_channels_total', 'Total number of channels', ['state'])
balance_local = Gauge('lnd_balance_local_satoshis', 'Total local balance across channels')
balance_remote = Gauge('lnd_balance_remote_satoshis', 'Total remote balance across channels')
invoices_created = Counter('lnd_invoices_created_total', 'Total invoices created')
invoices_settled = Counter('lnd_invoices_settled_total', 'Total invoices settled')
payments_sent = Counter('lnd_payments_sent_total', 'Total payments sent', ['status'])
routing_events = Counter('lnd_routing_events_total', 'Total routing events')
routing_fees = Counter('lnd_routing_fees_satoshis_total', 'Total routing fees earned')

def collect_metrics(client):
    """Collect metrics from LND"""
    while True:
        try:
            # Get node info
            info = client.get_info()
            node_uptime.set(info.uptime)

            # Get channel stats
            channels = client.stub.ListChannels(ln.ListChannelsRequest())
            active_count = sum(1 for c in channels.channels if c.active)
            inactive_count = len(channels.channels) - active_count

            channel_count.labels(state='active').set(active_count)
            channel_count.labels(state='inactive').set(inactive_count)

            total_local = sum(c.local_balance for c in channels.channels)
            total_remote = sum(c.remote_balance for c in channels.channels)

            balance_local.set(total_local)
            balance_remote.set(total_remote)

            # Get invoice stats
            invoices = client.stub.ListInvoices(ln.ListInvoiceRequest(num_max_invoices=10000))
            settled_invoices = [inv for inv in invoices.invoices if inv.settled]
            invoices_settled.inc(len(settled_invoices))

            # Sleep before next collection
            time.sleep(30)

        except Exception as e:
            print(f"Error collecting metrics: {e}")
            time.sleep(60)

if __name__ == '__main__':
    client = LightningClient()

    # Start Prometheus HTTP server
    start_http_server(9090)
    print("Prometheus exporter running on port 9090")

    # Collect metrics
    collect_metrics(client)
```

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Lightning Network Monitoring",
    "panels": [
      {
        "title": "Channel Balances",
        "type": "graph",
        "targets": [
          {
            "expr": "lnd_balance_local_satoshis",
            "legendFormat": "Local Balance"
          },
          {
            "expr": "lnd_balance_remote_satoshis",
            "legendFormat": "Remote Balance"
          }
        ]
      },
      {
        "title": "Payment Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(lnd_invoices_settled_total[5m]) / rate(lnd_invoices_created_total[5m]) * 100"
          }
        ]
      },
      {
        "title": "Active Channels",
        "type": "gauge",
        "targets": [
          {
            "expr": "lnd_channels_total{state=\"active\"}"
          }
        ]
      },
      {
        "title": "Routing Fee Income",
        "type": "graph",
        "targets": [
          {
            "expr": "increase(lnd_routing_fees_satoshis_total[1h])"
          }
        ]
      }
    ]
  }
}
```

### Alert Configuration

```yaml
# prometheus-alerts.yml
groups:
  - name: lightning_node
    interval: 30s
    rules:
      - alert: NodeDown
        expr: up{job="lnd"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Lightning node is down"
          description: "LND node has been down for more than 2 minutes"

      - alert: LowInboundLiquidity
        expr: lnd_balance_remote_satoshis / (lnd_balance_local_satoshis + lnd_balance_remote_satoshis) < 0.2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low inbound liquidity"
          description: "Inbound liquidity is below 20% - may affect payment reception"

      - alert: HighChannelForceCloseRate
        expr: rate(lnd_channel_force_closes_total[24h]) > 0.01
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "High channel force-close rate"
          description: "More than 1% of channels are being force-closed"

      - alert: LowPaymentSuccessRate
        expr: rate(lnd_invoices_settled_total[1h]) / rate(lnd_invoices_created_total[1h]) < 0.9
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low payment success rate"
          description: "Payment success rate is below 90%"
```

---

## Security Best Practices

### 1. Wallet Security

```bash
# Encrypt wallet with strong password
# During lncli create, use a 20+ character password

# Enable wallet auto-unlock (use with caution)
# Store password in encrypted file
echo "your-secure-password" | gpg --encrypt --recipient your-key > wallet-password.gpg

# Auto-unlock script
#!/bin/bash
PASSWORD=$(gpg --decrypt wallet-password.gpg)
lncli unlock <<< "$PASSWORD"
```

### 2. Macaroon Management

```bash
# Macaroons are LND's authentication tokens

# Create restricted macaroons for specific operations
# Invoice-only macaroon (can't spend funds)
lncli bakemacaroon invoices:write invoices:read

# Read-only macaroon (for monitoring)
lncli bakemacaroon info:read

# Store macaroons securely
chmod 600 ~/.lnd/data/chain/bitcoin/mainnet/*.macaroon
```

### 3. Network Security

```yaml
# lnd.conf security settings

[Application Options]
# Disable REST API on public interface
restlisten=127.0.0.1:8080

# Use strong TLS
tlsautorefresh=true
tlsdisableautofill=true

# Limit RPC connections
rpclisten=127.0.0.1:10009
maxlogfiles=10
maxlogfilesize=10

# Use Tor for privacy (optional)
[tor]
tor.active=true
tor.streamisolation=true
tor.v3=true
```

### 4. Backup Strategy

```bash
#!/bin/bash
# Lightning backup script

BACKUP_DIR="/secure/backup/location"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup channel state
lncli exportchanbackup --all --output_file="${BACKUP_DIR}/channels_${DATE}.backup"

# Backup LND database (when node is stopped)
# tar -czf "${BACKUP_DIR}/lnd_data_${DATE}.tar.gz" ~/.lnd/data

# Encrypt backup
gpg --encrypt --recipient your-key "${BACKUP_DIR}/channels_${DATE}.backup"

# Upload to cloud (optional)
# aws s3 cp "${BACKUP_DIR}/channels_${DATE}.backup.gpg" s3://your-bucket/

# Keep last 30 backups
find "$BACKUP_DIR" -name "channels_*.backup*" -mtime +30 -delete

echo "Backup completed: ${BACKUP_DIR}/channels_${DATE}.backup.gpg"
```

### 5. Watchtower Setup

```bash
# Watchtowers monitor your channels when your node is offline
# They can broadcast penalty transactions if peers cheat

# Enable watchtower client
[wtclient]
wtclient.active=true

# Add watchtower servers
lncli wtclient add 03xxx...@watchtower.example.com:9911

# Verify watchtowers
lncli wtclient towers

# Recommended watchtowers (2025):
# - The Eye of Satoshi (theeye.com)
# - WatchTower.observer
# - Your own watchtower on separate server
```

---

## Cost Analysis

### Infrastructure Costs

```yaml
Monthly Operating Costs:

Self-Hosted LND:
  Server (4 CPU, 8GB RAM, 1TB SSD): $40-80
  Bandwidth (unlimited): Included
  Backup storage (100GB): $5-10
  Monitoring/alerts: $0 (self-hosted)
  Total: $45-90/month

Hosted LND (Voltage):
  Standard node: $50/month
  Backup/monitoring: Included
  Support: Included
  Total: $50/month

Additional Costs:
  Channel opening fees: $10-50 (one-time per channel)
  Channel closing fees: $10-50 (one-time, hopefully rare)
  On-chain deposits/withdrawals: $5-30 per transaction
  Liquidity services: $0-200/month (optional)
```

### Transaction Fee Economics

```
Payment Fees:

Sending:
  Base fee: ~0-1000 millisats (configurable by route)
  Fee rate: ~0.000001-0.0001% (ppm - parts per million)
  Typical total: $0.001-0.01 per payment

Receiving:
  Fee: $0 (receiver doesn't pay routing fees)
  Only pays if invoice generation costs exist

Example:
  $100 payment:
    Sending fee: ~$0.005 (0.005%)
    vs Stripe: $3.20 (3.2%)
    Savings: 99.84%
```

### Revenue from Routing

```
If your node routes payments for others, you earn fees:

Channel Setup:
  - 10 channels, 0.05 BTC each
  - Total capacity: 0.5 BTC ($25,000)
  - Well-connected to major hubs

Fee Settings:
  Base fee: 1000 millisats (0.001 sat)
  Fee rate: 100 ppm (0.01%)

Monthly Routing Volume: 5 BTC ($250,000)
Monthly Fee Income: 0.005 BTC ($250)
Annual Income: 0.06 BTC ($3,000)

ROI: ~12% annually on locked capital
Plus: Improved payment success for your own transactions
```

---

## Testing Strategy

### Testnet Testing

```bash
# Switch to testnet in lnd.conf
[Bitcoin]
bitcoin.testnet=true
bitcoin.mainnet=false

# Get testnet Bitcoin
# https://testnet-faucet.com/btc-testnet/
# https://coinfaucet.eu/en/btc-testnet/

# Open testnet channels
# Connect to well-known testnet nodes

# Test full payment flow:
# 1. Generate invoice
# 2. Pay invoice from another testnet wallet
# 3. Verify payment received
# 4. Test hold invoice escrow
# 5. Test refunds
```

### Integration Tests

```javascript
// tests/lightning-integration.test.js
const LightningService = require('../lightning-service');
const assert = require('assert');

describe('Lightning Integration Tests', () => {
  let ln;

  before(async () => {
    ln = new LightningService();
    // Verify testnet connection
    const info = await ln.getInfo();
    assert(info.testnet, 'Must run on testnet');
  });

  it('should create an invoice', async () => {
    const invoice = await ln.createInvoice({
      amount: 10000,
      memo: 'Test invoice'
    });

    assert(invoice.payment_request);
    assert(invoice.payment_request.startsWith('lntb')); // testnet prefix
  });

  it('should create and settle hold invoice', async () => {
    const holdInvoice = await ln.createHoldInvoice({
      amount: 50000,
      memo: 'Test escrow'
    });

    assert(holdInvoice.preimage);
    assert(holdInvoice.payment_hash);

    // Pay invoice with another wallet...
    // (manual step in test, or use second LND instance)

    // Settle invoice
    const result = await ln.settleInvoice(holdInvoice.preimage);
    assert(result.settled);
  });

  it('should handle invoice expiry', async function() {
    this.timeout(70000); // 70 seconds

    const invoice = await ln.createInvoice({
      amount: 1000,
      memo: 'Expiry test',
      expiry: 60 // 1 minute
    });

    // Wait for expiry
    await new Promise(resolve => setTimeout(resolve, 65000));

    const status = await ln.lookupInvoice(invoice.r_hash);
    assert.equal(status.state, 'CANCELED');
  });
});
```

### Load Testing

```javascript
// load-test.js - Simulate high invoice generation rate
const LightningService = require('./lightning-service');
const ln = new LightningService();

async function loadTest() {
  const invoicesPerSecond = 10;
  const duration = 60; // seconds
  const totalInvoices = invoicesPerSecond * duration;

  console.log(`Generating ${totalInvoices} invoices over ${duration} seconds...`);

  const startTime = Date.now();
  let created = 0;
  let failed = 0;

  const interval = setInterval(async () => {
    for (let i = 0; i < invoicesPerSecond; i++) {
      try {
        await ln.createInvoice({
          amount: Math.floor(Math.random() * 100000) + 1000,
          memo: `Load test invoice ${created + 1}`
        });
        created++;
      } catch (error) {
        console.error('Invoice creation failed:', error);
        failed++;
      }
    }

    console.log(`Progress: ${created}/${totalInvoices} (${failed} failed)`);

    if (created + failed >= totalInvoices) {
      clearInterval(interval);
      const elapsed = (Date.now() - startTime) / 1000;
      console.log(`\nCompleted in ${elapsed}s`);
      console.log(`Success rate: ${(created / (created + failed) * 100).toFixed(2)}%`);
      console.log(`Actual rate: ${(created / elapsed).toFixed(2)} invoices/sec`);
    }
  }, 1000);
}

loadTest();
```

---

## Troubleshooting

### Common Issues

#### 1. Payment Routing Failures

```
Error: "unable to find a path to destination"

Causes:
- Insufficient inbound/outbound liquidity
- No route exists to destination
- Channels offline/inactive

Solutions:
# Check channel balance distribution
lncli listchannels | jq '.channels[] | {balance: .local_balance}'

# Open more channels to well-connected peers
# Add inbound liquidity (Loop In, marketplace)

# Check route to destination
lncli queryroutes --dest=<pubkey> --amt=<amount>
```

#### 2. Channel Force-Close

```
Error: "channel force-closed"

Causes:
- Peer node offline too long
- Uncooperative close
- Protocol violation detected

Impact:
- Funds locked for ~144 blocks (~24 hours)
- On-chain fee costs
- Channel capacity lost

Prevention:
- Use watchtowers
- Maintain good uptime
- Choose reliable peers
- Regular backups
```

#### 3. Invoice Generation Slow

```
Symptom: Invoices take >2 seconds to generate

Causes:
- Graph sync incomplete
- Database performance issues
- High system load

Solutions:
# Check sync status
lncli getinfo | jq '.synced_to_graph'

# Optimize database
lncli compactdb

# Check system resources
top
df -h
```

#### 4. Stuck Payments

```
Symptom: Payment shows "in_flight" indefinitely

Solutions:
# List pending payments
lncli listpayments --include_incomplete

# Track specific payment
lncli trackpayment --payment_hash=<hash>

# If truly stuck (rare), restart LND
sudo systemctl restart lnd
```

### Debug Mode

```bash
# Enable debug logging
# lnd.conf
[Application Options]
debuglevel=debug

# Restart LND
sudo systemctl restart lnd

# Tail logs
tail -f ~/.lnd/logs/bitcoin/mainnet/lnd.log

# Filter specific subsystem
tail -f ~/.lnd/logs/bitcoin/mainnet/lnd.log | grep "RPCS"
```

---

## References

### Official Documentation
- LND Documentation: https://docs.lightning.engineering/
- Lightning Network Specifications (BOLTs): https://github.com/lightning/bolts
- LND GitHub: https://github.com/lightningnetwork/lnd
- LND API Reference: https://lightning.engineering/api-docs/

### Tools & Services
- Voltage (Hosted Nodes): https://voltage.cloud/
- Amboss (Analytics): https://amboss.space/
- 1ML (Node Explorer): https://1ml.com/
- Lightning Loop: https://lightning.engineering/loop/
- ThunderHub (Node Management): https://thunderhub.io/

### Learning Resources
- "Mastering the Lightning Network" (Book): https://github.com/lnbook/lnbook
- Lightning Network Wiki: https://lightningwiki.net/
- Bitcoin Stack Exchange: https://bitcoin.stackexchange.com/

### Community
- Lightning Network Discord: https://discord.gg/lightning
- LND Slack: https://lightningcommunity.slack.com/
- Bitcoin Core Slack: https://bitcoincore.org/slack/

---

**Document Version:** 1.0
**Last Updated:** January 2025
**Author:** Agent 4 - Lightning Network Integration
**Next Steps:** Proceed to stablecoin integration guide
