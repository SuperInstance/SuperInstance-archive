# SMART CONTRACT DEPLOYMENT GUIDE
## ActiveLog, Inc. Equity Management Contracts

**Version:** 1.0  
**Date:** 2025  
**Network:** Ethereum Mainnet / Polygon / Arbitrum  

---

## OVERVIEW

This guide provides instructions for deploying the ActiveLog smart contract suite for equity management, regulatory compliance, and automated governance. The contracts implement SEC Regulation CF requirements and provide comprehensive equity management capabilities.

---

## CONTRACT ARCHITECTURE

### 1. Core Contracts

**ActiveLogShareToken.sol**
- ERC20 token representing equity shares
- Implements SEC Reg CF investment limits
- Automated dividend distribution
- Multi-class share structure (Common A/B/C, Preferred)

**VestingContract.sol**
- Employee stock option vesting
- Founder share vesting with acceleration
- Cliff periods and monthly vesting
- Change of control acceleration

**GovernanceContract.sol**
- Shareholder voting system
- Proposal creation and execution
- Multi-class voting rights
- Quorum and majority requirements

**ComplianceAutomation.sol**
- KYC/AML verification
- SEC regulatory reporting
- Audit trail generation
- Geographic restrictions

---

## DEPLOYMENT PREREQUISITES

### 1. Development Environment

```bash
# Install Node.js and npm
node --version  # v18.0.0+
npm --version   # v8.0.0+

# Install Hardhat development framework
npm install --save-dev hardhat
npm install --save-dev @nomiclabs/hardhat-ethers ethers

# Install OpenZeppelin contracts
npm install @openzeppelin/contracts

# Install additional dependencies
npm install --save-dev @nomiclabs/hardhat-waffle chai
```

### 2. Network Configuration

```javascript
// hardhat.config.js
require("@nomiclabs/hardhat-waffle");

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    mainnet: {
      url: process.env.MAINNET_RPC_URL,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      gasPrice: 20000000000 // 20 gwei
    },
    polygon: {
      url: "https://polygon-rpc.com/",
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      gasPrice: 30000000000 // 30 gwei
    },
    arbitrum: {
      url: "https://arb1.arbitrum.io/rpc",
      accounts: [process.env.DEPLOYER_PRIVATE_KEY]
    }
  }
};
```

### 3. Environment Variables

```bash
# .env file
DEPLOYER_PRIVATE_KEY=0x...
MAINNET_RPC_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY
COMPANY_MULTISIG=0x...
COMPLIANCE_OFFICER=0x...
```

---

## DEPLOYMENT SEQUENCE

### 1. Deploy Share Token Contract

```javascript
// scripts/deploy-share-token.js
const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  
  console.log("Deploying with account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString());
  
  // Deploy share token
  const ShareToken = await ethers.getContractFactory("ActiveLogShareToken");
  const shareToken = await ShareToken.deploy(
    "ActiveLog Shares",           // Token name
    "ALOG",                      // Token symbol
    ethers.utils.parseEther("1000000"), // $1M valuation
    1000000                      // 1M total shares
  );
  
  await shareToken.deployed();
  console.log("ShareToken deployed to:", shareToken.address);
  
  // Verify on Etherscan
  await hre.run("verify:verify", {
    address: shareToken.address,
    constructorArguments: [
      "ActiveLog Shares",
      "ALOG", 
      ethers.utils.parseEther("1000000"),
      1000000
    ],
  });
  
  return shareToken.address;
}
```

### 2. Deploy Vesting Contract

```javascript
// scripts/deploy-vesting.js
async function deployVesting(shareTokenAddress) {
  const VestingContract = await ethers.getContractFactory("VestingContract");
  const vesting = await VestingContract.deploy(shareTokenAddress);
  
  await vesting.deployed();
  console.log("VestingContract deployed to:", vesting.address);
  
  return vesting.address;
}
```

### 3. Deploy Governance Contract

```javascript
// scripts/deploy-governance.js
async function deployGovernance(shareTokenAddress) {
  const GovernanceContract = await ethers.getContractFactory("GovernanceContract");
  const governance = await GovernanceContract.deploy(shareTokenAddress);
  
  await governance.deployed();
  console.log("GovernanceContract deployed to:", governance.address);
  
  return governance.address;
}
```

### 4. Deploy Compliance Contract

```javascript
// scripts/deploy-compliance.js
async function deployCompliance(complianceOfficerAddress) {
  const ComplianceAutomation = await ethers.getContractFactory("ComplianceAutomation");
  const compliance = await ComplianceAutomation.deploy(complianceOfficerAddress);
  
  await compliance.deployed();
  console.log("ComplianceAutomation deployed to:", compliance.address);
  
  return compliance.address;
}
```

### 5. Complete Deployment Script

