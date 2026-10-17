# Deployment record and updates

Verified CloudFront migration on 17 October 2026:

- Site: https://resume.usamaaslam.site/
- AWS account: `129631621612`, region: `us-east-1`.
- CloudFormation stack: `resume-studio-origin`.
- Function: `resume-studio-origin-api`, Python 3.13, ARM64, 256 MB, 65-second timeout.
- Table: `resume-studio-origin-History-1J1J1NUCT1R1` (retained on stack deletion/replacement).
- Private bootstrap bucket: `resume-studio-129631621612-us-east-1`; all public access blocked, AES256 encryption, HTTPS-only bucket policy.
- CloudFront stack: `resume-studio-edge`, distribution `E1TER5XI4EAJIX` (`d4rcmawamtuw8.cloudfront.net`).
- Cloudflare DNS: DNS-only `resume` CNAME to the CloudFront domain; ACM validation CNAME retained for renewal.
- CloudFront origin: stable IAM-only Lambda alias `cloudfront`; OAC invoke permissions scoped to this distribution.
- Previous Worker: `resume-studio-proxy`, no domain binding or public workers.dev endpoint, retained for recovery.
- CloudFront standard logs: private encrypted S3 bucket, seven-day lifecycle, minimal fields excluding IP/cookies/query/body.
- Source checkout: `/home/usama/Work/personal/portfolio-workspace/resume`, branch: `codex/resume-studio`.

AWS Support lifted the original CloudFront account restriction. The domain now uses CloudFront with HTTPS, TLS 1.2 minimum, IAM origin access and a 75-second origin read timeout for the 65-second Lambda. No paid WAF/Shield Advanced, fixed-price subscription or real-time log stream was added. The Lambda account quota did not allow reserved concurrency; application login and generation quotas remain in place.

## Updating the AWS application

1. Run the checks in README.md. Preserve `.private/` and the existing DynamoDB table. Do not reset the history to redeploy.
2. Build with `python3 scripts/build-aws.py --bucket resume-studio-129631621612-us-east-1`. This produces the Lambda ZIP, `infra/template.json`, and an allowlisted upload manifest under `output/aws/`.
3. Upload the content-addressed ZIP to its `deploy/api-....zip` key in the bootstrap bucket. The manifest also lists public files for compatibility packaging; the active AWS app serves those files from the Lambda ZIP, so separate `public/` uploads are unnecessary. Upload `private/runtime.json` only when private settings change. Use short-lived S3 upload URLs with `scripts/upload-presigned.py`; provide the explicit JSON manifest through hidden stdin. Never include `.private/` in a public-site artifact.
4. Use AWS MCP CloudFormation tools (or the console) to validate the **complete generated template** and update the existing `resume-studio-origin` stack with `CAPABILITY_IAM`. Review the change set: a content release modifies the function, replaces its immutable `CloudFrontVersion`, and advances the `CloudFrontAlias`; the retained table must not be replaced. Updating only `Api.Code.S3Key` leaves the live alias on the old release. Wait for `UPDATE_COMPLETE` and verify the alias version and code hash. Preserve `infra/cloudfront-state.json` (`prepare` and `active` true), which keeps both function URLs IAM-only and permissions scoped to the distribution.
5. Invalidate changed public paths in distribution `E1TER5XI4EAJIX` (or use one `/*` path for a release), then wait for completion. CloudFront's monthly invalidation allowance is account-shared. Private API requests are never cached. Update version query strings when modifying CSS/JS so browser caches receive the release.
6. Verify with `python3 scripts/smoke-live.py --url https://resume.usamaaslam.site`. This checks login, private reads and logout without saving CV versions or generating AI text. Add `--generate` only for an intentional Qwen probe; it consumes one generation reservation. `--seed` creates a baseline when a type has no cloud version and must only be used when explicitly requested.

## Updating the edge configuration

`python3 scripts/build-cloudfront.py --origin-url https://nzachfp2q3tbmzeo4dyn5cl56a0ofump.lambda-url.us-east-1.on.aws/ --alias-arn arn:aws:lambda:us-east-1:129631621612:function:resume-studio-origin-api:cloudfront` regenerates `infra/cloudfront-template.json`. Validate and review a change set against existing stack `resume-studio-edge`, preserving its distribution identity, alternate hostname, certificate, `/api/*` disabled cache policy, origin request policy, OAC permissions and short log retention. Keep the origin read timeout above Lambda's timeout.

Cloudflare remains DNS only; do not restore the Worker route as part of a routine application deployment. The retained Worker code/ignored secrets are for deliberate recovery only. A rollback would require coordinating its custom-domain binding with the CNAME, then restoring the original header-guarded origin configuration. Do not delete the certificate validation CNAME, database, private configuration or unrelated portfolio records.

GitHub Pages remains a static compatibility site. Its workflow packages only the public allowlist and does not deploy the AWS backend. Pushing a commit does not update AWS automatically.

## Checks and limits

Backend tests cover origin guards, login limits, sessions/logout, version immutability, optimistic concurrency, history pagination, generation quotas and invalid provider output. Live checks verified the real Lambda/DynamoDB path, custom-domain delivery and private history. Qwen was tested before migration; a new paid generation was not needed for this cutover. Browser PDF exports of all three baselines were inspected. Browser print settings can affect pagination; disable browser headers/footers and use the stylesheet's A4 sizing.

CloudFormation service validation passed. Local `cfn-lint` and `cfn-guard` were unavailable and were not installed; their schema/compliance checks were not run. No external security audit or load test was performed. Private CV history has no automatic deletion; session/quota rows expire using DynamoDB TTL. Retention on stack deletion preserves records but is not a backup against accidental record deletion; export important CVs locally.
