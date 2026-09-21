import { Decimal } from 'decimal.js';
import axios from 'axios';

class PortfolioAnalytics {
    constructor(redisClient, walletManager, defiIntegration, nftConnector, yieldTracker) {
        this.redis = redisClient;
        this.walletManager = walletManager;
        this.defiIntegration = defiIntegration;
        this.nftConnector = nftConnector;
        this.yieldTracker = yieldTracker;
        
        // Price data sources
        this.priceApis = {
            coingecko: 'https://api.coingecko.com/api/v3',
            coinmarketcap: 'https://pro-api.coinmarketcap.com/v1'
        };
    }

    // Get comprehensive portfolio overview
    async getPortfolioOverview(userAddress, timeframe = '30d') {
        try {
            const overview = {
                totalValue: new Decimal(0),
                breakdown: {
                    tokens: { value: new Decimal(0), percentage: 0 },
                    defi: { value: new Decimal(0), percentage: 0 },
                    nft: { value: new Decimal(0), percentage: 0 },
                    yield: { value: new Decimal(0), percentage: 0 }
                },
                performance: {
                    period: timeframe,
                    totalReturn: new Decimal(0),
                    totalReturnPercentage: 0,
                    dailyChange: new Decimal(0),
                    dailyChangePercentage: 0,
                    weeklyChange: new Decimal(0),
                    weeklyChangePercentage: 0
                },
                diversification: {
                    score: 0,
                    topHoldings: [],
                    networkDistribution: {},
                    assetClassDistribution: {}
                },
                riskMetrics: {
                    volatility: 0,
                    sharpeRatio: 0,
                    maxDrawdown: 0,
                    riskScore: 0
                }
            };

            // Get token balances across all wallets
            const wallets = await this.walletManager.getUserWallets(userAddress);
            let tokenValue = new Decimal(0);

            for (const wallet of wallets) {
                const balances = await this.walletManager.getWalletBalances(wallet.walletId);
                for (const [network, balance] of Object.entries(balances)) {
                    tokenValue = tokenValue.plus(balance.usdValue || 0);
                }
            }

            // Get DeFi positions
            const defiPositions = await this.defiIntegration.getDeFiPositions(userAddress);
            const defiValue = defiPositions.totalValue;

            // Get NFT collection value
            const nftCollection = await this.nftConnector.getUserNFTCollection(userAddress);
            const nftValue = nftCollection.totalValue;

            // Get yield farming positions
            const yieldPositions = await this.yieldTracker.getYieldFarmingPositions(userAddress);
            const yieldValue = yieldPositions.totalValue;

            // Calculate totals
            overview.totalValue = tokenValue.plus(defiValue).plus(nftValue).plus(yieldValue);

            if (overview.totalValue.gt(0)) {
                overview.breakdown.tokens.value = tokenValue;
                overview.breakdown.tokens.percentage = tokenValue.div(overview.totalValue).mul(100).toNumber();

                overview.breakdown.defi.value = new Decimal(defiValue);
                overview.breakdown.defi.percentage = new Decimal(defiValue).div(overview.totalValue).mul(100).toNumber();

                overview.breakdown.nft.value = new Decimal(nftValue);
                overview.breakdown.nft.percentage = new Decimal(nftValue).div(overview.totalValue).mul(100).toNumber();

                overview.breakdown.yield.value = new Decimal(yieldValue);
                overview.breakdown.yield.percentage = new Decimal(yieldValue).div(overview.totalValue).mul(100).toNumber();
            }

            // Calculate performance metrics
            overview.performance = await this.calculatePortfolioPerformance(userAddress, timeframe);

            // Calculate diversification metrics
            overview.diversification = await this.calculateDiversificationMetrics(userAddress);

            // Calculate risk metrics
            overview.riskMetrics = await this.calculateRiskMetrics(userAddress, timeframe);

            // Cache results
            await this.redis.setEx(
                `portfolio:overview:${userAddress}:${timeframe}`,
                600, // 10 minutes cache
                JSON.stringify(overview, this.decimalReplacer)
            );

            return overview;
        } catch (error) {
            throw new Error(`Failed to get portfolio overview: ${error.message}`);
        }
    }

