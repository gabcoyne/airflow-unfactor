"""Convert Airflow Connections to Prefect Blocks.

Detects connection usage patterns in DAG code and generates:
1. Prefect Block scaffold code with .load() pattern
2. Setup instructions for configuring Blocks in Prefect UI
3. Warnings for unknown or unsupported connection types
"""

import ast
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class BlockInfo:
    """Information about a Prefect Block type."""
    block_class: str  # e.g., "SqlAlchemyConnector"
    import_statement: str  # e.g., "from prefect_sqlalchemy import SqlAlchemyConnector"
    pip_package: str  # e.g., "prefect-sqlalchemy"
    load_pattern: str  # Code template for .load()
    setup_instructions: str  # How to configure in Prefect UI
    connection_url_template: str | None = None  # For database connections


# Mapping from Airflow connection types to Prefect Block info
CONNECTION_TO_BLOCK: dict[str, BlockInfo] = {
    # PostgreSQL
    "postgres": BlockInfo(
        block_class="SqlAlchemyConnector",
        import_statement="from prefect_sqlalchemy import SqlAlchemyConnector",
        pip_package="prefect-sqlalchemy",
        load_pattern='connector = SqlAlchemyConnector.load("{block_name}")',
        setup_instructions="""Setup SqlAlchemyConnector Block in Prefect UI:
1. Go to Blocks > Add Block > SqlAlchemyConnector
2. Name it '{block_name}'
3. Set connection_info:
   - driver: postgresql+psycopg2
   - database: <your_database>
   - username: <your_username>
   - password: <your_password>  # Use Secret block for production
   - host: <your_host>
   - port: 5432
4. Save and reference with: SqlAlchemyConnector.load("{block_name}")""",
        connection_url_template="postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
    ),
    "postgresql": BlockInfo(
        block_class="SqlAlchemyConnector",
        import_statement="from prefect_sqlalchemy import SqlAlchemyConnector",
        pip_package="prefect-sqlalchemy",
        load_pattern='connector = SqlAlchemyConnector.load("{block_name}")',
        setup_instructions="""Setup SqlAlchemyConnector Block in Prefect UI:
1. Go to Blocks > Add Block > SqlAlchemyConnector
2. Name it '{block_name}'
3. Set connection_info:
   - driver: postgresql+psycopg2
   - database: <your_database>
   - username: <your_username>
   - password: <your_password>
   - host: <your_host>
   - port: 5432
4. Save and reference with: SqlAlchemyConnector.load("{block_name}")""",
        connection_url_template="postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
    ),
    # MySQL
    "mysql": BlockInfo(
        block_class="SqlAlchemyConnector",
        import_statement="from prefect_sqlalchemy import SqlAlchemyConnector",
        pip_package="prefect-sqlalchemy",
        load_pattern='connector = SqlAlchemyConnector.load("{block_name}")',
        setup_instructions="""Setup SqlAlchemyConnector Block in Prefect UI:
1. Go to Blocks > Add Block > SqlAlchemyConnector
2. Name it '{block_name}'
3. Set connection_info:
   - driver: mysql+pymysql
   - database: <your_database>
   - username: <your_username>
   - password: <your_password>
   - host: <your_host>
   - port: 3306
4. Save and reference with: SqlAlchemyConnector.load("{block_name}")""",
        connection_url_template="mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
    ),
    # AWS / S3
    "aws": BlockInfo(
        block_class="AwsCredentials",
        import_statement="from prefect_aws import AwsCredentials",
        pip_package="prefect-aws",
        load_pattern='aws_credentials = AwsCredentials.load("{block_name}")',
        setup_instructions="""Setup AwsCredentials Block in Prefect UI:
1. Go to Blocks > Add Block > AwsCredentials
2. Name it '{block_name}'
3. Set credentials:
   - aws_access_key_id: <your_access_key>
   - aws_secret_access_key: <your_secret_key>  # Use Secret block for production
   - region_name: <your_region>  # e.g., us-east-1
4. Save and reference with: AwsCredentials.load("{block_name}")

For S3 operations, also create an S3Bucket block:
1. Go to Blocks > Add Block > S3Bucket
2. Link it to your AwsCredentials block
3. Set bucket_name""",
    ),
    "s3": BlockInfo(
        block_class="S3Bucket",
        import_statement="from prefect_aws import S3Bucket, AwsCredentials",
        pip_package="prefect-aws",
        load_pattern='s3_bucket = S3Bucket.load("{block_name}")',
        setup_instructions="""Setup S3Bucket Block in Prefect UI:
1. First, create an AwsCredentials block with your AWS credentials
2. Go to Blocks > Add Block > S3Bucket
3. Name it '{block_name}'
4. Set:
   - bucket_name: <your_bucket>
   - credentials: Link to your AwsCredentials block
5. Save and reference with: S3Bucket.load("{block_name}")""",
    ),
    # GCP / BigQuery
    "google_cloud_platform": BlockInfo(
        block_class="GcpCredentials",
        import_statement="from prefect_gcp import GcpCredentials",
        pip_package="prefect-gcp",
        load_pattern='gcp_credentials = GcpCredentials.load("{block_name}")',
        setup_instructions="""Setup GcpCredentials Block in Prefect UI:
1. Go to Blocks > Add Block > GcpCredentials
2. Name it '{block_name}'
3. Set credentials:
   - service_account_info: Paste your service account JSON
   - OR service_account_file: Path to service account file
   - project: <your_project_id>
4. Save and reference with: GcpCredentials.load("{block_name}")""",
    ),
    "bigquery": BlockInfo(
        block_class="BigQueryWarehouse",
        import_statement="from prefect_gcp.bigquery import BigQueryWarehouse",
        pip_package="prefect-gcp",
        load_pattern='bq_warehouse = BigQueryWarehouse.load("{block_name}")',
        setup_instructions="""Setup BigQueryWarehouse Block in Prefect UI:
1. First, create a GcpCredentials block with your service account
2. Go to Blocks > Add Block > BigQueryWarehouse
3. Name it '{block_name}'
4. Set:
   - gcp_credentials: Link to your GcpCredentials block
   - fetch_size: 1 (or your preferred batch size)
5. Save and reference with: BigQueryWarehouse.load("{block_name}")""",
    ),
    "google_cloud": BlockInfo(
        block_class="GcpCredentials",
        import_statement="from prefect_gcp import GcpCredentials",
        pip_package="prefect-gcp",
        load_pattern='gcp_credentials = GcpCredentials.load("{block_name}")',
        setup_instructions="""Setup GcpCredentials Block in Prefect UI:
1. Go to Blocks > Add Block > GcpCredentials
2. Name it '{block_name}'
3. Set credentials:
   - service_account_info: Paste your service account JSON
   - project: <your_project_id>
4. Save and reference with: GcpCredentials.load("{block_name}")""",
    ),
    # Snowflake
    "snowflake": BlockInfo(
        block_class="SnowflakeConnector",
        import_statement="from prefect_snowflake import SnowflakeConnector, SnowflakeCredentials",
        pip_package="prefect-snowflake",
        load_pattern='snowflake = SnowflakeConnector.load("{block_name}")',
        setup_instructions="""Setup SnowflakeConnector Block in Prefect UI:
1. First, create a SnowflakeCredentials block:
   - account: <your_account>  # e.g., xy12345.us-east-1
   - user: <your_username>
   - password: <your_password>  # Use Secret block for production
2. Go to Blocks > Add Block > SnowflakeConnector
3. Name it '{block_name}'
4. Set:
   - credentials: Link to your SnowflakeCredentials block
   - database: <your_database>
   - warehouse: <your_warehouse>
   - schema: <your_schema>
5. Save and reference with: SnowflakeConnector.load("{block_name}")""",
    ),
    # Slack
    "slack": BlockInfo(
        block_class="SlackWebhook",
        import_statement="from prefect_slack import SlackWebhook",
        pip_package="prefect-slack",
        load_pattern='slack_webhook = SlackWebhook.load("{block_name}")',
        setup_instructions="""Setup SlackWebhook Block in Prefect UI:
1. Go to Blocks > Add Block > SlackWebhook
2. Name it '{block_name}'
3. Set:
   - url: <your_webhook_url>  # From Slack App Incoming Webhooks
4. Save and reference with: SlackWebhook.load("{block_name}")

To get a webhook URL:
1. Go to api.slack.com/apps
2. Create or select your app
3. Enable Incoming Webhooks
4. Add a webhook to your workspace""",
    ),
    "slack_webhook": BlockInfo(
        block_class="SlackWebhook",
        import_statement="from prefect_slack import SlackWebhook",
        pip_package="prefect-slack",
        load_pattern='slack_webhook = SlackWebhook.load("{block_name}")',
        setup_instructions="""Setup SlackWebhook Block in Prefect UI:
1. Go to Blocks > Add Block > SlackWebhook
2. Name it '{block_name}'
3. Set url: <your_webhook_url>
4. Save and reference with: SlackWebhook.load("{block_name}")""",
    ),
    # HTTP connections
    "http": BlockInfo(
        block_class="None",
        import_statement="import httpx",
        pip_package="httpx",
        load_pattern="# HTTP connections use httpx directly - no Block needed",
        setup_instructions="""HTTP connections in Prefect:
Prefect doesn't require a Block for HTTP connections. Use httpx directly:

    import httpx

    @task
    def call_api():
        response = httpx.get("https://api.example.com/endpoint")
        return response.json()

For authenticated APIs, store credentials in environment variables or use
a Secret block for sensitive values.""",
    ),
    # SSH
    "ssh": BlockInfo(
        block_class="None",
        import_statement="import paramiko",
        pip_package="paramiko",
        load_pattern="# SSH connections use paramiko directly",
        setup_instructions="""SSH connections in Prefect:
Use the paramiko library directly. Store SSH keys as files or use
environment variables / Secret blocks for credentials.

    import paramiko

    @task
    def run_ssh_command():
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect('hostname', username='user', key_filename='/path/to/key')
        stdin, stdout, stderr = client.exec_command('ls -la')
        return stdout.read().decode()""",
    ),
    # SFTP
    "sftp": BlockInfo(
        block_class="None",
        import_statement="import paramiko",
        pip_package="paramiko",
        load_pattern="# SFTP connections use paramiko directly",
        setup_instructions="""SFTP connections in Prefect:
Use the paramiko library for SFTP operations.

    import paramiko

    @task
    def download_file():
        transport = paramiko.Transport(('hostname', 22))
        transport.connect(username='user', password='pass')
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get('/remote/path', '/local/path')
        sftp.close()
        transport.close()""",
    ),
    # Azure
    "azure": BlockInfo(
        block_class="AzureBlobStorageCredentials",
        import_statement="from prefect_azure import AzureBlobStorageCredentials",
        pip_package="prefect-azure",
        load_pattern='azure_creds = AzureBlobStorageCredentials.load("{block_name}")',
        setup_instructions="""Setup AzureBlobStorageCredentials Block in Prefect UI:
1. Go to Blocks > Add Block > AzureBlobStorageCredentials
2. Name it '{block_name}'
3. Set:
   - connection_string: <your_connection_string>
   - OR account_url + credential (for Azure AD auth)
4. Save and reference with: AzureBlobStorageCredentials.load("{block_name}")""",
    ),
    "wasb": BlockInfo(
        block_class="AzureBlobStorageCredentials",
        import_statement="from prefect_azure import AzureBlobStorageCredentials",
        pip_package="prefect-azure",
        load_pattern='azure_creds = AzureBlobStorageCredentials.load("{block_name}")',
        setup_instructions="""Setup AzureBlobStorageCredentials Block:
1. Go to Blocks > Add Block > AzureBlobStorageCredentials
2. Name it '{block_name}'
3. Set connection_string or account_url + credential
4. Save and reference with: AzureBlobStorageCredentials.load("{block_name}")""",
    ),
    # Databricks
    "databricks": BlockInfo(
        block_class="DatabricksCredentials",
        import_statement="from prefect_databricks import DatabricksCredentials",
        pip_package="prefect-databricks",
        load_pattern='databricks_creds = DatabricksCredentials.load("{block_name}")',
        setup_instructions="""Setup DatabricksCredentials Block in Prefect UI:
1. Go to Blocks > Add Block > DatabricksCredentials
2. Name it '{block_name}'
3. Set:
   - databricks_instance: <your_workspace_url>  # e.g., adb-xxx.azuredatabricks.net
   - databricks_token: <your_personal_access_token>
4. Save and reference with: DatabricksCredentials.load("{block_name}")""",
    ),
}


