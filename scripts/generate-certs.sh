#!/usr/bin/env bash
# Generates a self-signed TLS certificate for local Traefik development.
# Output: deploy/traefik/certs/tls.key + tls.crt (gitignored, do not commit)
set -euo pipefail

CERT_DIR="$(git rev-parse --show-toplevel)/deploy/traefik/certs"
DOMAIN="resilience-lab.local"

mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout "$CERT_DIR/tls.key" \
  -out    "$CERT_DIR/tls.crt" \
  -subj   "/CN=$DOMAIN/O=resilience-lab" \
  -addext "subjectAltName=DNS:$DOMAIN,DNS:*.resilience-lab.local"

chmod 600 "$CERT_DIR/tls.key"
echo "Certs generated in $CERT_DIR"
