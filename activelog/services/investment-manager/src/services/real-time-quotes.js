import axios from 'axios';
import { Decimal } from 'decimal.js';

class RealTimeQuotes {
    constructor(redisClient) {
        this.redis = redisClient;
        
        // API endpoints and keys
        this.apis = {
            alphaVantage: {
                baseUrl: 'https://www.alphavantage.co/query',
                key: process.env.ALPHA_VANTAGE_API_KEY,
                rateLimitPerMinute: 5
            },
            finnhub: {
                baseUrl: 'https://finnhub.io/api/v1',
                key: process.env.FINNHUB_API_KEY,
                rateLimitPerMinute: 60
            },
            iex: {
                baseUrl: 'https://cloud.iexapis.com/stable',
                key: process.env.IEX_API_KEY,
                rateLimitPerMinute: 100
            },
            polygon: {
                baseUrl: 'https://api.polygon.io/v2',
                key: process.env.POLYGON_API_KEY,
                rateLimitPerMinute: 5
            },
            yahoo: {
                baseUrl: 'https://query1.finance.yahoo.com/v8/finance/chart'
            }
        };

        // Cache settings
        this.cacheSettings = {
            realTimeQuote: 30, // 30 seconds
            batchQuotes: 60,   // 1 minute
            historicalData: 3600, // 1 hour
            fundamentals: 86400 // 24 hours
        };

        // Start background price updates
        this.startPriceUpdates();
    }

    // Get real-time quote for single symbol
    async getQuote(symbol) {
        try {
            const cacheKey = `quote:${symbol.toUpperCase()}`;
            
            // Try cache first
            const cached = await this.redis.get(cacheKey);
            if (cached) {
                return JSON.parse(cached);
            }

            // Fetch from multiple sources for reliability
            let quote = null;
            
            // Try IEX first (most reliable for real-time)
            quote = await this.getIEXQuote(symbol);
            
            if (!quote) {
                // Fallback to Alpha Vantage
                quote = await this.getAlphaVantageQuote(symbol);
            }

            if (!quote) {
                // Fallback to Yahoo Finance
                quote = await this.getYahooQuote(symbol);
            }

            if (quote) {
                // Cache the quote
                await this.redis.setEx(cacheKey, this.cacheSettings.realTimeQuote, JSON.stringify(quote));
                
                // Store in time series for historical tracking
                await this.storeHistoricalPoint(symbol, quote);
            }

            return quote;
        } catch (error) {
            console.error(`Error getting quote for ${symbol}:`, error);
            return null;
        }
    }

    // Get quotes for multiple symbols
    async getBatchQuotes(symbols) {
        try {
            const quotes = {};
            const uncachedSymbols = [];
            
            // Check cache for each symbol
            for (const symbol of symbols) {
                const cacheKey = `quote:${symbol.toUpperCase()}`;
                const cached = await this.redis.get(cacheKey);
                
                if (cached) {
                    quotes[symbol] = JSON.parse(cached);
                } else {
                    uncachedSymbols.push(symbol);
                }
            }

            // Fetch uncached symbols in batches
            if (uncachedSymbols.length > 0) {
                const batchQuotes = await this.fetchBatchQuotes(uncachedSymbols);
                
                for (const [symbol, quote] of Object.entries(batchQuotes)) {
                    quotes[symbol] = quote;
                    
                    // Cache individual quotes
                    const cacheKey = `quote:${symbol.toUpperCase()}`;
                    await this.redis.setEx(
                        cacheKey, 
                        this.cacheSettings.batchQuotes, 
                        JSON.stringify(quote)
                    );
                    
                    // Store historical point
                    await this.storeHistoricalPoint(symbol, quote);
                }
            }

            return quotes;
        } catch (error) {
            console.error('Error getting batch quotes:', error);
            return {};
        }
    }

