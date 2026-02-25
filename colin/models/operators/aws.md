---
name: AWS Provider Operator Mappings
colin:
  output:
    format: json
---

{% section S3CreateObjectOperator %}
## operator
S3CreateObjectOperator

## module
airflow.providers.amazon.aws.operators.s3

## source_context
Creates an object in S3 with provided data. Uses boto3 `put_object`.

## prefect_pattern
S3Bucket.upload_from_path or write_path

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import S3Bucket

## example
### before
```python
upload = S3CreateObjectOperator(
    task_id="upload",
    s3_bucket="my-bucket",
    s3_key="output/data.json",
    data='{"result": "ok"}',
)
```
### after
```python
from prefect_aws import S3Bucket

@task
def upload(key: str, data: str):
    bucket = S3Bucket.load("my-bucket")
    bucket.write_path(key, content=data.encode())
```

## notes
- For file uploads, use upload_from_path
- For in-memory data, use write_path
{% endsection %}

{% section S3CopyObjectOperator %}
## operator
S3CopyObjectOperator

## module
airflow.providers.amazon.aws.operators.s3

## source_context
Copies an S3 object from one key to another. Uses boto3 `copy_object`.

## prefect_pattern
S3Bucket.copy_object or boto3 directly

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import S3Bucket

## example
### before
```python
copy = S3CopyObjectOperator(
    task_id="copy",
    source_bucket_key="s3://src/data.csv",
    dest_bucket_key="s3://dst/data.csv",
)
```
### after
```python
from prefect_aws import S3Bucket

@task
def copy_s3(source_key: str, dest_key: str):
    bucket = S3Bucket.load("my-bucket")
    bucket.copy_object(source_path=source_key, to_path=dest_key)
```
{% endsection %}

{% section S3DeleteObjectsOperator %}
## operator
S3DeleteObjectsOperator

## module
airflow.providers.amazon.aws.operators.s3

## source_context
Deletes objects from S3. Supports single key or list of keys.

## prefect_pattern
boto3 delete_objects via AwsCredentials

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import AwsCredentials

## example
### before
```python
delete = S3DeleteObjectsOperator(
    task_id="cleanup",
    bucket="my-bucket",
    keys=["tmp/file1.csv", "tmp/file2.csv"],
)
```
### after
```python
from prefect_aws import AwsCredentials

@task
def cleanup_s3(bucket: str, keys: list[str]):
    creds = AwsCredentials.load("aws-default")
    s3 = creds.get_boto3_session().client("s3")
    s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": k} for k in keys]})
```
{% endsection %}

{% section LambdaInvokeFunctionOperator %}
## operator
LambdaInvokeFunctionOperator

## module
airflow.providers.amazon.aws.operators.lambda_function

## source_context
Invokes an AWS Lambda function. Supports sync and async invocation.

## prefect_pattern
boto3 Lambda invoke via AwsCredentials

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import AwsCredentials

## example
### before
```python
invoke = LambdaInvokeFunctionOperator(
    task_id="invoke_lambda",
    function_name="my-function",
    payload='{"key": "value"}',
)
```
### after
```python
import json
from prefect_aws import AwsCredentials

@task
def invoke_lambda(function_name: str, payload: dict):
    creds = AwsCredentials.load("aws-default")
    client = creds.get_boto3_session().client("lambda")
    response = client.invoke(
        FunctionName=function_name,
        Payload=json.dumps(payload),
    )
    return json.loads(response["Payload"].read())
```
{% endsection %}

{% section GlueJobOperator %}
## operator
GlueJobOperator

## module
airflow.providers.amazon.aws.operators.glue

## source_context
Starts and monitors an AWS Glue ETL job. Waits for completion by default.

## prefect_pattern
boto3 Glue start_job_run via AwsCredentials

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import AwsCredentials

## example
### before
```python
glue = GlueJobOperator(
    task_id="run_glue",
    job_name="my-etl-job",
    script_args={"--input": "s3://bucket/input"},
)
```
### after
```python
import time
from prefect_aws import AwsCredentials

@task
def run_glue(job_name: str, script_args: dict):
    creds = AwsCredentials.load("aws-default")
    glue = creds.get_boto3_session().client("glue")
    run = glue.start_job_run(JobName=job_name, Arguments=script_args)
    run_id = run["JobRunId"]
    while True:
        status = glue.get_job_run(JobName=job_name, RunId=run_id)
        state = status["JobRun"]["JobRunState"]
        if state in ("SUCCEEDED",):
            return run_id
        if state in ("FAILED", "ERROR", "TIMEOUT"):
            raise Exception(f"Glue job {state}")
        time.sleep(30)
```
{% endsection %}

{% section EcsRunTaskOperator %}
## operator
EcsRunTaskOperator

## module
airflow.providers.amazon.aws.operators.ecs

## source_context
Runs a task on AWS ECS. Creates or uses existing task definition, starts task, and optionally waits for completion.

## prefect_pattern
ECSTask work pool or boto3 directly

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import AwsCredentials

