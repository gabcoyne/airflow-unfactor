"""Convert Airflow Datasets to Prefect Events.

See specs/dataset-event-converter.openspec.md for specification.
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


@dataclass
class DatasetInfo:
    """Information about a detected Dataset/Asset."""
    name: str  # Variable name
    uri: str   # Dataset URI
    event_name: str  # Converted Prefect event name
    line_number: int = 0
    is_asset: bool = False  # True for Airflow 3.x Assets


@dataclass
class ProducerInfo:
    """Task that produces (updates) a dataset."""
    task_name: str
    datasets: list[str]  # Dataset variable names
    line_number: int = 0


@dataclass
class ConsumerInfo:
    """DAG that consumes (triggered by) datasets."""
    dag_name: str
    datasets: list[str]  # Dataset variable names
    line_number: int = 0


@dataclass 
class DatasetAnalysis:
    """Complete analysis of Dataset usage in a DAG file."""
    datasets: list[DatasetInfo] = field(default_factory=list)
    producers: list[ProducerInfo] = field(default_factory=list)
    consumers: list[ConsumerInfo] = field(default_factory=list)
    
    @property
    def event_names(self) -> list[str]:
        return [d.event_name for d in self.datasets]
    
    @property
    def has_datasets(self) -> bool:
        return len(self.datasets) > 0

    @property
    def assets(self) -> list[DatasetInfo]:
        return [d for d in self.datasets if d.is_asset]


def uri_to_event_name(uri: str) -> str:
    """Convert a Dataset URI to a Prefect event name.
    
    Examples:
        s3://my-bucket/path/data.csv -> dataset.s3.my-bucket.path.data
        gs://bucket/data -> dataset.gs.bucket.data
        file:///path/to/file -> dataset.file.path.to.file
    """
    parsed = urlparse(uri)
    
    # Build event name from scheme, host, path
    parts = ["dataset"]
    
    if parsed.scheme:
        parts.append(parsed.scheme)
    
    if parsed.netloc:
        parts.append(parsed.netloc.replace("-", "_"))
    
    if parsed.path:
        # Remove leading slash, split, remove extension
        path_parts = parsed.path.strip("/").split("/")
        for part in path_parts:
            # Remove file extension and sanitize
            clean = part.rsplit(".", 1)[0]
            clean = re.sub(r"[^a-zA-Z0-9_]", "_", clean)
            if clean:
                parts.append(clean)
    
    return ".".join(parts)


class DatasetVisitor(ast.NodeVisitor):
    """AST visitor to extract Dataset patterns."""
    
    def __init__(self):
        self.datasets: dict[str, DatasetInfo] = {}  # var_name -> info
        self.producers: list[ProducerInfo] = []
        self.consumers: list[ConsumerInfo] = []
        self.current_dag: str | None = None
        
    def visit_Assign(self, node: ast.Assign):
        """Detect Dataset/Asset instantiation."""
        if isinstance(node.value, ast.Call):
            func_name = ""
            if isinstance(node.value.func, ast.Name):
                func_name = node.value.func.id
            elif isinstance(node.value.func, ast.Attribute):
                func_name = node.value.func.attr
            
            if func_name in ("Dataset", "Asset"):
                # Get variable name
                if node.targets and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id
                    
                    # Get URI from first argument
                    uri = ""
                    if node.value.args and isinstance(node.value.args[0], ast.Constant):
                        uri = node.value.args[0].value
                    
                    self.datasets[var_name] = DatasetInfo(
                        name=var_name,
                        uri=uri,
                        event_name=uri_to_event_name(uri),
                        line_number=node.lineno,
                        is_asset=(func_name == "Asset"),
                    )
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Detect @task(outlets=) and @dag(schedule=)."""
        for decorator in node.decorator_list:
            dec_str = ast.unparse(decorator)
            
            # Check for @dag with schedule containing datasets
            if "dag" in dec_str and "schedule" in dec_str:
                datasets = self._extract_schedule_datasets(decorator)
                if datasets:
                    self.consumers.append(ConsumerInfo(
                        dag_name=node.name,
                        datasets=datasets,
                        line_number=node.lineno,
                    ))
            
            # Check for @task with outlets
            if "task" in dec_str and "outlets" in dec_str:
                datasets = self._extract_outlets(decorator)
                if datasets:
                    self.producers.append(ProducerInfo(
                        task_name=node.name,
                        datasets=datasets,
                        line_number=node.lineno,
                    ))
        
        self.generic_visit(node)
    
    def _extract_schedule_datasets(self, decorator: ast.expr) -> list[str]:
        """Extract dataset names from schedule parameter."""
        datasets = []
        if isinstance(decorator, ast.Call):
            for kw in decorator.keywords:
                if kw.arg == "schedule":
                    datasets = self._extract_names_from_value(kw.value)
        return datasets
    
    def _extract_outlets(self, decorator: ast.expr) -> list[str]:
        """Extract dataset names from outlets parameter."""
        datasets = []
        if isinstance(decorator, ast.Call):
            for kw in decorator.keywords:
                if kw.arg == "outlets":
                    datasets = self._extract_names_from_value(kw.value)
        return datasets
    
    def _extract_names_from_value(self, value: ast.expr) -> list[str]:
        """Extract variable names from a list or single value."""
        names = []
        if isinstance(value, ast.List):
            for elt in value.elts:
                if isinstance(elt, ast.Name):
                    names.append(elt.id)
        elif isinstance(value, ast.Name):
            names.append(value.id)
        return names


