/**
 * K6 Load Testing Scenarios
 * Tests system under various load conditions
 *
 * Run with:
 *   k6 run load_test_scenarios.js
 *   k6 run --vus 100 --duration 5m load_test_scenarios.js
 */

import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');
const wsConnectionTime = new Trend('ws_connection_time');
const taskCompletionRate = new Rate('task_completion');
const swarmCreationCounter = new Counter('swarms_created');

// Configuration
const BASE_URL = __ENV.API_URL || 'http://localhost:8000';
const WS_URL = __ENV.WS_URL || 'ws://localhost:8000';

// Test scenarios
export const options = {
  scenarios: {
    // Scenario 1: 100 concurrent swarms
    concurrent_swarms: {
      executor: 'constant-vus',
      vus: 100,
      duration: '5m',
      tags: { scenario: 'concurrent_swarms' },
    },

    // Scenario 2: 1000 API requests/second
    high_throughput_api: {
      executor: 'constant-arrival-rate',
      rate: 1000,
      timeUnit: '1s',
      duration: '3m',
      preAllocatedVUs: 50,
      maxVUs: 200,
      tags: { scenario: 'high_throughput' },
    },

    // Scenario 3: Ramping load test
    ramping_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },
        { duration: '5m', target: 100 },
        { duration: '5m', target: 200 },
        { duration: '2m', target: 300 },
        { duration: '5m', target: 300 },
        { duration: '2m', target: 0 },
      ],
      tags: { scenario: 'ramping' },
    },

    // Scenario 4: Spike test
    spike_test: {
      executor: 'ramping-arrival-rate',
      startRate: 50,
      timeUnit: '1s',
      stages: [
        { duration: '2m', target: 100 },
        { duration: '1m', target: 1000 },  // Spike
        { duration: '3m', target: 100 },
        { duration: '1m', target: 2000 },  // Larger spike
        { duration: '2m', target: 100 },
      ],
      preAllocatedVUs: 100,
      maxVUs: 500,
      tags: { scenario: 'spike' },
    },

    // Scenario 5: WebSocket stress test
    websocket_stress: {
      executor: 'constant-vus',
      vus: 100,
      duration: '5m',
      exec: 'websocketTest',
      tags: { scenario: 'websocket' },
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],  // 95% under 500ms, 99% under 1s
    http_req_failed: ['rate<0.05'],  // Error rate < 5%
    errors: ['rate<0.1'],  // Custom error rate < 10%
    ws_connection_time: ['p(95)<2000'],  // WebSocket connection < 2s
    task_completion: ['rate>0.8'],  // 80% task completion rate
  },
};

// Setup: Authenticate and get API key
export function setup() {
  const authPayload = JSON.stringify({
    username: 'test@example.com',
    password: 'testpass',
  });

  const authRes = http.post(
    `${BASE_URL}/api/v1/auth/token`,
    authPayload,
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );

  if (authRes.status === 200) {
    return {
      apiKey: authRes.json('access_token'),
    };
  }

  return { apiKey: 'test-key' };
}

// Default test function
export default function (data) {
  const apiKey = data.apiKey;
  const headers = {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  };

  group('API Operations', () => {
    // Test 1: Health check
    group('Health Check', () => {
      const start = new Date();
      const res = http.get(`${BASE_URL}/health`);

      check(res, {
        'health status is 200': (r) => r.status === 200,
        'health response has status field': (r) => r.json('status') !== undefined,
      });

      apiLatency.add(new Date() - start);
      errorRate.add(res.status !== 200);
    });

    // Test 2: Create swarm
    let swarmId;
    group('Create Swarm', () => {
      const payload = JSON.stringify({
        name: `load-test-swarm-${__VU}-${__ITER}`,
        agent_count: Math.floor(Math.random() * 1000) + 100,
        agent_type: 'WORKER',
      });

      const start = new Date();
      const res = http.post(`${BASE_URL}/api/v1/swarms`, payload, { headers });

      const success = check(res, {
        'swarm created (status 200)': (r) => r.status === 200,
        'swarm has ID': (r) => r.json('swarm_id') !== undefined,
      });

      apiLatency.add(new Date() - start);
      errorRate.add(!success);

      if (success) {
        swarmId = res.json('swarm_id');
        swarmCreationCounter.add(1);
      }
    });

    sleep(1);

    // Test 3: Get swarm details
    if (swarmId) {
      group('Get Swarm', () => {
        const start = new Date();
        const res = http.get(`${BASE_URL}/api/v1/swarms/${swarmId}`, { headers });

        check(res, {
          'get swarm status 200': (r) => r.status === 200,
          'swarm data returned': (r) => r.json('swarm_id') === swarmId,
        });

        apiLatency.add(new Date() - start);
        errorRate.add(res.status !== 200);
      });

      // Test 4: Submit task
      group('Submit Task', () => {
        const taskPayload = JSON.stringify({
          type: 'compute',
          payload: { operation: 'test', data: Math.random() },
          priority: 'NORMAL',
        });

        const start = new Date();
        const res = http.post(
          `${BASE_URL}/api/v1/swarms/${swarmId}/tasks`,
          taskPayload,
          { headers }
        );

        const success = check(res, {
          'task submitted (status 200)': (r) => r.status === 200,
          'task has ID': (r) => r.json('task_id') !== undefined,
        });

        apiLatency.add(new Date() - start);
        errorRate.add(!success);
        taskCompletionRate.add(success);
      });

      sleep(0.5);

      // Test 5: Get metrics
      group('Get Metrics', () => {
        const start = new Date();
        const res = http.get(
          `${BASE_URL}/api/v1/swarms/${swarmId}/metrics?window=LAST_HOUR`,
          { headers }
        );

        check(res, {
          'metrics status 200': (r) => r.status === 200,
          'metrics data returned': (r) => r.json('metrics') !== undefined,
        });

        apiLatency.add(new Date() - start);
        errorRate.add(res.status !== 200);
      });

      // Test 6: Delete swarm (cleanup)
      group('Delete Swarm', () => {
        const res = http.del(`${BASE_URL}/api/v1/swarms/${swarmId}`, null, { headers });

        check(res, {
          'swarm deleted (status 200)': (r) => r.status === 200,
        });

        errorRate.add(res.status !== 200);
      });
    }
  });

  sleep(Math.random() * 2 + 1);  // Random sleep 1-3 seconds
}

