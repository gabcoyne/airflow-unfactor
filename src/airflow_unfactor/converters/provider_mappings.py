"""Map Airflow provider operators to Prefect integrations.

See specs/provider-operators.openspec.md for specification.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperatorMapping:
    """Mapping from Airflow operator to Prefect equivalent."""

    airflow_operator: str
    prefect_integration: str | None  # e.g., "prefect-aws"
    prefect_function: str  # e.g., "s3_upload"
    pip_packages: list[str] = field(default_factory=list)
    import_statement: str = ""
    code_template: str = ""
    notes: str = ""


# Operator mappings registry
OPERATOR_MAPPINGS: dict[str, OperatorMapping] = {
    # ==========================================================================
    # AWS S3 Operators
    # ==========================================================================
    "S3CreateObjectOperator": OperatorMapping(
        airflow_operator="S3CreateObjectOperator",
        prefect_integration="prefect-aws",
        prefect_function="s3_upload",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import S3Bucket",
        code_template="""@task
def upload_to_s3(data: bytes, key: str):
    s3_bucket = S3Bucket.load("my-bucket")  # Configure in Prefect UI
    s3_bucket.upload_from_bytes(data, key)""",
        notes="Configure S3Bucket block in Prefect UI with credentials",
    ),
    "S3DeleteObjectsOperator": OperatorMapping(
        airflow_operator="S3DeleteObjectsOperator",
        prefect_integration="prefect-aws",
        prefect_function="s3_delete",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import S3Bucket",
        code_template="""@task
def delete_s3_objects(keys: list[str]):
    import boto3
    s3 = boto3.client('s3')
    s3.delete_objects(Bucket='bucket', Delete={'Objects': [{'Key': k} for k in keys]})""",
    ),
    "S3CopyObjectOperator": OperatorMapping(
        airflow_operator="S3CopyObjectOperator",
        prefect_integration="prefect-aws",
        prefect_function="s3_copy",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import S3Bucket",
        code_template="""@task
def copy_s3_object(source_bucket: str, source_key: str, dest_bucket: str, dest_key: str):
    import boto3
    s3 = boto3.client('s3')
    copy_source = {'Bucket': source_bucket, 'Key': source_key}
    s3.copy_object(CopySource=copy_source, Bucket=dest_bucket, Key=dest_key)
    return dest_key""",
        notes="Configure AWS credentials via environment or Prefect blocks",
    ),
    "S3ListOperator": OperatorMapping(
        airflow_operator="S3ListOperator",
        prefect_integration="prefect-aws",
        prefect_function="s3_list",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import S3Bucket",
        code_template="""@task
def list_s3_objects(bucket: str, prefix: str = "") -> list[str]:
    s3_bucket = S3Bucket.load("my-bucket")
    return s3_bucket.list_objects(folder=prefix)""",
        notes="Returns list of object keys matching prefix",
    ),
    "S3FileTransformOperator": OperatorMapping(
        airflow_operator="S3FileTransformOperator",
        prefect_integration="prefect-aws",
        prefect_function="s3_transform",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import S3Bucket",
        code_template="""@task
def transform_s3_file(source_key: str, dest_key: str, transform_script: str):
    import subprocess
    import tempfile
    from pathlib import Path

    s3_bucket = S3Bucket.load("my-bucket")

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "source"
        dest_path = Path(tmpdir) / "dest"

        # Download source
        s3_bucket.download_object_to_path(source_key, source_path)

        # Run transform
        subprocess.run([transform_script, str(source_path), str(dest_path)], check=True)

        # Upload result
        s3_bucket.upload_from_path(dest_path, dest_key)

    return dest_key""",
        notes="Transform script receives source and dest file paths as arguments",
    ),
    # ==========================================================================
    # AWS Compute Operators
    # ==========================================================================
    "LambdaInvokeFunctionOperator": OperatorMapping(
        airflow_operator="LambdaInvokeFunctionOperator",
        prefect_integration="prefect-aws",
        prefect_function="lambda_invoke",
        pip_packages=["prefect-aws", "boto3"],
        import_statement="from prefect_aws.lambda_function import LambdaFunction",
        code_template="""@task