@dataclass
class ConnectionInfo:
    """Information about a detected Airflow connection."""
    name: str  # Connection ID (e.g., "my_postgres_conn")
    conn_type: str | None  # Inferred connection type (e.g., "postgres")
    hook_class: str | None  # Hook class if detected (e.g., "PostgresHook")
    line_number: int = 0


# Map hook classes to connection types
HOOK_TO_CONN_TYPE: dict[str, str] = {
    "PostgresHook": "postgres",
    "MySqlHook": "mysql",
    "MsSqlHook": "mssql",
    "OracleHook": "oracle",
    "SqliteHook": "sqlite",
    "S3Hook": "s3",
    "AwsBaseHook": "aws",
    "RedshiftSQLHook": "postgres",
    "GCSHook": "google_cloud",
    "BigQueryHook": "bigquery",
    "SnowflakeHook": "snowflake",
    "SlackHook": "slack",
    "SlackWebhookHook": "slack_webhook",
    "HttpHook": "http",
    "SSHHook": "ssh",
    "SFTPHook": "sftp",
    "WasbHook": "wasb",
    "AzureDataFactoryHook": "azure",
    "DatabricksHook": "databricks",
}

# Patterns for inferring connection types from connection IDs
CONN_ID_PATTERNS: list[tuple[str, str]] = [
    (r"postgres", "postgres"),
    (r"postgresql", "postgres"),
    (r"pg_", "postgres"),
    (r"mysql", "mysql"),
    (r"snowflake", "snowflake"),
    (r"sf_", "snowflake"),
    (r"bigquery", "bigquery"),
    (r"bq_", "bigquery"),
    (r"gcp", "google_cloud"),
    (r"google", "google_cloud"),
    (r"aws", "aws"),
    (r"s3", "s3"),
    (r"slack", "slack"),
    (r"http", "http"),
    (r"ssh", "ssh"),
    (r"sftp", "sftp"),
    (r"azure", "azure"),
    (r"wasb", "wasb"),
    (r"databricks", "databricks"),
]


