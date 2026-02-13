# Wizard Steps Spec

## Overview

Implement the 7 wizard steps with full functionality, each handling its specific part of the migration workflow.

## Step 1: DAG Selector

### Requirements

1. **File input**
   - Text input for directory path
   - Browse button (if host supports file picker)
   - Paste path from clipboard

2. **DAG list display**
   - List all `.py` files in directory
   - Quick complexity assessment (file size, operator count heuristics)
   - Complexity badge: Simple (green), Medium (amber), Complex (red)

3. **Selection**
   - Checkbox per DAG file
   - Select All / Deselect All buttons
   - Search/filter input
   - Selection count display

4. **Actions**
   - "Analyze Selected" button
   - Disabled if no DAGs selected
   - Shows loading state during quick scan

### Component Interface

```typescript
interface DagSelectorProps {
  dagsDirectory: string | null;
  selectedDags: string[];
  onDirectoryChange: (dir: string) => void;
  onSelectionChange: (dags: string[]) => void;
  onAnalyze: () => void;
}
```

## Step 2: Analysis View

### Requirements

1. **Analysis display**
   - Accordion for each analyzed DAG
   - Expand to see full details
   - Summary line: "8 tasks, 6 supported, 2 warnings"

2. **Per-DAG details**
   - **Operators table**: Name, Type, Support Status, Notes
   - **Dependencies**: Task count, edge count, graph type (linear, fan-out, complex)
   - **Features detected**: TaskFlow, Datasets, Sensors, Custom Operators
   - **Complexity score**: 0-100 with breakdown

3. **Warnings panel**
   - Prominent display of issues
   - Severity badges (Warning, Error)
   - Actionable descriptions
   - Links to documentation

4. **Summary stats**
   - Total DAGs analyzed
   - Total operators (supported / unsupported)
   - Average complexity score
   - Blocking issues count

### Component Interface

```typescript
interface AnalysisViewProps {
  analyses: Map<string, DagAnalysis>;
  status: 'idle' | 'loading' | 'complete' | 'error';
  error?: string;
}

interface DagAnalysis {
  dagId: string;
  filePath: string;
  operators: OperatorInfo[];
  dependencies: DependencyInfo;
  features: FeatureFlags;
  complexityScore: number;
  warnings: Warning[];
}
```

## Step 3: Conversion Configuration

### Requirements

1. **Global options**
   - Include educational comments (default: true)
   - Generate pytest tests (default: true)
   - Generate migration runbook (default: true)
   - Preserve Airflow comments (default: false)

2. **Output structure**
   - Radio group with 3 options:
     - Flat: All flows in single directory
     - PrefectHQ/flows: Workspace/flow structure (default)
     - Custom: User-defined template

3. **PrefectHQ/flows structure preview**
   ```
   deployments/
     {workspace}/
       prefect.yaml
       {flow-name}/
         flow.py
         requirements.txt
         Dockerfile
         test_flow.py
   ```

4. **Per-DAG overrides** (optional accordion)
   - Override any global option per DAG
   - Skip specific DAGs
   - Custom output path

### Component Interface

```typescript
interface ConversionConfigProps {
  options: ConversionOptions;
  dagOverrides: Map<string, Partial<ConversionOptions>>;
  onChange: (options: ConversionOptions) => void;
  onOverrideChange: (dagId: string, override: Partial<ConversionOptions>) => void;
}

interface ConversionOptions {
  includeComments: boolean;
  generateTests: boolean;
  generateRunbook: boolean;
  preserveAirflowComments: boolean;
  outputStructure: 'flat' | 'prefect-flows' | 'custom';
  customTemplate?: string;
}
```

## Step 4: Validation View

### Requirements

1. **Progress tracking**
   - Overall progress bar
   - Current phase: "Converting..." / "Validating..."
   - Per-DAG status indicators

2. **Conversion results**
   - Success/failure status per DAG
   - Generated file count
   - Warnings from conversion

3. **Validation results**
   - Confidence score with color coding
   - Task count comparison
   - Dependency preservation status
   - XCom conversion status
   - Issue list with details

4. **Side-by-side view** (expandable)
   - DAG structure (tasks, edges)
   - Flow structure (tasks, edges)
   - Highlight differences

### Component Interface

```typescript
interface ValidationViewProps {
  conversions: Map<string, ConversionResult>;
  validations: Map<string, ValidationResult>;
  status: 'idle' | 'converting' | 'validating' | 'complete' | 'error';
  progress: number; // 0-100
  currentDag: string | null;
}

interface ConversionResult {
  dagId: string;
  success: boolean;
  flowCode: string;
  testCode?: string;
  runbook?: string;
  warnings: string[];
  error?: string;
}

interface ValidationResult {
  dagId: string;
  isValid: boolean;
  confidenceScore: number;
  taskCountMatch: boolean;
  dependencyPreserved: boolean;
  issues: ValidationIssue[];
  dagTasks: string[];
  flowTasks: string[];
  dagEdges: [string, string][];
  flowEdges: [string, string][];
}
```

