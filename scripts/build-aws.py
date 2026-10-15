"""Build an allowlisted Lambda package and a reproducible CloudFormation template."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

FILES = ['index.html', 'studio.js', 'studio.css', 'resume.md', 'academic.md', 'general.md',
         'Usama DP.jpeg', 'Usama DP headshot.jpeg', 'robots.txt', 'sitemap.xml']


def ref(name):
    return {'Ref': name}


def sub(value):
    return {'Fn::Sub': value}


def attr(name, key):
    return {'Fn::GetAtt': [name, key]}


def template(bucket, code_key):
    return {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Description': 'Resume Studio AWS origin: CV app, private version history and bounded Qwen generation. Cloudflare provides HTTPS routing.',
        'Metadata': {'com.aws.cloudformation.Context': {
            'Purpose': 'Personal CV workspace',
            'Database': 'DynamoDB Standard provisioned 5 RCU/10 WCU; immutable revisions; retained on deletion',
            'Secrets': 'Private encrypted S3 runtime configuration, readable only by the Lambda role',
            'Origin': 'Lambda Function URL with an application-verified shared secret from the Cloudflare proxy',
            'Cost': 'Shared monthly Lambda/DynamoDB allowances; tiny S3 deployment/configuration storage and request costs may remain. No always-on compute.'}},
        'Resources': {
            'History': {'Type': 'AWS::DynamoDB::Table', 'DeletionPolicy': 'Retain', 'UpdateReplacePolicy': 'Retain', 'Properties': {
                'AttributeDefinitions': [{'AttributeName': key, 'AttributeType': 'S'} for key in ['pk', 'sk']],
                'KeySchema': [{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
                'BillingMode': 'PROVISIONED', 'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 10},
                'SSESpecification': {'SSEEnabled': True}, 'TimeToLiveSpecification': {'AttributeName': 'ttl', 'Enabled': True},
                'Tags': [{'Key': 'Project', 'Value': 'resume-studio'}]}},
            'ExecutionRole': {'Type': 'AWS::IAM::Role', 'Properties': {
                'AssumeRolePolicyDocument': {'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Principal': {'Service': 'lambda.amazonaws.com'}, 'Action': 'sts:AssumeRole'}]},
                'Policies': [{'PolicyName': 'ResumeRecords', 'PolicyDocument': {'Version': '2012-10-17', 'Statement': [
                    {'Effect': 'Allow', 'Action': ['dynamodb:GetItem', 'dynamodb:PutItem', 'dynamodb:UpdateItem', 'dynamodb:DeleteItem', 'dynamodb:Query', 'dynamodb:TransactWriteItems'], 'Resource': attr('History', 'Arn')},
                    {'Effect': 'Allow', 'Action': 's3:GetObject', 'Resource': f'arn:aws:s3:::{bucket}/private/runtime.json'},
                    {'Effect': 'Allow', 'Action': ['logs:CreateLogStream', 'logs:PutLogEvents'], 'Resource': sub('arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-api:*')},
                ]}}]}},
            'ApiLogs': {'Type': 'AWS::Logs::LogGroup', 'Properties': {'LogGroupName': sub('/aws/lambda/${AWS::StackName}-api'), 'RetentionInDays': 7}},
            'Api': {'Type': 'AWS::Lambda::Function', 'DependsOn': 'ApiLogs', 'Properties': {
                'FunctionName': sub('${AWS::StackName}-api'), 'Runtime': 'python3.13', 'Handler': 'app.handler',
                'Role': attr('ExecutionRole', 'Arn'), 'MemorySize': 256, 'Timeout': 65, 'Architectures': ['arm64'],
                'Code': {'S3Bucket': bucket, 'S3Key': code_key},
                'Environment': {'Variables': {'TABLE_NAME': ref('History'), 'CONFIG_BUCKET': bucket}},
                'Tags': [{'Key': 'Project', 'Value': 'resume-studio'}]}},
            'ApiUrl': {'Type': 'AWS::Lambda::Url', 'Properties': {'TargetFunctionArn': ref('Api'), 'AuthType': 'NONE'}},
            'AllowUrl': {'Type': 'AWS::Lambda::Permission', 'Properties': {
                'FunctionName': ref('Api'), 'Action': 'lambda:InvokeFunctionUrl', 'Principal': '*', 'FunctionUrlAuthType': 'NONE'}},
            'AllowInvoke': {'Type': 'AWS::Lambda::Permission', 'Properties': {
                'FunctionName': ref('Api'), 'Action': 'lambda:InvokeFunction', 'Principal': '*', 'InvokedViaFunctionUrl': True}},
        },
        'Outputs': {
            'OriginUrl': {'Description': 'AWS origin (requires the private proxy header)', 'Value': attr('ApiUrl', 'FunctionUrl')},
            'HistoryTable': {'Description': 'Retained private CV version history', 'Value': ref('History')},
            'ApiFunction': {'Description': 'Application function name', 'Value': ref('Api')},
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / 'output/aws'
    output.mkdir(parents=True, exist_ok=True)
    package = output / 'api.zip'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ['app.py', 'store.py']:
            archive.write(root / 'backend' / name, name)
        for name in FILES:
            archive.write(root / name, 'public/' + name)
    code_key = 'deploy/api-' + hashlib.sha256(package.read_bytes()).hexdigest()[:20] + '.zip'
    deployment = template(args.bucket, code_key)
    (root / 'infra').mkdir(exist_ok=True)
    (root / 'infra/template.json').write_text(json.dumps(deployment, indent=2) + '\n')
    (output / 'upload-manifest.json').write_text(json.dumps([{'path': str(package), 'key': code_key}] +
        [{'path': str(root / name), 'key': 'public/' + name} for name in FILES] +
        [{'path': str(root / '.private/runtime.json'), 'key': 'private/runtime.json'}], indent=2))
    print(f'Built API package ({package.stat().st_size} bytes), infrastructure and allowlisted upload manifest.')


if __name__ == '__main__':
    main()
