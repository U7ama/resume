# Deployment record and updates

Verified deployment on 15 October 2026:

- Site: https://resume.usamaaslam.site/
- AWS account: `129631621612`, region: `us-east-1`.
- CloudFormation stack: `resume-studio-origin`.
- Function: `resume-studio-origin-api`, Python 3.13, ARM64, 256 MB, 65-second timeout.
- Table: `resume-studio-origin-History-1J1J1NUCT1R1` (retained on stack deletion/replacement).
- Private bootstrap bucket: `resume-studio-129631621612-us-east-1`; all public access blocked, AES256 encryption, HTTPS-only bucket policy.
- Cloudflare Worker: `resume-studio-proxy`, custom domain `resume.usamaaslam.site`.
- Source checkout: `/home/usama/Work/personal/portfolio-workspace/resume`, branch: `codex/resume-studio`.

The initial CloudFront deployment failed because AWS requires manual account verification. Its rolled-back stack, empty retained tables, WAF/OAC resources and unused pending ACM certificate were removed. No paid CloudFront/WAF plan remains. The Lambda account quota did not allow a reserved concurrency allocation; the application uses login and AI quotas instead.

## Updating the AWS application

1. Run the checks in README.md. Preserve `.private/` and the existing DynamoDB table. Do not reset the history to redeploy.
2. Build with `python3 scripts/build-aws.py --bucket resume-studio-129631621612-us-east-1`. This produces the Lambda ZIP, `infra/template.json`, and an allowlisted upload manifest under `output/aws/`.
3. Upload the content-addressed ZIP to its `deploy/api-....zip` key in the bootstrap bucket. The manifest also lists public files for compatibility packaging; the active AWS app serves those files from the Lambda ZIP, so separate `public/` uploads are unnecessary. Upload `private/runtime.json` only when private settings change. Use short-lived S3 upload URLs with `scripts/upload-presigned.py`; provide the explicit JSON manifest through hidden stdin. Never include `.private/` in a public-site artifact.
4. Use the AWS MCP CloudFormation tools (or the CloudFormation console) to validate the generated template and update **the existing** `resume-studio-origin` stack with `CAPABILITY_IAM`. Review the change set: a content-only update should modify Lambda code without replacing the table. Wait for `UPDATE_COMPLETE`.
5. Obtain `OriginUrl` from stack outputs and prepare bindings:

```sh
python3 scripts/prepare-proxy.py --origin https://YOUR_ORIGIN.lambda-url.us-east-1.on.aws/
wrangler deploy --config infra/wrangler.jsonc --dry-run --outdir output/proxy
wrangler deploy --config infra/wrangler.jsonc --secrets-file .private/proxy-secrets.json
```

The ignored bindings file contains the origin URL, a proxy secret and the ZIP's asset revision. The revision changes the public cache key on deployment. Workers routes manage the custom domain; the remaining portfolio DNS and workers are preserved. Do not print the secret file. The current Wrangler OAuth login is sufficient; do not create a new broad API token.

6. Verify with `python3 scripts/smoke-live.py --url https://resume.usamaaslam.site`. Add `--generate` only for an intentional live Qwen probe; it consumes one generation reservation. `--seed` creates a baseline only when a CV type has no cloud version. It never replaces an existing CV.

GitHub Pages remains a static compatibility site. Its workflow packages only the public allowlist and does not deploy the AWS backend. Pushing a commit does not update AWS automatically.

## Checks and limits

Backend tests cover origin guards, login limits, sessions/logout, version immutability, optimistic concurrency, history pagination, generation quotas and invalid provider output. Live checks verified the real Lambda/DynamoDB path, custom-domain proxy and Qwen response. Browser PDF exports of all three baselines were inspected. Browser print settings can affect pagination; disable browser headers/footers and use the stylesheet's A4 sizing.

CloudFormation service validation passed. Local `cfn-lint` and `cfn-guard` were unavailable and were not installed; their schema/compliance checks were not run. No external security audit or load test was performed. Private CV history has no automatic deletion; session/quota rows expire using DynamoDB TTL. Retention on stack deletion preserves records but is not a backup against accidental record deletion; export important CVs locally.