def invoke_lambda(function_name: str, payload: dict):
    import boto3
    import json
    client = boto3.client('lambda')
    response = client.invoke(
        FunctionName=function_name,
        Payload=json.dumps(payload),
    )
    return json.loads(response['Payload'].read())""",
    ),
    "EcsRunTaskOperator": OperatorMapping(
        airflow_operator="EcsRunTaskOperator",
        prefect_integration="prefect-aws",
        prefect_function="ecs_run_task",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws.ecs import ECSTask",
        code_template="""@task
def run_ecs_task(
    task_definition: str,
    cluster: str,
    launch_type: str = "FARGATE",
    overrides: dict | None = None,
):
    import boto3

    client = boto3.client('ecs')
    response = client.run_task(
        taskDefinition=task_definition,
        cluster=cluster,
        launchType=launch_type,
        overrides=overrides or {},
    )
    return response['tasks'][0]['taskArn']""",
        notes="For infrastructure, consider using ECSTask work pool instead",
    ),
    "EksCreateClusterOperator": OperatorMapping(
        airflow_operator="EksCreateClusterOperator",
        prefect_integration="prefect-aws",
        prefect_function="eks_create_cluster",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import AwsCredentials",
        code_template="""@task
def create_eks_cluster(
    name: str,
    role_arn: str,
    resources_vpc_config: dict,
    kubernetes_version: str = "1.29",
):
    import boto3

    client = boto3.client('eks')
    response = client.create_cluster(
        name=name,
        version=kubernetes_version,
        roleArn=role_arn,
        resourcesVpcConfig=resources_vpc_config,
    )
    return response['cluster']['arn']""",
        notes="Long-running operation - consider polling for cluster status",
    ),
    "EksPodOperator": OperatorMapping(
        airflow_operator="EksPodOperator",
        prefect_integration="prefect-kubernetes",
        prefect_function="kubernetes_job",
        pip_packages=["prefect-kubernetes"],
        import_statement="from prefect_kubernetes import KubernetesJob",
        code_template="""@task
def run_eks_pod(
    cluster_name: str,
    image: str,
    cmds: list[str],
    arguments: list[str] | None = None,
    namespace: str = "default",
):
    from prefect_kubernetes import KubernetesJob
    from prefect_kubernetes.credentials import KubernetesCredentials

    k8s_creds = KubernetesCredentials.load("eks-credentials")
    job = KubernetesJob(
        image=image,
        command=cmds,
        args=arguments or [],
        namespace=namespace,
        credentials=k8s_creds,
    )
    return job.run()""",
        notes="Configure KubernetesCredentials block with EKS kubeconfig",
    ),
    # ==========================================================================
    # AWS Data Operators
    # ==========================================================================
    "GlueJobOperator": OperatorMapping(
        airflow_operator="GlueJobOperator",
        prefect_integration="prefect-aws",
        prefect_function="glue_job",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import AwsCredentials",
        code_template="""@task
def run_glue_job(job_name: str, arguments: dict | None = None):
    import boto3
    import time

    client = boto3.client('glue')
    response = client.start_job_run(
        JobName=job_name,
        Arguments=arguments or {},
    )
    run_id = response['JobRunId']

    # Poll for completion
    while True:
        status = client.get_job_run(JobName=job_name, RunId=run_id)
        state = status['JobRun']['JobRunState']
        if state in ('SUCCEEDED', 'FAILED', 'STOPPED'):
            break
        time.sleep(30)

    if state != 'SUCCEEDED':
        raise RuntimeError(f"Glue job {job_name} {state}")
    return run_id""",
        notes="Consider using Prefect's async patterns for long-running jobs",
    ),
    "GlueCrawlerOperator": OperatorMapping(
        airflow_operator="GlueCrawlerOperator",
        prefect_integration="prefect-aws",
        prefect_function="glue_crawler",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import AwsCredentials",
        code_template="""@task
def run_glue_crawler(crawler_name: str, wait_for_completion: bool = True):
    import boto3
    import time

    client = boto3.client('glue')
    client.start_crawler(Name=crawler_name)

    if wait_for_completion:
        while True:
            response = client.get_crawler(Name=crawler_name)
            state = response['Crawler']['State']
            if state == 'READY':
                break
            time.sleep(30)

    return crawler_name""",
    ),
    "RedshiftSQLOperator": OperatorMapping(
        airflow_operator="RedshiftSQLOperator",
        prefect_integration="prefect-aws",
        prefect_function="redshift_query",
        pip_packages=["prefect-aws", "redshift-connector"],
        import_statement="from prefect_aws import AwsCredentials",
        code_template="""@task
