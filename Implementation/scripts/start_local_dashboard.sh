#!/usr/bin/env bash
# Start visualization only; never provision services or rerun processing.
set -euo pipefail
if [[ $# -ne 1 || -z "$1" ]]; then
  echo 'Usage: bash Implementation/scripts/start_local_dashboard.sh YOUR_PROJECT_PROFILE' >&2
  exit 2
fi
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
dashboard_python="${AML_DASHBOARD_PYTHON:-$project_root/.venv-dashboard/bin/python}"
if [[ ! -x "$dashboard_python" ]]; then
  echo 'Dashboard environment missing. Follow the visualization setup in Implementation/SETUP.md.' >&2
  exit 2
fi
bash "$project_root/Implementation/scripts/check_aws_profile.sh" "$1"
export AML_AWS_PROFILE="$1"
export AML_ATHENA_WORKGROUP=is459-aml-dashboard
unset AML_USE_INSTANCE_ROLE
exec "$dashboard_python" -m streamlit run "$project_root/Implementation/dashboard/app.py" \
  --server.address=127.0.0.1 --server.port=8501 --server.headless=true
