import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const authFailureRate = new Rate('auth_failures');
const loginDuration = new Trend('login_duration');
const registrationCounter = new Counter('registrations_total');

// Test configuration
export const options = {
  scenarios: {
    // Ramp-up scenario for authentication load
    auth_ramp_up: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 20 },   // Ramp up to 20 users over 2 minutes
        { duration: '5m', target: 20 },   // Stay at 20 users for 5 minutes
        { duration: '2m', target: 50 },   // Ramp up to 50 users over 2 minutes
        { duration: '5m', target: 50 },   // Stay at 50 users for 5 minutes
        { duration: '2m', target: 0 },    // Ramp down to 0 users
      ],
    },
    
    // Spike test for sudden authentication bursts
    auth_spike: {
      executor: 'ramping-vus',
      startTime: '16m',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 100 }, // Quick ramp up to 100 users
        { duration: '1m', target: 100 },  // Stay at 100 users for 1 minute
        { duration: '10s', target: 0 },   // Quick ramp down
      ],
    },
    
    // Constant load for sustained authentication
    auth_constant: {
      executor: 'constant-vus',
      vus: 10,
      duration: '20m',
      startTime: '20m',
    },
  },
  
  thresholds: {
    http_req_duration: ['p(90)<2000', 'p(95)<3000'], // 90% of requests under 2s, 95% under 3s
    http_req_failed: ['rate<0.1'], // Error rate should be less than 10%
    auth_failures: ['rate<0.05'],  // Auth failure rate should be less than 5%
    login_duration: ['p(95)<1500'], // 95% of login attempts under 1.5s
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8201';

// Test data generators
function generateUserData() {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  
  return {
    email: `loadtest-${timestamp}-${random}@example.com`,
    password: `LoadTest123!${random}`,
    firstName: `Load${random}`,
    lastName: `Test${timestamp}`,
  };
}

function generateExistingUserCredentials() {
  // Simulate existing users with known credentials
  const users = [
    { email: 'existing1@example.com', password: 'ExistingPass123!' },
    { email: 'existing2@example.com', password: 'ExistingPass123!' },
    { email: 'existing3@example.com', password: 'ExistingPass123!' },
    { email: 'existing4@example.com', password: 'ExistingPass123!' },
    { email: 'existing5@example.com', password: 'ExistingPass123!' },
  ];
  
  return users[Math.floor(Math.random() * users.length)];
}

export function setup() {
  console.log('Setting up authentication load test...');
  
  // Create some existing users for login tests
  const existingUsers = [
    { email: 'existing1@example.com', password: 'ExistingPass123!', firstName: 'Existing1', lastName: 'User' },
    { email: 'existing2@example.com', password: 'ExistingPass123!', firstName: 'Existing2', lastName: 'User' },
    { email: 'existing3@example.com', password: 'ExistingPass123!', firstName: 'Existing3', lastName: 'User' },
    { email: 'existing4@example.com', password: 'ExistingPass123!', firstName: 'Existing4', lastName: 'User' },
    { email: 'existing5@example.com', password: 'ExistingPass123!', firstName: 'Existing5', lastName: 'User' },
  ];
  
  // Register existing users
  existingUsers.forEach(user => {
    const response = http.post(`${BASE_URL}/api/auth/register`, JSON.stringify(user), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (response.status !== 201 && response.status !== 409) {
      console.warn(`Failed to create existing user ${user.email}: ${response.status}`);
    }
  });
  
  console.log('Setup completed');
  return { baseUrl: BASE_URL };
}

export default function (data) {
  const scenario = __ENV.K6_SCENARIO || 'mixed';
  
  switch (scenario) {
    case 'login_only':
      performLogin();
      break;
    case 'register_only':
      performRegistration();
      break;
    case 'token_validation':
      performTokenValidation();
      break;
    case 'profile_access':
      performProfileAccess();
      break;
    default:
      performMixedAuthScenario();
  }
  
  sleep(1); // Wait 1 second between iterations
}

function performLogin() {
  const credentials = generateExistingUserCredentials();
  const startTime = Date.now();
  
  const response = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify(credentials),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'login' },
    }
  );
  
  const duration = Date.now() - startTime;
  loginDuration.add(duration);
  
  const success = check(response, {
    'login status is 200': (r) => r.status === 200,
    'login response has token': (r) => r.json('token') !== undefined,
    'login response has user': (r) => r.json('user') !== undefined,
    'login response time < 2s': () => duration < 2000,
  });
  
  if (!success) {
    authFailureRate.add(1);
    console.warn(`Login failed for ${credentials.email}: ${response.status} ${response.body}`);
  } else {
    authFailureRate.add(0);
  }
  
  return success ? response.json('token') : null;
}

