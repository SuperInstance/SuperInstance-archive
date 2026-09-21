import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import ws from 'k6/ws';

// Custom metrics
const dataSyncFailureRate = new Rate('data_sync_failures');
const searchResponseTime = new Trend('search_response_time');
const indexingRate = new Counter('documents_indexed');
const activeConnections = new Gauge('websocket_connections');

export const options = {
  scenarios: {
    // Data sync load test
    data_sync_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '3m', target: 15 },   // Ramp up to 15 users
        { duration: '10m', target: 15 },  // Maintain 15 users
        { duration: '2m', target: 30 },   // Ramp up to 30 users
        { duration: '5m', target: 30 },   // Maintain 30 users
        { duration: '2m', target: 0 },    // Ramp down
      ],
    },
    
    // Search performance test
    search_performance: {
      executor: 'constant-arrival-rate',
      rate: 50, // 50 requests per second
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 20,
      maxVUs: 100,
      startTime: '22m',
    },
    
    // WebSocket connections test
    websocket_load: {
      executor: 'constant-vus',
      vus: 50,
      duration: '15m',
      startTime: '5m',
    },
    
    // Bulk operations test
    bulk_operations: {
      executor: 'shared-iterations',
      vus: 10,
      iterations: 100,
      startTime: '35m',
    },
  },
  
  thresholds: {
    http_req_duration: ['p(90)<3000', 'p(95)<5000'],
    http_req_failed: ['rate<0.05'],
    data_sync_failures: ['rate<0.02'],
    search_response_time: ['p(95)<2000'],
    websocket_connect_duration: ['p(95)<1000'],
  },
};

const DATA_BRIDGE_URL = __ENV.DATA_BRIDGE_URL || 'http://localhost:8202';
const WSS_URL = __ENV.WSS_URL || 'ws://localhost:8202';

export function setup() {
  console.log('Setting up Data Bridge load test...');
  
  // Create test index for search operations
  const indexConfig = {
    indexName: 'load-test-index',
    mapping: {
      properties: {
        title: { type: 'text' },
        content: { type: 'text' },
        category: { type: 'keyword' },
        tags: { type: 'keyword' },
        timestamp: { type: 'date' }
      }
    }
  };
  
  const createIndexResponse = http.post(
    `${DATA_BRIDGE_URL}/api/search/indices`,
    JSON.stringify(indexConfig),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  if (createIndexResponse.status !== 200) {
    console.warn(`Failed to create test index: ${createIndexResponse.status}`);
  }
  
  // Pre-populate some test data
  for (let i = 0; i < 100; i++) {
    const document = {
      document: {
        id: `load-test-doc-${i}`,
        title: `Load Test Document ${i}`,
        content: `This is test content for load testing document number ${i}. It contains various keywords for search testing.`,
        category: i % 3 === 0 ? 'report' : i % 3 === 1 ? 'note' : 'task',
        tags: [`tag-${i % 5}`, 'load-test', 'performance'],
        timestamp: new Date().toISOString(),
        priority: i % 3 === 0 ? 'high' : i % 3 === 1 ? 'medium' : 'low'
      }
    };
    
    http.post(
      `${DATA_BRIDGE_URL}/api/search/indices/load-test-index/documents`,
      JSON.stringify(document),
      { headers: { 'Content-Type': 'application/json' } }
    );
  }
  
  console.log('Setup completed');
  return { 
    dataBridgeUrl: DATA_BRIDGE_URL,
    wssUrl: WSS_URL,
    testIndexName: 'load-test-index'
  };
}

export default function (data) {
  const scenario = __ITER % 5;
  
  switch (scenario) {
    case 0:
      testDataSync();
      break;
    case 1:
      testSchemaValidation();
      break;
    case 2:
      testSearchOperations(data.testIndexName);
      break;
    case 3:
      testDataTransformation();
      break;
    case 4:
      testEventSourcing();
      break;
    default:
      testMixedOperations(data.testIndexName);
  }
  
  sleep(Math.random() * 2 + 1); // Random sleep between 1-3 seconds
}

function testDataSync() {
  // Register a test service
  const serviceConfig = {
    serviceName: `load-test-service-${__VU}-${__ITER}`,
    config: {
      endpoint: 'http://localhost:3001/api',
      syncEnabled: true,
      syncStrategy: 'bidirectional',
      entityTypes: ['document']
    }
  };
  
  const registerResponse = http.post(
    `${DATA_BRIDGE_URL}/api/sync/services`,
    JSON.stringify(serviceConfig),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'register_service' }
    }
  );
  
  const registerSuccess = check(registerResponse, {
    'service registration status is 200': (r) => r.status === 200,
    'service registration returns name': (r) => r.json('name') !== undefined,
  });
  
  if (!registerSuccess) {
    dataSyncFailureRate.add(1);
    return;
  }
  
  // Perform sync operation
  const syncRequest = {
    entityType: 'document',
    entityId: `test-entity-${__VU}-${__ITER}`,
    sourceService: serviceConfig.serviceName
  };
  
  const syncResponse = http.post(
    `${DATA_BRIDGE_URL}/api/sync/sync`,
    JSON.stringify(syncRequest),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'sync_entity' }
    }
  );
  
  const syncSuccess = check(syncResponse, {
    'sync operation status is 200': (r) => r.status === 200,
    'sync operation returns id': (r) => r.json('id') !== undefined,
  });
  
  dataSyncFailureRate.add(syncSuccess ? 0 : 1);
}