def execute_redshift_sql(sql: str, cluster_identifier: str, database: str, db_user: str):
    import boto3
    import time

    client = boto3.client('redshift-data')
    response = client.execute_statement(
        ClusterIdentifier=cluster_identifier,
        Database=database,
        DbUser=db_user,
        Sql=sql,
    )
    statement_id = response['Id']

    # Poll for completion
    while True:
        status = client.describe_statement(Id=statement_id)
        state = status['Status']
        if state in ('FINISHED', 'FAILED', 'ABORTED'):
            break
        time.sleep(5)

    if state != 'FINISHED':
        raise RuntimeError(f"Redshift query {state}: {status.get('Error')}")

    # Fetch results if available
    if status.get('HasResultSet'):
        result = client.get_statement_result(Id=statement_id)
        return result['Records']
    return None""",
        notes="Uses Redshift Data API for serverless execution",
    ),
    # ==========================================================================
    # GCP Storage Operators
    # ==========================================================================
    "BigQueryInsertJobOperator": OperatorMapping(
        airflow_operator="BigQueryInsertJobOperator",
        prefect_integration="prefect-gcp",
        prefect_function="bigquery_query",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp.bigquery import bigquery_query",
        code_template="""@task
def run_bigquery_job(query: str):
    from prefect_gcp import GcpCredentials
    from google.cloud import bigquery

    credentials = GcpCredentials.load("my-gcp-creds")
    client = bigquery.Client(credentials=credentials.get_credentials_from_service_account())
    job = client.query(query)
    return job.result()""",
        notes="Configure GcpCredentials block in Prefect UI",
    ),
    "BigQueryExecuteQueryOperator": OperatorMapping(
        airflow_operator="BigQueryExecuteQueryOperator",
        prefect_integration="prefect-gcp",
        prefect_function="bigquery_query",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp.bigquery import bigquery_query",
        code_template="""@task
def execute_bigquery(sql: str):
    from prefect_gcp import GcpCredentials
    from google.cloud import bigquery

    credentials = GcpCredentials.load("my-gcp-creds")
    client = bigquery.Client(credentials=credentials.get_credentials_from_service_account())
    return list(client.query(sql).result())""",
    ),
    "GCSCreateBucketOperator": OperatorMapping(
        airflow_operator="GCSCreateBucketOperator",
        prefect_integration="prefect-gcp",
        prefect_function="create_gcs_bucket",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcsBucket",
        code_template="""@task
def create_gcs_bucket(bucket_name: str, location: str = "US"):
    from google.cloud import storage
    client = storage.Client()
    bucket = client.create_bucket(bucket_name, location=location)
    return bucket.name""",
    ),
    "GCSToGCSOperator": OperatorMapping(
        airflow_operator="GCSToGCSOperator",
        prefect_integration="prefect-gcp",
        prefect_function="gcs_copy",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcsBucket",
        code_template="""@task
def copy_gcs_objects(
    source_bucket: str,
    source_object: str,
    destination_bucket: str,
    destination_object: str | None = None,
):
    from google.cloud import storage

    client = storage.Client()
    src_bucket = client.bucket(source_bucket)
    dst_bucket = client.bucket(destination_bucket)

    src_blob = src_bucket.blob(source_object)
    dst_blob_name = destination_object or source_object

    src_bucket.copy_blob(src_blob, dst_bucket, dst_blob_name)
    return f"gs://{destination_bucket}/{dst_blob_name}" """,
    ),
    "GCSDeleteObjectsOperator": OperatorMapping(
        airflow_operator="GCSDeleteObjectsOperator",
        prefect_integration="prefect-gcp",
        prefect_function="gcs_delete",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcsBucket",
        code_template="""@task
def delete_gcs_objects(bucket_name: str, objects: list[str]):
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    for obj in objects:
        blob = bucket.blob(obj)
        blob.delete()

    return len(objects)""",
    ),
    "GCSFileTransformOperator": OperatorMapping(
        airflow_operator="GCSFileTransformOperator",
        prefect_integration="prefect-gcp",
        prefect_function="gcs_transform",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcsBucket",
        code_template="""@task
