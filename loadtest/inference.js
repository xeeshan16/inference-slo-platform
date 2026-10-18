// k6 load test for POST /predict. Runs in-cluster as a Job (see job.yaml.tpl).
//
//   SCENARIO  steady | ramp | spike     (default steady)
//   RATE      steady-state arrival rate, requests/s
//   PEAK      peak arrival rate for ramp/spike, requests/s
//   DURATION  steady duration (e.g. 4m)
//   BATCH     images per request (1..32)
//
// Arrival-rate executors keep an open model: k6 keeps sending at the target
// rate even when the service slows down, so queueing shows up as latency and
// dropped iterations instead of being hidden by a closed loop.
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const TARGET = __ENV.TARGET_URL || 'http://inference-service.inference.svc.cluster.local:8080';
const SCENARIO = __ENV.SCENARIO || 'steady';
const RATE = parseInt(__ENV.RATE || '100', 10);
const PEAK = parseInt(__ENV.PEAK || '400', 10);
const DURATION = __ENV.DURATION || '4m';
const BATCH = parseInt(__ENV.BATCH || '8', 10);
const MAX_VUS = parseInt(__ENV.MAX_VUS || '1500', 10);

const common = { preAllocatedVUs: 200, maxVUs: MAX_VUS, timeUnit: '1s', exec: 'predict' };

const scenarios = {
  steady: {
    executor: 'constant-arrival-rate',
    rate: RATE,
    duration: DURATION,
    ...common,
  },
  ramp: {
    executor: 'ramping-arrival-rate',
    startRate: RATE,
    stages: [
      { target: RATE, duration: '30s' },
      { target: PEAK, duration: '4m' },
      { target: PEAK, duration: '1m' },
    ],
    ...common,
  },
  spike: {
    executor: 'ramping-arrival-rate',
    startRate: RATE,
    stages: [
      { target: RATE, duration: '1m' },
      { target: PEAK, duration: '10s' },
      { target: PEAK, duration: '2m' },
      { target: RATE, duration: '10s' },
      { target: RATE, duration: '1m' },
    ],
    ...common,
  },
};

if (!scenarios[SCENARIO]) {
  throw new Error(`unknown SCENARIO ${SCENARIO}`);
}

export const options = {
  scenarios: { [SCENARIO]: scenarios[SCENARIO] },
  discardResponseBodies: true,
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  thresholds: {
    // Informational: mirrors the SLO (99% under 300 ms, no errors). Not abortOnFail.
    'http_req_duration{expected_response:true}': ['p(99)<300'],
    http_req_failed: ['rate<0.01'],
  },
};

// Pre-generate a pool of payloads so request building is not the bottleneck.
function makePayload() {
  const instances = [];
  for (let i = 0; i < BATCH; i++) {
    const row = [];
    for (let j = 0; j < 64; j++) row.push(Math.floor(Math.random() * 17));
    instances.push(row);
  }
  return JSON.stringify({ instances });
}
const PAYLOADS = Array.from({ length: 50 }, makePayload);
const PARAMS = { headers: { 'Content-Type': 'application/json' }, timeout: '10s', tags: { name: 'predict' } };

// Client-side view of the SLI. The server can only count requests it saw; a
// connection refused or reset during a rollout never reaches its histogram.
const sliGood = new Counter('sli_good');            // 2xx/4xx and <= 300 ms
const sliSlow = new Counter('sli_bad_slow');        // answered, but > 300 ms
const sli5xx = new Counter('sli_bad_5xx');          // server answered 5xx
const sliConn = new Counter('sli_bad_transport');   // no HTTP response (refused, reset, timeout)
const SLO_THRESHOLD_MS = 300;

export function predict() {
  const res = http.post(`${TARGET}/predict`, PAYLOADS[Math.floor(Math.random() * PAYLOADS.length)], PARAMS);
  check(res, { 'status is 200': (r) => r.status === 200 });
  if (res.status === 0) {
    sliConn.add(1, { error_code: String(res.error_code) });
  } else if (res.status >= 500) {
    sli5xx.add(1);
  } else if (res.timings.duration > SLO_THRESHOLD_MS) {
    sliSlow.add(1);
  } else {
    sliGood.add(1);
  }
}

// Emit the machine-readable summary between markers so the runner script can
// extract it from the Job's logs.
export function handleSummary(data) {
  return {
    stdout: `\nK6_SUMMARY_BEGIN\n${JSON.stringify(data)}\nK6_SUMMARY_END\n`,
  };
}
