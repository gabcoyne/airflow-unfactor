# Migration Wizard MCP App — Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Desktop                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Sandboxed iframe                        │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              Migration Wizard UI                     │  │  │
│  │  │                  (React + shadcn)                    │  │  │
│  │  │                                                       │  │  │
│  │  │  WizardProvider ─────────────────────────────────    │  │  │
│  │  │       │                                              │  │  │
│  │  │       ├── DagSelector                                │  │  │
│  │  │       ├── AnalysisView                               │  │  │
│  │  │       ├── ConversionConfig                           │  │  │
│  │  │       ├── ValidationView                             │  │  │
│  │  │       ├── ProjectSetup                               │  │  │
│  │  │       ├── DeploymentConfig                           │  │  │
│  │  │       └── ExportView                                 │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                          │                                 │  │
│  │                    postMessage                             │  │
│  │                          │                                 │  │
│  └──────────────────────────┼────────────────────────────────┘  │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   MCP Server      │
                    │  (TypeScript)     │
                    │                   │
                    │  migration-wizard │◄─── UI resource
                    │  analyze          │◄─── Existing tool
                    │  convert          │◄─── Existing tool
                    │  validate         │◄─── Existing tool
                    │  scaffold         │◄─── Existing tool
                    └───────────────────┘
```

## Directory Structure

```
airflow-unfactor/
├── src/airflow_unfactor/          # Existing Python package
│   ├── mcp/                       # Existing MCP tools
│   └── ...
├── mcp-app/                       # NEW: MCP App package
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── server.ts                  # MCP server entry point
│   ├── index.html                 # UI entry point
│   └── src/
│       ├── main.tsx               # React entry
│       ├── App.tsx                # Root component
│       ├── lib/
│       │   ├── mcp.ts             # MCP App client wrapper
│       │   └── utils.ts           # shadcn utils
│       ├── components/
│       │   ├── ui/                # shadcn components
│       │   │   ├── button.tsx
│       │   │   ├── card.tsx
│       │   │   ├── checkbox.tsx
│       │   │   ├── progress.tsx
│       │   │   ├── tabs.tsx
│       │   │   ├── accordion.tsx
│       │   │   ├── alert-dialog.tsx
│       │   │   └── ...
│       │   └── wizard/
│       │       ├── WizardProvider.tsx
│       │       ├── WizardNavigation.tsx
│       │       ├── WizardStep.tsx
│       │       └── steps/
│       │           ├── DagSelector.tsx
│       │           ├── AnalysisView.tsx
│       │           ├── ConversionConfig.tsx
│       │           ├── ValidationView.tsx
│       │           ├── ProjectSetup.tsx
│       │           ├── DeploymentConfig.tsx
│       │           └── ExportView.tsx
│       ├── hooks/
│       │   ├── useWizard.ts
│       │   ├── useMcp.ts
│       │   └── useAnalysis.ts
│       └── types/
│           ├── dag.ts
│           ├── analysis.ts
│           ├── conversion.ts
│           └── project.ts
└── ...
```

## State Management

### WizardState

```typescript
interface WizardState {
  // Navigation
  currentStep: 1 | 2 | 3 | 4 | 5 | 6 | 7;
  completedSteps: Set<number>;

  // Step 1: DAG Selection
  selectedDags: string[];
  dagsDirectory: string | null;

  // Step 2: Analysis Results
  analyses: Map<string, DagAnalysis>;
  analysisStatus: 'idle' | 'loading' | 'complete' | 'error';

  // Step 3: Conversion Config
  conversionOptions: {
    includeComments: boolean;
    generateTests: boolean;
    generateRunbook: boolean;
    preserveAirflowComments: boolean;
    outputStructure: 'flat' | 'prefect-flows' | 'custom';
    customStructure?: string;
  };

  // Step 4: Validation
  conversions: Map<string, ConversionResult>;
  validations: Map<string, ValidationResult>;
  conversionStatus: 'idle' | 'converting' | 'validating' | 'complete' | 'error';
  conversionProgress: number;

  // Step 5: Project Setup
  projectConfig: {
    projectName: string;
    workspace: string;
    includePyproject: boolean;
    includeDockerfile: boolean;
    includeGithubActions: boolean;
    includePrecommit: boolean;
    includeMise: boolean;
  };

  // Step 6: Deployment Config
  deploymentConfig: {
    workPool: string;
    dockerRegistry: string;
    deployments: DeploymentSpec[];
  };

  // Step 7: Export
  generatedProject: ProjectTree | null;
  exportFormat: 'zip' | 'clipboard' | 'deploy';
}
```

### Actions

```typescript
type WizardAction =
  | { type: 'SET_STEP'; step: number }
  | { type: 'SELECT_DAGS'; dags: string[] }
  | { type: 'SET_ANALYSES'; analyses: Map<string, DagAnalysis> }
  | { type: 'SET_CONVERSION_OPTIONS'; options: Partial<ConversionOptions> }
  | { type: 'SET_CONVERSION_RESULT'; dagId: string; result: ConversionResult }
  | { type: 'SET_VALIDATION_RESULT'; dagId: string; result: ValidationResult }
  | { type: 'SET_PROJECT_CONFIG'; config: Partial<ProjectConfig> }
  | { type: 'SET_DEPLOYMENT_CONFIG'; config: Partial<DeploymentConfig> }
  | { type: 'SET_GENERATED_PROJECT'; project: ProjectTree }
  | { type: 'RESET' };
