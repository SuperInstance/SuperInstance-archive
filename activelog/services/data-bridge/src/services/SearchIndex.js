const { EventEmitter } = require('events');
const crypto = require('crypto');
const { Client } = require('elasticsearch');

class SearchIndex extends EventEmitter {
    constructor(options = {}) {
        super();
        this.indices = new Map();
        this.indexMappings = new Map();
        this.searchHistory = [];
        this.indexingQueue = [];
        this.analyzers = new Map();
        this.filters = new Map();
        
        // Elasticsearch client (mock for this implementation)
        this.esClient = options.elasticsearchClient || this.createMockESClient();
        this.defaultIndex = options.defaultIndex || 'unified-search';
        this.batchSize = options.batchSize || 100;
        this.maxSearchHistory = options.maxSearchHistory || 1000;
        
        this.initializeAnalyzers();
        this.initializeFilters();
        this.setupEventHandlers();
    }

    createMockESClient() {
        // Mock Elasticsearch client for demonstration
        return {
            indices: {
                create: async (params) => ({ acknowledged: true }),
                delete: async (params) => ({ acknowledged: true }),
                exists: async (params) => ({ body: true }),
                putMapping: async (params) => ({ acknowledged: true })
            },
            index: async (params) => ({ 
                _id: crypto.randomUUID(),
                result: 'created',
                _version: 1
            }),
            bulk: async (params) => ({
                items: params.body.filter(item => item.index).map(() => ({
                    index: { _id: crypto.randomUUID(), result: 'created' }
                }))
            }),
            search: async (params) => this.mockSearch(params),
            delete: async (params) => ({ result: 'deleted' }),
            update: async (params) => ({ result: 'updated' })
        };
    }

    async mockSearch(params) {
        // Simple mock search implementation
        const hits = [];
        const query = params.body?.query?.multi_match?.query || '';
        
        // Mock some search results
        if (query) {
            hits.push({
                _index: params.index,
                _id: crypto.randomUUID(),
                _score: 1.0,
                _source: {
                    title: `Mock result for: ${query}`,
                    content: `This is a mock search result for query "${query}"`,
                    type: 'document',
                    timestamp: new Date().toISOString()
                }
            });
        }

        return {
            hits: {
                total: { value: hits.length },
                hits
            },
            took: Math.floor(Math.random() * 100) + 10
        };
    }

    initializeAnalyzers() {
        // Standard text analyzer
        this.registerAnalyzer('standard', {
            tokenizer: 'standard',
            filters: ['lowercase', 'stop'],
            description: 'Standard text analysis'
        });

        // Content analyzer for documents
        this.registerAnalyzer('content', {
            tokenizer: 'standard',
            filters: ['lowercase', 'stop', 'stemmer', 'synonym'],
            description: 'Enhanced content analysis with stemming and synonyms'
        });

        // Code analyzer for technical content
        this.registerAnalyzer('code', {
            tokenizer: 'keyword',
            filters: ['lowercase'],
            description: 'Code and technical content analysis'
        });

        // Person/entity analyzer
        this.registerAnalyzer('entity', {
            tokenizer: 'standard',
            filters: ['lowercase'],
            description: 'Entity and person name analysis'
        });
    }

    initializeFilters() {
        // Privacy filter
        this.registerFilter('privacy', (doc) => {
            const sensitiveFields = ['ssn', 'password', 'credit_card', 'email'];
            const filtered = { ...doc };
            
            for (const field of sensitiveFields) {
                if (filtered[field]) {
                    filtered[field] = '[REDACTED]';
                }
            }
            
            return filtered;
        });

        // Content length filter
        this.registerFilter('content-length', (doc, options = {}) => {
            const maxLength = options.maxLength || 1000;
            if (doc.content && doc.content.length > maxLength) {
                return {
                    ...doc,
                    content: doc.content.substring(0, maxLength) + '...',
                    truncated: true
                };
            }
            return doc;
        });

        // Access control filter
        this.registerFilter('access-control', (doc, options = {}) => {
            const userRole = options.userRole;
            const requiredRole = doc.metadata?.requiredRole;
            
            if (requiredRole && userRole !== requiredRole) {
                return null; // Document filtered out
            }
            
            return doc;
        });
    }

    registerAnalyzer(name, config) {
        this.analyzers.set(name, config);
        this.emit('analyzer:registered', { name, config });
    }

    registerFilter(name, filterFn) {
        this.filters.set(name, filterFn);
        this.emit('filter:registered', { name, filterFn });
    }