def transform_gcs_file(
    source_bucket: str,
    source_object: str,
    destination_bucket: str,
    destination_object: str,
    transform_script: str,
):
    import subprocess
    import tempfile
    from pathlib import Path
    from google.cloud import storage

    client = storage.Client()

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "source"
        dest_path = Path(tmpdir) / "dest"

        # Download source
        bucket = client.bucket(source_bucket)
        blob = bucket.blob(source_object)
        blob.download_to_filename(source_path)

        # Run transform
        subprocess.run([transform_script, str(source_path), str(dest_path)], check=True)

        # Upload result
        dst_bucket = client.bucket(destination_bucket)
        dst_blob = dst_bucket.blob(destination_object)
        dst_blob.upload_from_filename(dest_path)

    return f"gs://{destination_bucket}/{destination_object}" """,
    ),
    # ==========================================================================
    # GCP Compute Operators
    # ==========================================================================
    "DataprocSubmitJobOperator": OperatorMapping(
        airflow_operator="DataprocSubmitJobOperator",
        prefect_integration="prefect-gcp",
        prefect_function="dataproc_job",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcpCredentials",
        code_template="""@task
def submit_dataproc_job(
    project_id: str,
    region: str,
    cluster_name: str,
    job: dict,
):
    from google.cloud import dataproc_v1

    client = dataproc_v1.JobControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )

    job_config = {
        "placement": {"cluster_name": cluster_name},
        **job,
    }

    operation = client.submit_job_as_operation(
        request={"project_id": project_id, "region": region, "job": job_config}
    )
    response = operation.result()
    return response.reference.job_id""",
        notes="Job dict should contain spark_job, pyspark_job, hive_job, etc.",
    ),
    "DataprocCreateClusterOperator": OperatorMapping(
        airflow_operator="DataprocCreateClusterOperator",
        prefect_integration="prefect-gcp",
        prefect_function="dataproc_create_cluster",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcpCredentials",
        code_template="""@task
def create_dataproc_cluster(
    project_id: str,
    region: str,
    cluster_name: str,
    cluster_config: dict,
):
    from google.cloud import dataproc_v1

    client = dataproc_v1.ClusterControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )

    cluster = {
        "project_id": project_id,
        "cluster_name": cluster_name,
        "config": cluster_config,
    }

    operation = client.create_cluster(
        request={"project_id": project_id, "region": region, "cluster": cluster}
    )
    response = operation.result()
    return response.cluster_name""",
        notes="Long-running operation - consider async polling pattern",
    ),
    # ==========================================================================
    # GCP Messaging Operators
    # ==========================================================================
    "PubSubPublishMessageOperator": OperatorMapping(
        airflow_operator="PubSubPublishMessageOperator",
        prefect_integration="prefect-gcp",
        prefect_function="pubsub_publish",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcpCredentials",
        code_template="""@task
def publish_to_pubsub(
    project_id: str,
    topic: str,
    messages: list[dict],
):
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic)

    futures = []
    for msg in messages:
        data = msg.get('data', '').encode('utf-8')
        attrs = msg.get('attributes', {})
        future = publisher.publish(topic_path, data, **attrs)
        futures.append(future)

    # Wait for all publishes to complete
    message_ids = [f.result() for f in futures]
    return message_ids""",
    ),
    "PubSubCreateSubscriptionOperator": OperatorMapping(
        airflow_operator="PubSubCreateSubscriptionOperator",
        prefect_integration="prefect-gcp",
        prefect_function="pubsub_create_subscription",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcpCredentials",
        code_template="""@task
def create_pubsub_subscription(
    project_id: str,
    topic: str,
    subscription: str,
    ack_deadline_seconds: int = 10,
):
    from google.cloud import pubsub_v1

    subscriber = pubsub_v1.SubscriberClient()
    topic_path = subscriber.topic_path(project_id, topic)
    subscription_path = subscriber.subscription_path(project_id, subscription)

    sub = subscriber.create_subscription(
        request={
            "name": subscription_path,
            "topic": topic_path,
            "ack_deadline_seconds": ack_deadline_seconds,
        }
    )
    return sub.name""",
    ),
    # ==========================================================================
    # Azure Operators
    # ==========================================================================
    "WasbBlobOperator": OperatorMapping(
        airflow_operator="WasbBlobOperator",
        prefect_integration="prefect-azure",
        prefect_function="azure_blob",
        pip_packages=["prefect-azure"],
        import_statement="from prefect_azure import AzureBlobStorageCredentials",
        code_template="""@task
