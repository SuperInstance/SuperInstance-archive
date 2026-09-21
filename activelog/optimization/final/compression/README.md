# API Response Compression System

High-performance compression middleware with intelligent algorithm selection, caching, and monitoring.

## Features

- **Multi-Algorithm Support**: Gzip, Brotli, and Deflate compression
- **Smart Algorithm Selection**: Automatic selection based on content type and client support
- **Response Caching**: Built-in compression cache with LRU eviction
- **Performance Monitoring**: Comprehensive statistics and benchmarking
- **Express Integration**: Drop-in middleware for Express applications

## Quick Start

```typescript
import express from 'express';
import { compressionMiddleware } from './ResponseCompressor';

const app = express();

// Add compression middleware
app.use(compressionMiddleware({
  threshold: 1024,
  cacheSize: 50 * 1024 * 1024, // 50MB cache
}));

app.get('/api/data', (req, res) => {
  res.json({ large: 'data', array: new Array(1000).fill('item') });
});
```

## Algorithm Selection

The system automatically selects the best compression algorithm based on:

1. **Client Support** (Accept-Encoding header)
2. **Content Type** (JSON/text prefer Brotli, binary prefers Gzip)
3. **Content Size** (larger content may use Brotli for better compression)

## Configuration

```typescript
import { responseCompressor } from './ResponseCompressor';

// Configure Gzip settings
responseCompressor.configure('gzip', {
  level: 6,        // Compression level (1-9)
  threshold: 1024, // Minimum size to compress
  chunkSize: 16384 // Processing chunk size
});

// Configure Brotli settings
responseCompressor.configure('br', {
  level: 4,        // Quality level (0-11)
  threshold: 2048
});
```

## Monitoring

```typescript
import { useCompressionStats } from './ResponseCompressor';

// React component for monitoring
function CompressionDashboard() {
  const stats = useCompressionStats();

  return (
    <div>
      <h3>Compression Statistics</h3>
      <p>Total Requests: {stats.totalRequests}</p>
      <p>Avg Compression Ratio: {(stats.avgCompressionRatio * 100).toFixed(1)}%</p>
      <p>Avg Processing Time: {stats.avgProcessingTime.toFixed(2)}ms</p>
    </div>
  );
}
```

## Benchmarking

```typescript
import CompressionBenchmark from './CompressionBenchmark';

const benchmark = new CompressionBenchmark();

// Run comprehensive benchmarks
const results = await benchmark.runBenchmarkSuite();

// Generate detailed report
const report = benchmark.generateReport(results);
console.log(report);

// Get algorithm recommendations
const recommendations = benchmark.getRecommendations(results);
```

## Performance Tips

1. **Set Appropriate Thresholds**: Don't compress small responses (< 1KB)
2. **Use Brotli for Text**: Better compression for JSON, HTML, CSS, JS
3. **Cache Compressed Responses**: Avoid recompressing identical content
4. **Monitor Performance**: Use built-in statistics to optimize settings

## Compression Ratios by Content Type

| Content Type | Gzip | Brotli | Deflate |
|--------------|------|--------|---------|
| JSON         | 70-80% | 60-75% | 75-85% |
| HTML         | 65-75% | 55-70% | 70-80% |
| CSS          | 70-80% | 60-75% | 75-85% |
| JavaScript   | 65-75% | 55-70% | 70-80% |
| Text         | 60-70% | 50-65% | 65-75% |

## Cache Management

The compression cache automatically manages memory with:

- **LRU Eviction**: Removes least recently used entries when full
- **Size Monitoring**: Tracks total cache memory usage
- **Configurable Limits**: Set maximum cache size per application needs

```typescript
// Check cache status
const cacheInfo = responseCompressor.getCacheInfo();
console.log(`Cache: ${cacheInfo.entries} entries, ${cacheInfo.size} bytes`);

// Clear cache if needed
responseCompressor.clearCache();
```