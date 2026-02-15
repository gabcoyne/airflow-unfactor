/**
 * HTTP API client for standalone wizard mode.
 *
 * When the wizard runs standalone (served by Python's --ui mode),
 * it calls the Python HTTP API directly instead of using MCP postMessage.
 */

import type {
  DagAnalysis,
  ConversionOptions,
  ConversionResult,
  ValidationResult,
  ProjectConfig,
  DeploymentConfig,
  ProjectTreeNode,
} from "@/types";

// API base URL - empty for same-origin requests
const API_BASE = "";

// Error handling
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiCall<T>(
  endpoint: string,
  data: Record<string, unknown>
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new ApiError(
      result.error || "API request failed",
      response.status,
      result.details
    );
  }

  return result as T;
}

// API client functions

export async function analyzeDag(path: string): Promise<DagAnalysis> {
  return apiCall<DagAnalysis>("/api/analyze", { path });
}

export async function analyzeDagContent(content: string): Promise<DagAnalysis> {
  return apiCall<DagAnalysis>("/api/analyze", { content });
}

export async function analyzeDags(paths: string[]): Promise<DagAnalysis[]> {
  const results = await Promise.all(paths.map((path) => analyzeDag(path)));
  return results;
}

export async function convertDag(
  path: string,
  options: ConversionOptions
): Promise<ConversionResult> {
  const result = await apiCall<{
    flow_code: string;
    test_code: string;
    warnings: string[];
    original_to_new_mapping: Record<string, string>;
    conversion_runbook_md?: string;
    dataset_conversion?: unknown;
  }>("/api/convert", {
    path,
    include_comments: options.includeComments,
    generate_tests: options.generateTests,
  });

  // Map API response to ConversionResult type
  return {
    flowCode: result.flow_code,
    testCode: result.test_code,
    warnings: result.warnings,
    taskMapping: result.original_to_new_mapping,
    runbook: result.conversion_runbook_md,
  };
}

export async function convertDagContent(
  content: string,
  options: ConversionOptions
): Promise<ConversionResult> {
  const result = await apiCall<{
    flow_code: string;
    test_code: string;
    warnings: string[];
    original_to_new_mapping: Record<string, string>;
    conversion_runbook_md?: string;
  }>("/api/convert", {
    content,
    include_comments: options.includeComments,
    generate_tests: options.generateTests,
  });

  return {
    flowCode: result.flow_code,
    testCode: result.test_code,
    warnings: result.warnings,
    taskMapping: result.original_to_new_mapping,
    runbook: result.conversion_runbook_md,
  };
}

export async function validateConversion(
  originalDag: string,
  convertedFlow: string
): Promise<ValidationResult> {
  const result = await apiCall<{
    is_valid: boolean;
    confidence_score: number;
    issues: Array<{
      severity: string;
      category: string;
      message: string;
    }>;
    suggestions: string[];
  }>("/api/validate", {
    original_dag: originalDag,
    converted_flow: convertedFlow,
  });

  return {
    isValid: result.is_valid,
    confidenceScore: result.confidence_score,
    issues: result.issues.map((issue) => ({
      severity: issue.severity as "error" | "warning" | "info",
      category: issue.category,
      message: issue.message,
    })),
    suggestions: result.suggestions,
  };
}

export async function scaffoldProject(
  config: ProjectConfig,
  deploymentConfig: DeploymentConfig,
  conversions: Map<string, ConversionResult>
): Promise<ProjectTreeNode> {
  // For standalone mode, we generate the project tree client-side
  // The scaffold API creates files on disk, but we want a preview first

  const flows = Array.from(conversions.entries()).map(([dagId, conv]) => ({
    name: dagId,
    flowCode: conv.flowCode,
    testCode: conv.testCode,
  }));

  // Generate a preview tree structure
  const tree: ProjectTreeNode = {
    name: config.projectName,
    type: "directory",
    children: [
      {
        name: "flows",
        type: "directory",
        children: flows.map((f) => ({
          name: `${f.name}.py`,
          type: "file",
          content: f.flowCode,
        })),
      },
      {
        name: "tests",
        type: "directory",
        children: flows
          .filter((f) => f.testCode)
          .map((f) => ({
            name: `test_${f.name}.py`,
            type: "file",
            content: f.testCode,
          })),
      },
      {
        name: "prefect.yaml",
        type: "file",
        content: generatePrefectYaml(config, deploymentConfig),
      },
      {
        name: "pyproject.toml",
        type: "file",
        content: generatePyprojectToml(config),
      },
      {
        name: "README.md",
        type: "file",
        content: generateReadme(config, flows.length),
      },
    ],
  };

  if (config.includeDockerfile) {
    tree.children?.push({
      name: "Dockerfile",
      type: "file",
      content: generateDockerfile(),
    });
  }

  return tree;
}

// Helper functions for generating project files

function generatePrefectYaml(
  config: ProjectConfig,
  deployment: DeploymentConfig
): string {
  return `# Prefect deployment configuration
name: ${config.projectName}

deployments:
  - name: default
    entrypoint: flows/main.py:main_flow
    work_pool:
      name: ${deployment.workPoolName || "default"}
    schedules: ${deployment.schedule ? `\n      - cron: "${deployment.schedule}"` : "[]"}
`;
}

function generatePyprojectToml(config: ProjectConfig): string {
  return `[project]
name = "${config.projectName}"
version = "0.1.0"
description = "Prefect flows migrated from Airflow"
requires-python = ">=3.11"
dependencies = [
    "prefect>=3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
]
`;
}

function generateReadme(config: ProjectConfig, flowCount: number): string {
  return `# ${config.projectName}

Prefect flows migrated from Apache Airflow.

## Flows

This project contains ${flowCount} migrated flow(s).

## Setup

\`\`\`bash
pip install -e .
\`\`\`

## Running Flows

\`\`\`bash
python flows/main.py
\`\`\`

## Deployment

\`\`\`bash
prefect deploy --all
\`\`\`

---
Generated by [airflow-unfactor](https://github.com/prefecthq/airflow-unfactor)
`;
}

function generateDockerfile(): string {
  return `FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY flows/ flows/

CMD ["python", "-m", "prefect", "worker", "start"]
`;
}

// Check API health
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    const data = await response.json();
    return data.status === "ok";
  } catch {
    return false;
  }
}

// Determine if we're in standalone mode (HTTP API) or MCP App mode
export function isStandaloneMode(): boolean {
  try {
    // In MCP App context, window.parent !== window
    return window.parent === window;
  } catch {
    return true;
  }
}
