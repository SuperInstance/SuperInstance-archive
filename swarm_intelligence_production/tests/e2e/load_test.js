/*
 * K6 Load Test for Swarm Intelligence Platform
 * Tests API under various load conditions
 *
 * Usage:
 *   k6 run --vus 100 --duration 5m load_test.js
 *   k6 run --vus 1000 --duration 10m --env BASE_URL=https://staging-api.example.com load_test.js
 */

import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const swarmCreationTime = new Trend('swarm_creation_time');
const agentDeployTime = new Trend('agent_deploy_time');
const apiLatency = new Trend('api_latency');
const wsConnectionTime = new Trend('ws_connection_time');
const successfulSwarms = new Counter('successful_swarms');
const failedSwarms = new Counter('failed_swarms');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'https://staging-api.swarm-intelligence.example.com';
const WS_URL = BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://');

// Test configuration
export const options = {
    stages: [
        { duration: '2m', target: 100 },   // Ramp up to 100 users
        { duration: '5m', target: 100 },   // Stay at 100 users
        { duration: '2m', target: 500 },   // Ramp up to 500 users
        { duration: '5m', target: 500 },   // Stay at 500 users
        { duration: '2m', target: 1000 },  // Ramp up to 1000 users
        { duration: '5m', target: 1000 },  // Stay at 1000 users
        { duration: '5m', target: 0 },     // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<200', 'p(99)<500'],  // 95% under 200ms, 99% under 500ms
        http_req_failed: ['rate<0.01'],                  // Error rate < 1%
        errors: ['rate<0.01'],
        swarm_creation_time: ['p(95)<1000'],             // Swarm creation under 1s
    },
};

// Generate random swarm name
function randomSwarmName() {
    return `load-test-swarm-${Math.random().toString(36).substring(7)}`;
}

