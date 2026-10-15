"""SQLite for local development; DynamoDB for durable AWS records."""
import json
import sqlite3
import time
from contextlib import contextmanager


class Conflict(Exception):
    pass


class Limited(Exception):
    pass


class SQLiteStore:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS records (pk TEXT, sk TEXT, data TEXT, PRIMARY KEY (pk, sk))')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, pk, sk='record'):
        with self.connect() as db:
            row = db.execute('SELECT data FROM records WHERE pk=? AND sk=?', (pk, sk)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, pk, value, sk='record'):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO records VALUES (?, ?, ?)', (pk, sk, json.dumps(value)))

    def delete(self, pk, sk='record'):
        with self.connect() as db:
            db.execute('DELETE FROM records WHERE pk=? AND sk=?', (pk, sk))

    def consume(self, key, limit, ttl):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM records WHERE pk=? AND sk=?', (key, 'record')).fetchone()
            value = json.loads(row[0]) if row else {'count': 0}
            if value['count'] >= limit:
                raise Limited()
            value = {'count': value['count'] + 1, 'ttl': ttl}
            db.execute('INSERT OR REPLACE INTO records VALUES (?, ?, ?)', (key, 'record', json.dumps(value)))
            db.execute("DELETE FROM records WHERE json_extract(data, '$.ttl') < ?", (int(time.time()),))

    def save(self, kind, version, base_id):
        pk = f'cv#{kind}'
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM records WHERE pk=? AND sk=?', (pk, 'current')).fetchone()
            current = json.loads(row[0]) if row else None
            if (current or {}).get('id') != base_id:
                raise Conflict()
            db.execute('INSERT INTO records VALUES (?, ?, ?)', (pk, version['id'], json.dumps(version)))
            db.execute('INSERT OR REPLACE INTO records VALUES (?, ?, ?)', (pk, 'current', json.dumps(version)))

    def versions(self, kind, cursor=None):
        with self.connect() as db:
            rows = db.execute('SELECT sk, data FROM records WHERE pk=? AND sk LIKE ? AND sk < ? ORDER BY sk DESC LIMIT 21',
                              (f'cv#{kind}', 'v#%', cursor or 'z')).fetchall()
        return [json.loads(row[1]) for row in rows[:20]], rows[19][0] if len(rows) > 20 else None


class DynamoStore:
    def __init__(self, table_name):
        import boto3
        from botocore.config import Config
        self.table_name = table_name
        self.resource = boto3.resource('dynamodb', config=Config(retries={'mode': 'standard', 'total_max_attempts': 3}))
        self.table = self.resource.Table(table_name)

    def get(self, pk, sk='record'):
        return self.table.get_item(Key={'pk': pk, 'sk': sk}, ConsistentRead=True).get('Item')

    def put(self, pk, value, sk='record'):
        self.table.put_item(Item={**value, 'pk': pk, 'sk': sk})

    def delete(self, pk, sk='record'):
        self.table.delete_item(Key={'pk': pk, 'sk': sk})

    def consume(self, key, limit, ttl):
        from boto3.dynamodb.conditions import Attr
        try:
            self.table.update_item(Key={'pk': key, 'sk': 'record'},
                UpdateExpression='SET #count = if_not_exists(#count, :zero) + :one, #ttl = :ttl',
                ExpressionAttributeNames={'#count': 'count', '#ttl': 'ttl'},
                ExpressionAttributeValues={':zero': 0, ':one': 1, ':ttl': ttl},
                ConditionExpression=Attr('count').not_exists() | Attr('count').lt(limit))
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            raise Limited() from None

    def save(self, kind, version, base_id):
        current = {'TableName': self.table_name, 'Item': {**version, 'pk': f'cv#{kind}', 'sk': 'current'}}
        if base_id is None:
            current['ConditionExpression'] = 'attribute_not_exists(pk)'
        else:
            current.update(ConditionExpression='id = :base', ExpressionAttributeValues={':base': base_id})
        try:
            self.resource.meta.client.transact_write_items(TransactItems=[
                {'Put': current},
                {'Put': {'TableName': self.table_name, 'Item': {**version, 'pk': f'cv#{kind}', 'sk': version['id']},
                         'ConditionExpression': 'attribute_not_exists(pk)'}},
            ])
        except self.table.meta.client.exceptions.TransactionCanceledException as error:
            if any(reason.get('Code') == 'ConditionalCheckFailed' for reason in error.response.get('CancellationReasons', [])):
                raise Conflict() from None
            raise

    def versions(self, kind, cursor=None):
        from boto3.dynamodb.conditions import Key
        args = dict(KeyConditionExpression=Key('pk').eq(f'cv#{kind}') & Key('sk').begins_with('v#'),
                    ScanIndexForward=False, ConsistentRead=True, Limit=20)
        if cursor:
            args['ExclusiveStartKey'] = {'pk': f'cv#{kind}', 'sk': cursor}
        response = self.table.query(**args)
        return response.get('Items', []), response.get('LastEvaluatedKey', {}).get('sk')