function performRegistration() {
  const userData = generateUserData();
  
  const response = http.post(
    `${BASE_URL}/api/auth/register`,
    JSON.stringify(userData),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { operation: 'register' },
    }
  );
  
  const success = check(response, {
    'registration status is 201': (r) => r.status === 201,
    'registration response has token': (r) => r.json('token') !== undefined,
    'registration response has user': (r) => r.json('user') !== undefined,
    'registration email matches': (r) => r.json('user.email') === userData.email,
  });
  
  if (success) {
    registrationCounter.add(1);
  } else {
    console.warn(`Registration failed for ${userData.email}: ${response.status} ${response.body}`);
  }
  
  return success ? response.json('token') : null;
}

function performTokenValidation() {
  // First, get a token by logging in
  const token = performLogin();
  
  if (!token) {
    return;
  }
  
  // Then validate the token
  const response = http.get(`${BASE_URL}/api/auth/validate`, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/json',
    },
    tags: { operation: 'validate_token' },
  });
  
  check(response, {
    'token validation status is 200': (r) => r.status === 200,
    'token validation confirms valid': (r) => r.json('valid') === true,
    'token validation returns user': (r) => r.json('user') !== undefined,
  });
}

function performProfileAccess() {
  // First, get a token by logging in
  const token = performLogin();
  
  if (!token) {
    return;
  }
  
  // Then access user profile
  const response = http.get(`${BASE_URL}/api/users/profile`, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/json',
    },
    tags: { operation: 'get_profile' },
  });
  
  check(response, {
    'profile access status is 200': (r) => r.status === 200,
    'profile has user data': (r) => r.json('email') !== undefined,
    'profile has preferences': (r) => r.json('preferences') !== undefined,
  });
}

function performMixedAuthScenario() {
  const scenario = Math.random();
  
  if (scenario < 0.4) {
    // 40% login attempts
    performLogin();
  } else if (scenario < 0.6) {
    // 20% registration attempts
    performRegistration();
  } else if (scenario < 0.8) {
    // 20% token validation
    performTokenValidation();
  } else {
    // 20% profile access
    performProfileAccess();
  }
}

export function handleSummary(data) {
  return {
    'reports/load-auth-summary.json': JSON.stringify(data, null, 2),
    'reports/load-auth-summary.html': generateHTMLReport(data),
    stdout: generateTextSummary(data),
  };
}