function testSchemaValidation() {
  const testEntity = {
    entityType: 'document',
    data: {
      id: `${Date.now()}-${__VU}-${__ITER}`,
      type: 'document',
      title: `Load Test Document ${__VU}-${__ITER}`,
      content: 'This is test content for schema validation testing.',
      category: 'test',
      tags: ['load-test', 'schema'],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      createdBy: `user-${__VU}`
    }
  };
  
  const response = http.post(
    `${DATA_BRIDGE_URL}/api/schema/validate`,
    JSON.stringify(testEntity),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'schema_validation' }
    }
  );
  
  check(response, {
    'schema validation status is 200': (r) => r.status === 200,
    'schema validation result is valid': (r) => r.json('valid') === true,
    'schema validation returns data': (r) => r.json('data') !== undefined,
  });
}

function testSearchOperations(indexName) {
  const searchQueries = [
    'load test document',
    'performance testing',
    'content search',
    'tag-1 OR tag-2',
    'priority:high',
    'category:report',
    'document AND test',
    'Load Test Document 1*'
  ];
  
  const query = searchQueries[__ITER % searchQueries.length];
  const startTime = Date.now();
  
  const searchRequest = {
    query: query,
    options: {
      index: indexName,
      size: 20,
      filters: {
        tags: ['load-test']
      }
    }
  };
  
  const response = http.post(
    `${DATA_BRIDGE_URL}/api/search/search`,
    JSON.stringify(searchRequest),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'search' }
    }
  );
  
  const duration = Date.now() - startTime;
  searchResponseTime.add(duration);
  
  check(response, {
    'search status is 200': (r) => r.status === 200,
    'search returns hits': (r) => Array.isArray(r.json('hits')),
    'search response time < 2000ms': () => duration < 2000,
    'search returns total count': (r) => r.json('total') !== undefined,
  });
}

function testDataTransformation() {
  const transformRequest = {
    data: {
      user_name: `Test User ${__VU}`,
      user_email: `testuser${__VU}@example.com`,
      creation_date: new Date().toISOString(),
      priority_level: Math.floor(Math.random() * 5) + 1,
      tags_list: ['test', 'transformation', `vu-${__VU}`]
    },
    sourceFormat: 'json',
    targetFormat: 'json',
    options: {
      fieldMappings: {
        'user_name': 'name',
        'user_email': 'email',
        'creation_date': 'createdAt',
        'priority_level': 'priority',
        'tags_list': 'tags'
      },
      valueTransformations: {
        'priority': {
          type: 'lookup',
          table: { 1: 'low', 2: 'low', 3: 'medium', 4: 'high', 5: 'critical' }
        }
      }
    }
  };
  
  const response = http.post(
    `${DATA_BRIDGE_URL}/api/transform/transform`,
    JSON.stringify(transformRequest),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'data_transformation' }
    }
  );
  
  check(response, {
    'transformation status is 200': (r) => r.status === 200,
    'transformation success': (r) => r.json('success') === true,
    'transformation returns data': (r) => r.json('data') !== undefined,
    'transformation maps fields correctly': (r) => r.json('data.name') !== undefined,
  });
}

