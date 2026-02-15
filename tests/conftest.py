from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ASTRONOMER_TOYS = FIXTURES_DIR / "astronomer-2-9" / "dags" / "toys"
SNAPSHOTS_DIR = FIXTURES_DIR / "snapshots"


@pytest.fixture
def simple_etl_dag():
    return (FIXTURES_DIR / "simple_etl.py").read_text()


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def astronomer_toys_dir():
    return ASTRONOMER_TOYS


@pytest.fixture
def snapshots_dir():
    return SNAPSHOTS_DIR


def pytest_addoption(parser):
    """Add --snapshot-update option."""
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="Update snapshot golden files",
    )


@pytest.fixture
def snapshot_update(request):
    """Check if snapshot update mode is enabled."""
    return request.config.getoption("--snapshot-update", default=False)