def infer_conn_type_from_id(conn_id: str) -> str | None:
    """Infer connection type from connection ID naming patterns."""
    conn_id_lower = conn_id.lower()
    for pattern, conn_type in CONN_ID_PATTERNS:
        if re.search(pattern, conn_id_lower):
            return conn_type
    return None


class ConnectionVisitor(ast.NodeVisitor):
    """AST visitor to extract connection usage patterns."""

    def __init__(self):
        self.connections: list[ConnectionInfo] = []
        self._seen_conn_ids: set[str] = set()

    def visit_Call(self, node: ast.Call):
        """Detect connection usage patterns."""
        # Pattern 1: Hook instantiation with conn_id
        # e.g., PostgresHook(postgres_conn_id="x")
        self._check_hook_instantiation(node)

        # Pattern 2: BaseHook.get_connection("x")
        self._check_base_hook_get_connection(node)

        # Pattern 3: Operator with *conn_id parameter
        # e.g., SomeOperator(task_id="x", postgres_conn_id="y")
        self._check_operator_conn_id(node)

        self.generic_visit(node)

    def _check_hook_instantiation(self, node: ast.Call):
        """Check for Hook class instantiation with conn_id parameter."""
        func_name = self._get_func_name(node)
        if not func_name or not func_name.endswith("Hook"):
            return

        conn_type = HOOK_TO_CONN_TYPE.get(func_name)

        for kw in node.keywords:
            if kw.arg and kw.arg.endswith("_conn_id"):
                conn_id = self._get_string_value(kw.value)
                if conn_id and conn_id not in self._seen_conn_ids:
                    self._seen_conn_ids.add(conn_id)
                    self.connections.append(ConnectionInfo(
                        name=conn_id,
                        conn_type=conn_type or infer_conn_type_from_id(conn_id),
                        hook_class=func_name,
                        line_number=node.lineno,
                    ))

    def _check_base_hook_get_connection(self, node: ast.Call):
        """Check for BaseHook.get_connection("conn_id") pattern."""
        # Check for method call pattern: BaseHook.get_connection(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "get_connection":
                # Get connection ID from first argument
                if node.args:
                    conn_id = self._get_string_value(node.args[0])
                    if conn_id and conn_id not in self._seen_conn_ids:
                        self._seen_conn_ids.add(conn_id)
                        self.connections.append(ConnectionInfo(
                            name=conn_id,
                            conn_type=infer_conn_type_from_id(conn_id),
                            hook_class=None,
                            line_number=node.lineno,
                        ))

    def _check_operator_conn_id(self, node: ast.Call):
        """Check for Operator instantiation with conn_id parameters."""
        func_name = self._get_func_name(node)
        if not func_name or not func_name.endswith("Operator"):
            return

        for kw in node.keywords:
            if kw.arg and kw.arg.endswith("_conn_id"):
                conn_id = self._get_string_value(kw.value)
                if conn_id and conn_id not in self._seen_conn_ids:
                    self._seen_conn_ids.add(conn_id)
                    # Try to infer connection type from parameter name
                    conn_type = None
                    param_prefix = kw.arg.replace("_conn_id", "")
                    if param_prefix in ("postgres", "postgresql"):
                        conn_type = "postgres"
                    elif param_prefix == "mysql":
                        conn_type = "mysql"
                    elif param_prefix == "snowflake":
                        conn_type = "snowflake"
                    elif param_prefix in ("http", "https"):
                        conn_type = "http"
                    elif param_prefix in ("gcp", "google_cloud"):
                        conn_type = "google_cloud"
                    elif param_prefix in ("aws", "s3"):
                        conn_type = "s3"
                    elif param_prefix == "slack":
                        conn_type = "slack"
                    elif param_prefix == "ssh":
                        conn_type = "ssh"

                    if not conn_type:
                        conn_type = infer_conn_type_from_id(conn_id)

                    self.connections.append(ConnectionInfo(
                        name=conn_id,
                        conn_type=conn_type,
                        hook_class=None,
                        line_number=node.lineno,
                    ))

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function/class name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _get_string_value(self, node: ast.expr) -> str | None:
        """Extract string value from AST node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None


def extract_connections(dag_code: str) -> list[ConnectionInfo]:
    """Extract connection usage from DAG code.

    Detects patterns:
    - Hook instantiation: PostgresHook(postgres_conn_id="x")
    - BaseHook.get_connection("x")
    - Operator conn_id parameters: SomeOperator(postgres_conn_id="x")

    Args:
        dag_code: Source code of the DAG file

    Returns:
        List of detected connections
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return []

    visitor = ConnectionVisitor()
    visitor.visit(tree)
    return visitor.connections