def upload_azure_blob(
    container_name: str,
    blob_name: str,
    data: bytes,
):
    from prefect_azure import AzureBlobStorageCredentials

    credentials = AzureBlobStorageCredentials.load("azure-blob-creds")
    blob_client = credentials.get_blob_client(container_name, blob_name)
    blob_client.upload_blob(data, overwrite=True)
    return f"{container_name}/{blob_name}" """,
        notes="Configure AzureBlobStorageCredentials block with connection string",
    ),
    "AzureDataFactoryRunPipelineOperator": OperatorMapping(
        airflow_operator="AzureDataFactoryRunPipelineOperator",
        prefect_integration="prefect-azure",
        prefect_function="adf_run_pipeline",
        pip_packages=["prefect-azure"],
        import_statement="from prefect_azure import AzureDataFactoryCredentials",
        code_template="""@task
def run_adf_pipeline(
    resource_group: str,
    factory_name: str,
    pipeline_name: str,
    parameters: dict | None = None,
):
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.datafactory import DataFactoryManagementClient
    import time

    credential = DefaultAzureCredential()
    # Get subscription_id from environment or parameter
    subscription_id = "your-subscription-id"

    client = DataFactoryManagementClient(credential, subscription_id)

    # Start pipeline run
    run_response = client.pipelines.create_run(
        resource_group_name=resource_group,
        factory_name=factory_name,
        pipeline_name=pipeline_name,
        parameters=parameters or {},
    )
    run_id = run_response.run_id

    # Poll for completion
    while True:
        run_status = client.pipeline_runs.get(
            resource_group_name=resource_group,
            factory_name=factory_name,
            run_id=run_id,
        )
        if run_status.status in ('Succeeded', 'Failed', 'Cancelled'):
            break
        time.sleep(30)

    if run_status.status != 'Succeeded':
        raise RuntimeError(f"Pipeline {run_status.status}: {run_status.message}")

    return run_id""",
        notes="Configure Azure credentials via environment or managed identity",
    ),
    # ==========================================================================
    # Databricks Operators
    # ==========================================================================
    "DatabricksRunNowOperator": OperatorMapping(
        airflow_operator="DatabricksRunNowOperator",
        prefect_integration="prefect-databricks",
        prefect_function="databricks_run_now",
        pip_packages=["prefect-databricks"],
        import_statement="from prefect_databricks import DatabricksCredentials",
        code_template="""@task
def run_databricks_job(
    job_id: int,
    notebook_params: dict | None = None,
    python_params: list[str] | None = None,
):
    from prefect_databricks import DatabricksCredentials
    from prefect_databricks.jobs import jobs_run_now

    credentials = DatabricksCredentials.load("databricks-creds")

    run = jobs_run_now(
        databricks_credentials=credentials,
        job_id=job_id,
        notebook_params=notebook_params,
        python_params=python_params,
    )
    return run""",
        notes="Configure DatabricksCredentials block with host and token",
    ),
    "DatabricksSubmitRunOperator": OperatorMapping(
        airflow_operator="DatabricksSubmitRunOperator",
        prefect_integration="prefect-databricks",
        prefect_function="databricks_submit_run",
        pip_packages=["prefect-databricks"],
        import_statement="from prefect_databricks import DatabricksCredentials",
        code_template="""@task
def submit_databricks_run(
    task_key: str,
    new_cluster: dict | None = None,
    existing_cluster_id: str | None = None,
    notebook_task: dict | None = None,
    spark_python_task: dict | None = None,
):
    from prefect_databricks import DatabricksCredentials
    from prefect_databricks.jobs import jobs_submit

    credentials = DatabricksCredentials.load("databricks-creds")

    tasks = [{
        "task_key": task_key,
        **({"new_cluster": new_cluster} if new_cluster else {}),
        **({"existing_cluster_id": existing_cluster_id} if existing_cluster_id else {}),
        **({"notebook_task": notebook_task} if notebook_task else {}),
        **({"spark_python_task": spark_python_task} if spark_python_task else {}),
    }]

    run = jobs_submit(
        databricks_credentials=credentials,
        tasks=tasks,
    )
    return run""",
    ),
    "DatabricksSqlOperator": OperatorMapping(
        airflow_operator="DatabricksSqlOperator",
        prefect_integration="prefect-databricks",
        prefect_function="databricks_sql",
        pip_packages=["prefect-databricks", "databricks-sql-connector"],
        import_statement="from prefect_databricks import DatabricksCredentials",
        code_template="""@task
