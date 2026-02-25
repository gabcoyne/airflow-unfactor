---
name: GCP Provider Operator Mappings
colin:
  output:
    format: json
---

{% section BigQueryInsertJobOperator %}
## operator
BigQueryInsertJobOperator

## module
airflow.providers.google.cloud.operators.bigquery

## source_context
Submits a BigQuery job (query, load, extract, or copy). Wraps the BigQuery jobs.insert API.

## prefect_pattern
BigQueryWarehouse or google-cloud-bigquery client

## prefect_package
prefect-gcp

## prefect_import
from prefect_gcp import BigQueryWarehouse

## example
### before
```python
query = BigQueryInsertJobOperator(
    task_id="bq_query",
    configuration={"query": {"query": "SELECT * FROM dataset.table", "useLegacySql": False}},
)
```
### after
```python
from prefect_gcp import BigQueryWarehouse

@task
def bq_query(sql: str):
    bq = BigQueryWarehouse.load("bigquery-default")
    return bq.fetch_many(sql)
```

## notes
- For simple queries, BigQueryWarehouse is sufficient
- For complex jobs (load, extract), use the google.cloud.bigquery client directly
{% endsection %}

{% section GCSToGCSOperator %}
## operator
GCSToGCSOperator

## module
airflow.providers.google.cloud.transfers.gcs_to_gcs

## source_context
Copies objects between GCS buckets or prefixes.

## prefect_pattern
GcsBucket operations

## prefect_package
prefect-gcp

## prefect_import
from prefect_gcp import GcsBucket

## example
### before
```python
copy = GCSToGCSOperator(
    task_id="copy_gcs",
    source_bucket="src-bucket",
    source_object="data/*.csv",
    destination_bucket="dst-bucket",
    destination_object="archive/",
)
```
### after
```python
from prefect_gcp import GcsBucket, GcpCredentials

@task
def copy_gcs(source_prefix: str, dest_prefix: str):
    creds = GcpCredentials.load("gcp-default")
    from google.cloud import storage
    client = storage.Client(credentials=creds.get_credentials())
    src_bucket = client.bucket("src-bucket")
    dst_bucket = client.bucket("dst-bucket")
    for blob in src_bucket.list_blobs(prefix=source_prefix):
        src_bucket.copy_blob(blob, dst_bucket, dest_prefix + blob.name.split("/")[-1])
```
{% endsection %}

{% section DataprocSubmitJobOperator %}
## operator
DataprocSubmitJobOperator

## module
airflow.providers.google.cloud.operators.dataproc

## source_context
Submits a job to a Dataproc cluster. Supports Spark, PySpark, Hive, Pig, and Hadoop jobs.

## prefect_pattern
google.cloud.dataproc client via GcpCredentials

## prefect_package
prefect-gcp

## prefect_import
from prefect_gcp import GcpCredentials

## example
### before
```python
spark = DataprocSubmitJobOperator(
    task_id="spark_job",
    job={"reference": {"project_id": "my-project"}, "placement": {"cluster_name": "my-cluster"},
         "pyspark_job": {"main_python_file_uri": "gs://bucket/job.py"}},
    region="us-central1",
)
```
### after
```python
from prefect_gcp import GcpCredentials
from google.cloud import dataproc_v1

@task
def spark_job(cluster: str, main_file: str):
    creds = GcpCredentials.load("gcp-default")
    client = dataproc_v1.JobControllerClient(credentials=creds.get_credentials())
    job = {"placement": {"cluster_name": cluster}, "pyspark_job": {"main_python_file_uri": main_file}}
    operation = client.submit_job_as_operation(project_id="my-project", region="us-central1", job=job)
    return operation.result()
```
{% endsection %}

{% section GCSToLocalFilesystemOperator %}
## operator
GCSToLocalFilesystemOperator

## module
airflow.providers.google.cloud.transfers.gcs_to_local

## source_context
Downloads a file from GCS to the local filesystem.

## prefect_pattern
GcsBucket.download_object_to_path

## prefect_package
prefect-gcp

## prefect_import
from prefect_gcp import GcsBucket

## example
### before
```python
download = GCSToLocalFilesystemOperator(
    task_id="download",
    object_name="data/input.csv",
    bucket="my-bucket",
    filename="/tmp/input.csv",
)
```
### after
```python
from prefect_gcp import GcsBucket

@task
def download(blob_name: str, local_path: str):
    bucket = GcsBucket.load("my-gcs-bucket")
    bucket.download_object_to_path(blob_name, local_path)
    return local_path
```
{% endsection %}

{% section CloudDataFusionStartPipelineOperator %}
## operator
CloudDataFusionStartPipelineOperator

## module
airflow.providers.google.cloud.operators.datafusion

## source_context
Starts a Cloud Data Fusion pipeline and optionally waits for completion.

## prefect_pattern
google.cloud REST API via httpx

## prefect_package
prefect-gcp

## prefect_import
from prefect_gcp import GcpCredentials

## example
### before
```python
pipeline = CloudDataFusionStartPipelineOperator(
    task_id="start_pipeline",
    pipeline_name="my-pipeline",
    instance_name="my-instance",
    location="us-central1",
)
```
### after
```python
from prefect_gcp import GcpCredentials
import httpx

@task
def start_datafusion_pipeline(instance_url: str, pipeline_name: str):
    creds = GcpCredentials.load("gcp-default")
    token = creds.get_credentials().token
    resp = httpx.post(
        f"{instance_url}/api/v3/namespaces/default/apps/{pipeline_name}/workflows/DataPipelineWorkflow/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
```
{% endsection %}

{% section PubSubPublishMessageOperator %}
## operator
PubSubPublishMessageOperator

## module
airflow.providers.google.cloud.operators.pubsub

## source_context
Publishes messages to a Google Cloud Pub/Sub topic.

## prefect_pattern
google.cloud.pubsub client

## prefect_package
prefect-gcp

## prefect_import
from prefect_gcp import GcpCredentials

## example
### before
```python
publish = PubSubPublishMessageOperator(
    task_id="publish",
    topic="my-topic",
    messages=[{"data": b"message"}],
)
```
### after
```python
from prefect_gcp import GcpCredentials
from google.cloud import pubsub_v1

@task
def publish(topic: str, messages: list[bytes]):
    creds = GcpCredentials.load("gcp-default")
    publisher = pubsub_v1.PublisherClient(credentials=creds.get_credentials())
    topic_path = publisher.topic_path("my-project", topic)
    for msg in messages:
        publisher.publish(topic_path, data=msg)
```
{% endsection %}