## Step 5: Project Setup

### Requirements

1. **Project identity**
   - Project name (default: inferred from directory)
   - Workspace name (default: "default")
   - Description (optional)

2. **Infrastructure options**
   - Include pyproject.toml (default: true)
   - Include Dockerfile per flow (default: true)
   - Include GitHub Actions CI (default: false)
   - Include pre-commit config (default: false)
   - Include mise.toml (default: false)

3. **Dependency management**
   - Auto-detected from conversions
   - Add/remove dependencies
   - Version pinning options

4. **Preview panels**
   - pyproject.toml preview
   - .gitignore preview
   - README.md preview

### Component Interface

```typescript
interface ProjectSetupProps {
  config: ProjectConfig;
  detectedDependencies: string[];
  onChange: (config: ProjectConfig) => void;
}

interface ProjectConfig {
  projectName: string;
  workspace: string;
  description: string;
  includePyproject: boolean;
  includeDockerfile: boolean;
  includeGithubActions: boolean;
  includePrecommit: boolean;
  includeMise: boolean;
  dependencies: string[];
}
```

## Step 6: Deployment Configuration

### Requirements

1. **Work pool configuration**
   - Work pool name input
   - Work pool type selector (process, docker, kubernetes)
   - Link to Prefect docs for setup

2. **Docker configuration** (if applicable)
   - Docker registry URL
   - Image name template
   - Build configuration

3. **Deployment cards**
   - One card per flow
   - Expandable with details:
     - Deployment name
     - Description (from runbook)
     - Schedule (cron builder)
     - Parameters (JSON editor)
     - Concurrency limit
     - Collision strategy (ENQUEUE, CANCEL_NEW)

4. **prefect.yaml preview**
   - Syntax-highlighted YAML
   - Live updates as config changes
   - Copy to clipboard button

### Component Interface

```typescript
interface DeploymentConfigProps {
  config: DeploymentConfig;
  flows: string[];
  onChange: (config: DeploymentConfig) => void;
}

interface DeploymentConfig {
  workPool: {
    name: string;
    type: 'process' | 'docker' | 'kubernetes';
  };
  docker?: {
    registry: string;
    imageTemplate: string;
  };
  deployments: DeploymentSpec[];
}

interface DeploymentSpec {
  flowId: string;
  name: string;
  description: string;
  schedule?: {
    cron: string;
    timezone: string;
  };
  parameters?: Record<string, unknown>;
  concurrencyLimit?: number;
  concurrencyOptions?: {
    collisionStrategy: 'ENQUEUE' | 'CANCEL_NEW';
  };
}
```

## Step 7: Export View

### Requirements

1. **Project tree**
   - Expandable file tree
   - File icons by type
   - Click to preview file contents

2. **File preview**
   - Syntax highlighting for code
   - YAML/JSON formatting
   - Line numbers

3. **Export actions**
   - Download as ZIP
   - Copy individual file to clipboard
   - Copy all to clipboard (concatenated with headers)
   - Deploy button (if Prefect CLI available)

4. **Deploy flow** (optional)
   - Check Prefect authentication
   - Show deployment preview
   - Execute `prefect deploy`
   - Show success/error status

### Component Interface

```typescript
interface ExportViewProps {
  project: ProjectTree;
  onDownloadZip: () => void;
  onCopyFile: (path: string) => void;
  onCopyAll: () => void;
  onDeploy: () => void;
}

interface ProjectTree {
  name: string;
  type: 'directory' | 'file';
  children?: ProjectTree[];
  content?: string;
}
```

## Acceptance Criteria

- [ ] Step 1: Can select DAGs from directory path
- [ ] Step 1: Shows complexity indicators
- [ ] Step 2: Displays analysis results in accordion
- [ ] Step 2: Shows warnings prominently
- [ ] Step 3: All options configurable
- [ ] Step 3: Structure preview updates live
- [ ] Step 4: Progress bar shows conversion status
- [ ] Step 4: Validation results with confidence scores
- [ ] Step 5: Project config form functional
- [ ] Step 5: Dependency detection works
- [ ] Step 6: Deployment cards for each flow
- [ ] Step 6: prefect.yaml preview accurate
- [ ] Step 7: File tree navigation works
- [ ] Step 7: Download ZIP functional
- [ ] Step 7: Copy to clipboard works
