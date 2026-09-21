/**
 * Compression Benchmark and Testing Suite
 * Performance testing for different compression algorithms and configurations
 */

interface BenchmarkResult {
  algorithm: string;
  level: number;
  originalSize: number;
  compressedSize: number;
  compressionRatio: number;
  compressionTime: number;
  decompressionTime: number;
  throughput: number; // MB/s
}

interface BenchmarkSuite {
  testName: string;
  dataType: 'json' | 'html' | 'css' | 'javascript' | 'text' | 'binary';
  sampleSize: number;
  results: BenchmarkResult[];
}

class CompressionBenchmark {
  private testData: Map<string, Buffer> = new Map();

  constructor() {
    this.generateTestData();
  }

  /**
   * Generate test data for different content types
   */
  private generateTestData(): void {
    // JSON data
    const jsonData = {
      users: Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        name: `User ${i}`,
        email: `user${i}@example.com`,
        profile: {
          age: Math.floor(Math.random() * 80) + 18,
          city: `City ${i % 50}`,
          preferences: {
            theme: i % 2 === 0 ? 'dark' : 'light',
            language: ['en', 'es', 'fr', 'de'][i % 4],
            notifications: {
              email: i % 3 === 0,
              push: i % 2 === 0,
              sms: i % 5 === 0
            }
          }
        },
        metadata: {
          created: new Date(2020 + (i % 4), i % 12, (i % 28) + 1).toISOString(),
          lastActive: new Date().toISOString(),
          version: '1.0.0'
        }
      }))
    };
    this.testData.set('json', Buffer.from(JSON.stringify(jsonData)));

    // HTML data
    const htmlData = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Test Page</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; border-radius: 8px; padding: 20px; margin: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
          </style>
        </head>
        <body>
          <div class="container">
            ${Array.from({ length: 500 }, (_, i) => `
              <div class="card">
                <h2>Article ${i + 1}</h2>
                <p>This is the content of article ${i + 1}. It contains various information about topics that are interesting and relevant to our users.</p>
                <div class="meta">
                  <span>Published: ${new Date(2023, i % 12, (i % 28) + 1).toLocaleDateString()}</span>
                  <span>Author: Author ${i % 10}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </body>
      </html>
    `;
    this.testData.set('html', Buffer.from(htmlData));

    // CSS data
    const cssData = Array.from({ length: 200 }, (_, i) => `
      .component-${i} {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background-color: #${Math.floor(Math.random() * 16777215).toString(16)};
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 10px;
        margin: 5px;
        font-size: 14px;
        color: #333;
      }
      .component-${i}:hover {
        background-color: #f5f5f5;
        transform: scale(1.02);
        transition: all 0.2s ease;
      }
    `).join('\n');
    this.testData.set('css', Buffer.from(cssData));

    // JavaScript data
    const jsData = Array.from({ length: 100 }, (_, i) => `
      function processData${i}(input) {
        const result = [];
        for (let j = 0; j < input.length; j++) {
          const item = input[j];
          if (item && typeof item === 'object') {
            result.push({
              id: item.id || j,
              processed: true,
              timestamp: Date.now(),
              data: JSON.stringify(item)
            });
          }
        }
        return result.filter(item => item.processed);
      }
      
      const config${i} = {
        endpoint: 'https://api.example.com/v${i}',
        timeout: 5000,
        retries: 3,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer token${i}'
        }
      };
    `).join('\n');
    this.testData.set('javascript', Buffer.from(jsData));

    // Text data
    const textData = Array.from({ length: 1000 }, (_, i) => 
      `This is line ${i + 1} of the test document. It contains repetitive patterns and common English words that should compress well with various algorithms.`
    ).join('\n');
    this.testData.set('text', Buffer.from(textData));

    // Binary-like data (less compressible)
    const binaryData = Buffer.from(Array.from({ length: 50000 }, () => 
      Math.floor(Math.random() * 256)
    ));
    this.testData.set('binary', binaryData);
  }

  /**
   * Run comprehensive benchmark suite
   */
  async runBenchmarkSuite(): Promise<BenchmarkSuite[]> {
    const suites: BenchmarkSuite[] = [];

    for (const [dataType, buffer] of this.testData.entries()) {
      const suite: BenchmarkSuite = {
        testName: `Compression Benchmark - ${dataType.toUpperCase()}`,
        dataType: dataType as any,
        sampleSize: buffer.length,
        results: []
      };

      // Test Gzip with different levels
      for (let level = 1; level <= 9; level++) {
        const result = await this.benchmarkCompression(buffer, 'gzip', level);
        suite.results.push(result);
      }

      // Test Brotli with different quality levels
      for (let level = 1; level <= 6; level++) {
        const result = await this.benchmarkCompression(buffer, 'brotli', level);
        suite.results.push(result);
      }

      // Test Deflate with different levels
      for (let level = 1; level <= 9; level++) {
        const result = await this.benchmarkCompression(buffer, 'deflate', level);
        suite.results.push(result);
      }

      suites.push(suite);
    }

    return suites;
  }

  /**
   * Benchmark specific compression algorithm and level
   */
  private async benchmarkCompression(
    data: Buffer,
    algorithm: string,
    level: number
  ): Promise<BenchmarkResult> {
    const iterations = 10;
    const compressionTimes: number[] = [];
    const decompressionTimes: number[] = [];
    let compressedBuffer: Buffer;

    for (let i = 0; i < iterations; i++) {
      // Compression benchmark
      const compStart = process.hrtime.bigint();
      compressedBuffer = await this.compressData(data, algorithm, level);
      const compEnd = process.hrtime.bigint();
      compressionTimes.push(Number(compEnd - compStart) / 1000000); // Convert to ms

      // Decompression benchmark
      const decompStart = process.hrtime.bigint();
      await this.decompressData(compressedBuffer!, algorithm);
      const decompEnd = process.hrtime.bigint();
      decompressionTimes.push(Number(decompEnd - decompStart) / 1000000); // Convert to ms
    }

    const avgCompressionTime = compressionTimes.reduce((a, b) => a + b) / compressionTimes.length;
    const avgDecompressionTime = decompressionTimes.reduce((a, b) => a + b) / decompressionTimes.length;
    const throughput = (data.length / 1024 / 1024) / (avgCompressionTime / 1000); // MB/s

    return {
      algorithm,
      level,
      originalSize: data.length,
      compressedSize: compressedBuffer!.length,
      compressionRatio: compressedBuffer!.length / data.length,
      compressionTime: avgCompressionTime,
      decompressionTime: avgDecompressionTime,
      throughput
    };
  }

  /**
   * Compress data using specified algorithm and level
   */
  private async compressData(data: Buffer, algorithm: string, level: number): Promise<Buffer> {
    const { promisify } = require('util');
    
    switch (algorithm) {
      case 'gzip': {
        const { gzip } = require('zlib');
        const gzipAsync = promisify(gzip);
        return await gzipAsync(data, { level });
      }
      case 'brotli': {
        const { brotliCompress, constants } = require('zlib');
        const brotliAsync = promisify(brotliCompress);
        return await brotliAsync(data, {
          params: { [constants.BROTLI_PARAM_QUALITY]: level }
        });
      }
      case 'deflate': {
        const { deflate } = require('zlib');
        const deflateAsync = promisify(deflate);
        return await deflateAsync(data, { level });
      }
      default:
        throw new Error(`Unknown algorithm: ${algorithm}`);
    }
  }

  /**
   * Decompress data using specified algorithm
   */
  private async decompressData(data: Buffer, algorithm: string): Promise<Buffer> {
    const { promisify } = require('util');
    
    switch (algorithm) {
      case 'gzip': {
        const { gunzip } = require('zlib');
        const gunzipAsync = promisify(gunzip);
        return await gunzipAsync(data);
      }
      case 'brotli': {
        const { brotliDecompress } = require('zlib');
        const brotliAsync = promisify(brotliDecompress);
        return await brotliAsync(data);
      }
      case 'deflate': {
        const { inflate } = require('zlib');
        const inflateAsync = promisify(inflate);
        return await inflateAsync(data);
      }
      default:
        throw new Error(`Unknown algorithm: ${algorithm}`);
    }
  }

  /**
   * Generate benchmark report
   */
  generateReport(suites: BenchmarkSuite[]): string {
    let report = '# Compression Benchmark Report\n\n';
    
    for (const suite of suites) {
      report += `## ${suite.testName}\n`;
      report += `**Sample Size:** ${(suite.sampleSize / 1024).toFixed(1)} KB\n\n`;

      // Find best results
      const bestCompression = suite.results.reduce((best, current) => 
        current.compressionRatio < best.compressionRatio ? current : best
      );
      const fastestCompression = suite.results.reduce((fastest, current) =>
        current.compressionTime < fastest.compressionTime ? current : fastest
      );
      const bestThroughput = suite.results.reduce((best, current) =>
        current.throughput > best.throughput ? current : best
      );

      report += `**Best Compression:** ${bestCompression.algorithm}(${bestCompression.level}) - ${(bestCompression.compressionRatio * 100).toFixed(1)}% of original\n`;
      report += `**Fastest Compression:** ${fastestCompression.algorithm}(${fastestCompression.level}) - ${fastestCompression.compressionTime.toFixed(2)}ms\n`;
      report += `**Best Throughput:** ${bestThroughput.algorithm}(${bestThroughput.level}) - ${bestThroughput.throughput.toFixed(2)} MB/s\n\n`;

      // Detailed results table
      report += '| Algorithm | Level | Ratio (%) | Comp. Time (ms) | Decomp. Time (ms) | Throughput (MB/s) |\n';
      report += '|-----------|-------|-----------|-----------------|-------------------|-------------------|\n';

      suite.results
        .sort((a, b) => a.compressionRatio - b.compressionRatio)
        .forEach(result => {
          report += `| ${result.algorithm} | ${result.level} | ${(result.compressionRatio * 100).toFixed(1)} | ${result.compressionTime.toFixed(2)} | ${result.decompressionTime.toFixed(2)} | ${result.throughput.toFixed(2)} |\n`;
        });

      report += '\n';
    }

    return report;
  }

  /**
   * Get recommendations based on benchmark results
   */
  getRecommendations(suites: BenchmarkSuite[]): {
    dataType: string;
    recommended: {
      algorithm: string;
      level: number;
      reason: string;
    };
  }[] {
    const recommendations = [];

    for (const suite of suites) {
      let recommended;
      
      switch (suite.dataType) {
        case 'json':
        case 'text':
          // For text-based content, prioritize compression ratio
          recommended = suite.results
            .filter(r => r.compressionRatio < 0.7) // Only consider good compression
            .sort((a, b) => a.compressionRatio - b.compressionRatio)[0];
          recommended = recommended || suite.results[0];
          break;

        case 'html':
        case 'css':
        case 'javascript':
          // For web assets, balance compression and speed
          recommended = suite.results
            .sort((a, b) => {
              const scoreA = (a.compressionRatio * 0.7) + ((a.compressionTime / 1000) * 0.3);
              const scoreB = (b.compressionRatio * 0.7) + ((b.compressionTime / 1000) * 0.3);
              return scoreA - scoreB;
            })[0];
          break;

        case 'binary':
          // For binary data, prioritize speed over compression
          recommended = suite.results
            .filter(r => r.compressionTime < 50) // Fast compression
            .sort((a, b) => a.compressionRatio - b.compressionRatio)[0];
          recommended = recommended || suite.results.sort((a, b) => a.compressionTime - b.compressionTime)[0];
          break;

        default:
          recommended = suite.results.sort((a, b) => a.compressionRatio - b.compressionRatio)[0];
      }

      recommendations.push({
        dataType: suite.dataType,
        recommended: {
          algorithm: recommended.algorithm,
          level: recommended.level,
          reason: this.getRecommendationReason(suite.dataType, recommended)
        }
      });
    }

    return recommendations;
  }

  private getRecommendationReason(dataType: string, result: BenchmarkResult): string {
    if (result.compressionRatio < 0.3) {
      return `Excellent compression ratio (${(result.compressionRatio * 100).toFixed(1)}%) with acceptable speed`;
    }
    if (result.compressionTime < 10) {
      return `Very fast compression (${result.compressionTime.toFixed(2)}ms) with good ratio`;
    }
    if (result.throughput > 100) {
      return `High throughput (${result.throughput.toFixed(2)} MB/s) for real-time processing`;
    }
    return `Best overall balance of compression ratio and speed for ${dataType} content`;
  }
}

export default CompressionBenchmark;