def generate_block_scaffold(
    info: ConnectionInfo,
    include_comments: bool = True,
) -> tuple[str, str, list[str]]:
    """Generate Prefect Block scaffold code for a connection.

    Args:
        info: Connection information
        include_comments: Include educational comments

    Returns:
        Tuple of (code, setup_instructions, warnings)
    """
    warnings: list[str] = []
    block_name = _sanitize_block_name(info.name)

    # Look up Block info
    block_info = None
    if info.conn_type:
        block_info = CONNECTION_TO_BLOCK.get(info.conn_type)

    if not block_info:
        # Unknown connection type
        warnings.append(
            f"Unknown connection type for '{info.name}'. "
            f"Manual configuration required."
        )
        code_lines = []
        if include_comments:
            code_lines.append(f"# Connection: {info.name}")
            code_lines.append(f"# Type: {info.conn_type or 'unknown'}")
            if info.hook_class:
                code_lines.append(f"# Hook: {info.hook_class}")
            code_lines.append("# TODO: Configure appropriate Prefect Block")
            code_lines.append("")

        code_lines.append("# Manual configuration required for this connection")
        code_lines.append(f'# Original Airflow connection ID: "{info.name}"')

        setup = f"""Unknown connection type: {info.conn_type or 'unknown'}

The connection '{info.name}' uses an unrecognized connection type.
You'll need to:
1. Identify the equivalent Prefect Block or library
2. Configure credentials appropriately
3. Replace Airflow Hook usage with Prefect Block .load() pattern

See Prefect documentation: https://docs.prefect.io/latest/concepts/blocks/"""

        return "\n".join(code_lines), setup, warnings

    # Generate code scaffold
    code_lines = []
    if include_comments:
        code_lines.append(f"# Connection: {info.name} -> Prefect Block: {block_info.block_class}")
        if info.hook_class:
            code_lines.append(f"# Replaces: {info.hook_class}")
        code_lines.append("")

    code_lines.append(block_info.import_statement)
    code_lines.append("")
    code_lines.append(block_info.load_pattern.format(block_name=block_name))

    # Format setup instructions with block name
    setup = block_info.setup_instructions.format(block_name=block_name)

    return "\n".join(code_lines), setup, warnings