    // Get extended quote with additional data
    async getExtendedQuote(symbol) {
        try {
            const cacheKey = `extended_quote:${symbol.toUpperCase()}`;
            
            // Try cache first
            const cached = await this.redis.get(cacheKey);
            if (cached) {
                return JSON.parse(cached);
            }

            // Get basic quote
            const basicQuote = await this.getQuote(symbol);
            if (!basicQuote) return null;

            // Get additional data
            const [fundamentals, technicals, news] = await Promise.all([
                this.getFundamentals(symbol),
                this.getTechnicalIndicators(symbol),
                this.getLatestNews(symbol, 5)
            ]);

            const extendedQuote = {
                ...basicQuote,
                fundamentals: fundamentals || {},
                technicals: technicals || {},
                news: news || [],
                lastUpdated: new Date().toISOString()
            };

            // Cache extended quote for longer period
            await this.redis.setEx(
                cacheKey, 
                this.cacheSettings.fundamentals, 
                JSON.stringify(extendedQuote)
            );

            return extendedQuote;
        } catch (error) {
            console.error(`Error getting extended quote for ${symbol}:`, error);
            return null;
        }
    }

    // Get historical data
    async getHistoricalData(symbol, period = '1y', interval = '1d') {
        try {
            const cacheKey = `historical:${symbol.toUpperCase()}:${period}:${interval}`;
            
            // Try cache first
            const cached = await this.redis.get(cacheKey);
            if (cached) {
                return JSON.parse(cached);
            }

            let data = null;

            // Try different providers
            data = await this.getAlphaVantageHistorical(symbol, period, interval);
            
            if (!data) {
                data = await this.getYahooHistorical(symbol, period, interval);
            }

            if (data) {
                await this.redis.setEx(
                    cacheKey, 
                    this.cacheSettings.historicalData, 
                    JSON.stringify(data)
                );
            }

            return data;
        } catch (error) {
            console.error(`Error getting historical data for ${symbol}:`, error);
            return null;
        }
    }

    // IEX Cloud implementation
    async getIEXQuote(symbol) {
        try {
            if (!this.apis.iex.key) return null;

            const response = await axios.get(`${this.apis.iex.baseUrl}/stock/${symbol}/quote`, {
                params: { token: this.apis.iex.key },
                timeout: 5000
            });

            const data = response.data;
            return {
                symbol: data.symbol,
                price: new Decimal(data.latestPrice || 0).toNumber(),
                change: new Decimal(data.change || 0).toNumber(),
                changePercent: new Decimal(data.changePercent || 0).mul(100).toNumber(),
                volume: data.volume || 0,
                open: new Decimal(data.open || 0).toNumber(),
                high: new Decimal(data.high || 0).toNumber(),
                low: new Decimal(data.low || 0).toNumber(),
                previousClose: new Decimal(data.previousClose || 0).toNumber(),
                marketCap: data.marketCap || 0,
                pe: data.peRatio || null,
                week52High: new Decimal(data.week52High || 0).toNumber(),
                week52Low: new Decimal(data.week52Low || 0).toNumber(),
                avgVolume: data.avgTotalVolume || 0,
                timestamp: new Date(data.latestUpdate).toISOString(),
                source: 'iex'
            };
        } catch (error) {
            console.error(`IEX API error for ${symbol}:`, error.message);
            return null;
        }
    }

    // Alpha Vantage implementation
    async getAlphaVantageQuote(symbol) {
        try {
            if (!this.apis.alphaVantage.key) return null;

            const response = await axios.get(this.apis.alphaVantage.baseUrl, {
                params: {
                    function: 'GLOBAL_QUOTE',
                    symbol: symbol,
                    apikey: this.apis.alphaVantage.key
                },
                timeout: 10000
            });

            const data = response.data['Global Quote'];
            if (!data || Object.keys(data).length === 0) return null;

            return {
                symbol: data['01. Symbol'],
                price: new Decimal(data['05. price'] || 0).toNumber(),
                change: new Decimal(data['09. change'] || 0).toNumber(),
                changePercent: new Decimal(data['10. change percent']?.replace('%', '') || 0).toNumber(),
                volume: parseInt(data['06. volume'] || 0),
                open: new Decimal(data['02. open'] || 0).toNumber(),
                high: new Decimal(data['03. high'] || 0).toNumber(),
                low: new Decimal(data['04. low'] || 0).toNumber(),
                previousClose: new Decimal(data['08. previous close'] || 0).toNumber(),
                timestamp: new Date(data['07. latest trading day']).toISOString(),
                source: 'alphavantage'
            };
        } catch (error) {
            console.error(`Alpha Vantage API error for ${symbol}:`, error.message);
            return null;
        }
    }

