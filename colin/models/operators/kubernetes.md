---
name: Kubernetes Provider Operator Mappings
colin:
  output:
    format: json
---

{% section KubernetesPodOperator %}
## operator
KubernetesPodOperator

## module
airflow.providers.cncf.kubernetes.operators.pod

## source_context
Spawns a Kubernetes pod per task execution, running a container image with specified resources, environment variables, and commands. Uses the kubernetes Python SDK internally. Supports `image`, `namespace`, `cmds`, `arguments`, `env_vars`, `container_resources`, and `in_cluster` parameters. Each task invocation creates a new pod, waits for completion, and collects logs.

## prefect_pattern
Kubernetes work pool with base job template — infrastructure is declared at the work pool level, not per-task. The flow contains business logic; image, env vars, and resource requests are set in the work pool base job template.

## prefect_package
prefect-kubernetes

## prefect_import
from prefect import flow, task

## example
### before
```python
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

process = KubernetesPodOperator(
    task_id="process_data",
    name="process-data-pod",
    namespace="default",
    image="my-registry/data-processor:v1.2",
    cmds=["python", "-c"],
    arguments=["import pipeline; pipeline.run()"],
    env_vars={"ENV": "prod", "BATCH_SIZE": "1000"},
    container_resources=k8s.V1ResourceRequirements(
        requests={"cpu": "500m", "memory": "1Gi"}
    ),
)
```
### after
```python
from prefect import flow, task

# ARCHITECTURE SHIFT: Infrastructure moves to the Kubernetes work pool.
# Steps to deploy:
# 1. Create a Kubernetes work pool in Prefect UI or via CLI:
#    prefect work-pool create --type kubernetes my-k8s-pool
# 2. In the work pool base job template, set:
#    - image: my-registry/data-processor:v1.2
#    - env: {ENV: prod, BATCH_SIZE: "1000"}
#    - resources: {requests: {cpu: 500m, memory: 1Gi}}
# 3. Deploy this flow targeting that pool:
#    prefect deploy --pool my-k8s-pool
# The @flow runs inside the pod; no per-task pod spawning in code.

@flow(name="process-data")
def process_data(env: str = "prod", batch_size: int = 1000):
    # Business logic here — infrastructure is defined in the work pool,
    # not in this code. The worker spawns the pod automatically.
    import pipeline
    pipeline.run()
```

## notes
- KubernetesPodOperator is an INFRASTRUCTURE concern, not a task concern in Prefect
- There is no per-task pod spawning in Prefect; infrastructure is defined at the work pool level
- `image` → set in the Kubernetes work pool base job template, not in task code
- `env_vars` → set as environment variables in the work pool base job template or KubernetesJob block
- `container_resources` (requests/limits) → customized via base job template
- `cmds`, `arguments` → override container command in the base job template
- For per-task image isolation: deploy each flow or subflow to a separate Kubernetes work pool with a custom base job template
- Do NOT use subprocess.run() or docker SDK to emulate KubernetesPodOperator
- Do NOT use the kubernetes Python SDK (kubernetes.client) directly to spawn pods in @task
- Do NOT wrap the Airflow operator class: never call KubernetesPodOperator(...).execute(context) in a Prefect flow
- Consult Prefect docs for the exact base job template YAML structure — it varies across prefect-kubernetes versions

## related_concepts
- infrastructure-as-work-pool
- deployment-patterns
{% endsection %}