def execute_databricks_sql(
    sql: str,
    warehouse_id: str,
):
    from databricks import sql as databricks_sql

    # Get credentials from environment or block
    host = "your-workspace.cloud.databricks.com"  # Configure via block
    token = "your-token"  # Configure via block

    connection = databricks_sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        access_token=token,
    )

    cursor = connection.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    connection.close()

    return result""",
        notes="Configure Databricks SQL warehouse credentials via block",
    ),
    # ==========================================================================
    # dbt Operators
    # ==========================================================================
    "DbtCloudRunJobOperator": OperatorMapping(
        airflow_operator="DbtCloudRunJobOperator",
        prefect_integration="prefect-dbt",
        prefect_function="dbt_cloud_run_job",
        pip_packages=["prefect-dbt"],
        import_statement="from prefect_dbt.cloud import DbtCloudCredentials",
        code_template="""@task
def run_dbt_cloud_job(
    job_id: int,
    cause: str = "Triggered by Prefect",
    wait_for_job_run_completion: bool = True,
):
    from prefect_dbt.cloud import DbtCloudCredentials
    from prefect_dbt.cloud.jobs import trigger_dbt_cloud_job_run

    credentials = DbtCloudCredentials.load("dbt-cloud-creds")

    result = trigger_dbt_cloud_job_run(
        dbt_cloud_credentials=credentials,
        job_id=job_id,
        options={"cause": cause},
    )

    if wait_for_job_run_completion:
        from prefect_dbt.cloud.jobs import get_dbt_cloud_run_info
        import time

        while True:
            run_info = get_dbt_cloud_run_info(
                dbt_cloud_credentials=credentials,
                run_id=result.run_id,
            )
            if run_info.status_humanized in ('Success', 'Error', 'Cancelled'):
                break
            time.sleep(30)

        if run_info.status_humanized != 'Success':
            raise RuntimeError(f"dbt Cloud job {run_info.status_humanized}")

    return result.run_id""",
        notes="Configure DbtCloudCredentials block with API token",
    ),
    "DbtRunOperator": OperatorMapping(
        airflow_operator="DbtRunOperator",
        prefect_integration="prefect-dbt",
        prefect_function="dbt_run",
        pip_packages=["prefect-dbt", "dbt-core"],
        import_statement="from prefect_dbt.cli import DbtCliProfile",
        code_template="""@task
def run_dbt(
    project_dir: str,
    profiles_dir: str | None = None,
    select: str | None = None,
    exclude: str | None = None,
):
    from prefect_dbt.cli.commands import DbtCoreOperation

    dbt_op = DbtCoreOperation(
        commands=["dbt run"],
        project_dir=project_dir,
        profiles_dir=profiles_dir,
        overwrite_profiles=False,
    )

    # Build command with selectors
    cmd = "dbt run"
    if select:
        cmd += f" --select {select}"
    if exclude:
        cmd += f" --exclude {exclude}"

    dbt_op.commands = [cmd]
    return dbt_op.run()""",
        notes="For cosmos integration, use DbtDag patterns",
    ),
    # ==========================================================================
    # Database Operators
    "PostgresOperator": OperatorMapping(
        airflow_operator="PostgresOperator",
        prefect_integration="prefect-sqlalchemy",
        prefect_function="execute_sql",
        pip_packages=["prefect-sqlalchemy", "psycopg2-binary"],
        import_statement="from prefect_sqlalchemy import SqlAlchemyConnector",
        code_template="""@task
def execute_postgres(sql: str):
    connector = SqlAlchemyConnector.load("postgres-conn")  # Configure in Prefect UI
    with connector.get_connection() as conn:
        conn.execute(sql)""",
        notes="Configure SqlAlchemyConnector block with PostgreSQL connection string",
    ),
    "MySqlOperator": OperatorMapping(
        airflow_operator="MySqlOperator",
        prefect_integration="prefect-sqlalchemy",
        prefect_function="execute_sql",
        pip_packages=["prefect-sqlalchemy", "pymysql"],
        import_statement="from prefect_sqlalchemy import SqlAlchemyConnector",
        code_template="""@task