    // Yahoo Finance implementation (free but unofficial)
    async getYahooQuote(symbol) {
        try {
            const response = await axios.get(`${this.apis.yahoo.baseUrl}/${symbol}`, {
                timeout: 5000
            });

            const result = response.data.chart.result[0];
            const quote = result.meta;
            const indicators = result.indicators.quote[0];

            if (!quote) return null;

            return {
                symbol: quote.symbol,
                price: new Decimal(quote.regularMarketPrice || 0).toNumber(),
                change: new Decimal((quote.regularMarketPrice || 0) - (quote.previousClose || 0)).toNumber(),
                changePercent: new Decimal(((quote.regularMarketPrice || 0) - (quote.previousClose || 0)) / (quote.previousClose || 1) * 100).toNumber(),
                volume: quote.regularMarketVolume || 0,
                open: new Decimal(indicators.open?.[indicators.open.length - 1] || 0).toNumber(),
                high: new Decimal(indicators.high?.[indicators.high.length - 1] || 0).toNumber(),
                low: new Decimal(indicators.low?.[indicators.low.length - 1] || 0).toNumber(),
                previousClose: new Decimal(quote.previousClose || 0).toNumber(),
                marketCap: quote.marketCap || 0,
                timestamp: new Date(quote.regularMarketTime * 1000).toISOString(),
                source: 'yahoo'
            };
        } catch (error) {
            console.error(`Yahoo Finance API error for ${symbol}:`, error.message);
            return null;
        }
    }

    // Fetch multiple quotes efficiently
    async fetchBatchQuotes(symbols) {
        const quotes = {};
        
        // Split into smaller batches to avoid rate limits
        const batchSize = 10;
        const batches = [];
        
        for (let i = 0; i < symbols.length; i += batchSize) {
            batches.push(symbols.slice(i, i + batchSize));
        }

        // Process batches sequentially to avoid rate limiting
        for (const batch of batches) {
            const batchPromises = batch.map(symbol => 
                this.getQuote(symbol).then(quote => ({ symbol, quote }))
            );

            try {
                const results = await Promise.all(batchPromises);
                for (const { symbol, quote } of results) {
                    if (quote) {
                        quotes[symbol] = quote;
                    }
                }

                // Small delay between batches
                await new Promise(resolve => setTimeout(resolve, 200));
            } catch (error) {
                console.error('Error processing batch:', error);
            }
        }

        return quotes;
    }

    // Get company fundamentals
    async getFundamentals(symbol) {
        try {
            const cacheKey = `fundamentals:${symbol.toUpperCase()}`;
            
            const cached = await this.redis.get(cacheKey);
            if (cached) {
                return JSON.parse(cached);
            }

            // Try Alpha Vantage fundamentals
            let fundamentals = await this.getAlphaVantageFundamentals(symbol);
            
            if (fundamentals) {
                await this.redis.setEx(
                    cacheKey, 
                    this.cacheSettings.fundamentals, 
                    JSON.stringify(fundamentals)
                );
            }

            return fundamentals;
        } catch (error) {
            console.error(`Error getting fundamentals for ${symbol}:`, error);
            return null;
        }
    }

