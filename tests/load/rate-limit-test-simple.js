/**
 * K6 Load Test - Rate Limiting Validation (Simplified)
 * Uses /openapi.json (FastAPI's auto-generated schema) to avoid the
 * Payments service dependency.
 *
 * `/healthz` is used only for the readiness check in setup(). Rate-limit
 * validation targets `/openapi.json` because `/healthz` and `/metrics` are
 * excluded from rate limiting (see RateLimitMiddleware.excluded_paths) and
 * would never produce a 429 no matter the load. (The `/` root endpoint is
 * avoided too — it currently returns 500 due to an unrelated
 * ResponseValidationError bug.)
 */

import http from 'k6/http';
import { check } from 'k6';
import { Rate, Counter } from 'k6/metrics';

const errorRate = new Rate('errors');
const rateLimitHits = new Counter('rate_limit_429_count');
const successfulRequests = new Counter('successful_requests');

export const options = {
  scenarios: {
    under_limit: {
      executor: 'constant-arrival-rate',
      rate: 50,
      timeUnit: '1m',
      duration: '1m',
      preAllocatedVUs: 5,
      maxVUs: 10,
      tags: { scenario: 'under_limit' },
      exec: 'underLimit',
    },
    over_limit: {
      executor: 'constant-arrival-rate',
      rate: 100,
      timeUnit: '1m',
      duration: '1m',
      preAllocatedVUs: 10,
      maxVUs: 20,
      startTime: '2m30s',
      tags: { scenario: 'over_limit' },
      exec: 'overLimit',
    },
  },
  thresholds: {
    'errors{scenario:under_limit}': ['rate<0.05'],
    'errors{scenario:over_limit}': ['rate>0.30'],
    http_req_duration: ['p(95)<500'],
  },
};

const BASE_URL = __ENV.K6_BASE_URL || 'http://localhost:8001';
const TENANT_ID = __ENV.K6_TENANT_ID || 'test-tenant';

const params = {
  headers: {
    'X-Tenant': TENANT_ID,
  },
};

export function underLimit() {
  const response = http.get(`${BASE_URL}/openapi.json`, params);

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'no rate limit error': (r) => r.status !== 429,
  });

  if (!success) {
    errorRate.add(1);
    if (response.status === 429) {
      rateLimitHits.add(1);
      console.log(`[UNDER_LIMIT] Unexpected 429`);
    }
  } else {
    successfulRequests.add(1);
  }
}

export function overLimit() {
  const response = http.get(`${BASE_URL}/openapi.json`, params);

  check(response, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
  });

  if (response.status === 429) {
    rateLimitHits.add(1);
    check(response, {
      'has rate limit error': (r) => r.json('error') === 'rate_limit_exceeded',
      'has tenant in response': (r) => r.json('tenant') === TENANT_ID,
    });
  } else if (response.status === 200) {
    successfulRequests.add(1);
  } else {
    errorRate.add(1);
    console.log(`[OVER_LIMIT] Unexpected status ${response.status}`);
  }
}

export function setup() {
  console.log('Testing rate limiting with /openapi.json endpoint (/healthz and /metrics are excluded)');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Tenant: ${TENANT_ID}`);

  const healthCheck = http.get(`${BASE_URL}/healthz`);
  if (healthCheck.status !== 200) {
    throw new Error(`Health check failed: ${healthCheck.status}`);
  }
  console.log('✓ Health check passed\n');
}

export function teardown(data) {
  console.log('\n✓ Test completed!');
}