def execute_mysql(sql: str):
    connector = SqlAlchemyConnector.load("mysql-conn")
    with connector.get_connection() as conn:
        conn.execute(sql)""",
    ),
    "SnowflakeOperator": OperatorMapping(
        airflow_operator="SnowflakeOperator",
        prefect_integration="prefect-snowflake",
        prefect_function="snowflake_query",
        pip_packages=["prefect-snowflake"],
        import_statement="from prefect_snowflake import SnowflakeConnector",
        code_template="""@task
def execute_snowflake(query: str):
    connector = SnowflakeConnector.load("snowflake-conn")
    return connector.fetch_all(query)""",
        notes="Configure SnowflakeConnector block in Prefect UI",
    ),
    # Notification Operators
    "SlackWebhookOperator": OperatorMapping(
        airflow_operator="SlackWebhookOperator",
        prefect_integration="prefect-slack",
        prefect_function="send_message",
        pip_packages=["prefect-slack"],
        import_statement="from prefect_slack import SlackWebhook",
        code_template="""@task
def send_slack_message(message: str):
    webhook = SlackWebhook.load("slack-webhook")  # Configure in Prefect UI
    webhook.notify(body=message)""",
        notes="Configure SlackWebhook block with webhook URL",
    ),
    "EmailOperator": OperatorMapping(
        airflow_operator="EmailOperator",
        prefect_integration="prefect-email",
        prefect_function="send_email",
        pip_packages=["prefect-email"],
        import_statement="from prefect_email import EmailServerCredentials, email_send_message",
        code_template="""@task
def send_email(to: list[str], subject: str, body: str):
    credentials = EmailServerCredentials.load("email-creds")
    email_send_message(
        email_server_credentials=credentials,
        subject=subject,
        msg=body,
        email_to=to,
    )""",
    ),
    # Generic/Utility Operators
    "SimpleHttpOperator": OperatorMapping(
        airflow_operator="SimpleHttpOperator",
        prefect_integration=None,
        prefect_function="http_request",
        pip_packages=["httpx"],
        import_statement="import httpx",
        code_template="""@task
def http_request(method: str, url: str, data: dict = None):
    response = httpx.request(method, url, json=data)
    response.raise_for_status()
    return response.json()""",
    ),
}


def get_operator_mapping(operator_name: str) -> OperatorMapping | None:
    """Get the Prefect mapping for an Airflow operator.

    Args:
        operator_name: Name of the Airflow operator

    Returns:
        OperatorMapping if found, None otherwise
    """
    return OPERATOR_MAPPINGS.get(operator_name)


def get_all_mappings() -> dict[str, OperatorMapping]:
    """Get all operator mappings."""
    return OPERATOR_MAPPINGS.copy()


def generate_conversion_code(
    operator_name: str,
    task_id: str,
    parameters: dict[str, Any],
    include_comments: bool = True,
) -> dict[str, Any]:
    """Generate Prefect code for an Airflow operator.

    Args:
        operator_name: Name of the Airflow operator
        task_id: The task_id from Airflow
        parameters: Operator parameters
        include_comments: Include educational comments

    Returns:
        Dictionary with code, imports, packages, notes
    """
    mapping = get_operator_mapping(operator_name)

    if not mapping:
        # Unknown operator - generate generic task
        return {
            "code": f"""@task