    // Calculate portfolio performance over time
    async calculatePortfolioPerformance(userAddress, timeframe) {
        try {
            const performance = {
                period: timeframe,
                totalReturn: new Decimal(0),
                totalReturnPercentage: 0,
                dailyChange: new Decimal(0),
                dailyChangePercentage: 0,
                weeklyChange: new Decimal(0),
                weeklyChangePercentage: 0,
                monthlyChange: new Decimal(0),
                monthlyChangePercentage: 0,
                priceHistory: []
            };

            // Get historical portfolio values
            const historicalValues = await this.getHistoricalPortfolioValues(userAddress, timeframe);
            
            if (historicalValues.length > 1) {
                const currentValue = new Decimal(historicalValues[historicalValues.length - 1].value);
                const initialValue = new Decimal(historicalValues[0].value);

                // Calculate total return
                performance.totalReturn = currentValue.minus(initialValue);
                performance.totalReturnPercentage = initialValue.gt(0) 
                    ? performance.totalReturn.div(initialValue).mul(100).toNumber()
                    : 0;

                // Calculate daily change (24h)
                if (historicalValues.length >= 2) {
                    const previousValue = new Decimal(historicalValues[historicalValues.length - 2].value);
                    performance.dailyChange = currentValue.minus(previousValue);
                    performance.dailyChangePercentage = previousValue.gt(0)
                        ? performance.dailyChange.div(previousValue).mul(100).toNumber()
                        : 0;
                }

                // Calculate weekly change (7 days)
                const weekIndex = Math.max(0, historicalValues.length - 8);
                if (weekIndex > 0) {
                    const weekValue = new Decimal(historicalValues[weekIndex].value);
                    performance.weeklyChange = currentValue.minus(weekValue);
                    performance.weeklyChangePercentage = weekValue.gt(0)
                        ? performance.weeklyChange.div(weekValue).mul(100).toNumber()
                        : 0;
                }

                // Calculate monthly change (30 days)
                const monthIndex = Math.max(0, historicalValues.length - 31);
                if (monthIndex > 0) {
                    const monthValue = new Decimal(historicalValues[monthIndex].value);
                    performance.monthlyChange = currentValue.minus(monthValue);
                    performance.monthlyChangePercentage = monthValue.gt(0)
                        ? performance.monthlyChange.div(monthValue).mul(100).toNumber()
                        : 0;
                }

                performance.priceHistory = historicalValues;
            }

            return performance;
        } catch (error) {
            console.error('Error calculating portfolio performance:', error);
            return {
                period: timeframe,
                totalReturn: new Decimal(0),
                totalReturnPercentage: 0,
                dailyChange: new Decimal(0),
                dailyChangePercentage: 0,
                weeklyChange: new Decimal(0),
                weeklyChangePercentage: 0,
                priceHistory: []
            };
        }
    }