    async createIndex(indexName, mapping = {}, settings = {}) {
        const indexConfig = {
            name: indexName,
            mapping: {
                properties: {
                    id: { type: 'keyword' },
                    type: { type: 'keyword' },
                    title: { 
                        type: 'text',
                        analyzer: 'standard',
                        fields: {
                            raw: { type: 'keyword' },
                            suggest: { type: 'completion' }
                        }
                    },
                    content: { 
                        type: 'text',
                        analyzer: 'content'
                    },
                    tags: { type: 'keyword' },
                    category: { type: 'keyword' },
                    source: { type: 'keyword' },
                    timestamp: { type: 'date' },
                    metadata: { type: 'object' },
                    ...mapping.properties
                },
                ...mapping
            },
            settings: {
                number_of_shards: 1,
                number_of_replicas: 0,
                analysis: {
                    analyzer: {
                        content: {
                            tokenizer: 'standard',
                            filter: ['lowercase', 'stop', 'stemmer']
                        }
                    }
                },
                ...settings
            },
            createdAt: new Date()
        };

        // Create index in Elasticsearch
        await this.esClient.indices.create({
            index: indexName,
            body: {
                mappings: indexConfig.mapping,
                settings: indexConfig.settings
            }
        });

        this.indices.set(indexName, indexConfig);
        this.indexMappings.set(indexName, indexConfig.mapping);

        this.emit('index:created', indexConfig);
        return indexConfig;
    }

    async indexDocument(indexName, document, options = {}) {
        const docId = document.id || crypto.randomUUID();
        const timestamp = new Date().toISOString();

        // Prepare document for indexing
        let indexableDoc = {
            ...document,
            id: docId,
            indexed_at: timestamp,
            source: options.source || 'unknown'
        };

        // Apply preprocessing filters
        const filters = options.filters || ['privacy'];
        for (const filterName of filters) {
            const filter = this.filters.get(filterName);
            if (filter) {
                indexableDoc = filter(indexableDoc, options);
                if (!indexableDoc) {
                    this.emit('document:filtered', { docId, filter: filterName });
                    return null;
                }
            }
        }

        // Extract searchable content
        const searchableContent = this.extractSearchableContent(indexableDoc);
        indexableDoc.searchable_content = searchableContent;

        // Index document
        const result = await this.esClient.index({
            index: indexName,
            id: docId,
            body: indexableDoc
        });

        this.emit('document:indexed', {
            indexName,
            docId,
            result: result.result,
            source: indexableDoc.source
        });

        return {
            id: docId,
            index: indexName,
            result: result.result,
            version: result._version
        };
    }

    async bulkIndex(indexName, documents, options = {}) {
        const bulkId = crypto.randomUUID();
        const bulkInfo = {
            id: bulkId,
            indexName,
            totalDocuments: documents.length,
            successful: 0,
            failed: 0,
            errors: [],
            startTime: new Date()
        };

        this.emit('bulk-index:started', bulkInfo);

        try {
            // Process documents in batches
            for (let i = 0; i < documents.length; i += this.batchSize) {
                const batch = documents.slice(i, i + this.batchSize);
                const bulkBody = [];

                for (const doc of batch) {
                    const docId = doc.id || crypto.randomUUID();
                    
                    // Apply preprocessing
                    let processedDoc = { ...doc, id: docId, indexed_at: new Date().toISOString() };
                    
                    const filters = options.filters || ['privacy'];
                    let filtered = false;
                    for (const filterName of filters) {
                        const filter = this.filters.get(filterName);
                        if (filter) {
                            processedDoc = filter(processedDoc, options);
                            if (!processedDoc) {
                                filtered = true;
                                break;
                            }
                        }
                    }

                    if (!filtered) {
                        bulkBody.push({ index: { _index: indexName, _id: docId } });
                        bulkBody.push({
                            ...processedDoc,
                            searchable_content: this.extractSearchableContent(processedDoc)
                        });
                    }
                }

                if (bulkBody.length > 0) {
                    const bulkResponse = await this.esClient.bulk({ body: bulkBody });
                    
                    // Process bulk response
                    for (const item of bulkResponse.items) {
                        if (item.index.error) {
                            bulkInfo.failed++;
                            bulkInfo.errors.push(item.index.error);
                        } else {
                            bulkInfo.successful++;
                        }
                    }
                }

                this.emit('bulk-index:progress', {
                    bulkId,
                    processed: Math.min(i + this.batchSize, documents.length),
                    total: documents.length
                });
            }

            bulkInfo.endTime = new Date();
            bulkInfo.duration = bulkInfo.endTime - bulkInfo.startTime;

            this.emit('bulk-index:completed', bulkInfo);
            return bulkInfo;

        } catch (error) {
            bulkInfo.error = error.message;
            this.emit('bulk-index:failed', bulkInfo);
            throw error;
        }
    }

