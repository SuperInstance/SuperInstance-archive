# Stablecoin Integration Guide (USDC on Layer 2)

## Table of Contents
1. [Introduction](#introduction)
2. [Chain Selection Analysis](#chain-selection-analysis)
3. [Architecture Overview](#architecture-overview)
4. [Smart Contract Development](#smart-contract-development)
5. [Web3 Frontend Integration](#web3-frontend-integration)
6. [Backend Integration](#backend-integration)
7. [Gas Fee Management](#gas-fee-management)
8. [Event Monitoring](#event-monitoring)
9. [Multi-Chain Support](#multi-chain-support)
10. [Security Considerations](#security-considerations)
11. [Testing Strategy](#testing-strategy)
12. [Deployment Guide](#deployment-guide)
13. [Cost Analysis](#cost-analysis)
14. [Troubleshooting](#troubleshooting)
15. [References](#references)

---

## Introduction

This guide provides comprehensive instructions for integrating USDC stablecoin payments on Layer 2 networks (Base, Polygon, Arbitrum) into a compute marketplace platform.

### Why Stablecoins?

**Advantages:**
- **Price Stability:** 1:1 USD peg eliminates volatility
- **Low Fees:** L2 transactions cost $0.01-0.50
- **Fast Settlement:** 2-5 second confirmation times
- **Global Access:** No bank account required
- **Programmable:** Smart contract escrow automation
- **Transparent:** All transactions on public blockchain
- **24/7 Availability:** No banking hours

**USDC Specifics:**
- Issued by Circle (regulated financial institution)
- Fully backed by USD reserves (1:1)
- Monthly attestations by Grant Thornton LLP
- Native support on 28+ blockchain networks
- $34B+ in circulation (as of January 2025)
- ERC-20 compatible on Ethereum and L2s

### Use Cases in Compute Marketplace

| Use Case | Benefit |
|----------|---------|
| International payments | No FX fees, instant settlement |
| Large transactions (>$100) | Lower fees than Stripe (0.01% vs 2.9%) |
| Self-custody providers | Receive directly to their wallet |
| Automated escrow | Smart contracts handle trust |
| Underbanked regions | Access without traditional banking |
| Transparent accounting | On-chain audit trail |

---

## Chain Selection Analysis

### Supported Networks (2025)

| Network | USDC Native | Avg Gas Fee | TPS | Finality | Ecosystem Size | Recommendation |
|---------|-------------|-------------|-----|----------|----------------|----------------|
| **Base** | ✅ Yes | $0.02 | 1,000 | 2-3 sec | Fast growing | **Primary** |
| **Polygon** | ✅ Yes | $0.01 | 7,000 | 2-3 sec | Very large | **Secondary** |
| **Arbitrum** | ✅ Yes | $0.10 | 4,000 | 15 min* | Large | Optional |
| **Optimism** | ✅ Yes | $0.08 | 2,000 | 15 min* | Medium | Optional |
| Ethereum L1 | ✅ Yes | $2-15 | 15 | 12 min | Largest | Emergency only |

*Finality includes L1 challenge period for withdrawals

### Recommended Multi-Chain Strategy

**Phase 1:** Base only (fastest to market)
**Phase 2:** Add Polygon (liquidity + lower fees)
**Phase 3:** Add Arbitrum/Optimism if demand exists

### Why Base + Polygon?

**Base:**
```
Pros:
- Built by Coinbase (trusted name)
- Fast growth (9th largest chain in 2025)
- Low fees ($0.01-0.03 average)
- Fast finality (2-3 seconds)
- Optimistic rollup security
- Strong wallet support (Coinbase Wallet, MetaMask)
- 60% of transactions are USDC

Cons:
- Newer ecosystem (launched 2023)
- Smaller liquidity than Polygon
- Withdrawal to L1 has 7-day challenge period

Best For:
- US customers
- Coinbase users
- Future growth positioning
```

**Polygon PoS:**
```
Pros:
- Mature ecosystem (since 2020)
- Very low fees ($0.005-0.02)
- High throughput (7,000 TPS)
- Large DeFi liquidity
- Excellent wallet support
- Fast finality (no L1 wait for withdrawals)

Cons:
- Sidechain vs rollup security model
- More complex bridge architecture

Best For:
- Crypto-native users
- High-frequency transactions
- Cost optimization
```

### USDC Contract Addresses

```javascript
// Mainnet USDC addresses (as of 2025)
const USDC_ADDRESSES = {
  // Layer 2 Networks
  base: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  polygon: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359', // Native USDC
  arbitrum: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
  optimism: '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',

  // Layer 1 (reference)
  ethereum: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',

  // Testnets
  baseSepolia: '0x036CbD53842c5426634e7929541eC2318f3dCF7e',
  polygonMumbai: '0x9999f7fea5938fd3b1e26a12c3f2fb024e194f97',
  arbitrumSepolia: '0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d',
};
```

---

## Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Compute Marketplace Platform                     │
│                                                                       │
│  ┌──────────────┐         ┌──────────────┐        ┌──────────────┐  │
│  │   Frontend   │────────>│   Backend    │───────>│   Database   │  │
│  │  (React +    │         │     API      │        │  (PostgreSQL)│  │
│  │   viem/wagmi)│         │              │        │              │  │
│  └──────────────┘         └──────────────┘        └──────────────┘  │
│         │                         │                                  │
│         │                         │                                  │
│         ▼                         ▼                                  │
│  ┌──────────────┐         ┌──────────────┐                          │
│  │   WalletConnect      │  │ Event Monitor│                          │
│  │   (User Wallet)      │  │ (Alchemy/    │                          │
│  │                      │  │  TheGraph)   │                          │
│  └──────────────┘         └──────────────┘                          │
│         │                         │                                  │
└─────────┼─────────────────────────┼──────────────────────────────────┘
          │                         │
          ▼                         ▼
    ┌──────────────────────────────────────┐
    │      Blockchain Layer (Base/Polygon) │
    │                                       │
    │  ┌────────────────┐  ┌─────────────┐ │
    │  │ USDC Contract  │  │   Escrow    │ │
    │  │   (Circle)     │  │  Contract   │ │
    │  └────────────────┘  └─────────────┘ │
    └──────────────────────────────────────┘
```

### Payment Flow

```
1. Customer initiates payment
   └─> Frontend: Connect wallet (MetaMask/Coinbase Wallet)

2. Backend creates order
   └─> Generates escrow contract call
   └─> Returns transaction data to frontend

3. Frontend prepares transaction
   └─> Check USDC balance
   └─> Request USDC approval (if needed)
   └─> Estimate gas fees

4. Customer approves USDC spending
   └─> One-time approval transaction
   └─> Allows escrow contract to transfer USDC

5. Customer deposits to escrow
   └─> Calls escrow contract
   └─> Transfers USDC from wallet to escrow
   └─> Emits PaymentReceived event

6. Backend monitors blockchain
   └─> Detects PaymentReceived event
   └─> Updates order status to "funded"
   └─> Notifies provider to start work

7. Provider completes job
   └─> Marks job as complete
   └─> Customer or timeout triggers release

8. Payment released
   └─> Escrow contract transfers USDC to provider
   └─> Platform fee transferred to platform wallet
   └─> Emits PaymentReleased event

9. Backend confirms completion
   └─> Updates order status to "completed"
   └─> Archives transaction data
```

---

## Smart Contract Development

### Escrow Contract (Solidity)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title ComputeMarketplaceEscrow
 * @dev Escrow contract for USDC payments in compute marketplace
 * @notice Handles customer deposits, provider payouts, and dispute resolution
 */
contract ComputeMarketplaceEscrow is ReentrancyGuard, Pausable, AccessControl {
    using SafeERC20 for IERC20;

    // Roles
    bytes32 public constant MEDIATOR_ROLE = keccak256("MEDIATOR_ROLE");
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");

    // USDC token contract
    IERC20 public immutable usdc;

    // Platform wallet for fees
    address public platformWallet;

    // Platform fee in basis points (15% = 1500)
    uint256 public platformFeeBps = 1500;

    // Auto-release timeout (30 days)
    uint256 public constant AUTO_RELEASE_TIMEOUT = 30 days;

    // Order states
    enum OrderState {
        Created,       // Order created but not funded
        Funded,        // USDC deposited to escrow
        Completed,     // Job completed, awaiting release
        Released,      // Payment released to provider
        Refunded,      // Payment refunded to customer
        Disputed       // Dispute opened
    }

    // Order structure
    struct Order {
        bytes32 orderId;          // Off-chain order ID
        address customer;
        address provider;
        uint256 amount;           // Total USDC amount (6 decimals)
        uint256 platformFee;      // Platform fee amount
        OrderState state;
        uint256 createdAt;
        uint256 fundedAt;
        uint256 completedAt;
        uint256 autoReleaseAt;    // Auto-release timestamp
    }

    // Order storage
    mapping(bytes32 => Order) public orders;

    // Events
    event OrderCreated(
        bytes32 indexed orderId,
        address indexed customer,
        address indexed provider,
        uint256 amount
    );

    event PaymentReceived(
        bytes32 indexed orderId,
        address indexed customer,
        uint256 amount,
        uint256 platformFee
    );

    event OrderCompleted(
        bytes32 indexed orderId,
        uint256 completedAt
    );

    event PaymentReleased(
        bytes32 indexed orderId,
        address indexed provider,
        uint256 providerAmount,
        uint256 platformFee
    );

    event PaymentRefunded(
        bytes32 indexed orderId,
        address indexed customer,
        uint256 amount
    );

    event DisputeOpened(
        bytes32 indexed orderId,
        address indexed initiator
    );

    event DisputeResolved(
        bytes32 indexed orderId,
        uint256 customerAmount,
        uint256 providerAmount,
        uint256 platformFee
    );

    event PlatformFeeUpdated(uint256 oldFeeBps, uint256 newFeeBps);
    event PlatformWalletUpdated(address oldWallet, address newWallet);

    /**
     * @dev Constructor
     * @param _usdc USDC token address
     * @param _platformWallet Platform wallet address for fees
     */
    constructor(address _usdc, address _platformWallet) {
        require(_usdc != address(0), "Invalid USDC address");
        require(_platformWallet != address(0), "Invalid platform wallet");

        usdc = IERC20(_usdc);
        platformWallet = _platformWallet;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MEDIATOR_ROLE, msg.sender);
        _grantRole(OPERATOR_ROLE, msg.sender);
    }

    /**
     * @notice Create and fund an order in one transaction
     * @param orderId Unique order identifier
     * @param provider Provider's address
     * @param amount Total USDC amount (including platform fee)
     */
    function createAndFundOrder(
        bytes32 orderId,
        address provider,
        uint256 amount
    ) external nonReentrant whenNotPaused {
        require(provider != address(0), "Invalid provider address");
        require(provider != msg.sender, "Cannot be your own provider");
        require(amount > 0, "Amount must be positive");
        require(orders[orderId].customer == address(0), "Order already exists");

        // Calculate platform fee
        uint256 platformFee = (amount * platformFeeBps) / 10000;
        require(platformFee < amount, "Fee exceeds amount");

        // Create order
        Order storage order = orders[orderId];
        order.orderId = orderId;
        order.customer = msg.sender;
        order.provider = provider;
        order.amount = amount;
        order.platformFee = platformFee;
        order.state = OrderState.Funded;
        order.createdAt = block.timestamp;
        order.fundedAt = block.timestamp;
        order.autoReleaseAt = block.timestamp + AUTO_RELEASE_TIMEOUT;

        // Transfer USDC from customer to escrow
        usdc.safeTransferFrom(msg.sender, address(this), amount);

        emit OrderCreated(orderId, msg.sender, provider, amount);
        emit PaymentReceived(orderId, msg.sender, amount, platformFee);
    }

    /**
     * @notice Mark order as completed (job finished)
     * @param orderId Order identifier
     */
    function completeOrder(bytes32 orderId) external nonReentrant {
        Order storage order = orders[orderId];
        require(order.state == OrderState.Funded, "Invalid order state");
        require(
            msg.sender == order.customer ||
            msg.sender == order.provider ||
            hasRole(OPERATOR_ROLE, msg.sender),
            "Unauthorized"
        );

        order.state = OrderState.Completed;
        order.completedAt = block.timestamp;

        emit OrderCompleted(orderId, block.timestamp);
    }

    /**
     * @notice Release payment to provider
     * @param orderId Order identifier
     */
    function releasePayment(bytes32 orderId) external nonReentrant {
        Order storage order = orders[orderId];
        require(order.state == OrderState.Completed, "Order not completed");
        require(
            msg.sender == order.customer ||
            msg.sender == order.provider ||
            hasRole(OPERATOR_ROLE, msg.sender) ||
            block.timestamp >= order.autoReleaseAt,
            "Unauthorized or too early"
        );

        order.state = OrderState.Released;

        uint256 providerAmount = order.amount - order.platformFee;

        // Transfer to provider
        usdc.safeTransfer(order.provider, providerAmount);

        // Transfer platform fee
        usdc.safeTransfer(platformWallet, order.platformFee);

        emit PaymentReleased(orderId, order.provider, providerAmount, order.platformFee);
    }

    /**
     * @notice Refund payment to customer
     * @param orderId Order identifier
     */
    function refundPayment(bytes32 orderId) external nonReentrant {
        Order storage order = orders[orderId];
        require(
            order.state == OrderState.Funded ||
            order.state == OrderState.Completed ||
            order.state == OrderState.Disputed,
            "Invalid state for refund"
        );
        require(
            msg.sender == order.provider ||
            hasRole(MEDIATOR_ROLE, msg.sender),
            "Unauthorized"
        );

        order.state = OrderState.Refunded;

        // Return full amount to customer
        usdc.safeTransfer(order.customer, order.amount);

        emit PaymentRefunded(orderId, order.customer, order.amount);
    }

    /**
     * @notice Open a dispute
     * @param orderId Order identifier
     */
    function openDispute(bytes32 orderId) external {
        Order storage order = orders[orderId];
        require(
            order.state == OrderState.Funded ||
            order.state == OrderState.Completed,
            "Invalid state for dispute"
        );
        require(
            msg.sender == order.customer ||
            msg.sender == order.provider,
            "Unauthorized"
        );

        order.state = OrderState.Disputed;

        emit DisputeOpened(orderId, msg.sender);
    }

    /**
     * @notice Resolve dispute with custom split
     * @param orderId Order identifier
     * @param customerAmount Amount to refund to customer
     * @param providerAmount Amount to pay to provider
     */
    function resolveDispute(
        bytes32 orderId,
        uint256 customerAmount,
        uint256 providerAmount
    ) external nonReentrant onlyRole(MEDIATOR_ROLE) {
        Order storage order = orders[orderId];
        require(order.state == OrderState.Disputed, "Order not disputed");
        require(
            customerAmount + providerAmount <= order.amount,
            "Amounts exceed total"
        );

        order.state = OrderState.Released;

        // Platform receives remainder (partial or full fee)
        uint256 platformAmount = order.amount - customerAmount - providerAmount;

        // Execute transfers
        if (customerAmount > 0) {
            usdc.safeTransfer(order.customer, customerAmount);
        }

        if (providerAmount > 0) {
            usdc.safeTransfer(order.provider, providerAmount);
        }

        if (platformAmount > 0) {
            usdc.safeTransfer(platformWallet, platformAmount);
        }

        emit DisputeResolved(orderId, customerAmount, providerAmount, platformAmount);
    }

    /**
     * @notice Get order details
     * @param orderId Order identifier
     */
    function getOrder(bytes32 orderId) external view returns (
        address customer,
        address provider,
        uint256 amount,
        uint256 platformFee,
        OrderState state,
        uint256 createdAt,
        uint256 fundedAt,
        uint256 completedAt
    ) {
        Order storage order = orders[orderId];
        return (
            order.customer,
            order.provider,
            order.amount,
            order.platformFee,
            order.state,
            order.createdAt,
            order.fundedAt,
            order.completedAt
        );
    }

    // Admin functions

    /**
     * @notice Update platform fee
     * @param newFeeBps New fee in basis points
     */
    function updatePlatformFee(uint256 newFeeBps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newFeeBps <= 2500, "Fee too high (max 25%)");
        uint256 oldFee = platformFeeBps;
        platformFeeBps = newFeeBps;
        emit PlatformFeeUpdated(oldFee, newFeeBps);
    }

    /**
     * @notice Update platform wallet
     * @param newWallet New platform wallet address
     */
    function updatePlatformWallet(address newWallet) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newWallet != address(0), "Invalid wallet address");
        address oldWallet = platformWallet;
        platformWallet = newWallet;
        emit PlatformWalletUpdated(oldWallet, newWallet);
    }

    /**
     * @notice Pause contract
     */
    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause contract
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    /**
     * @notice Emergency withdraw (only if paused)
     * @dev Should only be used in extreme circumstances
     */
    function emergencyWithdraw(address token, uint256 amount)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
        whenPaused
    {
        IERC20(token).safeTransfer(msg.sender, amount);
    }
}
```

### Deployment Script (Hardhat)

```javascript
// scripts/deploy-escrow.js
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString());

  // Network-specific USDC addresses
  const USDC_ADDRESSES = {
    base: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    polygon: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    baseSepolia: "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
  };

  const network = hre.network.name;
  const usdcAddress = USDC_ADDRESSES[network];

  if (!usdcAddress) {
    throw new Error(`USDC address not configured for network: ${network}`);
  }

  // Platform wallet (replace with your actual wallet)
  const platformWallet = process.env.PLATFORM_WALLET || deployer.address;

  console.log(`Deploying to network: ${network}`);
  console.log(`USDC address: ${usdcAddress}`);
  console.log(`Platform wallet: ${platformWallet}`);

  // Deploy escrow contract
  const Escrow = await hre.ethers.getContractFactory("ComputeMarketplaceEscrow");
  const escrow = await Escrow.deploy(usdcAddress, platformWallet);

  await escrow.deployed();

  console.log("Escrow contract deployed to:", escrow.address);

  // Verify contract on block explorer
  if (network !== "hardhat" && network !== "localhost") {
    console.log("Waiting for block confirmations...");
    await escrow.deployTransaction.wait(6);

    console.log("Verifying contract...");
    try {
      await hre.run("verify:verify", {
        address: escrow.address,
        constructorArguments: [usdcAddress, platformWallet],
      });
      console.log("Contract verified!");
    } catch (error) {
      console.log("Verification failed:", error.message);
    }
  }

  // Save deployment info
  const fs = require("fs");
  const deploymentInfo = {
    network: network,
    escrowAddress: escrow.address,
    usdcAddress: usdcAddress,
    platformWallet: platformWallet,
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
  };

  fs.writeFileSync(
    `deployments/${network}-deployment.json`,
    JSON.stringify(deploymentInfo, null, 2)
  );

  console.log("Deployment info saved to deployments/" + network + "-deployment.json");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
```

### Hardhat Configuration

```javascript
// hardhat.config.js
require("@nomicfoundation/hardhat-toolbox");
require("@nomiclabs/hardhat-etherscan");
require("dotenv").config();

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },

  networks: {
    // Base Mainnet
    base: {
      url: "https://mainnet.base.org",
      accounts: [process.env.PRIVATE_KEY],
      chainId: 8453,
      gasPrice: 1000000000, // 1 gwei
    },

    // Base Sepolia Testnet
    baseSepolia: {
      url: "https://sepolia.base.org",
      accounts: [process.env.PRIVATE_KEY],
      chainId: 84532,
      gasPrice: 1000000000,
    },

    // Polygon Mainnet
    polygon: {
      url: "https://polygon-rpc.com",
      accounts: [process.env.PRIVATE_KEY],
      chainId: 137,
      gasPrice: 50000000000, // 50 gwei
    },

    // Polygon Mumbai Testnet
    polygonMumbai: {
      url: "https://rpc-mumbai.maticvigil.com",
      accounts: [process.env.PRIVATE_KEY],
      chainId: 80001,
      gasPrice: 50000000000,
    },

    // Arbitrum One
    arbitrum: {
      url: "https://arb1.arbitrum.io/rpc",
      accounts: [process.env.PRIVATE_KEY],
      chainId: 42161,
    },
  },

  etherscan: {
    apiKey: {
      base: process.env.BASESCAN_API_KEY,
      baseSepolia: process.env.BASESCAN_API_KEY,
      polygon: process.env.POLYGONSCAN_API_KEY,
      polygonMumbai: process.env.POLYGONSCAN_API_KEY,
      arbitrumOne: process.env.ARBISCAN_API_KEY,
    },
    customChains: [
      {
        network: "base",
        chainId: 8453,
        urls: {
          apiURL: "https://api.basescan.org/api",
          browserURL: "https://basescan.org"
        }
      },
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api-sepolia.basescan.org/api",
          browserURL: "https://sepolia.basescan.org"
        }
      }
    ]
  },

  gasReporter: {
    enabled: process.env.REPORT_GAS === "true",
    currency: "USD",
    coinmarketcap: process.env.COINMARKETCAP_API_KEY,
  },
};
```

---

## Web3 Frontend Integration

### Installation

```bash
# Install dependencies
npm install viem wagmi @tanstack/react-query
npm install @rainbow-me/rainbowkit  # Optional: Nice wallet connection UI
```

### Wagmi Configuration

```typescript
// config/wagmi.ts
import { createConfig, http } from 'wagmi';
import { base, polygon, baseSepolia } from 'wagmi/chains';
import { coinbaseWallet, metaMask, walletConnect } from 'wagmi/connectors';

export const config = createConfig({
  chains: [base, polygon, baseSepolia],
  connectors: [
    metaMask(),
    coinbaseWallet({ appName: 'Compute Marketplace' }),
    walletConnect({
      projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID!,
    }),
  ],
  transports: {
    [base.id]: http('https://mainnet.base.org'),
    [polygon.id]: http('https://polygon-rpc.com'),
    [baseSepolia.id]: http('https://sepolia.base.org'),
  },
});
```

### React Component - Payment Flow

```typescript
// components/USDCPayment.tsx
'use client';

import { useState, useEffect } from 'react';
import {
  useAccount,
  useBalance,
  useWriteContract,
  useWaitForTransactionReceipt,
  useReadContract,
} from 'wagmi';
import { parseUnits, formatUnits, Address } from 'viem';
import { base } from 'wagmi/chains';

// Contract ABIs
import ESCROW_ABI from '@/abis/ComputeMarketplaceEscrow.json';
import ERC20_ABI from '@/abis/ERC20.json';

interface USDCPaymentProps {
  orderId: string;
  providerAddress: Address;
  amountUSD: number;
  onSuccess: () => void;
}

const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'; // Base mainnet
const ESCROW_ADDRESS = '0x...'; // Your deployed escrow contract

export default function USDCPayment({
  orderId,
  providerAddress,
  amountUSD,
  onSuccess,
}: USDCPaymentProps) {
  const { address, isConnected } = useAccount();
  const [step, setStep] = useState<'approve' | 'deposit' | 'complete'>('approve');
  const [txHash, setTxHash] = useState<Address | null>(null);

  // Convert USD amount to USDC (6 decimals)
  const amountUSDC = parseUnits(amountUSD.toString(), 6);

  // Check USDC balance
  const { data: usdcBalance } = useBalance({
    address: address,
    token: USDC_ADDRESS,
    chainId: base.id,
  });

  // Check current USDC allowance
  const { data: currentAllowance } = useReadContract({
    address: USDC_ADDRESS,
    abi: ERC20_ABI,
    functionName: 'allowance',
    args: [address, ESCROW_ADDRESS],
    chainId: base.id,
  });

  // Write contracts hooks
  const {
    writeContract: approveUSDC,
    data: approveHash,
    isPending: isApproving,
  } = useWriteContract();

  const {
    writeContract: depositToEscrow,
    data: depositHash,
    isPending: isDepositing,
  } = useWriteContract();

  // Wait for approval transaction
  const { isLoading: isApproveTxLoading, isSuccess: isApproveTxSuccess } =
    useWaitForTransactionReceipt({
      hash: approveHash,
    });

  // Wait for deposit transaction
  const { isLoading: isDepositTxLoading, isSuccess: isDepositTxSuccess } =
    useWaitForTransactionReceipt({
      hash: depositHash,
    });

  // Check if approval is needed
  const needsApproval =
    !currentAllowance || (currentAllowance as bigint) < amountUSDC;

  // Handle approval transaction
  const handleApprove = async () => {
    try {
      approveUSDC({
        address: USDC_ADDRESS,
        abi: ERC20_ABI,
        functionName: 'approve',
        args: [ESCROW_ADDRESS, amountUSDC],
        chainId: base.id,
      });
    } catch (error) {
      console.error('Approval failed:', error);
    }
  };

  // Handle deposit transaction
  const handleDeposit = async () => {
    try {
      const orderIdBytes = `0x${Buffer.from(orderId).toString('hex').padEnd(64, '0')}`;

      depositToEscrow({
        address: ESCROW_ADDRESS,
        abi: ESCROW_ABI,
        functionName: 'createAndFundOrder',
        args: [orderIdBytes, providerAddress, amountUSDC],
        chainId: base.id,
      });
    } catch (error) {
      console.error('Deposit failed:', error);
    }
  };

  // Update steps based on transaction status
  useEffect(() => {
    if (isApproveTxSuccess) {
      setStep('deposit');
    }
  }, [isApproveTxSuccess]);

  useEffect(() => {
    if (isDepositTxSuccess) {
      setStep('complete');
      setTxHash(depositHash || null);
      onSuccess();
    }
  }, [isDepositTxSuccess, depositHash]);

  if (!isConnected) {
    return (
      <div className="payment-container">
        <p>Please connect your wallet to continue</p>
      </div>
    );
  }

  // Check sufficient balance
  const hasSufficientBalance =
    usdcBalance && usdcBalance.value >= amountUSDC;

  if (!hasSufficientBalance) {
    return (
      <div className="payment-container error">
        <h3>Insufficient USDC Balance</h3>
        <p>
          Required: {formatUnits(amountUSDC, 6)} USDC
          <br />
          Your balance: {usdcBalance ? formatUnits(usdcBalance.value, 6) : '0'} USDC
        </p>
        <a
          href="https://www.coinbase.com/onramp"
          target="_blank"
          rel="noopener noreferrer"
        >
          Buy USDC
        </a>
      </div>
    );
  }

  return (
    <div className="payment-container">
      <h3>Pay with USDC</h3>

      <div className="payment-details">
        <p>
          <strong>Amount:</strong> {formatUnits(amountUSDC, 6)} USDC
        </p>
        <p>
          <strong>Network:</strong> Base
        </p>
        <p>
          <strong>Provider:</strong> {providerAddress.slice(0, 6)}...{providerAddress.slice(-4)}
        </p>
      </div>

      {/* Step 1: Approve USDC */}
      {step === 'approve' && (
        <div className="step">
          <h4>Step 1: Approve USDC</h4>
          <p>Allow the escrow contract to transfer your USDC</p>
          <button
            onClick={handleApprove}
            disabled={isApproving || isApproveTxLoading}
          >
            {isApproving || isApproveTxLoading
              ? 'Approving...'
              : needsApproval
              ? 'Approve USDC'
              : 'Already Approved - Continue'}
          </button>
        </div>
      )}

      {/* Step 2: Deposit to Escrow */}
      {step === 'deposit' && (
        <div className="step">
          <h4>Step 2: Deposit to Escrow</h4>
          <p>Transfer USDC to escrow contract</p>
          <button
            onClick={handleDeposit}
            disabled={isDepositing || isDepositTxLoading}
          >
            {isDepositing || isDepositTxLoading
              ? 'Depositing...'
              : 'Deposit USDC'}
          </button>
        </div>
      )}

      {/* Step 3: Complete */}
      {step === 'complete' && (
        <div className="step success">
          <h4>✓ Payment Complete!</h4>
          <p>Your USDC has been deposited to escrow</p>
          {txHash && (
            <a
              href={`https://basescan.org/tx/${txHash}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              View Transaction
            </a>
          )}
        </div>
      )}

      {/* Gas estimate (optional) */}
      <div className="gas-estimate">
        <small>Estimated gas fee: ~$0.02</small>
      </div>
    </div>
  );
}
```

### Wallet Connection Component

```typescript
// components/WalletConnect.tsx
'use client';

import { useAccount, useConnect, useDisconnect } from 'wagmi';
import { useEffect } from 'react';

export default function WalletConnect() {
  const { address, isConnected, chain } = useAccount();
  const { connect, connectors, error, isPending } = useConnect();
  const { disconnect } = useDisconnect();

  // Auto-connect to previously connected wallet
  useEffect(() => {
    const lastConnector = localStorage.getItem('lastConnector');
    if (lastConnector && !isConnected) {
      const connector = connectors.find(c => c.id === lastConnector);
      if (connector) {
        connect({ connector });
      }
    }
  }, []);

  const handleConnect = (connector: any) => {
    connect({ connector });
    localStorage.setItem('lastConnector', connector.id);
  };

  if (isConnected) {
    return (
      <div className="wallet-connected">
        <div className="wallet-info">
          <span className="network">{chain?.name}</span>
          <span className="address">
            {address?.slice(0, 6)}...{address?.slice(-4)}
          </span>
        </div>
        <button onClick={() => disconnect()}>Disconnect</button>
      </div>
    );
  }

  return (
    <div className="wallet-connect">
      <h3>Connect Wallet</h3>
      <div className="connectors">
        {connectors.map((connector) => (
          <button
            key={connector.id}
            onClick={() => handleConnect(connector)}
            disabled={isPending}
          >
            {connector.name}
          </button>
        ))}
      </div>
      {error && <div className="error">{error.message}</div>}
    </div>
  );
}
```

---

## Backend Integration

### Event Monitoring with Viem

```typescript
// services/blockchain-monitor.ts
import { createPublicClient, http, parseAbiItem, Address } from 'viem';
import { base } from 'viem/chains';
import ESCROW_ABI from '../abis/ComputeMarketplaceEscrow.json';

const ESCROW_ADDRESS = process.env.ESCROW_CONTRACT_ADDRESS as Address;

const client = createPublicClient({
  chain: base,
  transport: http(process.env.BASE_RPC_URL),
});

/**
 * Monitor PaymentReceived events
 */
export async function watchPaymentEvents() {
  const unwatch = client.watchContractEvent({
    address: ESCROW_ADDRESS,
    abi: ESCROW_ABI,
    eventName: 'PaymentReceived',
    onLogs: async (logs) => {
      for (const log of logs) {
        const { orderId, customer, amount, platformFee } = log.args;

        console.log('Payment received:', {
          orderId,
          customer,
          amount: amount.toString(),
          platformFee: platformFee.toString(),
        });

        // Update database
        await updateOrderStatus(orderId, 'funded', {
          transactionHash: log.transactionHash,
          blockNumber: log.blockNumber,
          customer: customer,
          amount: amount,
          platformFee: platformFee,
        });

        // Notify provider
        await notifyProvider(orderId);
      }
    },
  });

  return unwatch;
}

/**
 * Monitor PaymentReleased events
 */
export async function watchReleaseEvents() {
  const unwatch = client.watchContractEvent({
    address: ESCROW_ADDRESS,
    abi: ESCROW_ABI,
    eventName: 'PaymentReleased',
    onLogs: async (logs) => {
      for (const log of logs) {
        const { orderId, provider, providerAmount, platformFee } = log.args;

        console.log('Payment released:', {
          orderId,
          provider,
          providerAmount: providerAmount.toString(),
          platformFee: platformFee.toString(),
        });

        // Update database
        await updateOrderStatus(orderId, 'completed', {
          transactionHash: log.transactionHash,
          blockNumber: log.blockNumber,
          provider: provider,
          providerAmount: providerAmount,
          platformFee: platformFee,
        });

        // Notify both parties
        await notifyCompletion(orderId);
      }
    },
  });

  return unwatch;
}

/**
 * Get past events (for historical sync)
 */
export async function syncHistoricalEvents(fromBlock: bigint) {
  const logs = await client.getLogs({
    address: ESCROW_ADDRESS,
    events: parseAbiItem([
      'event PaymentReceived(bytes32 indexed orderId, address indexed customer, uint256 amount, uint256 platformFee)',
    ]),
    fromBlock: fromBlock,
    toBlock: 'latest',
  });

  for (const log of logs) {
    // Process historical events
    // ...
  }
}

// Helper functions
async function updateOrderStatus(orderId: string, status: string, data: any) {
  // Update database
  // Implementation depends on your database
}

async function notifyProvider(orderId: string) {
  // Send notification to provider
  // Email, WebSocket, push notification, etc.
}

async function notifyCompletion(orderId: string) {
  // Notify customer and provider of completion
}
```

### API Endpoints

```typescript
// api/payments/usdc/create.ts
import { NextApiRequest, NextApiResponse } from 'next';
import { createPublicClient, http, encodeFunctionData, Address } from 'viem';
import { base } from 'viem/chains';
import ESCROW_ABI from '@/abis/ComputeMarketplaceEscrow.json';
import { prisma } from '@/lib/prisma';

const ESCROW_ADDRESS = process.env.ESCROW_CONTRACT_ADDRESS as Address;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { orderId, customerId, providerId, amount } = req.body;

    // Validate inputs
    if (!orderId || !customerId || !providerId || !amount) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Get customer and provider details
    const customer = await prisma.user.findUnique({ where: { id: customerId } });
    const provider = await prisma.user.findUnique({ where: { id: providerId } });

    if (!customer || !provider) {
      return res.status(404).json({ error: 'User not found' });
    }

    if (!provider.walletAddress) {
      return res.status(400).json({ error: 'Provider has no wallet address' });
    }

    // Calculate platform fee (15%)
    const platformFee = Math.floor(amount * 0.15);
    const totalAmount = amount;

    // Create order in database
    const order = await prisma.order.create({
      data: {
        id: orderId,
        customerId: customerId,
        providerId: providerId,
        amount: totalAmount,
        platformFee: platformFee,
        paymentMethod: 'usdc',
        paymentNetwork: 'base',
        status: 'awaiting_payment',
      },
    });

    // Prepare transaction data for frontend
    const orderIdBytes = `0x${Buffer.from(orderId).toString('hex').padEnd(64, '0')}`;

    res.status(200).json({
      orderId: orderId,
      escrowAddress: ESCROW_ADDRESS,
      providerAddress: provider.walletAddress,
      amount: totalAmount,
      platformFee: platformFee,
      orderIdBytes: orderIdBytes,
      network: 'base',
      chainId: 8453,
    });
  } catch (error) {
    console.error('Create payment error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}
```

```typescript
// api/payments/usdc/status.ts
import { NextApiRequest, NextApiResponse } from 'next';
import { createPublicClient, http, Address } from 'viem';
import { base } from 'viem/chains';
import ESCROW_ABI from '@/abis/ComputeMarketplaceEscrow.json';

const ESCROW_ADDRESS = process.env.ESCROW_CONTRACT_ADDRESS as Address;

const client = createPublicClient({
  chain: base,
  transport: http(process.env.BASE_RPC_URL),
});

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { orderId } = req.query;

    if (!orderId || typeof orderId !== 'string') {
      return res.status(400).json({ error: 'Invalid order ID' });
    }

    // Convert orderId to bytes32
    const orderIdBytes = `0x${Buffer.from(orderId).toString('hex').padEnd(64, '0')}`;

    // Query smart contract
    const orderData = await client.readContract({
      address: ESCROW_ADDRESS,
      abi: ESCROW_ABI,
      functionName: 'getOrder',
      args: [orderIdBytes],
    });

    const [
      customer,
      provider,
      amount,
      platformFee,
      state,
      createdAt,
      fundedAt,
      completedAt,
    ] = orderData as any[];

    // Map state enum to string
    const states = ['Created', 'Funded', 'Completed', 'Released', 'Refunded', 'Disputed'];
    const stateString = states[state] || 'Unknown';

    res.status(200).json({
      orderId: orderId,
      customer: customer,
      provider: provider,
      amount: amount.toString(),
      platformFee: platformFee.toString(),
      state: stateString,
      createdAt: Number(createdAt),
      fundedAt: Number(fundedAt),
      completedAt: Number(completedAt),
    });
  } catch (error) {
    console.error('Status check error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}
```

---

## Gas Fee Management

### Gas Estimation

```typescript
// utils/gas.ts
import { createPublicClient, http, parseUnits, Address } from 'viem';
import { base } from 'viem/chains';

const client = createPublicClient({
  chain: base,
  transport: http(),
});

/**
 * Estimate gas for USDC approval
 */
export async function estimateApprovalGas(
  userAddress: Address,
  spenderAddress: Address,
  amount: bigint
) {
  try {
    const gasEstimate = await client.estimateGas({
      account: userAddress,
      to: USDC_ADDRESS,
      data: encodeFunctionData({
        abi: ERC20_ABI,
        functionName: 'approve',
        args: [spenderAddress, amount],
      }),
    });

    const gasPrice = await client.getGasPrice();
    const gasCost = gasEstimate * gasPrice;

    return {
      gasEstimate: gasEstimate.toString(),
      gasPrice: gasPrice.toString(),
      gasCostWei: gasCost.toString(),
      gasCostEth: formatEther(gasCost),
      gasCostUSD: await convertEthToUSD(Number(formatEther(gasCost))),
    };
  } catch (error) {
    console.error('Gas estimation failed:', error);
    throw error;
  }
}

/**
 * Estimate gas for escrow deposit
 */
export async function estimateDepositGas(
  userAddress: Address,
  orderId: string,
  providerAddress: Address,
  amount: bigint
) {
  try {
    const orderIdBytes = `0x${Buffer.from(orderId).toString('hex').padEnd(64, '0')}`;

    const gasEstimate = await client.estimateGas({
      account: userAddress,
      to: ESCROW_ADDRESS,
      data: encodeFunctionData({
        abi: ESCROW_ABI,
        functionName: 'createAndFundOrder',
        args: [orderIdBytes, providerAddress, amount],
      }),
    });

    const gasPrice = await client.getGasPrice();
    const gasCost = gasEstimate * gasPrice;

    return {
      gasEstimate: gasEstimate.toString(),
      gasPrice: gasPrice.toString(),
      gasCostWei: gasCost.toString(),
      gasCostEth: formatEther(gasCost),
      gasCostUSD: await convertEthToUSD(Number(formatEther(gasCost))),
    };
  } catch (error) {
    console.error('Gas estimation failed:', error);
    throw error;
  }
}

/**
 * Get current gas price in different units
 */
export async function getGasPrices() {
  const gasPrice = await client.getGasPrice();

  return {
    wei: gasPrice.toString(),
    gwei: formatGwei(gasPrice),
    eth: formatEther(gasPrice),
  };
}

/**
 * Convert ETH to USD (using price oracle or API)
 */
async function convertEthToUSD(ethAmount: number): Promise<number> {
  // Use price oracle or API like CoinGecko
  const response = await fetch(
    'https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd'
  );
  const data = await response.json();
  const ethPrice = data.ethereum.usd;

  return ethAmount * ethPrice;
}
```

### Gas Fee Subsidy (Optional)

```solidity
// contracts/GaslessEscrow.sol
// Meta-transaction support for gasless deposits

import "@openzeppelin/contracts/metatx/ERC2771Context.sol";

contract GaslessEscrow is ComputeMarketplaceEscrow, ERC2771Context {
    constructor(
        address _usdc,
        address _platformWallet,
        address _trustedForwarder
    )
        ComputeMarketplaceEscrow(_usdc, _platformWallet)
        ERC2771Context(_trustedForwarder)
    {}

    // Override _msgSender for meta-transactions
    function _msgSender()
        internal
        view
        override(Context, ERC2771Context)
        returns (address)
    {
        return ERC2771Context._msgSender();
    }

    // Override _msgData for meta-transactions
    function _msgData()
        internal
        view
        override(Context, ERC2771Context)
        returns (bytes calldata)
    {
        return ERC2771Context._msgData();
    }
}
```

---

## Event Monitoring

### Using Alchemy Webhooks

```typescript
// services/alchemy-webhook.ts
import { Alchemy, Network } from 'alchemy-sdk';

const settings = {
  apiKey: process.env.ALCHEMY_API_KEY,
  network: Network.BASE_MAINNET,
};

const alchemy = new Alchemy(settings);

/**
 * Setup webhook for contract events
 */
export async function setupWebhook() {
  const webhook = await alchemy.notify.createWebhook(
    'https://your-api.com/webhooks/alchemy',
    {
      type: 'ADDRESS_ACTIVITY',
      addresses: [ESCROW_ADDRESS],
      network: Network.BASE_MAINNET,
    }
  );

  console.log('Webhook created:', webhook.id);
  return webhook;
}

/**
 * Handle incoming webhook
 */
export async function handleWebhook(req: NextApiRequest, res: NextApiResponse) {
  const { event } = req.body;

  // Verify webhook signature
  const signature = req.headers['x-alchemy-signature'];
  if (!verifySignature(req.body, signature)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  // Process event
  for (const log of event.logs) {
    const topic = log.topics[0];

    // PaymentReceived event
    if (topic === PAYMENT_RECEIVED_TOPIC) {
      await handlePaymentReceived(log);
    }

    // PaymentReleased event
    if (topic === PAYMENT_RELEASED_TOPIC) {
      await handlePaymentReleased(log);
    }
  }

  res.status(200).json({ success: true });
}
```

### Using TheGraph Subgraph

```graphql
# schema.graphql
type Order @entity {
  id: ID!
  orderId: Bytes!
  customer: Bytes!
  provider: Bytes!
  amount: BigInt!
  platformFee: BigInt!
  state: OrderState!
  createdAt: BigInt!
  fundedAt: BigInt
  completedAt: BigInt
  transactionHash: Bytes!
  blockNumber: BigInt!
}

enum OrderState {
  Created
  Funded
  Completed
  Released
  Refunded
  Disputed
}

type PaymentEvent @entity {
  id: ID!
  orderId: Bytes!
  eventType: EventType!
  from: Bytes!
  to: Bytes
  amount: BigInt!
  timestamp: BigInt!
  transactionHash: Bytes!
  blockNumber: BigInt!
}

enum EventType {
  PaymentReceived
  PaymentReleased
  PaymentRefunded
  DisputeOpened
  DisputeResolved
}
```

```typescript
// subgraph/src/mapping.ts
import { PaymentReceived, PaymentReleased } from '../generated/Escrow/Escrow';
import { Order, PaymentEvent } from '../generated/schema';

export function handlePaymentReceived(event: PaymentReceived): void {
  let order = Order.load(event.params.orderId.toHex());

  if (!order) {
    order = new Order(event.params.orderId.toHex());
    order.orderId = event.params.orderId;
    order.customer = event.params.customer;
    order.amount = event.params.amount;
    order.platformFee = event.params.platformFee;
    order.state = 'Funded';
    order.fundedAt = event.block.timestamp;
    order.transactionHash = event.transaction.hash;
    order.blockNumber = event.block.number;
    order.save();
  }

  // Create payment event
  let paymentEvent = new PaymentEvent(
    event.transaction.hash.toHex() + '-' + event.logIndex.toString()
  );
  paymentEvent.orderId = event.params.orderId;
  paymentEvent.eventType = 'PaymentReceived';
  paymentEvent.from = event.params.customer;
  paymentEvent.amount = event.params.amount;
  paymentEvent.timestamp = event.block.timestamp;
  paymentEvent.transactionHash = event.transaction.hash;
  paymentEvent.blockNumber = event.block.number;
  paymentEvent.save();
}

export function handlePaymentReleased(event: PaymentReleased): void {
  let order = Order.load(event.params.orderId.toHex());

  if (order) {
    order.state = 'Released';
    order.completedAt = event.block.timestamp;
    order.save();
  }

  // Create payment event
  let paymentEvent = new PaymentEvent(
    event.transaction.hash.toHex() + '-' + event.logIndex.toString()
  );
  paymentEvent.orderId = event.params.orderId;
  paymentEvent.eventType = 'PaymentReleased';
  paymentEvent.from = event.address;
  paymentEvent.to = event.params.provider;
  paymentEvent.amount = event.params.providerAmount;
  paymentEvent.timestamp = event.block.timestamp;
  paymentEvent.transactionHash = event.transaction.hash;
  paymentEvent.blockNumber = event.block.number;
  paymentEvent.save();
}
```

---

(Continued due to length - this document covers approximately 700 lines. The remaining sections for Multi-Chain Support, Security, Testing, Deployment, Cost Analysis, Troubleshooting, and References would follow similar comprehensive patterns.)

**Document Version:** 1.0
**Last Updated:** January 2025
**Author:** Agent 4 - Stablecoin Integration
**Status:** Part 1 of 2 (Core Implementation)
