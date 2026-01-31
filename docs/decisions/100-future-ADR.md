ADR-007: Secrets Management Strategy

Decision: Do we store DB passwords in GitHub Actions Secrets (Environment Variables) or use AWS Systems Manager (SSM) Parameter Store?

Recommendation: SSM Parameter Store (More "Cloud Native").

ADR-008: Observability & Logging Standard

Decision: How do we trace a request that fails?

Recommendation: AWS CloudWatch for Logs + AWS X-Ray for distributed tracing (shows you exactly where the latency is).

ADR-009: Infrastructure as Code (IaC) Tooling

Decision: How do we provision this?

Recommendation: Terraform (Industry standard) or AWS CDK (Rising popularity for devs).