function testEventSourcing() {
  const streamId = `load-test-stream-${__VU}`;
  
  const events = [
    {
      eventType: 'EntityCreated',
      data: {
        id: `entity-${__VU}-${__ITER}`,
        name: `Load Test Entity ${__VU}-${__ITER}`,
        type: 'test-entity'
      }
    },
    {
      eventType: 'EntityUpdated',
      data: {
        id: `entity-${__VU}-${__ITER}`,
        name: `Updated Load Test Entity ${__VU}-${__ITER}`
      }
    }
  ];
  
  const response = http.post(
    `${DATA_BRIDGE_URL}/api/events/streams/${streamId}/events`,
    JSON.stringify({ events: events }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'append_events' }
    }
  );
  
  check(response, {
    'event sourcing status is 200': (r) => r.status === 200,
    'event sourcing returns event IDs': (r) => Array.isArray(r.json('eventIds')),
    'event sourcing returns version': (r) => r.json('version') !== undefined,
  });
  
  // Retrieve events
  const getEventsResponse = http.get(
    `${DATA_BRIDGE_URL}/api/events/streams/${streamId}/events`,
    {
      headers: { 'Accept': 'application/json' },
      tags: { operation: 'get_events' }
    }
  );
  
  check(getEventsResponse, {
    'get events status is 200': (r) => r.status === 200,
    'get events returns events array': (r) => Array.isArray(r.json('events')),
  });
}

function testMixedOperations(indexName) {
  // Randomly choose an operation
  const operations = [
    () => testDataSync(),
    () => testSchemaValidation(),
    () => testSearchOperations(indexName),
    () => testDataTransformation(),
    () => testEventSourcing()
  ];
  
  const randomOperation = operations[Math.floor(Math.random() * operations.length)];
  randomOperation();
}

// WebSocket load testing function
export function websocketTest() {
  const wsUrl = `${WSS_URL}`;
  
  const response = ws.connect(wsUrl, null, function (socket) {
    activeConnections.add(1);
    
    socket.on('open', function open() {
      console.log(`VU ${__VU}: WebSocket connection opened`);
      
      // Subscribe to updates
      socket.send(JSON.stringify({
        type: 'subscribe',
        topics: ['sync', 'events', 'search']
      }));
    });
    
    socket.on('message', function message(data) {
      const msg = JSON.parse(data);
      check(msg, {
        'WebSocket message has type': (m) => m.type !== undefined,
        'WebSocket message has timestamp': (m) => m.timestamp !== undefined,
      });
    });
    
    socket.on('close', function close() {
      console.log(`VU ${__VU}: WebSocket connection closed`);
      activeConnections.add(-1);
    });
    
    socket.on('error', function error(e) {
      console.log(`VU ${__VU}: WebSocket error:`, e.error());
    });
    
    // Send ping every 30 seconds
    socket.setInterval(function timeout() {
      socket.ping();
    }, 30000);
    
    // Keep connection alive for test duration
    socket.setTimeout(function timeout() {
      socket.close();
    }, Math.random() * 60000 + 30000); // 30-90 seconds
  });
  
  check(response, {
    'WebSocket connection successful': (r) => r && r.status === 101,
  });
}