    extractSearchableContent(document) {
        const searchableFields = ['title', 'content', 'description', 'tags'];
        const content = [];

        for (const field of searchableFields) {
            if (document[field]) {
                if (Array.isArray(document[field])) {
                    content.push(...document[field]);
                } else {
                    content.push(document[field]);
                }
            }
        }

        return content.join(' ');
    }

    async search(query, options = {}) {
        const searchId = crypto.randomUUID();
        const searchInfo = {
            id: searchId,
            query: query,
            index: options.index || this.defaultIndex,
            startTime: new Date(),
            userId: options.userId
        };

        this.emit('search:started', searchInfo);

        try {
            const searchParams = this.buildSearchParams(query, options);
            const response = await this.esClient.search(searchParams);

            // Process search results
            const results = this.processSearchResults(response, options);

            searchInfo.endTime = new Date();
            searchInfo.duration = searchInfo.endTime - searchInfo.startTime;
            searchInfo.resultCount = results.hits.length;
            searchInfo.totalHits = response.hits.total.value;

            // Store search history
            this.searchHistory.push(searchInfo);
            if (this.searchHistory.length > this.maxSearchHistory) {
                this.searchHistory.shift();
            }

            this.emit('search:completed', searchInfo);

            return {
                query,
                took: response.took,
                total: response.hits.total.value,
                hits: results.hits,
                aggregations: results.aggregations,
                searchId
            };

        } catch (error) {
            searchInfo.error = error.message;
            this.emit('search:failed', searchInfo);
            throw error;
        }
    }

    buildSearchParams(query, options) {
        const params = {
            index: options.index || this.defaultIndex,
            size: options.size || 20,
            from: options.from || 0,
            body: {}
        };

        // Build query
        if (typeof query === 'string') {
            params.body.query = {
                multi_match: {
                    query,
                    fields: options.fields || ['title^2', 'content', 'tags', 'searchable_content'],
                    type: options.matchType || 'best_fields',
                    fuzziness: options.fuzziness || 'AUTO'
                }
            };
        } else if (typeof query === 'object') {
            params.body.query = query;
        }

        // Add filters
        if (options.filters && Object.keys(options.filters).length > 0) {
            const filters = Object.entries(options.filters).map(([field, value]) => {
                if (Array.isArray(value)) {
                    return { terms: { [field]: value } };
                } else {
                    return { term: { [field]: value } };
                }
            });

            params.body.query = {
                bool: {
                    must: params.body.query,
                    filter: filters
                }
            };
        }

        // Add date range
        if (options.dateRange) {
            const dateFilter = {
                range: {
                    [options.dateField || 'timestamp']: options.dateRange
                }
            };

            if (params.body.query.bool) {
                params.body.query.bool.filter.push(dateFilter);
            } else {
                params.body.query = {
                    bool: {
                        must: params.body.query,
                        filter: [dateFilter]
                    }
                };
            }
        }

        // Add sorting
        if (options.sort) {
            params.body.sort = Array.isArray(options.sort) ? options.sort : [options.sort];
        } else {
            params.body.sort = [
                { _score: { order: 'desc' } },
                { timestamp: { order: 'desc' } }
            ];
        }

        // Add aggregations
        if (options.aggregations) {
            params.body.aggs = options.aggregations;
        } else {
            // Default aggregations
            params.body.aggs = {
                sources: {
                    terms: { field: 'source', size: 10 }
                },
                types: {
                    terms: { field: 'type', size: 10 }
                },
                categories: {
                    terms: { field: 'category', size: 10 }
                }
            };
        }

        // Add highlighting
        if (options.highlight !== false) {
            params.body.highlight = {
                pre_tags: ['<mark>'],
                post_tags: ['</mark>'],
                fields: {
                    title: {},
                    content: { fragment_size: 150 },
                    searchable_content: { fragment_size: 150 }
                }
            };
        }

        return params;
    }

    processSearchResults(response, options) {
        const hits = response.hits.hits.map(hit => {
            let result = {
                id: hit._id,
                index: hit._index,
                score: hit._score,
                source: hit._source,
                highlight: hit.highlight
            };

            // Apply post-processing filters
            const filters = options.postFilters || ['access-control'];
            for (const filterName of filters) {
                const filter = this.filters.get(filterName);
                if (filter) {
                    result.source = filter(result.source, options);
                    if (!result.source) {
                        return null; // Filter out this result
                    }
                }
            }

            return result;
        }).filter(Boolean);

        return {
            hits,
            aggregations: response.aggregations
        };
    }

    async suggest(text, options = {}) {
        const suggestionParams = {
            index: options.index || this.defaultIndex,
            body: {
                suggest: {
                    title_suggest: {
                        prefix: text,
                        completion: {
                            field: 'title.suggest',
                            size: options.size || 10
                        }
                    }
                }
            }
        };

        const response = await this.esClient.search(suggestionParams);
        return response.suggest.title_suggest[0].options.map(option => ({
            text: option.text,
            score: option._score,
            source: option._source
        }));
    }

