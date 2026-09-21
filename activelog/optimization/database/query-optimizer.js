const fs = require('fs');
const path = require('path');

class DatabaseQueryOptimizer {
  constructor(config = {}) {
    this.config = {
      slowQueryThreshold: config.slowQueryThreshold || 1000, // ms
      enableLogging: config.enableLogging ?? true,
      enableIndexSuggestions: config.enableIndexSuggestions ?? true,
      enableQueryRewriting: config.enableQueryRewriting ?? true,
      cacheSize: config.cacheSize || 1000,
      ...config
    };
    
    this.queryCache = new Map();
    this.slowQueries = new Map();
    this.queryStats = new Map();
    this.indexSuggestions = new Set();
  }

  // Analyze query performance and suggest optimizations
  analyzeQuery(query, executionTime, params = []) {
    const queryKey = this.normalizeQuery(query);
    
    // Track query statistics
    this.updateQueryStats(queryKey, executionTime);
    
    // Check for slow queries
    if (executionTime > this.config.slowQueryThreshold) {
      this.recordSlowQuery(queryKey, query, executionTime, params);
    }

    // Generate optimization suggestions
    const suggestions = this.generateOptimizationSuggestions(query, executionTime);
    
    return {
      queryKey,
      executionTime,
      suggestions,
      isOptimized: suggestions.length === 0
    };
  }

  // Normalize query for consistent caching and analysis
  normalizeQuery(query) {
    return query
      .replace(/\s+/g, ' ')
      .replace(/\$\d+|\?/g, '?')
      .trim()
      .toLowerCase();
  }

  // Update query execution statistics
  updateQueryStats(queryKey, executionTime) {
    if (!this.queryStats.has(queryKey)) {
      this.queryStats.set(queryKey, {
        count: 0,
        totalTime: 0,
        avgTime: 0,
        minTime: Infinity,
        maxTime: 0
      });
    }

    const stats = this.queryStats.get(queryKey);
    stats.count++;
    stats.totalTime += executionTime;
    stats.avgTime = stats.totalTime / stats.count;
    stats.minTime = Math.min(stats.minTime, executionTime);
    stats.maxTime = Math.max(stats.maxTime, executionTime);
  }

  // Record slow query for analysis
  recordSlowQuery(queryKey, originalQuery, executionTime, params) {
    if (!this.slowQueries.has(queryKey)) {
      this.slowQueries.set(queryKey, {
        query: originalQuery,
        occurrences: [],
        avgTime: 0,
        count: 0
      });
    }

    const slowQuery = this.slowQueries.get(queryKey);
    slowQuery.occurrences.push({
      timestamp: new Date(),
      executionTime,
      params: params.slice(0, 10) // Limit params for memory
    });
    
    slowQuery.count++;
    slowQuery.avgTime = slowQuery.occurrences.reduce((sum, occ) => sum + occ.executionTime, 0) / slowQuery.count;

    if (this.config.enableLogging) {
      console.warn(`Slow Query Detected [${executionTime}ms]: ${originalQuery.substring(0, 100)}...`);
    }
  }

  // Generate optimization suggestions based on query analysis
  generateOptimizationSuggestions(query, executionTime) {
    const suggestions = [];
    const queryLower = query.toLowerCase();

    // Check for missing WHERE clause
    if (queryLower.includes('select') && !queryLower.includes('where') && !queryLower.includes('limit')) {
      suggestions.push({
        type: 'missing_where',
        message: 'Consider adding a WHERE clause to limit the result set',
        impact: 'high',
        suggestion: 'Add WHERE clause with appropriate conditions'
      });
    }

    // Check for SELECT *
    if (queryLower.includes('select *')) {
      suggestions.push({
        type: 'select_star',
        message: 'Avoid SELECT * - specify only needed columns',
        impact: 'medium',
        suggestion: 'Replace SELECT * with specific column names'
      });
    }

    // Check for missing ORDER BY with LIMIT
    if (queryLower.includes('limit') && !queryLower.includes('order by')) {
      suggestions.push({
        type: 'limit_without_order',
        message: 'LIMIT without ORDER BY may return inconsistent results',
        impact: 'medium',
        suggestion: 'Add ORDER BY clause before LIMIT'
      });
    }

    // Check for OR conditions that might benefit from UNION
    if ((queryLower.match(/\bor\b/g) || []).length > 3) {
      suggestions.push({
        type: 'multiple_or_conditions',
        message: 'Multiple OR conditions may be inefficient',
        impact: 'medium',
        suggestion: 'Consider rewriting as UNION or using IN clause'
      });
    }

    // Check for subqueries that might benefit from JOINs
    if (queryLower.includes('select') && (queryLower.match(/\bselect\b/g) || []).length > 1) {
      suggestions.push({
        type: 'subquery_optimization',
        message: 'Subquery might be optimized with JOIN',
        impact: 'medium',
        suggestion: 'Consider rewriting subquery as JOIN for better performance'
      });
    }

    // Check for LIKE with leading wildcard
    if (queryLower.includes("like '%")) {
      suggestions.push({
        type: 'like_leading_wildcard',
        message: 'LIKE with leading wildcard cannot use index',
        impact: 'high',
        suggestion: 'Avoid leading wildcards or use full-text search'
      });
    }

    // Suggest indexes based on WHERE and JOIN conditions
    this.suggestIndexes(query).forEach(indexSuggestion => {
      suggestions.push({
        type: 'index_suggestion',
        message: `Consider creating index: ${indexSuggestion}`,
        impact: 'high',
        suggestion: `CREATE INDEX idx_${indexSuggestion.replace(/[^a-zA-Z0-9_]/g, '_')} ON table_name (${indexSuggestion})`
      });
    });

    return suggestions;
  }