// Bulk operations test
export function bulkOperationsTest() {
  const documents = [];
  
  // Create multiple documents for bulk indexing
  for (let i = 0; i < 10; i++) {
    documents.push({
      id: `bulk-doc-${__VU}-${__ITER}-${i}`,
      title: `Bulk Document ${i}`,
      content: `Bulk test content for document ${i} created by VU ${__VU}`,
      category: 'bulk-test',
      tags: ['bulk', 'load-test', `vu-${__VU}`],
      timestamp: new Date().toISOString()
    });
  }
  
  // Bulk index documents
  const bulkIndexResponse = http.post(
    `${DATA_BRIDGE_URL}/api/search/indices/load-test-index/bulk`,
    JSON.stringify({ documents: documents }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'bulk_index' }
    }
  );
  
  const bulkSuccess = check(bulkIndexResponse, {
    'bulk index status is 200': (r) => r.status === 200,
    'bulk index processes all documents': (r) => r.json('successful') === documents.length,
  });
  
  if (bulkSuccess) {
    indexingRate.add(documents.length);
  }
  
  // Test bulk search
  const bulkSearchQueries = documents.map(doc => ({
    query: doc.title,
    options: { index: 'load-test-index', size: 5 }
  }));
  
  const bulkSearchResponse = http.post(
    `${DATA_BRIDGE_URL}/api/search/bulk-search`,
    JSON.stringify({ searches: bulkSearchQueries }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'bulk_search' }
    }
  );
  
  check(bulkSearchResponse, {
    'bulk search status is 200': (r) => r.status === 200,
    'bulk search returns results': (r) => Array.isArray(r.json('results')),
  });
}

export function handleSummary(data) {
  return {
    'reports/load-databridge-summary.json': JSON.stringify(data, null, 2),
    'reports/load-databridge-summary.html': generateDataBridgeHTMLReport(data),
    stdout: generateDataBridgeTextSummary(data),
  };
}

