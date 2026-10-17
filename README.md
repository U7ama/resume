# Resume Studio

Live site: https://resume.usamaaslam.site/

Three independently editable CVs: software engineering (`resume.md`), academic study (`academic.md`), and general applications (`general.md`). The original software CV is preserved. The academic baseline uses the supplied BSCS transcript and English-medium certificate; scans, identity records, private study plans and referee contact details are not published.

Choose a type, open **AI Studio**, and enter the code in `.private/access-code.txt`. Ask Qwen to tailor the current draft, review the proposal, and choose **Use draft in editor**. **Save version to cloud** creates an immutable private revision. History can load an earlier revision as a draft; saving it creates another revision. **Download / Print PDF** exports the current preview through the browser's Save as PDF option. Markdown export is also available. Private saves do not publish or replace public templates.

Browser drafts are stored separately by CV type. Locking the workspace revokes its server session but keeps the local browser draft. Use a trusted device. Sessions expire after eight hours. Login permits five attempts per IP per 15 minutes, with a global limit of 30. AI generation permits ten attempts per UTC day and 100 per UTC month, including failed attempts, with a 6,000-output-token limit and no automatic retries or provider fallback. These application limits do not establish the provider's free-quota balance.

## Architecture and costs

The application and its assets run in an ARM64 Python Lambda. DynamoDB Standard stores CV revisions, session hashes and quota counters, with 5 provisioned read units and 10 write units. SQLite is used only for local development/tests. Qwen uses DeviceOps' configured model and international OpenAI-compatible endpoint, with thinking disabled. Its API key stays in a private, AES256-encrypted S3 configuration object. The browser never receives it.

CloudFront provides HTTPS for the custom domain, caches only allowlisted public assets and forwards private API requests without caching. Its origin access control signs requests to an IAM-only Lambda alias URL; private operations also require the owner's session. Cloudflare manages DNS only. The previous Worker is retained without a domain binding for recovery. Minimal CloudFront access logs expire after seven days and exclude IP addresses, query strings, cookies and request bodies. No EC2 instance, RDS database, NAT gateway, API Gateway, paid WAF or Shield Advanced plan was created.

This is configured for low personal usage within the recurring [Lambda](https://aws.amazon.com/lambda/pricing/), [DynamoDB](https://aws.amazon.com/dynamodb/pricing/) and pay-as-you-go [CloudFront](https://aws.amazon.com/cloudfront/pricing/) allowances. Allowances are shared with other applications in the account. S3 configuration, deployment packages and short-retention logs can incur small storage/request charges if not covered by the account's current benefits; [S3 pricing](https://aws.amazon.com/s3/pricing/) is separate. Qwen billing/free quota is also separate. This setup is **not a guaranteed $0 bill or an account spending cap**. No fixed-price plan was selected.

## Local development

Python 3.10+ and Node.js are enough for local development; no Python packages are required for SQLite tests. Lambda supplies boto3 in its Python runtime.

Print layouts use the bundled Resume Print font (Carlito derivative) to keep text metrics consistent across desktop and mobile. Font sources and the SIL Open Font License are in `assets/fonts/`. After changing those files, regenerate the embedded CSS with `python3 scripts/embed-print-fonts.py`. The Print PDF button waits for both font weights before opening the print preview.

All CV types share the same print spacing. A compact spacing fallback is selected only when the content exceeds the A4 printable height; it preserves the font size and page margins. Measurement temporarily applies the print rules at the A4 content width because Chromium fires `beforeprint` before its print media query changes. The temporary rules and width are restored immediately, and compact spacing is cleared after printing.

```sh
python3 scripts/prepare-runtime.py --qwen-env /path/to/private/DeviceOps.env --origin http://localhost:4081
python3 scripts/studio-dev.py --port 4081
```

Only selected Qwen settings are copied. DeviceOps configuration is not modified. Private configuration, code, SQLite data, provider responses and build artifacts are Git-ignored. Never run a general directory-serving HTTP server in this checkout: use the allowlisted preview server above.

```sh
python3 -m unittest discover -s backend -v
node --test scripts/portfolio-content.test.mjs scripts/photo-preference.test.mjs scripts/print-readiness.test.mjs scripts/studio-history.test.mjs infra/cloudfront-viewer.test.mjs infra/proxy.test.mjs
node scripts/validate-content.mjs
node --check studio.js
node --check infra/proxy.mjs
git diff --check
```

See [DEPLOY.md](DEPLOY.md) for deployment and verification.