```javascript
// scripts/deploy-all.js
const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  
  // Company parameters
  const COMPANY_VALUATION = ethers.utils.parseEther("1000000"); // $1M
  const TOTAL_SHARES = 1000000; // 1M shares
  const COMPLIANCE_OFFICER = process.env.COMPLIANCE_OFFICER;
  
  console.log("=== ActiveLog Smart Contract Deployment ===");
  console.log("Deployer:", deployer.address);
  console.log("Balance:", ethers.utils.formatEther(await deployer.getBalance()));
  
  // 1. Deploy Share Token
  console.log("\n1. Deploying Share Token...");
  const ShareToken = await ethers.getContractFactory("ActiveLogShareToken");
  const shareToken = await ShareToken.deploy(
    "ActiveLog Shares",
    "ALOG",
    COMPANY_VALUATION,
    TOTAL_SHARES
  );
  await shareToken.deployed();
  console.log("✓ ShareToken:", shareToken.address);
  
  // 2. Deploy Vesting Contract
  console.log("\n2. Deploying Vesting Contract...");
  const VestingContract = await ethers.getContractFactory("VestingContract");
  const vesting = await VestingContract.deploy(shareToken.address);
  await vesting.deployed();
  console.log("✓ VestingContract:", vesting.address);
  
  // 3. Deploy Governance Contract
  console.log("\n3. Deploying Governance Contract...");
  const GovernanceContract = await ethers.getContractFactory("GovernanceContract");
  const governance = await GovernanceContract.deploy(shareToken.address);
  await governance.deployed();
  console.log("✓ GovernanceContract:", governance.address);
  
  // 4. Deploy Compliance Contract
  console.log("\n4. Deploying Compliance Contract...");
  const ComplianceAutomation = await ethers.getContractFactory("ComplianceAutomation");
  const compliance = await ComplianceAutomation.deploy(COMPLIANCE_OFFICER);
  await compliance.deployed();
  console.log("✓ ComplianceAutomation:", compliance.address);
  
  // 5. Configure contracts
  console.log("\n5. Configuring contracts...");
  
  // Grant vesting contract permission to mint shares
  await shareToken.transfer(vesting.address, ethers.utils.parseEther("100000")); // 100k shares for vesting
  
  // Set up governance voting classes
  await governance.setShareholderClass(deployer.address, "COMMON_A"); // Founder shares
  
  console.log("\n=== Deployment Complete ===");
  console.log("ShareToken:", shareToken.address);
  console.log("VestingContract:", vesting.address);
  console.log("GovernanceContract:", governance.address);
  console.log("ComplianceAutomation:", compliance.address);
  
  // Save addresses
  const addresses = {
    network: hre.network.name,
    shareToken: shareToken.address,
    vesting: vesting.address,
    governance: governance.address,
    compliance: compliance.address,
    deployer: deployer.address,
    timestamp: new Date().toISOString()
  };
  
  const fs = require('fs');
  fs.writeFileSync(
    `deployment-${hre.network.name}.json`,
    JSON.stringify(addresses, null, 2)
  );
  
  return addresses;
}

if (require.main === module) {
  main()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });
}

module.exports = main;
```

---

## DEPLOYMENT COMMANDS

### Local Development

```bash
# Start local Hardhat node
npx hardhat node

# Deploy to local network
npx hardhat run scripts/deploy-all.js --network localhost
```

### Testnet Deployment

```bash
# Deploy to Goerli testnet
npx hardhat run scripts/deploy-all.js --network goerli

# Verify contracts on Etherscan
npx hardhat verify --network goerli DEPLOYED_ADDRESS "constructor" "args"
```

### Mainnet Deployment

```bash
# Deploy to Ethereum mainnet
npx hardhat run scripts/deploy-all.js --network mainnet

# Deploy to Polygon
npx hardhat run scripts/deploy-all.js --network polygon

# Deploy to Arbitrum
npx hardhat run scripts/deploy-all.js --network arbitrum
```

---

## POST-DEPLOYMENT CONFIGURATION

### 1. Contract Verification

```bash
# Verify all contracts on block explorer
npx hardhat verify --network mainnet SHARE_TOKEN_ADDRESS "ActiveLog Shares" "ALOG" "1000000000000000000000000" "1000000"
npx hardhat verify --network mainnet VESTING_ADDRESS SHARE_TOKEN_ADDRESS
npx hardhat verify --network mainnet GOVERNANCE_ADDRESS SHARE_TOKEN_ADDRESS
npx hardhat verify --network mainnet COMPLIANCE_ADDRESS COMPLIANCE_OFFICER_ADDRESS
```

### 2. Initial Configuration

```javascript
// scripts/configure.js
async function configure() {
  // Load deployed addresses
  const addresses = require('./deployment-mainnet.json');
  
  // Initialize contracts
  const shareToken = await ethers.getContractAt("ActiveLogShareToken", addresses.shareToken);
  const vesting = await ethers.getContractAt("VestingContract", addresses.vesting);
  const governance = await ethers.getContractAt("GovernanceContract", addresses.governance);
  const compliance = await ethers.getContractAt("ComplianceAutomation", addresses.compliance);
  
  // Configure share classes
  await governance.setShareholderClass(FOUNDER_ADDRESS, "COMMON_A");
  await governance.setShareholderClass(EMPLOYEE_POOL_ADDRESS, "COMMON_B");
  
  // Set up initial vesting schedules
  await vesting.createFounderVesting(FOUNDER_ADDRESS, ethers.utils.parseEther("200000"));
  
  // Configure compliance settings
  await compliance.setRegulatoryAuthority(SEC_FILING_ADDRESS);
  
  console.log("Configuration complete");
}
```