    // Get technical indicators
    async getTechnicalIndicators(symbol) {
        try {
            // Get recent price data for technical calculations
            const historicalData = await this.getHistoricalData(symbol, '3m', '1d');
            if (!historicalData || historicalData.length < 50) return null;

            const prices = historicalData.map(d => d.close);
            
            return {
                sma20: this.calculateSMA(prices, 20),
                sma50: this.calculateSMA(prices, 50),
                sma200: this.calculateSMA(prices, 200),
                ema12: this.calculateEMA(prices, 12),
                ema26: this.calculateEMA(prices, 26),
                rsi14: this.calculateRSI(prices, 14),
                macd: this.calculateMACD(prices),
                bollinger: this.calculateBollingerBands(prices, 20, 2)
            };
        } catch (error) {
            console.error(`Error calculating technical indicators for ${symbol}:`, error);
            return null;
        }
    }

    // Get latest news
    async getLatestNews(symbol, limit = 10) {
        try {
            if (!this.apis.alphaVantage.key) return [];

            const response = await axios.get(this.apis.alphaVantage.baseUrl, {
                params: {
                    function: 'NEWS_SENTIMENT',
                    tickers: symbol,
                    limit: limit,
                    apikey: this.apis.alphaVantage.key
                },
                timeout: 10000
            });

            const news = response.data.feed || [];
            return news.map(article => ({
                title: article.title,
                url: article.url,
                source: article.source,
                summary: article.summary,
                publishedAt: article.time_published,
                sentiment: article.overall_sentiment_label,
                sentimentScore: parseFloat(article.overall_sentiment_score || 0)
            }));
        } catch (error) {
            console.error(`Error getting news for ${symbol}:`, error);
            return [];
        }
    }

    // Background price updates for subscribed symbols
    startPriceUpdates() {
        setInterval(async () => {
            try {
                // Get list of subscribed symbols
                const subscribedSymbols = await this.redis.sMembers('subscribed_symbols');
                
                if (subscribedSymbols.length > 0) {
                    // Update quotes for subscribed symbols
                    const quotes = await this.getBatchQuotes(subscribedSymbols);
                    
                    // Broadcast updates via Redis pub/sub
                    for (const [symbol, quote] of Object.entries(quotes)) {
                        await this.redis.publish(`quote:${symbol}`, JSON.stringify(quote));
                    }
                }
            } catch (error) {
                console.error('Error in background price updates:', error);
            }
        }, 30000); // Update every 30 seconds
    }

    // Subscribe to symbol updates
    async subscribeToSymbol(symbol) {
        await this.redis.sAdd('subscribed_symbols', symbol.toUpperCase());
    }

    // Unsubscribe from symbol updates
    async unsubscribeFromSymbol(symbol) {
        await this.redis.sRem('subscribed_symbols', symbol.toUpperCase());
    }

    // Store historical price points
    async storeHistoricalPoint(symbol, quote) {
        try {
            const key = `historical_points:${symbol.toUpperCase()}`;
            const point = {
                timestamp: quote.timestamp || new Date().toISOString(),
                price: quote.price,
                volume: quote.volume
            };
            
            // Store in Redis sorted set with timestamp as score
            const timestamp = new Date(point.timestamp).getTime();
            await this.redis.zAdd(key, { score: timestamp, value: JSON.stringify(point) });
            
            // Keep only last 1000 points
            await this.redis.zRemRangeByRank(key, 0, -1001);
        } catch (error) {
            console.error(`Error storing historical point for ${symbol}:`, error);
        }
    }

    // Technical analysis helper functions
    calculateSMA(prices, period) {
        if (prices.length < period) return null;
        const recentPrices = prices.slice(-period);
        const sum = recentPrices.reduce((acc, price) => acc + price, 0);
        return sum / period;
    }

    calculateEMA(prices, period) {
        if (prices.length < period) return null;
        
        const multiplier = 2 / (period + 1);
        let ema = prices[0];
        
        for (let i = 1; i < prices.length; i++) {
            ema = (prices[i] * multiplier) + (ema * (1 - multiplier));
        }
        
        return ema;
    }

