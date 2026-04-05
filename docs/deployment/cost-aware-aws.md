# Cost-aware AWS deployment (personal / portfolio dev)

This document describes how to run CloudClearingAPI on AWS **without paying for NAT Gateway** while keeping the same Terraform codebase you can show in DE interviews.

---

## Recommended strategy

| Goal | Approach |
|------|----------|
| **Minimum monthly burn** | `enable_nat_gateway = false` in `terraform.tfvars` (see example file). Terraform places Step Functions–launched ECS tasks in **public subnets** with **`AssignPublicIp: ENABLED`** so the weekly job can still reach Google Earth Engine, scrapers, and OSM. |
| **Production-style networking** | `enable_nat_gateway = true`: tasks stay in **private subnets** with `AssignPublicIp: DISABLED` (~\$32+/month per NAT path in typical 2-AZ setups). |
| **\$0 AWS** | Do not run `terraform apply`, or run `terraform destroy` when you are not demoing. IaC in Git still demonstrates DE skills. |

The root module **selects subnets and public IP automatically** from `enable_nat_gateway` (see `infra/terraform/main.tf` → `module.step_functions`).

---

## What you still pay (no NAT)

Rough order of magnitude for a **weekly** Fargate task:

- **Fargate**: only while the task runs (CPU/memory × duration).
- **S3 / ECR / CloudWatch / Step Functions / EventBridge**: usually a few dollars/month if logs and images are modest.
- **VPC endpoints** (if enabled): interface endpoint hourly charges; you can set `enable_vpc_endpoints = false` in dev to trim further (trades cost vs data-processing path).

NAT Gateway **hourly charges stop** when `enable_nat_gateway = false`.

---

## Trade-offs (no NAT)

- Tasks get a **public IP** while running: acceptable for a **batch** workload with locked-down security groups (this stack allows **egress only** from the ECS task SG by default; no inbound ports required for the monitor).
- Not the same isolation story as **private subnet + NAT**; use **NAT + private subnets** for production or strict compliance narratives.

---

## Related files

- `infra/terraform/terraform.tfvars.example` — copy to `terraform.tfvars` and set `earthengine_project`, emails, and `enable_nat_gateway`.
- `docs/deployment/terraform-guide.md` — full module and workflow reference.
- `infra/terraform/README.md` — quick commands and post-deploy steps.
