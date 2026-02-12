import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / 'fixtures'

@pytest.fixture
def simple_etl_dag():
    return (FIXTURES_DIR / 'simple_etl.py').read_text()

@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR