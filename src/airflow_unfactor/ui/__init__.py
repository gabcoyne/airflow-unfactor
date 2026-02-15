"""Wizard UI resources.

The UI is built from mcp-app/ and embedded here during release builds.
For development, the HTTP server can serve from mcp-app/dist/ directly.
"""

from pathlib import Path


def get_ui_path() -> Path | None:
    """Get path to UI directory.

    Returns:
        Path to UI directory if available, None otherwise.
    """
    ui_dir = Path(__file__).parent
    if (ui_dir / "index.html").exists():
        return ui_dir
    return None


def get_ui_html() -> str | None:
    """Get UI HTML content.

    Returns:
        HTML content if available, None otherwise.
    """
    ui_path = get_ui_path()
    if ui_path:
        return (ui_path / "index.html").read_text()
    return None