def analyze_datasets(dag_code: str) -> DatasetAnalysis:
    """Analyze Dataset usage in DAG code.
    
    Args:
        dag_code: Source code of the DAG file
        
    Returns:
        DatasetAnalysis with detected datasets, producers, consumers
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return DatasetAnalysis()
    
    visitor = DatasetVisitor()
    visitor.visit(tree)
    
    return DatasetAnalysis(
        datasets=list(visitor.datasets.values()),
        producers=visitor.producers,
        consumers=visitor.consumers,
    )


def generate_event_code(
    analysis: DatasetAnalysis,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Generate Prefect event emission code.
    
    Args:
        analysis: Dataset analysis result
        include_comments: Include educational comments
        
    Returns:
        Dictionary with producer_code, deployment_yaml, notes, events, assets,
        and materialization_code
    """
    lines = []
    deployment_triggers = []
    notes = []
    
    if not analysis.has_datasets:
        return {
            "producer_code": "",
            "deployment_yaml": "",
            "notes": ["No Datasets detected"],
            "events": [],
            "assets": [],
            "materialization_code": "",
        }
    
    if include_comments:
        lines.append("# \u2728 Prefect Events: Converting Airflow Datasets")
        lines.append("# Datasets in Airflow trigger downstream DAGs when updated.")
        lines.append("# In Prefect, use Events + Automations for the same pattern.")
        lines.append("")
    
    lines.append("from prefect.events import emit_event")
    lines.append("")
    
    dataset_map = {d.name: d for d in analysis.datasets}

    # Generate emit_event calls for each producer
    for producer in analysis.producers:
        if include_comments:
            lines.append(f"# Task '{producer.task_name}' produces datasets/assets:")
        
        for ds_name in producer.datasets:
            if ds_name in dataset_map:
                ds = dataset_map[ds_name]
                lines.append(f"")
                lines.append(f"def emit_{ds_name}_updated():")
                lines.append(f"    \"\"\"Emit event when {ds_name} is updated.\"\"\"")
                lines.append(f"    emit_event(")
                lines.append(f'        event="{ds.event_name}.updated",') 
                lines.append(f"        resource={{\"prefect.resource.id\": \"{ds.uri}\"}}")
                lines.append(f"    )")
    
    # Generate deployment trigger YAML for consumers
    for consumer in analysis.consumers:
        notes.append(f"DAG '{consumer.dag_name}' should be deployed with event triggers")
        
        for ds_name in consumer.datasets:
            if ds_name in dataset_map:
                ds = dataset_map[ds_name]
                deployment_triggers.append({
                    "match": {"prefect.resource.id": ds.uri},
                    "expect": [f"{ds.event_name}.updated"],
                })
    
    # Format deployment YAML
    deployment_yaml = ""
    if deployment_triggers:
        deployment_yaml = f"""# Prefect Deployment triggers (prefect.yaml)
triggers:"""
        for trigger in deployment_triggers:
            deployment_yaml += f"""\n  - match:\n      prefect.resource.id: "{trigger['match']['prefect.resource.id']}"\n    expect:\n      - "{trigger['expect'][0]}"\n"""
    
    materialization_lines: list[str] = []
    if analysis.assets:
        if include_comments:
            materialization_lines.append("# Airflow 3.x Asset materialization scaffold")
            materialization_lines.append(
                "# Exact Prefect asset APIs may vary by Prefect version."
            )
        materialization_lines.append("from prefect.assets import materialize")
        materialization_lines.append("")
        for asset in analysis.assets:
            materialization_lines.append(f"@materialize(\"{asset.uri}\")")
            materialization_lines.append(f"def materialize_{asset.name}() -> str:")
            materialization_lines.append(f"    \"\"\"Materialize asset '{asset.name}'.\"\"\"")
            materialization_lines.append(f"    # TODO: replace with your concrete Prefect asset API usage")
            materialization_lines.append(f"    return \"{asset.uri}\"")
            materialization_lines.append("")
        notes.append(
            "Assets detected: generated materialization scaffold. "
            "Finalize concrete Prefect asset API for your runtime version."
        )

    return {
        "producer_code": "\n".join(lines),
        "deployment_yaml": deployment_yaml,
        "notes": notes,
        "events": [d.event_name for d in analysis.datasets],
        "assets": [
            {
                "name": asset.name,
                "uri": asset.uri,
                "event_name": asset.event_name,
                "line_number": asset.line_number,
            }
            for asset in analysis.assets
        ],
        "materialization_code": "\n".join(materialization_lines).strip(),
    }