## example
### before
```python
ecs = EcsRunTaskOperator(
    task_id="run_ecs",
    task_definition="my-task",
    cluster="my-cluster",
    overrides={"containerOverrides": [{"name": "app", "command": ["python", "run.py"]}]},
)
```
### after
```python
# Option 1: Use ECS work pool (preferred for deployment)
# Option 2: Direct boto3
from prefect_aws import AwsCredentials

@task
def run_ecs(task_def: str, cluster: str, command: list[str]):
    creds = AwsCredentials.load("aws-default")
    ecs = creds.get_boto3_session().client("ecs")
    response = ecs.run_task(
        cluster=cluster,
        taskDefinition=task_def,
        overrides={"containerOverrides": [{"name": "app", "command": command}]},
    )
    return response["tasks"][0]["taskArn"]
```

## notes
- For production: use an ECS work pool to run entire flows on ECS
- For one-off tasks: use boto3 directly
{% endsection %}

{% section SageMakerTrainingOperator %}
## operator
SageMakerTrainingOperator

## module
airflow.providers.amazon.aws.operators.sagemaker

## source_context
Creates and monitors a SageMaker training job. Configures algorithm, input/output, and instance settings.

## prefect_pattern
boto3 SageMaker create_training_job

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import AwsCredentials

## example
### before
```python
train = SageMakerTrainingOperator(
    task_id="train_model",
    config={
        "TrainingJobName": "my-job",
        "AlgorithmSpecification": {...},
        "InputDataConfig": [...],
        "OutputDataConfig": {...},
    },
)
```
### after
```python
from prefect_aws import AwsCredentials

@task
def train_model(config: dict):
    creds = AwsCredentials.load("aws-default")
    sm = creds.get_boto3_session().client("sagemaker")
    sm.create_training_job(**config)
    # Poll for completion...
```
{% endsection %}

{% section StepFunctionStartExecutionOperator %}
## operator
StepFunctionStartExecutionOperator

## module
airflow.providers.amazon.aws.operators.step_function

## source_context
Starts an AWS Step Functions state machine execution and optionally waits for completion.

## prefect_pattern
boto3 stepfunctions start_execution

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import AwsCredentials

## example
### before
```python
step = StepFunctionStartExecutionOperator(
    task_id="start_workflow",
    state_machine_arn="arn:aws:states:...",
    input='{"key": "value"}',
)
```
### after
```python
import json
from prefect_aws import AwsCredentials

@task
def start_step_function(state_machine_arn: str, input_data: dict):
    creds = AwsCredentials.load("aws-default")
    sfn = creds.get_boto3_session().client("stepfunctions")
    response = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(input_data),
    )
    return response["executionArn"]
```
{% endsection %}

{% section AthenaOperator %}
## operator
AthenaOperator

## module
airflow.providers.amazon.aws.operators.athena

## source_context
Runs an Amazon Athena query and waits for results.

## prefect_pattern
boto3 Athena start_query_execution

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import AwsCredentials

## example
### before
```python
query = AthenaOperator(
    task_id="athena_query",
    query="SELECT * FROM my_table WHERE date = '{{ ds }}'",
    database="my_database",
    output_location="s3://bucket/athena-results/",
)
```
### after
```python
from prefect_aws import AwsCredentials

@task
def athena_query(query: str, database: str, output_location: str):
    creds = AwsCredentials.load("aws-default")
    athena = creds.get_boto3_session().client("athena")
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": output_location},
    )
    return response["QueryExecutionId"]
```
{% endsection %}

{% section RedshiftSQLOperator %}
## operator
RedshiftSQLOperator

## module
airflow.providers.amazon.aws.operators.redshift_sql

## source_context
Executes SQL on Amazon Redshift using redshift_connector.

## prefect_pattern
SqlAlchemyConnector with Redshift driver

## prefect_package
prefect-sqlalchemy

## prefect_import
from prefect_sqlalchemy import SqlAlchemyConnector

## example
### before
```python
query = RedshiftSQLOperator(
    task_id="redshift_query",
    sql="COPY table FROM 's3://bucket/data' IAM_ROLE '{{ var.value.role }}'",
    redshift_conn_id="redshift_default",
)
```
### after
```python
from prefect_sqlalchemy import SqlAlchemyConnector

@task
def redshift_query(sql: str):
    connector = SqlAlchemyConnector.load("redshift-default")
    with connector.get_connection() as conn:
        conn.execute(text(sql))
```
{% endsection %}

{% section SnsPublishOperator %}
## operator
SnsPublishOperator

## module
airflow.providers.amazon.aws.operators.sns

## source_context
Publishes a message to an Amazon SNS topic.

## prefect_pattern
boto3 SNS publish

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import AwsCredentials

## example
### before
```python
notify = SnsPublishOperator(
    task_id="notify",
    target_arn="arn:aws:sns:us-east-1:123:my-topic",
    message="Pipeline complete",
)
```
### after
```python
from prefect_aws import AwsCredentials

@task
def notify(topic_arn: str, message: str):
    creds = AwsCredentials.load("aws-default")
    sns = creds.get_boto3_session().client("sns")
    sns.publish(TopicArn=topic_arn, Message=message)
```
{% endsection %}