    // Calculate portfolio diversification metrics
    async calculateDiversificationMetrics(userAddress) {
        try {
            const diversification = {
                score: 0,
                topHoldings: [],
                networkDistribution: {},
                assetClassDistribution: {
                    'Layer 1': 0,
                    'Layer 2': 0,
                    'DeFi': 0,
                    'NFT': 0,
                    'Stablecoin': 0,
                    'Yield': 0
                },
                concentrationRisk: 0
            };

            // Get all holdings with values
            const holdings = await this.getAllHoldings(userAddress);
            const totalValue = holdings.reduce((sum, holding) => sum + holding.value, 0);

            if (totalValue === 0) return diversification;

            // Sort by value and get top holdings
            holdings.sort((a, b) => b.value - a.value);
            diversification.topHoldings = holdings.slice(0, 10).map(holding => ({
                ...holding,
                percentage: (holding.value / totalValue) * 100
            }));

            // Calculate network distribution
            holdings.forEach(holding => {
                if (holding.network) {
                    if (!diversification.networkDistribution[holding.network]) {
                        diversification.networkDistribution[holding.network] = 0;
                    }
                    diversification.networkDistribution[holding.network] += (holding.value / totalValue) * 100;
                }
            });

            // Calculate asset class distribution
            holdings.forEach(holding => {
                const assetClass = this.classifyAsset(holding);
                diversification.assetClassDistribution[assetClass] += (holding.value / totalValue) * 100;
            });

            // Calculate diversification score (Herfindahl-Hirschman Index)
            const concentrationScore = holdings.reduce((sum, holding) => {
                const percentage = holding.value / totalValue;
                return sum + (percentage * percentage);
            }, 0);

            // Invert and normalize to 0-100 scale
            diversification.score = Math.max(0, 100 * (1 - concentrationScore));
            diversification.concentrationRisk = concentrationScore * 100;

            return diversification;
        } catch (error) {
            console.error('Error calculating diversification metrics:', error);
            return {
                score: 0,
                topHoldings: [],
                networkDistribution: {},
                assetClassDistribution: {},
                concentrationRisk: 0
            };
        }
    }

    // Calculate risk metrics
    async calculateRiskMetrics(userAddress, timeframe) {
        try {
            const riskMetrics = {
                volatility: 0,
                sharpeRatio: 0,
                maxDrawdown: 0,
                riskScore: 0,
                beta: 0,
                valueAtRisk: 0
            };

            // Get historical values for volatility calculation
            const historicalValues = await this.getHistoricalPortfolioValues(userAddress, timeframe);
            
            if (historicalValues.length < 30) {
                return riskMetrics; // Need at least 30 data points
            }

            // Calculate daily returns
            const dailyReturns = [];
            for (let i = 1; i < historicalValues.length; i++) {
                const currentValue = historicalValues[i].value;
                const previousValue = historicalValues[i - 1].value;
                if (previousValue > 0) {
                    dailyReturns.push((currentValue - previousValue) / previousValue);
                }
            }

            if (dailyReturns.length === 0) return riskMetrics;

            // Calculate volatility (standard deviation of daily returns)
            const meanReturn = dailyReturns.reduce((sum, ret) => sum + ret, 0) / dailyReturns.length;
            const variance = dailyReturns.reduce((sum, ret) => sum + Math.pow(ret - meanReturn, 2), 0) / dailyReturns.length;
            riskMetrics.volatility = Math.sqrt(variance * 365) * 100; // Annualized volatility

            // Calculate Sharpe Ratio (assuming risk-free rate of 2%)
            const riskFreeRate = 0.02;
            const excessReturn = (meanReturn * 365) - riskFreeRate;
            riskMetrics.sharpeRatio = riskMetrics.volatility > 0 ? excessReturn / (riskMetrics.volatility / 100) : 0;

            // Calculate Maximum Drawdown
            let maxValue = historicalValues[0].value;
            let maxDrawdown = 0;
            
            for (const point of historicalValues) {
                if (point.value > maxValue) {
                    maxValue = point.value;
                }
                const drawdown = (maxValue - point.value) / maxValue;
                maxDrawdown = Math.max(maxDrawdown, drawdown);
            }
            riskMetrics.maxDrawdown = maxDrawdown * 100;

            // Calculate Value at Risk (95% confidence level)
            const sortedReturns = [...dailyReturns].sort((a, b) => a - b);
            const varIndex = Math.floor(sortedReturns.length * 0.05);
            riskMetrics.valueAtRisk = Math.abs(sortedReturns[varIndex] * 100);

            // Calculate composite risk score (0-100, higher = riskier)
            const volatilityScore = Math.min(riskMetrics.volatility, 100);
            const drawdownScore = Math.min(riskMetrics.maxDrawdown, 50) * 2;
            const sharpeScore = Math.max(0, 50 - (riskMetrics.sharpeRatio * 10));
            
            riskMetrics.riskScore = (volatilityScore + drawdownScore + sharpeScore) / 3;

            return riskMetrics;
        } catch (error) {
            console.error('Error calculating risk metrics:', error);
            return {
                volatility: 0,
                sharpeRatio: 0,
                maxDrawdown: 0,
                riskScore: 0,
                beta: 0,
                valueAtRisk: 0
            };
        }
    }

