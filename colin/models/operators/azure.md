---
name: Azure Provider Operator Mappings
colin:
  output:
    format: json
---

{% section AzureDataFactoryRunPipelineOperator %}
## operator
AzureDataFactoryRunPipelineOperator

## module
airflow.providers.microsoft.azure.operators.data_factory

## intent
Triggers an Azure Data Factory pipeline run and polls for completion. Used in DAGs that orchestrate ADF pipelines as part of a data processing or ELT workflow — for example, kicking off an ADF pipeline that copies and transforms data before downstream tasks run. The operator abstracts the ADF REST API and handles the run-then-poll lifecycle.

## source_context
Operator uses `azure_data_factory_conn_id`, `pipeline_name`, `resource_group_name`, `factory_name`, `parameters` (dict of pipeline parameters), and `wait_for_termination` (True by default). Under the hood it calls the ADF REST API to create a run and then polls `PipelineRunClient.get_pipeline_run()` until the run reaches a terminal state.

## prefect_pattern
ARCHITECTURE SHIFT — `prefect-azure` has no Azure Data Factory module. Do NOT attempt `from prefect_azure import DataFactory*` — no such class exists. The correct pattern is to use the `azure-mgmt-datafactory` SDK directly inside a `@task`, authenticating with `ClientSecretCredential` populated from Prefect `Secret` blocks. The task creates a `DataFactoryManagementClient`, calls `pipelines.create_run()`, then polls `pipeline_runs.get()` until the run completes. Wrap with `@task(retries=3, retry_delay_seconds=30)` for transient ADF API errors.

## prefect_package
none (use azure-mgmt-datafactory + azure-identity directly)

## prefect_import
from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models import PipelineRun
from prefect import task
from prefect.blocks.system import Secret

## example
### before
```python
from airflow.providers.microsoft.azure.operators.data_factory import (
    AzureDataFactoryRunPipelineOperator,
)

run_pipeline = AzureDataFactoryRunPipelineOperator(
    task_id="run_adf_pipeline",
    azure_data_factory_conn_id="azure_data_factory_default",
    pipeline_name="copy_and_transform",
    resource_group_name="my-resource-group",
    factory_name="my-data-factory",
    parameters={"batch_date": "{{ ds }}", "env": "prod"},
    wait_for_termination=True,
)
```
### after
```python
import time
from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from prefect import flow, task
from prefect.blocks.system import Secret

@task(retries=3, retry_delay_seconds=30)
def run_adf_pipeline(
    subscription_id: str,
    resource_group: str,
    factory_name: str,
    pipeline_name: str,
    parameters: dict | None = None,
) -> str:
    """Trigger an ADF pipeline run and poll until completion."""
    tenant_id = Secret.load("adf-tenant-id").get()
    client_id = Secret.load("adf-client-id").get()
    client_secret = Secret.load("adf-client-secret").get()

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    adf_client = DataFactoryManagementClient(credential, subscription_id)

    # Trigger the pipeline run
    run_response = adf_client.pipelines.create_run(
        resource_group,
        factory_name,
        pipeline_name,
        parameters=parameters or {},
    )
    run_id = run_response.run_id

    # Poll until terminal state (mirrors wait_for_termination=True)
    terminal_states = {"Succeeded", "Failed", "Cancelled"}
    while True:
        run = adf_client.pipeline_runs.get(resource_group, factory_name, run_id)
        if run.status in terminal_states:
            break
        time.sleep(30)

    if run.status != "Succeeded":
        raise RuntimeError(
            f"ADF pipeline '{pipeline_name}' run {run_id} ended with status: {run.status}"
        )
    return run_id


@flow
def my_flow(batch_date: str, env: str = "prod"):
    run_id = run_adf_pipeline(
        subscription_id="00000000-0000-0000-0000-000000000000",
        resource_group="my-resource-group",
        factory_name="my-data-factory",
        pipeline_name="copy_and_transform",
        parameters={"batch_date": batch_date, "env": env},
    )
    return run_id
```

