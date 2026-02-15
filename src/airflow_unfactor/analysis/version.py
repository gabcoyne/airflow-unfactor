"""Detect Airflow version from DAG source code.

See specs/airflow-version-detection.openspec.md for full specification.
"""

import ast
import re
from dataclasses import dataclass, field

# Import patterns that indicate specific versions
# Key is the import module, value is (major, minor)
IMPORT_PATTERNS = {
    # Airflow 1.x patterns (old module structure)
    "airflow.operators.python_operator": (1, None),
    "airflow.operators.dummy_operator": (1, None),
    "airflow.operators.bash_operator": (1, None),
    
    # Airflow 2.x patterns (module restructure)
    "airflow.operators.python": (2, 0),
    "airflow.operators.bash": (2, 0),
    "airflow.operators.empty": (2, 0),
    "airflow.decorators": (2, 0),
    
    # Airflow 2.4+ (Datasets)
    "airflow.datasets": (2, 4),
    
    # Airflow 3.x (Assets replace Datasets)
    "airflow.assets": (3, 0),
}

# Feature detection patterns
FEATURE_PATTERNS = {
    "taskflow": [
        r"@dag\b",
        r"@task\b",
        r"from airflow\.decorators import",
    ],
    "datasets": [
        r"from airflow\.datasets import",
        r"Dataset\(",
    ],
    "assets": [
        r"from airflow\.assets import",
        r"Asset\(",
    ],
    "task_bash": [
        r"@task\.bash\b",
    ],
    "dynamic_task_mapping": [
        r"\.expand\(",
        r"\.partial\(",
    ],
    "empty_operator": [
        r"EmptyOperator\(",
        r"from airflow\.operators\.empty import",
    ],
    "dummy_operator": [
        r"DummyOperator\(",
        r"from airflow\.operators\.dummy",
    ],
}


@dataclass
class AirflowVersion:
    """Detected Airflow version with feature flags."""
    
    major: int = 2  # Default to 2.x (most common)
    minor: int | None = None
    
    # Feature flags
    has_taskflow: bool = False
    has_datasets: bool = False
    has_assets: bool = False
    has_task_bash: bool = False
    has_dynamic_task_mapping: bool = False
    has_empty_operator: bool = False
    has_dummy_operator: bool = False
    
    # Confidence and evidence
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    
    @property
    def version_string(self) -> str:
        """Human-readable version string."""
        if self.minor is not None:
            return f"{self.major}.{self.minor}+"
        return f"{self.major}.x"
    
    def __str__(self) -> str:
        features = []
        if self.has_taskflow:
            features.append("TaskFlow")
        if self.has_datasets:
            features.append("Datasets")
        if self.has_assets:
            features.append("Assets")
        if self.has_task_bash:
            features.append("@task.bash")
        if self.has_dynamic_task_mapping:
            features.append("DynamicMapping")
        
        feature_str = ", ".join(features) if features else "basic"
        return f"Airflow {self.version_string} ({feature_str}) [{self.confidence:.0%} confidence]"


class VersionDetector(ast.NodeVisitor):
    """AST visitor to detect Airflow version patterns."""
    
    def __init__(self):
        self.imports: list[str] = []
        self.decorators: list[str] = []
        self.calls: list[str] = []
        
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        for decorator in node.decorator_list:
            self.decorators.append(ast.unparse(decorator))
        self.generic_visit(node)
        
    def visit_Call(self, node: ast.Call):
        import contextlib
        with contextlib.suppress(Exception):
            self.calls.append(ast.unparse(node.func))
        self.generic_visit(node)


def detect_airflow_version(dag_code: str) -> AirflowVersion:
    """Detect Airflow version from DAG source code.
    
    Analyzes imports, decorators, and patterns to determine the Airflow
    version and available features.
    
    Args:
        dag_code: Source code of the DAG file
        
    Returns:
        AirflowVersion with detected version and feature flags
    """
    result = AirflowVersion()
    evidence = []
    version_signals: list[tuple[int, int | None]] = []
    
    # Parse AST
    try:
        tree = ast.parse(dag_code)
        visitor = VersionDetector()
        visitor.visit(tree)
    except SyntaxError:
        result.confidence = 0.0
        result.evidence = ["Failed to parse DAG"]
        return result
    
    # Check imports against known patterns
    for imp in visitor.imports:
        for pattern, version in IMPORT_PATTERNS.items():
            if imp == pattern or imp.startswith(pattern + "."):
                version_signals.append(version)
                evidence.append(f"Import '{imp}' suggests Airflow {version[0]}.{version[1] or 'x'}")
    
    # Check for features using regex on source
    for feature, patterns in FEATURE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, dag_code):
                setattr(result, f"has_{feature}", True)
                evidence.append(f"Found {feature} pattern: {pattern}")
                break
    
    # Infer version from features
    if result.has_assets:
        version_signals.append((3, 0))
        evidence.append("Assets API indicates Airflow 3.x")
    elif result.has_task_bash:
        version_signals.append((2, 9))
        evidence.append("@task.bash indicates Airflow 2.9+")
    elif result.has_datasets:
        version_signals.append((2, 4))
        evidence.append("Datasets API indicates Airflow 2.4+")
    elif result.has_dynamic_task_mapping:
        version_signals.append((2, 3))
        evidence.append("Dynamic task mapping indicates Airflow 2.3+")
    elif result.has_taskflow:
        version_signals.append((2, 0))
        evidence.append("TaskFlow API indicates Airflow 2.0+")
    
    # DummyOperator is a 1.x signal
    if result.has_dummy_operator:
        evidence.append("DummyOperator suggests Airflow 1.x or early 2.x")
    
    # Determine final version
    if version_signals:
        # Check for 1.x signals
        has_1x = any(v[0] == 1 for v in version_signals)
        has_2x_plus = any(v[0] >= 2 for v in version_signals)
        
        if has_1x and not has_2x_plus:
            # Pure 1.x
            result.major = 1
            result.minor = None
        else:
            # Take the highest version indicated (ignoring 1.x if 2.x+ present)
            non_1x = [v for v in version_signals if v[0] >= 2] or version_signals
            max_major = max(v[0] for v in non_1x)
            same_major = [v for v in non_1x if v[0] == max_major]
            max_minor = max((v[1] or 0) for v in same_major)
            
            result.major = max_major
            result.minor = max_minor if max_minor > 0 else None
        
        # Calculate confidence
        if len(version_signals) >= 3:
            result.confidence = 0.9
        elif len(version_signals) >= 2:
            result.confidence = 0.8
        else:
            result.confidence = 0.6
            
        # Check for conflicting signals (1.x vs 2.x+)
        majors = set(v[0] for v in version_signals)
        if 1 in majors and len(majors) > 1:
            result.confidence = min(result.confidence, 0.5)
            evidence.append("Mixed version signals: likely upgrading from 1.x")
    
    result.evidence = evidence
    return result