    // Get portfolio allocation recommendations
    async getAllocationRecommendations(userAddress, riskTolerance = 'moderate') {
        try {
            const currentOverview = await this.getPortfolioOverview(userAddress);
            const recommendations = {
                currentAllocation: currentOverview.breakdown,
                recommendedAllocation: {},
                rebalanceActions: [],
                riskAssessment: '',
                expectedReturn: 0,
                expectedVolatility: 0
            };

            // Define allocation targets based on risk tolerance
            const allocationTargets = {
                conservative: {
                    tokens: 30, defi: 20, nft: 10, yield: 40
                },
                moderate: {
                    tokens: 40, defi: 30, nft: 15, yield: 15
                },
                aggressive: {
                    tokens: 50, defi: 35, nft: 10, yield: 5
                }
            };

            const targets = allocationTargets[riskTolerance] || allocationTargets.moderate;
            recommendations.recommendedAllocation = targets;

            // Calculate rebalance actions
            const totalValue = currentOverview.totalValue.toNumber();
            for (const [category, targetPercentage] of Object.entries(targets)) {
                const currentPercentage = currentOverview.breakdown[category]?.percentage || 0;
                const difference = targetPercentage - currentPercentage;
                
                if (Math.abs(difference) > 5) { // Only suggest if difference > 5%
                    const dollarAmount = (Math.abs(difference) / 100) * totalValue;
                    recommendations.rebalanceActions.push({
                        category,
                        action: difference > 0 ? 'increase' : 'decrease',
                        currentPercentage,
                        targetPercentage,
                        differencePercentage: Math.abs(difference),
                        dollarAmount: dollarAmount
                    });
                }
            }

            // Risk assessment
            const riskScore = currentOverview.riskMetrics.riskScore;
            if (riskScore < 30) {
                recommendations.riskAssessment = 'Low Risk - Conservative allocation';
            } else if (riskScore < 60) {
                recommendations.riskAssessment = 'Moderate Risk - Balanced allocation';
            } else {
                recommendations.riskAssessment = 'High Risk - Aggressive allocation';
            }

            return recommendations;
        } catch (error) {
            throw new Error(`Failed to get allocation recommendations: ${error.message}`);
        }
    }

    // Get portfolio analytics dashboard data
    async getAnalyticsDashboard(userAddress, timeframe = '30d') {
        try {
            const dashboard = await Promise.all([
                this.getPortfolioOverview(userAddress, timeframe),
                this.getTopGainersLosers(userAddress, timeframe),
                this.getTransactionAnalytics(userAddress, timeframe),
                this.getYieldAnalytics(userAddress, timeframe),
                this.getAllocationRecommendations(userAddress)
            ]);

            return {
                overview: dashboard[0],
                gainersLosers: dashboard[1],
                transactions: dashboard[2],
                yield: dashboard[3],
                recommendations: dashboard[4],
                lastUpdated: new Date().toISOString()
            };
        } catch (error) {
            throw new Error(`Failed to get analytics dashboard: ${error.message}`);
        }
    }

