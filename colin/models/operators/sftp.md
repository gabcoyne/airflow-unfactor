---
name: SSH Provider Operator Mappings
colin:
  output:
    format: json
---

{% section SSHOperator %}
## operator
SSHOperator

## module
airflow.providers.ssh.operators.ssh

## source_context
Executes a command on a remote host via SSH. Uses paramiko internally, takes ssh_conn_id for host, username, and key or password. Captures stdout and stderr, and can raise on non-zero exit status.

## prefect_pattern
paramiko.SSHClient or fabric.Connection inside @task with Secret block for credentials

## prefect_package
none (use paramiko or fabric directly)

## prefect_import
import paramiko

## example
### before
```python
from airflow.providers.ssh.operators.ssh import SSHOperator

ssh_task = SSHOperator(
    task_id="run_remote",
    ssh_conn_id="my_ssh_server",
    command="cd /data && python process.py",
)
```
### after
```python
import paramiko
from prefect import task
from prefect.logging import get_run_logger
from prefect.blocks.system import Secret

@task
def run_remote_command(host: str, username: str, command: str) -> str:
    # Before running: create a Secret block named "ssh-private-key"
    # containing the private key content (PEM string).
    logger = get_run_logger()
    private_key_str = Secret.load("ssh-private-key").get()
    import io
    private_key = paramiko.RSAKey.from_private_key(io.StringIO(private_key_str))

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, pkey=private_key)

    stdin, stdout, stderr = client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode()
    err = stderr.read().decode()
    client.close()

    logger.info(output)
    if exit_status != 0:
        raise RuntimeError(f"SSH command failed (exit {exit_status}): {err}")
    return output
```

## notes
- There is NO prefect-ssh package; use paramiko or fabric directly inside @task
- ssh_conn_id → create a Secret block named "ssh-private-key" with private key PEM content, and pass host/username as flow parameters or separate Secret blocks
- Before running: user must create Secret block(s) for SSH credentials in the Prefect UI or via CLI
- paramiko is the baseline recommendation (stable API surface); fabric is a higher-level option for common SSH patterns
- Use get_run_logger() to log command output
- Always check exit status and raise on non-zero exit to propagate failures to Prefect
- For password auth: store the password in a Secret block instead of the private key
- fabric.Connection is an alternative: `from fabric import Connection; c = Connection(host, user=username); c.run(command)`

## related_concepts
- connection-to-secret-block
- no-package-pattern
{% endsection %}