// WebSocket test function
export function websocketTest(data) {
  const apiKey = data.apiKey;

  // Create swarm first
  const swarmPayload = JSON.stringify({
    name: `ws-test-swarm-${__VU}`,
    agent_count: 50,
  });

  const headers = {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  };

  const swarmRes = http.post(`${BASE_URL}/api/v1/swarms`, swarmPayload, { headers });

  if (swarmRes.status !== 200) {
    errorRate.add(1);
    return;
  }

  const swarmId = swarmRes.json('swarm_id');

  // Test WebSocket connection
  const url = `${WS_URL}/ws/${swarmId}`;
  const start = new Date();

  const response = ws.connect(url, {}, (socket) => {
    socket.on('open', () => {
      wsConnectionTime.add(new Date() - start);

      // Authenticate
      socket.send(JSON.stringify({
        type: 'auth',
        api_key: apiKey,
      }));

      // Subscribe to events
      socket.send(JSON.stringify({
        type: 'subscribe',
        events: ['task_progress', 'agent_status'],
      }));

      // Send periodic pings
      socket.setInterval(() => {
        socket.send(JSON.stringify({ type: 'ping' }));
      }, 5000);

      socket.setTimeout(() => {
        socket.close();
      }, 30000);  // Close after 30 seconds
    });

    socket.on('message', (msg) => {
      try {
        const data = JSON.parse(msg);
        check(data, {
          'message has type': (d) => d.type !== undefined,
        });
      } catch (e) {
        errorRate.add(1);
      }
    });

    socket.on('error', (e) => {
      errorRate.add(1);
    });
  });

  check(response, {
    'websocket connected': (r) => r && r.status === 101,
  });

  // Cleanup
  http.del(`${BASE_URL}/api/v1/swarms/${swarmId}`, null, { headers });
}

// Batch processing test
export function batchProcessingTest(data) {
  const apiKey = data.apiKey;
  const headers = {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  };

  // Create swarm
  const swarmPayload = JSON.stringify({
    name: `batch-test-${__VU}`,
    agent_count: 500,
  });

  const swarmRes = http.post(`${BASE_URL}/api/v1/swarms`, swarmPayload, { headers });

  if (swarmRes.status !== 200) {
    errorRate.add(1);
    return;
  }

  const swarmId = swarmRes.json('swarm_id');

  sleep(2);  // Wait for swarm initialization

  // Submit batch of tasks
  const tasks = [];
  for (let i = 0; i < 50; i++) {
    tasks.push({
      type: 'render',
      payload: { scene: i, quality: 'high' },
    });
  }

  const batchPayload = JSON.stringify({ tasks });

  const start = new Date();
  const batchRes = http.post(
    `${BASE_URL}/api/v1/creative/batch?swarm_id=${swarmId}`,
    batchPayload,
    { headers }
  );

  const success = check(batchRes, {
    'batch submitted (status 200)': (r) => r.status === 200,
    'batch has ID': (r) => r.json('batch_id') !== undefined,
    'task count correct': (r) => r.json('task_count') === 50,
  });

  apiLatency.add(new Date() - start);
  errorRate.add(!success);

  // Cleanup
  http.del(`${BASE_URL}/api/v1/swarms/${swarmId}`, null, { headers });
}

// Teardown
export function teardown(data) {
  console.log('Load test completed');
}