### 3. Security Setup

```javascript
// Transfer ownership to multisig
await shareToken.transferOwnership(COMPANY_MULTISIG);
await vesting.transferOwnership(COMPANY_MULTISIG);
await governance.transferOwnership(COMPANY_MULTISIG);
await compliance.transferOwnership(COMPANY_MULTISIG);

// Pause contracts if needed
await shareToken.pause();
```

---

## INTEGRATION WITH EXISTING SYSTEMS

### 1. Backend API Integration

```javascript
// Backend service integration
const { ethers } = require('ethers');

class BlockchainService {
  constructor(contractAddresses, providerUrl, privateKey) {
    this.provider = new ethers.providers.JsonRpcProvider(providerUrl);
    this.wallet = new ethers.Wallet(privateKey, this.provider);
    
    // Initialize contracts
    this.shareToken = new ethers.Contract(
      contractAddresses.shareToken,
      ShareTokenABI,
      this.wallet
    );
  }
  
  async purchaseShares(investor, amount, shareClass) {
    return await this.shareToken.purchaseShares(
      amount,
      investor.annualIncome,
      investor.netWorth,
      shareClass
    );
  }
  
  async distributeDividends(totalAmount) {
    return await this.shareToken.distributeDividends(totalAmount);
  }
}
```

### 2. Frontend Integration

```javascript
// Web3 frontend integration
import { ethers } from 'ethers';

class ActiveLogDApp {
  async connectWallet() {
    if (window.ethereum) {
      await window.ethereum.request({ method: 'eth_requestAccounts' });
      this.provider = new ethers.providers.Web3Provider(window.ethereum);
      this.signer = this.provider.getSigner();
      
      this.shareToken = new ethers.Contract(
        CONTRACT_ADDRESSES.shareToken,
        ShareTokenABI,
        this.signer
      );
    }
  }
  
  async getInvestorInfo() {
    const address = await this.signer.getAddress();
    return await this.shareToken.getInvestorInfo(address);
  }
}
```

---

## MONITORING AND MAINTENANCE

### 1. Contract Monitoring

```javascript
// Event monitoring script
async function monitorEvents() {
  const shareToken = await ethers.getContractAt("ActiveLogShareToken", SHARE_TOKEN_ADDRESS);
  
  // Monitor share purchases
  shareToken.on("SharesPurchased", (investor, amount, shares, shareClass) => {
    console.log(`New investment: ${investor} purchased ${shares} shares for ${amount}`);
    // Trigger compliance reporting
  });
  
  // Monitor dividend distributions
  shareToken.on("DividendDistributed", (round, totalAmount, perShare) => {
    console.log(`Dividend distributed: Round ${round}, Total ${totalAmount}`);
    // Generate tax documents
  });
}
```

### 2. Automated Compliance Reporting

```javascript
// Daily compliance check
async function dailyComplianceCheck() {
  const compliance = await ethers.getContractAt("ComplianceAutomation", COMPLIANCE_ADDRESS);
  
  const summary = await compliance.getComplianceSummary();
  
  if (summary.totalRaised > ethers.utils.parseEther("4500000")) { // Approaching $5M limit
    // Generate early warning report
    await compliance.generateComplianceReport(
      ReportType.MATERIAL_CHANGE,
      startPeriod,
      endPeriod,
      dataHash,
      ipfsHash
    );
  }
}
```

---

## SECURITY CONSIDERATIONS

### 1. Access Control
- Use multisig wallets for contract ownership
- Implement role-based permissions
- Regular security audits

### 2. Upgrade Strategy
- Consider using OpenZeppelin's upgradeable contracts
- Implement timelock for sensitive operations
- Emergency pause functionality

### 3. Regulatory Compliance
- Regular compliance audits
- Automated reporting to regulators
- Geographic restriction enforcement

---

## COST ESTIMATES

### Gas Costs (Ethereum Mainnet)

| Operation | Gas Limit | Cost @ 20 gwei |
|-----------|-----------|----------------|
| Deploy ShareToken | ~2,500,000 | ~$100-200 |
| Deploy Vesting | ~2,000,000 | ~$80-160 |
| Deploy Governance | ~2,200,000 | ~$90-180 |
| Deploy Compliance | ~2,800,000 | ~$110-220 |
| Purchase Shares | ~150,000 | ~$6-12 |
| Claim Dividends | ~100,000 | ~$4-8 |
| Vote on Proposal | ~80,000 | ~$3-6 |

### Alternative Networks

**Polygon:** ~1000x cheaper gas costs  
**Arbitrum:** ~100x cheaper gas costs  
**BSC:** ~100x cheaper gas costs  

---

## SUPPORT AND MAINTENANCE

For technical support with smart contract deployment:

**Email:** tech@activelog.ai  
**Documentation:** https://docs.activelog.ai/smart-contracts  
**GitHub:** https://github.com/activelogai/equity-contracts  

---

*This deployment guide should be reviewed by qualified smart contract developers and legal counsel before implementation.*