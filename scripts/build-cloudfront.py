"""Build the separate CloudFront edge stack without embedding credentials."""
import argparse
import json
from pathlib import Path


def ref(name): return {'Ref': name}
def attr(name, key): return {'Fn::GetAtt': [name, key]}
def sub(value): return {'Fn::Sub': value}
def resource(kind, properties, why, must, **extra):
    return {'Type': kind, 'Properties': properties,
            'Metadata': {'com.aws.cloudformation.Context': {'why': why, 'must': must}}, **extra}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--origin-url', required=True)
    p.add_argument('--alias-arn', required=True)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    state = json.loads((root / 'infra/cloudfront-state.json').read_text())
    origin = a.origin_url.removeprefix('https://').rstrip('/')
    r = {}
    r['OriginAccess'] = resource('AWS::CloudFront::OriginAccessControl', {'OriginAccessControlConfig': {
        'Name': sub('${AWS::StackName}-lambda'), 'OriginAccessControlOriginType': 'lambda',
        'SigningBehavior': 'always', 'SigningProtocol': 'sigv4'}}, 'IAM-signed Lambda origin access.', ['Never expose an unsigned origin.'])
    r['ViewerRequest'] = resource('AWS::CloudFront::Function', {
        'Name': sub('${AWS::StackName}-viewer'), 'AutoPublish': True,
        'FunctionConfig': {'Comment': 'Preserve allowlist, request-size guard, and trusted client IP.', 'Runtime': 'cloudfront-js-2.0'},
        'FunctionCode': (root / 'infra/cloudfront-viewer.js').read_text()}, 'Retain existing edge validation and rate-limit identity.', ['Overwrite client IP from event.viewer.ip; never trust viewer-supplied identity.'])
    r['PublicCache'] = resource('AWS::CloudFront::CachePolicy', {'CachePolicyConfig': {
        'Name': sub('${AWS::StackName}-public'), 'DefaultTTL': 300, 'MaxTTL': 3600, 'MinTTL': 0,
        'ParametersInCacheKeyAndForwardedToOrigin': {'EnableAcceptEncodingGzip': True, 'EnableAcceptEncodingBrotli': True,
            'HeadersConfig': {'HeaderBehavior': 'none'}, 'CookiesConfig': {'CookieBehavior': 'none'},
            'QueryStringsConfig': {'QueryStringBehavior': 'whitelist', 'QueryStrings': ['v']}}}},
        'Cache public assets by release query without forwarding the viewer Host to Lambda.', ['Minimum TTL zero; private API has separate disabled caching.'])
    csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data: blob:; connect-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'"
    r['SecurityHeaders'] = resource('AWS::CloudFront::ResponseHeadersPolicy', {'ResponseHeadersPolicyConfig': {
        'Name': sub('${AWS::StackName}-security'), 'SecurityHeadersConfig': {
            'ContentSecurityPolicy': {'ContentSecurityPolicy': csp, 'Override': True},
            'StrictTransportSecurity': {'AccessControlMaxAgeSec': 31536000, 'Override': True},
            'ContentTypeOptions': {'Override': True}, 'FrameOptions': {'FrameOption': 'DENY', 'Override': True},
            'ReferrerPolicy': {'ReferrerPolicy': 'same-origin', 'Override': True}}}},
        'Keep HTTPS and browser security headers while allowing bundled print fonts.', ['Keep font-src data: for the licensed embedded print font.'])
    function = {'EventType': 'viewer-request', 'FunctionARN': attr('ViewerRequest', 'FunctionMetadata.FunctionARN')}
    base = {'TargetOriginId': 'lambda', 'ViewerProtocolPolicy': 'redirect-to-https', 'Compress': True,
            'FunctionAssociations': [function], 'ResponseHeadersPolicyId': ref('SecurityHeaders')}
    public = {**base, 'AllowedMethods': ['GET', 'HEAD'], 'CachedMethods': ['GET', 'HEAD'], 'CachePolicyId': ref('PublicCache')}
    private = {**base, 'PathPattern': '/api/*', 'AllowedMethods': ['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST', 'PATCH', 'DELETE'],
               'CachedMethods': ['GET', 'HEAD'], 'CachePolicyId': state['cache_disabled_policy_id'],
               'OriginRequestPolicyId': state['origin_request_policy_id']}
    r['Distribution'] = resource('AWS::CloudFront::Distribution', {'DistributionConfig': {
        'Comment': 'Personal Resume Studio', 'Enabled': True, 'IPV6Enabled': True,
        'Aliases': ['resume.usamaaslam.site'], 'HttpVersion': 'http2and3', 'PriceClass': 'PriceClass_100',
        'Origins': [{'Id': 'lambda', 'DomainName': origin, 'OriginAccessControlId': ref('OriginAccess'),
                     'CustomOriginConfig': {'OriginProtocolPolicy': 'https-only', 'OriginSSLProtocols': ['TLSv1.2'],
                                            'OriginReadTimeout': 75}}],
        'DefaultCacheBehavior': public, 'CacheBehaviors': [private],
        'CustomErrorResponses': [{'ErrorCode': code, 'ErrorCachingMinTTL': 0} for code in [400, 403, 404, 405, 414, 416, 500, 501, 502, 503, 504]],
        'ViewerCertificate': {'AcmCertificateArn': state['certificate_arn'], 'SslSupportMethod': 'sni-only', 'MinimumProtocolVersion': 'TLSv1.2_2025'}},
        'Tags': [{'Key': 'Project', 'Value': 'resume-studio'}]}, 'AWS HTTPS delivery replacing the temporary Worker.',
        ['Test before DNS cutover; retain /api no-cache, HTTPS origin, OAC and custom certificate.'])
    for suffix, action, extras in [('Url', 'lambda:InvokeFunctionUrl', {'FunctionUrlAuthType': 'AWS_IAM'}),
                                    ('Invoke', 'lambda:InvokeFunction', {'InvokedViaFunctionUrl': True})]:
        r['Allow' + suffix] = resource('AWS::Lambda::Permission', {'FunctionName': a.alias_arn, 'Action': action,
            'Principal': 'cloudfront.amazonaws.com', 'SourceArn': sub('arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${Distribution}'), **extras},
            'Grant only this distribution access to the IAM Lambda alias.', ['Keep exact SourceArn; no public principal.'])
    r['LogsBucket'] = resource('AWS::S3::Bucket', {
        'PublicAccessBlockConfiguration': {k: True for k in ['BlockPublicAcls', 'BlockPublicPolicy', 'IgnorePublicAcls', 'RestrictPublicBuckets']},
        'BucketEncryption': {'ServerSideEncryptionConfiguration': [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]},
        'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]},
        'VersioningConfiguration': {'Status': 'Enabled'},
        'LifecycleConfiguration': {'Rules': [{'Id': 'short-retention', 'Status': 'Enabled', 'ExpirationInDays': 7,
            'NoncurrentVersionExpiration': {'NoncurrentDays': 7}, 'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 1}},
            {'Id': 'delete-markers', 'Status': 'Enabled', 'ExpiredObjectDeleteMarker': True}]}},
        'Private encrypted standard logs with short retention.', ['No public access; expire logs after seven days.'], DeletionPolicy='Retain', UpdateReplacePolicy='Retain')
    r['LogSource'] = resource('AWS::Logs::DeliverySource', {'Name': sub('${AWS::StackName}-access'), 'LogType': 'ACCESS_LOGS',
        'ResourceArn': sub('arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${Distribution}')},
        'Standard access logging for edge errors and cache behavior.', ['No request bodies or cookies in selected fields.'])
    r['LogsPolicy'] = resource('AWS::S3::BucketPolicy', {'Bucket': ref('LogsBucket'), 'PolicyDocument': {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Deny', 'Principal': '*', 'Action': 's3:*', 'Resource': [attr('LogsBucket', 'Arn'), sub('${LogsBucket.Arn}/*')], 'Condition': {'Bool': {'aws:SecureTransport': 'false'}}},
        {'Effect': 'Allow', 'Principal': {'Service': 'delivery.logs.amazonaws.com'}, 'Action': ['s3:GetBucketAcl'], 'Resource': attr('LogsBucket', 'Arn'),
         'Condition': {'StringEquals': {'aws:SourceAccount': ref('AWS::AccountId')}, 'ArnLike': {'aws:SourceArn': attr('LogSource', 'Arn')}}},
        {'Effect': 'Allow', 'Principal': {'Service': 'delivery.logs.amazonaws.com'}, 'Action': ['s3:PutObject'], 'Resource': sub('${LogsBucket.Arn}/*'),
         'Condition': {'StringEquals': {'aws:SourceAccount': ref('AWS::AccountId'), 's3:x-amz-acl': 'bucket-owner-full-control'}, 'ArnLike': {'aws:SourceArn': attr('LogSource', 'Arn')}}}]}},
        'Allow scoped log delivery and deny unencrypted transport.', ['Only this account delivery source may write logs.'])
    r['LogDestination'] = resource('AWS::Logs::DeliveryDestination', {'Name': sub('${AWS::StackName}-s3'),
        'DestinationResourceArn': attr('LogsBucket', 'Arn'), 'OutputFormat': 'json'},
        'Encrypted S3 destination avoids a paid KMS key or real-time stream.', ['Keep destination private.'], DependsOn='LogsPolicy')
    r['LogDelivery'] = resource('AWS::Logs::Delivery', {'DeliveryDestinationArn': attr('LogDestination', 'Arn'),
        'DeliverySourceName': sub('${AWS::StackName}-access'),
        'RecordFields': ['date', 'time', 'cs-method', 'cs-uri-stem', 'sc-status', 'x-edge-result-type', 'time-taken'],
        'S3SuffixPath': '/access/{yyyy}/{MM}/{dd}/{HH}'},
        'Deliver minimal diagnostic fields without query strings or cookies.', ['Exclude sensitive request data.'], DependsOn='LogSource')
    template = {'AWSTemplateFormatVersion': '2010-09-09', 'Description': 'Resume Studio secure CloudFront delivery and short-retention private access logs.',
        'Metadata': {'AWSToolsMetrics': {'AWSAgentToolkit': 'aws-cloudformation@3'}, 'com.aws.cloudformation.Context': {
            'Purpose': 'Move resume.usamaaslam.site from a temporary Worker to CloudFront.',
            'Cost': 'Pay-as-you-go recurring monthly CloudFront allowances; no paid WAF, Shield Advanced, real-time logging, or KMS key. S3 log storage remains usage-based.',
            'Safety': 'Separate IAM origin alias permits testing before DNS cutover. Existing CV database and history remain untouched.'}},
        'Resources': r, 'Outputs': {'DistributionId': {'Value': ref('Distribution')}, 'DistributionDomain': {'Value': attr('Distribution', 'DomainName')},
            'DistributionArn': {'Value': sub('arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${Distribution}')}}}
    path = root / 'infra/cloudfront-template.json'
    path.write_text(json.dumps(template, indent=2) + '\n')
    print(f'Built CloudFront template ({path.stat().st_size} bytes).')


if __name__ == '__main__': main()
