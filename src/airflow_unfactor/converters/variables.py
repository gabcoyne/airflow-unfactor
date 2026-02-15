"""Convert Airflow Variables to Prefect configuration options.

Detects Variable.get() and Variable.set() patterns in Airflow DAGs
and generates scaffold code with recommendations for:
- Prefect Secrets (for sensitive values)
- Prefect Variables (for dynamic, non-sensitive values)
- Flow parameters (for static configuration with defaults)
"""

import ast
import re
from dataclasses import dataclass
from typing import Any

# Patterns that indicate sensitive values - match anywhere in variable name
SENSITIVE_PATTERNS: list[str] = [
    "key",
    "password",
    "secret",
    "token",
    "credential",
    "auth",
    "api_key",
    "apikey",
    "private",
    "passphrase",
]


@dataclass
class VariableInfo:
    """Information about a detected Airflow Variable usage."""

    name: str
    default_value: str | None = None
    is_set: bool = False  # True if Variable.set(), False if Variable.get()
    is_sensitive: bool = False
    line_number: int = 0


class VariableVisitor(ast.NodeVisitor):
    """AST visitor to detect Variable.get() and Variable.set() patterns."""

    def __init__(self):
        self.variables: list[VariableInfo] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to detect Variable.get/set patterns."""
        method_name = self._get_method_name(node)

        if method_name in ("get", "set") and self._is_variable_call(node):
            var_info = self._extract_variable_info(node, method_name)
            if var_info:
                self.variables.append(var_info)

        self.generic_visit(node)

    def _get_method_name(self, node: ast.Call) -> str:
        """Extract method name from a call node."""
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _is_variable_call(self, node: ast.Call) -> bool:
        """Check if this is a call on Variable (Variable.get/Variable.set)."""
        if isinstance(node.func, ast.Attribute):
            # Check for Variable.get() or Variable.set()
            if isinstance(node.func.value, ast.Name):
                return node.func.value.id == "Variable"
            # Check for models.Variable.get() pattern
            if isinstance(node.func.value, ast.Attribute):
                return node.func.value.attr == "Variable"
        return False

    def _extract_variable_info(self, node: ast.Call, method_name: str) -> VariableInfo | None:
        """Extract variable information from a Variable.get/set call."""
        var_name: str | None = None
        default_value: str | None = None
        is_set = method_name == "set"

        # Get variable name from first positional argument
        if node.args:
            if isinstance(node.args[0], ast.Constant):
                var_name = str(node.args[0].value)
            else:
                # Try to unparse complex expressions
                try:
                    var_name = ast.unparse(node.args[0])
                except Exception:
                    var_name = "<dynamic>"

        # For Variable.set, the second arg is the value (not default)
        # For Variable.get, check for default_var keyword
        if not is_set:
            # Check keyword arguments for default_var
            for kw in node.keywords:
                if kw.arg == "default_var":
                    if isinstance(kw.value, ast.Constant):
                        default_value = repr(kw.value.value)
                    else:
                        try:
                            default_value = ast.unparse(kw.value)
                        except Exception:
                            default_value = "<expression>"

            # Also check second positional argument (older API style)
            if len(node.args) >= 2 and default_value is None:
                if isinstance(node.args[1], ast.Constant):
                    default_value = repr(node.args[1].value)
                else:
                    try:
                        default_value = ast.unparse(node.args[1])
                    except Exception:
                        default_value = "<expression>"

        if not var_name:
            return None

        # Determine if variable is sensitive based on name patterns
        is_sensitive = _is_sensitive_name(var_name)

        return VariableInfo(
            name=var_name,
            default_value=default_value,
            is_set=is_set,
            is_sensitive=is_sensitive,
            line_number=node.lineno,
        )


def _is_sensitive_name(name: str) -> bool:
    """Check if a variable name matches sensitive patterns."""
    name_lower = name.lower()
    return any(pattern in name_lower for pattern in SENSITIVE_PATTERNS)


def extract_variables(dag_code: str) -> list[VariableInfo]:
    """Extract Variable usage from DAG code.

    Args:
        dag_code: Source code of the DAG file

    Returns:
        List of detected variable usages
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return []

    visitor = VariableVisitor()
    visitor.visit(tree)
    return visitor.variables


