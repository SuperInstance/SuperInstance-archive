import { Decimal } from 'decimal.js';
import { differenceInDays, parseISO, format } from 'date-fns';

class StockPortfolioTracker {
    constructor(redisClient, realTimeQuotes) {
        this.redis = redisClient;
        this.realTimeQuotes = realTimeQuotes;
    }

    // Create new portfolio
    async createPortfolio(userId, portfolioData) {
        try {
            const {
                name,
                description = '',
                benchmarkSymbol = 'SPY',
                baseCurrency = 'USD',
                riskTolerance = 'moderate'
            } = portfolioData;

            const portfolioId = `port_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            const portfolio = {
                portfolioId,
                userId,
                name,
                description,
                benchmarkSymbol,
                baseCurrency,
                riskTolerance,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                totalValue: new Decimal(0),
                totalCost: new Decimal(0),
                totalReturn: new Decimal(0),
                totalReturnPercentage: 0,
                dayChange: new Decimal(0),
                dayChangePercentage: 0,
                positions: {},
                isActive: true
            };

            await this.redis.hSet(`portfolio:${portfolioId}`, this.flattenPortfolio(portfolio));
            await this.redis.sAdd(`user:${userId}:portfolios`, portfolioId);

            return {
                portfolioId,
                ...portfolio,
                totalValue: portfolio.totalValue.toString(),
                totalCost: portfolio.totalCost.toString(),
                totalReturn: portfolio.totalReturn.toString(),
                dayChange: portfolio.dayChange.toString()
            };
        } catch (error) {
            throw new Error(`Failed to create portfolio: ${error.message}`);
        }
    }

    // Add position to portfolio
    async addPosition(portfolioId, positionData) {
        try {
            const {
                symbol,
                quantity,
                averagePrice,
                purchaseDate,
                positionType = 'long', // long, short
                sector,
                industry
            } = positionData;

            const portfolio = await this.getPortfolio(portfolioId);
            if (!portfolio) {
                throw new Error('Portfolio not found');
            }

            const positionId = `pos_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
            const totalCost = new Decimal(quantity).mul(averagePrice);

            const position = {
                positionId,
                symbol,
                quantity: new Decimal(quantity),
                averagePrice: new Decimal(averagePrice),
                totalCost,
                currentPrice: new Decimal(0),
                marketValue: new Decimal(0),
                unrealizedGainLoss: new Decimal(0),
                unrealizedGainLossPercentage: 0,
                dayChange: new Decimal(0),
                dayChangePercentage: 0,
                purchaseDate,
                positionType,
                sector: sector || 'Unknown',
                industry: industry || 'Unknown',
                weight: 0,
                addedAt: new Date().toISOString()
            };

            // Get current market price
            const quote = await this.realTimeQuotes.getQuote(symbol);
            if (quote) {
                position.currentPrice = new Decimal(quote.price);
                position.marketValue = position.quantity.mul(position.currentPrice);
                position.unrealizedGainLoss = position.marketValue.minus(position.totalCost);
                position.unrealizedGainLossPercentage = position.totalCost.gt(0) 
                    ? position.unrealizedGainLoss.div(position.totalCost).mul(100).toNumber()
                    : 0;
                position.dayChange = position.quantity.mul(quote.change || 0);
                position.dayChangePercentage = quote.changePercent || 0;
            }

            // Add position to portfolio
            portfolio.positions[positionId] = position;
            
            // Update portfolio totals
            await this.updatePortfolioTotals(portfolio);
            
            // Save updated portfolio
            await this.redis.hSet(`portfolio:${portfolioId}`, this.flattenPortfolio(portfolio));

            return {
                positionId,
                ...this.sanitizePosition(position)
            };
        } catch (error) {
            throw new Error(`Failed to add position: ${error.message}`);
        }
    }