## notes
- WARNING: No prefect-azure ADF module exists — do NOT attempt `from prefect_azure import DataFactory*`. This import will fail. The `azure-mgmt-datafactory` SDK is the only option.
- Do NOT use `AzureContainerInstanceCredentials` for ADF — that block is for Azure Container Instances, not Data Factory.
- Install dependencies: `uv pip install azure-mgmt-datafactory azure-identity`
- Create Prefect Secret blocks for ADF credentials (run once before deploying):
  ```python
  from prefect.blocks.system import Secret
  Secret(value="your-tenant-id").save("adf-tenant-id")
  Secret(value="your-client-id").save("adf-client-id")
  Secret(value="your-client-secret").save("adf-client-secret")
  ```
- Terminal states for ADF pipeline runs: `Succeeded`, `Failed`, `Cancelled`, `Queued`, `InProgress`
- Use `@task(retries=3, retry_delay_seconds=30)` to handle transient ADF API 429/503 errors
- The `subscription_id` is not stored in Airflow's `azure_data_factory_conn_id` the same way — extract it from your Azure configuration or pass as a flow parameter
- If you need `DefaultAzureCredential` (managed identity in Azure-hosted environments), replace `ClientSecretCredential` with `from azure.identity import DefaultAzureCredential`

## related_concepts
- azure-mgmt-datafactory-sdk
- prefect-secret-blocks
- architecture-shift
{% endsection %}

{% section WasbOperator %}
## operator
WasbOperator

## module
airflow.providers.microsoft.azure.operators.wasb_delete

## intent
Reads or writes blob data to Azure Blob Storage using the `wasb://` protocol. Used in DAGs that process files stored in Azure containers — for example, downloading a file before processing or uploading transformed results. The operator wraps Azure Blob Storage operations with Airflow connection management.

## source_context
Operator uses `wasb_conn_id`, `container_name`, `blob_name`, and operation-specific parameters. For reads, it retrieves blob content; for writes, it uploads data. The wasb connection stores Azure storage account credentials (connection string or service principal). Most WasbOperator usages in production DAGs are for reading inputs and writing outputs to Azure Blob Storage.

## prefect_pattern
Use `AzureBlobStorageCredentials` block from `prefect_azure` with `blob_storage_download` or `blob_storage_upload` tasks from `prefect_azure.blob_storage`. The credential block stores either a connection string or service principal credentials — set it up once, then load by name in your tasks.

## prefect_package
prefect-azure[blob_storage]

## prefect_import
from prefect import flow, task
from prefect_azure import AzureBlobStorageCredentials
from prefect_azure.blob_storage import blob_storage_download, blob_storage_upload

## example
### before
```python
from airflow.providers.microsoft.azure.hooks.wasb import WasbHook

def process_blob(**context):
    hook = WasbHook(wasb_conn_id="azure_wasb_default")
    blob_data = hook.read_file(container_name="my-container", blob_name="data/input.csv")
    # process blob_data...
    hook.load_bytes(
        blob_data_processed,
        container_name="my-container",
        blob_name="data/output.csv",
    )
```
### after
```python
from prefect import flow, task
from prefect_azure import AzureBlobStorageCredentials
from prefect_azure.blob_storage import blob_storage_download, blob_storage_upload

@task
def download_blob(container: str, blob: str) -> bytes:
    credentials = AzureBlobStorageCredentials.load("my-azure-blob-credentials")
    return blob_storage_download(
        container=container,
        blob=blob,
        blob_storage_credentials=credentials,
    )

@task
def upload_blob(data: bytes, container: str, blob: str) -> None:
    credentials = AzureBlobStorageCredentials.load("my-azure-blob-credentials")
    blob_storage_upload(
        data=data,
        container=container,
        blob=blob,
        blob_storage_credentials=credentials,
        overwrite=True,
    )

@flow
def process_blob_flow():
    raw = download_blob(container="my-container", blob="data/input.csv")
    processed = process_data(raw)  # your processing task
    upload_blob(data=processed, container="my-container", blob="data/output.csv")
```

