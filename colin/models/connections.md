---
name: Airflow Connection to Prefect Block Mappings
colin:
  output:
    format: json
---

{% section postgres %}
## connection_pattern
postgres_default, postgres_*

## block_type
SqlAlchemyConnector

## package
prefect-sqlalchemy

## config_guidance
Create a SqlAlchemyConnector block with the PostgreSQL connection URI. Install `prefect-sqlalchemy` and register the block type with `prefect block register -m prefect_sqlalchemy`.

## example
```python
from prefect_sqlalchemy import SqlAlchemyConnector, ConnectionComponents, SyncDriver

connector = SqlAlchemyConnector(
    connection_info=ConnectionComponents(
        driver=SyncDriver.POSTGRESQL_PSYCOPG2,
        host="localhost",
        port=5432,
        database="mydb",
        username="user",
        password="pass",
    )
)
connector.save("postgres-default")

# Usage in flow
connector = SqlAlchemyConnector.load("postgres-default")
with connector.get_connection() as conn:
    result = conn.execute(text("SELECT 1"))
```
{% endsection %}

{% section mysql %}
## connection_pattern
mysql_default, mysql_*

## block_type
SqlAlchemyConnector

## package
prefect-sqlalchemy

## config_guidance
Use SqlAlchemyConnector with MySQL driver. Install `prefect-sqlalchemy` with mysql extras.

## example
```python
from prefect_sqlalchemy import SqlAlchemyConnector, ConnectionComponents, SyncDriver

connector = SqlAlchemyConnector(
    connection_info=ConnectionComponents(
        driver=SyncDriver.MYSQL_PYMYSQL,
        host="localhost",
        port=3306,
        database="mydb",
        username="user",
        password="pass",
    )
)
connector.save("mysql-default")
```
{% endsection %}

{% section aws %}
## connection_pattern
aws_default, aws_*

## block_type
AwsCredentials

## package
prefect-aws

## config_guidance
Create an AwsCredentials block with access key and secret. For IAM roles, leave credentials empty and configure instance profile.

## example
```python
from prefect_aws import AwsCredentials

creds = AwsCredentials(
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    region_name="us-east-1",
)
creds.save("aws-default")

# Usage
creds = AwsCredentials.load("aws-default")
s3_client = creds.get_boto3_session().client("s3")
```
{% endsection %}

{% section s3 %}
## connection_pattern
s3_*, aws_s3_*

## block_type
S3Bucket

## package
prefect-aws

## config_guidance
Create an S3Bucket block referencing an AwsCredentials block. Provides read/write/list operations.

## example
```python
from prefect_aws import S3Bucket, AwsCredentials

creds = AwsCredentials.load("aws-default")
bucket = S3Bucket(bucket_name="my-bucket", credentials=creds)
bucket.save("my-s3-bucket")

# Usage
bucket = S3Bucket.load("my-s3-bucket")
bucket.upload_from_path("local.csv", "remote/path.csv")
```
{% endsection %}

{% section gcp %}
## connection_pattern
google_cloud_default, gcp_*

## block_type
GcpCredentials

## package
prefect-gcp

## config_guidance
Create a GcpCredentials block with service account JSON or use application default credentials.

## example
```python
from prefect_gcp import GcpCredentials

creds = GcpCredentials(service_account_file="/path/to/sa.json")
creds.save("gcp-default")

# Usage
creds = GcpCredentials.load("gcp-default")
client = creds.get_client()
```
{% endsection %}

{% section gcs %}
## connection_pattern
gcs_*, google_cloud_storage_*

## block_type
GcsBucket

## package
prefect-gcp

## config_guidance
Create a GcsBucket block referencing a GcpCredentials block.

## example
```python
from prefect_gcp import GcsBucket, GcpCredentials

creds = GcpCredentials.load("gcp-default")
bucket = GcsBucket(bucket="my-bucket", gcp_credentials=creds)
bucket.save("my-gcs-bucket")
```
{% endsection %}

{% section bigquery %}
## connection_pattern
bigquery_default, google_cloud_bigquery_*

## block_type
BigQueryWarehouse

## package
prefect-gcp

## config_guidance
Create a BigQueryWarehouse block referencing GcpCredentials. Provides query execution and data loading.

## example
```python
from prefect_gcp import BigQueryWarehouse, GcpCredentials

creds = GcpCredentials.load("gcp-default")
bq = BigQueryWarehouse(gcp_credentials=creds)
bq.save("bigquery-default")

# Usage
bq = BigQueryWarehouse.load("bigquery-default")
results = bq.fetch_many("SELECT * FROM dataset.table LIMIT 10")
```
{% endsection %}

{% section azure %}
## connection_pattern
azure_*, wasb_*

## block_type
AzureBlobStorageCredentials

## package
prefect-azure

## config_guidance
Create an AzureBlobStorageCredentials block with connection string or SAS token.

## example
```python
from prefect_azure import AzureBlobStorageCredentials

creds = AzureBlobStorageCredentials(connection_string="DefaultEndpointsProtocol=...")
creds.save("azure-default")
```
{% endsection %}

