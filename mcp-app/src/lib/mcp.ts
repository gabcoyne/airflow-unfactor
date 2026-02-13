import type {
  DagAnalysis,
  ConversionOptions,
  ConversionResult,
  ValidationResult,
  ProjectConfig,
  DeploymentConfig,
  ProjectTreeNode,
} from "@/types";

// MCP App client state
let isConnected = false;
let pendingToolResult: unknown = null;
let toolResultCallback: ((result: unknown) => void) | null = null;

// Message handling
function sendMessage(message: unknown): void {
  window.parent.postMessage(message, "*");
}

function handleMessage(event: MessageEvent): void {
  const data = event.data;
  if (!data || typeof data !== "object") return;

  // Handle JSON-RPC responses
  if ("result" in data || "error" in data) {
    // This is a response to a tool call
    return;
  }

  // Handle notifications
  if (data.method === "ui/toolResult") {
    pendingToolResult = data.params;
    if (toolResultCallback) {
      toolResultCallback(data.params);
    }
  }
}

// Initialize connection with host
export async function connect(): Promise<void> {
  if (isConnected) return;

  window.addEventListener("message", handleMessage);

  // Send initialization
  sendMessage({
    jsonrpc: "2.0",
    method: "ui/initialize",
    params: {
      name: "Airflow Migration Wizard",
      version: "1.0.0",
    },
    id: "init",
  });

  isConnected = true;
}

// Set callback for initial tool result
export function onToolResult(callback: (result: unknown) => void): void {
  toolResultCallback = callback;
  if (pendingToolResult) {
    callback(pendingToolResult);
  }
}

// Call a tool on the server
let callId = 0;
async function callTool<T>(name: string, args: Record<string, unknown>): Promise<T> {
  const id = `call-${++callId}`;

  return new Promise((resolve, reject) => {
    const handler = (event: MessageEvent) => {
      const data = event.data;
      if (!data || data.id !== id) return;

      window.removeEventListener("message", handler);

      if (data.error) {
        reject(new Error(data.error.message || "Tool call failed"));
      } else {
        // Parse the result content
        const content = data.result?.content;
        if (Array.isArray(content)) {
          const textContent = content.find((c: { type: string }) => c.type === "text");
          if (textContent?.text) {
            try {
              resolve(JSON.parse(textContent.text));
            } catch {
              resolve(textContent.text as T);
            }
          } else {
            resolve(data.result as T);
          }
        } else {
          resolve(data.result as T);
        }
      }
    };

    window.addEventListener("message", handler);

    sendMessage({
      jsonrpc: "2.0",
      method: "tools/call",
      params: { name, arguments: args },
      id,
    });

    // Timeout after 60 seconds
    setTimeout(() => {
      window.removeEventListener("message", handler);
      reject(new Error("Tool call timed out"));
    }, 60000);
  });
}

// Tool wrappers

export async function listDagFiles(directory: string): Promise<{ path: string; name: string }[]> {
  // This will be implemented when integrated with Python server
  // For now, return mock data for testing
  return callTool<{ path: string; name: string }[]>("wizard/list-dags", { directory });
}

export async function analyzeDag(path: string): Promise<DagAnalysis> {
  return callTool<DagAnalysis>("wizard/analyze", { path });
}

export async function analyzeDags(paths: string[]): Promise<DagAnalysis[]> {
  const results = await Promise.all(paths.map((path) => analyzeDag(path)));
  return results;
}

export async function convertDag(
  path: string,
  options: ConversionOptions
): Promise<ConversionResult> {
  return callTool<ConversionResult>("wizard/convert", {
    path,
    include_comments: options.includeComments,
    generate_tests: options.generateTests,
    include_runbook: options.generateRunbook,
  });
}

export async function validateConversion(
  originalDag: string,
  convertedFlow: string
): Promise<ValidationResult> {
  return callTool<ValidationResult>("wizard/validate", {
    original_dag: originalDag,
    converted_flow: convertedFlow,
  });
}

export async function scaffoldProject(
  config: ProjectConfig,
  deploymentConfig: DeploymentConfig,
  conversions: Map<string, ConversionResult>
): Promise<ProjectTreeNode> {
  const flows = Array.from(conversions.entries()).map(([dagId, conv]) => ({
    dagId,
    flowCode: conv.flowCode,
    testCode: conv.testCode,
    runbook: conv.runbook,
  }));

  return callTool<ProjectTreeNode>("wizard/scaffold", {
    project_name: config.projectName,
    workspace: config.workspace,
    include_docker: config.includeDockerfile,
    include_github_actions: config.includeGithubActions,
    flows,
    deployment_config: deploymentConfig,
  });
}

// Check if running in MCP App context
export function isMcpAppContext(): boolean {
  try {
    return window.parent !== window;
  } catch {
    return false;
  }
}
