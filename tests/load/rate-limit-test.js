/**
 * K6 Load Test - Rate Limiting Validation
 *
 * Tests the rate limiting middleware with two scenarios:
 * 1. Under limit: 50 req/min - should succeed
 * 2. Over limit: 100 req/min - should get 429 responses
 *
 * Rate limit: 60 requests per 60 seconds per tenant
 *
 * Usage:
 *   k6 run tests/load/rate-limit-test.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const rateLimitHits = new Counter('rate_limit_429_count');
const successfulRequests = new Counter('successful_requests');

// Test configuration
export const options = {
  scenarios: {
    // Scenario 1: Under limit - 50 req/min
    under_limit: {
      executor: 'constant-arrival-rate',
      rate: 50,           // 50 requests
      timeUnit: '1m',     // per minute
      duration: '1m',     // for 1 minute
      preAllocatedVUs: 5,
      maxVUs: 10,
      tags: { scenario: 'under_limit' },
      exec: 'underLimit',
    },

    // Scenario 2: Over limit - 100 req/min
    // Wait 90s after scenario 1 to let rate limit window reset
    over_limit: {
      executor: 'constant-arrival-rate',
      rate: 100,          // 100 requests
      timeUnit: '1m',     // per minute
      duration: '1m',     // for 1 minute
      preAllocatedVUs: 10,
      maxVUs: 20,
      startTime: '2m30s', // Start after 2m30s (1m test + 1m30s cooldown)
      tags: { scenario: 'over_limit' },
      exec: 'overLimit',
    },
  },

  thresholds: {
    // Under limit scenario should have <5% errors
    'errors{scenario:under_limit}': ['rate<0.05'],
    // Over limit scenario should have >30% errors (rate limit hits)
    'errors{scenario:over_limit}': ['rate>0.30'],
    // HTTP request duration should be under 500ms for p95
    http_req_duration: ['p(95)<500'],
  },
};

// Base URL - override with K6_BASE_URL env var
const BASE_URL = __ENV.K6_BASE_URL || 'http://localhost:8080';
const TENANT_ID = __ENV.K6_TENANT_ID || 'test-tenant';

// Test payload
const paymentPayload = JSON.stringify({
  amount: 99.99,
  currency: 'USD',
  tenant_id: TENANT_ID,
});

const params = {
  headers: {
    'Content-Type': 'application/json',
    'X-Tenant': TENANT_ID,
  },
  tags: { name: 'CreatePayment' },
};

/**
 * Scenario 1: Under limit (50 req/min)
 * Expected: All requests should succeed (201 Created)
 */
export function underLimit() {
  const response = http.post(`${BASE_URL}/pay`, paymentPayload, params);

  const success = check(response, {
    'status is 201': (r) => r.status === 201,
    'response has payment_id': (r) => r.json('payment_id') !== undefined,
    'no rate limit error': (r) => r.status !== 429,
  });

  if (!success) {
    errorRate.add(1);
    if (response.status === 429) {
      rateLimitHits.add(1);
      console.log(`[UNDER_LIMIT] Unexpected 429 - Rate limit hit at ${new Date().toISOString()}`);
    }
  } else {
    successfulRequests.add(1);
  }
}

/**
 * Scenario 2: Over limit (100 req/min)
 * Expected: Should get 429 responses when limit exceeded
 */
export function overLimit() {
  const response = http.post(`${BASE_URL}/pay`, paymentPayload, params);

  const success = check(response, {
    'status is 201 or 429': (r) => r.status === 201 || r.status === 429,
  });

  if (response.status === 429) {
    rateLimitHits.add(1);

    // Verify 429 response structure
    check(response, {
      'has rate limit error': (r) => r.json('error') === 'rate_limit_exceeded',
      'has tenant in response': (r) => r.json('tenant') === TENANT_ID,
      'has limit info': (r) => r.json('limit') !== undefined,
    });
  } else if (response.status === 201) {
    successfulRequests.add(1);
  } else {
    errorRate.add(1);
    console.log(`[OVER_LIMIT] Unexpected status ${response.status}`);
  }
}

/**
 * Setup - runs once before test
 */
export function setup() {
  console.log('='.repeat(60));
  console.log('K6 Rate Limiting Load Test');
  console.log('='.repeat(60));
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Tenant ID: ${TENANT_ID}`);
  console.log(`Rate Limit: 60 requests per 60 seconds`);
  console.log('');
  console.log('Scenarios:');
  console.log('  1. Under limit:  50 req/min for 1 min (0s-60s)');
  console.log('  2. Cooldown:     90s wait to reset rate limit window');
  console.log('  3. Over limit:   100 req/min for 1 min (150s-210s)');
  console.log('');
  console.log('Total test duration: ~3m30s');
  console.log('='.repeat(60));

  // Health check
  const healthCheck = http.get(`${BASE_URL}/healthz`);
  if (healthCheck.status !== 200) {
    throw new Error(`Health check failed: ${healthCheck.status}`);
  }
  console.log('✓ Health check passed');
  console.log('');
}

/**
 * Teardown - runs once after test
 */
export function teardown(data) {
  console.log('');
  console.log('='.repeat(60));
  console.log('Test completed!');
  console.log('');
  console.log('Next steps:');
  console.log('  1. Check metrics: kubectl port-forward svc/api 8080:8080');
  console.log('     curl http://localhost:8080/metrics | grep rl_denied_total');
  console.log('  2. Check logs: kubectl logs -l app=api --tail=100');
  console.log('  3. Verify results in summary above');
  console.log('='.repeat(60));
}

/**
 * Default function - for quick testing
 */
export default function() {
  // Simple test - make one request
  const response = http.post(`${BASE_URL}/pay`, paymentPayload, params);

  check(response, {
    'status is 201 or 429': (r) => r.status === 201 || r.status === 429,
  });

  sleep(1);
}