```

## MCP Integration

### Server Setup

```typescript
// mcp-app/server.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { registerAppTool, registerAppResource, RESOURCE_MIME_TYPE } from "@modelcontextprotocol/ext-apps/server";
import express from "express";
import cors from "cors";
import fs from "node:fs/promises";
import path from "node:path";

const server = new McpServer({
  name: "airflow-unfactor",
  version: "1.0.0",
});

const WIZARD_URI = "ui://migration-wizard/app.html";

// Register the wizard tool
registerAppTool(
  server,
  "migration-wizard",
  {
    title: "Airflow Migration Wizard",
    description: "Interactive wizard to migrate Airflow DAGs to Prefect flows. Opens a visual interface for selecting DAGs, configuring conversion options, and generating production-ready Prefect projects.",
    inputSchema: {
      type: "object",
      properties: {
        dags_directory: {
          type: "string",
          description: "Optional path to directory containing Airflow DAGs"
        }
      }
    },
    _meta: { ui: { resourceUri: WIZARD_URI } }
  },
  async (args) => {
    // Return initial state for the wizard
    const initialState = {
      dagsDirectory: args.dags_directory || null,
      timestamp: new Date().toISOString()
    };
    return {
      content: [{ type: "text", text: JSON.stringify(initialState) }]
    };
  }
);

// Register the UI resource
registerAppResource(
  server,
  WIZARD_URI,
  WIZARD_URI,
  { mimeType: RESOURCE_MIME_TYPE },
  async () => {
    const html = await fs.readFile(
      path.join(import.meta.dirname, "dist", "index.html"),
      "utf-8"
    );
    return {
      contents: [{ uri: WIZARD_URI, mimeType: RESOURCE_MIME_TYPE, text: html }]
    };
  }
);

// Proxy tools - forward to Python MCP server
// These wrap the existing Python tools for the UI to call

server.tool("wizard/analyze", {
  description: "Analyze Airflow DAG files",
  inputSchema: {
    type: "object",
    properties: {
      paths: { type: "array", items: { type: "string" } }
    },
    required: ["paths"]
  }
}, async (args) => {
  // Forward to Python server via HTTP or subprocess
  const results = await forwardToPythonServer("analyze", args);
  return { content: [{ type: "text", text: JSON.stringify(results) }] };
});

// Similar proxy tools for convert, validate, scaffold...
```

### Client Integration

```typescript
// mcp-app/src/lib/mcp.ts
import { App } from "@modelcontextprotocol/ext-apps";

const app = new App({
  name: "Migration Wizard",
  version: "1.0.0"
});

export async function initialize(): Promise<void> {
  await app.connect();
}

export async function analyzeDags(paths: string[]): Promise<DagAnalysis[]> {
  const result = await app.callServerTool({
    name: "wizard/analyze",
    arguments: { paths }
  });
  const text = result.content?.find(c => c.type === "text")?.text;
  return text ? JSON.parse(text) : [];
}

export async function convertDag(
  path: string,
  options: ConversionOptions
): Promise<ConversionResult> {
  const result = await app.callServerTool({
    name: "wizard/convert",
    arguments: { path, ...options }
  });
  const text = result.content?.find(c => c.type === "text")?.text;
  return text ? JSON.parse(text) : null;
}

export async function validateConversion(
  originalDag: string,
  convertedFlow: string
): Promise<ValidationResult> {
  const result = await app.callServerTool({
    name: "wizard/validate",
    arguments: { original_dag: originalDag, converted_flow: convertedFlow }
  });
  const text = result.content?.find(c => c.type === "text")?.text;
  return text ? JSON.parse(text) : null;
}

export async function scaffoldProject(
  config: ProjectConfig
): Promise<ProjectTree> {
  const result = await app.callServerTool({
    name: "wizard/scaffold",
    arguments: config
  });
  const text = result.content?.find(c => c.type === "text")?.text;
  return text ? JSON.parse(text) : null;
}

// Handle initial tool result
export function onToolResult(callback: (result: any) => void): void {
  app.ontoolresult = (result) => {
    const text = result.content?.find(c => c.type === "text")?.text;
    if (text) {
      callback(JSON.parse(text));
    }
  };
}
```

## Component Design

### WizardNavigation

```tsx
// Horizontal step indicator with clickable steps
interface WizardNavigationProps {
  currentStep: number;
  completedSteps: Set<number>;
  onStepClick: (step: number) => void;
}

