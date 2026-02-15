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
  const result = await apiCall<{
    dag_id: string;
    operators: Array<{ type: string; task_id: string; line?: number }>;
    dependencies: string[][];
    complexity_score: number;
    notes: string[];
    xcom_usage: string[];
  }>("/api/analyze", { path });

  // Map API response to DagAnalysis type
  return {
    dagId: result.dag_id,
    filePath: path,
    operators: result.operators.map((op) => ({
      name: op.task_id,
      type: op.type,
      taskId: op.task_id,
      supported: true,
    })),
    dependencies: {
      taskCount: result.operators.length,
      edgeCount: result.dependencies.length,
      graphType: result.dependencies.length > 5 ? "complex" : "linear",
      edges: result.dependencies as [string, string][],
    },
    features: {
      taskflow: result.notes.some((n) => n.toLowerCase().includes("taskflow")),
      datasets: result.notes.some((n) => n.toLowerCase().includes("dataset")),
      sensors: result.notes.some((n) => n.toLowerCase().includes("sensor")),
      customOperators: result.notes.some((n) => n.toLowerCase().includes("custom")),
      dynamicTasks: result.notes.some((n) => n.toLowerCase().includes("dynamic")),
      taskGroups: result.notes.some((n) => n.toLowerCase().includes("taskgroup")),
      triggerRules: result.notes.some((n) => n.toLowerCase().includes("trigger")),
      jinjaTemplates: result.notes.some((n) => n.toLowerCase().includes("jinja")),
    },
    complexityScore: result.complexity_score,
    warnings: result.notes.map((note) => ({
      severity: "warning" as const,
      message: note,
    })),
  };
}

export async function analyzeDagContent(content: string): Promise<DagAnalysis> {
  const result = await apiCall<{
    dag_id: string;
    operators: Array<{ type: string; task_id: string; line?: number }>;
    dependencies: string[][];
    complexity_score: number;
    notes: string[];
    xcom_usage: string[];
  }>("/api/analyze", { content });

  return {
    dagId: result.dag_id,
    filePath: "",
    operators: result.operators.map((op) => ({
      name: op.task_id,
      type: op.type,
      taskId: op.task_id,
      supported: true,
    })),
    dependencies: {
      taskCount: result.operators.length,
      edgeCount: result.dependencies.length,
      graphType: result.dependencies.length > 5 ? "complex" : "linear",
      edges: result.dependencies as [string, string][],
    },
    features: {
      taskflow: false,
      datasets: false,
      sensors: false,
      customOperators: false,
      dynamicTasks: false,
      taskGroups: false,
      triggerRules: false,
      jinjaTemplates: false,
    },
    complexityScore: result.complexity_score,
    warnings: result.notes.map((note) => ({
      severity: "warning" as const,
      message: note,
    })),
  };
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

  // Extract dagId from path or flow code
  const dagIdMatch = result.flow_code.match(/name="([^"]+)"/);
  const dagId = dagIdMatch ? dagIdMatch[1] : path.split("/").pop()?.replace(".py", "") || "unknown";

  return {
    dagId,
    success: true,
    flowCode: result.flow_code,
    testCode: result.test_code,
    runbook: result.conversion_runbook_md,
    warnings: result.warnings,
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

  const dagIdMatch = result.flow_code.match(/name="([^"]+)"/);
  const dagId = dagIdMatch ? dagIdMatch[1] : "unknown";

  return {
    dagId,
    success: true,
    flowCode: result.flow_code,
    testCode: result.test_code,
    runbook: result.conversion_runbook_md,
    warnings: result.warnings,
  };
}

export async function validateConversion(
  originalDag: string,
  convertedFlow: string
): Promise<ValidationResult> {
  const result = await apiCall<{
    is_valid: boolean;
    confidence_score: number;
    task_count_match?: boolean;
    dependency_preserved?: boolean;
    issues: Array<{
      severity: string;
      category: string;
      message: string;
    }>;
    suggestions?: string[];
    dag_tasks?: string[];
    flow_tasks?: string[];
  }>("/api/validate", {
    original_dag: originalDag,
    converted_flow: convertedFlow,
  });

  return {
    dagId: "validation",
    isValid: result.is_valid,
    confidenceScore: result.confidence_score,
    taskCountMatch: result.task_count_match ?? true,
    dependencyPreserved: result.dependency_preserved ?? true,
    issues: result.issues.map((issue) => ({
      type: (issue.category === "task_count" ? "task_count" :
             issue.category === "dependency" ? "dependency" :
             issue.category === "xcom" ? "xcom" : "other") as "task_count" | "dependency" | "xcom" | "other",
      severity: (issue.severity === "error" ? "error" : "warning") as "error" | "warning",
      message: issue.message,
    })),
    dagTasks: result.dag_tasks ?? [],
    flowTasks: result.flow_tasks ?? [],
    dagEdges: [],
    flowEdges: [],
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

  const basePath = config.projectName;

  // Generate a preview tree structure
  const tree: ProjectTreeNode = {
    name: config.projectName,
    type: "directory",
    path: basePath,
    children: [
      {
        name: "flows",
        type: "directory",
        path: `${basePath}/flows`,
        children: flows.map((f) => ({
          name: `${f.name}.py`,
          type: "file" as const,
          path: `${basePath}/flows/${f.name}.py`,
          content: f.flowCode,
        })),
      },
      {
        name: "tests",
        type: "directory",
        path: `${basePath}/tests`,
        children: flows
          .filter((f) => f.testCode)
          .map((f) => ({
            name: `test_${f.name}.py`,
            type: "file" as const,
            path: `${basePath}/tests/test_${f.name}.py`,
            content: f.testCode,
          })),
      },
      {
        name: "prefect.yaml",
        type: "file",
        path: `${basePath}/prefect.yaml`,
        content: generatePrefectYaml(config, deploymentConfig),
      },
      {
        name: "pyproject.toml",
        type: "file",
        path: `${basePath}/pyproject.toml`,
        content: generatePyprojectToml(config),
      },
      {
        name: "README.md",
        type: "file",
        path: `${basePath}/README.md`,
        content: generateReadme(config, flows.length),
      },
    ],
  };

  if (config.includeDockerfile) {
    tree.children?.push({
      name: "Dockerfile",
      type: "file",
      path: `${basePath}/Dockerfile`,
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
  const workPoolName = deployment.workPool?.name || "default";
  const schedules = deployment.deployments
    .filter((d) => d.schedule?.cron)
    .map((d) => `      - cron: "${d.schedule!.cron}"`)
    .join("\n");

  return `# Prefect deployment configuration
name: ${config.projectName}

deployments:
  - name: default
    entrypoint: flows/main.py:main_flow
    work_pool:
      name: ${workPoolName}
    schedules: ${schedules ? `\n${schedules}` : "[]"}
`;
}

function generatePyprojectToml(config: ProjectConfig): string {
  return `[project]
name = "${config.projectName}"
version = "0.1.0"
description = "${config.description || "Prefect flows migrated from Airflow"}"
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

${config.description || "Prefect flows migrated from Apache Airflow."}

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
