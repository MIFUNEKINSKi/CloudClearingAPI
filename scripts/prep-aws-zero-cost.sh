#!/usr/bin/env bash
# Zero-cost AWS prep: Terraform init/validate/plan and optional local Docker build.
# Does NOT run terraform apply, push to ECR, or start billable services.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT/infra/terraform"

echo "==> Terraform init (local state; backend block is commented in main.tf)"
(cd "$TF_DIR" && terraform init -input=false)

echo "==> Terraform validate"
(cd "$TF_DIR" && terraform validate)

echo "==> Terraform plan (read-only; no resources created)"
if [[ -f "$TF_DIR/terraform.tfvars" ]]; then
  (cd "$TF_DIR" && terraform plan -input=false)
else
  echo "    No infra/terraform/terraform.tfvars — using dev + placeholder GEE id for plan only."
  echo "    Copy terraform.tfvars.example to terraform.tfvars when you want real values."
  (cd "$TF_DIR" && terraform plan -input=false \
    -var='environment=dev' \
    -var='earthengine_project=plan-only-placeholder-not-used-until-apply')
fi

if command -v docker >/dev/null 2>&1; then
  echo "==> Docker build (local image only; no ECR push)"
  docker build -t cloudclearing-api:local "$ROOT"
else
  echo "==> Docker not found — skipped local image build"
fi

echo ""
echo "Done. No terraform apply was run; nothing was deployed to AWS."