    // Helper functions
    async getAllHoldings(userAddress) {
        const holdings = [];

        try {
            // Get token holdings
            const wallets = await this.walletManager.getUserWallets(userAddress);
            for (const wallet of wallets) {
                const balances = await this.walletManager.getWalletBalances(wallet.walletId);
                for (const [network, balance] of Object.entries(balances)) {
                    holdings.push({
                        type: 'token',
                        symbol: balance.symbol,
                        network: network,
                        value: balance.usdValue || 0,
                        amount: balance.balance
                    });
                }
            }

            // Get DeFi holdings
            const defiPositions = await this.defiIntegration.getDeFiPositions(userAddress);
            defiPositions.lending.forEach(position => {
                holdings.push({
                    type: 'defi_lending',
                    symbol: position.token,
                    network: position.network,
                    value: position.value || 0,
                    amount: position.amount,
                    protocol: position.protocol
                });
            });

            // Get NFT holdings
            const nftCollection = await this.nftConnector.getUserNFTCollection(userAddress);
            nftCollection.owned.forEach(nft => {
                holdings.push({
                    type: 'nft',
                    symbol: nft.collectionName,
                    network: nft.network,
                    value: nft.estimatedValue || 0,
                    amount: 1,
                    tokenId: nft.tokenId
                });
            });

            // Get yield farming holdings
            const yieldPositions = await this.yieldTracker.getYieldFarmingPositions(userAddress);
            yieldPositions.activeFarms.forEach(farm => {
                holdings.push({
                    type: 'yield_farming',
                    symbol: farm.pair || farm.token,
                    network: farm.network,
                    value: farm.stakedValue || 0,
                    amount: farm.stakedAmount,
                    protocol: farm.protocol
                });
            });

        } catch (error) {
            console.error('Error getting all holdings:', error);
        }

        return holdings;
    }

    classifyAsset(holding) {
        const symbol = holding.symbol?.toLowerCase() || '';
        
        if (['usdc', 'usdt', 'dai', 'busd'].includes(symbol)) {
            return 'Stablecoin';
        }
        
        if (holding.type === 'nft') {
            return 'NFT';
        }
        
        if (holding.type === 'yield_farming') {
            return 'Yield';
        }
        
        if (holding.type === 'defi_lending') {
            return 'DeFi';
        }

        if (['matic', 'avax', 'ftm', 'one'].includes(symbol)) {
            return 'Layer 2';
        }

        return 'Layer 1';
    }

    async getHistoricalPortfolioValues(userAddress, timeframe) {
        // Mock implementation - would fetch from database or calculate
        const days = timeframe === '7d' ? 7 : timeframe === '30d' ? 30 : 365;
        const values = [];
        const baseValue = 10000;
        
        for (let i = 0; i < days; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (days - i));
            
            // Simulate price movement
            const randomChange = (Math.random() - 0.5) * 0.1; // ±5% daily change
            const value = baseValue * (1 + (Math.sin(i / 10) * 0.2) + randomChange);
            
            values.push({
                date: date.toISOString(),
                value: Math.max(0, value)
            });
        }
        
        return values;
    }

    async getTopGainersLosers(userAddress, timeframe) {
        // Mock implementation
        return {
            gainers: [
                { symbol: 'ETH', change: 15.5, value: 2500 },
                { symbol: 'MATIC', change: 12.3, value: 850 }
            ],
            losers: [
                { symbol: 'BTC', change: -5.2, value: 45000 },
                { symbol: 'SOL', change: -8.1, value: 110 }
            ]
        };
    }

    async getTransactionAnalytics(userAddress, timeframe) {
        // Mock implementation
        return {
            totalTransactions: 45,
            totalVolume: 25000,
            averageTransactionSize: 556,
            gasSpent: 125.50,
            mostActiveNetwork: 'ethereum'
        };
    }

    async getYieldAnalytics(userAddress, timeframe) {
        const yieldPositions = await this.yieldTracker.getYieldFarmingPositions(userAddress);
        return {
            totalYieldEarned: yieldPositions.totalRewards.toNumber(),
            averageAPY: yieldPositions.summary.averageAPY,
            activePositions: yieldPositions.summary.totalPositions
        };
    }

    decimalReplacer(key, value) {
        return value instanceof Decimal ? value.toString() : value;
    }
}

export default PortfolioAnalytics;