// Main test scenario
export default function() {
    // Test 1: Health check
    group('Health Check', function() {
        const start = Date.now();
        const res = http.get(`${BASE_URL}/health`);
        const duration = Date.now() - start;

        check(res, {
            'health check status is 200': (r) => r.status === 200,
            'health check has correct body': (r) => r.json('status') === 'healthy',
        }) || errorRate.add(1);

        apiLatency.add(duration);
    });

    sleep(1);

    // Test 2: Create swarm
    let swarmId;
    group('Create Swarm', function() {
        const payload = JSON.stringify({
            name: randomSwarmName(),
            agent_count: 1000,
            behavior: 'foraging',
            config: {
                target_fps: 60,
                bounds: {
                    min: { x: -1000, y: -1000, z: -100 },
                    max: { x: 1000, y: 1000, z: 100 }
                }
            }
        });

        const params = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const start = Date.now();
        const res = http.post(`${BASE_URL}/api/swarms`, payload, params);
        const duration = Date.now() - start;

        const success = check(res, {
            'swarm created successfully': (r) => r.status === 201 || r.status === 200,
            'swarm has ID': (r) => r.json('swarm_id') !== undefined,
        });

        if (success) {
            swarmId = res.json('swarm_id');
            swarmCreationTime.add(duration);
            successfulSwarms.add(1);
        } else {
            errorRate.add(1);
            failedSwarms.add(1);
        }
    });

    sleep(2);

    // Test 3: Get swarm details
    if (swarmId) {
        group('Get Swarm Details', function() {
            const start = Date.now();
            const res = http.get(`${BASE_URL}/api/swarms/${swarmId}`);
            const duration = Date.now() - start;

            check(res, {
                'get swarm status is 200': (r) => r.status === 200,
                'swarm has agent count': (r) => r.json('agent_count') !== undefined,
            }) || errorRate.add(1);

            apiLatency.add(duration);
        });

        sleep(1);

        // Test 4: Get swarm metrics
        group('Get Swarm Metrics', function() {
            const start = Date.now();
            const res = http.get(`${BASE_URL}/api/swarms/${swarmId}/metrics`);
            const duration = Date.now() - start;

            check(res, {
                'metrics status is 200': (r) => r.status === 200,
                'metrics has FPS': (r) => r.json('fps') !== undefined,
                'FPS is reasonable': (r) => {
                    const fps = r.json('fps');
                    return fps > 0 && fps <= 120;
                },
            }) || errorRate.add(1);

            apiLatency.add(duration);
        });

        sleep(1);

        // Test 5: Submit task
        group('Submit Task', function() {
            const payload = JSON.stringify({
                swarm_id: swarmId,
                type: 'resource_optimization',
                description: 'Load test task',
                parameters: {
                    resource_count: 50,
                    optimization_target: 'speed'
                }
            });

            const params = {
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            const start = Date.now();
            const res = http.post(`${BASE_URL}/api/tasks`, payload, params);
            const duration = Date.now() - start;

            check(res, {
                'task submitted successfully': (r) => r.status === 201 || r.status === 200,
                'task has ID': (r) => r.json('task_id') !== undefined,
            }) || errorRate.add(1);

            apiLatency.add(duration);
        });

        sleep(2);

        // Test 6: List swarms
        group('List Swarms', function() {
            const start = Date.now();
            const res = http.get(`${BASE_URL}/api/swarms?limit=10`);
            const duration = Date.now() - start;

            check(res, {
                'list swarms status is 200': (r) => r.status === 200,
                'response is array': (r) => Array.isArray(r.json()),
            }) || errorRate.add(1);

            apiLatency.add(duration);
        });

        sleep(1);

        // Test 7: Update swarm (scale)
        group('Scale Swarm', function() {
            const payload = JSON.stringify({
                agent_count: 1500
            });

            const params = {
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            const start = Date.now();
            const res = http.patch(`${BASE_URL}/api/swarms/${swarmId}`, payload, params);
            const duration = Date.now() - start;

            check(res, {
                'scale request accepted': (r) => r.status === 200 || r.status === 202,
            }) || errorRate.add(1);

            apiLatency.add(duration);
        });

        sleep(2);

        // Test 8: Delete swarm (cleanup)
        group('Delete Swarm', function() {
            const start = Date.now();
            const res = http.del(`${BASE_URL}/api/swarms/${swarmId}`);
            const duration = Date.now() - start;

            check(res, {
                'delete successful': (r) => r.status === 204 || r.status === 200,
            }) || errorRate.add(1);

            apiLatency.add(duration);
        });
    }

    sleep(3);
}

// WebSocket connection test (separate VU)
export function websocketTest() {
    group('WebSocket Connection', function() {
        const start = Date.now();

        const res = ws.connect(`${WS_URL}/ws`, function(socket) {
            socket.on('open', function() {
                const duration = Date.now() - start;
                wsConnectionTime.add(duration);

                // Send subscription message
                socket.send(JSON.stringify({
                    type: 'subscribe',
                    channel: 'metrics'
                }));

                // Listen for messages for 30 seconds
                socket.setTimeout(function() {
                    socket.close();
                }, 30000);
            });

            socket.on('message', function(data) {
                check(data, {
                    'message is valid JSON': (d) => {
                        try {
                            JSON.parse(d);
                            return true;
                        } catch (e) {
                            return false;
                        }
                    },
                });
            });

            socket.on('error', function(e) {
                errorRate.add(1);
            });
        });

        check(res, {
            'ws connection successful': (r) => r && r.status === 101,
        }) || errorRate.add(1);
    });
}

// Setup function - runs once per VU
export function setup() {
    console.log(`Load test starting against ${BASE_URL}`);

    // Verify API is accessible
    const res = http.get(`${BASE_URL}/health`);
    if (res.status !== 200) {
        throw new Error(`API is not accessible: ${res.status}`);
    }

    console.log('API is healthy, starting load test...');
    return { startTime: new Date().toISOString() };
}

// Teardown function - runs once at the end
export function teardown(data) {
    console.log(`Load test completed. Started at: ${data.startTime}`);
}

// Handle summary - custom report
export function handleSummary(data) {
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'summary.json': JSON.stringify(data),
        'summary.html': htmlReport(data),
    };
}

function textSummary(data, options) {
    let summary = '\n=== Load Test Summary ===\n\n';

    const metrics = data.metrics;

    summary += `Total Requests: ${metrics.http_reqs ? metrics.http_reqs.values.count : 0}\n`;
    summary += `Failed Requests: ${metrics.http_req_failed ? (metrics.http_req_failed.values.rate * 100).toFixed(2) : 0}%\n`;
    summary += `Successful Swarms: ${metrics.successful_swarms ? metrics.successful_swarms.values.count : 0}\n`;
    summary += `Failed Swarms: ${metrics.failed_swarms ? metrics.failed_swarms.values.count : 0}\n`;

    if (metrics.http_req_duration) {
        summary += `\nLatency:\n`;
        summary += `  p50: ${metrics.http_req_duration.values['p(50)'].toFixed(2)}ms\n`;
        summary += `  p95: ${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
        summary += `  p99: ${metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n`;
    }

    if (metrics.swarm_creation_time) {
        summary += `\nSwarm Creation Time:\n`;
        summary += `  avg: ${metrics.swarm_creation_time.values.avg.toFixed(2)}ms\n`;
        summary += `  p95: ${metrics.swarm_creation_time.values['p(95)'].toFixed(2)}ms\n`;
    }

    return summary;
}

function htmlReport(data) {
    return `
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .pass { color: green; }
        .fail { color: red; }
    </style>
</head>
<body>
    <h1>Load Test Report</h1>
    <p>Generated: ${new Date().toISOString()}</p>
    <pre>${JSON.stringify(data, null, 2)}</pre>
</body>
</html>
    `;
}