def _sanitize_block_name(conn_id: str) -> str:
    """Convert Airflow connection ID to valid Prefect block name.

    Prefect block names must be lowercase with hyphens.
    """
    # Replace underscores with hyphens, lowercase
    name = conn_id.lower().replace("_", "-")
    # Remove any invalid characters
    name = re.sub(r"[^a-z0-9-]", "", name)
    # Ensure doesn't start or end with hyphen
    name = name.strip("-")
    return name or "default-connection"


def convert_all_connections(
    dag_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert all detected connections to Prefect Block scaffolds.

    Args:
        dag_code: Source code of the DAG file
        include_comments: Include educational comments

    Returns:
        Dictionary with:
        - connections: List of ConnectionInfo
        - scaffolds: List of (code, setup, warnings) tuples
        - combined_code: All scaffold code combined
        - combined_setup: All setup instructions combined
        - all_warnings: All warnings
        - pip_packages: Required pip packages
    """
    connections = extract_connections(dag_code)

    if not connections:
        return {
            "connections": [],
            "scaffolds": [],
            "combined_code": "",
            "combined_setup": "No Airflow connections detected.",
            "all_warnings": [],
            "pip_packages": [],
        }

    scaffolds = []
    all_code = []
    all_setup = []
    all_warnings = []
    pip_packages: set[str] = set()

    for conn in connections:
        code, setup, warnings = generate_block_scaffold(conn, include_comments)
        scaffolds.append((code, setup, warnings))
        all_code.append(code)
        all_setup.append(f"## {conn.name}\n\n{setup}")
        all_warnings.extend(warnings)

        # Collect pip packages
        if conn.conn_type and conn.conn_type in CONNECTION_TO_BLOCK:
            pkg = CONNECTION_TO_BLOCK[conn.conn_type].pip_package
            if pkg and pkg != "httpx":  # httpx is usually already available
                pip_packages.add(pkg)

    combined_code = "\n\n".join(all_code)
    combined_setup = "\n\n---\n\n".join(all_setup)

    return {
        "connections": connections,
        "scaffolds": scaffolds,
        "combined_code": combined_code,
        "combined_setup": combined_setup,
        "all_warnings": all_warnings,
        "pip_packages": sorted(pip_packages),
    }


def summarize_connection_support() -> str:
    """Generate a summary of supported connection type conversions."""
    lines = ["# Supported Airflow Connection Type Conversions", ""]

    categories = {
        "Databases": ["postgres", "postgresql", "mysql", "snowflake", "bigquery"],
        "Cloud Storage": ["s3", "aws", "google_cloud", "google_cloud_platform", "azure", "wasb"],
        "Messaging": ["slack", "slack_webhook"],
        "Compute": ["databricks"],
        "Network": ["http", "ssh", "sftp"],
    }

    for category, conn_types in categories.items():
        lines.append(f"## {category}")
        for conn_type in conn_types:
            if conn_type in CONNECTION_TO_BLOCK:
                block = CONNECTION_TO_BLOCK[conn_type]
                lines.append(f"- {conn_type} -> {block.block_class} ({block.pip_package})")
        lines.append("")

    return "\n".join(lines)