    async updateDocument(indexName, docId, updates, options = {}) {
        const updateDoc = {
            ...updates,
            updated_at: new Date().toISOString()
        };

        if (updates.content || updates.title || updates.tags) {
            updateDoc.searchable_content = this.extractSearchableContent({
                ...updates,
                content: updates.content,
                title: updates.title,
                tags: updates.tags
            });
        }

        const result = await this.esClient.update({
            index: indexName,
            id: docId,
            body: {
                doc: updateDoc
            }
        });

        this.emit('document:updated', {
            indexName,
            docId,
            result: result.result
        });

        return result;
    }

    async deleteDocument(indexName, docId) {
        const result = await this.esClient.delete({
            index: indexName,
            id: docId
        });

        this.emit('document:deleted', {
            indexName,
            docId,
            result: result.result
        });

        return result;
    }

    async reindex(sourceIndex, targetIndex, options = {}) {
        const reindexId = crypto.randomUUID();
        const reindexInfo = {
            id: reindexId,
            sourceIndex,
            targetIndex,
            startTime: new Date()
        };

        this.emit('reindex:started', reindexInfo);

        try {
            // Simple reindex implementation
            // In production, use Elasticsearch's reindex API
            const searchResponse = await this.esClient.search({
                index: sourceIndex,
                scroll: '5m',
                size: this.batchSize,
                body: { query: { match_all: {} } }
            });

            let documents = searchResponse.hits.hits.map(hit => hit._source);
            await this.bulkIndex(targetIndex, documents, options);

            reindexInfo.endTime = new Date();
            reindexInfo.documentsProcessed = documents.length;

            this.emit('reindex:completed', reindexInfo);
            return reindexInfo;

        } catch (error) {
            reindexInfo.error = error.message;
            this.emit('reindex:failed', reindexInfo);
            throw error;
        }
    }

    async deleteIndex(indexName) {
        await this.esClient.indices.delete({ index: indexName });
        
        this.indices.delete(indexName);
        this.indexMappings.delete(indexName);

        this.emit('index:deleted', { indexName });
    }

    getSearchAnalytics(options = {}) {
        const since = options.since ? new Date(options.since) : new Date(Date.now() - 24 * 60 * 60 * 1000);
        const recentSearches = this.searchHistory.filter(search => search.startTime >= since);

        const analytics = {
            totalSearches: recentSearches.length,
            averageResponseTime: 0,
            topQueries: {},
            searchVolume: {},
            successfulSearches: 0,
            failedSearches: 0
        };

        if (recentSearches.length > 0) {
            const totalDuration = recentSearches.reduce((sum, search) => sum + (search.duration || 0), 0);
            analytics.averageResponseTime = totalDuration / recentSearches.length;

            // Count query frequencies
            recentSearches.forEach(search => {
                const query = search.query;
                analytics.topQueries[query] = (analytics.topQueries[query] || 0) + 1;
                
                if (search.error) {
                    analytics.failedSearches++;
                } else {
                    analytics.successfulSearches++;
                }

                // Group by hour for search volume
                const hour = new Date(search.startTime).toISOString().substring(0, 13);
                analytics.searchVolume[hour] = (analytics.searchVolume[hour] || 0) + 1;
            });

            // Sort top queries
            analytics.topQueries = Object.entries(analytics.topQueries)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 10)
                .reduce((obj, [query, count]) => {
                    obj[query] = count;
                    return obj;
                }, {});
        }

        return analytics;
    }

    setupEventHandlers() {
        this.on('search:completed', (info) => {
            console.log(`Search completed: "${info.query}" found ${info.resultCount} results in ${info.duration}ms`);
        });

        this.on('document:indexed', (info) => {
            console.log(`Document indexed: ${info.docId} in ${info.indexName}`);
        });

        this.on('bulk-index:completed', (info) => {
            console.log(`Bulk index completed: ${info.successful}/${info.totalDocuments} documents indexed`);
        });
    }

    getStats() {
        return {
            indices: this.indices.size,
            analyzers: this.analyzers.size,
            filters: this.filters.size,
            searchHistory: this.searchHistory.length,
            indexingQueue: this.indexingQueue.length
        };
    }

    getIndices() {
        return Array.from(this.indices.values());
    }

    getSearchHistory(limit = 100) {
        return this.searchHistory
            .sort((a, b) => b.startTime - a.startTime)
            .slice(0, limit);
    }

    reset() {
        this.indices.clear();
        this.indexMappings.clear();
        this.searchHistory.length = 0;
        this.indexingQueue.length = 0;
        this.emit('reset');
    }
}

module.exports = SearchIndex;