{% section databricks %}
## connection_pattern
databricks_default, databricks_*

## block_type
DatabricksCredentials

## package
prefect-databricks

## config_guidance
Create a DatabricksCredentials block with host URL and token. Use for job submission and workspace operations.

## example
```python
from prefect_databricks import DatabricksCredentials

creds = DatabricksCredentials(
    databricks_instance="https://myworkspace.cloud.databricks.com",
    token="dapi...",
)
creds.save("databricks-default")
```
{% endsection %}

{% section snowflake %}
## connection_pattern
snowflake_default, snowflake_*

## block_type
SnowflakeConnector

## package
prefect-snowflake

## config_guidance
Create a SnowflakeConnector block with account, user, password, and warehouse. Supports key-pair auth.

## example
```python
from prefect_snowflake import SnowflakeConnector, SnowflakeCredentials

creds = SnowflakeCredentials(
    account="myaccount",
    user="myuser",
    password="mypassword",
)
connector = SnowflakeConnector(
    credentials=creds,
    database="mydb",
    schema="public",
    warehouse="compute_wh",
)
connector.save("snowflake-default")

# Usage
connector = SnowflakeConnector.load("snowflake-default")
results = connector.fetch_many("SELECT * FROM table")
```
{% endsection %}

{% section ssh %}
## connection_pattern
ssh_default, ssh_*

## block_type
RemoteFileSystem or subprocess

## package
prefect (core)

## config_guidance
No dedicated SSH block. Use `paramiko` or `fabric` in a task, or RemoteFileSystem for file operations.

## example
```python
@task
def run_remote(host: str, command: str):
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host)
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode()
```
{% endsection %}

{% section http %}
## connection_pattern
http_default, http_*

## block_type
No dedicated block — use httpx or requests in a task

## package
prefect (core)

## config_guidance
Store base URL and auth in a Secret or JSON block. Use httpx/requests in tasks.

## example
```python
from prefect import task
from prefect.blocks.system import Secret
import httpx

@task
def call_api(endpoint: str):
    token = Secret.load("api-token").get()
    resp = httpx.get(endpoint, headers={"Authorization": f"Bearer {token}"})
    return resp.json()
```
{% endsection %}

{% section slack %}
## connection_pattern
slack_default, slack_*

## block_type
SlackWebhook

## package
prefect-slack

## config_guidance
Create a SlackWebhook block with the webhook URL. Use for notifications.

## example
```python
from prefect_slack import SlackWebhook

webhook = SlackWebhook(url="https://hooks.slack.com/services/...")
webhook.save("slack-alerts")

# Usage
webhook = SlackWebhook.load("slack-alerts")
webhook.notify("Pipeline completed successfully")
```
{% endsection %}

{% section dbt %}
## connection_pattern
dbt_cloud_*, dbt_*

## block_type
DbtCloudCredentials or DbtCoreOperation

## package
prefect-dbt

## config_guidance
For dbt Cloud: create DbtCloudCredentials with API key. For dbt Core: use DbtCoreOperation to run dbt commands.

## example
```python
# dbt Cloud
from prefect_dbt.cloud import DbtCloudCredentials
creds = DbtCloudCredentials(api_key="...", account_id=12345)
creds.save("dbt-cloud")

# dbt Core
from prefect_dbt.cli import DbtCoreOperation
dbt = DbtCoreOperation(
    commands=["dbt run --select my_model"],
    project_dir="/path/to/dbt",
)
dbt.save("dbt-run")
```
{% endsection %}

{% section email %}
## connection_pattern
smtp_default, email_*

## block_type
EmailServerCredentials

## package
prefect-email

## config_guidance
Create an EmailServerCredentials block with SMTP server details.

## example
```python
from prefect_email import EmailServerCredentials, email_send_message

creds = EmailServerCredentials(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="user@gmail.com",
    password="app-password",
)
creds.save("email-default")
```
{% endsection %}

{% section redis %}
## connection_pattern
redis_default, redis_*

## block_type
No dedicated block — use redis-py in a task

## package
prefect (core)

## config_guidance
Store connection URL in a Secret block. Use `redis` package directly in tasks.

## example
```python
from prefect import task
from prefect.blocks.system import Secret
import redis

@task
def get_from_cache(key: str):
    url = Secret.load("redis-url").get()
    r = redis.from_url(url)
    return r.get(key)
```
{% endsection %}

{% section mongo %}
## connection_pattern
mongo_default, mongodb_*

## block_type
MongoDb

## package
prefect-mongo (community)

## config_guidance
Use `pymongo` directly in tasks. Store connection string in a Secret block.

## example
```python
from prefect import task
from prefect.blocks.system import Secret
from pymongo import MongoClient

@task
def query_mongo(collection: str, query: dict):
    uri = Secret.load("mongo-uri").get()
    client = MongoClient(uri)
    return list(client.mydb[collection].find(query))
```
{% endsection %}