const steps = [
  { number: 1, label: "Select DAGs", icon: FolderIcon },
  { number: 2, label: "Analysis", icon: SearchIcon },
  { number: 3, label: "Configure", icon: SettingsIcon },
  { number: 4, label: "Validate", icon: CheckCircleIcon },
  { number: 5, label: "Project", icon: PackageIcon },
  { number: 6, label: "Deploy", icon: RocketIcon },
  { number: 7, label: "Export", icon: DownloadIcon },
];
```

### DagSelector (Step 1)

```tsx
interface DagSelectorProps {
  selectedDags: string[];
  onSelect: (dags: string[]) => void;
  onAnalyze: () => void;
}

// Features:
// - Directory browser with file tree
// - Checkbox selection for individual files
// - Complexity badge (Simple/Medium/Complex) from quick heuristics
// - "Select All" / "Deselect All" buttons
// - Search/filter input
```

### AnalysisView (Step 2)

```tsx
interface AnalysisViewProps {
  analyses: Map<string, DagAnalysis>;
  status: 'loading' | 'complete' | 'error';
}

// Features:
// - Accordion for each DAG
// - Operator table with support status
// - Dependency graph visualization (simple)
// - Feature checklist (TaskFlow, Datasets, Sensors)
// - Warning cards with details
// - Complexity score breakdown
```

### ConversionConfig (Step 3)

```tsx
interface ConversionConfigProps {
  options: ConversionOptions;
  onChange: (options: Partial<ConversionOptions>) => void;
}

// Features:
// - Checkbox group for options
// - Radio group for output structure
// - Preview of directory structure
// - Per-DAG override accordion (optional)
```

### ValidationView (Step 4)

```tsx
interface ValidationViewProps {
  conversions: Map<string, ConversionResult>;
  validations: Map<string, ValidationResult>;
  status: 'converting' | 'validating' | 'complete';
  progress: number;
}

// Features:
// - Overall progress bar
// - Per-DAG status cards
// - Confidence score with color coding
// - Expandable diff view (DAG vs Flow structure)
// - Issue list with severity badges
```

### ProjectSetup (Step 5)

```tsx
interface ProjectSetupProps {
  config: ProjectConfig;
  onChange: (config: Partial<ProjectConfig>) => void;
}

// Features:
// - Text inputs for project name, workspace
// - Checkbox group for infrastructure options
// - Live preview of pyproject.toml
// - Dependency detection from converted flows
```

### DeploymentConfig (Step 6)

```tsx
interface DeploymentConfigProps {
  config: DeploymentConfig;
  onChange: (config: Partial<DeploymentConfig>) => void;
}

// Features:
// - Work pool selector/creator
// - Docker registry input
// - Deployment cards for each flow
//   - Name, description
//   - Cron schedule builder
//   - Parameters editor
//   - Concurrency settings
// - YAML preview with syntax highlighting
```

### ExportView (Step 7)

```tsx
interface ExportViewProps {
  project: ProjectTree;
  onExport: (format: 'zip' | 'clipboard' | 'deploy') => void;
}

// Features:
// - File tree with expand/collapse
// - File preview on click
// - Download ZIP button
// - Copy file contents button
// - Deploy button (requires Prefect auth)
```

## Styling

### Design Tokens

Following shadcn defaults with minor customizations for the wizard context:

```css
:root {
  /* Colors */
  --wizard-success: hsl(142, 76%, 36%);  /* Green for completed */
  --wizard-warning: hsl(38, 92%, 50%);   /* Amber for warnings */
  --wizard-error: hsl(0, 84%, 60%);      /* Red for errors */
  --wizard-info: hsl(217, 91%, 60%);     /* Blue for info */

  /* Complexity badges */
  --complexity-simple: hsl(142, 76%, 36%);
  --complexity-medium: hsl(38, 92%, 50%);
  --complexity-complex: hsl(0, 84%, 60%);

  /* Confidence scores */
  --confidence-high: hsl(142, 76%, 36%);   /* 80-100 */
  --confidence-medium: hsl(38, 92%, 50%);  /* 60-79 */
  --confidence-low: hsl(25, 95%, 53%);     /* 40-59 */
  --confidence-very-low: hsl(0, 84%, 60%); /* 0-39 */
}
```

### Layout

- **Max width**: 800px centered
- **Step content**: Card with padding
- **Navigation**: Fixed bottom bar with Back/Next buttons
- **Progress**: Step indicator at top

## Error Handling

### Network Errors
- Toast notification for transient failures
- Retry button for failed tool calls
- Graceful degradation if Python server unavailable

### Validation Errors
- Inline error messages on form fields
- Summary of blocking issues before proceeding
- Allow proceeding with warnings (user acknowledgment)

### Conversion Errors
- Per-DAG error display
- Option to skip failed DAGs
- Detailed error accordion with stack trace

## Testing Strategy

### Unit Tests
- WizardProvider state transitions
- Individual step component rendering
- MCP client wrapper functions

### Integration Tests
- Full wizard flow with mocked MCP responses
- Step navigation and validation
- Export functionality

### E2E Tests (with basic-host)
- Full migration flow with real Python server
- File selection and analysis
- Project generation and download