    // Update position quantity (buy/sell)
    async updatePosition(portfolioId, positionId, updateData) {
        try {
            const { quantity, price, transactionType, date } = updateData;
            
            const portfolio = await this.getPortfolio(portfolioId);
            const position = portfolio.positions[positionId];
            
            if (!position) {
                throw new Error('Position not found');
            }

            const transactionQuantity = new Decimal(quantity);
            const transactionPrice = new Decimal(price);
            const transactionValue = transactionQuantity.mul(transactionPrice);

            if (transactionType === 'buy') {
                // Calculate new average price
                const currentValue = position.quantity.mul(position.averagePrice);
                const newTotalValue = currentValue.plus(transactionValue);
                const newTotalQuantity = position.quantity.plus(transactionQuantity);
                
                position.averagePrice = newTotalQuantity.gt(0) 
                    ? newTotalValue.div(newTotalQuantity)
                    : new Decimal(0);
                position.quantity = newTotalQuantity;
                position.totalCost = newTotalQuantity.mul(position.averagePrice);
                
            } else if (transactionType === 'sell') {
                if (transactionQuantity.gt(position.quantity)) {
                    throw new Error('Cannot sell more shares than owned');
                }
                
                position.quantity = position.quantity.minus(transactionQuantity);
                position.totalCost = position.quantity.mul(position.averagePrice);
                
                // Record realized gain/loss
                const realizedGainLoss = transactionValue.minus(transactionQuantity.mul(position.averagePrice));
                
                // Log transaction for tax purposes
                await this.logTransaction(portfolioId, {
                    type: 'sell',
                    symbol: position.symbol,
                    quantity: transactionQuantity.toString(),
                    price: transactionPrice.toString(),
                    date,
                    realizedGainLoss: realizedGainLoss.toString()
                });
            }

            // Update market value with current price
            const quote = await this.realTimeQuotes.getQuote(position.symbol);
            if (quote) {
                position.currentPrice = new Decimal(quote.price);
                position.marketValue = position.quantity.mul(position.currentPrice);
                position.unrealizedGainLoss = position.marketValue.minus(position.totalCost);
                position.unrealizedGainLossPercentage = position.totalCost.gt(0)
                    ? position.unrealizedGainLoss.div(position.totalCost).mul(100).toNumber()
                    : 0;
            }

            // Remove position if quantity is zero
            if (position.quantity.eq(0)) {
                delete portfolio.positions[positionId];
            }

            // Update portfolio totals
            await this.updatePortfolioTotals(portfolio);
            
            // Save updated portfolio
            await this.redis.hSet(`portfolio:${portfolioId}`, this.flattenPortfolio(portfolio));

            return {
                success: true,
                position: position.quantity.gt(0) ? this.sanitizePosition(position) : null,
                realizedGainLoss: transactionType === 'sell' ? 
                    transactionValue.minus(transactionQuantity.mul(position.averagePrice)).toString() : null
            };
        } catch (error) {
            throw new Error(`Failed to update position: ${error.message}`);
        }
    }

    // Get portfolio with current market values
    async getPortfolioWithMarketData(portfolioId) {
        try {
            const portfolio = await this.getPortfolio(portfolioId);
            if (!portfolio) {
                throw new Error('Portfolio not found');
            }

            // Update all positions with current market data
            const symbols = Object.values(portfolio.positions).map(pos => pos.symbol);
            const quotes = await this.realTimeQuotes.getBatchQuotes(symbols);

            for (const [positionId, position] of Object.entries(portfolio.positions)) {
                const quote = quotes[position.symbol];
                if (quote) {
                    position.currentPrice = new Decimal(quote.price);
                    position.marketValue = position.quantity.mul(position.currentPrice);
                    position.unrealizedGainLoss = position.marketValue.minus(position.totalCost);
                    position.unrealizedGainLossPercentage = position.totalCost.gt(0)
                        ? position.unrealizedGainLoss.div(position.totalCost).mul(100).toNumber()
                        : 0;
                    position.dayChange = position.quantity.mul(quote.change || 0);
                    position.dayChangePercentage = quote.changePercent || 0;
                }
            }

            // Update portfolio totals
            await this.updatePortfolioTotals(portfolio);

            // Calculate sector and industry allocations
            const allocations = this.calculateAllocations(portfolio);

            return {
                ...this.sanitizePortfolio(portfolio),
                allocations,
                lastUpdated: new Date().toISOString()
            };
        } catch (error) {
            throw new Error(`Failed to get portfolio with market data: ${error.message}`);
        }
    }