## notes
- Use `AzureBlobStorageCredentials` NOT `AzureBlobCredentials` — `AzureBlobCredentials` is an older class for flow code storage blocks, not blob tasks
- Install: `uv pip install "prefect-azure[blob_storage]"`
- Credential block setup — connection string method (simpler):
  ```python
  from prefect_azure import AzureBlobStorageCredentials
  creds = AzureBlobStorageCredentials(
      connection_string="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=...;EndpointSuffix=core.windows.net"
  )
  creds.save("my-azure-blob-credentials")
  ```
- Credential block setup — service principal method (recommended for production):
  ```python
  from prefect_azure import AzureBlobStorageCredentials
  creds = AzureBlobStorageCredentials(
      account_url="https://myaccount.blob.core.windows.net/",
      tenant_id="your-tenant-id",
      client_id="your-client-id",
      client_secret="your-client-secret",
  )
  creds.save("my-azure-spn-credentials")
  ```
- `blob_storage_download` returns `bytes`; decode with `.decode("utf-8")` for text content
- For large files, consider streaming — the `blob_storage_download` task loads the entire blob into memory

## related_concepts
- prefect-azure-credentials
- blob-storage-tasks
{% endsection %}

{% section WasbDeleteOperator %}
## operator
WasbDeleteOperator

## module
airflow.providers.microsoft.azure.operators.wasb_delete

## intent
Deletes blobs from Azure Blob Storage. A cleanup companion to WasbOperator — used in DAGs that delete temporary or processed files after downstream tasks have consumed them, or to implement data retention policies.

## source_context
Operator uses `wasb_conn_id`, `container_name`, `blob_name`. Optionally accepts `check_options` for prefix-based deletion. Follows the same authentication pattern as WasbOperator via the WASB hook.

## prefect_pattern
Use `AzureBlobStorageCredentials` block from `prefect_azure` with the Azure `BlobServiceClient` for deletion, or use `blob_storage_list` to find blobs and delete them individually. See the WasbOperator section for credential block setup — the same `AzureBlobStorageCredentials` block applies here.

## prefect_package
prefect-azure[blob_storage]

## prefect_import
from prefect import task
from prefect_azure import AzureBlobStorageCredentials

## example
### before
```python
from airflow.providers.microsoft.azure.operators.wasb_delete import WasbDeleteOperator

delete_temp = WasbDeleteOperator(
    task_id="delete_temp_blob",
    wasb_conn_id="azure_wasb_default",
    container_name="my-container",
    blob_name="temp/processing_artifact.parquet",
)
```
### after
```python
from prefect import task
from prefect_azure import AzureBlobStorageCredentials

@task
def delete_blob(container: str, blob: str) -> None:
    credentials = AzureBlobStorageCredentials.load("my-azure-blob-credentials")
    blob_service_client = credentials.get_client()
    container_client = blob_service_client.get_container_client(container)
    container_client.delete_blob(blob)

# In your flow:
# delete_blob(container="my-container", blob="temp/processing_artifact.parquet")
```

## notes
- See WasbOperator section above for credential block setup — same `AzureBlobStorageCredentials` block applies
- `credentials.get_client()` returns an `azure.storage.blob.BlobServiceClient` — use the standard Azure SDK for delete operations
- For prefix-based deletion (delete all blobs with a prefix), use `container_client.list_blobs(name_starts_with=prefix)` and delete each blob individually
- `delete_blob` is idempotent if the blob no longer exists — catch `ResourceNotFoundError` if you want to suppress "already deleted" errors

## related_concepts
- prefect-azure-credentials
- wasb-operator
{% endsection %}