    calculateRSI(prices, period = 14) {
        if (prices.length < period + 1) return null;
        
        let gains = 0;
        let losses = 0;
        
        for (let i = 1; i <= period; i++) {
            const change = prices[i] - prices[i - 1];
            if (change > 0) gains += change;
            else losses += Math.abs(change);
        }
        
        const avgGain = gains / period;
        const avgLoss = losses / period;
        const rs = avgGain / avgLoss;
        
        return 100 - (100 / (1 + rs));
    }

    calculateMACD(prices) {
        const ema12 = this.calculateEMA(prices, 12);
        const ema26 = this.calculateEMA(prices, 26);
        
        if (!ema12 || !ema26) return null;
        
        return {
            line: ema12 - ema26,
            ema12,
            ema26
        };
    }

    calculateBollingerBands(prices, period = 20, stdDev = 2) {
        const sma = this.calculateSMA(prices, period);
        if (!sma || prices.length < period) return null;
        
        const recentPrices = prices.slice(-period);
        const variance = recentPrices.reduce((acc, price) => acc + Math.pow(price - sma, 2), 0) / period;
        const standardDeviation = Math.sqrt(variance);
        
        return {
            upper: sma + (standardDeviation * stdDev),
            middle: sma,
            lower: sma - (standardDeviation * stdDev)
        };
    }

    // Alpha Vantage fundamentals
    async getAlphaVantageFundamentals(symbol) {
        try {
            if (!this.apis.alphaVantage.key) return null;

            const response = await axios.get(this.apis.alphaVantage.baseUrl, {
                params: {
                    function: 'OVERVIEW',
                    symbol: symbol,
                    apikey: this.apis.alphaVantage.key
                },
                timeout: 10000
            });

            const data = response.data;
            if (!data || Object.keys(data).length === 0) return null;

            return {
                marketCap: parseInt(data.MarketCapitalization || 0),
                pe: parseFloat(data.PERatio || 0),
                peg: parseFloat(data.PEGRatio || 0),
                pb: parseFloat(data.PriceToBookRatio || 0),
                ev: parseInt(data.EVToEBITDA || 0),
                eps: parseFloat(data.EPS || 0),
                beta: parseFloat(data.Beta || 0),
                dividendYield: parseFloat(data.DividendYield || 0),
                payoutRatio: parseFloat(data.PayoutRatio || 0),
                profitMargin: parseFloat(data.ProfitMargin || 0),
                operatingMargin: parseFloat(data.OperatingMarginTTM || 0),
                returnOnAssets: parseFloat(data.ReturnOnAssetsTTM || 0),
                returnOnEquity: parseFloat(data.ReturnOnEquityTTM || 0),
                revenuePerShare: parseFloat(data.RevenuePerShareTTM || 0),
                quarterlyEarningsGrowth: parseFloat(data.QuarterlyEarningsGrowthYOY || 0),
                quarterlyRevenueGrowth: parseFloat(data.QuarterlyRevenueGrowthYOY || 0),
                analystTargetPrice: parseFloat(data.AnalystTargetPrice || 0),
                week52High: parseFloat(data['52WeekHigh'] || 0),
                week52Low: parseFloat(data['52WeekLow'] || 0)
            };
        } catch (error) {
            console.error(`Alpha Vantage fundamentals error for ${symbol}:`, error.message);
            return null;
        }
    }

    // Historical data implementations
    async getAlphaVantageHistorical(symbol, period, interval) {
        // Implementation would fetch historical data from Alpha Vantage
        return null;
    }

    async getYahooHistorical(symbol, period, interval) {
        // Implementation would fetch historical data from Yahoo Finance
        return null;
    }

    // Rate limiting helper
    async checkRateLimit(provider) {
        const key = `rate_limit:${provider}`;
        const current = await this.redis.incr(key);
        
        if (current === 1) {
            await this.redis.expire(key, 60); // 1 minute window
        }
        
        const limit = this.apis[provider]?.rateLimitPerMinute || 60;
        return current <= limit;
    }
}

export default RealTimeQuotes;