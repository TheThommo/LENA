#!/usr/bin/env bash
# LENA production smoke test — run before marketing launch.
# Usage: ./scripts/smoke_test_production.sh
set -euo pipefail

FRONTEND="${FRONTEND_URL:-https://lena-app.up.railway.app}"
BACKEND="${BACKEND_URL:-https://lena-production-health.up.railway.app}"

pass=0
fail=0

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

echo
echo "[2] Backend health"
check "Backend /api/health returns 200" "curl -sf -o /dev/null '$BACKEND/api/health'"
check "Backend /api/discover/suggestions returns 200" "curl -sf -o /dev/null '$BACKEND/api/discover/suggestions?persona=general'"

echo
echo "[3] API proxy (same-origin /api via frontend)"
check "Frontend /api/health proxy" "curl -sf -o /dev/null '$FRONTEND/api/health'"

echo
echo "[4] Static assets"
check "Logo asset exists" "curl -sf -o /dev/null '$FRONTEND/lena_logo_1.png'"
check "Favicon exists" "curl -sf -o /dev/null '$FRONTEND/favicon-32x32.png'"

echo
echo "[5] Landing page content"
check "Landing mentions PULSE" "curl -sf '$FRONTEND/' | grep -qi 'PULSE'"
check "Landing mentions Pro pricing" "curl -sf '$FRONTEND/' | grep -qi 'Pro'"
check "Landing links to /chat" "curl -sf '$FRONTEND/' | grep -q '/chat'"

echo
echo "=============================================="
echo "Results: $pass passed, $fail failed"
echo "=============================================="

if [ "$fail" -gt 0 ]; then
  exit 1
fi

echo "All smoke checks passed. Ready for Stripe + marketing."