    // Get portfolio performance over time
    async getPortfolioPerformance(portfolioId, period = '1y') {
        try {
            const portfolio = await this.getPortfolio(portfolioId);
            if (!portfolio) {
                throw new Error('Portfolio not found');
            }

            // Get historical data for all positions
            const symbols = Object.values(portfolio.positions).map(pos => pos.symbol);
            const historicalData = await this.getHistoricalPortfolioData(portfolioId, symbols, period);

            const performance = {
                period,
                totalReturn: portfolio.totalReturn.toString(),
                totalReturnPercentage: portfolio.totalReturnPercentage,
                annualizedReturn: this.calculateAnnualizedReturn(portfolio, period),
                volatility: this.calculateVolatility(historicalData),
                sharpeRatio: this.calculateSharpeRatio(historicalData),
                maxDrawdown: this.calculateMaxDrawdown(historicalData),
                beta: await this.calculateBeta(portfolioId, period),
                alpha: await this.calculateAlpha(portfolioId, period),
                historicalValues: historicalData
            };

            return performance;
        } catch (error) {
            throw new Error(`Failed to get portfolio performance: ${error.message}`);
        }
    }

    // Get user's portfolios
    async getUserPortfolios(userId) {
        try {
            const portfolioIds = await this.redis.sMembers(`user:${userId}:portfolios`);
            const portfolios = [];

            for (const portfolioId of portfolioIds) {
                const portfolio = await this.getPortfolio(portfolioId);
                if (portfolio && portfolio.isActive) {
                    portfolios.push(this.sanitizePortfolio(portfolio));
                }
            }

            return portfolios.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
        } catch (error) {
            throw new Error(`Failed to get user portfolios: ${error.message}`);
        }
    }

    // Calculate portfolio analytics
    async getPortfolioAnalytics(portfolioId) {
        try {
            const portfolio = await this.getPortfolioWithMarketData(portfolioId);
            
            const analytics = {
                summary: {
                    totalPositions: Object.keys(portfolio.positions).length,
                    totalValue: portfolio.totalValue,
                    totalReturn: portfolio.totalReturn,
                    totalReturnPercentage: portfolio.totalReturnPercentage,
                    dayChange: portfolio.dayChange,
                    dayChangePercentage: portfolio.dayChangePercentage
                },
                diversification: this.calculateDiversificationMetrics(portfolio),
                riskMetrics: await this.calculateRiskMetrics(portfolioId),
                topPositions: this.getTopPositions(portfolio, 10),
                worstPerformers: this.getWorstPerformers(portfolio, 5),
                bestPerformers: this.getBestPerformers(portfolio, 5)
            };

            return analytics;
        } catch (error) {
            throw new Error(`Failed to get portfolio analytics: ${error.message}`);
        }
    }

    // Helper functions
    async getPortfolio(portfolioId) {
        try {
            const data = await this.redis.hGetAll(`portfolio:${portfolioId}`);
            if (!data.portfolioId) return null;

            const portfolio = this.unflattenPortfolio(data);
            return portfolio;
        } catch (error) {
            return null;
        }
    }

    async updatePortfolioTotals(portfolio) {
        let totalValue = new Decimal(0);
        let totalCost = new Decimal(0);
        let dayChange = new Decimal(0);

        for (const position of Object.values(portfolio.positions)) {
            totalValue = totalValue.plus(position.marketValue);
            totalCost = totalCost.plus(position.totalCost);
            dayChange = dayChange.plus(position.dayChange);

            // Calculate position weight
            if (totalValue.gt(0)) {
                position.weight = position.marketValue.div(totalValue).mul(100).toNumber();
            }
        }

        portfolio.totalValue = totalValue;
        portfolio.totalCost = totalCost;
        portfolio.totalReturn = totalValue.minus(totalCost);
        portfolio.totalReturnPercentage = totalCost.gt(0)
            ? portfolio.totalReturn.div(totalCost).mul(100).toNumber()
            : 0;
        portfolio.dayChange = dayChange;
        portfolio.dayChangePercentage = totalValue.gt(0) && totalValue.minus(dayChange).gt(0)
            ? dayChange.div(totalValue.minus(dayChange)).mul(100).toNumber()
            : 0;
        portfolio.updatedAt = new Date().toISOString();

        // Recalculate position weights with final total
        for (const position of Object.values(portfolio.positions)) {
            position.weight = totalValue.gt(0)
                ? position.marketValue.div(totalValue).mul(100).toNumber()
                : 0;
        }
    }