  // Suggest database indexes based on query patterns
  suggestIndexes(query) {
    const suggestions = [];
    const queryLower = query.toLowerCase();

    // Extract WHERE conditions
    const whereMatch = queryLower.match(/where\s+(.+?)(?:\s+order\s+by|\s+group\s+by|\s+having|\s+limit|$)/i);
    if (whereMatch) {
      const whereClause = whereMatch[1];
      
      // Find column references in WHERE clause
      const columnMatches = whereClause.match(/(\w+)\s*[=<>!]/g);
      if (columnMatches) {
        columnMatches.forEach(match => {
          const column = match.replace(/\s*[=<>!].*/, '').trim();
          if (column.length > 1) {
            suggestions.push(column);
          }
        });
      }
    }

    // Extract JOIN conditions
    const joinMatches = queryLower.match(/join\s+\w+\s+on\s+([^\\s]+)/gi);
    if (joinMatches) {
      joinMatches.forEach(match => {
        const onClause = match.replace(/.*on\s+/i, '');
        const columns = onClause.match(/(\w+\.\w+)/g);
        if (columns) {
          columns.forEach(col => {
            const column = col.split('.')[1];
            if (column) suggestions.push(column);
          });
        }
      });
    }

    // Extract ORDER BY columns
    const orderMatch = queryLower.match(/order\s+by\s+([^\\s]+(?:\s*,\s*[^\\s]+)*)/i);
    if (orderMatch) {
      const orderColumns = orderMatch[1].split(',').map(col => col.trim().replace(/\s+desc|\s+asc/i, ''));
      suggestions.push(...orderColumns);
    }

    return [...new Set(suggestions)].filter(s => s && s.length > 1);
  }

  // Rewrite query for better performance
  rewriteQuery(query) {
    if (!this.config.enableQueryRewriting) {
      return query;
    }

    let rewritten = query;

    // Convert correlated subqueries to JOINs where possible
    rewritten = this.convertSubqueriesToJoins(rewritten);
    
    // Optimize IN clauses
    rewritten = this.optimizeInClauses(rewritten);
    
    // Add LIMIT to unbounded queries
    rewritten = this.addLimitToUnboundedQueries(rewritten);

    return rewritten;
  }

  // Convert some subqueries to JOINs for better performance
  convertSubqueriesToJoins(query) {
    // This is a simplified example - real implementation would be more complex
    const subqueryPattern = /WHERE\s+(\w+)\s+IN\s+\(\s*SELECT\s+(\w+)\s+FROM\s+(\w+)\s*\)/gi;
    
    return query.replace(subqueryPattern, (match, col1, col2, table) => {
      return `INNER JOIN ${table} ON ${col1} = ${col2}`;
    });
  }

  // Optimize IN clauses with many values
  optimizeInClauses(query) {
    const inPattern = /IN\s*\([^)]{100,}\)/gi; // IN clauses with 100+ characters
    
