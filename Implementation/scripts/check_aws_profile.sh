#!/usr/bin/env bash
# Read-only guard. Require an explicit member-selected profile; never default.
set -euo pipefail
if [[ $# -ne 1 || -z "$1" ]]; then
  echo 'Usage: bash Implementation/scripts/check_aws_profile.sh YOUR_PROJECT_PROFILE' >&2
  exit 2
fi
EXPECTED_ACCOUNT="160885259244"
EXPECTED_REGION="us-east-1"
PROFILE="$1"

if ! region=$(aws configure get region --profile "$PROFILE"); then
  echo 'ERROR: Could not read the selected profile region. Check your approved setup.' >&2
  exit 1
fi
if [[ "$region" != "$EXPECTED_REGION" ]]; then
  echo "ERROR: Selected profile region is '$region', expected $EXPECTED_REGION. ABORTING." >&2
  exit 1
fi
if ! account=$(aws sts get-caller-identity --profile "$PROFILE" --region "$EXPECTED_REGION" --query Account --output text); then
  echo 'ERROR: Identity check failed. Refresh your own approved login; no default fallback.' >&2
  exit 1
fi
if [[ "$account" != "$EXPECTED_ACCOUNT" ]]; then
  echo "ERROR: Selected profile account is $account, expected project account $EXPECTED_ACCOUNT. ABORTING." >&2
  exit 1
fi
echo "OK: profile '$PROFILE' -> account $account, region $region"