def generate_variable_scaffold(
    info: VariableInfo,
) -> tuple[str, str, list[str]]:
    """Generate Prefect code options for an Airflow Variable.

    Args:
        info: VariableInfo describing the variable

    Returns:
        Tuple of (code_options, setup_instructions, warnings)
        - code_options: Multi-option code showing different approaches
        - setup_instructions: Instructions for setting up the variable
        - warnings: List of warning messages
    """
    warnings: list[str] = []
    code_lines: list[str] = []
    setup_lines: list[str] = []

    # Clean variable name for use as Python identifier
    safe_name = _to_python_identifier(info.name)

    if info.is_set:
        # Variable.set() requires Prefect Variable (not Secret or parameter)
        warnings.append(
            f"Variable.set('{info.name}') detected. "
            "Dynamic writes require Prefect Variables API, not Secrets or parameters."
        )
        code_lines.extend(_generate_variable_set_code(info, safe_name))
        setup_lines.extend(_generate_variable_set_setup(info))

    elif info.is_sensitive:
        # Sensitive variable - recommend Secret
        code_lines.extend(_generate_sensitive_options(info, safe_name))
        setup_lines.extend(_generate_sensitive_setup(info))

    else:
        # Non-sensitive variable - show all options
        code_lines.extend(_generate_nonsensitive_options(info, safe_name))
        setup_lines.extend(_generate_nonsensitive_setup(info))

    return "\n".join(code_lines), "\n".join(setup_lines), warnings


def _to_python_identifier(name: str) -> str:
    """Convert a variable name to a valid Python identifier."""
    # Replace non-alphanumeric characters with underscores
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Ensure it doesn't start with a digit
    if safe and safe[0].isdigit():
        safe = "_" + safe
    return safe or "variable"


def _generate_variable_set_code(info: VariableInfo, safe_name: str) -> list[str]:
    """Generate code for Variable.set() conversion."""
    return [
        f"# Converted from Variable.set('{info.name}', ...)",
        "# Variable.set requires Prefect Variables API for dynamic updates",
        "",
        "from prefect.variables import Variable",
        "",
        f"async def set_{safe_name}(value: str) -> None:",
        f'    """Set the {info.name} variable dynamically."""',
        f'    await Variable.set(name="{info.name}", value=value, overwrite=True)',
        "",
        "# Synchronous alternative:",
        "# from prefect.variables import Variable",
        f'# Variable.set(name="{info.name}", value=value, overwrite=True)',
    ]


def _generate_variable_set_setup(info: VariableInfo) -> list[str]:
    """Generate setup instructions for Variable.set() conversion."""
    return [
        f"# Setup for writable variable: {info.name}",
        "#",
        "# Prefect Variables can be created/updated via:",
        "#",
        "# 1. Prefect UI: Settings > Variables > Add Variable",
        "#",
        "# 2. CLI:",
        f'#    prefect variable set {info.name} "initial_value"',
        "#",
        "# 3. Python (in flow/task or setup script):",
        "#    from prefect.variables import Variable",
        f'#    Variable.set(name="{info.name}", value="initial_value")',
        "#",
        "# Note: Variables are stored unencrypted. Use Secrets for sensitive data.",
    ]


def _generate_sensitive_options(info: VariableInfo, safe_name: str) -> list[str]:
    """Generate code options for sensitive variables."""
    default_part = ""
    if info.default_value:
        default_part = f"  # Airflow default was: {info.default_value}"

    return [
        f"# Converted from Variable.get('{info.name}')",
        f"# SENSITIVE: Name contains sensitive pattern - using Prefect Secret{default_part}",
        "",
        "# ==========================================================",
        "# RECOMMENDED: Prefect Secret Block (encrypted, access-controlled)",
        "# ==========================================================",
        "from prefect.blocks.system import Secret",
        "",
        f"def get_{safe_name}() -> str:",
        f'    """Retrieve {info.name} from Prefect Secret block."""',
        f'    secret_block = Secret.load("{info.name}")',
        "    return secret_block.get()",
        "",
        "# Usage in flow/task:",
        f"# {safe_name} = get_{safe_name}()",
    ]


def _generate_sensitive_setup(info: VariableInfo) -> list[str]:
    """Generate setup instructions for sensitive variables."""
    return [
        f"# Setup for sensitive variable: {info.name}",
        "#",
        "# Create the Secret block via:",
        "#",
        "# 1. Prefect UI: Blocks > Add Block > Secret",
        f"#    - Block Name: {info.name}",
        "#    - Value: <your secret value>",
        "#",
        "# 2. CLI:",
        "#    prefect block register -m prefect.blocks.system",
        "#    # Then create via UI or Python",
        "#",
        "# 3. Python:",
        "#    from prefect.blocks.system import Secret",
        '#    secret = Secret(value="your-secret-value")',
        f'#    secret.save("{info.name}")',
        "#",
        "# Secrets are encrypted at rest and access-controlled.",
    ]