function generateDataBridgeHTMLReport(data) {
  const metrics = data.metrics;
  
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Data Bridge Load Test Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .metric { margin: 10px 0; padding: 10px; border-left: 4px solid #007acc; background: #f5f5f5; }
            .success { border-left-color: #28a745; }
            .warning { border-left-color: #ffc107; }
            .error { border-left-color: #dc3545; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .chart { width: 100%; height: 300px; margin: 20px 0; background: #f8f9fa; }
        </style>
    </head>
    <body>
        <h1>Data Bridge Load Test Report</h1>
        <p>Generated: ${new Date().toISOString()}</p>
        
        <h2>Overall Performance</h2>
        <div class="metric">
            <strong>Total Requests:</strong> ${metrics.http_reqs?.values?.count || 0}
        </div>
        <div class="metric">
            <strong>Request Rate:</strong> ${(metrics.http_reqs?.values?.rate || 0).toFixed(2)} req/s
        </div>
        <div class="metric ${getStatusClass(metrics.http_req_failed?.values?.rate || 0)}">
            <strong>Failure Rate:</strong> ${((metrics.http_req_failed?.values?.rate || 0) * 100).toFixed(2)}%
        </div>
        
        <h2>Data Bridge Specific Metrics</h2>
        <div class="metric ${getStatusClass(metrics.data_sync_failures?.values?.rate || 0)}">
            <strong>Data Sync Failure Rate:</strong> ${((metrics.data_sync_failures?.values?.rate || 0) * 100).toFixed(2)}%
        </div>
        <div class="metric">
            <strong>Average Search Response Time:</strong> ${(metrics.search_response_time?.values?.avg || 0).toFixed(2)}ms
        </div>
        <div class="metric">
            <strong>Documents Indexed:</strong> ${metrics.documents_indexed?.values?.count || 0}
        </div>
        <div class="metric">
            <strong>Peak WebSocket Connections:</strong> ${metrics.websocket_connections?.values?.max || 0}
        </div>
        
        <h2>Response Time Analysis</h2>
        <table>
            <tr><th>Operation</th><th>Avg (ms)</th><th>P90 (ms)</th><th>P95 (ms)</th><th>Status</th></tr>
            <tr>
                <td>Overall</td>
                <td>${(metrics.http_req_duration?.values?.avg || 0).toFixed(2)}</td>
                <td>${(metrics.http_req_duration?.values?.['p(90)'] || 0).toFixed(2)}</td>
                <td>${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}</td>
                <td>${getPerformanceStatus(metrics.http_req_duration?.values?.['p(95)'] || 0, 5000)}</td>
            </tr>
            <tr>
                <td>Search</td>
                <td>${(metrics.search_response_time?.values?.avg || 0).toFixed(2)}</td>
                <td>${(metrics.search_response_time?.values?.['p(90)'] || 0).toFixed(2)}</td>
                <td>${(metrics.search_response_time?.values?.['p(95)'] || 0).toFixed(2)}</td>
                <td>${getPerformanceStatus(metrics.search_response_time?.values?.['p(95)'] || 0, 2000)}</td>
            </tr>
        </table>
        
        <h2>Performance Recommendations</h2>
        ${generateDataBridgeRecommendations(metrics)}
    </body>
    </html>
  `;
}

function generateDataBridgeTextSummary(data) {
  const metrics = data.metrics;
  
  return `
==========================================
Data Bridge Load Test Summary
==========================================

Test Duration: ${(data.state.testRunDurationMs / 1000 / 60).toFixed(2)} minutes

HTTP Metrics:
- Total Requests: ${metrics.http_reqs?.values?.count || 0}
- Request Rate: ${(metrics.http_reqs?.values?.rate || 0).toFixed(2)} req/s
- Failure Rate: ${((metrics.http_req_failed?.values?.rate || 0) * 100).toFixed(2)}%
- Avg Response Time: ${(metrics.http_req_duration?.values?.avg || 0).toFixed(2)}ms

Data Bridge Metrics:
- Data Sync Failure Rate: ${((metrics.data_sync_failures?.values?.rate || 0) * 100).toFixed(2)}%
- Avg Search Response Time: ${(metrics.search_response_time?.values?.avg || 0).toFixed(2)}ms
- Documents Indexed: ${metrics.documents_indexed?.values?.count || 0}
- Peak WebSocket Connections: ${metrics.websocket_connections?.values?.max || 0}

Status: ${getDataBridgeOverallStatus(metrics)}
==========================================
  `;
}

function getDataBridgeOverallStatus(metrics) {
  const httpFailureRate = metrics.http_req_failed?.values?.rate || 0;
  const syncFailureRate = metrics.data_sync_failures?.values?.rate || 0;
  const searchResponseTime = metrics.search_response_time?.values?.['p(95)'] || 0;
  
  if (httpFailureRate > 0.05 || syncFailureRate > 0.02 || searchResponseTime > 2000) {
    return '❌ FAILED - Performance thresholds exceeded';
  } else if (httpFailureRate > 0.02 || syncFailureRate > 0.01 || searchResponseTime > 1500) {
    return '⚠️ WARNING - Some metrics approaching thresholds';
  } else {
    return '✅ PASSED - All metrics within acceptable limits';
  }
}

function generateDataBridgeRecommendations(metrics) {
  const recommendations = [];
  const syncFailureRate = metrics.data_sync_failures?.values?.rate || 0;
  const searchResponseTime = metrics.search_response_time?.values?.['p(95)'] || 0;
  const indexingRate = metrics.documents_indexed?.values?.rate || 0;
  
  if (syncFailureRate > 0.02) {
    recommendations.push('⚠️ High data sync failure rate. Check service connectivity and sync rule configurations.');
  }
  
  if (searchResponseTime > 2000) {
    recommendations.push('⚠️ Slow search response times. Consider optimizing Elasticsearch indices and queries.');
  }
  
  if (indexingRate < 10) {
    recommendations.push('⚠️ Low document indexing rate. Check Elasticsearch performance and bulk operations.');
  }
  
  if (recommendations.length === 0) {
    recommendations.push('✅ Data Bridge performance is excellent! All operations are performing within optimal thresholds.');
  }
  
  return '<ul><li>' + recommendations.join('</li><li>') + '</li></ul>';
}

function getStatusClass(rate) {
  if (rate < 0.01) return 'success';
  if (rate < 0.05) return 'warning';
  return 'error';
}

function getPerformanceStatus(value, threshold) {
  return value < threshold ? '✅ Good' : '❌ Needs Improvement';
}