#!/usr/bin/env bash
# Fault injection for resilience testing

set -euo pipefail

NAMESPACE="${NAMESPACE:-resilience-lab}"
MODE="${1:-help}"

usage() {
  cat << EOF
Usage: $0 [MODE]

Modes:
  latency    - Inject 300ms latency to payments pod
  failure    - Set FAIL_MODE=1 (payments returns 500)
  slow       - Set SLOW_MODE=1 (payments delays 2s)
  kill       - Delete random payments pod
  cleanup    - Remove all fault injections
  help       - Show this help

Examples:
  $0 latency
  $0 failure
  $0 cleanup

Environment variables:
  NAMESPACE - K8s namespace (default: resilience-lab)
EOF
}

inject_latency() {
  echo "🔥 Injecting 300ms latency to payments pods..."
  PODS=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=payments -o name)

  if [ -z "$PODS" ]; then
    echo "ERROR: No payments pods found in namespace $NAMESPACE" >&2
    exit 1
  fi

  for POD in $PODS; do
    echo "  → $POD"

    if ! kubectl exec -n "$NAMESPACE" "$POD" -- which tc > /dev/null 2>&1; then
      echo "ERROR: 'tc' not found in $POD." >&2
      echo "  Fix: rebuild the payments image with iproute2 and redeploy." >&2
      exit 1
    fi

    kubectl exec -n "$NAMESPACE" "$POD" -- \
      tc qdisc add dev eth0 root netem delay 300ms
  done

  echo "✅ Latency injected. Verify with:"
  echo "   kubectl exec -n $NAMESPACE <pod> -- tc qdisc show dev eth0"
}

inject_failure() {
  echo "🔥 Setting FAIL_MODE=1 on payments deployment..."

  kubectl set env deployment/resilience-lab-payments \
    -n "$NAMESPACE" FAIL_MODE=1

  echo "✅ FAIL_MODE enabled. Payments will return 500."
  echo "   Monitor retries and outlier ejection in Envoy stats."
}

inject_slow() {
  echo "🔥 Setting SLOW_MODE=1 on payments deployment..."

  kubectl set env deployment/resilience-lab-payments \
    -n "$NAMESPACE" SLOW_MODE=1

  echo "✅ SLOW_MODE enabled. Payments will delay 2s."
  echo "   Monitor timeouts in Envoy stats."
}

kill_pod() {
  echo "🔥 Deleting random payments pod..."

  POD=$(kubectl get pods -n "$NAMESPACE" \
    -l app.kubernetes.io/name=payments \
    -o jsonpath='{.items[0].metadata.name}')

  echo "  → Killing $POD"
  kubectl delete pod -n "$NAMESPACE" "$POD"

  echo "✅ Pod deleted. Monitor retries and pod recovery."
}

cleanup() {
  echo "🧹 Cleaning up fault injections..."

  # Remove env vars
  kubectl set env deployment/resilience-lab-payments \
    -n "$NAMESPACE" FAIL_MODE- SLOW_MODE- 2>/dev/null || true

  # Remove tc latency
  PODS=$(kubectl get pods -n "$NAMESPACE" \
    -l app.kubernetes.io/name=payments -o name 2>/dev/null || true)

  for POD in $PODS; do
    echo "  → Cleaning $POD"
    kubectl exec -n "$NAMESPACE" "$POD" -- \
      tc qdisc del dev eth0 root 2>/dev/null || true

    REMAINING=$(kubectl exec -n "$NAMESPACE" "$POD" -- \
      tc qdisc show dev eth0 2>/dev/null \
      | grep -v -E 'noqueue|pfifo_fast|noop' || true)
    if [ -n "$REMAINING" ]; then
      echo "  ⚠️  WARNING: non-default tc qdisc still present on $POD:"
      echo "  $REMAINING"
    else
      echo "  ✅ tc qdisc clean on $POD"
    fi
  done

  echo "✅ Cleanup complete."
}

case "$MODE" in
  latency)
    inject_latency
    ;;
  failure)
    inject_failure
    ;;
  slow)
    inject_slow
    ;;
  kill)
    kill_pod
    ;;
  cleanup)
    cleanup
    ;;
  help|*)
    usage
    exit 0
    ;;
esac