    calculateAllocations(portfolio) {
        const allocations = {
            sector: {},
            industry: {},
            geography: {},
            marketCap: { large: 0, mid: 0, small: 0 }
        };

        const totalValue = portfolio.totalValue;
        if (totalValue.eq(0)) return allocations;

        for (const position of Object.values(portfolio.positions)) {
            const weight = position.marketValue.div(totalValue).mul(100).toNumber();
            
            // Sector allocation
            if (position.sector) {
                allocations.sector[position.sector] = (allocations.sector[position.sector] || 0) + weight;
            }
            
            // Industry allocation
            if (position.industry) {
                allocations.industry[position.industry] = (allocations.industry[position.industry] || 0) + weight;
            }
        }

        return allocations;
    }

    calculateDiversificationMetrics(portfolio) {
        const positions = Object.values(portfolio.positions);
        if (positions.length === 0) return { score: 0, concentration: 100 };

        const totalValue = portfolio.totalValue;
        let herfindahlIndex = 0;

        for (const position of positions) {
            const weight = position.marketValue.div(totalValue).toNumber();
            herfindahlIndex += weight * weight;
        }

        return {
            score: Math.max(0, 100 * (1 - herfindahlIndex)),
            concentration: herfindahlIndex * 100,
            effectivePositions: herfindahlIndex > 0 ? 1 / herfindahlIndex : 0
        };
    }

    async calculateRiskMetrics(portfolioId) {
        // Simplified risk metrics calculation
        return {
            volatility: 0.15,
            sharpeRatio: 1.2,
            beta: 1.05,
            maxDrawdown: 0.12,
            var95: 0.05
        };
    }

    getTopPositions(portfolio, limit) {
        return Object.values(portfolio.positions)
            .sort((a, b) => b.marketValue.minus(a.marketValue).toNumber())
            .slice(0, limit)
            .map(pos => this.sanitizePosition(pos));
    }

    getBestPerformers(portfolio, limit) {
        return Object.values(portfolio.positions)
            .sort((a, b) => b.unrealizedGainLossPercentage - a.unrealizedGainLossPercentage)
            .slice(0, limit)
            .map(pos => this.sanitizePosition(pos));
    }

    getWorstPerformers(portfolio, limit) {
        return Object.values(portfolio.positions)
            .sort((a, b) => a.unrealizedGainLossPercentage - b.unrealizedGainLossPercentage)
            .slice(0, limit)
            .map(pos => this.sanitizePosition(pos));
    }

    calculateAnnualizedReturn(portfolio, period) {
        const days = this.getPeriodDays(period);
        const totalReturn = portfolio.totalReturnPercentage / 100;
        return Math.pow(1 + totalReturn, 365 / days) - 1;
    }

    calculateVolatility(historicalData) {
        if (historicalData.length < 2) return 0;

        const returns = [];
        for (let i = 1; i < historicalData.length; i++) {
            const dailyReturn = (historicalData[i].value - historicalData[i-1].value) / historicalData[i-1].value;
            returns.push(dailyReturn);
        }

        const mean = returns.reduce((sum, ret) => sum + ret, 0) / returns.length;
        const variance = returns.reduce((sum, ret) => sum + Math.pow(ret - mean, 2), 0) / returns.length;
        
        return Math.sqrt(variance * 252); // Annualized volatility
    }

    calculateSharpeRatio(historicalData) {
        const volatility = this.calculateVolatility(historicalData);
        const riskFreeRate = 0.02; // 2% risk-free rate
        const avgReturn = 0.08; // Assumed average return
        
        return volatility > 0 ? (avgReturn - riskFreeRate) / volatility : 0;
    }

    calculateMaxDrawdown(historicalData) {
        let maxValue = historicalData[0]?.value || 0;
        let maxDrawdown = 0;

        for (const point of historicalData) {
            if (point.value > maxValue) {
                maxValue = point.value;
            }
            const drawdown = (maxValue - point.value) / maxValue;
            maxDrawdown = Math.max(maxDrawdown, drawdown);
        }

        return maxDrawdown;
    }

