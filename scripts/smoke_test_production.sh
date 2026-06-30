#!/usr/bin/env bash
# LENA production smoke test — run before marketing launch and after deploys.
# Usage:
#   ./scripts/smoke_test_production.sh
#   FRONTEND_URL=https://www.lenamd.com ./scripts/smoke_test_production.sh
set -euo pipefail

FRONTEND="${FRONTEND_URL:-https://www.lenamd.com}"
BACKEND="${BACKEND_URL:-https://lena-production-health.up.railway.app}"

pass=0
fail=0
warn=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✓ $name"
    pass=$((pass + 1))
  else
    echo "  ✗ $name"
    fail=$((fail + 1))
  fi
}

warn_check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✓ $name"
    pass=$((pass + 1))
  else
    echo "  ⚠ $name (warning)"
    warn=$((warn + 1))
  fi
}

echo "=============================================="
echo "LENA Production Smoke Test"
echo "Frontend: $FRONTEND"
echo "Backend:  $BACKEND"
echo "=============================================="
echo

echo "[1] Frontend pages"
check "Landing page (/) returns 200" "curl -sf -o /dev/null -w '%{http_code}' '$FRONTEND/' | grep -q 200"
check "Chat app (/chat) returns 200" "curl -sf -o /dev/null -w '%{http_code}' '$FRONTEND/chat' | grep -q 200"
check "Login page returns 200" "curl -sf -o /dev/null -w '%{http_code}' '$FRONTEND/login' | grep -q 200"
check "Register page returns 200" "curl -sf -o /dev/null -w '%{http_code}' '$FRONTEND/register' | grep -q 200"

health_ok() {
  local base="$1"
  local path
  for path in /api/health /api/health/; do
    if curl -sfL "${base}${path}" 2>/dev/null | grep -q '"status":"healthy"'; then
      return 0
    fi
  done
  return 1
}

echo
echo "[2] Backend health"
if health_ok "$BACKEND"; then
  echo "  ✓ Backend health endpoint returns healthy"
  pass=$((pass + 1))
else
  echo "  ✗ Backend health endpoint returns healthy"
  fail=$((fail + 1))
fi
check "Backend /api/discover/suggestions returns 200" "curl -sf -o /dev/null '$BACKEND/api/discover/suggestions?persona=general'"

echo
echo "[3] API proxy (same-origin /api via frontend)"
if health_ok "$FRONTEND"; then
  echo "  ✓ Frontend /api/health proxy"
  pass=$((pass + 1))
else
  if curl -sf -o /dev/null "$FRONTEND/api/discover/suggestions?persona=general"; then
    echo "  ⚠ Frontend /api/health proxy (API works; deploy health route fix)"
    warn=$((warn + 1))
  else
    echo "  ✗ Frontend /api/health proxy"
    fail=$((fail + 1))
  fi
fi
check "Frontend /api/discover/suggestions proxy" "curl -sf -o /dev/null '$FRONTEND/api/discover/suggestions?persona=general'"

echo
echo "[4] Security headers"
warn_check "HSTS header present" "curl -sfI '$FRONTEND/' | grep -qi 'strict-transport-security'"
warn_check "Frontend served over HTTPS" "curl -sfI '$FRONTEND/' | head -1 | grep -q 'HTTP/2 200'"

echo
echo "[5] Static assets"
check "Logo asset exists" "curl -sf -o /dev/null '$FRONTEND/lena_logo_1.png'"
check "Favicon exists" "curl -sf -o /dev/null '$FRONTEND/favicon-32x32.png'"

echo
echo "[6] Landing page content"
check "Landing mentions PULSE" "curl -sf '$FRONTEND/' | grep -qi 'PULSE'"
check "Landing mentions Pro pricing" "curl -sf '$FRONTEND/' | grep -qi 'Pro'"
check "Landing links to /chat" "curl -sf '$FRONTEND/' | grep -q '/chat'"
warn_check "Landing mentions 3 free searches" "curl -sf '$FRONTEND/' | grep -qi '3 search'"

echo
echo "[7] TLS certificate"
warn_check "TLS cert valid for www.lenamd.com" "echo | openssl s_client -connect www.lenamd.com:443 -servername www.lenamd.com 2>/dev/null | openssl x509 -noout -subject 2>/dev/null | grep -q 'www.lenamd.com'"

echo
echo "=============================================="
echo "Results: $pass passed, $fail failed, $warn warnings"
echo "=============================================="

if [ "$fail" -gt 0 ]; then
  exit 1
fi

echo "All required smoke checks passed."
if [ "$warn" -gt 0 ]; then
  echo "Review warnings before broad public launch."
fi