def {task_id}():
    \"\"\"Converted from {operator_name}.\"\"\"  
    # TODO: Implement operator logic
    # Original parameters: {parameters}
    raise NotImplementedError("Manual conversion needed for {operator_name}")""",
            "imports": ["from prefect import task"],
            "packages": [],
            "notes": [f"Unknown operator: {operator_name}. Manual conversion required."],
        }

    lines = []

    if include_comments:
        lines.append(f"# Converted from Airflow {operator_name}")
        if mapping.prefect_integration:
            lines.append(f"# Using Prefect integration: {mapping.prefect_integration}")
        if mapping.notes:
            lines.append(f"# Note: {mapping.notes}")
        lines.append("")

    lines.append(mapping.import_statement)
    lines.append("from prefect import task")
    lines.append("")

    # Customize code template with task_id
    code = mapping.code_template.replace("@task\ndef ", f"@task\ndef {task_id}_")
    lines.append(code)

    return {
        "code": "\n".join(lines),
        "imports": [mapping.import_statement, "from prefect import task"],
        "packages": mapping.pip_packages,
        "notes": [mapping.notes] if mapping.notes else [],
    }


def summarize_operator_support() -> str:
    """Generate a summary of supported operator conversions."""
    lines = ["# Supported Airflow Operator Conversions", ""]

    # Group by category
    categories = {
        "AWS S3": [
            "S3CreateObjectOperator",
            "S3DeleteObjectsOperator",
            "S3CopyObjectOperator",
            "S3ListOperator",
            "S3FileTransformOperator",
        ],
        "AWS Compute": [
            "LambdaInvokeFunctionOperator",
            "EcsRunTaskOperator",
            "EksCreateClusterOperator",
            "EksPodOperator",
        ],
        "AWS Data": [
            "GlueJobOperator",
            "GlueCrawlerOperator",
            "RedshiftSQLOperator",
        ],
        "GCP Storage": [
            "BigQueryInsertJobOperator",
            "BigQueryExecuteQueryOperator",
            "GCSCreateBucketOperator",
            "GCSToGCSOperator",
            "GCSDeleteObjectsOperator",
            "GCSFileTransformOperator",
        ],
        "GCP Compute": [
            "DataprocSubmitJobOperator",
            "DataprocCreateClusterOperator",
        ],
        "GCP Messaging": [
            "PubSubPublishMessageOperator",
            "PubSubCreateSubscriptionOperator",
        ],
        "Azure": [
            "WasbBlobOperator",
            "AzureDataFactoryRunPipelineOperator",
        ],
        "Databricks": [
            "DatabricksRunNowOperator",
            "DatabricksSubmitRunOperator",
            "DatabricksSqlOperator",
        ],
        "dbt": [
            "DbtCloudRunJobOperator",
            "DbtRunOperator",
        ],
        "Database": [
            "PostgresOperator",
            "MySqlOperator",
            "SnowflakeOperator",
        ],
        "Notifications": [
            "SlackWebhookOperator",
            "EmailOperator",
        ],
        "HTTP": [
            "SimpleHttpOperator",
        ],
    }

    for category, operators in categories.items():
        lines.append(f"## {category}")
        for op in operators:
            mapping = OPERATOR_MAPPINGS.get(op)
            if mapping:
                integration = mapping.prefect_integration or "stdlib"
                lines.append(f"- {op} → {integration}: {mapping.prefect_function}")
        lines.append("")

    return "\n".join(lines)


def get_operators_by_category() -> dict[str, list[str]]:
    """Get operators grouped by provider category."""
    return {
        "aws_s3": [
            "S3CreateObjectOperator",
            "S3DeleteObjectsOperator",
            "S3CopyObjectOperator",
            "S3ListOperator",
            "S3FileTransformOperator",
        ],
        "aws_compute": [
            "LambdaInvokeFunctionOperator",
            "EcsRunTaskOperator",
            "EksCreateClusterOperator",
            "EksPodOperator",
        ],
        "aws_data": [
            "GlueJobOperator",
            "GlueCrawlerOperator",
            "RedshiftSQLOperator",
        ],
        "gcp_storage": [
            "BigQueryInsertJobOperator",
            "BigQueryExecuteQueryOperator",
            "GCSCreateBucketOperator",
            "GCSToGCSOperator",
            "GCSDeleteObjectsOperator",
            "GCSFileTransformOperator",
        ],
        "gcp_compute": [
            "DataprocSubmitJobOperator",
            "DataprocCreateClusterOperator",
        ],
        "gcp_messaging": [
            "PubSubPublishMessageOperator",
            "PubSubCreateSubscriptionOperator",
        ],
        "azure": [
            "WasbBlobOperator",
            "AzureDataFactoryRunPipelineOperator",
        ],
        "databricks": [
            "DatabricksRunNowOperator",
            "DatabricksSubmitRunOperator",
            "DatabricksSqlOperator",
        ],
        "dbt": [
            "DbtCloudRunJobOperator",
            "DbtRunOperator",
        ],
        "database": [
            "PostgresOperator",
            "MySqlOperator",
            "SnowflakeOperator",
        ],
        "notifications": [
            "SlackWebhookOperator",
            "EmailOperator",
        ],
        "http": [
            "SimpleHttpOperator",
        ],
    }
