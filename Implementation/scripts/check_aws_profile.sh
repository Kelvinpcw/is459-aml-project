#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Guard: abort if the profile is not the project account.
#
# This machine has another account authenticated to the AWS CLI (see
# Implementation/SETUP.md). Run this before EVERY mutating AWS command.
#
# Usage: ./scripts/check_aws_profile.sh [profile]    (default profile: is459)
# Exit 0 = safe to proceed; exit 1 = WRONG ACCOUNT/REGION, do not continue.
# ---------------------------------------------------------------------------
set -euo pipefail

EXPECTED_ACCOUNT="160885259244"
EXPECTED_REGION="us-east-1"
PROFILE="${1:-is459}"

account=$(aws sts get-caller-identity --profile "$PROFILE" --query Account --output text)
region=$(aws configure get region --profile "$PROFILE")

if [[ "$account" != "$EXPECTED_ACCOUNT" ]]; then
  echo "ERROR: profile '$PROFILE' is account $account, expected project account $EXPECTED_ACCOUNT. ABORTING." >&2
  exit 1
fi
if [[ "$region" != "$EXPECTED_REGION" ]]; then
  echo "ERROR: profile '$PROFILE' region is '$region', expected $EXPECTED_REGION." >&2
  exit 1
fi
echo "OK: profile '$PROFILE' -> account $account, region $region"
