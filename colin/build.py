#!/usr/bin/env python3
"""Build Colin output from model templates.

Interim build script that parses model .md files into JSON output
until colin-py CLI is stable. Reads the markdown section structure
and produces JSON files matching what `colin run` would generate.

Usage:
    python colin/build.py
    # or from colin/: python build.py
"""

import json
import re
from pathlib import Path


def parse_sections(content: str) -> dict[str, dict[str, str]]:
    """Parse {% section name %} ... {% endsection %} blocks from a template."""
    sections: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        r'\{%\s*section\s+["\']?(\w[\w-]*)["\']?\s*%\}(.*?)\{%\s*endsection\s*%\}',
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        name = match.group(1)
        body = match.group(2).strip()
        sections[name] = parse_section_body(body)
    return sections


def parse_section_body(body: str) -> dict[str, str]:
    """Parse a section body into key-value pairs based on ## headers."""
    result: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in body.split("\n"):
        # Check for ## header (top-level key)
        h2_match = re.match(r"^## (.+)$", line)
        if h2_match:
            if current_key is not None:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = h2_match.group(1).strip()
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        result[current_key] = "\n".join(current_lines).strip()

    # Post-process: parse nested ### headers into sub-dicts
    processed: dict = {}
    for key, value in result.items():
        if "\n### " in f"\n{value}":
            processed[key] = parse_subsections(value)
        elif value.startswith("- "):
            # Parse bullet lists into arrays
            processed[key] = [line.lstrip("- ").strip() for line in value.split("\n") if line.startswith("- ")]
        else:
            processed[key] = value
    return processed


def parse_subsections(text: str) -> dict[str, str]:
    """Parse ### sub-headers into a dict."""
    result: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        h3_match = re.match(r"^### (.+)$", line)
        if h3_match:
            if current_key is not None:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = h3_match.group(1).strip()
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        result[current_key] = "\n".join(current_lines).strip()

    return result


def build_model(model_path: Path) -> dict:
    """Build a single model file into a JSON dict."""
    content = model_path.read_text()

    # Strip frontmatter
    if content.startswith("---"):
        _, _, content = content.split("---", 2)

    # Skip files that only contain ref() calls (like _index.md)
    if "ref(" in content and "{% section" not in content:
        return {}

    sections = parse_sections(content)
    return sections


def main():
    # Find project root (colin/ directory)
    script_dir = Path(__file__).parent
    models_dir = script_dir / "models"
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)

    if not models_dir.exists():
        print(f"Error: {models_dir} not found")
        return

    # Process each .md file (excluding _index.md aggregators)
    for md_file in sorted(models_dir.rglob("*.md")):
        if md_file.name.startswith("_"):
            continue

        rel_path = md_file.relative_to(models_dir)
        output_name = str(rel_path).replace("/", "-").replace(".md", ".json")

        data = build_model(md_file)
        if not data:
            continue

        output_file = output_dir / output_name
        output_file.write_text(json.dumps(data, indent=2))
        section_count = len(data)
        print(f"  {rel_path} → {output_name} ({section_count} entries)")

    print(f"\nOutput written to {output_dir}/")


if __name__ == "__main__":
    main()