function generateHTMLReport(data) {
  const scenarios = Object.keys(data.metrics.iterations.values || {});
  const metrics = data.metrics;
  
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentication Load Test Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .metric { margin: 10px 0; padding: 10px; border-left: 4px solid #007acc; background: #f5f5f5; }
            .scenario { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .success { border-left-color: #28a745; }
            .warning { border-left-color: #ffc107; }
            .error { border-left-color: #dc3545; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h1>Authentication Load Test Report</h1>
        <p>Generated: ${new Date().toISOString()}</p>
        
        <h2>Test Summary</h2>
        <div class="metric ${getStatusClass(metrics.http_req_failed?.values?.rate || 0)}">
            <strong>HTTP Request Failure Rate:</strong> ${((metrics.http_req_failed?.values?.rate || 0) * 100).toFixed(2)}%
        </div>
        
        <div class="metric">
            <strong>Total Requests:</strong> ${metrics.http_reqs?.values?.count || 0}
        </div>
        
        <div class="metric">
            <strong>Average Response Time:</strong> ${(metrics.http_req_duration?.values?.avg || 0).toFixed(2)}ms
        </div>
        
        <div class="metric">
            <strong>95th Percentile Response Time:</strong> ${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms
        </div>
        
        <h2>Authentication Metrics</h2>
        <div class="metric ${getStatusClass(metrics.auth_failures?.values?.rate || 0)}">
            <strong>Authentication Failure Rate:</strong> ${((metrics.auth_failures?.values?.rate || 0) * 100).toFixed(2)}%
        </div>
        
        <div class="metric">
            <strong>Average Login Duration:</strong> ${(metrics.login_duration?.values?.avg || 0).toFixed(2)}ms
        </div>
        
        <div class="metric">
            <strong>Total Registrations:</strong> ${metrics.registrations_total?.values?.count || 0}
        </div>
        
        <h2>Performance Breakdown by Percentile</h2>
        <table>
            <tr>
                <th>Percentile</th>
                <th>Response Time (ms)</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>50th (Median)</td>
                <td>${(metrics.http_req_duration?.values?.med || 0).toFixed(2)}</td>
                <td>${getPerformanceStatus(metrics.http_req_duration?.values?.med || 0, 1000)}</td>
            </tr>
            <tr>
                <td>90th</td>
                <td>${(metrics.http_req_duration?.values?.['p(90)'] || 0).toFixed(2)}</td>
                <td>${getPerformanceStatus(metrics.http_req_duration?.values?.['p(90)'] || 0, 2000)}</td>
            </tr>
            <tr>
                <td>95th</td>
                <td>${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}</td>
                <td>${getPerformanceStatus(metrics.http_req_duration?.values?.['p(95)'] || 0, 3000)}</td>
            </tr>
            <tr>
                <td>99th</td>
                <td>${(metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2)}</td>
                <td>${getPerformanceStatus(metrics.http_req_duration?.values?.['p(99)'] || 0, 5000)}</td>
            </tr>
        </table>
        
        <h2>Recommendations</h2>
        ${generateRecommendations(metrics)}
    </body>
    </html>
  `;
}

function getStatusClass(rate) {
  if (rate < 0.01) return 'success';
  if (rate < 0.05) return 'warning';
  return 'error';
}

function getPerformanceStatus(value, threshold) {
  return value < threshold ? '✅ Good' : '❌ Needs Improvement';
}

function generateRecommendations(metrics) {
  const recommendations = [];
  const failureRate = metrics.http_req_failed?.values?.rate || 0;
  const avgResponseTime = metrics.http_req_duration?.values?.avg || 0;
  const p95ResponseTime = metrics.http_req_duration?.values?.['p(95)'] || 0;
  
  if (failureRate > 0.05) {
    recommendations.push('⚠️ High failure rate detected. Check server capacity and error logs.');
  }
  
  if (avgResponseTime > 1000) {
    recommendations.push('⚠️ High average response time. Consider optimizing database queries and server performance.');
  }
  
  if (p95ResponseTime > 3000) {
    recommendations.push('⚠️ 95th percentile response time is high. This may indicate performance issues under load.');
  }
  
  if (recommendations.length === 0) {
    recommendations.push('✅ Performance looks good! All metrics are within acceptable thresholds.');
  }
  
  return '<ul><li>' + recommendations.join('</li><li>') + '</li></ul>';
}

function generateTextSummary(data) {
  const metrics = data.metrics;
  
  return `
==========================================
Authentication Load Test Summary
==========================================

Test Duration: ${(data.state.testRunDurationMs / 1000 / 60).toFixed(2)} minutes
Total Virtual Users: ${data.root_group.checks?.length || 'N/A'}

HTTP Metrics:
- Total Requests: ${metrics.http_reqs?.values?.count || 0}
- Request Rate: ${(metrics.http_reqs?.values?.rate || 0).toFixed(2)} req/s
- Failure Rate: ${((metrics.http_req_failed?.values?.rate || 0) * 100).toFixed(2)}%
- Avg Response Time: ${(metrics.http_req_duration?.values?.avg || 0).toFixed(2)}ms
- 95th Percentile: ${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms

Authentication Metrics:
- Auth Failure Rate: ${((metrics.auth_failures?.values?.rate || 0) * 100).toFixed(2)}%
- Avg Login Duration: ${(metrics.login_duration?.values?.avg || 0).toFixed(2)}ms
- Total Registrations: ${metrics.registrations_total?.values?.count || 0}

Status: ${getOverallStatus(metrics)}
==========================================
  `;
}

function getOverallStatus(metrics) {
  const failureRate = metrics.http_req_failed?.values?.rate || 0;
  const authFailureRate = metrics.auth_failures?.values?.rate || 0;
  const p95ResponseTime = metrics.http_req_duration?.values?.['p(95)'] || 0;
  
  if (failureRate > 0.1 || authFailureRate > 0.05 || p95ResponseTime > 3000) {
    return '❌ FAILED - Performance thresholds exceeded';
  } else if (failureRate > 0.05 || authFailureRate > 0.02 || p95ResponseTime > 2000) {
    return '⚠️ WARNING - Some metrics approaching thresholds';
  } else {
    return '✅ PASSED - All metrics within acceptable limits';
  }
}