    return query.replace(inPattern, (match) => {
      console.warn('Large IN clause detected - consider using temporary table or EXISTS');
      return match; // Return as-is for now
    });
  }

  // Add LIMIT to potentially unbounded queries
  addLimitToUnboundedQueries(query) {
    const queryLower = query.toLowerCase();
    
    if (queryLower.includes('select') && 
        !queryLower.includes('where') && 
        !queryLower.includes('limit') &&
        !queryLower.includes('count(')) {
      
      console.warn('Adding safety LIMIT to unbounded query');
      return query + ' LIMIT 1000';
    }
    
    return query;
  }

  // Generate performance report
  generatePerformanceReport() {
    const report = {
      timestamp: new Date().toISOString(),
      totalQueries: this.queryStats.size,
      slowQueries: this.slowQueries.size,
      indexSuggestions: Array.from(this.indexSuggestions),
      topSlowQueries: this.getTopSlowQueries(10),
      queryStatistics: this.getQueryStatistics(),
      recommendations: this.getGeneralRecommendations()
    };

    return report;
  }

  // Get top slow queries
  getTopSlowQueries(limit = 10) {
    return Array.from(this.slowQueries.entries())
      .map(([key, data]) => ({
        queryKey: key,
        avgExecutionTime: data.avgTime,
        count: data.count,
        lastOccurrence: data.occurrences[data.occurrences.length - 1]?.timestamp
      }))
      .sort((a, b) => b.avgExecutionTime - a.avgExecutionTime)
      .slice(0, limit);
  }

  // Get overall query statistics
  getQueryStatistics() {
    const stats = Array.from(this.queryStats.values());
    
    return {
      totalExecutions: stats.reduce((sum, s) => sum + s.count, 0),
      averageExecutionTime: stats.reduce((sum, s) => sum + s.avgTime, 0) / stats.length,
      slowestQuery: Math.max(...stats.map(s => s.maxTime)),
      fastestQuery: Math.min(...stats.map(s => s.minTime))
    };
  }

  // Get general optimization recommendations
  getGeneralRecommendations() {
    const recommendations = [];

    if (this.slowQueries.size > this.queryStats.size * 0.1) {
      recommendations.push({
        type: 'high_slow_query_ratio',
        message: 'High percentage of slow queries detected',
        action: 'Review database indexes and query patterns'
      });
    }

    if (this.indexSuggestions.size > 5) {
      recommendations.push({
        type: 'many_index_suggestions',
        message: 'Many index suggestions generated',
        action: 'Consider implementing suggested indexes'
      });
    }

    return recommendations;
  }

  // Save performance report to file
  saveReport(filename = null) {
    const report = this.generatePerformanceReport();
    const reportFilename = filename || `query-performance-${Date.now()}.json`;
    const reportPath = path.join(__dirname, 'reports', reportFilename);
    
    // Ensure reports directory exists
    const reportsDir = path.join(__dirname, 'reports');
    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }

    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`Performance report saved to: ${reportPath}`);
    
    return reportPath;
  }

  // Clear collected statistics
  reset() {
    this.queryCache.clear();
    this.slowQueries.clear();
    this.queryStats.clear();
    this.indexSuggestions.clear();
  }

  // Database-specific optimizers
  
  // PostgreSQL specific optimizations
  optimizePostgreSQL(query) {
    let optimized = query;
    
    // Suggest ANALYZE for better query planning
    if (!query.toLowerCase().includes('analyze')) {
      console.log('Consider running ANALYZE on tables for better query planning');
    }
    
    // Convert LIKE to pattern matching operators for better performance
    optimized = optimized.replace(/LIKE\s+'([^%]+)%'/gi, "~ '^$1'");
    
    return optimized;
  }

  // MySQL specific optimizations
  optimizeMySQL(query) {
    let optimized = query;
    
    // Convert to InnoDB hints where appropriate
    if (query.toLowerCase().includes('select') && query.toLowerCase().includes('join')) {
      optimized = optimized.replace(/SELECT/i, 'SELECT /*+ USE_INDEX */');
    }
    
    return optimized;
  }

  // MongoDB aggregation pipeline optimizer
  optimizeMongoAggregation(pipeline) {
    const optimized = [...pipeline];
    
    // Move $match stages to the beginning
    const matchStages = optimized.filter(stage => stage.$match);
    const otherStages = optimized.filter(stage => !stage.$match);
    
    if (matchStages.length > 0) {
      return [...matchStages, ...otherStages];
    }
    
    return optimized;
  }
}

// Query execution wrapper with optimization
class OptimizedQueryExecutor {
  constructor(database, optimizer) {
    this.database = database;
    this.optimizer = optimizer;
  }

  async execute(query, params = []) {
    const startTime = Date.now();
    
    try {
      // Rewrite query if optimization is enabled
      const optimizedQuery = this.optimizer.rewriteQuery(query);
      
      // Execute the query
      const result = await this.database.query(optimizedQuery, params);
      
      const executionTime = Date.now() - startTime;
      
      // Analyze the query performance
      this.optimizer.analyzeQuery(query, executionTime, params);
      
      return result;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.optimizer.analyzeQuery(query, executionTime, params);
      throw error;
    }
  }
}

module.exports = {
  DatabaseQueryOptimizer,
  OptimizedQueryExecutor
};