"""Tests for HTTP server."""

import pytest

# Skip tests if aiohttp not installed
pytest.importorskip("aiohttp")

from aiohttp.test_utils import AioHTTPTestCase

from airflow_unfactor.http_server import create_app


class TestHealthEndpoint(AioHTTPTestCase):
    """Test health check endpoint."""

    async def get_application(self):
        return create_app(ui_path=None)

    async def test_health_returns_ok(self):
        """Health endpoint returns status ok."""
        response = await self.client.get("/health")
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data


class TestAnalyzeEndpoint(AioHTTPTestCase):
    """Test analyze API endpoint."""

    async def get_application(self):
        return create_app(ui_path=None)

    async def test_analyze_with_content(self):
        """Analyze endpoint works with content."""
        dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def my_callable():
    return 42

with DAG(
    dag_id="test_dag",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
) as dag:
    task = PythonOperator(task_id="test_task", python_callable=my_callable)
"""
        response = await self.client.post(
            "/api/analyze",
            json={"content": dag_code},
        )
        assert response.status == 200
        data = await response.json()
        # Should have dag_id or operators in a successful response
        assert "dag_id" in data or "operators" in data or "error" not in data

    async def test_analyze_missing_input(self):
        """Analyze endpoint requires path or content."""
        response = await self.client.post("/api/analyze", json={})
        assert response.status == 400
        data = await response.json()
        assert "error" in data

    async def test_analyze_invalid_json(self):
        """Analyze endpoint handles invalid JSON."""
        response = await self.client.post(
            "/api/analyze",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status == 400


class TestConvertEndpoint(AioHTTPTestCase):
    """Test convert API endpoint."""

    async def get_application(self):
        return create_app(ui_path=None)

    async def test_convert_with_content(self):
        """Convert endpoint works with content."""
        dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator

def my_func():
    return 42

with DAG("test_dag") as dag:
    task = PythonOperator(task_id="test", python_callable=my_func)
"""
        response = await self.client.post(
            "/api/convert",
            json={
                "content": dag_code,
                "include_comments": True,
                "generate_tests": True,
            },
        )
        assert response.status == 200
        data = await response.json()
        assert "flow_code" in data

    async def test_convert_missing_input(self):
        """Convert endpoint requires path or content."""
        response = await self.client.post("/api/convert", json={})
        assert response.status == 400


class TestValidateEndpoint(AioHTTPTestCase):
    """Test validate API endpoint."""

    async def get_application(self):
        return create_app(ui_path=None)

    async def test_validate_missing_input(self):
        """Validate endpoint requires both inputs."""
        response = await self.client.post(
            "/api/validate",
            json={"original_dag": "test"},
        )
        assert response.status == 400

    async def test_validate_with_content(self):
        """Validate endpoint works with content."""
        dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("test_dag") as dag:
    task = PythonOperator(task_id="test", python_callable=lambda: None)
"""
        flow_code = """
from prefect import flow, task

@task
def test():
    return None

@flow
def test_dag():
    test()
"""
        response = await self.client.post(
            "/api/validate",
            json={
                "original_dag": dag_code,
                "converted_flow": flow_code,
            },
        )
        assert response.status == 200
        data = await response.json()
        assert "is_valid" in data or "confidence_score" in data


class TestCORS(AioHTTPTestCase):
    """Test CORS middleware."""

    async def get_application(self):
        return create_app(ui_path=None)

    async def test_cors_headers_present(self):
        """CORS headers are added to responses."""
        response = await self.client.get("/health")
        assert "Access-Control-Allow-Origin" in response.headers

    async def test_options_request(self):
        """OPTIONS request returns CORS headers."""
        response = await self.client.options("/api/analyze")
        assert response.status == 200
        assert "Access-Control-Allow-Methods" in response.headers
