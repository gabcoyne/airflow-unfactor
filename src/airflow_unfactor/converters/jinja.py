"""Jinja2 template converter for Airflow to Prefect.

Converts Airflow Jinja2 template patterns to Prefect runtime context expressions.

Airflow provides template variables like {{ ds }}, {{ ds_nodash }}, {{ ts }}, and
macros like {{ macros.ds_add(ds, 7) }}. Prefect uses runtime context to access
similar information through `prefect.runtime.flow_run`.

This module detects Jinja2 patterns in strings and converts them to Python f-strings
that use Prefect's runtime context.
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class JinjaPatternType(Enum):
    """Types of Jinja2 patterns supported."""

    DS = "ds"  # {{ ds }} - execution date as YYYY-MM-DD
    DS_NODASH = "ds_nodash"  # {{ ds_nodash }} - execution date as YYYYMMDD
    TS = "ts"  # {{ ts }} - ISO timestamp
    PARAMS = "params"  # {{ params.x }} - DAG parameters
    MACROS_DS_ADD = "macros_ds_add"  # {{ macros.ds_add(ds, N) }} - date arithmetic
    MACROS_DS_FORMAT = "macros_ds_format"  # {{ macros.ds_format(ds, fmt) }}
    EXECUTION_DATE = "execution_date"  # {{ execution_date }} - datetime object
    PREV_DS = "prev_ds"  # {{ prev_ds }} - previous execution date
    NEXT_DS = "next_ds"  # {{ next_ds }} - next execution date
    UNKNOWN = "unknown"  # Unrecognized pattern


@dataclass
class JinjaPattern:
    """A detected Jinja2 pattern in a string.

    Attributes:
        pattern_type: The type of Jinja2 pattern detected
        original: The original matched text (e.g., "{{ ds }}")
        start: Start position in the original string
        end: End position in the original string
        params: Additional parameters extracted from the pattern
    """

    pattern_type: JinjaPatternType
    original: str
    start: int
    end: int
    params: dict = field(default_factory=dict)

    @property
    def is_supported(self) -> bool:
        """Check if this pattern type is fully supported."""
        return self.pattern_type != JinjaPatternType.UNKNOWN


# Regex patterns for detecting Jinja2 templates
JINJA_PATTERNS = [
    # {{ ds }} - execution date
    (
        re.compile(r"\{\{\s*ds\s*\}\}"),
        JinjaPatternType.DS,
        lambda m: {},
    ),
    # {{ ds_nodash }} - execution date without dashes
    (
        re.compile(r"\{\{\s*ds_nodash\s*\}\}"),
        JinjaPatternType.DS_NODASH,
        lambda m: {},
    ),
    # {{ ts }} - ISO timestamp
    (
        re.compile(r"\{\{\s*ts\s*\}\}"),
        JinjaPatternType.TS,
        lambda m: {},
    ),
    # {{ execution_date }} - datetime object
    (
        re.compile(r"\{\{\s*execution_date\s*\}\}"),
        JinjaPatternType.EXECUTION_DATE,
        lambda m: {},
    ),
    # {{ prev_ds }} - previous execution date
    (
        re.compile(r"\{\{\s*prev_ds\s*\}\}"),
        JinjaPatternType.PREV_DS,
        lambda m: {},
    ),
    # {{ next_ds }} - next execution date
    (
        re.compile(r"\{\{\s*next_ds\s*\}\}"),
        JinjaPatternType.NEXT_DS,
        lambda m: {},
    ),
    # {{ params.x }} - DAG parameters
    (
        re.compile(r"\{\{\s*params\.(\w+)\s*\}\}"),
        JinjaPatternType.PARAMS,
        lambda m: {"param_name": m.group(1)},
    ),
    # {{ macros.ds_add(ds, N) }} - date arithmetic
    (
        re.compile(r"\{\{\s*macros\.ds_add\s*\(\s*ds\s*,\s*(-?\d+)\s*\)\s*\}\}"),
        JinjaPatternType.MACROS_DS_ADD,
        lambda m: {"days": int(m.group(1))},
    ),
    # {{ macros.ds_format(ds, 'format') }} - date formatting
    (
        re.compile(
            r"\{\{\s*macros\.ds_format\s*\(\s*ds\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}"
        ),
        JinjaPatternType.MACROS_DS_FORMAT,
        lambda m: {"format": m.group(1)},
    ),
]

# Catch-all for any Jinja2 pattern {{ ... }}
JINJA_CATCH_ALL = re.compile(r"\{\{[^}]+\}\}")


def detect_jinja_patterns(code: str) -> list[JinjaPattern]:
    """Detect Jinja2 patterns in a string.

    Scans the input string for Jinja2 template patterns and returns
    information about each detected pattern.

    Args:
        code: The string to scan for Jinja2 patterns

    Returns:
        List of JinjaPattern objects describing detected patterns,
        sorted by start position
    """
    patterns: list[JinjaPattern] = []
    found_positions: set[tuple[int, int]] = set()

    # Check for known patterns first
    for regex, pattern_type, param_extractor in JINJA_PATTERNS:
        for match in regex.finditer(code):
            pos = (match.start(), match.end())
            if pos not in found_positions:
                found_positions.add(pos)
                patterns.append(
                    JinjaPattern(
                        pattern_type=pattern_type,
                        original=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        params=param_extractor(match),
                    )
                )

    # Find any remaining Jinja2 patterns (unknown)
    for match in JINJA_CATCH_ALL.finditer(code):
        pos = (match.start(), match.end())
        if pos not in found_positions:
            found_positions.add(pos)
            patterns.append(
                JinjaPattern(
                    pattern_type=JinjaPatternType.UNKNOWN,
                    original=match.group(0),
                    start=match.start(),
                    end=match.end(),
                )
            )

    # Sort by position
    patterns.sort(key=lambda p: p.start)
    return patterns


def _pattern_to_fstring_expr(pattern: JinjaPattern) -> str | None:
    """Convert a single Jinja2 pattern to an f-string expression.

    Args:
        pattern: The JinjaPattern to convert

    Returns:
        The f-string expression (without braces), or None if unsupported
    """
    scheduled_time = "runtime.flow_run.scheduled_start_time"

    if pattern.pattern_type == JinjaPatternType.DS:
        return f"{scheduled_time}.strftime('%Y-%m-%d')"

    elif pattern.pattern_type == JinjaPatternType.DS_NODASH:
        return f"{scheduled_time}.strftime('%Y%m%d')"

    elif pattern.pattern_type == JinjaPatternType.TS:
        return f"{scheduled_time}.isoformat()"

    elif pattern.pattern_type == JinjaPatternType.EXECUTION_DATE:
        return scheduled_time

    elif pattern.pattern_type == JinjaPatternType.PARAMS:
        param_name = pattern.params.get("param_name", "unknown")
        return param_name

    elif pattern.pattern_type == JinjaPatternType.MACROS_DS_ADD:
        days = pattern.params.get("days", 0)
        if days >= 0:
            return f"({scheduled_time} + timedelta(days={days})).strftime('%Y-%m-%d')"
        else:
            return f"({scheduled_time} - timedelta(days={abs(days)})).strftime('%Y-%m-%d')"

    elif pattern.pattern_type == JinjaPatternType.MACROS_DS_FORMAT:
        fmt = pattern.params.get("format", "%Y-%m-%d")
        # Convert Python strftime format
        return f"{scheduled_time}.strftime('{fmt}')"

    elif pattern.pattern_type == JinjaPatternType.PREV_DS:
        # Approximation - in Airflow this depends on schedule
        return f"({scheduled_time} - timedelta(days=1)).strftime('%Y-%m-%d')"

    elif pattern.pattern_type == JinjaPatternType.NEXT_DS:
        # Approximation - in Airflow this depends on schedule
        return f"({scheduled_time} + timedelta(days=1)).strftime('%Y-%m-%d')"

    return None


def convert_jinja_to_fstring(
    template_str: str,
) -> tuple[str, list[str], list[str]]:
    """Convert a Jinja2 template string to a Python f-string.

    Takes a string containing Jinja2 template patterns and converts it to
    a Python f-string using Prefect runtime context.

    Args:
        template_str: The string containing Jinja2 patterns

    Returns:
        A tuple of:
        - converted: The converted f-string
        - imports_needed: List of import statements needed
        - warnings: List of warning messages for unsupported patterns
    """
    patterns = detect_jinja_patterns(template_str)

    if not patterns:
        # No Jinja2 patterns found - return as-is
        return template_str, [], []

    imports_needed: set[str] = set()
    warnings: list[str] = []

    # Build the converted string by replacing patterns
    result_parts: list[str] = []
    last_end = 0

    for pattern in patterns:
        # Add literal text before this pattern
        if pattern.start > last_end:
            result_parts.append(template_str[last_end : pattern.start])

        # Convert the pattern
        expr = _pattern_to_fstring_expr(pattern)
        if expr is not None:
            result_parts.append("{" + expr + "}")

            # Track needed imports
            if pattern.pattern_type in (
                JinjaPatternType.DS,
                JinjaPatternType.DS_NODASH,
                JinjaPatternType.TS,
                JinjaPatternType.EXECUTION_DATE,
                JinjaPatternType.MACROS_DS_FORMAT,
            ):
                imports_needed.add("from prefect import runtime")

            if pattern.pattern_type in (
                JinjaPatternType.MACROS_DS_ADD,
                JinjaPatternType.PREV_DS,
                JinjaPatternType.NEXT_DS,
            ):
                imports_needed.add("from prefect import runtime")
                imports_needed.add("from datetime import timedelta")
        else:
            # Unknown pattern - keep original and warn
            result_parts.append(pattern.original)
            warnings.append(
                f"Unrecognized Jinja2 pattern: {pattern.original!r} - manual conversion required"
            )

        last_end = pattern.end

    # Add any remaining literal text
    if last_end < len(template_str):
        result_parts.append(template_str[last_end:])

    converted = "".join(result_parts)

    # If we made any conversions, prefix with 'f'
    has_fstring_exprs = any(
        p.pattern_type != JinjaPatternType.UNKNOWN for p in patterns
    )
    if has_fstring_exprs:
        converted = f'f"{converted}"'
    else:
        converted = f'"{converted}"'

    return converted, sorted(imports_needed), warnings


def has_jinja_patterns(code: str) -> bool:
    """Check if a string contains any Jinja2 patterns.

    Args:
        code: The string to check

    Returns:
        True if Jinja2 patterns are detected
    """
    return bool(JINJA_CATCH_ALL.search(code))


def analyze_jinja_in_code(code: str) -> dict:
    """Analyze all Jinja2 usage in a code snippet.

    Provides a summary of Jinja2 patterns found and conversion recommendations.

    Args:
        code: The source code to analyze

    Returns:
        Dictionary with:
        - patterns: List of detected patterns
        - supported_count: Number of fully supported patterns
        - unsupported_count: Number of patterns needing manual review
        - imports_needed: Set of imports that would be needed
        - conversion_notes: List of notes about the conversion
    """
    patterns = detect_jinja_patterns(code)

    supported = [p for p in patterns if p.is_supported]
    unsupported = [p for p in patterns if not p.is_supported]

    # Collect imports
    all_imports: set[str] = set()
    for pattern in supported:
        _, imports, _ = convert_jinja_to_fstring(pattern.original)
        all_imports.update(imports)

    # Generate notes
    notes: list[str] = []

    if any(p.pattern_type == JinjaPatternType.PARAMS for p in patterns):
        notes.append(
            "params.x references will be converted to flow parameters - "
            "ensure these are defined in the @flow decorator"
        )

    if any(
        p.pattern_type in (JinjaPatternType.PREV_DS, JinjaPatternType.NEXT_DS)
        for p in patterns
    ):
        notes.append(
            "prev_ds/next_ds conversions assume daily schedule - "
            "adjust timedelta for other schedules"
        )

    if unsupported:
        notes.append(
            f"{len(unsupported)} pattern(s) require manual conversion: "
            + ", ".join(p.original for p in unsupported[:3])
            + ("..." if len(unsupported) > 3 else "")
        )

    return {
        "patterns": patterns,
        "supported_count": len(supported),
        "unsupported_count": len(unsupported),
        "imports_needed": all_imports,
        "conversion_notes": notes,
    }