    async calculateBeta(portfolioId, period) {
        // Simplified beta calculation - would need market data correlation
        return 1.0;
    }

    async calculateAlpha(portfolioId, period) {
        // Simplified alpha calculation
        return 0.02;
    }

    async getHistoricalPortfolioData(portfolioId, symbols, period) {
        // Mock historical data - would integrate with market data provider
        const days = this.getPeriodDays(period);
        const data = [];
        const baseValue = 10000;

        for (let i = 0; i < days; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (days - i));
            
            const value = baseValue * (1 + Math.sin(i / 30) * 0.1 + Math.random() * 0.02);
            data.push({
                date: date.toISOString(),
                value: Math.max(0, value)
            });
        }

        return data;
    }

    getPeriodDays(period) {
        const periods = {
            '1d': 1, '1w': 7, '1m': 30, '3m': 90, '6m': 180, '1y': 365, '2y': 730, '5y': 1825
        };
        return periods[period] || 365;
    }

    async logTransaction(portfolioId, transaction) {
        const transactionId = `txn_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
        await this.redis.hSet(`transaction:${transactionId}`, {
            transactionId,
            portfolioId,
            ...transaction,
            timestamp: new Date().toISOString()
        });
        await this.redis.lPush(`portfolio:${portfolioId}:transactions`, transactionId);
    }

    // Serialization helpers
    flattenPortfolio(portfolio) {
        const flattened = { ...portfolio };
        flattened.totalValue = portfolio.totalValue.toString();
        flattened.totalCost = portfolio.totalCost.toString();
        flattened.totalReturn = portfolio.totalReturn.toString();
        flattened.dayChange = portfolio.dayChange.toString();
        flattened.positions = JSON.stringify(portfolio.positions, this.decimalReplacer);
        return flattened;
    }

    unflattenPortfolio(data) {
        const portfolio = { ...data };
        portfolio.totalValue = new Decimal(data.totalValue || 0);
        portfolio.totalCost = new Decimal(data.totalCost || 0);
        portfolio.totalReturn = new Decimal(data.totalReturn || 0);
        portfolio.dayChange = new Decimal(data.dayChange || 0);
        portfolio.totalReturnPercentage = parseFloat(data.totalReturnPercentage || 0);
        portfolio.dayChangePercentage = parseFloat(data.dayChangePercentage || 0);
        portfolio.isActive = data.isActive === 'true';
        
        const positions = JSON.parse(data.positions || '{}');
        for (const [positionId, position] of Object.entries(positions)) {
            positions[positionId] = this.deserializePosition(position);
        }
        portfolio.positions = positions;
        
        return portfolio;
    }

    deserializePosition(position) {
        return {
            ...position,
            quantity: new Decimal(position.quantity || 0),
            averagePrice: new Decimal(position.averagePrice || 0),
            totalCost: new Decimal(position.totalCost || 0),
            currentPrice: new Decimal(position.currentPrice || 0),
            marketValue: new Decimal(position.marketValue || 0),
            unrealizedGainLoss: new Decimal(position.unrealizedGainLoss || 0),
            dayChange: new Decimal(position.dayChange || 0)
        };
    }

    sanitizePortfolio(portfolio) {
        return {
            ...portfolio,
            totalValue: portfolio.totalValue.toString(),
            totalCost: portfolio.totalCost.toString(),
            totalReturn: portfolio.totalReturn.toString(),
            dayChange: portfolio.dayChange.toString(),
            positions: Object.fromEntries(
                Object.entries(portfolio.positions).map(([id, pos]) => [id, this.sanitizePosition(pos)])
            )
        };
    }

    sanitizePosition(position) {
        return {
            ...position,
            quantity: position.quantity.toString(),
            averagePrice: position.averagePrice.toString(),
            totalCost: position.totalCost.toString(),
            currentPrice: position.currentPrice.toString(),
            marketValue: position.marketValue.toString(),
            unrealizedGainLoss: position.unrealizedGainLoss.toString(),
            dayChange: position.dayChange.toString()
        };
    }

    decimalReplacer(key, value) {
        return value instanceof Decimal ? value.toString() : value;
    }
}

export default StockPortfolioTracker;