def _generate_nonsensitive_options(info: VariableInfo, safe_name: str) -> list[str]:
    """Generate code options for non-sensitive variables."""
    default_comment = ""
    default_param = '""'
    if info.default_value:
        default_comment = f"  # Original default: {info.default_value}"
        default_param = info.default_value

    return [
        f"# Converted from Variable.get('{info.name}')",
        f"# Non-sensitive variable - multiple options available{default_comment}",
        "",
        "# ==========================================================",
        "# OPTION 1: Flow Parameter (best for config with defaults)",
        "# ==========================================================",
        "from prefect import flow",
        "",
        "@flow",
        f"def my_flow({safe_name}: str = {default_param}):",
        f'    """Flow with {info.name} as parameter."""',
        f"    # Use {safe_name} directly",
        "    pass",
        "",
        "# ==========================================================",
        "# OPTION 2: Prefect Variable (best for dynamic values)",
        "# ==========================================================",
        "from prefect.variables import Variable",
        "",
        f"def get_{safe_name}() -> str:",
        f'    """Retrieve {info.name} from Prefect Variables."""',
        f'    value = Variable.get("{info.name}"'
        + (f", default={default_param}" if info.default_value else "")
        + ")",
        "    return value",
        "",
        "# ==========================================================",
        "# OPTION 3: Environment Variable (best for deployment config)",
        "# ==========================================================",
        "import os",
        "",
        f"def get_{safe_name}_from_env() -> str:",
        f'    """Retrieve {info.name} from environment."""',
        f'    return os.environ.get("{info.name.upper()}"'
        + (f", {default_param}" if info.default_value else "")
        + ")",
    ]


def _generate_nonsensitive_setup(info: VariableInfo) -> list[str]:
    """Generate setup instructions for non-sensitive variables."""
    default_note = ""
    if info.default_value:
        default_note = f" (default: {info.default_value})"

    return [
        f"# Setup for variable: {info.name}{default_note}",
        "#",
        "# Choose based on your use case:",
        "#",
        "# OPTION 1 - Flow Parameter:",
        "#   No setup needed - pass value when running flow:",
        f"#   my_flow({_to_python_identifier(info.name)}='value')",
        "#   Or via deployment parameters in prefect.yaml",
        "#",
        "# OPTION 2 - Prefect Variable:",
        "#   CLI: prefect variable set " + info.name + ' "value"',
        "#   UI: Settings > Variables > Add Variable",
        "#",
        "# OPTION 3 - Environment Variable:",
        f"#   export {info.name.upper()}='value'",
        "#   Or set in deployment/docker configuration",
    ]


def convert_all_variables(
    dag_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert all Variable usage in a DAG file.

    Args:
        dag_code: Source code of the DAG file
        include_comments: Include educational comments (unused, for API consistency)

    Returns:
        Dictionary with:
        - variables: List of VariableInfo objects
        - scaffolds: Dict mapping variable name to (code, setup, warnings)
        - summary: Human-readable summary
        - all_warnings: Aggregated warnings
        - has_sensitive: Whether any sensitive variables were detected
        - has_writes: Whether any Variable.set() calls were detected
    """
    variables = extract_variables(dag_code)

    if not variables:
        return {
            "variables": [],
            "scaffolds": {},
            "summary": "No Airflow Variables detected",
            "all_warnings": [],
            "has_sensitive": False,
            "has_writes": False,
        }

    scaffolds: dict[str, tuple[str, str, list[str]]] = {}
    all_warnings: list[str] = []
    has_sensitive = False
    has_writes = False

    # Track unique variable names (may have multiple usages)
    seen_names: set[str] = set()

    for var in variables:
        if var.is_sensitive:
            has_sensitive = True
        if var.is_set:
            has_writes = True

        # Generate scaffold only once per unique variable name
        if var.name not in seen_names:
            seen_names.add(var.name)
            code, setup, warnings = generate_variable_scaffold(var)
            scaffolds[var.name] = (code, setup, warnings)
            all_warnings.extend(warnings)

    # Build summary
    sensitive_count = sum(1 for v in variables if v.is_sensitive)
    write_count = sum(1 for v in variables if v.is_set)
    read_count = len(variables) - write_count

    summary_parts = [f"Found {len(seen_names)} unique Airflow Variable(s)"]
    if read_count:
        summary_parts.append(f"{read_count} read(s)")
    if write_count:
        summary_parts.append(f"{write_count} write(s)")
    if sensitive_count:
        summary_parts.append(f"{sensitive_count} sensitive")

    return {
        "variables": variables,
        "scaffolds": scaffolds,
        "summary": ": ".join(summary_parts[:1]) + " - " + ", ".join(summary_parts[1:])
        if len(summary_parts) > 1
        else summary_parts[0],
        "all_warnings": all_warnings,
        "has_sensitive": has_sensitive,
        "has_writes": has_writes,
    }
