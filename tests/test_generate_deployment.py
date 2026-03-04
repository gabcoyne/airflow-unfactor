# tests/test_generate_deployment.py
"""Tests for generate_deployment tool."""

import asyncio
import json

from airflow_unfactor.tools.generate_deployment import (
    _build_prefect_yaml,
    _flow_to_deployment_yaml,
    generate_deployment,
)


class TestFlowToDeploymentYaml:
    """Unit tests for the per-flow YAML block builder."""

    def test_minimal_flow(self):
        """flow_name and entrypoint only — no schedule, params, tags."""
        yaml = _flow_to_deployment_yaml(
            flow_name="my_flow",
            entrypoint="deployments/default/my-flow/flow.py:my_flow",
        )
        assert "name: my-flow" in yaml
        assert "entrypoint: deployments/default/my-flow/flow.py:my_flow" in yaml
        assert "schedules" not in yaml
        assert "parameters" not in yaml

    def test_cron_schedule(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            schedule="0 6 * * *",
        )
        assert 'cron: "0 6 * * *"' in yaml

    def test_interval_schedule(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            schedule="3600",
        )
        assert "interval: 3600" in yaml

    def test_parameters(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            parameters={"date": "2024-01-01", "env": "prod"},
        )
        assert "parameters:" in yaml
        assert "date:" in yaml
        assert "env:" in yaml

    def test_tags(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            tags=["etl", "daily"],
        )
        assert 'tags: ["etl", "daily"]' in yaml

    def test_tags_with_spaces_are_quoted(self):
        """Tags containing spaces or colons must be quoted to produce valid YAML."""
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            tags=["my tag", "env:prod"],
        )
        assert '"my tag"' in yaml
        assert '"env:prod"' in yaml

    def test_description(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            description="Converted from etl_dag",
        )
        assert "description: Converted from etl_dag" in yaml

    def test_dataset_triggers_emit_comment(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            dataset_triggers=["s3://bucket/path"],
        )
        assert "Automation" in yaml or "automation" in yaml
        assert "s3://bucket/path" in yaml


class TestBuildPrefectYaml:
    """Tests for full prefect.yaml document construction."""

    def test_single_flow_produces_valid_yaml(self):
        content = _build_prefect_yaml(
            project_name="my-project",
            flows=[
                {
                    "flow_name": "etl",
                    "entrypoint": "deployments/default/etl/flow.py:etl",
                }
            ],
        )
        assert "name: my-project" in content
        assert "prefect-version:" in content
        assert "definitions:" in content
        assert "work_pools:" in content
        assert "deployments:" in content
        assert "TODO" in content  # work pool stub

    def test_multiple_flows(self):
        content = _build_prefect_yaml(
            project_name="proj",
            flows=[
                {"flow_name": "flow_a", "entrypoint": "deployments/default/flow-a/flow.py:flow_a"},
                {"flow_name": "flow_b", "entrypoint": "deployments/default/flow-b/flow.py:flow_b"},
            ],
        )
        assert "name: flow-a" in content
        assert "name: flow-b" in content

    def test_yaml_anchors_present(self):
        content = _build_prefect_yaml(
            project_name="proj",
            flows=[{"flow_name": "f", "entrypoint": "deployments/default/f/flow.py:f"}],
        )
        assert "&default_pool" in content
        assert "*default_pool" in content

    def test_pull_step_commented_out(self):
        content = _build_prefect_yaml(
            project_name="proj",
            flows=[{"flow_name": "f", "entrypoint": "deployments/default/f/flow.py:f"}],
        )
        assert "# pull:" in content or "pull:" not in content

    def test_empty_flows_emits_empty_list(self):
        """Empty flows list must produce 'deployments: []' not 'deployments: null'."""
        content = _build_prefect_yaml(project_name="proj", flows=[])
        assert "deployments: []" in content
        assert "deployments: null" not in content
        # prefect.yaml header should still be present
        assert "name: proj" in content


class TestGenerateDeploymentTool:
    """Integration tests for the full tool."""

    def test_writes_prefect_yaml(self, tmp_path):
        result_json = asyncio.run(
            generate_deployment(
                output_directory=str(tmp_path),
                flows=[
                    {
                        "flow_name": "etl",
                        "entrypoint": "deployments/default/etl/flow.py:etl",
                        "schedule": "0 6 * * *",
                    }
                ],
            )
        )
        result = json.loads(result_json)
        assert (tmp_path / "prefect.yaml").exists()
        assert result["created_file"].endswith("prefect.yaml")
        assert "etl" in result["deployment_names"]
        assert len(result["next_steps"]) > 0

    def test_next_steps_mention_work_pool(self, tmp_path):
        result_json = asyncio.run(
            generate_deployment(
                output_directory=str(tmp_path),
                flows=[{"flow_name": "f", "entrypoint": "deployments/default/f/flow.py:f"}],
            )
        )
        result = json.loads(result_json)
        combined = " ".join(result["next_steps"])
        assert "work pool" in combined.lower()

    def test_dataset_triggers_mentioned_in_next_steps(self, tmp_path):
        result_json = asyncio.run(
            generate_deployment(
                output_directory=str(tmp_path),
                flows=[
                    {
                        "flow_name": "f",
                        "entrypoint": "deployments/default/f/flow.py:f",
                        "dataset_triggers": ["s3://bucket/key"],
                    }
                ],
            )
        )
        result = json.loads(result_json)
        combined = " ".join(result["next_steps"])
        assert "automation" in combined.lower() or "Automation" in combined

    def test_flow_name_slugified(self, tmp_path):
        """flow_name with underscores → slug with hyphens in deployment name."""
        asyncio.run(
            generate_deployment(
                output_directory=str(tmp_path),
                flows=[{"flow_name": "my_etl_flow", "entrypoint": "f.py:my_etl_flow"}],
            )
        )
        content = (tmp_path / "prefect.yaml").read_text()
        assert "name: my-etl-flow" in content
