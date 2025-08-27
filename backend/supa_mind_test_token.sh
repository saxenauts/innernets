#!/usr/bin/env bash
# supa_mint_test_token_v2.sh
set -euo pipefail

EMAIL="${1:-test@user.com}"
PASSWORD="${2:-T3stUser!2025}"
ENV_FILE="${ENV_FILE:-.env}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 1; }; }
need curl; need jq

if [[ -f "$ENV_FILE" ]]; then set -a; . "$ENV_FILE"; set +a; else
  echo "No $ENV_FILE found. Set ENV_FILE or create one with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY." >&2; exit 1
fi

: "${SUPABASE_URL:?}"; : "${SUPABASE_SERVICE_ROLE_KEY:?}"; : "${SUPABASE_ANON_KEY:?}"
URL="${SUPABASE_URL%/}"
ADMIN=(-H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY")
json() { jq -cn "$@"; }

# 1) Try create
create_body="$(mktemp)"; trap 'rm -f "$create_body"' EXIT
create_code=$(curl -sS -o "$create_body" -w "%{http_code}" -X POST \
  "$URL/auth/v1/admin/users" "${ADMIN[@]}" -H "Content-Type: application/json" \
  --data "$(json --arg email "$EMAIL" --arg password "$PASSWORD" '{email:$email,password:$password,email_confirm:true}')")

uid=""
if [[ "$create_code" == "201" || "$create_code" == "200" ]]; then
  uid="$(jq -r '.id // .user.id // empty' < "$create_body")"
elif [[ "$create_code" == "409" ]] || { [[ "$create_code" == "422" ]] && grep -q 'email_exists' "$create_body"; }; then
  # Already exists → lookup
  uid="$(curl -sS "$URL/auth/v1/admin/users?email=$EMAIL" "${ADMIN[@]}" | jq -r '.users[0].id // .id // empty')"
else
  echo "Admin create failed (HTTP $create_code):" >&2
  cat "$create_body" >&2
  # Helpful hint on weak password
  if [[ "$create_code" == "422" ]] && grep -qi 'password' "$create_body"; then
    echo "Hint: your password likely violates the policy. Try a stronger one (e.g., 'Supabase_Test!2025_Alpha')." >&2
  fi
  exit 1
fi

if [[ -z "$uid" || "$uid" == "null" ]]; then
  echo "Could not determine user id for $EMAIL." >&2; exit 1
fi

# 2) Ensure password meets policy
setpw_code=$(curl -sS -o /dev/null -w "%{http_code}" -X PUT \
  "$URL/auth/v1/admin/users/$uid" "${ADMIN[@]}" -H "Content-Type: application/json" \
  --data "$(json --arg password "$PASSWORD" '{password:$password}')")
if [[ "$setpw_code" != "200" ]]; then
  echo "Password update failed (HTTP $setpw_code). Likely policy issue; try a stronger password." >&2; exit 1
fi

# 3) Password grant → print only the access_token
login_json="$(curl -sS -X POST "$URL/auth/v1/token?grant_type=password" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Content-Type: application/json" \
  --data "$(json --arg email "$EMAIL" --arg password "$PASSWORD" '{email:$email,password:$password}')" )"

token="$(jq -r '.access_token // empty' <<<"$login_json")"
if [[ -z "$token" || "$token" == "null" ]]; then
  echo "Login failed. Response:" >&2
  echo "$login_json" | jq . >&2
  exit 1
fi

echo "$token"

