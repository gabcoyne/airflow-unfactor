import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import express from "express";
import cors from "cors";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.PORT || "3002", 10);
const PYTHON_SERVER_URL = process.env.PYTHON_SERVER_URL || "http://localhost:3001";

// Initialize MCP Server
const server = new McpServer({
  name: "airflow-unfactor-wizard",
  version: "1.0.0",
});

const WIZARD_URI = "ui://migration-wizard/app.html";

// Register the migration wizard tool
server.tool(
  "migration-wizard",
  "Interactive wizard to migrate Airflow DAGs to Prefect flows. Opens a visual interface for selecting DAGs, configuring conversion options, and generating production-ready Prefect projects.",
  {
    dags_directory: z.string().optional().describe("Optional path to directory containing Airflow DAGs"),
  },
  async (args) => {
    const initialState = {
      dagsDirectory: args.dags_directory || null,
      timestamp: new Date().toISOString(),
    };
    return {
      content: [{ type: "text" as const, text: JSON.stringify(initialState) }],
    };
  }
);

// Register proxy tools that forward to Python server

async function callPythonTool(toolName: string, args: Record<string, unknown>): Promise<unknown> {
  try {
    const response = await fetch(`${PYTHON_SERVER_URL}/mcp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/call",
        params: { name: toolName, arguments: args },
        id: Date.now(),
      }),
    });

    const result = await response.json();
    if (result.error) {
      throw new Error(result.error.message || "Tool call failed");
    }
    return result.result;
  } catch (error) {
    console.error(`Error calling Python tool ${toolName}:`, error);
    throw error;
  }
}

server.tool(
  "wizard/analyze",
  "Analyze an Airflow DAG file",
  {
    path: z.string().describe("Path to DAG file"),
  },
  async (args) => {
    const result = await callPythonTool("analyze", { path: args.path });
    return {
      content: [{ type: "text" as const, text: JSON.stringify(result) }],
    };
  }
);

server.tool(
  "wizard/convert",
  "Convert an Airflow DAG to Prefect flow",
  {
    path: z.string().describe("Path to DAG file"),
    include_comments: z.boolean().optional().describe("Include educational comments"),
    generate_tests: z.boolean().optional().describe("Generate pytest tests"),
    include_runbook: z.boolean().optional().describe("Generate migration runbook"),
  },
  async (args) => {
    const result = await callPythonTool("convert", args);
    return {
      content: [{ type: "text" as const, text: JSON.stringify(result) }],
    };
  }
);

server.tool(
  "wizard/validate",
  "Validate a conversion by comparing DAG and flow",
  {
    original_dag: z.string().describe("Path to original DAG"),
    converted_flow: z.string().describe("Converted flow code"),
  },
  async (args) => {
    const result = await callPythonTool("validate", args);
    return {
      content: [{ type: "text" as const, text: JSON.stringify(result) }],
    };
  }
);

server.tool(
  "wizard/scaffold",
  "Generate a complete Prefect project structure",
  {
    project_name: z.string().describe("Project name"),
    workspace: z.string().describe("Workspace name"),
    include_docker: z.boolean().optional().describe("Include Dockerfiles"),
    include_github_actions: z.boolean().optional().describe("Include GitHub Actions"),
  },
  async (args) => {
    const result = await callPythonTool("scaffold", args);
    return {
      content: [{ type: "text" as const, text: JSON.stringify(result) }],
    };
  }
);

// Register UI resource
server.resource(
  WIZARD_URI,
  WIZARD_URI,
  { mimeType: "text/html" },
  async () => {
    const htmlPath = path.join(__dirname, "dist", "index.html");
    const html = await fs.readFile(htmlPath, "utf-8");
    return {
      contents: [{ uri: WIZARD_URI, mimeType: "text/html", text: html }],
    };
  }
);

// Express app for HTTP transport
const app = express();
app.use(cors());
app.use(express.json());

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// MCP endpoint
app.post("/mcp", async (req, res) => {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
  });

  res.on("close", () => transport.close());
  await server.connect(transport);
  await transport.handleRequest(req, res, req.body);
});

// Serve static files for development
app.use(express.static(path.join(__dirname, "dist")));

// Start server
app.listen(PORT, () => {
  console.log(`Airflow Migration Wizard MCP Server`);
  console.log(`  Listening on: http://localhost:${PORT}/mcp`);
  console.log(`  Health check: http://localhost:${PORT}/health`);
  console.log(`  Python server: ${PYTHON_SERVER_URL}`);
});
